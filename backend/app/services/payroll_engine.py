from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models import Branch, DailyEntry
from app.models.branch_bank_details import BranchBankDetails
from app.models.finance import BranchAccount
from app.models.hr import StaffAttendanceLog, StaffAttendanceStatus, StaffNotification, StaffProfile
from app.models.payroll.models import (
    AdvanceRequest,
    AdvanceStatus,
    PayrollRun,
    PayrollRunStatus,
    PayrollTransaction,
    ReimbursementClaim,
    ReimbursementStatus,
    StaffSalaryConfig,
    StaffTaxDeclaration,
)

PRESENT_STATUSES = {
    StaffAttendanceStatus.PRESENT,
    StaffAttendanceStatus.LATE,
    StaffAttendanceStatus.WORK_FROM_HOME,
}


def _to_decimal(value: object, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _month_window(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def _professional_tax(gross_monthly: Decimal) -> Decimal:
    if gross_monthly >= Decimal("25000"):
        return Decimal("200")
    if gross_monthly >= Decimal("15000"):
        return Decimal("150")
    if gross_monthly >= Decimal("10000"):
        return Decimal("75")
    return Decimal("0")


def _tds_monthly(gross_monthly: Decimal, declaration: Optional[StaffTaxDeclaration]) -> Decimal:
    annual_income = gross_monthly * Decimal("12")
    declared = Decimal("0")
    if declaration is not None:
        declared = _to_decimal(declaration.section_80c) + _to_decimal(declaration.medical) + _to_decimal(declaration.rent_allowance)
    taxable_annual = max(Decimal("0"), annual_income - declared)
    return (taxable_annual * Decimal("0.05")) / Decimal("12")


def _overtime_hours(staff_id: int, logs: list[StaffAttendanceLog]) -> Decimal:
    total = Decimal("0")
    for log in logs:
        if log.staff_profile_id != staff_id:
            continue
        if not log.clock_in_time or not log.clock_out_time:
            continue
        hours = Decimal(str((log.clock_out_time - log.clock_in_time).total_seconds() / 3600.0))
        overtime = hours - Decimal("8")
        if overtime > 0:
            total += overtime
    return total.quantize(Decimal("0.01"))


def _attendance_summary(staff_id: int, logs: list[StaffAttendanceLog], year: int, month: int) -> Dict[str, Decimal]:
    days_in_month = Decimal(str(monthrange(year, month)[1]))
    present_count = Decimal("0")
    approved_leave_count = Decimal("0")

    for log in logs:
        if log.staff_profile_id != staff_id:
            continue
        status = log.status
        if status in PRESENT_STATUSES:
            present_count += Decimal("1")
        elif status == StaffAttendanceStatus.APPROVED_LEAVE:
            approved_leave_count += Decimal("1")

    lop_days = max(Decimal("0"), days_in_month - present_count - approved_leave_count)
    return {
        "days_in_month": days_in_month,
        "lop_days": lop_days,
    }


def _monthly_incentive(db: Session, staff: StaffProfile, start: datetime, end: datetime) -> Decimal:
    blood_draw_like_count = (
        db.query(DailyEntry)
        .filter(
            DailyEntry.created_by == staff.user_id,
            DailyEntry.entry_date >= start,
            DailyEntry.entry_date < end,
        )
        .count()
    )
    return Decimal(str(blood_draw_like_count)) * Decimal("20")


def _reimbursement_total(db: Session, staff_id: int) -> Decimal:
    rows = (
        db.query(ReimbursementClaim)
        .filter(
            ReimbursementClaim.staff_id == staff_id,
            ReimbursementClaim.status.in_([ReimbursementStatus.APPROVED, ReimbursementStatus.PAID]),
        )
        .all()
    )
    return sum((_to_decimal(r.amount) for r in rows), Decimal("0"))


def _advance_installment(db: Session, staff_id: int) -> Decimal:
    requests = (
        db.query(AdvanceRequest)
        .filter(
            AdvanceRequest.staff_id == staff_id,
            AdvanceRequest.status.in_([AdvanceStatus.APPROVED, AdvanceStatus.DISBURSED]),
            AdvanceRequest.repaid_months < AdvanceRequest.tenure_months,
        )
        .all()
    )

    installment_total = Decimal("0")
    for req in requests:
        tenure = max(int(req.tenure_months or 1), 1)
        installment = _to_decimal(req.amount) / Decimal(str(tenure))
        installment_total += installment
        req.repaid_months = int(req.repaid_months or 0) + 1
    return installment_total


def _branch_balance(db: Session, branch_id: int) -> Decimal:
    bank = db.query(BranchBankDetails).filter(BranchBankDetails.branch_id == branch_id).first()
    if bank and hasattr(bank, "current_balance"):
        return _to_decimal(getattr(bank, "current_balance", 0))
    account = db.query(BranchAccount).filter(BranchAccount.branch_id == branch_id).order_by(BranchAccount.id.asc()).first()
    return _to_decimal(account.current_balance if account else 0)


def generate_payroll_run(
    db: Session,
    branch_id: int,
    month: int,
    year: int,
    generated_by_user_id: Optional[int] = None,
) -> PayrollRun:
    start, end = _month_window(year, month)

    run = (
        db.query(PayrollRun)
        .filter(PayrollRun.branch_id == branch_id, PayrollRun.month == month, PayrollRun.year == year)
        .first()
    )
    if run and run.status == PayrollRunStatus.LOCKED:
        raise ValueError("Payroll is locked and cannot be regenerated")

    if not run:
        run = PayrollRun(branch_id=branch_id, month=month, year=year, status=PayrollRunStatus.DRAFT)
        db.add(run)
        db.flush()

    existing_locked = (
        db.query(PayrollTransaction)
        .filter(PayrollTransaction.payroll_run_id == run.id)
        .count()
    )
    if existing_locked:
        db.query(PayrollTransaction).filter(PayrollTransaction.payroll_run_id == run.id).delete(synchronize_session=False)

    configs = (
        db.query(StaffSalaryConfig)
        .join(StaffProfile, StaffProfile.id == StaffSalaryConfig.staff_id)
        .filter(StaffSalaryConfig.is_active.is_(True), StaffProfile.branch_id == branch_id)
        .all()
    )

    logs = (
        db.query(StaffAttendanceLog)
        .filter(
            StaffAttendanceLog.branch_id == branch_id,
            StaffAttendanceLog.attendance_date >= start,
            StaffAttendanceLog.attendance_date < end,
        )
        .all()
    )

    total_gross = Decimal("0")
    total_deductions = Decimal("0")
    total_net = Decimal("0")

    for config in configs:
        staff = config.staff_profile
        grade = config.grade
        if staff is None or grade is None:
            continue

        base_salary = _to_decimal(grade.base_salary)
        summary = _attendance_summary(staff.id, logs, year, month)
        lop_days = summary["lop_days"]
        days_in_month = summary["days_in_month"]
        lop_amount = (base_salary / days_in_month) * lop_days if days_in_month > 0 else Decimal("0")

        overtime_hours = _overtime_hours(staff.id, logs)
        hourly = base_salary / Decimal("240") if base_salary > 0 else Decimal("0")
        ot_amount = overtime_hours * hourly * Decimal("1.5")

        incentive_amount = _monthly_incentive(db, staff, start, end)
        reimbursement_amount = _reimbursement_total(db, staff.id)

        pf = base_salary * Decimal("0.12")
        declaration = (
            db.query(StaffTaxDeclaration)
            .filter(StaffTaxDeclaration.staff_id == staff.id, StaffTaxDeclaration.declaration_year == year)
            .first()
        )

        gross = base_salary + ot_amount + incentive_amount + reimbursement_amount
        tds = _tds_monthly(gross, declaration)
        pt = _professional_tax(gross)
        advance_deduction = _advance_installment(db, staff.id)
        deductions = lop_amount + pf + tds + pt + advance_deduction
        net = max(Decimal("0"), gross - deductions)

        tx = PayrollTransaction(
            payroll_run_id=run.id,
            staff_id=staff.id,
            base_salary=base_salary.quantize(Decimal("0.01")),
            overtime_hours=overtime_hours,
            lop_days=lop_days,
            incentive_amount=incentive_amount.quantize(Decimal("0.01")),
            reimbursement_amount=reimbursement_amount.quantize(Decimal("0.01")),
            total_deductions=deductions.quantize(Decimal("0.01")),
            net_pay=net.quantize(Decimal("0.01")),
        )
        db.add(tx)

        total_gross += gross
        total_deductions += deductions
        total_net += net

    run.total_gross_pay = total_gross.quantize(Decimal("0.01"))
    run.total_deductions = total_deductions.quantize(Decimal("0.01"))
    run.total_net_pay = total_net.quantize(Decimal("0.01"))
    run.status = PayrollRunStatus.READY
    if generated_by_user_id:
        run.approved_by = generated_by_user_id

    db.flush()
    return run


def check_funds_for_run(db: Session, run: PayrollRun) -> dict:
    available = _branch_balance(db, run.branch_id)
    required = _to_decimal(run.total_net_pay)
    return {
        "hasSufficientFunds": available >= required,
        "required": float(required),
        "available": float(available),
    }


def notify_staff_for_approved_payroll(db: Session, run: PayrollRun) -> None:
    tx_rows = db.query(PayrollTransaction).filter(PayrollTransaction.payroll_run_id == run.id).all()
    for tx in tx_rows:
        staff = db.query(StaffProfile).filter(StaffProfile.id == tx.staff_id).first()
        if not staff:
            continue
        db.add(
            StaffNotification(
                staff_profile_id=staff.id,
                branch_id=staff.branch_id,
                message=f"Salary for {run.month:02d}/{run.year} approved. Net pay: INR {tx.net_pay}.",
                link="/staff/profile",
            )
        )
