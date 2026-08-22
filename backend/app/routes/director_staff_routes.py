from datetime import datetime, date, timedelta
import calendar
import csv
import io
import secrets
import string
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, text

from app.database import get_db
from app.models import User, Branch
from app.models.hr import (
    BranchNotification,
    BranchNotificationType,
    DirectorProfile,
    StaffProfile,
    StaffSalaryDetail,
    StaffAttendanceLog,
    StaffLeaveRequest,
    StaffPerformanceNote,
    StaffDocument,
    DirectorNotification,
    DirectorStaffStatus,
    DirectorAttendanceType,
    StaffAttendanceStatus,
    LeaveStatus,
    StaffNotification,
)
from app.utils.auth_system import get_current_user, auth_guard
from app.utils.security import hash_password


router = APIRouter()
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "@#_-"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _assert_branch_access(current_user: User, branch_id: int) -> None:
    if current_user.role == "super_admin":
        return
    if current_user.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied for this branch")


def _get_director_for_branch(db: Session, branch_id: int) -> Optional[User]:
    return db.query(User).filter(
        User.branch_id == branch_id,
        User.role == "branch_director",
        User.is_active.is_(True),
    ).first()


def _ensure_director_or_admin(current_user: User) -> None:
    if current_user.role not in ["branch_director", "branch_admin", "super_admin", "staff"]:
        raise HTTPException(status_code=403, detail="Access denied")


def _save_uploaded_file(upload: UploadFile, folder_name: str) -> str:
    target_dir = UPLOADS_DIR / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(upload.filename or "file").suffix
    generated_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(6)}{ext}"
    target_path = target_dir / generated_name
    with target_path.open("wb") as handle:
        handle.write(upload.file.read())
    return str(target_path.relative_to(UPLOADS_DIR))


def _uploaded_file_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    raw = path.strip()
    if not raw:
        return None
    if raw.startswith("/api/files/"):
        return raw
    if raw.startswith("/"):
        return f"/api/files/{raw.lstrip('/')}"
    return f"/api/files/{raw}"


def _leave_quota() -> dict:
    return {"casual": 12, "sick": 12, "earned": 15, "unpaid": 999}


def _ensure_branch_notifications_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS branch_notifications (
                id INTEGER PRIMARY KEY,
                branch_id INTEGER NOT NULL,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                related_entity_id INTEGER,
                is_read BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_branch_notifications_branch_id ON branch_notifications(branch_id)"))


class DirectorCreatePayload(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    mobile: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = None
    designation: Optional[str] = "Branch Director"
    address: Optional[str] = None
    date_of_joining: Optional[datetime] = None
    specialization: Optional[str] = None
    emergency_contact: Optional[str] = None


class DirectorProfileUpdatePayload(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    designation: Optional[str] = None
    address: Optional[str] = None
    date_of_joining: Optional[datetime] = None
    specialization: Optional[str] = None
    emergency_contact: Optional[str] = None


class StaffCreatePayload(BaseModel):
    first_name: str
    last_name: str
    email: str
    mobile: str
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    role: str = Field(default="staff")
    department: Optional[str] = None
    specialization: Optional[str] = None
    date_of_joining: Optional[datetime] = None
    shift_timings: Optional[str] = None
    reporting_manager_id: Optional[int] = None
    temporary_password: Optional[str] = None
    auto_generate_password: bool = True


class StaffUpdatePayload(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    department: Optional[str] = None
    specialization: Optional[str] = None
    date_of_joining: Optional[datetime] = None
    shift_timings: Optional[str] = None
    reporting_manager_id: Optional[int] = None
    status: Optional[str] = None


class SalaryUpdatePayload(BaseModel):
    basic: float = 0
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


@router.post("/directors/create")
def create_branch_director(
    payload: DirectorCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only branch admin can create branch director")

    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment required")

    existing_director = _get_director_for_branch(db, current_user.branch_id)
    if existing_director:
        raise HTTPException(status_code=400, detail="Branch director already exists for this branch")

    branch = db.query(Branch).filter(Branch.id == current_user.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    username = f"director_{branch.branch_code.lower()}_{secrets.token_hex(2)}"
    email = payload.email or f"{username}@vaidyavihar.com"
    raw_password = _generate_temp_password()

    if db.query(User).filter(or_(User.username == username, User.email == email)).first():
        username = f"{username}_{secrets.token_hex(2)}"
        email = f"{username}@vaidyavihar.com"

    director_user = User(
        username=username,
        email=email,
        hashed_password=hash_password(raw_password),
        role="branch_director",
        branch_id=current_user.branch_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.mobile,
        is_active=True,
    )
    db.add(director_user)
    db.flush()

    profile = DirectorProfile(
        user_id=director_user.id,
        branch_id=current_user.branch_id,
        designation=payload.designation,
        mobile=payload.mobile,
        address=payload.address,
        date_of_joining=payload.date_of_joining,
        specialization=payload.specialization,
        emergency_contact=payload.emergency_contact,
    )
    db.add(profile)
    db.commit()

    return {
        "message": "Branch director created successfully",
        "credentials": {
            "username": username,
            "password": raw_password,
            "role": "branch_director",
        },
        "director": {
            "user_id": director_user.id,
            "name": f"{director_user.first_name} {director_user.last_name}",
            "branch_id": current_user.branch_id,
        },
    }


@router.get("/profile")
def get_director_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_director_or_admin(current_user)

    if current_user.role == "branch_director":
        target_user = current_user
    else:
        if not current_user.branch_id:
            raise HTTPException(status_code=400, detail="No branch associated")
        target_user = _get_director_for_branch(db, current_user.branch_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="Director profile not found")

    profile = db.query(DirectorProfile).filter(DirectorProfile.user_id == target_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Director profile not found")

    return {
        "user_id": target_user.id,
        "photo_path": profile.photo_path,
        "full_name": f"{target_user.first_name} {target_user.last_name}",
        "designation": profile.designation,
        "mobile": profile.mobile or target_user.phone,
        "email": target_user.email,
        "address": profile.address,
        "date_of_joining": profile.date_of_joining,
        "specialization": profile.specialization,
        "emergency_contact": profile.emergency_contact,
        "role": target_user.role,
        "branch_id": target_user.branch_id,
    }


@router.put("/profile")
def update_director_profile(
    payload: DirectorProfileUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_director_or_admin(current_user)

    if current_user.role == "branch_director":
        target_user = current_user
    else:
        target_user = _get_director_for_branch(db, current_user.branch_id or 0)
        if not target_user:
            raise HTTPException(status_code=404, detail="Director profile not found")

    profile = db.query(DirectorProfile).filter(DirectorProfile.user_id == target_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Director profile not found")

    if payload.first_name is not None:
        target_user.first_name = payload.first_name
    if payload.last_name is not None:
        target_user.last_name = payload.last_name
    if payload.email is not None:
        target_user.email = payload.email
    if payload.mobile is not None:
        target_user.phone = payload.mobile
        profile.mobile = payload.mobile

    for key in ["designation", "address", "date_of_joining", "specialization", "emergency_contact"]:
        value = getattr(payload, key)
        if value is not None:
            setattr(profile, key, value)

    db.commit()
    return {"message": "Director profile updated successfully"}


@router.post("/profile/photo")
def upload_director_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_director_or_admin(current_user)

    if current_user.role == "branch_director":
        target_user = current_user
    else:
        target_user = _get_director_for_branch(db, current_user.branch_id or 0)
        if not target_user:
            raise HTTPException(status_code=404, detail="Director not found")

    profile = db.query(DirectorProfile).filter(DirectorProfile.user_id == target_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Director profile not found")

    profile.photo_path = _save_uploaded_file(file, "director_photos")
    db.commit()
    return {"photo_path": profile.photo_path}


@router.post("/staff")
def create_staff_member(
    payload: StaffCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "branch_director":
        raise HTTPException(status_code=403, detail="Only branch director can add staff")
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment missing")

    same_email = db.query(User).filter(User.email == payload.email).first()
    if same_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    seq = db.query(StaffProfile).filter(StaffProfile.branch_id == current_user.branch_id).count() + 1
    staff_id = f"ST{current_user.branch_id:03d}{seq:04d}"
    while db.query(StaffProfile).filter(StaffProfile.staff_id == staff_id).first():
        seq += 1
        staff_id = f"ST{current_user.branch_id:03d}{seq:04d}"

    username = f"{payload.first_name.lower()}.{payload.last_name.lower()}.{secrets.token_hex(2)}"
    temp_password = payload.temporary_password if payload.temporary_password else _generate_temp_password()

    user = User(
        username=username,
        email=payload.email,
        hashed_password=hash_password(temp_password),
        role="staff",
        branch_id=current_user.branch_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.mobile,
        is_active=True,
    )
    db.add(user)
    db.flush()

    profile = StaffProfile(
        user_id=user.id,
        branch_id=current_user.branch_id,
        created_by=current_user.id,
        staff_id=staff_id,
        department=payload.department,
        specialization=payload.specialization,
        shift_timings=payload.shift_timings,
        reporting_manager_id=payload.reporting_manager_id,
        date_of_joining=payload.date_of_joining,
        address=payload.address,
        emergency_contact=payload.emergency_contact,
        status=DirectorStaffStatus.ACTIVE,
        is_active=True,
    )
    db.add(profile)
    db.flush()

    salary = StaffSalaryDetail(staff_profile_id=profile.id, basic=0, allowances=0, deductions=0, net_pay=0)
    db.add(salary)

    _ensure_branch_notifications_table(db)
    role_label = (
        (payload.role or "").strip()
        or (payload.specialization or "").strip()
        or "Staff"
    )
    db.add(
        BranchNotification(
            branch_id=current_user.branch_id,
            type=BranchNotificationType.SYSTEM_ALERT,
            title="New Staff Joined",
            message=f"{user.first_name} {user.last_name} joined as {role_label}.",
            related_entity_id=profile.id,
            is_read=False,
        )
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
        },
        "credentials": {
            "username": user.username,
            "password": temp_password,
            "role": user.role,
        },
    }


@router.get("/staff")
def list_staff(
    role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    show_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_director_or_admin(current_user)
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment missing")

    query = db.query(StaffProfile, User).join(User, StaffProfile.user_id == User.id).filter(
        StaffProfile.branch_id == current_user.branch_id
    )

    # Filter out inactive staff unless explicitly requested
    if not show_inactive:
        query = query.filter(StaffProfile.is_active.is_(True))

    if role:
        query = query.filter(User.role == role)
    if department:
        query = query.filter(StaffProfile.department == department)
    if status:
        try:
            query = query.filter(StaffProfile.status == DirectorStaffStatus(status))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid status filter")
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
            "staff_id": sp.staff_id,
            "name": f"{u.first_name} {u.last_name}",
            "email": u.email,
            "mobile": u.phone,
            "role": u.role,
            "department": sp.department,
            "specialization": sp.specialization,
            "date_of_joining": sp.date_of_joining,
            "shift_timings": sp.shift_timings,
            "status": sp.status.value,
            "is_active": sp.is_active,
        }
        for sp, u in rows
    ]


@router.get("/staff/{staff_profile_id}")
def get_staff_profile(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_director_or_admin(current_user)

    row = db.query(StaffProfile, User).join(User, StaffProfile.user_id == User.id).filter(StaffProfile.id == staff_profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Staff not found")

    profile, user = row
    _assert_branch_access(current_user, profile.branch_id)

    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == profile.id).first()
    docs = db.query(StaffDocument).filter(StaffDocument.staff_profile_id == profile.id).order_by(StaffDocument.created_at.desc()).all()

    return {
        "id": profile.id,
        "user_id": user.id,
        "staff_id": profile.staff_id,
        "photo_path": profile.photo_path,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "mobile": user.phone,
        "address": profile.address,
        "emergency_contact": profile.emergency_contact,
        "role": user.role,
        "specialization": profile.specialization,
        "department": profile.department,
        "date_of_joining": profile.date_of_joining,
        "shift_timings": profile.shift_timings,
        "reporting_manager_id": profile.reporting_manager_id,
        "status": profile.status.value,
        "salary": {
            "basic": float(salary.basic or 0) if salary else 0,
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


@router.put("/staff/{staff_profile_id}")
def update_staff_profile(
    staff_profile_id: int,
    payload: StaffUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_director_or_admin(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    user = db.query(User).filter(User.id == profile.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for key in ["first_name", "last_name", "email", "mobile"]:
        value = getattr(payload, key)
        if value is not None:
            if key == "mobile":
                user.phone = value
            else:
                setattr(user, key, value)

    for key in ["address", "emergency_contact", "department", "specialization", "date_of_joining", "shift_timings", "reporting_manager_id"]:
        value = getattr(payload, key)
        if value is not None:
            setattr(profile, key, value)

    if payload.status:
        profile.status = DirectorStaffStatus(payload.status)
        profile.is_active = payload.status == "active"
        user.is_active = profile.is_active

    db.commit()
    return {"message": "Staff profile updated"}


@router.delete("/staff/{staff_profile_id}")
def deactivate_staff(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["branch_director", "branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

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
    return {"message": "Staff deactivated successfully"}


@router.post("/staff/{staff_profile_id}/photo")
def upload_staff_photo(
    staff_profile_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["branch_director", "branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    profile.photo_path = _save_uploaded_file(file, "staff_photos")
    db.commit()
    return {"photo_url": _uploaded_file_url(profile.photo_path)}


@router.get("/staff/{staff_profile_id}/salary")
def get_staff_salary(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "branch_director":
        raise HTTPException(status_code=403, detail="Only branch director can view salary bank details")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == staff_profile_id).first()
    if not salary:
        salary = StaffSalaryDetail(staff_profile_id=staff_profile_id, basic=0, allowances=0, deductions=0, net_pay=0)
        db.add(salary)
        db.commit()
        db.refresh(salary)

    return {
        "basic": float(salary.basic or 0),
        "allowances": float(salary.allowances or 0),
        "deductions": float(salary.deductions or 0),
        "net_pay": float(salary.net_pay or 0),
        "bank_name": salary.bank_name,
        "account_number": salary.account_number,
        "ifsc_code": salary.ifsc_code,
        "upi_id": salary.upi_id,
    }


@router.put("/staff/{staff_profile_id}/salary")
def upsert_staff_salary(
    staff_profile_id: int,
    payload: SalaryUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "branch_director":
        raise HTTPException(status_code=403, detail="Only branch director can manage salary details")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == staff_profile_id).first()
    if not salary:
        salary = StaffSalaryDetail(staff_profile_id=staff_profile_id)
        db.add(salary)

    salary.basic = payload.basic
    salary.allowances = payload.allowances
    salary.deductions = payload.deductions
    salary.net_pay = payload.basic + payload.allowances - payload.deductions
    salary.bank_name = payload.bank_name
    salary.account_number = payload.account_number
    salary.ifsc_code = payload.ifsc_code
    salary.upi_id = payload.upi_id

    db.commit()
    return {"message": "Salary details saved", "net_pay": float(salary.net_pay or 0)}


@router.post("/staff/{staff_profile_id}/attendance/clock")
def clock_attendance(
    staff_profile_id: int,
    action: str = Form(...),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["branch_director", "staff", "branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")

    _assert_branch_access(current_user, profile.branch_id)

    if current_user.role == "staff" and current_user.id != profile.user_id:
        raise HTTPException(status_code=403, detail="Staff can only mark own attendance")

    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())

    record = db.query(StaffAttendanceLog).filter(
        StaffAttendanceLog.staff_profile_id == staff_profile_id,
        StaffAttendanceLog.attendance_date >= start,
        StaffAttendanceLog.attendance_date <= end,
    ).first()

    if action not in ["in", "out"]:
        raise HTTPException(status_code=400, detail="Action must be 'in' or 'out'")

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
    else:
        if not record:
            raise HTTPException(status_code=400, detail="Clock in is required before clock out")
        record.clock_out_time = now
        record.clock_out_latitude = latitude
        record.clock_out_longitude = longitude
        if photo_path:
            record.clock_out_photo_path = photo_path

    db.commit()
    return {
        "message": f"Clock {action} captured",
        "record_id": record.id,
        "clock_in_time": record.clock_in_time,
        "clock_out_time": record.clock_out_time,
    }


@router.get("/staff/{staff_profile_id}/attendance/monthly")
def monthly_attendance(
    staff_profile_id: int,
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_director_or_admin(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

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

    log_map = {log.attendance_date.date().isoformat(): log for log in logs}
    leave_dates = set()
    for leave in leaves:
        day = leave.start_date.date()
        while day <= leave.end_date.date():
            leave_dates.add(day.isoformat())
            day += timedelta(days=1)

    status_label_map = {
        DirectorAttendanceType.PRESENT.value: "Present",
        DirectorAttendanceType.ABSENT.value: "Absent",
        DirectorAttendanceType.LEAVE.value: "Leave",
        DirectorAttendanceType.HOLIDAY.value: "Leave",
        StaffAttendanceStatus.PRESENT.value: "Present",
        StaffAttendanceStatus.LATE.value: "Late",
        StaffAttendanceStatus.ABSENT.value: "Absent",
        StaffAttendanceStatus.APPROVED_LEAVE.value: "Leave",
        StaffAttendanceStatus.WORK_FROM_HOME.value: "Leave",
    }

    rows = []
    for day_num in range(1, last_day + 1):
        current_day = date(year, month, day_num)
        key = current_day.isoformat()
        if key in log_map:
            log_row = log_map[key]
            status = status_label_map.get(
                getattr(log_row.attendance_type, "value", str(log_row.attendance_type)).lower(),
                status_label_map.get(getattr(log_row.status, "value", str(log_row.status)).lower(), "Present"),
            )
        elif key in leave_dates:
            status = "Leave"
        else:
            status = "Absent"

        rows.append({
            "date": key,
            "status": status,
            "clock_in_time": log_map[key].clock_in_time if key in log_map else None,
            "clock_out_time": log_map[key].clock_out_time if key in log_map else None,
            "task": log_map[key].task if key in log_map else None,
            "staff_note": log_map[key].staff_note if key in log_map else None,
            "clock_in_selfie_url": _uploaded_file_url(log_map[key].clock_in_photo_path) if key in log_map else None,
            "clock_out_selfie_url": _uploaded_file_url(log_map[key].clock_out_photo_path) if key in log_map else None,
        })

    return rows


@router.post("/leave/apply")
def apply_leave(
    payload: LeaveApplyPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_director_or_admin(current_user)

    if current_user.role == "staff":
        staff_profile = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
        if not staff_profile:
            raise HTTPException(status_code=404, detail="Staff profile missing")
    else:
        if not payload.staff_profile_id:
            raise HTTPException(status_code=400, detail="staff_profile_id is required")
        staff_profile = db.query(StaffProfile).filter(StaffProfile.id == payload.staff_profile_id).first()
        if not staff_profile:
            raise HTTPException(status_code=404, detail="Staff not found")

    _assert_branch_access(current_user, staff_profile.branch_id)

    total_days = (payload.end_date.date() - payload.start_date.date()).days + 1
    if total_days <= 0:
        raise HTTPException(status_code=400, detail="Invalid leave date range")

    request = StaffLeaveRequest(
        staff_profile_id=staff_profile.id,
        branch_id=staff_profile.branch_id,
        leave_type=payload.leave_type.lower(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        total_days=total_days,
        reason=payload.reason,
        status=LeaveStatus.PENDING,
    )
    db.add(request)

    director = _get_director_for_branch(db, staff_profile.branch_id)
    if director:
        note = DirectorNotification(
            director_user_id=director.id,
            branch_id=staff_profile.branch_id,
            title="New leave request",
            message=f"{staff_profile.staff_id} submitted {payload.leave_type} leave request.",
            is_read=False,
        )
        db.add(note)

    db.commit()
    return {"message": "Leave request submitted", "request_id": request.id}


@router.get("/leave/requests")
def list_leave_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_director_or_admin(current_user)
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment missing")

    query = db.query(StaffLeaveRequest, StaffProfile).join(
        StaffProfile, StaffLeaveRequest.staff_profile_id == StaffProfile.id
    ).filter(StaffLeaveRequest.branch_id == current_user.branch_id)

    if status:
        query = query.filter(StaffLeaveRequest.status == LeaveStatus(status.lower()))

    rows = query.order_by(StaffLeaveRequest.created_at.desc()).all()
    return [
        {
            "id": req.id,
            "staff_profile_id": req.staff_profile_id,
            "staff_id": prof.staff_id,
            "leave_type": req.leave_type,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "total_days": req.total_days,
            "reason": req.reason,
            "status": req.status.value.lower(),
            "created_at": req.created_at,
        }
        for req, prof in rows
    ]


@router.put("/leave/requests/{leave_request_id}/decision")
def decide_leave_request(
    leave_request_id: int,
    payload: LeaveDecisionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["branch_director", "branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only director/admin can approve leaves")

    req = db.query(StaffLeaveRequest).filter(StaffLeaveRequest.id == leave_request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    _assert_branch_access(current_user, req.branch_id)

    status_value = LeaveStatus.APPROVED if payload.status == "approved" else LeaveStatus.REJECTED
    req.status = status_value
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.utcnow()
    req.review_comment = payload.review_comment

    if status_value == LeaveStatus.APPROVED:
        day = req.start_date.date()
        while day <= req.end_date.date():
            start = datetime.combine(day, datetime.min.time())
            end = datetime.combine(day, datetime.max.time())
            existing = db.query(StaffAttendanceLog).filter(
                StaffAttendanceLog.staff_profile_id == req.staff_profile_id,
                StaffAttendanceLog.attendance_date >= start,
                StaffAttendanceLog.attendance_date <= end,
            ).first()
            if existing:
                existing.attendance_type = DirectorAttendanceType.LEAVE
                existing.status = StaffAttendanceStatus.APPROVED_LEAVE
            else:
                db.add(StaffAttendanceLog(
                    staff_profile_id=req.staff_profile_id,
                    branch_id=req.branch_id,
                    attendance_date=start,
                    date=day,
                    attendance_type=DirectorAttendanceType.LEAVE,
                    status=StaffAttendanceStatus.APPROVED_LEAVE,
                    task_status="Pending",
                ))
            day += timedelta(days=1)

    db.add(
        StaffNotification(
            staff_profile_id=req.staff_profile_id,
            branch_id=req.branch_id,
            message=(
                f"Leave request #{req.id} {req.status.value}."
                if not payload.review_comment
                else f"Leave request #{req.id} {req.status.value}: {payload.review_comment}"
            ),
            link="/staff/attendance",
        )
    )

    db.commit()
    return {"message": "Leave request updated", "status": req.status.value.lower()}


@router.get("/leave/balance/{staff_profile_id}")
def get_leave_balance(
    staff_profile_id: int,
    year: int = Query(default=datetime.utcnow().year),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_director_or_admin(current_user)

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    quota = _leave_quota()
    used = {k: 0 for k in quota}

    approved = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.staff_profile_id == staff_profile_id,
        StaffLeaveRequest.status == LeaveStatus.APPROVED,
        StaffLeaveRequest.start_date >= datetime(year, 1, 1),
        StaffLeaveRequest.end_date <= datetime(year, 12, 31, 23, 59, 59),
    ).all()

    pending = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.staff_profile_id == staff_profile_id,
        StaffLeaveRequest.status == LeaveStatus.PENDING,
        StaffLeaveRequest.start_date >= datetime(year, 1, 1),
        StaffLeaveRequest.end_date <= datetime(year, 12, 31, 23, 59, 59),
    ).all()

    pending_map = {k: 0 for k in quota}
    for req in approved:
        key = req.leave_type.lower()
        if key in used:
            used[key] += req.total_days

    for req in pending:
        key = req.leave_type.lower()
        if key in pending_map:
            pending_map[key] += req.total_days

    return [
        {
            "leave_type": leave_type,
            "quota": quota[leave_type],
            "used": used[leave_type],
            "pending": pending_map[leave_type],
            "remaining": quota[leave_type] - used[leave_type],
        }
        for leave_type in quota
    ]


@router.get("/dashboard/summary")
def director_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["branch_director", "branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment missing")

    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())

    staff_ids = [row.id for row in db.query(StaffProfile.id).filter(
        StaffProfile.branch_id == current_user.branch_id,
        StaffProfile.is_active.is_(True),
    ).all()]

    total_staff = len(staff_ids)
    present_today = db.query(StaffAttendanceLog).filter(
        StaffAttendanceLog.branch_id == current_user.branch_id,
        StaffAttendanceLog.attendance_date >= start,
        StaffAttendanceLog.attendance_date <= end,
        StaffAttendanceLog.attendance_type == DirectorAttendanceType.PRESENT,
    ).count()

    on_leave = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.branch_id == current_user.branch_id,
        StaffLeaveRequest.status == LeaveStatus.APPROVED,
        StaffLeaveRequest.start_date <= end,
        StaffLeaveRequest.end_date >= start,
    ).count()

    pending_leave_requests = db.query(StaffLeaveRequest).filter(
        StaffLeaveRequest.branch_id == current_user.branch_id,
        StaffLeaveRequest.status == LeaveStatus.PENDING,
    ).count()

    upcoming_birthdays = []
    upcoming_anniversaries = []

    return {
        "total_staff": total_staff,
        "present_today": present_today,
        "on_leave": on_leave,
        "pending_leave_requests": pending_leave_requests,
        "upcoming_birthdays": upcoming_birthdays,
        "upcoming_anniversaries": upcoming_anniversaries,
    }


@router.get("/notifications")
def get_notifications(
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "branch_director":
        raise HTTPException(status_code=403, detail="Only branch director can access notifications")

    query = db.query(DirectorNotification).filter(DirectorNotification.director_user_id == current_user.id)
    if unread_only:
        query = query.filter(DirectorNotification.is_read.is_(False))

    rows = query.order_by(DirectorNotification.created_at.desc()).limit(100).all()
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
    if current_user.role != "branch_director":
        raise HTTPException(status_code=403, detail="Only branch director can update notifications")

    row = db.query(DirectorNotification).filter(
        DirectorNotification.id == notification_id,
        DirectorNotification.director_user_id == current_user.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")

    row.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}


@router.post("/staff/{staff_profile_id}/performance-notes")
def create_performance_note(
    staff_profile_id: int,
    payload: PerformanceNotePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "branch_director":
        raise HTTPException(status_code=403, detail="Only branch director can add performance notes")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    note = StaffPerformanceNote(
        staff_profile_id=staff_profile_id,
        director_user_id=current_user.id,
        note=payload.note,
    )
    db.add(note)
    db.commit()
    return {"message": "Performance note added"}


@router.get("/staff/{staff_profile_id}/performance-notes")
def list_performance_notes(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "branch_director":
        raise HTTPException(status_code=403, detail="Only branch director can view performance notes")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    rows = db.query(StaffPerformanceNote).filter(
        StaffPerformanceNote.staff_profile_id == staff_profile_id,
        StaffPerformanceNote.director_user_id == current_user.id,
    ).order_by(StaffPerformanceNote.created_at.desc()).all()

    return [
        {
            "id": row.id,
            "note": row.note,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("/staff/{staff_profile_id}/documents")
def upload_staff_document(
    staff_profile_id: int,
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["branch_director", "staff", "branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    if current_user.role == "staff" and current_user.id != profile.user_id:
        raise HTTPException(status_code=403, detail="Staff can upload only own documents")

    rel_path = _save_uploaded_file(file, "staff_documents")
    doc = StaffDocument(
        staff_profile_id=staff_profile_id,
        uploaded_by=current_user.id,
        file_name=file.filename or "document",
        file_path=rel_path,
        document_type=document_type,
    )
    db.add(doc)
    db.commit()
    return {"message": "Document uploaded", "document_id": doc.id, "file_path": rel_path}


@router.get("/staff/{staff_profile_id}/documents")
def list_staff_documents(
    staff_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["branch_director", "staff", "branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff not found")
    _assert_branch_access(current_user, profile.branch_id)

    if current_user.role == "staff" and current_user.id != profile.user_id:
        raise HTTPException(status_code=403, detail="Staff can view only own documents")

    rows = db.query(StaffDocument).filter(StaffDocument.staff_profile_id == staff_profile_id).order_by(StaffDocument.created_at.desc()).all()
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


@router.get("/orders/attendance/csv")
def export_attendance_csv(
    staff_profile_id: Optional[int] = Query(None),
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["branch_director", "branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment missing")

    start = datetime(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end = datetime(year, month, last_day, 23, 59, 59)

    query = db.query(StaffAttendanceLog, StaffProfile, User).join(
        StaffProfile, StaffAttendanceLog.staff_profile_id == StaffProfile.id
    ).join(User, StaffProfile.user_id == User.id).filter(
        StaffAttendanceLog.branch_id == current_user.branch_id,
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
