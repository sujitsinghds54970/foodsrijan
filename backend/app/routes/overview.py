from datetime import datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, User
from app.models.branch_bank_details import BranchBankDetails
from app.models.hr import DirectorAttendanceType, DirectorProfile, StaffAttendanceLog, StaffProfile
from app.utils.auth_system import get_current_user, is_super_ceo_user
from app.utils.schema_compat import ensure_branch_logo_column
from app.utils.security import hash_password


router = APIRouter()


class OverviewProfileUpdatePayload(BaseModel):
    branch_id: Optional[int] = None
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    age: Optional[str] = None
    address: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    director_photo_url: Optional[str] = None


class OverviewCredentialsUpdatePayload(BaseModel):
    branch_id: Optional[int] = None
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class _OverviewScope:
    def __init__(self, branch_id: int, branch: Branch):
        self.branch_id = branch_id
        self.branch = branch


def _assert_allowed(user: User) -> None:
    if user.role not in ["branch_admin", "branch_director"] and not is_super_ceo_user(user):
        raise HTTPException(status_code=403, detail="Access denied")


def _resolve_scope(db: Session, user: User, requested_branch_id: Optional[int]) -> _OverviewScope:
    _assert_allowed(user)

    if is_super_ceo_user(user):
        if requested_branch_id is None:
            branch = db.query(Branch).order_by(Branch.id.asc()).first()
            if not branch:
                raise HTTPException(status_code=404, detail="Branch not found")
            return _OverviewScope(branch_id=branch.id, branch=branch)
        branch_id = requested_branch_id
    else:
        if user.branch_id is None:
            raise HTTPException(status_code=400, detail="Branch assignment required")
        branch_id = user.branch_id
        if requested_branch_id is not None and requested_branch_id != branch_id:
            raise HTTPException(status_code=403, detail="Access denied for this branch")

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    return _OverviewScope(branch_id=branch_id, branch=branch)


def _get_director_user(db: Session, branch_id: int) -> Optional[User]:
    # Branch admin is now treated as the branch director for this dashboard.
    branch_admin = (
        db.query(User)
        .filter(User.branch_id == branch_id, User.role == "branch_admin", User.is_active.is_(True))
        .order_by(User.id.desc())
        .first()
    )
    if branch_admin:
        return branch_admin

    return (
        db.query(User)
        .filter(User.branch_id == branch_id, User.role == "branch_director", User.is_active.is_(True))
        .order_by(User.id.desc())
        .first()
    )


@router.get("/dashboard")
def get_overview_dashboard(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope = _resolve_scope(db, current_user, branch_id)
    director_user = _get_director_user(db, scope.branch_id)

    director_profile = None
    if director_user:
        director_profile = db.query(DirectorProfile).filter(DirectorProfile.user_id == director_user.id).first()

    bank_details = db.query(BranchBankDetails).filter(BranchBankDetails.branch_id == scope.branch_id).first()

    now = datetime.utcnow()
    day_start = datetime.combine(now.date(), time.min)
    day_end = datetime.combine(now.date(), time.max)

    total_staff = (
        db.query(StaffProfile)
        .filter(StaffProfile.branch_id == scope.branch_id, StaffProfile.is_active.is_(True))
        .count()
    )
    present_staff = (
        db.query(StaffAttendanceLog)
        .filter(
            StaffAttendanceLog.branch_id == scope.branch_id,
            StaffAttendanceLog.attendance_date >= day_start,
            StaffAttendanceLog.attendance_date <= day_end,
            StaffAttendanceLog.attendance_type == DirectorAttendanceType.PRESENT,
        )
        .count()
    )

    credentials_username = (
        scope.branch.director_credentials_username
        or (director_user.username if director_user else "")
    )
    credentials_password = scope.branch.director_credentials_password or ""

    full_name = ""
    if director_user:
        full_name = f"{director_user.first_name or ''} {director_user.last_name or ''}".strip()

    return {
        "branch": {
            "id": scope.branch.id,
            "name": scope.branch.name,
            "address": scope.branch.address,
            "city": scope.branch.city,
            "state": scope.branch.state,
            "phone": scope.branch.phone,
            "email": scope.branch.email,
            "branch_code": scope.branch.branch_code,
        },
        "director": {
            "full_name": full_name,
            "mobile": (director_profile.mobile if director_profile and director_profile.mobile else (director_user.phone if director_user else "")),
            "email": (director_user.email if director_user else ""),
            "age": scope.branch.director_age or "",
            "address": (director_profile.address if director_profile and director_profile.address else scope.branch.address),
            "photo_url": scope.branch.director_photo_url or (director_profile.photo_path if director_profile else ""),
        },
        "attendance_summary": {
            "present_today": present_staff,
            "total_staff": total_staff,
            "label": f"{present_staff}/{total_staff} present today",
        },
        "bank_details": {
            "account_number": bank_details.account_number if bank_details else "",
            "ifsc_code": bank_details.ifsc_code if bank_details else "",
        },
        "credentials": {
            "username": credentials_username,
            "password": credentials_password,
        },
    }


@router.put("/profile")
def update_overview_profile(
    payload: OverviewProfileUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope = _resolve_scope(db, current_user, payload.branch_id)
    director_user = _get_director_user(db, scope.branch_id)

    if not director_user:
        raise HTTPException(status_code=404, detail="Branch director/admin user not found")

    director_profile = db.query(DirectorProfile).filter(DirectorProfile.user_id == director_user.id).first()
    if not director_profile:
        director_profile = DirectorProfile(user_id=director_user.id, branch_id=scope.branch_id)
        db.add(director_profile)
        db.flush()

    if payload.full_name is not None:
        parts = [p for p in payload.full_name.strip().split(" ") if p]
        if parts:
            director_user.first_name = parts[0]
            director_user.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    if payload.mobile is not None:
        director_user.phone = payload.mobile
        director_profile.mobile = payload.mobile

    if payload.email is not None:
        existing_email = db.query(User).filter(User.email == payload.email, User.id != director_user.id).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already in use")
        director_user.email = payload.email

    if payload.address is not None:
        director_profile.address = payload.address

    if payload.age is not None:
        scope.branch.director_age = payload.age

    if payload.director_photo_url is not None:
        scope.branch.director_photo_url = payload.director_photo_url
        ensure_branch_logo_column(db)
        db.execute(
            text("UPDATE branches SET logo_url = :logo_url WHERE id = :branch_id"),
            {"logo_url": payload.director_photo_url, "branch_id": scope.branch_id},
        )

    if payload.account_number is not None or payload.ifsc_code is not None:
        bank_details = db.query(BranchBankDetails).filter(BranchBankDetails.branch_id == scope.branch_id).first()
        if not bank_details:
            bank_details = BranchBankDetails(
                branch_id=scope.branch_id,
                account_holder_name=(payload.full_name or f"{director_user.first_name} {director_user.last_name}").strip() or scope.branch.name,
                account_number=payload.account_number or "",
                ifsc_code=payload.ifsc_code or "",
                bank_name="Not Set",
                upi_id="not-configured@upi",
                is_active=True,
            )
            db.add(bank_details)
        else:
            if payload.full_name:
                bank_details.account_holder_name = payload.full_name
            if payload.account_number is not None:
                bank_details.account_number = payload.account_number
            if payload.ifsc_code is not None:
                bank_details.ifsc_code = payload.ifsc_code

    db.commit()

    return {"message": "Overview profile updated successfully"}


@router.put("/credentials")
def update_overview_credentials(
    payload: OverviewCredentialsUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope = _resolve_scope(db, current_user, payload.branch_id)
    director_user = _get_director_user(db, scope.branch_id)

    if not director_user:
        raise HTTPException(status_code=404, detail="Branch director/admin user not found")

    existing_username = (
        db.query(User)
        .filter(func.lower(User.username) == payload.username.lower(), User.id != director_user.id)
        .first()
    )
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already in use")

    director_user.username = payload.username
    director_user.hashed_password = hash_password(payload.password)

    scope.branch.director_credentials_username = payload.username
    scope.branch.director_credentials_password = payload.password

    db.commit()

    return {"message": "Credentials updated successfully"}
