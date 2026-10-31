from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, User
from app.models.ceo import CeoAuditLog
from app.models.hr import StaffAttendanceLog, StaffProfile, StaffRequest, StaffTask
from app.models.payroll.models import AdvanceRequest, PayrollRun, PayrollTransaction
from app.services.executive_metrics import ResolvedScope, envelope
from app.services.file_storage import save_upload
from app.services.outlet_service import write_audit
from app.services.staff_service import get_staff_profile, serialize_staff, sync_staff_profile, update_staff
from app.utils.guards import StaffContext, staff_context


router = APIRouter(prefix="/staff", tags=["Staff Self Service"])


class StaffSelfUpdatePayload(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    alternate_phone: str | None = Field(default=None, max_length=20)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=32)
    blood_group: str | None = Field(default=None, max_length=10)
    marital_status: str | None = Field(default=None, max_length=32)
    current_address: str | None = None
    permanent_address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    emergency_contact_relation: str | None = Field(default=None, max_length=100)
    bank_account_name: str | None = Field(default=None, max_length=255)
    bank_account_number: str | None = None
    ifsc_code: str | None = None
    bank_name: str | None = Field(default=None, max_length=255)
    branch_name: str | None = Field(default=None, max_length=255)
    upi_id: str | None = None
    qualifications: list[Any] | None = None
    certifications: list[Any] | None = None
    experience_years: float | None = Field(default=None, ge=0)
    previous_employer: str | None = Field(default=None, max_length=255)
    skills: list[Any] | None = None
    shift_preference: str | None = Field(default=None, max_length=100)
    weekly_off_day: str | None = Field(default=None, max_length=20)
    staff_role: str | None = None
    salary_type: str | None = None
    monthly_salary: float | None = None
    daily_wage: float | None = None
    hourly_rate: float | None = None
    employment_type: str | None = None
    company_id: int | None = None
    outlet_id: int | None = None
    employee_code: str | None = None
    manager_id: int | None = None


class StaffRequestCreatePayload(BaseModel):
    type: str = Field(..., min_length=2, max_length=40)
    reason: str = Field(..., min_length=3, max_length=2000)


def _scope(context: StaffContext) -> ResolvedScope:
    return ResolvedScope(
        level="branch",
        company_ids=(context.company_id,),
        company_id=context.company_id,
        branch_id=context.outlet_id,
    )


def _envelope(
    data: Any,
    context: StaffContext,
    *,
    source_status: str = "complete",
    sources: list[str] | None = None,
    missing_sources: list[str] | None = None,
) -> dict[str, Any]:
    return envelope(
        data,
        _scope(context),
        source_status=source_status,
        sources=sources or ["users"],
        missing_sources=missing_sources or [],
        ttl_seconds=60,
    )


def _own_profile_or_404(db: Session, user: User) -> StaffProfile:
    profile = get_staff_profile(db, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Staff profile not found")
    return profile


def _outlet_payload(outlet: Branch) -> dict[str, Any]:
    return {
        "id": outlet.id,
        "name": outlet.name,
        "code": outlet.code,
        "city": outlet.city,
        "state": outlet.state,
        "status": outlet.status,
        "outlet_type": outlet.outlet_type,
        "address_line_1": outlet.address_line_1,
        "address_line_2": outlet.address_line_2,
        "outlet_phone": outlet.outlet_phone,
        "outlet_email": outlet.outlet_email,
        "opening_time": outlet.opening_time,
        "closing_time": outlet.closing_time,
        "logo_url": outlet.logo_url,
    }


@router.get("/me")
def get_me(
    context: StaffContext = Depends(staff_context),
    db: Session = Depends(get_db),
):
    _own_profile_or_404(db, context.user)
    return _envelope({"staff": serialize_staff(context.user, masked=False, include_private_email=True)}, context, sources=["users"])


@router.put("/me")
def update_me(
    payload: StaffSelfUpdatePayload,
    request: Request,
    context: StaffContext = Depends(staff_context),
    db: Session = Depends(get_db),
):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one profile field must be provided")
    updated = update_staff(db, context.user, request, context.user, changes, self_service=True)
    return _envelope({"staff": serialize_staff(updated, masked=False, include_private_email=True)}, context, sources=["users", "staff_profiles", "ceo_audit_logs"])


@router.post("/me/photo")
async def upload_my_photo(
    request: Request,
    file: UploadFile = File(...),
    context: StaffContext = Depends(staff_context),
    db: Session = Depends(get_db),
):
    _own_profile_or_404(db, context.user)
    asset = await save_upload(file, "staff-photos", context.user.id)
    context.user.profile_photo_url = asset["url"]
    sync_staff_profile(db, context.user, context.user.id)
    write_audit(
        db,
        context.user,
        request,
        "staff.updated",
        resource_type="user",
        resource_id=context.user.id,
        company_id=context.company_id,
        outlet_id=context.outlet_id,
        changes={"fields": ["profile_photo_url"]},
        extra={"self_service": True, "asset": {"url": asset["url"], "filename": asset["filename"]}},
    )
    db.commit()
    return _envelope({"staff": serialize_staff(context.user, masked=False, include_private_email=True), "asset": asset}, context, sources=["users", "ceo_audit_logs"])


@router.get("/me/outlet")
def get_my_outlet(
    context: StaffContext = Depends(staff_context),
):
    return _envelope({"outlet": _outlet_payload(context.outlet)}, context, sources=["branches"])


@router.get("/me/dashboard")
def get_my_dashboard(
    context: StaffContext = Depends(staff_context),
    db: Session = Depends(get_db),
):
    profile = _own_profile_or_404(db, context.user)
    today_start = datetime.combine(date.today(), datetime.min.time())
    tomorrow = today_start + timedelta(days=1)
    month_start = date.today().replace(day=1)
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    month_end_dt = datetime.combine((month_start + timedelta(days=32)).replace(day=1), datetime.min.time())

    today_log = (
        db.query(StaffAttendanceLog)
        .filter(
            StaffAttendanceLog.StaffEmployee_profile_id == profile.id,
            StaffAttendanceLog.attendance_date >= today_start,
            StaffAttendanceLog.attendance_date < tomorrow,
        )
        .order_by(StaffAttendanceLog.attendance_date.desc(), StaffAttendanceLog.id.desc())
        .first()
    )
    my_tasks_today = (
        db.query(StaffTask)
        .filter(
            StaffTask.branch_id == context.outlet_id,
            or_(StaffTask.assigned_to == context.user.id, StaffTask.StaffEmployee_profile_id == profile.id),
            or_(
                StaffTask.deadline.is_(None),
                func.date(StaffTask.deadline) == date.today().isoformat(),
                func.date(StaffTask.due_date) == date.today().isoformat(),
            ),
        )
        .order_by(StaffTask.deadline.asc().nullslast(), StaffTask.due_date.asc().nullslast(), StaffTask.id.desc())
        .all()
    )
    attendance_rows = (
        db.query(StaffAttendanceLog)
        .filter(
            StaffAttendanceLog.StaffEmployee_profile_id == profile.id,
            StaffAttendanceLog.attendance_date >= month_start_dt,
            StaffAttendanceLog.attendance_date < month_end_dt,
        )
        .all()
    )
    present_rows = sum(1 for row in attendance_rows if str(getattr(row.status, "value", row.status) or "").lower() in {"present", "late"})
    attendance_pct = round((present_rows / len(attendance_rows)) * 100, 2) if attendance_rows else None
    pending_requests = (
        db.query(func.count(StaffRequest.id))
        .filter(StaffRequest.staff_id == context.user.id, StaffRequest.status == "pending")
        .scalar()
        or 0
    )
    payslip_txn = (
        db.query(PayrollTransaction, PayrollRun)
        .join(PayrollRun, PayrollRun.id == PayrollTransaction.payroll_run_id)
        .filter(PayrollTransaction.staff_id == profile.id, PayrollRun.branch_id == context.outlet_id)
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc(), PayrollRun.id.desc())
        .first()
    )
    source_status = "complete"
    missing_sources: list[str] = []
    last_payslip_date = None
    if payslip_txn:
        _, payroll_run = payslip_txn
        last_payslip_date = payroll_run.created_at.isoformat() if payroll_run.created_at else None
    else:
        source_status = "partial"
        missing_sources.append("payroll_transactions")
    return _envelope(
        {
            "dashboard": {
                "today_shift": {
                    "attendance_date": today_log.attendance_date.isoformat() if today_log and today_log.attendance_date else None,
                    "clock_in_time": today_log.clock_in_time.isoformat() if today_log and today_log.clock_in_time else None,
                    "clock_out_time": today_log.clock_out_time.isoformat() if today_log and today_log.clock_out_time else None,
                    "status": str(getattr(today_log.status, "value", today_log.status) or "").lower() if today_log else None,
                },
                "my_tasks_today": [
                    {
                        "id": row.id,
                        "title": row.title or row.task_name,
                        "status": row.status,
                        "priority": row.priority,
                        "deadline": row.deadline.isoformat() if row.deadline else None,
                        "due_date": row.due_date.isoformat() if row.due_date else None,
                    }
                    for row in my_tasks_today
                ],
                "attendance_month_percentage": attendance_pct,
                "pending_requests_count": int(pending_requests),
                "last_payslip_date": last_payslip_date,
                "rating": None,
            }
        },
        context,
        source_status=source_status,
        sources=["staff_attendance_logs", "staff_tasks", "staff_requests", "payroll_transactions"],
        missing_sources=missing_sources,
    )


@router.get("/me/attendance")
def get_my_attendance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: StaffContext = Depends(staff_context),
    db: Session = Depends(get_db),
):
    profile = _own_profile_or_404(db, context.user)
    query = (
        db.query(StaffAttendanceLog)
        .filter(StaffAttendanceLog.StaffEmployee_profile_id == profile.id, StaffAttendanceLog.branch_id == context.outlet_id)
    )
    total = query.count()
    rows = query.order_by(StaffAttendanceLog.attendance_date.desc(), StaffAttendanceLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return _envelope(
        {
            "items": [
                {
                    "id": row.id,
                    "attendance_date": row.attendance_date.isoformat() if row.attendance_date else None,
                    "clock_in_time": row.clock_in_time.isoformat() if row.clock_in_time else None,
                    "clock_out_time": row.clock_out_time.isoformat() if row.clock_out_time else None,
                    "status": str(getattr(row.status, "value", row.status) or "").lower(),
                    "task": row.task,
                }
                for row in rows
            ],
            "pagination": {"page": page, "page_size": page_size, "total": total},
        },
        context,
        source_status="empty" if not rows else "complete",
        sources=["staff_attendance_logs"],
    )


@router.get("/me/tasks")
def get_my_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: StaffContext = Depends(staff_context),
    db: Session = Depends(get_db),
):
    profile = _own_profile_or_404(db, context.user)
    query = (
        db.query(StaffTask)
        .filter(
            StaffTask.branch_id == context.outlet_id,
            or_(StaffTask.assigned_to == context.user.id, StaffTask.StaffEmployee_profile_id == profile.id),
        )
    )
    total = query.count()
    rows = query.order_by(StaffTask.deadline.asc().nullslast(), StaffTask.due_date.asc().nullslast(), StaffTask.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return _envelope(
        {
            "items": [
                {
                    "id": row.id,
                    "title": row.title or row.task_name,
                    "description": row.description,
                    "status": row.status,
                    "priority": row.priority,
                    "deadline": row.deadline.isoformat() if row.deadline else None,
                    "due_date": row.due_date.isoformat() if row.due_date else None,
                }
                for row in rows
            ],
            "pagination": {"page": page, "page_size": page_size, "total": total},
        },
        context,
        source_status="empty" if not rows else "complete",
        sources=["staff_tasks"],
    )


@router.get("/me/payslips")
def get_my_payslips(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: StaffContext = Depends(staff_context),
    db: Session = Depends(get_db),
):
    profile = _own_profile_or_404(db, context.user)
    query = (
        db.query(PayrollTransaction, PayrollRun)
        .join(PayrollRun, PayrollRun.id == PayrollTransaction.payroll_run_id)
        .filter(PayrollTransaction.staff_id == profile.id, PayrollRun.branch_id == context.outlet_id)
    )
    total = query.count()
    rows = query.order_by(PayrollRun.year.desc(), PayrollRun.month.desc(), PayrollRun.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return _envelope(
        {
            "items": [
                {
                    "payroll_run_id": payroll_run.id,
                    "month": payroll_run.month,
                    "year": payroll_run.year,
                    "status": str(getattr(payroll_run.status, "value", payroll_run.status) or "").lower(),
                    "base_salary": float(txn.base_salary or 0),
                    "total_deductions": float(txn.total_deductions or 0),
                    "net_pay": float(txn.net_pay or 0),
                    "created_at": payroll_run.created_at.isoformat() if payroll_run.created_at else None,
                }
                for txn, payroll_run in rows
            ],
            "pagination": {"page": page, "page_size": page_size, "total": total},
            "source_status": "complete" if rows else "partial",
        },
        context,
        source_status="empty" if not rows else "complete",
        sources=["payroll_transactions", "payroll_runs"],
        missing_sources=[] if rows else ["payroll_transactions"],
    )


@router.post("/me/requests", status_code=status.HTTP_201_CREATED)
def create_my_request(
    payload: StaffRequestCreatePayload,
    request: Request,
    context: StaffContext = Depends(staff_context),
    db: Session = Depends(get_db),
):
    row = StaffRequest(
        staff_id=context.user.id,
        company_id=context.company_id,
        outlet_id=context.outlet_id,
        type=payload.type.strip().lower(),
        reason=payload.reason.strip(),
        status="pending",
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        context.user,
        request,
        "staff.request_created",
        resource_type="staff_request",
        resource_id=row.id,
        company_id=context.company_id,
        outlet_id=context.outlet_id,
        changes={"fields": ["type", "reason", "status"]},
        extra={"request_type": row.type},
        response_status=201,
    )
    db.commit()
    db.refresh(row)
    return _envelope(
        {
            "request": {
                "id": row.id,
                "type": row.type,
                "reason": row.reason,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        },
        context,
        sources=["staff_requests", "ceo_audit_logs"],
    )


@router.get("/me/requests")
def get_my_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: StaffContext = Depends(staff_context),
    db: Session = Depends(get_db),
):
    query = db.query(StaffRequest).filter(StaffRequest.staff_id == context.user.id).order_by(StaffRequest.created_at.desc(), StaffRequest.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return _envelope(
        {
            "items": [
                {
                    "id": row.id,
                    "type": row.type,
                    "reason": row.reason,
                    "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in rows
            ],
            "pagination": {"page": page, "page_size": page_size, "total": total},
        },
        context,
        source_status="empty" if not rows else "complete",
        sources=["staff_requests"],
    )


@router.get("/me/activity")
def get_my_activity(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: StaffContext = Depends(staff_context),
    db: Session = Depends(get_db),
):
    query = db.query(CeoAuditLog).filter(CeoAuditLog.user_id == context.user.id)
    total = query.count()
    rows = query.order_by(CeoAuditLog.created_at.desc(), CeoAuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return _envelope(
        {
            "items": [
                {
                    "id": row.id,
                    "action": row.action,
                    "endpoint": row.endpoint,
                    "http_method": row.http_method,
                    "response_status": row.response_status,
                    "metadata": row.request_meta,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ],
            "pagination": {"page": page, "page_size": page_size, "total": total},
        },
        context,
        source_status="empty" if not rows else "complete",
        sources=["ceo_audit_logs"],
    )
