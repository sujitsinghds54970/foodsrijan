from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import io
import logging
import os
import smtplib
from decimal import Decimal
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, DailyEntry, User
from app.models.hr import StaffAttendanceLog, StaffLeaveRequest, StaffProfile, StaffSalaryDetail
from app.models.payroll.models import (
    AdvanceRequest,
    AdvanceStatus,
    PayrollAuditLog,
    PayrollLock,
    PayrollRun,
    PayrollRunStatus,
    PayrollTransaction,
)
from app.services.payroll_engine import generate_payroll_run
from app.utils.auth_system import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def _to_decimal(value: object, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _to_float(value: object) -> float:
    return float(_to_decimal(value))


def _compute_payroll_totals(
    *,
    basic: Decimal,
    da: Decimal,
    hra: Decimal,
    shift_allowance: Decimal,
    ot: Decimal,
    lop: Decimal,
    incentives: Decimal,
    statutory_deductions: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    gross_pay = basic + da + hra + shift_allowance + ot + incentives
    total_deductions = lop + statutory_deductions
    net_pay = gross_pay - total_deductions
    return gross_pay, total_deductions, net_pay


def _require_branch_director_scope(user: User) -> int:
    role = (user.role or "").strip().lower()
    if role not in {"branch_director", "branch_admin"}:
        raise HTTPException(status_code=403, detail="Branch director scope required")
    if not user.branch_id:
        raise HTTPException(status_code=400, detail="User is not assigned to a branch")
    return int(user.branch_id)


def _month_window(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def _latest_run(db: Session, branch_id: int, month: int, year: int) -> Optional[PayrollRun]:
    return (
        db.query(PayrollRun)
        .filter(PayrollRun.branch_id == branch_id, PayrollRun.month == month, PayrollRun.year == year)
        .order_by(PayrollRun.updated_at.desc(), PayrollRun.id.desc())
        .first()
    )


def _status_for_ui(run: Optional[PayrollRun], tx_count: int) -> str:
    if not run:
        return "Draft"
    status = run.status.value if hasattr(run.status, "value") else str(run.status or "Draft")
    normalized = status.strip().lower()
    if normalized == "locked":
        return "Locked"
    if normalized == "approved":
        return "Approved"
    if normalized == "ready":
        return "Ready for Approval" if tx_count > 0 else "In Review"
    if normalized == "draft":
        return "In Review" if tx_count > 0 else "Draft"
    return status


def _health_band(score: int) -> str:
    if score >= 75:
        return "Green"
    if score >= 50:
        return "Yellow"
    return "Red"


def _calculate_health_score(total_payroll: Decimal, revenue: Decimal) -> int:
    ratio = float((total_payroll / revenue) if revenue > 0 else Decimal("0"))
    return max(0, min(100, int(100 - (ratio * 42.0))))


def _current_run_or_404(db: Session, branch_id: int, payroll_run_id: Optional[int] = None) -> PayrollRun:
    if payroll_run_id is not None:
        run = db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id, PayrollRun.branch_id == branch_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Payroll run not found for current branch")
        return run
    run = (
        db.query(PayrollRun)
        .filter(PayrollRun.branch_id == branch_id)
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc(), PayrollRun.updated_at.desc(), PayrollRun.id.desc())
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="No payroll run found for current branch")
    return run


def _ensure_support_tables(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS payroll_security_settings (
                branch_id INTEGER PRIMARY KEY,
                two_factor_enabled INTEGER NOT NULL DEFAULT 0,
                updated_by INTEGER NOT NULL,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS payroll_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                action VARCHAR(40) NOT NULL,
                endpoint VARCHAR(120) NOT NULL,
                details TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.flush()


def _audit_log(db: Session, branch_id: int, user_id: int, action: str, endpoint: str, details: str) -> None:
    _ensure_support_tables(db)
    db.add(
        PayrollAuditLog(
            branch_id=branch_id,
            user_id=user_id,
            action=action,
            endpoint=endpoint,
            details=details,
        )
    )


def _statutory_for_row(row: _PayrollComputedRow) -> dict[str, Decimal]:
    basic = _to_decimal(row.basic)
    gross = _to_decimal(row.basic + row.da + row.hra + row.shift_allowance + row.ot + row.incentives)
    pf = (basic * Decimal("0.12")).quantize(Decimal("0.01"))
    esi = (gross * Decimal("0.0075")).quantize(Decimal("0.01")) if gross <= Decimal("21000") else Decimal("0.00")
    if gross >= Decimal("25000"):
        pt = Decimal("200.00")
    elif gross >= Decimal("15000"):
        pt = Decimal("150.00")
    elif gross >= Decimal("10000"):
        pt = Decimal("75.00")
    else:
        pt = Decimal("0.00")
    estimated_tds = (gross * Decimal("0.05")).quantize(Decimal("0.01"))
    return {"pf": pf, "esi": esi, "pt": pt, "tds": estimated_tds}


@dataclass
class _PayrollComputedRow:
    staff_profile_id: int
    employee_name: str
    department: str
    basic: float
    da: float
    hra: float
    shift_allowance: float
    ot: float
    lop: float
    incentives: float
    statutory_deductions: float
    net_pay: float


def _compute_grid_rows(db: Session, run: PayrollRun, branch_id: int) -> list[_PayrollComputedRow]:
    tx_rows = (
        db.query(PayrollTransaction, StaffProfile, StaffSalaryDetail, User)
        .join(StaffProfile, StaffProfile.id == PayrollTransaction.staff_id)
        .outerjoin(StaffSalaryDetail, StaffSalaryDetail.staff_profile_id == StaffProfile.id)
        .join(User, User.id == StaffProfile.user_id)
        .filter(PayrollTransaction.payroll_run_id == run.id, StaffProfile.branch_id == branch_id)
        .all()
    )

    computed_rows: list[_PayrollComputedRow] = []
    included_staff_profile_ids: set[int] = set()
    for tx, profile, salary_detail, user in tx_rows:
        included_staff_profile_ids.add(profile.id)
        basic = _to_decimal(tx.base_salary if tx.base_salary is not None else (salary_detail.basic if salary_detail else 0))
        da = _to_decimal(tx.reimbursement_amount)
        if da <= 0:
            da = basic * Decimal("0.10")
        hra = _to_decimal(salary_detail.hra if salary_detail else 0)
        shift_allowance = _to_decimal(salary_detail.allowances if salary_detail else 0)
        ot = _to_decimal(tx.overtime_hours)
        if ot <= 0 and shift_allowance > 0:
            ot = shift_allowance * Decimal("0.30")
        lop = _to_decimal(tx.lop_days)
        if lop <= 0 and basic > 0 and _to_decimal(tx.total_deductions) > 0:
            lop = (basic / Decimal("30")) * _to_decimal(tx.lop_days)
        incentives = _to_decimal(tx.incentive_amount)
        statutory_deductions = _to_decimal(salary_detail.deductions if salary_detail else 0)
        if statutory_deductions <= 0:
            statutory_deductions = max(Decimal("0"), _to_decimal(tx.total_deductions) - lop)
        gross_pay = basic + da + hra + shift_allowance + ot + incentives
        total_deductions = lop + statutory_deductions
        net_pay = gross_pay - total_deductions

        computed_rows.append(
            _PayrollComputedRow(
                staff_profile_id=profile.id,
                employee_name=f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username,
                department=(profile.department or "Unassigned").strip() or "Unassigned",
                basic=float(basic),
                da=float(da),
                hra=float(hra),
                shift_allowance=float(shift_allowance),
                ot=float(ot),
                lop=float(lop),
                incentives=float(incentives),
                statutory_deductions=float(statutory_deductions),
                net_pay=float(net_pay),
            )
        )

    missing_staff_query = (
        db.query(StaffProfile, StaffSalaryDetail, User)
        .outerjoin(StaffSalaryDetail, StaffSalaryDetail.staff_profile_id == StaffProfile.id)
        .join(User, User.id == StaffProfile.user_id)
        .filter(StaffProfile.branch_id == branch_id, StaffProfile.is_active.is_(True))
    )
    if included_staff_profile_ids:
        missing_staff_query = missing_staff_query.filter(~StaffProfile.id.in_(included_staff_profile_ids))
    missing_staff_rows = missing_staff_query.all()

    for profile, salary_detail, user in missing_staff_rows:
        basic = _to_decimal(salary_detail.basic if salary_detail else 0)
        da = basic * Decimal("0.10")
        hra = _to_decimal(salary_detail.hra if salary_detail else 0)
        allowances = _to_decimal(salary_detail.allowances if salary_detail else 0)
        shift_allowance = allowances * Decimal("0.35")
        ot = allowances * Decimal("0.30")
        incentives = allowances - shift_allowance - ot
        if incentives < 0:
            incentives = Decimal("0")
        lop = Decimal("0")
        statutory_deductions = _to_decimal(salary_detail.deductions if salary_detail else 0)
        gross_pay = basic + da + hra + shift_allowance + ot + incentives
        total_deductions = lop + statutory_deductions
        net_pay = max(Decimal("0"), gross_pay - total_deductions)

        computed_rows.append(
            _PayrollComputedRow(
                staff_profile_id=profile.id,
                employee_name=f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username,
                department=(profile.department or "Unassigned").strip() or "Unassigned",
                basic=float(basic),
                da=float(da),
                hra=float(hra),
                shift_allowance=float(shift_allowance),
                ot=float(ot),
                lop=float(lop),
                incentives=float(incentives),
                statutory_deductions=float(statutory_deductions),
                net_pay=float(net_pay),
            )
        )
    return computed_rows


def _render_payslip_pdf_bytes(run: PayrollRun, staff: StaffProfile, user: User, tx: PayrollTransaction, branch: Optional[Branch]) -> bytes:
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    y = 280 * mm
    c.setFont("Helvetica-Bold", 15)
    c.drawString(20 * mm, y, "PAYSLIP")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Branch: {(branch.name if branch else 'VaidyaVihar Diagnostic')}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Employee: {((user.first_name or '').strip() + ' ' + (user.last_name or '').strip()).strip() or user.username}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Staff ID: {staff.staff_id}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Pay Period: {run.month:02d}/{run.year}")
    y -= 10 * mm
    c.drawString(20 * mm, y, f"Basic: INR {tx.base_salary}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"DA: INR {tx.reimbursement_amount}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"OT: INR {tx.overtime_hours}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Incentives: INR {tx.incentive_amount}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Total Deductions: INR {tx.total_deductions}")
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, f"Net Pay: INR {tx.net_pay}")
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, 16 * mm, "Generated by VaidyaVihar Diagnostic. This is a computer-generated document.")
    c.showPage()
    c.save()
    packet.seek(0)
    return packet.read()


def send_payslip_email(to_email: str, user_name: str, payslip_bytes: bytes, month: int, year: int) -> bool:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username or "noreply@vaidyavihar.com")
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() != "false"

    subject = f"Salary Payslip - {month:02d}/{year}"
    html = f"""
    <html><body style="font-family:Arial,sans-serif;">
      <p>Dear {user_name},</p>
      <p>Please find attached your salary payslip for {month:02d}/{year}.</p>
      <p>Regards,<br/>VaidyaVihar Diagnostic</p>
    </body></html>
    """
    if not smtp_username or not smtp_password:
        logger.warning("SMTP not configured; payslip email skipped for %s", to_email)
        return False

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    attachment = MIMEApplication(payslip_bytes, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=f"payslip_{month:02d}_{year}.pdf")
    msg.attach(attachment)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as error:
        logger.exception("Failed to send payslip email to %s: %s", to_email, error)
        return False


def _serialize_grid_rows(rows: list[_PayrollComputedRow]) -> list[dict]:
    return [
        {
            "staff_profile_id": row.staff_profile_id,
            "employee_name": row.employee_name,
            "department": row.department,
            "basic": row.basic,
            "da": row.da,
            "hra": row.hra,
            "shift_allowance": row.shift_allowance,
            "ot": row.ot,
            "lop": row.lop,
            "incentives": row.incentives,
            "statutory_deductions": row.statutory_deductions,
            "net_pay": row.net_pay,
        }
        for row in rows
    ]


class BranchPayrollGeneratePayload(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2200)
    step: Literal["fetch_data", "review", "freeze"] = "fetch_data"


class BranchPayrollAdjustPayload(BaseModel):
    payroll_run_id: int
    adjustment_type: Literal["percent", "fixed"]
    value: float
    target_department: Optional[str] = None
    staff_profile_ids: list[int] = Field(default_factory=list)
    unlock_reason: Optional[str] = None


class BranchPayrollPreviewPayload(BaseModel):
    payroll_run_id: int


class BranchPayrollApprovePayload(BaseModel):
    payroll_run_id: int
    force_lock: bool = True


class BranchPayrollStaffCellUpdatePayload(BaseModel):
    payroll_run_id: int
    basic: float = 0
    da: float = 0
    hra: float = 0
    shift_allowance: float = 0
    ot: float = 0
    lop: float = 0
    incentives: float = 0
    statutory_deductions: float = 0


class BranchPayrollProcessSelectedPayload(BaseModel):
    staff_ids: list[int] = Field(default_factory=list)
    payroll_run_id: Optional[int] = None


class BranchPayrollSimulatePayload(BaseModel):
    department: str = Field(..., min_length=1)
    hike_percentage: float = Field(..., ge=-100, le=300)


class BranchPayrollTwoFactorPayload(BaseModel):
    enabled: bool


@router.get("/health-score")
def branch_payroll_health_score(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    now = datetime.utcnow()
    mm = month or now.month
    yy = year or now.year
    prev_mm = 12 if mm == 1 else mm - 1
    prev_yy = yy - 1 if mm == 1 else yy
    yoy_yy = yy - 1

    run = _latest_run(db, branch_id, mm, yy)
    prev_run = _latest_run(db, branch_id, prev_mm, prev_yy)
    yoy_run = _latest_run(db, branch_id, mm, yoy_yy)
    tx_count = (
        db.query(PayrollTransaction).filter(PayrollTransaction.payroll_run_id == run.id).count()
        if run
        else 0
    )

    total_branch_payroll = _to_decimal(run.total_net_pay if run else 0)
    prev_payroll = _to_decimal(prev_run.total_net_pay if prev_run else 0)
    yoy_payroll = _to_decimal(yoy_run.total_net_pay if yoy_run else 0)
    mom_variance = float(((total_branch_payroll - prev_payroll) / prev_payroll * Decimal("100")) if prev_payroll > 0 else Decimal("0"))
    yoy_variance = float(((total_branch_payroll - yoy_payroll) / yoy_payroll * Decimal("100")) if yoy_payroll > 0 else Decimal("0"))

    start, end = _month_window(yy, mm)
    revenue = _to_decimal(
        db.query(func.coalesce(func.sum(DailyEntry.total_amount), 0))
        .filter(DailyEntry.branch_id == branch_id, DailyEntry.entry_date >= start, DailyEntry.entry_date < end)
        .scalar()
    )
    ratio = float((total_branch_payroll / revenue) if revenue > 0 else Decimal("0"))

    score = _calculate_health_score(total_branch_payroll, revenue)
    status = _status_for_ui(run, tx_count)
    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/health-score",
        f"Viewed health score for {mm:02d}/{yy}",
    )
    db.commit()

    return {
        "health_score": score,
        "health_band": _health_band(score),
        "cost_to_income_ratio": ratio,
        "total_branch_payroll": float(total_branch_payroll),
        "mom_variance_percent": mom_variance,
        "yoy_variance_percent": yoy_variance,
        "payroll_run_status": status,
        "payroll_run": {
            "id": run.id,
            "month": run.month,
            "year": run.year,
            "status": status,
            "tx_count": tx_count,
        }
        if run
        else None,
        "pending_actions": [
            {"title": "Pending leave approvals", "count": int(db.query(StaffLeaveRequest).filter(StaffLeaveRequest.branch_id == branch_id, StaffLeaveRequest.status == "pending").count())},
            {"title": "Unapproved payroll runs", "count": int(db.query(PayrollRun).filter(PayrollRun.branch_id == branch_id, PayrollRun.status.in_([PayrollRunStatus.DRAFT, PayrollRunStatus.READY])).count())},
            {"title": "Pending adjustments review", "count": 1 if run and status in {"Draft", "In Review", "Ready for Approval"} else 0},
        ],
    }


@router.get("/analytics")
def branch_payroll_analytics(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    now = datetime.utcnow()
    mm = month or now.month
    yy = year or now.year
    run = _latest_run(db, branch_id, mm, yy)
    if not run:
        run = (
            db.query(PayrollRun)
            .filter(PayrollRun.branch_id == branch_id)
            .order_by(PayrollRun.year.desc(), PayrollRun.month.desc(), PayrollRun.updated_at.desc(), PayrollRun.id.desc())
            .first()
        )

    if run:
        dept_rows = (
            db.query(StaffProfile.department, func.coalesce(func.sum(PayrollTransaction.net_pay), 0))
            .join(PayrollTransaction, PayrollTransaction.staff_id == StaffProfile.id)
            .filter(PayrollTransaction.payroll_run_id == run.id, StaffProfile.branch_id == branch_id)
            .group_by(StaffProfile.department)
            .all()
        )
        dept_total = sum((_to_decimal(value) for _, value in dept_rows), Decimal("0"))
        department_burn = [
            {
                "department": (department or "Unassigned").strip() or "Unassigned",
                "amount": _to_float(amount),
                "percentage": float((_to_decimal(amount) / dept_total * Decimal("100")) if dept_total > 0 else Decimal("0")),
            }
            for department, amount in dept_rows
        ]
    else:
        department_burn = []

    # 12-month trend
    trend: list[dict] = []
    month_cursor = mm
    year_cursor = yy
    for _ in range(12):
        run_for_month = _latest_run(db, branch_id, month_cursor, year_cursor)
        if run_for_month:
            tx_count = db.query(PayrollTransaction.staff_id).filter(PayrollTransaction.payroll_run_id == run_for_month.id).distinct().count()
            trend.append(
                {
                    "label": f"{month_cursor:02d}/{year_cursor}",
                    "month": month_cursor,
                    "year": year_cursor,
                    "payroll_cost": _to_float(run_for_month.total_net_pay),
                    "employee_count": int(tx_count),
                }
            )
        else:
            trend.append(
                {
                    "label": f"{month_cursor:02d}/{year_cursor}",
                    "month": month_cursor,
                    "year": year_cursor,
                    "payroll_cost": 0.0,
                    "employee_count": 0,
                }
            )

        if month_cursor == 1:
            month_cursor = 12
            year_cursor -= 1
        else:
            month_cursor -= 1
    trend.reverse()

    overtime_total = Decimal("0")
    allowance_total = Decimal("0")
    incentive_total = Decimal("0")
    reimbursement_total = Decimal("0")
    top_earners: list[dict] = []
    if run:
        tx_rows = (
            db.query(PayrollTransaction, StaffProfile, StaffSalaryDetail, User)
            .join(StaffProfile, StaffProfile.id == PayrollTransaction.staff_id)
            .outerjoin(StaffSalaryDetail, StaffSalaryDetail.staff_profile_id == StaffProfile.id)
            .join(User, User.id == StaffProfile.user_id)
            .filter(PayrollTransaction.payroll_run_id == run.id, StaffProfile.branch_id == branch_id)
            .order_by(PayrollTransaction.net_pay.desc())
            .all()
        )
        included_top_earner_ids: set[int] = set()
        for tx, profile, salary_detail, user in tx_rows:
            included_top_earner_ids.add(profile.id)
            basic = _to_decimal(tx.base_salary)
            overtime_hours = _to_decimal(tx.overtime_hours)
            overtime_total += overtime_hours * (basic / Decimal("240") if basic > 0 else Decimal("0")) * Decimal("1.5")
            allowance_total += _to_decimal(salary_detail.allowances if salary_detail else 0) + _to_decimal(salary_detail.hra if salary_detail else 0)
            incentive_total += _to_decimal(tx.incentive_amount)
            reimbursement_total += _to_decimal(tx.reimbursement_amount)
            if len(top_earners) < 8:
                top_earners.append(
                    {
                        "staff_profile_id": profile.id,
                        "employee_name": f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username,
                        "department": (profile.department or "Unassigned").strip() or "Unassigned",
                        "net_pay": _to_float(tx.net_pay),
                        "basic": _to_float(tx.base_salary),
                        "incentives": _to_float(tx.incentive_amount),
                        "deductions": _to_float(tx.total_deductions),
                    }
                )

        missing_top_earners_query = (
            db.query(StaffProfile, StaffSalaryDetail, User)
            .outerjoin(StaffSalaryDetail, StaffSalaryDetail.staff_profile_id == StaffProfile.id)
            .join(User, User.id == StaffProfile.user_id)
            .filter(StaffProfile.branch_id == branch_id, StaffProfile.is_active.is_(True))
        )
        if included_top_earner_ids:
            missing_top_earners_query = missing_top_earners_query.filter(~StaffProfile.id.in_(included_top_earner_ids))
        missing_top_earners = missing_top_earners_query.all()
        for profile, salary_detail, user in missing_top_earners:
            basic = _to_decimal(salary_detail.basic if salary_detail else 0)
            da = basic * Decimal("0.10")
            hra = _to_decimal(salary_detail.hra if salary_detail else 0)
            allowances = _to_decimal(salary_detail.allowances if salary_detail else 0)
            shift_allowance = allowances * Decimal("0.35")
            ot = allowances * Decimal("0.30")
            incentives = allowances - shift_allowance - ot
            if incentives < 0:
                incentives = Decimal("0")
            deductions = _to_decimal(salary_detail.deductions if salary_detail else 0)
            gross = basic + da + hra + shift_allowance + ot + incentives
            net = max(Decimal("0"), gross - deductions)

            overtime_total += ot
            allowance_total += allowances + hra
            incentive_total += incentives
            if len(top_earners) < 16:
                top_earners.append(
                    {
                        "staff_profile_id": profile.id,
                        "employee_name": f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username,
                        "department": (profile.department or "Unassigned").strip() or "Unassigned",
                        "net_pay": _to_float(net),
                        "basic": _to_float(basic),
                        "incentives": _to_float(incentives),
                        "deductions": _to_float(deductions),
                    }
                )
        top_earners.sort(key=lambda item: item["net_pay"], reverse=True)
        top_earners = top_earners[:8]

    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/analytics",
        f"Viewed analytics for {mm:02d}/{yy}",
    )
    db.commit()
    return {
        "department_wise_burn": department_burn,
        "payroll_trend_12m": trend,
        "employee_count_vs_payroll_cost": [
            {"label": item["label"], "employee_count": item["employee_count"], "payroll_cost": item["payroll_cost"]}
            for item in trend
        ],
        "overtime_allowance_breakdown": {
            "overtime": float(overtime_total),
            "allowances": float(allowance_total),
            "incentives": float(incentive_total),
            "reimbursements": float(reimbursement_total),
        },
        "top_earners": top_earners,
    }


@router.post("/generate")
def branch_generate_payroll(
    payload: BranchPayrollGeneratePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    try:
        run = generate_payroll_run(
            db=db,
            branch_id=branch_id,
            month=payload.month,
            year=payload.year,
            generated_by_user_id=current_user.id,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    if payload.step == "fetch_data":
        run.status = PayrollRunStatus.DRAFT
    elif payload.step == "review":
        run.status = PayrollRunStatus.READY
    elif payload.step == "freeze":
        run.status = PayrollRunStatus.LOCKED
        run.approved_by = current_user.id
        run.approved_at = datetime.utcnow()
        db.add(
            PayrollLock(
                payroll_run_id=run.id,
                unlocked_by=None,
                unlock_reason="Freeze step lock",
                unlocked_at=None,
            )
        )

    action = "locking" if payload.step == "freeze" else "editing"
    _audit_log(
        db,
        branch_id,
        current_user.id,
        action,
        "/api/branch/payroll/generate",
        f"Generate step {payload.step} for run {run.id}",
    )
    db.commit()
    db.refresh(run)
    rows = _compute_grid_rows(db, run, branch_id)
    return {
        "message": f"Payroll flow step '{payload.step}' completed",
        "payroll_run": {
            "id": run.id,
            "month": run.month,
            "year": run.year,
            "status": _status_for_ui(run, len(rows)),
            "total_gross_pay": _to_float(run.total_gross_pay),
            "total_deductions": _to_float(run.total_deductions),
            "total_net_pay": _to_float(run.total_net_pay),
        },
        "grid_rows": _serialize_grid_rows(rows),
    }


@router.put("/adjust")
def branch_adjust_payroll(
    payload: BranchPayrollAdjustPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    run = db.query(PayrollRun).filter(PayrollRun.id == payload.payroll_run_id, PayrollRun.branch_id == branch_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found for current branch")

    if run.status == PayrollRunStatus.LOCKED:
        if not payload.unlock_reason or not payload.unlock_reason.strip():
            raise HTTPException(status_code=409, detail="Payroll is locked. Unlock reason is required for post-approval edits.")
        db.add(
            PayrollLock(
                payroll_run_id=run.id,
                unlocked_by=current_user.id,
                unlock_reason=payload.unlock_reason.strip(),
                unlocked_at=datetime.utcnow(),
            )
        )
        run.status = PayrollRunStatus.DRAFT

    query = (
        db.query(PayrollTransaction)
        .join(StaffProfile, StaffProfile.id == PayrollTransaction.staff_id)
        .filter(PayrollTransaction.payroll_run_id == run.id, StaffProfile.branch_id == branch_id)
    )

    if payload.target_department:
        query = query.filter(StaffProfile.department == payload.target_department)
    if payload.staff_profile_ids:
        query = query.filter(PayrollTransaction.staff_id.in_(payload.staff_profile_ids))

    targets = query.all()
    if not targets:
        raise HTTPException(status_code=404, detail="No employees matched the adjustment criteria")

    for tx in targets:
        net_before = _to_decimal(tx.net_pay)
        if payload.adjustment_type == "percent":
            delta = (net_before * _to_decimal(payload.value)) / Decimal("100")
        else:
            delta = _to_decimal(payload.value)
        tx.incentive_amount = (_to_decimal(tx.incentive_amount) + delta).quantize(Decimal("0.01"))
        tx.net_pay = max(Decimal("0"), (net_before + delta)).quantize(Decimal("0.01"))

    run.total_net_pay = sum((_to_decimal(tx.net_pay) for tx in db.query(PayrollTransaction).filter(PayrollTransaction.payroll_run_id == run.id).all()), Decimal("0")).quantize(Decimal("0.01"))
    _audit_log(
        db,
        branch_id,
        current_user.id,
        "editing",
        "/api/branch/payroll/adjust",
        f"Adjustment type={payload.adjustment_type} value={payload.value} run={run.id}",
    )
    db.commit()
    db.refresh(run)
    rows = _compute_grid_rows(db, run, branch_id)
    return {
        "message": "Bulk adjustment applied",
        "affected_employees": len(targets),
        "payroll_run_status": _status_for_ui(run, len(rows)),
        "total_net_pay": _to_float(run.total_net_pay),
        "grid_rows": _serialize_grid_rows(rows),
    }


@router.post("/preview")
def branch_preview_payroll(
    payload: BranchPayrollPreviewPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    run = db.query(PayrollRun).filter(PayrollRun.id == payload.payroll_run_id, PayrollRun.branch_id == branch_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found for current branch")

    rows = _compute_grid_rows(db, run, branch_id)
    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/preview",
        f"Previewed run {run.id}",
    )
    db.commit()
    return {
        "payroll_run": {
            "id": run.id,
            "month": run.month,
            "year": run.year,
            "status": _status_for_ui(run, len(rows)),
            "total_gross_pay": _to_float(run.total_gross_pay),
            "total_deductions": _to_float(run.total_deductions),
            "total_net_pay": _to_float(run.total_net_pay),
        },
        "summary": {
            "employee_count": len(rows),
            "total_net_pay": _to_float(run.total_net_pay),
        },
        "grid_rows": _serialize_grid_rows(rows),
    }


@router.post("/approve")
def branch_approve_payroll(
    payload: BranchPayrollApprovePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    run = db.query(PayrollRun).filter(PayrollRun.id == payload.payroll_run_id, PayrollRun.branch_id == branch_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found for current branch")
    if run.status == PayrollRunStatus.LOCKED:
        raise HTTPException(status_code=409, detail="Payroll is already locked")

    run.approved_by = current_user.id
    run.approved_at = datetime.utcnow()
    run.status = PayrollRunStatus.LOCKED if payload.force_lock else PayrollRunStatus.APPROVED

    tx_rows = (
        db.query(PayrollTransaction, StaffProfile, User, StaffSalaryDetail)
        .join(StaffProfile, StaffProfile.id == PayrollTransaction.staff_id)
        .join(User, User.id == StaffProfile.user_id)
        .outerjoin(StaffSalaryDetail, StaffSalaryDetail.staff_profile_id == StaffProfile.id)
        .filter(PayrollTransaction.payroll_run_id == run.id, StaffProfile.branch_id == branch_id)
        .all()
    )
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    emailed_count = 0
    total_net = Decimal("0")
    total_gross = Decimal("0")
    total_deductions = Decimal("0")

    for tx, staff, user, salary_detail in tx_rows:
        basic = _to_decimal(tx.base_salary)
        da = _to_decimal(tx.reimbursement_amount)
        hra = _to_decimal(salary_detail.hra if salary_detail else 0)
        shift_allowance = _to_decimal(salary_detail.allowances if salary_detail else 0)
        ot = _to_decimal(tx.overtime_hours)
        lop = _to_decimal(tx.lop_days)
        incentives = _to_decimal(tx.incentive_amount)
        statutory_deductions = _to_decimal(salary_detail.deductions if salary_detail else 0)
        gross, deductions, net = _compute_payroll_totals(
            basic=basic,
            da=da,
            hra=hra,
            shift_allowance=shift_allowance,
            ot=ot,
            lop=lop,
            incentives=incentives,
            statutory_deductions=statutory_deductions,
        )
        net = net.quantize(Decimal("0.01"))

        tx.total_deductions = deductions.quantize(Decimal("0.01"))
        tx.net_pay = net
        total_gross += gross
        total_deductions += deductions
        total_net += net

        if user.email:
            user_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username
            payslip_pdf = _render_payslip_pdf_bytes(run, staff, user, tx, branch)
            if send_payslip_email(user.email, user_name, payslip_pdf, run.month, run.year):
                emailed_count += 1

    run.total_gross_pay = total_gross.quantize(Decimal("0.01"))
    run.total_deductions = total_deductions.quantize(Decimal("0.01"))
    run.total_net_pay = total_net.quantize(Decimal("0.01"))

    db.add(
        PayrollLock(
            payroll_run_id=run.id,
            unlocked_by=None,
            unlock_reason="Locked on branch approval",
            unlocked_at=None,
        )
    )
    _audit_log(
        db,
        branch_id,
        current_user.id,
        "approving",
        "/api/branch/payroll/approve",
        f"Approved run {run.id} force_lock={payload.force_lock}",
    )
    db.commit()
    db.refresh(run)
    return {
        "message": "Payroll approved successfully",
        "status": _status_for_ui(run, 0),
        "approved_at": run.approved_at,
        "payslips_emailed": emailed_count,
    }


@router.post("/process-selected")
def branch_process_selected_payroll(
    payload: BranchPayrollProcessSelectedPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    unique_staff_ids = [staff_id for staff_id in sorted(set(payload.staff_ids)) if staff_id > 0]
    if not unique_staff_ids:
        raise HTTPException(status_code=400, detail="At least one staff_id is required")

    run = _current_run_or_404(db, branch_id, payload.payroll_run_id)
    if run.status == PayrollRunStatus.LOCKED:
        raise HTTPException(status_code=409, detail="Payroll is locked and cannot be selectively processed")

    tx_rows = (
        db.query(PayrollTransaction, StaffProfile, User, StaffSalaryDetail)
        .join(StaffProfile, StaffProfile.id == PayrollTransaction.staff_id)
        .join(User, User.id == StaffProfile.user_id)
        .outerjoin(StaffSalaryDetail, StaffSalaryDetail.staff_profile_id == StaffProfile.id)
        .filter(
            PayrollTransaction.payroll_run_id == run.id,
            StaffProfile.branch_id == branch_id,
            StaffProfile.id.in_(unique_staff_ids),
        )
        .all()
    )
    branch = db.query(Branch).filter(Branch.id == branch_id).first()

    processed_count = 0
    emailed_count = 0
    failed_emails: list[dict[str, str]] = []

    for tx, staff, user, salary_detail in tx_rows:
        basic = _to_decimal(tx.base_salary)
        da = _to_decimal(tx.reimbursement_amount)
        hra = _to_decimal(salary_detail.hra if salary_detail else 0)
        shift_allowance = _to_decimal(salary_detail.allowances if salary_detail else 0)
        ot = _to_decimal(tx.overtime_hours)
        lop = _to_decimal(tx.lop_days)
        incentives = _to_decimal(tx.incentive_amount)
        statutory_deductions = _to_decimal(salary_detail.deductions if salary_detail else 0)
        gross, deductions, net = _compute_payroll_totals(
            basic=basic,
            da=da,
            hra=hra,
            shift_allowance=shift_allowance,
            ot=ot,
            lop=lop,
            incentives=incentives,
            statutory_deductions=statutory_deductions,
        )
        net = net.quantize(Decimal("0.01"))

        tx.total_deductions = deductions.quantize(Decimal("0.01"))
        tx.net_pay = net
        processed_count += 1

        if user.email:
            user_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username
            try:
                payslip_pdf = _render_payslip_pdf_bytes(run, staff, user, tx, branch)
                if send_payslip_email(user.email, user_name, payslip_pdf, run.month, run.year):
                    emailed_count += 1
                else:
                    failed_emails.append({"staff_id": str(staff.id), "email": user.email})
            except Exception as error:
                logger.exception("Selective payroll email failed for staff_id=%s: %s", staff.id, error)
                failed_emails.append({"staff_id": str(staff.id), "email": user.email})
        else:
            failed_emails.append({"staff_id": str(staff.id), "email": ""})

    tx_totals = db.query(PayrollTransaction).filter(PayrollTransaction.payroll_run_id == run.id).all()
    run.total_net_pay = sum((_to_decimal(item.net_pay) for item in tx_totals), Decimal("0")).quantize(Decimal("0.01"))
    run.total_deductions = sum((_to_decimal(item.total_deductions) for item in tx_totals), Decimal("0")).quantize(Decimal("0.01"))
    run.total_gross_pay = sum((_to_decimal(item.net_pay) + _to_decimal(item.total_deductions) for item in tx_totals), Decimal("0")).quantize(Decimal("0.01"))

    _audit_log(
        db,
        branch_id,
        current_user.id,
        "processing",
        "/api/branch/payroll/process-selected",
        f"Processed selected staff count={processed_count} for run={run.id}",
    )
    db.commit()

    return {
        "message": f"Processed {processed_count} selected staff",
        "payroll_run_id": run.id,
        "processed_count": processed_count,
        "emails_sent": emailed_count,
        "email_failures": failed_emails,
    }


@router.put("/staff/{staff_id}")
def branch_update_staff_payroll_row(
    staff_id: int,
    payload: BranchPayrollStaffCellUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    run = db.query(PayrollRun).filter(PayrollRun.id == payload.payroll_run_id, PayrollRun.branch_id == branch_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found for current branch")
    if run.status == PayrollRunStatus.LOCKED:
        raise HTTPException(status_code=409, detail="Payroll is locked and cannot be edited")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_id, StaffProfile.branch_id == branch_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff profile not found for current branch")

    tx = (
        db.query(PayrollTransaction)
        .filter(PayrollTransaction.payroll_run_id == run.id, PayrollTransaction.staff_id == staff_id)
        .first()
    )
    if not tx:
        tx = PayrollTransaction(payroll_run_id=run.id, staff_id=staff_id)
        db.add(tx)

    salary_detail = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == staff_id).first()
    if not salary_detail:
        salary_detail = StaffSalaryDetail(staff_profile_id=staff_id)
        db.add(salary_detail)

    basic = _to_decimal(payload.basic)
    da = _to_decimal(payload.da)
    hra = _to_decimal(payload.hra)
    shift_allowance = _to_decimal(payload.shift_allowance)
    ot = _to_decimal(payload.ot)
    lop = _to_decimal(payload.lop)
    incentives = _to_decimal(payload.incentives)
    statutory_deductions = _to_decimal(payload.statutory_deductions)

    gross, total_deductions, net = _compute_payroll_totals(
        basic=basic,
        da=da,
        hra=hra,
        shift_allowance=shift_allowance,
        ot=ot,
        lop=lop,
        incentives=incentives,
        statutory_deductions=statutory_deductions,
    )
    net = net.quantize(Decimal("0.01"))

    tx.base_salary = basic.quantize(Decimal("0.01"))
    tx.reimbursement_amount = da.quantize(Decimal("0.01"))
    tx.overtime_hours = ot.quantize(Decimal("0.01"))
    tx.lop_days = lop.quantize(Decimal("0.01"))
    tx.incentive_amount = incentives.quantize(Decimal("0.01"))
    tx.total_deductions = total_deductions.quantize(Decimal("0.01"))
    tx.net_pay = net

    salary_detail.basic = basic.quantize(Decimal("0.01"))
    salary_detail.hra = hra.quantize(Decimal("0.01"))
    salary_detail.allowances = shift_allowance.quantize(Decimal("0.01"))
    salary_detail.deductions = statutory_deductions.quantize(Decimal("0.01"))
    salary_detail.net_pay = net

    tx_rows = db.query(PayrollTransaction).filter(PayrollTransaction.payroll_run_id == run.id).all()
    run.total_net_pay = sum((_to_decimal(item.net_pay) for item in tx_rows), Decimal("0")).quantize(Decimal("0.01"))
    run.total_deductions = sum((_to_decimal(item.total_deductions) for item in tx_rows), Decimal("0")).quantize(Decimal("0.01"))
    run.total_gross_pay = sum((_to_decimal(item.net_pay) + _to_decimal(item.total_deductions) for item in tx_rows), Decimal("0")).quantize(Decimal("0.01"))
    run.status = PayrollRunStatus.DRAFT

    _audit_log(
        db,
        branch_id,
        current_user.id,
        "editing",
        f"/api/branch/payroll/staff/{staff_id}",
        f"Updated payroll cells for run {run.id}",
    )
    db.commit()

    return {
        "message": "Saved",
        "staff_profile_id": staff_id,
        "payroll_run_id": run.id,
        "net_pay": float(net),
        "gross_pay": float(gross),
        "total_deductions": float(total_deductions),
    }


@router.post("/simulate")
def branch_simulate_hike(
    payload: BranchPayrollSimulatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    run = _current_run_or_404(db, branch_id)
    rows = _compute_grid_rows(db, run, branch_id)
    department = payload.department.strip()
    target_rows = [row for row in rows if row.department.lower() == department.lower()]
    if not target_rows:
        raise HTTPException(status_code=404, detail="Department not found in current payroll run")

    current_total = sum((_to_decimal(row.net_pay) for row in rows), Decimal("0"))
    target_total = sum((_to_decimal(row.net_pay) for row in target_rows), Decimal("0"))
    projected_delta = (target_total * _to_decimal(payload.hike_percentage) / Decimal("100")).quantize(Decimal("0.01"))
    projected_total = (current_total + projected_delta).quantize(Decimal("0.01"))

    start, end = _month_window(run.year, run.month)
    revenue = _to_decimal(
        db.query(func.coalesce(func.sum(DailyEntry.total_amount), 0))
        .filter(DailyEntry.branch_id == branch_id, DailyEntry.entry_date >= start, DailyEntry.entry_date < end)
        .scalar()
    )
    current_score = _calculate_health_score(current_total, revenue)
    projected_score = _calculate_health_score(projected_total, revenue)

    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/simulate",
        f"Simulated {payload.hike_percentage}% hike for {department}",
    )
    db.commit()
    return {
        "department": department,
        "hike_percentage": payload.hike_percentage,
        "current_total_cost": float(current_total),
        "projected_total_cost": float(projected_total),
        "projected_delta": float(projected_delta),
        "current_health_score": current_score,
        "projected_health_score": projected_score,
        "health_score_impact": projected_score - current_score,
    }


@router.get("/reports/statutory")
def branch_statutory_report(
    payroll_run_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    run = _current_run_or_404(db, branch_id, payroll_run_id)
    rows = _compute_grid_rows(db, run, branch_id)

    department_summary: dict[str, dict[str, Decimal]] = {}
    for row in rows:
        dept = row.department
        if dept not in department_summary:
            department_summary[dept] = {"pf": Decimal("0"), "esi": Decimal("0"), "pt": Decimal("0"), "tds": Decimal("0")}
        statutory = _statutory_for_row(row)
        for key in ("pf", "esi", "pt", "tds"):
            department_summary[dept][key] += statutory[key]

    contributions = []
    totals = {"pf": Decimal("0"), "esi": Decimal("0"), "pt": Decimal("0"), "tds": Decimal("0"), "total": Decimal("0")}
    for department, values in sorted(department_summary.items(), key=lambda item: item[0].lower()):
        total = values["pf"] + values["esi"] + values["pt"] + values["tds"]
        totals["pf"] += values["pf"]
        totals["esi"] += values["esi"]
        totals["pt"] += values["pt"]
        totals["tds"] += values["tds"]
        totals["total"] += total
        contributions.append(
            {
                "department": department,
                "pf": float(values["pf"]),
                "esi": float(values["esi"]),
                "pt": float(values["pt"]),
                "tds": float(values["tds"]),
                "total": float(total),
            }
        )

    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/reports/statutory",
        f"Viewed statutory report for run {run.id}",
    )
    db.commit()
    return {
        "payroll_run_id": run.id,
        "month": run.month,
        "year": run.year,
        "contributions": contributions,
        "totals": {key: float(value) for key, value in totals.items()},
    }


@router.get("/reports/bank-file")
def branch_bank_file(
    payroll_run_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    run = _current_run_or_404(db, branch_id, payroll_run_id)

    tx_rows = (
        db.query(PayrollTransaction, StaffProfile, StaffSalaryDetail, User)
        .join(StaffProfile, StaffProfile.id == PayrollTransaction.staff_id)
        .outerjoin(StaffSalaryDetail, StaffSalaryDetail.staff_profile_id == StaffProfile.id)
        .join(User, User.id == StaffProfile.user_id)
        .filter(PayrollTransaction.payroll_run_id == run.id, StaffProfile.branch_id == branch_id)
        .all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["beneficiary_name", "account_number", "ifsc", "amount", "reference", "payment_mode"])
    for tx, profile, salary_detail, user in tx_rows:
        writer.writerow(
            [
                f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username,
                (salary_detail.account_number if salary_detail else "") or "N/A",
                (salary_detail.ifsc_code if salary_detail else "") or "N/A",
                f"{_to_float(tx.net_pay):.2f}",
                f"PAYROLL-{run.id}-{profile.staff_id}",
                "NEFT",
            ]
        )

    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/reports/bank-file",
        f"Generated bank file for run {run.id}",
    )
    db.commit()

    output = io.BytesIO(buffer.getvalue().encode("utf-8"))
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=bank_file_run_{run.id}.csv"},
    )


@router.get("/reports/payroll")
def branch_payroll_report_export(
    format: Literal["pdf", "excel", "csv"] = Query(default="csv"),
    payroll_run_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    run = _current_run_or_404(db, branch_id, payroll_run_id)
    rows = _compute_grid_rows(db, run, branch_id)

    if format == "csv":
        text_buffer = io.StringIO()
        writer = csv.writer(text_buffer)
        writer.writerow(["employee_name", "department", "basic", "da", "hra", "shift_allowance", "ot", "lop", "incentives", "statutory_deductions", "net_pay"])
        for row in rows:
            writer.writerow([row.employee_name, row.department, row.basic, row.da, row.hra, row.shift_allowance, row.ot, row.lop, row.incentives, row.statutory_deductions, row.net_pay])
        payload = io.BytesIO(text_buffer.getvalue().encode("utf-8"))
        media_type = "text/csv"
        filename = f"payroll_report_{run.month:02d}_{run.year}.csv"
    elif format == "excel":
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Payroll Report"
        sheet.append(["Employee", "Department", "Basic", "DA", "HRA", "Shift Allowance", "OT", "LOP", "Incentives", "Statutory Deductions", "Net Pay"])
        for row in rows:
            sheet.append([row.employee_name, row.department, row.basic, row.da, row.hra, row.shift_allowance, row.ot, row.lop, row.incentives, row.statutory_deductions, row.net_pay])
        binary = io.BytesIO()
        workbook.save(binary)
        binary.seek(0)
        payload = binary
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"payroll_report_{run.month:02d}_{run.year}.xlsx"
    else:
        packet = io.BytesIO()
        report_canvas = canvas.Canvas(packet, pagesize=A4)
        report_canvas.setFont("Helvetica-Bold", 13)
        report_canvas.drawString(20 * mm, 280 * mm, f"Payroll Report {run.month:02d}/{run.year}")
        report_canvas.setFont("Helvetica", 9)
        y = 270 * mm
        for row in rows[:24]:
            report_canvas.drawString(20 * mm, y, row.employee_name[:30])
            report_canvas.drawString(88 * mm, y, row.department[:18])
            report_canvas.drawRightString(190 * mm, y, f"INR {row.net_pay:,.2f}")
            y -= 6 * mm
        report_canvas.showPage()
        report_canvas.save()
        packet.seek(0)
        payload = packet
        media_type = "application/pdf"
        filename = f"payroll_report_{run.month:02d}_{run.year}.pdf"

    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/reports/payroll",
        f"Exported payroll report format={format} run={run.id}",
    )
    db.commit()

    return StreamingResponse(payload, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/readiness")
def branch_payroll_readiness(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    now = datetime.utcnow()
    mm = month or now.month
    yy = year or now.year
    start, end = _month_window(yy, mm)

    active_staff = db.query(StaffProfile).filter(StaffProfile.branch_id == branch_id, StaffProfile.is_active.is_(True)).all()
    staff_ids = [staff.id for staff in active_staff]
    total_staff = len(staff_ids)
    attendance_complete = 0
    if total_staff > 0:
        for staff_id in staff_ids:
            has_log = (
                db.query(StaffAttendanceLog.id)
                .filter(
                    StaffAttendanceLog.branch_id == branch_id,
                    StaffAttendanceLog.staff_profile_id == staff_id,
                    StaffAttendanceLog.attendance_date >= start,
                    StaffAttendanceLog.attendance_date < end,
                )
                .first()
                is not None
            )
            if has_log:
                attendance_complete += 1

    attendance_percent = (attendance_complete / total_staff * 100.0) if total_staff > 0 else 100.0
    leave_total = db.query(StaffLeaveRequest).filter(StaffLeaveRequest.branch_id == branch_id, StaffLeaveRequest.start_date >= start, StaffLeaveRequest.start_date < end).count()
    leave_pending = db.query(StaffLeaveRequest).filter(StaffLeaveRequest.branch_id == branch_id, StaffLeaveRequest.status == "pending", StaffLeaveRequest.start_date >= start, StaffLeaveRequest.start_date < end).count()
    leave_approval_percent = ((leave_total - leave_pending) / leave_total * 100.0) if leave_total > 0 else 100.0

    readiness_score = int(round((attendance_percent * 0.7) + (leave_approval_percent * 0.3)))
    reasons: list[str] = []
    if attendance_percent < 95:
        reasons.append("Attendance logs are incomplete for one or more employees.")
    if leave_pending > 0:
        reasons.append(f"{leave_pending} leave requests are still pending approval.")
    if not reasons:
        reasons.append("Payroll readiness checks passed.")

    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/readiness",
        f"Readiness check for {mm:02d}/{yy}",
    )
    db.commit()
    return {
        "readiness_score": readiness_score,
        "attendance_completeness_percent": round(attendance_percent, 2),
        "leave_approval_percent": round(leave_approval_percent, 2),
        "can_generate": readiness_score >= 70,
        "reasons": reasons,
    }


@router.get("/anomalies")
def branch_payroll_anomalies(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    now = datetime.utcnow()
    mm = month or now.month
    yy = year or now.year
    prev_mm = 12 if mm == 1 else mm - 1
    prev_yy = yy - 1 if mm == 1 else yy
    start, end = _month_window(yy, mm)
    prev_start, prev_end = _month_window(prev_yy, prev_mm)

    staff_rows = (
        db.query(StaffProfile, User)
        .join(User, User.id == StaffProfile.user_id)
        .filter(StaffProfile.branch_id == branch_id, StaffProfile.is_active.is_(True))
        .all()
    )

    def _overtime_hours_for_window(staff_profile_id: int, window_start: datetime, window_end: datetime) -> Decimal:
        logs = (
            db.query(StaffAttendanceLog)
            .filter(
                StaffAttendanceLog.branch_id == branch_id,
                StaffAttendanceLog.staff_profile_id == staff_profile_id,
                StaffAttendanceLog.attendance_date >= window_start,
                StaffAttendanceLog.attendance_date < window_end,
            )
            .all()
        )
        total = Decimal("0")
        for log in logs:
            if not log.clock_in_time or not log.clock_out_time:
                continue
            hours = Decimal(str((log.clock_out_time - log.clock_in_time).total_seconds() / 3600.0))
            if hours > Decimal("8"):
                total += (hours - Decimal("8"))
        return total

    anomalies: list[dict] = []
    for profile, user in staff_rows:
        prev_ot = _overtime_hours_for_window(profile.id, prev_start, prev_end)
        current_ot = _overtime_hours_for_window(profile.id, start, end)
        if prev_ot > 0:
            increase = float(((current_ot - prev_ot) / prev_ot) * Decimal("100"))
            if increase >= 300:
                anomalies.append(
                    {
                        "staff_profile_id": profile.id,
                        "employee_name": f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username,
                        "department": (profile.department or "Unassigned").strip() or "Unassigned",
                        "previous_overtime_hours": float(prev_ot),
                        "current_overtime_hours": float(current_ot),
                        "increase_percent": round(increase, 2),
                        "message": f"Warning: Overtime increased by {round(increase, 2)}% this month. Please review.",
                    }
                )
        elif current_ot >= Decimal("20"):
            anomalies.append(
                {
                    "staff_profile_id": profile.id,
                    "employee_name": f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or user.username,
                    "department": (profile.department or "Unassigned").strip() or "Unassigned",
                    "previous_overtime_hours": 0.0,
                    "current_overtime_hours": float(current_ot),
                    "increase_percent": 999.0,
                    "message": "Warning: Overtime baseline was zero and current month is unusually high. Please review.",
                }
            )

    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/anomalies",
        f"Viewed anomalies for {mm:02d}/{yy}",
    )
    db.commit()
    return {"anomalies": anomalies}


@router.get("/wellness")
def branch_payroll_wellness(
    payroll_run_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    run = _current_run_or_404(db, branch_id, payroll_run_id)
    rows = _compute_grid_rows(db, run, branch_id)

    total_salary = sum((row.net_pay for row in rows), 0.0)
    average_salary = (total_salary / len(rows)) if rows else 0.0
    distribution = {"<20k": 0, "20k-40k": 0, ">40k": 0}
    for row in rows:
        if row.net_pay < 20000:
            distribution["<20k"] += 1
        elif row.net_pay <= 40000:
            distribution["20k-40k"] += 1
        else:
            distribution[">40k"] += 1

    branch_staff_ids = [item[0] for item in db.query(StaffProfile.id).filter(StaffProfile.branch_id == branch_id).all()]
    high_advances = 0
    pending_advances = 0
    if branch_staff_ids:
        high_advances = db.query(AdvanceRequest).filter(AdvanceRequest.staff_id.in_(branch_staff_ids), AdvanceRequest.amount >= 50000).count()
        pending_advances = db.query(AdvanceRequest).filter(AdvanceRequest.staff_id.in_(branch_staff_ids), AdvanceRequest.status == AdvanceStatus.PENDING).count()

    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/wellness",
        f"Viewed wellness for run {run.id}",
    )
    db.commit()
    return {
        "average_salary": round(average_salary, 2),
        "salary_distribution": [{"bucket": key, "count": value} for key, value in distribution.items()],
        "financial_stress": {
            "high_advance_requests": high_advances,
            "pending_advance_requests": pending_advances,
        },
    }


@router.get("/security/two-factor")
def get_two_factor_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    _ensure_support_tables(db)
    row = db.execute(
        text("SELECT two_factor_enabled FROM payroll_security_settings WHERE branch_id = :branch_id"),
        {"branch_id": branch_id},
    ).first()
    enabled = bool(row[0]) if row else False
    _audit_log(
        db,
        branch_id,
        current_user.id,
        "viewing",
        "/api/branch/payroll/security/two-factor",
        f"Viewed 2FA toggle state ({enabled})",
    )
    db.commit()
    return {"two_factor_enabled": enabled}


@router.post("/security/two-factor")
def set_two_factor_state(
    payload: BranchPayrollTwoFactorPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch_id = _require_branch_director_scope(current_user)
    _ensure_support_tables(db)
    db.execute(
        text(
            """
            INSERT INTO payroll_security_settings (branch_id, two_factor_enabled, updated_by, updated_at)
            VALUES (:branch_id, :enabled, :updated_by, CURRENT_TIMESTAMP)
            ON CONFLICT(branch_id) DO UPDATE SET
                two_factor_enabled = excluded.two_factor_enabled,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "branch_id": branch_id,
            "enabled": 1 if payload.enabled else 0,
            "updated_by": current_user.id,
        },
    )
    _audit_log(
        db,
        branch_id,
        current_user.id,
        "editing",
        "/api/branch/payroll/security/two-factor",
        f"Set 2FA to {payload.enabled}",
    )
    db.commit()
    return {"two_factor_enabled": payload.enabled}
