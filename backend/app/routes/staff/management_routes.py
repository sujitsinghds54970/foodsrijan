from datetime import datetime, date, timedelta
import calendar
import csv
import io
import json
import secrets
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.hr import (
    StaffProfile,
    StaffSalaryDetail,
    StaffSalaryRecord,
    StaffAttendanceLog,
    StaffLeaveRequest,
    StaffPerformanceNote,
    StaffDocument,
    StaffWeeklyRoster,
    DirectorStaffStatus,
    DirectorAttendanceType,
    LeaveStatus,
)
from app.models.hr import DirectorNotification
from app.models.daily_entry_module import DailyEntryModule
from app.utils.auth_system import get_current_user
from app.utils.security import hash_password


router = APIRouter()
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uploads"
STAFF_ACCESS_ROLES = ["branch_admin", "branch_director"]
STAFF_ROLE_CHOICES = {"Technician", "Receptionist", "Lab Assistant", "Radiologist"}


class StaffCreatePayload(BaseModel):
    branch_id: Optional[int] = None
    first_name: str
    last_name: str
    email: str
    mobile: str
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    role: str = Field(default="Technician")
    department: Optional[str] = None
    specialization: Optional[str] = None
    joined_date: Optional[datetime] = None
    shift_timing: Optional[str] = None
    reporting_manager_id: Optional[int] = None
    temporary_password: Optional[str] = None
    auto_generate_password: bool = True


class StaffUpdatePayload(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    role: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    department: Optional[str] = None
    specialization: Optional[str] = None
    joined_date: Optional[datetime] = None
    shift_timing: Optional[str] = None
    reporting_manager_id: Optional[int] = None
    status: Optional[str] = None


class SalaryUpdatePayload(BaseModel):
    month: Optional[int] = None
    year: Optional[int] = None
    basic: float = 0
    hra: float = 0
    allowances: float = 0
    deductions: float = 0
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    upi_id: Optional[str] = None


class LeaveApplyPayload(BaseModel):
    leave_type: str
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None
    staff_profile_id: Optional[int] = None


class LeaveDecisionPayload(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    review_comment: Optional[str] = None


class PerformanceNotePayload(BaseModel):
    note: str


class WeeklyRosterPayload(BaseModel):
    week_start_date: datetime
    week_end_date: datetime
    schedule: dict
    notes: Optional[str] = None


class StaffCredentialsUpdatePayload(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    auto_generate_password: bool = False


def _assert_staff_scope(user: User) -> None:
    if user.role not in STAFF_ACCESS_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")


def _assert_director_scope(user: User) -> None:
    _assert_staff_scope(user)


def _assert_branch_access(user: User, branch_id: int) -> None:
    if user.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied for this branch")


def _generate_username(first_name: str, last_name: str) -> str:
    return f"{first_name.lower()}.{last_name.lower()}.{secrets.token_hex(2)}"


def _generate_staff_id(db: Session, branch_id: int) -> str:
    seq = db.query(StaffProfile).filter(StaffProfile.branch_id == branch_id).count() + 1
    candidate = f"ST{branch_id:03d}{seq:04d}"
    while db.query(StaffProfile).filter(StaffProfile.staff_id == candidate).first():
        seq += 1
        candidate = f"ST{branch_id:03d}{seq:04d}"
    return candidate


def _generate_temp_password(length: int = 12) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#_-"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _save_uploaded_file(upload: UploadFile, folder_name: str) -> str:
    target_dir = UPLOADS_DIR / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "file").suffix
    generated_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(6)}{suffix}"
    target_file = target_dir / generated_name

    with target_file.open("wb") as f:
        f.write(upload.file.read())

    return str(target_file.relative_to(UPLOADS_DIR))


def _ensure_director_notification(db: Session, branch_id: int, title: str, message: str) -> None:
    director_user = db.query(User).filter(
        User.branch_id == branch_id,
        User.role == "branch_director",
        User.is_active.is_(True),
    ).first()
    if not director_user:
        return

    row = DirectorNotification(
        director_user_id=director_user.id,
        branch_id=branch_id,
        title=title,
        message=message,
        is_read=False,
    )
    db.add(row)


@router.post("/")
def create_staff(
    payload: StaffCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    target_branch_id = current_user.branch_id
    if not target_branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment missing")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if payload.role not in STAFF_ROLE_CHOICES:
        raise HTTPException(status_code=400, detail="role must be one of Technician, Receptionist, Lab Assistant, Radiologist")

    username = _generate_username(payload.first_name, payload.last_name)
    while db.query(User).filter(User.username == username).first():
        username = _generate_username(payload.first_name, payload.last_name)

    temp_password = payload.temporary_password or _generate_temp_password()

    user = User(
        username=username,
        email=payload.email,
        hashed_password=hash_password(temp_password),
        role=payload.role,
        branch_id=target_branch_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.mobile,
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Contract requirement: generated login should be `staff_<id>`.
    user.username = f"staff_{user.id}"

    profile = StaffProfile(
        user_id=user.id,
        branch_id=target_branch_id,
        created_by=current_user.id,
        staff_id=_generate_staff_id(db, target_branch_id),
        department=payload.department,
        specialization=payload.specialization,
        shift_timings=payload.shift_timing,
        reporting_manager_id=payload.reporting_manager_id,
        date_of_joining=payload.joined_date,
        address=payload.address,
        emergency_contact=payload.emergency_contact,
        status=DirectorStaffStatus.ACTIVE,
        is_active=True,
    )
    db.add(profile)
    db.flush()

    db.add(StaffSalaryDetail(staff_profile_id=profile.id, basic=0, hra=0, allowances=0, deductions=0, net_pay=0))

    _ensure_director_notification(
        db,
        branch_id=target_branch_id,
        title="Staff Created",
        message=f"{profile.staff_id} was created by {current_user.username}.",
    )

    db.commit()

    return {
        "message": "Staff created successfully",
        "staff": {
            "staff_profile_id": profile.id,
            "staff_id": profile.staff_id,
            "name": f"{user.first_name} {user.last_name}",
            "department": profile.department,
            "status": profile.status.value,
            "photo_url": profile.photo_path,
            "full_name": f"{user.first_name} {user.last_name}",
            "mobile": user.phone,
            "email": user.email,
            "role": user.role,
            "joined_date": profile.date_of_joining,
            "shift_timing": profile.shift_timings,
        },
        "credentials": {
            "username": user.username,
            "password": temp_password,
            "role": user.role,
        },
    }


@router.get("/")
def list_staff(
    branch_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    target_branch_id = current_user.branch_id
    if not target_branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment missing")
    if branch_id is not None and branch_id != target_branch_id:
        raise HTTPException(status_code=403, detail="Access denied for this branch")

    query = db.query(StaffProfile, User).join(User, StaffProfile.user_id == User.id).filter(
        StaffProfile.branch_id == target_branch_id
    )

    if role:
        query = query.filter(User.role == role)
    if department:
        query = query.filter(StaffProfile.department == department)
    if status:
        query = query.filter(StaffProfile.status == DirectorStaffStatus(status))
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.email.ilike(like),
                StaffProfile.staff_id.ilike(like),
                StaffProfile.department.ilike(like),
            )
        )

    rows = query.order_by(StaffProfile.created_at.desc()).all()
    return [
        {
            "id": sp.id,
            "branch_id": sp.branch_id,
            "photo_url": sp.photo_path,
            "staff_id": sp.staff_id,
            "name": f"{u.first_name} {u.last_name}",
            "full_name": f"{u.first_name} {u.last_name}",
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "mobile": u.phone,
            "role": u.role,
            "department": sp.department,
            "specialization": sp.specialization,
            "joined_date": sp.date_of_joining,
            "shift_timing": sp.shift_timings,
            "status": sp.status.value,
            "is_active": sp.is_active,
        }
        for sp, u in rows
    ]


@router.get("/{staff_profile_id}")
def get_staff_profile(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    row = db.query(StaffProfile, User).join(User, StaffProfile.user_id == User.id).filter(StaffProfile.id == staff_profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Staff not found")

    profile, user = row
    _assert_branch_access(current_user, profile.branch_id)

    if current_user.role == "staff" and current_user.id != profile.user_id:
        raise HTTPException(status_code=403, detail="Staff can only view own profile")

    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == profile.id).first()
    docs = db.query(StaffDocument).filter(StaffDocument.staff_profile_id == profile.id).order_by(StaffDocument.created_at.desc()).all()

    return {
        "id": profile.id,
        "user_id": user.id,
        "branch_id": profile.branch_id,
        "staff_id": profile.staff_id,
        "photo_url": profile.photo_path,
        "full_name": f"{user.first_name} {user.last_name}",
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "mobile": user.phone,
        "address": profile.address,
        "emergency_contact": profile.emergency_contact,
        "role": user.role,
        "specialization": profile.specialization,
        "department": profile.department,
        "joined_date": profile.date_of_joining,
        "shift_timing": profile.shift_timings,
        "reporting_manager_id": profile.reporting_manager_id,
        "status": profile.status.value,
        "salary": {
            "basic": float(salary.basic or 0) if salary else 0,
            "hra": float(salary.hra or 0) if salary else 0,
            "allowances": float(salary.allowances or 0) if salary else 0,
            "deductions": float(salary.deductions or 0) if salary else 0,
            "net_pay": float(salary.net_pay or 0) if salary else 0,
            "bank_name": salary.bank_name if salary else None,
            "account_number": salary.account_number if salary else None,
            "ifsc_code": salary.ifsc_code if salary else None,
            "upi_id": salary.upi_id if salary else None,
        },
        "documents": [
            {
                "id": d.id,
                "file_name": d.file_name,
                "file_path": d.file_path,
                "document_type": d.document_type,
                "created_at": d.created_at,
            }
            for d in docs
        ],
    }


@router.put("/{staff_profile_id}")
def update_staff(
    staff_profile_id: int,
    payload: StaffUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    user = db.query(User).filter(User.id == profile.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.email is not None:
        user.email = payload.email
    if payload.mobile is not None:
        user.phone = payload.mobile
    if payload.role is not None:
        if payload.role not in STAFF_ROLE_CHOICES:
            raise HTTPException(status_code=400, detail="role must be one of Technician, Receptionist, Lab Assistant, Radiologist")
        user.role = payload.role

    for field in [
        "address",
        "emergency_contact",
        "department",
        "specialization",
        "joined_date",
        "shift_timing",
        "reporting_manager_id",
    ]:
        value = getattr(payload, field)
        if value is not None:
            if field == "joined_date":
                profile.date_of_joining = value
            elif field == "shift_timing":
                profile.shift_timings = value
            else:
                setattr(profile, field, value)

    if payload.status:
        profile.status = DirectorStaffStatus(payload.status)
        profile.is_active = payload.status == "active"
        user.is_active = profile.is_active

    db.commit()
    return {"message": "Staff profile updated"}


@router.delete("/{staff_profile_id}")
def deactivate_staff(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    user = db.query(User).filter(User.id == profile.user_id).first()
    profile.status = DirectorStaffStatus.INACTIVE
    profile.is_active = False
    if user:
        user.is_active = False

    db.commit()
    return {"message": "Staff deactivated"}


@router.post("/{staff_profile_id}/photo")
def upload_staff_photo(
    staff_profile_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    profile.photo_path = _save_uploaded_file(file, "staff_photos")
    db.commit()
    return {"photo_path": profile.photo_path}


@router.put("/{staff_profile_id}/credentials")
def update_staff_credentials(
    staff_profile_id: int,
    payload: StaffCredentialsUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    user = db.query(User).filter(User.id == profile.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    next_username = (payload.username or "").strip()
    if next_username and next_username != user.username:
        exists = db.query(User).filter(User.username == next_username, User.id != user.id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = next_username

    generated_password = None
    if payload.auto_generate_password:
        generated_password = _generate_temp_password()
        user.hashed_password = hash_password(generated_password)
    elif payload.password:
        user.hashed_password = hash_password(payload.password)

    if not next_username and not payload.password and not payload.auto_generate_password:
        raise HTTPException(status_code=400, detail="Provide username and/or password update")

    db.commit()

    return {
        "message": "Staff credentials updated",
        "credentials": {
            "username": user.username,
            "password": generated_password,
        },
    }


@router.get("/{staff_profile_id}/salary")
def get_salary(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == staff_profile_id).first()
    if not salary:
        salary = StaffSalaryDetail(staff_profile_id=staff_profile_id, basic=0, hra=0, allowances=0, deductions=0, net_pay=0)
        db.add(salary)
        db.commit()
        db.refresh(salary)

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


@router.put("/{staff_profile_id}/salary")
def upsert_salary(
    staff_profile_id: int,
    payload: SalaryUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == staff_profile_id).first()
    if not salary:
        salary = StaffSalaryDetail(staff_profile_id=staff_profile_id)
        db.add(salary)

    month = payload.month or datetime.utcnow().month
    year = payload.year or datetime.utcnow().year

    salary.basic = payload.basic
    salary.hra = payload.hra
    salary.allowances = payload.allowances
    salary.deductions = payload.deductions
    salary.net_pay = payload.basic + payload.hra + payload.allowances - payload.deductions
    salary.bank_name = payload.bank_name
    salary.account_number = payload.account_number
    salary.ifsc_code = payload.ifsc_code
    salary.upi_id = payload.upi_id

    db.add(StaffSalaryRecord(
        staff_profile_id=staff_profile_id,
        branch_id=profile.branch_id,
        month=month,
        year=year,
        basic_salary=payload.basic,
        hra=payload.hra,
        allowances=payload.allowances,
        deductions=payload.deductions,
        net_pay=salary.net_pay,
        generated_by=current_user.id,
    ))

    db.commit()
    return {"message": "Salary details saved", "net_pay": float(salary.net_pay or 0)}


@router.get("/{staff_profile_id}/salary-records")
def list_salary_records(
    staff_profile_id: int,
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    q = db.query(StaffSalaryRecord).filter(StaffSalaryRecord.staff_profile_id == staff_profile_id)
    if month:
        q = q.filter(StaffSalaryRecord.month == month)
    if year:
        q = q.filter(StaffSalaryRecord.year == year)

    rows = q.order_by(StaffSalaryRecord.generated_at.desc()).all()
    return [
        {
            "id": row.id,
            "month": row.month,
            "year": row.year,
            "basic_salary": float(row.basic_salary or 0),
            "hra": float(row.hra or 0),
            "allowances": float(row.allowances or 0),
            "deductions": float(row.deductions or 0),
            "net_pay": float(row.net_pay or 0),
            "generated_at": row.generated_at,
        }
        for row in rows
    ]


@router.post("/{staff_profile_id}/attendance/clock")
def attendance_clock(
    staff_profile_id: int,
    action: str = Form(...),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    if current_user.role == "staff" and current_user.id != profile.user_id:
        raise HTTPException(status_code=403, detail="Staff can mark own attendance only")

    today = date.today()
    day_start = datetime.combine(today, datetime.min.time())
    day_end = datetime.combine(today, datetime.max.time())

    record = db.query(StaffAttendanceLog).filter(
        StaffAttendanceLog.staff_profile_id == staff_profile_id,
        StaffAttendanceLog.attendance_date >= day_start,
        StaffAttendanceLog.attendance_date <= day_end,
    ).first()

    now = datetime.utcnow()
    photo_path = _save_uploaded_file(photo, "attendance_selfies") if photo else None

    if action == "in":
        if not record:
            record = StaffAttendanceLog(
                staff_profile_id=staff_profile_id,
                branch_id=profile.branch_id,
                attendance_date=now,
                attendance_type=DirectorAttendanceType.PRESENT,
            )
            db.add(record)

        record.clock_in_time = now
        record.clock_in_latitude = latitude
        record.clock_in_longitude = longitude
        if photo_path:
            record.clock_in_photo_path = photo_path

    elif action == "out":
        if not record:
            raise HTTPException(status_code=400, detail="Clock-in is required before clock-out")

        record.clock_out_time = now
        record.clock_out_latitude = latitude
        record.clock_out_longitude = longitude
        if photo_path:
            record.clock_out_photo_path = photo_path
    else:
        raise HTTPException(status_code=400, detail="Action must be 'in' or 'out'")

    _ensure_director_notification(
        db,
        branch_id=profile.branch_id,
        title="Attendance Event",
        message=f"{profile.staff_id} clocked {action} at {now.strftime('%H:%M')}.",
    )

    db.commit()
    return {
        "message": f"Clock {action} captured",
        "record_id": record.id,
        "clock_in_time": record.clock_in_time,
        "clock_out_time": record.clock_out_time,
    }


@router.get("/{staff_profile_id}/attendance/monthly")
def monthly_attendance(
    staff_profile_id: int,
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    if current_user.role == "staff" and current_user.id != profile.user_id:
        raise HTTPException(status_code=403, detail="Staff can only view own attendance")

    start = datetime(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end = datetime(year, month, last_day, 23, 59, 59)

    logs = db.query(StaffAttendanceLog).filter(
        StaffAttendanceLog.staff_profile_id == staff_profile_id,
        StaffAttendanceLog.attendance_date >= start,
        StaffAttendanceLog.attendance_date <= end,
    ).all()

    leaves = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.staff_profile_id == staff_profile_id,
        StaffLeaveRequest.status == LeaveStatus.APPROVED,
        StaffLeaveRequest.start_date <= end,
        StaffLeaveRequest.end_date >= start,
    ).all()

    log_map = {l.attendance_date.date().isoformat(): l for l in logs}
    leave_dates = set()
    for leave in leaves:
        curr = leave.start_date.date()
        while curr <= leave.end_date.date():
            leave_dates.add(curr.isoformat())
            curr += timedelta(days=1)

    rows = []
    for day_num in range(1, last_day + 1):
        current_day = date(year, month, day_num)
        key = current_day.isoformat()
        if key in log_map:
            status = log_map[key].attendance_type.value
            clock_in = log_map[key].clock_in_time
            clock_out = log_map[key].clock_out_time
        elif key in leave_dates:
            status = "leave"
            clock_in = None
            clock_out = None
        elif current_day.weekday() == 6:
            status = "holiday"
            clock_in = None
            clock_out = None
        else:
            status = "absent"
            clock_in = None
            clock_out = None

        rows.append({
            "date": key,
            "status": status,
            "clock_in_time": clock_in,
            "clock_out_time": clock_out,
        })

    return rows


@router.post("/leave/apply")
def apply_leave(
    payload: LeaveApplyPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    if current_user.role == "staff":
        profile = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Staff profile missing")
    else:
        if not payload.staff_profile_id:
            raise HTTPException(status_code=400, detail="staff_profile_id is required")
        profile = db.query(StaffProfile).filter(StaffProfile.id == payload.staff_profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Staff not found")

    _assert_branch_access(current_user, profile.branch_id)

    total_days = (payload.end_date.date() - payload.start_date.date()).days + 1
    if total_days <= 0:
        raise HTTPException(status_code=400, detail="Invalid leave date range")

    leave = StaffLeaveRequest(
        staff_profile_id=profile.id,
        branch_id=profile.branch_id,
        leave_type=payload.leave_type.lower(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        total_days=total_days,
        reason=payload.reason,
        status=LeaveStatus.PENDING,
    )
    db.add(leave)

    _ensure_director_notification(
        db,
        branch_id=profile.branch_id,
        title="New Leave Request",
        message=f"{profile.staff_id} requested {payload.leave_type} leave.",
    )

    db.commit()
    return {"message": "Leave request submitted", "request_id": leave.id}


@router.get("/leave/requests")
def list_leave_requests(
    branch_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)
    target_branch_id = current_user.branch_id
    if not target_branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment missing")
    if branch_id is not None and branch_id != target_branch_id:
        raise HTTPException(status_code=403, detail="Access denied for this branch")

    query = db.query(StaffLeaveRequest, StaffProfile).join(
        StaffProfile,
        StaffLeaveRequest.staff_profile_id == StaffProfile.id,
    ).filter(StaffLeaveRequest.branch_id == target_branch_id)

    if status:
        query = query.filter(StaffLeaveRequest.status == LeaveStatus(status.lower()))

    rows = query.order_by(StaffLeaveRequest.created_at.desc()).all()
    return [
        {
            "id": req.id,
            "staff_profile_id": req.staff_profile_id,
            "staff_id": profile.staff_id,
            "leave_type": req.leave_type,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "total_days": req.total_days,
            "reason": req.reason,
            "status": req.status.value,
            "created_at": req.created_at,
        }
        for req, profile in rows
    ]


@router.put("/leave/requests/{leave_request_id}/decision")
def decide_leave(
    leave_request_id: int,
    payload: LeaveDecisionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    req = db.query(StaffLeaveRequest).filter(StaffLeaveRequest.id == leave_request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")

    _assert_branch_access(current_user, req.branch_id)

    req.status = LeaveStatus.APPROVED if payload.status == "approved" else LeaveStatus.REJECTED
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.utcnow()
    req.review_comment = payload.review_comment

    db.commit()
    return {"message": "Leave status updated", "status": req.status.value}


@router.get("/leave/balance/{staff_profile_id}")
def leave_balance(
    staff_profile_id: int,
    year: int = Query(default=datetime.utcnow().year),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")

    _assert_branch_access(current_user, profile.branch_id)

    if current_user.role == "staff" and current_user.id != profile.user_id:
        raise HTTPException(status_code=403, detail="Staff can only view own leave balance")

    quota = {"casual": 12, "sick": 12, "earned": 15, "unpaid": 999}
    used = {k: 0 for k in quota}
    pending = {k: 0 for k in quota}

    approved_rows = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.staff_profile_id == staff_profile_id,
        StaffLeaveRequest.status == LeaveStatus.APPROVED,
        StaffLeaveRequest.start_date >= datetime(year, 1, 1),
        StaffLeaveRequest.end_date <= datetime(year, 12, 31, 23, 59, 59),
    ).all()
    for row in approved_rows:
        key = row.leave_type.lower()
        if key in used:
            used[key] += row.total_days

    pending_rows = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.staff_profile_id == staff_profile_id,
        StaffLeaveRequest.status == LeaveStatus.PENDING,
        StaffLeaveRequest.start_date >= datetime(year, 1, 1),
        StaffLeaveRequest.end_date <= datetime(year, 12, 31, 23, 59, 59),
    ).all()
    for row in pending_rows:
        key = row.leave_type.lower()
        if key in pending:
            pending[key] += row.total_days

    return [
        {
            "leave_type": leave_type,
            "quota": quota[leave_type],
            "used": used[leave_type],
            "pending": pending[leave_type],
            "remaining": quota[leave_type] - used[leave_type],
        }
        for leave_type in quota
    ]


@router.post("/{staff_profile_id}/performance-notes")
def add_performance_note(
    staff_profile_id: int,
    payload: PerformanceNotePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")

    _assert_branch_access(current_user, profile.branch_id)

    row = StaffPerformanceNote(
        staff_profile_id=staff_profile_id,
        director_user_id=current_user.id,
        note=payload.note,
    )
    db.add(row)
    db.commit()
    return {"message": "Performance note added"}


@router.get("/{staff_profile_id}/performance-notes")
def list_performance_notes(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")

    _assert_branch_access(current_user, profile.branch_id)

    rows = db.query(StaffPerformanceNote).filter(
        StaffPerformanceNote.staff_profile_id == staff_profile_id
    ).order_by(StaffPerformanceNote.created_at.desc()).all()

    return [
        {
            "id": row.id,
            "note": row.note,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("/{staff_profile_id}/documents")
def upload_staff_document(
    staff_profile_id: int,
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")

    _assert_branch_access(current_user, profile.branch_id)

    rel_path = _save_uploaded_file(file, "staff_documents")
    row = StaffDocument(
        staff_profile_id=staff_profile_id,
        uploaded_by=current_user.id,
        file_name=file.filename or "document",
        file_path=rel_path,
        document_type=document_type,
    )
    db.add(row)
    db.commit()
    return {"message": "Document uploaded", "document_id": row.id, "file_path": rel_path}


@router.get("/{staff_profile_id}/documents")
def list_staff_documents(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")

    _assert_branch_access(current_user, profile.branch_id)

    rows = db.query(StaffDocument).filter(
        StaffDocument.staff_profile_id == staff_profile_id
    ).order_by(StaffDocument.created_at.desc()).all()

    return [
        {
            "id": row.id,
            "file_name": row.file_name,
            "file_path": row.file_path,
            "document_type": row.document_type,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/reports/attendance/csv")
def export_attendance_csv(
    branch_id: Optional[int] = Query(None),
    staff_profile_id: Optional[int] = Query(None),
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    target_branch_id = current_user.branch_id
    if not target_branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment missing")
    if branch_id is not None and branch_id != target_branch_id:
        raise HTTPException(status_code=403, detail="Access denied for this branch")

    start = datetime(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end = datetime(year, month, last_day, 23, 59, 59)

    query = db.query(StaffAttendanceLog, StaffProfile, User).join(
        StaffProfile, StaffAttendanceLog.staff_profile_id == StaffProfile.id
    ).join(User, StaffProfile.user_id == User.id).filter(
        StaffAttendanceLog.branch_id == target_branch_id,
        StaffAttendanceLog.attendance_date >= start,
        StaffAttendanceLog.attendance_date <= end,
    )

    if staff_profile_id:
        query = query.filter(StaffAttendanceLog.staff_profile_id == staff_profile_id)

    rows = query.order_by(StaffAttendanceLog.attendance_date.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "staff_id",
        "name",
        "date",
        "status",
        "clock_in",
        "clock_out",
        "clock_in_latitude",
        "clock_in_longitude",
        "clock_out_latitude",
        "clock_out_longitude",
    ])

    for log, profile, user in rows:
        writer.writerow([
            profile.staff_id,
            f"{user.first_name} {user.last_name}",
            log.attendance_date.date().isoformat(),
            log.attendance_type.value,
            log.clock_in_time.isoformat() if log.clock_in_time else "",
            log.clock_out_time.isoformat() if log.clock_out_time else "",
            log.clock_in_latitude or "",
            log.clock_in_longitude or "",
            log.clock_out_latitude or "",
            log.clock_out_longitude or "",
        ])

    output.seek(0)
    filename = f"attendance_{year}_{month:02d}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{staff_profile_id}/performance/metrics")
def performance_metrics(
    staff_profile_id: int,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    start = datetime(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end = datetime(year, month, last_day, 23, 59, 59)

    rows = db.query(
        func.date(DailyEntryModule.created_at).label("entry_date"),
        func.count(DailyEntryModule.id).label("tests_completed"),
    ).filter(
        DailyEntryModule.branch_id == profile.branch_id,
        DailyEntryModule.created_by == profile.user_id,
        DailyEntryModule.created_at >= start,
        DailyEntryModule.created_at <= end,
    ).group_by(func.date(DailyEntryModule.created_at)).order_by(func.date(DailyEntryModule.created_at)).all()

    daily = [
        {
            "date": str(row.entry_date),
            "tests_completed": int(row.tests_completed or 0),
        }
        for row in rows
    ]

    total_tests = sum(item["tests_completed"] for item in daily)
    active_days = len(daily)
    avg_per_day = round(total_tests / active_days, 2) if active_days else 0

    return {
        "month": month,
        "year": year,
        "total_tests": total_tests,
        "active_days": active_days,
        "average_tests_per_active_day": avg_per_day,
        "daily": daily,
    }


@router.post("/{staff_profile_id}/roster")
def upsert_weekly_roster(
    staff_profile_id: int,
    payload: WeeklyRosterPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    existing = db.query(StaffWeeklyRoster).filter(
        StaffWeeklyRoster.staff_profile_id == staff_profile_id,
        StaffWeeklyRoster.week_start_date == payload.week_start_date,
        StaffWeeklyRoster.week_end_date == payload.week_end_date,
    ).first()

    schedule_json = json.dumps(payload.schedule)
    if existing:
        existing.schedule_json = schedule_json
        existing.notes = payload.notes
    else:
        db.add(StaffWeeklyRoster(
            staff_profile_id=staff_profile_id,
            branch_id=profile.branch_id,
            week_start_date=payload.week_start_date,
            week_end_date=payload.week_end_date,
            schedule_json=schedule_json,
            notes=payload.notes,
            created_by=current_user.id,
        ))

    db.commit()
    return {"message": "Weekly roster saved"}


@router.get("/{staff_profile_id}/roster")
def list_weekly_roster(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    rows = db.query(StaffWeeklyRoster).filter(
        StaffWeeklyRoster.staff_profile_id == staff_profile_id
    ).order_by(StaffWeeklyRoster.week_start_date.desc()).all()

    return [
        {
            "id": row.id,
            "week_start_date": row.week_start_date,
            "week_end_date": row.week_end_date,
            "schedule": json.loads(row.schedule_json or "{}"),
            "notes": row.notes,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/notifications")
def list_director_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    q = db.query(DirectorNotification).filter(
        DirectorNotification.branch_id == current_user.branch_id,
        DirectorNotification.director_user_id == current_user.id,
    )
    if unread_only:
        q = q.filter(DirectorNotification.is_read.is_(False))

    rows = q.order_by(DirectorNotification.created_at.desc()).limit(100).all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "message": row.message,
            "is_read": row.is_read,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_staff_scope(current_user)

    row = db.query(DirectorNotification).filter(
        DirectorNotification.id == notification_id,
        DirectorNotification.director_user_id == current_user.id,
        DirectorNotification.branch_id == current_user.branch_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")

    row.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}
