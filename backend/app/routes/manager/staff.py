from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.login_credentials import LoginCredentialsUpdate
from app.services.login_credentials import login_credentials, update_login_credentials
from app.models.ceo import CeoAuditLog
from app.models.hr import StaffAttendanceLog, StaffProfile, StaffRequest, StaffTask
from app.models.payroll.models import PayrollRun, PayrollTransaction
from app.services.executive_metrics import ResolvedScope, envelope
from app.services.file_storage import save_upload
from app.services.staff_rate_limit import check_staff_creation_allowed, record_staff_creation
from app.services.staff_service import (
    STAFF_MUTABLE_MANAGER_FIELDS,
    create_staff,
    deactivate_staff,
    get_scoped_staff,
    get_staff_profile,
    masked_audit_fields,
    reset_staff_password,
    restore_staff,
    reveal_staff_field,
    serialize_staff,
    serialize_staff_list_item,
    staff_credentials_response,
    sync_staff_profile,
    update_staff,
)
from app.services.token_revocation import revoke_user_sessions
from app.services.outlet_service import write_audit
from app.utils.auth_system import auth_guard
from app.utils.guards import OutletManagerContext, outlet_manager_context


router = APIRouter(prefix="/manager/staff", tags=["Outlet Manager Staff"])


class StaffCreatePayload(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=150)
    email: EmailStr | None = None
    phone: str = Field(..., min_length=10, max_length=20)
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
    aadhaar_number: str | None = None
    pan_number: str | None = None
    voter_id: str | None = None
    driving_license: str | None = None
    passport_number: str | None = None
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
    joining_date: date | None = None
    employment_type: Literal["full_time", "part_time", "contract", "intern", "probation"] | None = None
    probation_end_date: date | None = None
    salary_type: Literal["monthly", "daily", "hourly"] | None = None
    monthly_salary: float | None = Field(default=None, ge=0)
    daily_wage: float | None = Field(default=None, ge=0)
    hourly_rate: float | None = Field(default=None, ge=0)
    shift_preference: str | None = Field(default=None, max_length=100)
    weekly_off_day: str | None = Field(default=None, max_length=20)
    pf_applicable: bool = False
    esi_applicable: bool = False
    tds_applicable: bool = False
    staff_role: str = Field(..., max_length=40)
    employee_code: str = Field(..., min_length=2, max_length=40)
    password: str | None = Field(default=None, min_length=1, max_length=72)
    username: str | None = Field(default=None, min_length=4, max_length=30)
    company_id: int | None = None
    outlet_id: int | None = None
    branch_id: int | None = None


class StaffUpdatePayload(BaseModel):
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
    profile_photo_url: str | None = Field(default=None, max_length=2048)
    current_address: str | None = None
    permanent_address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    emergency_contact_relation: str | None = Field(default=None, max_length=100)
    aadhaar_number: str | None = None
    pan_number: str | None = None
    voter_id: str | None = None
    driving_license: str | None = None
    passport_number: str | None = None
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
    joining_date: date | None = None
    employment_type: Literal["full_time", "part_time", "contract", "intern", "probation"] | None = None
    probation_end_date: date | None = None
    salary_type: Literal["monthly", "daily", "hourly"] | None = None
    monthly_salary: float | None = Field(default=None, ge=0)
    daily_wage: float | None = Field(default=None, ge=0)
    hourly_rate: float | None = Field(default=None, ge=0)
    shift_preference: str | None = Field(default=None, max_length=100)
    weekly_off_day: str | None = Field(default=None, max_length=20)
    pf_applicable: bool | None = None
    esi_applicable: bool | None = None
    tds_applicable: bool | None = None
    staff_role: str | None = Field(default=None, max_length=40)
    employee_code: str | None = Field(default=None, min_length=2, max_length=40)
    manager_id: int | None = None
    company_id: int | None = None
    outlet_id: int | None = None
    branch_id: int | None = None


class StaffDeactivatePayload(BaseModel):
    deactivated_reason: str | None = Field(default=None, max_length=1000)


class StaffLoginTestPayload(BaseModel):
    password: str = Field(..., min_length=1, max_length=72)
    identifier: str | None = Field(default=None, max_length=254)


class StaffScopeQuery(BaseModel):
    page: int = 1


def _scope(context: OutletManagerContext) -> ResolvedScope:
    return ResolvedScope(
        level="branch",
        company_ids=(context.company_id,),
        company_id=context.company_id,
        branch_id=context.outlet_id,
    )


def _envelope(
    data: Any,
    context: OutletManagerContext,
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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_staff_member(
    payload: StaffCreatePayload,
    request: Request,
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    check_staff_creation_allowed(context.user.id)
    staff, password = create_staff(db, context.user, context.outlet, request, payload.model_dump(exclude_none=True))
    record_staff_creation(context.user.id)
    return _envelope(
        {
            "staff": serialize_staff(staff, masked=True),
            "credentials": staff_credentials_response(staff, password, "Store this password now. It will not be shown again."),
        },
        context,
        sources=["users", "staff_profiles", "ceo_audit_logs"],
    )


@router.get("")
def list_staff_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    staff_role: str | None = Query(default=None),
    status_filter: Literal["active", "inactive", "all"] = Query(default="active", alias="status"),
    search: str | None = Query(default=None, max_length=100),
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(
        User.company_id == context.company_id,
        User.outlet_id == context.outlet_id,
        User.is_staff.is_(True),
    )
    if staff_role:
        query = query.filter(User.staff_role == staff_role.strip().lower())
    if status_filter == "active":
        query = query.filter(User.is_active.is_(True), User.is_deleted.is_(False))
    elif status_filter == "inactive":
        query = query.filter(User.is_active.is_(False))
    else:
        query = query.filter(or_(User.is_deleted.is_(False), User.is_deleted.is_(True)))
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                func.lower(User.first_name).like(term.lower()),
                func.lower(User.last_name).like(term.lower()),
                func.lower(User.display_name).like(term.lower()),
                User.phone.like(term),
                func.lower(User.employee_code).like(term.lower()),
            )
        )
    total = query.count()
    rows = (
        query.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return _envelope(
        {
            "items": [serialize_staff_list_item(row) for row in rows],
            "pagination": {"page": page, "page_size": page_size, "total": total},
        },
        context,
        source_status="empty" if not rows else "complete",
        sources=["users"],
    )


@router.get("/stats")
def staff_stats(
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    today = datetime.combine(date.today(), datetime.min.time())
    tomorrow = today + timedelta(days=1)
    total_staff = (
        db.query(func.count(User.id))
        .filter(
            User.company_id == context.company_id,
            User.outlet_id == context.outlet_id,
            User.is_staff.is_(True),
            User.is_deleted.is_(False),
        )
        .scalar()
        or 0
    )
    active_today = (
        db.query(func.count(func.distinct(StaffAttendanceLog.StaffEmployee_profile_id)))
        .join(StaffProfile, StaffProfile.id == StaffAttendanceLog.StaffEmployee_profile_id)
        .join(User, User.id == StaffProfile.user_id)
        .filter(
            User.company_id == context.company_id,
            User.outlet_id == context.outlet_id,
            User.is_staff.is_(True),
            StaffAttendanceLog.attendance_date >= today,
            StaffAttendanceLog.attendance_date < tomorrow,
        )
        .scalar()
        or 0
    )
    on_shift_now = (
        db.query(func.count(func.distinct(StaffAttendanceLog.StaffEmployee_profile_id)))
        .join(StaffProfile, StaffProfile.id == StaffAttendanceLog.StaffEmployee_profile_id)
        .join(User, User.id == StaffProfile.user_id)
        .filter(
            User.company_id == context.company_id,
            User.outlet_id == context.outlet_id,
            User.is_staff.is_(True),
            StaffAttendanceLog.attendance_date >= today,
            StaffAttendanceLog.attendance_date < tomorrow,
            StaffAttendanceLog.clock_in_time.is_not(None),
            StaffAttendanceLog.clock_out_time.is_(None),
        )
        .scalar()
        or 0
    )
    pending_requests = (
        db.query(func.count(StaffRequest.id))
        .filter(
            StaffRequest.company_id == context.company_id,
            StaffRequest.outlet_id == context.outlet_id,
            StaffRequest.status == "pending",
        )
        .scalar()
        or 0
    )
    return _envelope(
        {
            "stats": {
                "total_staff": int(total_staff),
                "active_today": int(active_today),
                "on_shift_now": int(on_shift_now),
                "pending_requests": int(pending_requests),
            },
            "source_status": "complete",
        },
        context,
        sources=["users", "staff_attendance_logs", "staff_requests"],
    )


@router.get("/{staff_id}")
def get_staff_member(
    staff_id: int,
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    staff = get_scoped_staff(db, context.company_id, context.outlet_id, staff_id)
    return _envelope({"staff": serialize_staff(staff, masked=True)}, context, sources=["users"])


@router.get("/{staff_id}/reveal")
def reveal_staff_pii(
    staff_id: int,
    field: str = Query(..., min_length=2),
    request: Request = None,
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    staff = get_scoped_staff(db, context.company_id, context.outlet_id, staff_id)
    return _envelope({"reveal": reveal_staff_field(db, context.user, request, staff, field)}, context, sources=["users", "ceo_audit_logs"])


@router.get("/{staff_id}/credentials")
def get_staff_credentials(
    staff_id: int, response: Response,
    context: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db),
):
    staff = get_scoped_staff(db, context.company_id, context.outlet_id, staff_id)
    response.headers["Cache-Control"] = "no-store"
    return _envelope({"login": login_credentials(staff)}, context)


@router.patch("/{staff_id}/credentials")
def edit_staff_credentials(
    staff_id: int, payload: LoginCredentialsUpdate, request: Request, response: Response,
    context: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db),
):
    staff = get_scoped_staff(db, context.company_id, context.outlet_id, staff_id)
    response.headers["Cache-Control"] = "no-store"
    return _envelope(update_login_credentials(db, context.user, request, staff, payload, "staff"), context)


@router.put("/{staff_id}")
def update_staff_member(
    staff_id: int,
    payload: StaffUpdatePayload,
    request: Request,
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    staff = get_scoped_staff(db, context.company_id, context.outlet_id, staff_id)
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("company_id", None)
    changes.pop("outlet_id", None)
    changes.pop("branch_id", None)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one staff field must be provided")
    updated = update_staff(db, context.user, request, staff, changes)
    return _envelope({"staff": serialize_staff(updated, masked=True)}, context, sources=["users", "staff_profiles", "ceo_audit_logs"])


@router.delete("/{staff_id}")
def delete_staff_member(
    staff_id: int,
    payload: StaffDeactivatePayload,
    request: Request,
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    staff = get_scoped_staff(db, context.company_id, context.outlet_id, staff_id)
    deactivate_staff(db, context.user, request, staff, payload.deactivated_reason)
    revoke_user_sessions(staff.id)
    return _envelope({"staff": serialize_staff(staff, masked=True)}, context, sources=["users", "staff_profiles", "ceo_audit_logs"])


@router.post("/{staff_id}/restore")
def restore_staff_member(
    staff_id: int,
    request: Request,
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    staff = get_scoped_staff(db, context.company_id, context.outlet_id, staff_id, include_deleted=True)
    restored = restore_staff(db, context.user, request, staff)
    return _envelope({"staff": serialize_staff(restored, masked=True)}, context, sources=["users", "staff_profiles", "ceo_audit_logs"])


@router.post("/{staff_id}/reset-password")
def reset_staff_member_password(
    staff_id: int,
    request: Request,
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    staff = get_scoped_staff(db, context.company_id, context.outlet_id, staff_id)
    password = reset_staff_password(db, context.user, request, staff)
    revoke_user_sessions(staff.id)
    return _envelope(
        {
            "credentials": staff_credentials_response(staff, password, "Store this password now. It will not be shown again."),
            "staff": serialize_staff(staff, masked=True),
        },
        context,
        sources=["users", "ceo_audit_logs"],
    )


@router.post("/{staff_id}/test-login")
def test_staff_member_login(
    staff_id: int,
    payload: StaffLoginTestPayload,
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    staff = get_scoped_staff(db, context.company_id, context.outlet_id, staff_id)
    identifier = payload.identifier or staff.username
    valid = bool(staff.is_active and not staff.is_deleted and auth_guard.verify_password(payload.password, staff.hashed_password))
    return _envelope(
        {"result": {"identifier": identifier, "can_login": valid, "is_active": bool(staff.is_active and not staff.is_deleted)}},
        context,
        sources=["users"],
    )


@router.get("/{staff_id}/audit")
def get_staff_member_audit(
    staff_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    get_scoped_staff(db, context.company_id, context.outlet_id, staff_id)
    query = db.query(CeoAuditLog).filter(
        CeoAuditLog.request_meta["resource_id"].as_integer() == staff_id,
        CeoAuditLog.request_meta["company_id"].as_integer() == context.company_id,
        CeoAuditLog.request_meta["outlet_id"].as_integer() == context.outlet_id,
    )
    total = query.count()
    rows = query.order_by(CeoAuditLog.created_at.desc(), CeoAuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return _envelope(
        {
            "items": [
                {
                    "id": row.id,
                    "action": row.action,
                    "actor_id": row.user_id,
                    "http_method": row.http_method,
                    "endpoint": row.endpoint,
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


@router.post("/{staff_id}/photo")
async def upload_staff_member_photo(
    staff_id: int,
    request: Request,
    file: UploadFile = File(...),
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    staff = get_scoped_staff(db, context.company_id, context.outlet_id, staff_id)
    asset = await save_upload(file, "staff-photos", staff.id)
    staff.profile_photo_url = asset["url"]
    sync_staff_profile(db, staff, context.user.id)
    write_audit(
        db,
        context.user,
        request,
        "staff.updated",
        resource_type="user",
        resource_id=staff.id,
        company_id=context.company_id,
        outlet_id=context.outlet_id,
        changes={"fields": ["profile_photo_url"]},
        extra={"asset": {"url": asset["url"], "filename": asset["filename"]}},
    )
    db.commit()
    return _envelope({"staff": serialize_staff(staff, masked=True), "asset": asset}, context, sources=["users", "ceo_audit_logs"])
