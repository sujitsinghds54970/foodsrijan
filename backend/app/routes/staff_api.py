from datetime import date, datetime, time
from pathlib import Path
import secrets
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.staff import (
    AttendanceStatus,
    LeaveApprovalStatus,
    StaffAttendanceLog,
    StaffLeaveRequest,
    StaffProfile,
    StaffSalaryDetail,
    StaffStatus,
)
from app.schemas.staff import (
    StaffAttendanceCreateRequest,
    StaffBulkToggleDailyOpsRequest,
    StaffCreateRequest,
    StaffCredentialsUpdateRequest,
    StaffLeaveCreateRequest,
    StaffLeaveDecisionRequest,
    StaffSalaryUpdateRequest,
    StaffUpdateRequest,
)
from app.utils.schema_compat import ensure_staff_daily_ops_column
from app.utils.auth_system import get_current_user
from app.utils.security import hash_password

staff_router = APIRouter(prefix="/staff", tags=["Staff"])
leave_router = APIRouter(prefix="/leave", tags=["Staff Leave"])

ALLOWED_ROLES = {"branch_admin", "branch_director"}
BASE_DIR = Path(__file__).resolve().parents[2]
STAFF_UPLOADS_DIR = BASE_DIR / "uploads" / "staff"
ATTENDANCE_UPLOADS_DIR = STAFF_UPLOADS_DIR / "attendance"


def _normalize_role(role: Optional[str]) -> str:
    return (role or "").strip().lower()


def _assert_access(user: User) -> None:
    if _normalize_role(user.role) not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")
    if not user.branch_id:
        raise HTTPException(status_code=400, detail="User is not mapped to a branch")


def _photo_url(photo_path: Optional[str]) -> Optional[str]:
    if not photo_path:
        return None
    return f"/api/files/{photo_path}"


def _staff_role_from_designation(designation: Optional[str]) -> str:
    value = (designation or "").strip().lower()
    mapping = {
        "technician": "technician",
        "receptionist": "receptionist",
        "lab assistant": "lab_assistant",
        "lab_assistant": "lab_assistant",
        "radiologist": "radiologist",
    }
    return mapping.get(value, "technician")


def _generate_staff_id(db: Session, branch_id: int) -> str:
    seq = db.query(StaffProfile).filter(StaffProfile.branch_id == branch_id).count() + 1
    candidate = f"ST{branch_id:03d}{seq:04d}"
    while db.query(StaffProfile).filter(StaffProfile.staff_id == candidate).first():
        seq += 1
        candidate = f"ST{branch_id:03d}{seq:04d}"
    return candidate


def _build_staff_row(profile: StaffProfile, user: User, salary: Optional[StaffSalaryDetail] = None):
    return {
        "staff_profile_id": profile.id,
        "staff_id": profile.staff_id,
        "user_id": user.id,
        "branch_id": profile.branch_id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip(),
        "mobile": user.phone,
        "department": profile.department,
        "designation": user.role,
        "specialization": profile.specialization,
        "shift_timings": profile.shift_timings,
        "date_of_joining": profile.date_of_joining,
        "address": profile.address,
        "emergency_contact": profile.emergency_contact,
        "status": profile.status.value if profile.status else StaffStatus.ACTIVE.value,
        "can_access_daily_ops": bool(profile.can_access_daily_ops),
        "photo_path": profile.photo_path,
        "photo_url": _photo_url(profile.photo_path),
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "salary": {
            "basic": float(salary.basic) if salary else 0,
            "hra": float(salary.hra) if salary else 0,
            "allowances": float(salary.allowances) if salary else 0,
            "deductions": float(salary.deductions) if salary else 0,
            "net_pay": float(salary.net_pay) if salary else 0,
            "bank_name": salary.bank_name if salary else None,
            "account_number": salary.account_number if salary else None,
            "ifsc_code": salary.ifsc_code if salary else None,
            "upi_id": salary.upi_id if salary else None,
        },
    }


def _get_scoped_profile(db: Session, branch_id: int, staff_profile_id: int) -> StaffProfile:
    profile = (
        db.query(StaffProfile)
        .filter(StaffProfile.id == staff_profile_id, StaffProfile.branch_id == branch_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    return profile


@staff_router.get("")
def list_staff(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        _assert_access(current_user)
        ensure_staff_daily_ops_column(db)
        branch_id = current_user.branch_id

        query = (
            db.query(StaffProfile, User)
            .join(User, User.id == StaffProfile.user_id)
            .filter(StaffProfile.branch_id == branch_id)
        )

        if search:
            like = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    StaffProfile.staff_id.ilike(like),
                    User.first_name.ilike(like),
                    User.last_name.ilike(like),
                    User.username.ilike(like),
                    User.email.ilike(like),
                )
            )

        if status:
            normalized_status = status.strip().lower()
            if normalized_status not in {"active", "inactive"}:
                raise HTTPException(status_code=400, detail="status must be active or inactive")
            query = query.filter(StaffProfile.status == StaffStatus(normalized_status))

        if department:
            query = query.filter(StaffProfile.department.ilike(department.strip()))

        rows = query.order_by(StaffProfile.created_at.desc()).all()

        data = []
        for profile, user in rows:
            data.append(
                {
                    "staff_profile_id": profile.id,
                    "user_id": user.id,
                    "branch_id": profile.branch_id,
                    "staff_id": profile.staff_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "full_name": f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip(),
                    "email": user.email,
                    "mobile": user.phone,
                    "department": profile.department,
                    "designation": user.role,
                    "status": profile.status.value if profile.status else StaffStatus.ACTIVE.value,
                    "can_access_daily_ops": bool(profile.can_access_daily_ops),
                    "photo_url": _photo_url(profile.photo_path),
                }
            )

        return {"items": data, "count": len(data)}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"CRITICAL ERROR in GET /api/staff: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch staff directory") from exc


@staff_router.post("")
def create_staff(
    payload: StaffCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    ensure_staff_daily_ops_column(db)
    branch_id = current_user.branch_id

    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")

    username = f"staff_{secrets.token_hex(4)}"
    while db.query(User).filter(User.username == username).first():
        username = f"staff_{secrets.token_hex(4)}"

    raw_password = payload.temporary_password or f"VV@{secrets.token_hex(4)}"

    user = User(
        username=username,
        email=payload.email,
        hashed_password=hash_password(raw_password),
        role=(payload.designation or "technician").strip().lower(),
        branch_id=branch_id,
        is_active=True,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.mobile,
    )
    db.add(user)
    db.flush()

    profile = StaffProfile(
        user_id=user.id,
        branch_id=branch_id,
        created_by=current_user.id,
        staff_id=_generate_staff_id(db, branch_id),
        department=payload.department,
        specialization=payload.specialization,
        shift_timings=payload.shift_timings,
        date_of_joining=payload.date_of_joining,
        address=payload.address,
        emergency_contact=payload.emergency_contact,
        can_access_daily_ops=bool(payload.can_access_daily_ops),
        status=StaffStatus.ACTIVE,
        is_active=True,
    )
    db.add(profile)
    db.flush()

    salary = StaffSalaryDetail(
        staff_profile_id=profile.id,
        basic=0,
        hra=0,
        allowances=0,
        deductions=0,
        net_pay=0,
    )
    db.add(salary)

    db.commit()
    db.refresh(profile)

    return {
        "message": "Staff created successfully",
        "temporary_password": raw_password,
        "username": username,
        "staff": _build_staff_row(profile, user, salary),
    }


@staff_router.get("/{staff_profile_id}")
def get_staff(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    ensure_staff_daily_ops_column(db)
    branch_id = current_user.branch_id

    profile = _get_scoped_profile(db, branch_id, staff_profile_id)
    user = db.query(User).filter(User.id == profile.user_id).first()
    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == profile.id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Linked user not found")

    return _build_staff_row(profile, user, salary)


@staff_router.put("/{staff_profile_id}")
def update_staff(
    staff_profile_id: int,
    payload: StaffUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    ensure_staff_daily_ops_column(db)
    branch_id = current_user.branch_id

    profile = _get_scoped_profile(db, branch_id, staff_profile_id)
    user = db.query(User).filter(User.id == profile.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Linked user not found")

    if payload.email and payload.email != user.email:
        existing_email = db.query(User).filter(User.email == payload.email, User.id != user.id).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = payload.email

    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.mobile is not None:
        user.phone = payload.mobile
    if payload.designation is not None:
        user.role = _staff_role_from_designation(payload.designation)

    if payload.department is not None:
        profile.department = payload.department
    if payload.specialization is not None:
        profile.specialization = payload.specialization
    if payload.shift_timings is not None:
        profile.shift_timings = payload.shift_timings
    if payload.date_of_joining is not None:
        profile.date_of_joining = payload.date_of_joining
    if payload.address is not None:
        profile.address = payload.address
    if payload.emergency_contact is not None:
        profile.emergency_contact = payload.emergency_contact
    if payload.can_access_daily_ops is not None:
        profile.can_access_daily_ops = bool(payload.can_access_daily_ops)
    if payload.status is not None:
        normalized = payload.status.strip().lower()
        if normalized not in {"active", "inactive"}:
            raise HTTPException(status_code=400, detail="status must be active or inactive")
        profile.status = StaffStatus(normalized)
        profile.is_active = normalized == "active"
        user.is_active = profile.is_active

    db.commit()

    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == profile.id).first()
    return {"message": "Staff profile updated", "staff": _build_staff_row(profile, user, salary)}


@staff_router.post("/bulk-toggle-daily-ops")
def bulk_toggle_daily_ops_access(
    payload: StaffBulkToggleDailyOpsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    ensure_staff_daily_ops_column(db)
    branch_id = current_user.branch_id

    target_ids = sorted(set(payload.staff_profile_ids))
    if not target_ids:
        raise HTTPException(status_code=400, detail="No staff profiles selected")

    profiles = (
        db.query(StaffProfile)
        .filter(StaffProfile.branch_id == branch_id, StaffProfile.id.in_(target_ids))
        .all()
    )

    found_ids = {profile.id for profile in profiles}
    missing_ids = [item for item in target_ids if item not in found_ids]
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Staff not found for ids: {missing_ids}")

    for profile in profiles:
        profile.can_access_daily_ops = bool(payload.can_access_daily_ops)
        profile.updated_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Daily Operations access updated",
        "updated_count": len(profiles),
        "can_access_daily_ops": bool(payload.can_access_daily_ops),
    }


@staff_router.delete("/{staff_profile_id}")
def soft_delete_staff(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id

    profile = _get_scoped_profile(db, branch_id, staff_profile_id)
    user = db.query(User).filter(User.id == profile.user_id).first()

    profile.status = StaffStatus.INACTIVE
    profile.is_active = False
    if user:
        user.is_active = False

    db.commit()
    return {"message": "Staff deactivated"}


@staff_router.put("/{staff_profile_id}/credentials")
def update_staff_credentials(
    staff_profile_id: int,
    payload: StaffCredentialsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id

    profile = _get_scoped_profile(db, branch_id, staff_profile_id)
    user = db.query(User).filter(User.id == profile.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Linked user not found")

    if not payload.username and not payload.password:
        raise HTTPException(status_code=400, detail="Provide username or password")

    if payload.username and payload.username != user.username:
        existing = db.query(User).filter(User.username == payload.username, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = payload.username

    if payload.password:
        user.hashed_password = hash_password(payload.password)

    db.commit()
    return {"message": "Credentials updated", "username": user.username}


@staff_router.post("/{staff_profile_id}/photo")
def upload_staff_photo(
    staff_profile_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id

    profile = _get_scoped_profile(db, branch_id, staff_profile_id)

    suffix = Path(file.filename or "photo").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp are allowed")

    STAFF_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"staff_{staff_profile_id}_{secrets.token_hex(8)}{suffix}"
    destination = STAFF_UPLOADS_DIR / filename

    with destination.open("wb") as output:
        output.write(file.file.read())

    profile.photo_path = f"staff/{filename}"
    profile.updated_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Photo uploaded",
        "photo_path": profile.photo_path,
        "photo_url": _photo_url(profile.photo_path),
    }


@staff_router.get("/{staff_profile_id}/salary")
def get_staff_salary(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id

    _get_scoped_profile(db, branch_id, staff_profile_id)

    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == staff_profile_id).first()
    if not salary:
        return {
            "basic": 0,
            "hra": 0,
            "allowances": 0,
            "deductions": 0,
            "net_pay": 0,
            "bank_name": None,
            "account_number": None,
            "ifsc_code": None,
            "upi_id": None,
        }

    return {
        "basic": float(salary.basic or 0),
        "hra": float(salary.hra or 0),
        "allowances": float(salary.allowances or 0),
        "deductions": float(salary.deductions or 0),
        "net_pay": float(salary.net_pay or 0),
        "bank_name": salary.bank_name,
        "account_number": salary.account_number,
        "ifsc_code": salary.ifsc_code,
        "upi_id": salary.upi_id,
    }


@staff_router.post("/{staff_profile_id}/salary")
def update_staff_salary(
    staff_profile_id: int,
    payload: StaffSalaryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id

    _get_scoped_profile(db, branch_id, staff_profile_id)

    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == staff_profile_id).first()
    if not salary:
        salary = StaffSalaryDetail(staff_profile_id=staff_profile_id)
        db.add(salary)

    salary.basic = payload.basic
    salary.hra = payload.hra
    salary.allowances = payload.allowances
    salary.deductions = payload.deductions
    salary.net_pay = payload.net_pay if payload.net_pay is not None else (payload.basic + payload.hra + payload.allowances - payload.deductions)
    salary.bank_name = payload.bank_name
    salary.account_number = payload.account_number
    salary.ifsc_code = payload.ifsc_code
    salary.upi_id = payload.upi_id

    db.commit()

    return {
        "message": "Salary updated",
        "salary": {
            "basic": float(salary.basic or 0),
            "hra": float(salary.hra or 0),
            "allowances": float(salary.allowances or 0),
            "deductions": float(salary.deductions or 0),
            "net_pay": float(salary.net_pay or 0),
            "bank_name": salary.bank_name,
            "account_number": salary.account_number,
            "ifsc_code": salary.ifsc_code,
            "upi_id": salary.upi_id,
        },
    }


@staff_router.get("/{staff_profile_id}/attendance")
def list_staff_attendance(
    staff_profile_id: int,
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id
    _get_scoped_profile(db, branch_id, staff_profile_id)

    query = db.query(StaffAttendanceLog).filter(
        StaffAttendanceLog.staff_profile_id == staff_profile_id,
        StaffAttendanceLog.branch_id == branch_id,
    )

    if month and year:
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        query = query.filter(StaffAttendanceLog.attendance_date >= start, StaffAttendanceLog.attendance_date < end)

    rows = query.order_by(StaffAttendanceLog.attendance_date.desc()).all()

    items = []
    for row in rows:
        items.append(
            {
                "id": row.id,
                "attendance_date": row.attendance_date,
                "attendance_type": row.attendance_type.value if row.attendance_type else AttendanceStatus.PRESENT.value,
                "clock_in_time": row.clock_in_time,
                "clock_out_time": row.clock_out_time,
            }
        )

    return {"items": items, "count": len(items)}


@staff_router.post("/{staff_profile_id}/attendance")
def create_staff_attendance(
    staff_profile_id: int,
    payload: StaffAttendanceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id
    _get_scoped_profile(db, branch_id, staff_profile_id)

    if payload.clock_in_time and payload.clock_out_time and payload.clock_out_time < payload.clock_in_time:
        raise HTTPException(status_code=400, detail="clock_out_time cannot be before clock_in_time")

    target_start = datetime.combine(payload.attendance_date, time.min)
    target_end = datetime.combine(payload.attendance_date, time.max)

    row = (
        db.query(StaffAttendanceLog)
        .filter(
            StaffAttendanceLog.staff_profile_id == staff_profile_id,
            StaffAttendanceLog.branch_id == branch_id,
            StaffAttendanceLog.attendance_date >= target_start,
            StaffAttendanceLog.attendance_date <= target_end,
        )
        .first()
    )

    attendance_enum = AttendanceStatus(payload.attendance_type.lower())

    if not row:
        row = StaffAttendanceLog(
            staff_profile_id=staff_profile_id,
            branch_id=branch_id,
            attendance_date=target_start,
        )
        db.add(row)

    row.attendance_type = attendance_enum
    row.clock_in_time = payload.clock_in_time
    row.clock_out_time = payload.clock_out_time

    db.commit()

    return {
        "message": "Attendance saved",
        "attendance": {
            "id": row.id,
            "attendance_date": row.attendance_date,
            "attendance_type": row.attendance_type.value,
            "clock_in_time": row.clock_in_time,
            "clock_out_time": row.clock_out_time,
        },
    }


@staff_router.post("/{staff_profile_id}/attendance/clock-in")
def clock_in_staff_attendance(
    staff_profile_id: int,
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    attendance_date: Optional[date] = Form(None),
    clock_in_time: Optional[datetime] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id
    _get_scoped_profile(db, branch_id, staff_profile_id)

    target_date = attendance_date or date.today()
    target_start = datetime.combine(target_date, time.min)
    target_end = datetime.combine(target_date, time.max)

    row = (
        db.query(StaffAttendanceLog)
        .filter(
            StaffAttendanceLog.staff_profile_id == staff_profile_id,
            StaffAttendanceLog.branch_id == branch_id,
            StaffAttendanceLog.attendance_date >= target_start,
            StaffAttendanceLog.attendance_date <= target_end,
        )
        .first()
    )

    if not row:
        row = StaffAttendanceLog(
            staff_profile_id=staff_profile_id,
            branch_id=branch_id,
            attendance_date=target_start,
        )
        db.add(row)

    row.attendance_type = AttendanceStatus.PRESENT
    row.clock_in_time = clock_in_time or datetime.utcnow()
    row.clock_in_latitude = str(latitude) if latitude is not None else None
    row.clock_in_longitude = str(longitude) if longitude is not None else None

    if photo:
        suffix = Path(photo.filename or "selfie").suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp are allowed")
        ATTENDANCE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"attendance_{staff_profile_id}_{secrets.token_hex(8)}{suffix}"
        destination = ATTENDANCE_UPLOADS_DIR / filename
        with destination.open("wb") as output:
            output.write(photo.file.read())
        row.clock_in_photo_path = f"staff/attendance/{filename}"

    db.commit()

    return {
        "message": "Clock-in saved",
        "attendance": {
            "id": row.id,
            "attendance_date": row.attendance_date,
            "attendance_type": row.attendance_type.value,
            "clock_in_time": row.clock_in_time,
            "clock_in_latitude": row.clock_in_latitude,
            "clock_in_longitude": row.clock_in_longitude,
            "selfie_url": _photo_url(row.clock_in_photo_path),
        },
    }


@staff_router.get("/{staff_profile_id}/leave")
def list_staff_leave_requests(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id
    _get_scoped_profile(db, branch_id, staff_profile_id)

    rows = (
        db.query(StaffLeaveRequest)
        .filter(
            StaffLeaveRequest.staff_profile_id == staff_profile_id,
            StaffLeaveRequest.branch_id == branch_id,
        )
        .order_by(StaffLeaveRequest.created_at.desc())
        .all()
    )

    items = []
    for row in rows:
        items.append(
            {
                "id": row.id,
                "leave_type": row.leave_type,
                "start_date": row.start_date,
                "end_date": row.end_date,
                "total_days": row.total_days,
                "reason": row.reason,
                "status": row.status.value if row.status else LeaveApprovalStatus.PENDING.value,
                "review_comment": row.review_comment,
                "created_at": row.created_at,
            }
        )

    return {"items": items, "count": len(items)}


@staff_router.post("/{staff_profile_id}/leave")
def create_staff_leave_request(
    staff_profile_id: int,
    payload: StaffLeaveCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id
    _get_scoped_profile(db, branch_id, staff_profile_id)

    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date")

    total_days = float((payload.end_date - payload.start_date).days + 1)

    row = StaffLeaveRequest(
        staff_profile_id=staff_profile_id,
        branch_id=branch_id,
        leave_type=payload.leave_type.strip().lower(),
        start_date=datetime.combine(payload.start_date, time.min),
        end_date=datetime.combine(payload.end_date, time.min),
        total_days=total_days,
        reason=payload.reason,
        status=LeaveApprovalStatus.PENDING,
    )
    db.add(row)
    db.commit()

    return {
        "message": "Leave request submitted",
        "leave": {
            "id": row.id,
            "status": row.status.value,
            "total_days": row.total_days,
        },
    }


@leave_router.put("/{leave_request_id}/approve")
def approve_or_reject_leave(
    leave_request_id: int,
    payload: StaffLeaveDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(current_user)
    branch_id = current_user.branch_id

    row = (
        db.query(StaffLeaveRequest)
        .filter(StaffLeaveRequest.id == leave_request_id, StaffLeaveRequest.branch_id == branch_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Leave request not found")

    status_value = payload.status.strip().lower()
    if status_value not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="status must be approved or rejected")

    row.status = LeaveApprovalStatus(status_value)
    row.review_comment = payload.review_comment
    row.reviewed_by = current_user.id
    row.reviewed_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Leave status updated",
        "leave": {
            "id": row.id,
            "status": row.status.value,
            "review_comment": row.review_comment,
        },
    }


@staff_router.patch("/leave/{leave_request_id}")
def decide_staff_leave_request_legacy(
    leave_request_id: int,
    payload: StaffLeaveDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return approve_or_reject_leave(leave_request_id, payload, db, current_user)
