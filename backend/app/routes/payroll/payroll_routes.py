from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, DailyEntry, User
from app.models.branch_bank_details import BranchBankDetails
from app.models.hr import StaffProfile
from app.models.finance import FinanceTransaction
from app.models.payroll.models import (
    AdvanceRequest,
    AdvanceStatus,
    EarningHead,
    PayrollDispute,
    PayrollLock,
    PayrollRun,
    PayrollRunStatus,
    PayrollTransaction,
    ReimbursementClaim,
    ReimbursementStatus,
    SalaryGrade,
    StaffSalaryConfig,
    StaffTaxDeclaration,
)
from app.services.payroll_engine import check_funds_for_run, generate_payroll_run, notify_staff_for_approved_payroll
from app.utils.auth_system import get_current_user

router = APIRouter()


class SalaryConfigPayload(BaseModel):
    grade_id: int
    bank_account_number: Optional[str] = None
    ifsc: Optional[str] = None
    upi_id: Optional[str] = None
    date_of_joining: Optional[datetime] = None
    is_active: bool = True


class PayrollGeneratePayload(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2200)
    branch_id: Optional[int] = None


class AdvanceRequestPayload(BaseModel):
    amount: float = Field(..., gt=0)
    reason: Optional[str] = None
    tenure_months: int = Field(..., ge=1, le=60)


class AdvanceApprovalPayload(BaseModel):
    status: AdvanceStatus


class ApprovePayrollPayload(BaseModel):
    force_lock: bool = True


class SimulatePayload(BaseModel):
    percentage: float = Field(..., ge=-100, le=300)
    branch_id: Optional[int] = None


class PayrollDisputePayload(BaseModel):
    payroll_transaction_id: int
    reason: str = Field(..., min_length=3)


class TaxDeclarationPayload(BaseModel):
    declaration_year: int
    section_80c: float = 0
    medical: float = 0
    rent_allowance: float = 0


def _role(user: User) -> str:
    return (user.role or "").strip().lower()


def _is_staff_role(role: str) -> bool:
    """Check if role is a staff-type role (not admin/director/doctor)"""
    role_normalized = (role or "").strip().lower()
    non_staff_roles = {'super_admin', 'branch_admin', 'branch_director', 'admin', 'doctor'}
    return role_normalized not in non_staff_roles


def _require_director_or_admin(user: User) -> None:
    if _role(user) not in {"branch_director", "super_admin", "branch_admin", "admin"}:
        raise HTTPException(status_code=403, detail="Director/Admin privileges required")


def _require_staff(user: User) -> None:
    if not _is_staff_role(user.role):
        raise HTTPException(status_code=403, detail="Only staff users can access this endpoint")


def _effective_branch_id(user: User, payload_branch_id: Optional[int]) -> int:
    if payload_branch_id:
        return payload_branch_id
    if user.branch_id:
        return int(user.branch_id)
    raise HTTPException(status_code=400, detail="branch_id is required")


@router.get("/payroll/setup/earning-heads")
def list_earning_heads(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_director_or_admin(current_user)
    rows = db.query(EarningHead).order_by(EarningHead.id.asc()).all()
    return {"items": [{"id": r.id, "name": r.name, "is_fixed": r.is_fixed, "taxable": r.taxable} for r in rows]}


@router.post("/payroll/setup/seed-defaults")
def seed_payroll_defaults(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_director_or_admin(current_user)
    defaults = [
        ("Basic", True, True),
        ("DA", True, True),
        ("HRA", True, False),
        ("Conveyance", True, False),
        ("Shift Allowance", False, True),
    ]
    for name, is_fixed, taxable in defaults:
        exists = db.query(EarningHead).filter(EarningHead.name == name).first()
        if not exists:
            db.add(EarningHead(name=name, is_fixed=is_fixed, taxable=taxable))
    db.commit()
    return {"message": "Default earning heads ensured"}


@router.get("/staff/{staff_id}/salary-config")
def get_salary_config(staff_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if _role(current_user) == "staff":
        profile = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
        if not profile or profile.id != staff_id:
            raise HTTPException(status_code=403, detail="Not allowed")
    else:
        _require_director_or_admin(current_user)

    config = db.query(StaffSalaryConfig).filter(StaffSalaryConfig.staff_id == staff_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")

    run = (
        db.query(PayrollRun)
        .join(PayrollTransaction, PayrollTransaction.payroll_run_id == PayrollRun.id)
        .filter(PayrollTransaction.staff_id == staff_id, PayrollRun.status == PayrollRunStatus.LOCKED)
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
        .first()
    )

    return {
        "id": config.id,
        "staff_id": config.staff_id,
        "grade_id": config.grade_id,
        "bank_account_number": config.bank_account_number,
        "ifsc": config.ifsc,
        "upi_id": config.upi_id,
        "date_of_joining": config.date_of_joining,
        "is_active": config.is_active,
        "is_editable": run is None,
    }


@router.put("/staff/{staff_id}/salary-config")
def upsert_salary_config(
    staff_id: int,
    payload: SalaryConfigPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_director_or_admin(current_user)

    locked_exists = (
        db.query(PayrollRun)
        .join(PayrollTransaction, PayrollTransaction.payroll_run_id == PayrollRun.id)
        .filter(PayrollTransaction.staff_id == staff_id, PayrollRun.status == PayrollRunStatus.LOCKED)
        .first()
    )
    if locked_exists:
        raise HTTPException(status_code=409, detail="Payroll is locked for this staff. Unlock flow required before edits")

    grade = db.query(SalaryGrade).filter(SalaryGrade.id == payload.grade_id).first()
    if not grade:
        raise HTTPException(status_code=404, detail="Salary grade not found")

    config = db.query(StaffSalaryConfig).filter(StaffSalaryConfig.staff_id == staff_id).first()
    if not config:
        config = StaffSalaryConfig(staff_id=staff_id)
        db.add(config)

    config.grade_id = payload.grade_id
    config.bank_account_number = payload.bank_account_number
    config.ifsc = payload.ifsc
    config.upi_id = payload.upi_id
    config.date_of_joining = payload.date_of_joining.date() if payload.date_of_joining else None
    config.is_active = payload.is_active
    db.commit()
    db.refresh(config)
    return {"message": "Salary config saved", "id": config.id}


@router.post("/payroll/generate")
def generate_payroll(
    payload: PayrollGeneratePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_director_or_admin(current_user)
    branch_id = _effective_branch_id(current_user, payload.branch_id)

    run = generate_payroll_run(
        db=db,
        branch_id=branch_id,
        month=payload.month,
        year=payload.year,
        generated_by_user_id=current_user.id,
    )
    db.commit()
    db.refresh(run)
    return {
        "message": "Payroll generated",
        "payroll_run": {
            "id": run.id,
            "branch_id": run.branch_id,
            "month": run.month,
            "year": run.year,
            "status": run.status.value,
            "total_gross_pay": float(run.total_gross_pay or 0),
            "total_deductions": float(run.total_deductions or 0),
            "total_net_pay": float(run.total_net_pay or 0),
        },
    }


@router.get("/payroll/runs")
def list_payroll_runs(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_director_or_admin(current_user)
    eff_branch_id = _effective_branch_id(current_user, branch_id)
    rows = (
        db.query(PayrollRun)
        .filter(PayrollRun.branch_id == eff_branch_id)
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "month": r.month,
                "year": r.year,
                "status": r.status.value,
                "total_gross_pay": float(r.total_gross_pay or 0),
                "total_deductions": float(r.total_deductions or 0),
                "total_net_pay": float(r.total_net_pay or 0),
                "approved_at": r.approved_at,
            }
            for r in rows
        ]
    }


@router.get("/payroll/dashboard")
def payroll_dashboard(
    branch_id: Optional[int] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_director_or_admin(current_user)
    eff_branch_id = _effective_branch_id(current_user, branch_id)
    now = datetime.utcnow()
    mm = month or now.month
    yy = year or now.year
    prev_mm = 12 if mm == 1 else mm - 1
    prev_yy = yy - 1 if mm == 1 else yy

    current_run = db.query(PayrollRun).filter(PayrollRun.branch_id == eff_branch_id, PayrollRun.month == mm, PayrollRun.year == yy).first()
    prev_run = db.query(PayrollRun).filter(PayrollRun.branch_id == eff_branch_id, PayrollRun.month == prev_mm, PayrollRun.year == prev_yy).first()

    current_total = float(current_run.total_net_pay) if current_run else 0.0
    prev_total = float(prev_run.total_net_pay) if prev_run else 0.0
    variance_pct = ((current_total - prev_total) / prev_total * 100.0) if prev_total > 0 else 0.0

    dept_rows = (
        db.query(StaffProfile.department, func.sum(PayrollTransaction.net_pay))
        .join(PayrollTransaction, PayrollTransaction.staff_id == StaffProfile.id)
        .join(PayrollRun, PayrollRun.id == PayrollTransaction.payroll_run_id)
        .filter(PayrollRun.branch_id == eff_branch_id, PayrollRun.month == mm, PayrollRun.year == yy)
        .group_by(StaffProfile.department)
        .all()
    )

    month_start = datetime(yy, mm, 1)
    month_end = datetime(yy + 1, 1, 1) if mm == 12 else datetime(yy, mm + 1, 1)
    revenue = (
        db.query(func.coalesce(func.sum(DailyEntry.total_amount), 0))
        .filter(DailyEntry.branch_id == eff_branch_id, DailyEntry.entry_date >= month_start, DailyEntry.entry_date < month_end)
        .scalar()
    )
    revenue_value = float(revenue or 0)
    ratio = (current_total / revenue_value) if revenue_value > 0 else 0

    return {
        "total_branch_payroll_this_month": current_total,
        "total_branch_payroll_last_month": prev_total,
        "variance_percent": variance_pct,
        "department_wise_burn": [
            {"department": dept or "Unassigned", "amount": float(amount or 0)} for dept, amount in dept_rows
        ],
        "cost_to_income_ratio": ratio,
    }


@router.get("/payroll/{payroll_id}/check-funds")
def check_funds(payroll_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_director_or_admin(current_user)
    run = db.query(PayrollRun).filter(PayrollRun.id == payroll_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    return check_funds_for_run(db, run)


@router.post("/payroll/{payroll_id}/approve")
def approve_payroll(
    payroll_id: int,
    payload: ApprovePayrollPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_director_or_admin(current_user)
    run = db.query(PayrollRun).filter(PayrollRun.id == payroll_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    if run.status == PayrollRunStatus.LOCKED:
        raise HTTPException(status_code=409, detail="Payroll already locked")

    funds = check_funds_for_run(db, run)
    if not funds["hasSufficientFunds"]:
        raise HTTPException(status_code=400, detail=f"Insufficient funds. Required {funds['required']} available {funds['available']}")

    run.approved_by = current_user.id
    run.approved_at = datetime.utcnow()
    run.status = PayrollRunStatus.APPROVED if not payload.force_lock else PayrollRunStatus.LOCKED
    db.add(
        PayrollLock(
            payroll_run_id=run.id,
            unlocked_by=None,
            unlock_reason="Auto lock on approval",
            unlocked_at=None,
        )
    )

    notify_staff_for_approved_payroll(db, run)
    db.commit()
    return {"message": "Payroll approved", "status": run.status.value, "funds": funds}


@router.post("/staff/advance-request")
def create_advance_request(
    payload: AdvanceRequestPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff profile not found")

    req = AdvanceRequest(
        staff_id=profile.id,
        amount=payload.amount,
        reason=payload.reason,
        tenure_months=payload.tenure_months,
        status=AdvanceStatus.PENDING,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"message": "Advance request submitted", "id": req.id}


@router.put("/advance/{advance_id}/approve")
def approve_advance_request(
    advance_id: int,
    payload: AdvanceApprovalPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_director_or_admin(current_user)
    req = db.query(AdvanceRequest).filter(AdvanceRequest.id == advance_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Advance request not found")
    req.status = payload.status
    req.approved_by = current_user.id
    db.commit()
    return {"message": "Advance request updated", "status": req.status.value}


@router.post("/staff/reimbursement-claim")
def create_reimbursement_claim(
    category: str = Form(...),
    amount: float = Form(...),
    file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff profile not found")

    file_url = None
    if file is not None:
        file_url = f"staff/reimbursements/{profile.id}_{int(datetime.utcnow().timestamp())}_{file.filename or 'bill'}"

    claim = ReimbursementClaim(
        staff_id=profile.id,
        category=category,
        amount=amount,
        file_url=file_url,
        status=ReimbursementStatus.PENDING,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return {"message": "Reimbursement claim submitted", "id": claim.id}


@router.put("/reimbursement/{claim_id}/approve")
def approve_reimbursement(
    claim_id: int,
    status: ReimbursementStatus = ReimbursementStatus.APPROVED,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_director_or_admin(current_user)
    claim = db.query(ReimbursementClaim).filter(ReimbursementClaim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    claim.status = status
    db.commit()
    return {"message": "Reimbursement updated", "status": claim.status.value}


@router.put("/staff/{staff_id}/tax-declaration")
def upsert_tax_declaration(
    staff_id: int,
    payload: TaxDeclarationPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if _role(current_user) == "staff":
        profile = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
        if not profile or profile.id != staff_id:
            raise HTTPException(status_code=403, detail="Not allowed")
    else:
        _require_director_or_admin(current_user)

    row = db.query(StaffTaxDeclaration).filter(StaffTaxDeclaration.staff_id == staff_id).first()
    if not row:
        row = StaffTaxDeclaration(staff_id=staff_id)
        db.add(row)

    row.declaration_year = payload.declaration_year
    row.section_80c = payload.section_80c
    row.medical = payload.medical
    row.rent_allowance = payload.rent_allowance
    db.commit()
    return {"message": "Tax declaration saved"}


@router.post("/payroll/disputes")
def create_payroll_dispute(
    payload: PayrollDisputePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff profile not found")

    tx = db.query(PayrollTransaction).filter(PayrollTransaction.id == payload.payroll_transaction_id).first()
    if not tx or tx.staff_id != profile.id:
        raise HTTPException(status_code=404, detail="Payroll transaction not found")

    dispute = PayrollDispute(
        payroll_transaction_id=payload.payroll_transaction_id,
        staff_id=profile.id,
        reason=payload.reason,
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return {"message": "Payroll dispute raised", "id": dispute.id}


@router.post("/payroll/simulate")
def simulate_hike(
    payload: SimulatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_director_or_admin(current_user)
    branch_id = _effective_branch_id(current_user, payload.branch_id)

    run = (
        db.query(PayrollRun)
        .filter(PayrollRun.branch_id == branch_id)
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="No payroll run found for simulation")

    current_cost = float(run.total_net_pay or 0)
    projected = current_cost * (1 + payload.percentage / 100.0)
    return {
        "current_cost": current_cost,
        "percentage": payload.percentage,
        "projected_cost": projected,
        "delta": projected - current_cost,
    }


@router.get("/payroll/{payroll_id}/payslip/{staff_id}")
def generate_payslip_pdf(
    payroll_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if _role(current_user) == "staff":
        profile = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
        if not profile or profile.id != staff_id:
            raise HTTPException(status_code=403, detail="Not allowed")
    else:
        _require_director_or_admin(current_user)

    run = db.query(PayrollRun).filter(PayrollRun.id == payroll_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")

    tx = (
        db.query(PayrollTransaction)
        .filter(PayrollTransaction.payroll_run_id == payroll_id, PayrollTransaction.staff_id == staff_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Payslip transaction not found")

    staff = db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff profile not found")

    user = db.query(User).filter(User.id == staff.user_id).first()
    branch = db.query(Branch).filter(Branch.id == run.branch_id).first()

    # Policy: payslip password must be staff phone number only.
    # Normalize to digits to avoid mismatches from +91/spaces/dashes.
    raw_phone = (getattr(user, "phone", None) if user else None) or (getattr(staff, "mobile", None) if staff else None)
    normalized_phone = re.sub(r"\D", "", str(raw_phone or ""))
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="Registered phone number is required to open payslip PDF")
    password = normalized_phone

    packet = io.BytesIO()
    encrypt = StandardEncryption(userPassword=password, ownerPassword=password, canPrint=1, canModify=0, canCopy=0)
    c = canvas.Canvas(packet, pagesize=A4, encrypt=encrypt)

    y = 280 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, "Salary Payslip")
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Branch: {(branch.name if branch else 'N/A')}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Staff: {(user.first_name + ' ' + user.last_name) if user else staff.staff_id}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Period: {run.month:02d}/{run.year}")
    y -= 10 * mm

    c.drawString(20 * mm, y, f"Base Salary: INR {tx.base_salary}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Overtime Hours: {tx.overtime_hours}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Incentive: INR {tx.incentive_amount}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Reimbursement: INR {tx.reimbursement_amount}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Deductions: INR {tx.total_deductions}")
    y -= 6 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, f"Net Pay: INR {tx.net_pay}")

    qr_data = f"PAYSLIP|RUN:{run.id}|STAFF:{staff.id}|MONTH:{run.month}|YEAR:{run.year}|NET:{tx.net_pay}"
    qr_code = qr.QrCodeWidget(qr_data)
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    d = 30 * mm
    scale = min(d / width, d / height)

    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF

    drawing = Drawing(d, d, transform=[scale, 0, 0, scale, 0, 0])
    drawing.add(qr_code)
    renderPDF.draw(drawing, c, 160 * mm, 235 * mm)

    c.setFont("Helvetica", 8)
    c.drawString(160 * mm, 232 * mm, "Scan to verify")

    c.showPage()
    c.save()
    packet.seek(0)

    return StreamingResponse(
        packet,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=payslip_{run.month:02d}_{run.year}_staff_{staff_id}.pdf",
            "X-Payslip-Password-Hint": "Use registered phone number digits only",
        },
    )


@router.get("/payroll/my/payslips")
def list_my_payslips(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_staff(current_user)
    profile = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff profile not found")

    rows = (
        db.query(PayrollTransaction, PayrollRun)
        .join(PayrollRun, PayrollRun.id == PayrollTransaction.payroll_run_id)
        .filter(PayrollTransaction.staff_id == profile.id)
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
        .all()
    )

    return {
        "items": [
            {
                "payroll_id": run.id,
                "month": run.month,
                "year": run.year,
                "status": run.status.value,
                "net_pay": float(tx.net_pay or 0),
                "download_url": f"/api/payroll/{run.id}/payslip/{profile.id}",
            }
            for tx, run in rows
        ]
    }


@router.get("/payroll/compliance/pf-esi-file")
def generate_pf_esi_file(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_director_or_admin(current_user)

    run = db.query(PayrollRun).filter(PayrollRun.id == payroll_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")

    tx_rows = db.query(PayrollTransaction).filter(PayrollTransaction.payroll_run_id == payroll_id).all()
    lines = ["staff_id,month,year,basic,pf_12pct"]
    for tx in tx_rows:
        pf = float(tx.base_salary or 0) * 0.12
        lines.append(f"{tx.staff_id},{run.month},{run.year},{float(tx.base_salary or 0):.2f},{pf:.2f}")

    output = "\n".join(lines)
    return StreamingResponse(
        io.BytesIO(output.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pf_esi_{payroll_id}.csv"},
    )
