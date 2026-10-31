from datetime import date, datetime, time
from pathlib import Path
import secrets
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, User
from app.models.hr import (
    AttendanceStatus,
    LeaveStatus as LeaveApprovalStatus,
    StaffAttendanceLog,
    StaffLeaveRequest,
    StaffProfile,
    StaffSalaryDetail,
    DirectorStaffStatus as StaffStatus,
)
from app.models.hr import BranchNotification, BranchNotificationType
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
from app.utils.file_utils import replace_file, storage_relative_path_from_public_url
from app.utils.onboarding_offer import run_offer_letter_workflow
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


def _photo_url(photo_path: Optional[str], request: Optional[Request] = None) -> Optional[str]:
    if not photo_path:
        return None
    if photo_path.startswith("http://") or photo_path.startswith("https://"):
        return photo_path
    if photo_path.startswith("/api/files/"):
        return photo_path
    clean_path = photo_path.lstrip("/")
    # Build the full URL using request base URL if available
    if request:
        base_url = str(request.base_url).rstrip("/")
        return f"{base_url}/api/files/{clean_path}"
    # Fallback to localhost if no request provided
    return f"http://localhost:8000/api/files/{clean_path}"


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
        "role": (getattr(profile, "role", None) or user.role),
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
            "basic": float(salary.basic or 0) if salary else 0,
            "da": 0,
            "hra": float(salary.hra or 0) if salary else 0,
            "shift_allowance": 0,
            "ot": 0,
            "incentives": float(salary.allowances or 0) if salary else 0,
            "lop": 0,
            "statutory_deductions": float(salary.deductions or 0) if salary else 0,
            "allowances": float(salary.allowances or 0) if salary else 0,
            "deductions": float(salary.deductions or 0) if salary else 0,
            "net_pay": (float(salary.basic or 0) + float(salary.hra or 0) + float(salary.allowances or 0) - float(salary.deductions or 0)) if salary else 0,
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
            .filter(StaffProfile.is_active.is_(True))
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
    try:
        # Debug logging
        print(f"\n{'='*60}")
        print(f"CREATE_STAFF_PAYLOAD: {payload}")
        print(f"AUTH_USER: ID={current_user.id}, Role={current_user.role}, Branch={current_user.branch_id}")
        print(f"{'='*60}\n")
        
        _assert_access(current_user)
        ensure_staff_daily_ops_column(db)
        
        # Validate required fields
        if not payload.first_name or not payload.first_name.strip():
            raise HTTPException(status_code=400, detail="Missing required field: first_name")
        if not payload.last_name or not payload.last_name.strip():
            raise HTTPException(status_code=400, detail="Missing required field: last_name")
        if not payload.email or not payload.email.strip():
            raise HTTPException(status_code=400, detail="Missing required field: email")
        if not payload.mobile or not payload.mobile.strip():
            raise HTTPException(status_code=400, detail="Missing required field: mobile")
        
        branch_id = current_user.branch_id
        if not branch_id:
            raise HTTPException(status_code=400, detail="Branch assignment missing for current user")

        # Check for duplicate email
        existing_email = db.query(User).filter(User.email == payload.email.strip().lower()).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists in the system")

        # Generate unique username
        username = f"staff_{secrets.token_hex(4)}"
        while db.query(User).filter(User.username == username).first():
            username = f"staff_{secrets.token_hex(4)}"

        # Generate secure password
        raw_password = payload.temporary_password or f"VV@{secrets.token_hex(4)}"
        hashed_password = hash_password(raw_password)
        
        print(f"Generated Username: {username} (password hash omitted from logs)")

        # Create User record
        user = User(
            username=username,
            email=payload.email.strip().lower(),
            hashed_password=hashed_password,
            role=(payload.designation or "technician").strip().lower(),
            branch_id=branch_id,
            is_active=True,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            phone=payload.mobile.strip(),
        )
        db.add(user)
        db.flush()
        print(f"User created: ID={user.id}, Username={username}")

        # Create StaffProfile record
        staff_id = _generate_staff_id(db, branch_id)
        profile = StaffProfile(
            user_id=user.id,
            branch_id=branch_id,
            created_by=current_user.id,
            staff_id=staff_id,
            department=payload.department.strip() if payload.department else None,
            specialization=payload.specialization.strip() if payload.specialization else None,
            shift_timings=payload.shift_timings.strip() if payload.shift_timings else None,
            date_of_joining=payload.date_of_joining,
            address=payload.address.strip() if payload.address else None,
            emergency_contact=payload.emergency_contact.strip() if payload.emergency_contact else None,
            can_access_daily_ops=bool(payload.can_access_daily_ops),
            status=StaffStatus.ACTIVE,
            is_active=True,
        )
        db.add(profile)
        db.flush()
        print(f"StaffProfile created: ID={profile.id}, Staff_ID={staff_id}")

        # Create Salary record
        salary = StaffSalaryDetail(
            staff_profile_id=profile.id,
            basic=0,
            hra=0,
            allowances=0,
            deductions=0,
            net_pay=0,
        )
        db.add(salary)

        _ensure_branch_notifications_table(db)
        role_label = (
            (payload.designation or "").strip()
            or (payload.specialization or "").strip()
            or "Staff"
        )
        db.add(
            BranchNotification(
                branch_id=branch_id,
                type=BranchNotificationType.SYSTEM_ALERT,
                title="New Staff Joined",
                message=f"{payload.first_name.strip()} {payload.last_name.strip()} joined as {role_label}.",
                related_entity_id=profile.id,
                is_read=False,
            )
        )

        db.commit()
        db.refresh(profile)
        print(f"Staff member created successfully: {profile.id}")

        onboarding_delivery = {"offer_email_sent": False, "offer_sms_sent": False}
        try:
            branch = db.query(Branch).filter(Branch.id == branch_id).first()
            delivery_result = run_offer_letter_workflow(
                user_data={
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "full_name": f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip(),
                    "email": user.email,
                    "phone": user.phone,
                    "joining_date": profile.date_of_joining.strftime("%Y-%m-%d") if profile.date_of_joining else datetime.utcnow().strftime("%Y-%m-%d"),
                    "reporting_manager": f"{(current_user.first_name or '').strip()} {(current_user.last_name or '').strip()}".strip() or current_user.username,
                    "salary": f"INR {float(salary.net_pay or 0):,.2f}",
                },
                branch_data={
                    "name": branch.name if branch else "VaidyaVihar Diagnostic",
                    "address": branch.address if branch else "",
                    "city": branch.city if branch else "",
                    "state": branch.state if branch else "",
                    "phone": branch.phone if branch else "",
                    "email": branch.email if branch else "",
                    "logo_url": getattr(branch, "logo_url", None) if branch else None,
                    "director_photo_url": getattr(branch, "director_photo_url", None) if branch else None,
                },
                role=user.role or "staff",
            )
            onboarding_delivery["offer_email_sent"] = bool(delivery_result.get("email_sent", False))
            onboarding_delivery["offer_sms_sent"] = bool(delivery_result.get("sms_sent", False))
        except Exception as onboarding_exc:
            print(f"OFFER_WORKFLOW_WARNING(staff_create): {onboarding_exc}")

        return {
            "message": "Staff created successfully",
            "temporary_password": raw_password,
            "username": username,
            "staff": _build_staff_row(profile, user, salary),
            "offer_email_sent": onboarding_delivery["offer_email_sent"],
            "offer_sms_sent": onboarding_delivery["offer_sms_sent"],
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"\nERROR in CREATE_STAFF:")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"\n")
        raise HTTPException(status_code=500, detail=f"Failed to create staff: {str(e)}")



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
    incoming_role = payload.role if payload.role is not None else payload.designation
    if incoming_role is not None:
        normalized_role = incoming_role.strip()
        if not normalized_role:
            raise HTTPException(status_code=400, detail="role/designation cannot be empty")
        user.role = normalized_role
        print(f"UPDATED ROLE TO: {normalized_role} for staff ID {staff_profile_id}")

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
    request: Request = None,
):
    _assert_access(current_user)
    branch_id = current_user.branch_id

    profile = _get_scoped_profile(db, branch_id, staff_profile_id)

    suffix = Path(file.filename or "photo").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp are allowed")

    new_photo_url = replace_file(profile.photo_path, file, "staff")
    new_photo_path = storage_relative_path_from_public_url(new_photo_url)
    if not new_photo_path:
        raise HTTPException(status_code=500, detail="Unable to store uploaded photo")

    profile.photo_path = new_photo_path
    profile.updated_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Photo uploaded",
        "photo_path": profile.photo_path,
        "photo_url": _photo_url(profile.photo_path, request),
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
            "basic": 0.0,
            "da": 0.0,
            "hra": 0.0,
            "shift_allowance": 0.0,
            "ot": 0.0,
            "incentives": 0.0,
            "lop": 0.0,
            "statutory_deductions": 0.0,
            "allowances": 0.0,
            "deductions": 0.0,
            "net_pay": 0.0,
            "bank_name": None,
            "account_number": None,
            "ifsc_code": None,
            "upi_id": None,
        }

    basic = float(salary.basic or 0)
    hra = float(salary.hra or 0)
    allowances = float(salary.allowances or 0)
    deductions = float(salary.deductions or 0)
    net_pay = basic + hra + allowances - deductions
    return {
        "basic": basic,
        "da": 0.0,
        "hra": hra,
        "shift_allowance": 0.0,
        "ot": 0.0,
        "incentives": allowances,
        "lop": 0.0,
        "statutory_deductions": deductions,
        "allowances": allowances,
        "deductions": deductions,
        "net_pay": net_pay,
        "bank_name": salary.bank_name,
        "account_number": salary.account_number,
        "ifsc_code": salary.ifsc_code,
        "upi_id": salary.upi_id,
    }


def _build_salary_response(
    salary: StaffSalaryDetail,
    *,
    da: float,
    shift_allowance: float,
    ot: float,
    incentives: float,
    lop: float,
    statutory_deductions: float,
) -> dict:
    basic = float(salary.basic or 0)
    hra = float(salary.hra or 0)
    allowances = float(salary.allowances or 0)
    deductions = float(salary.deductions or 0)
    net_pay = float(salary.net_pay or 0)
    return {
        "basic": basic,
        "da": da,
        "hra": hra,
        "shift_allowance": shift_allowance,
        "ot": ot,
        "incentives": incentives,
        "lop": lop,
        "statutory_deductions": statutory_deductions,
        "allowances": allowances,
        "deductions": deductions,
        "net_pay": net_pay,
        "bank_name": salary.bank_name,
        "account_number": salary.account_number,
        "ifsc_code": salary.ifsc_code,
        "upi_id": salary.upi_id,
    }


@staff_router.put("/{staff_profile_id}/salary")
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

    basic = float(payload.basic or 0)
    da = float(payload.da or 0)
    hra = float(payload.hra or 0)
    shift_allowance = float(payload.shift_allowance or 0)
    ot = float(payload.ot or 0)
    incentives = float(payload.incentives or 0)
    lop = float(payload.lop or 0)
    statutory_deductions = float(payload.statutory_deductions or 0)

    detailed_allowances = da + shift_allowance + ot + incentives
    detailed_deductions = lop + statutory_deductions
    if detailed_allowances == 0 and float(payload.allowances or 0) > 0:
        incentives = float(payload.allowances or 0)
        detailed_allowances = incentives
    if detailed_deductions == 0 and float(payload.deductions or 0) > 0:
        statutory_deductions = float(payload.deductions or 0)
        detailed_deductions = statutory_deductions
    allowances = detailed_allowances if detailed_allowances > 0 else float(payload.allowances or 0)
    deductions = detailed_deductions if detailed_deductions > 0 else float(payload.deductions or 0)

    gross_pay = basic + da + hra + shift_allowance + ot + incentives
    total_deductions = detailed_deductions if detailed_deductions > 0 else deductions
    computed_net_pay = gross_pay - total_deductions

    salary.basic = basic
    salary.hra = hra
    salary.allowances = allowances
    salary.deductions = deductions
    salary.net_pay = computed_net_pay
    salary.bank_name = payload.bank_name
    salary.account_number = payload.account_number
    salary.ifsc_code = payload.ifsc_code
    salary.upi_id = payload.upi_id

    db.commit()

    return {
        "message": "Salary updated",
        "salary": _build_salary_response(
            salary,
            da=da,
            shift_allowance=shift_allowance,
            ot=ot,
            incentives=incentives,
            lop=lop,
            statutory_deductions=statutory_deductions,
        ),
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
    request: Request = None,
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
            "selfie_url": _photo_url(row.clock_in_photo_path, request),
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
