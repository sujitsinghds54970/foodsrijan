from datetime import datetime
import secrets
import string
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Branch
from app.models.hr import DirectorProfile, DirectorNotification, StaffProfile, StaffLeaveRequest, LeaveStatus
from app.utils.auth_system import get_current_user
from app.utils.security import hash_password


router = APIRouter()


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


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "@#_-"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _assert_director_scope(user: User) -> None:
    if user.role not in ["branch_director", "branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")


def _assert_branch_access(user: User, branch_id: int) -> None:
    if user.role == "super_admin":
        return
    if user.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied for this branch")


def _get_branch_director_user(db: Session, branch_id: int) -> Optional[User]:
    return db.query(User).filter(
        User.branch_id == branch_id,
        User.role == "branch_director",
        User.is_active.is_(True),
    ).first()


@router.post("/create")
def create_branch_director(
    payload: DirectorCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["branch_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only branch admin/super admin can create branch director")
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment required")

    branch = db.query(Branch).filter(Branch.id == current_user.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    existing = _get_branch_director_user(db, current_user.branch_id)
    if existing:
        raise HTTPException(status_code=400, detail="Branch director already exists")

    username = f"director_{branch.branch_code.lower()}_{secrets.token_hex(2)}"
    email = payload.email or f"{username}@vaidyavihar.com"
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        username = f"{username}_{secrets.token_hex(2)}"
        email = payload.email or f"{username}@vaidyavihar.com"

    temp_password = _generate_temp_password()

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(temp_password),
        role="branch_director",
        branch_id=current_user.branch_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.mobile,
        is_active=True,
    )
    db.add(user)
    db.flush()

    director_profile = DirectorProfile(
        user_id=user.id,
        branch_id=current_user.branch_id,
        designation=payload.designation,
        mobile=payload.mobile,
        address=payload.address,
        date_of_joining=payload.date_of_joining,
        specialization=payload.specialization,
        emergency_contact=payload.emergency_contact,
    )
    db.add(director_profile)
    db.commit()

    return {
        "message": "Branch director created successfully",
        "credentials": {
            "username": username,
            "password": temp_password,
            "role": "branch_director",
        },
        "director": {
            "user_id": user.id,
            "full_name": f"{user.first_name} {user.last_name}",
            "branch_id": user.branch_id,
            "designation": director_profile.designation,
        },
    }


@router.get("/profile")
def get_director_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    target_user: Optional[User] = None
    if current_user.role == "branch_director":
        target_user = current_user
    elif current_user.branch_id:
        target_user = _get_branch_director_user(db, current_user.branch_id)

    if not target_user:
        return {
            "exists": False,
            "message": "Director profile not found",
        }

    profile = db.query(DirectorProfile).filter(DirectorProfile.user_id == target_user.id).first()
    if not profile:
        return {
            "exists": False,
            "message": "Director profile not found",
        }

    return {
        "exists": True,
        "user_id": target_user.id,
        "branch_id": target_user.branch_id,
        "full_name": f"{target_user.first_name} {target_user.last_name}",
        "first_name": target_user.first_name,
        "last_name": target_user.last_name,
        "email": target_user.email,
        "mobile": profile.mobile or target_user.phone,
        "designation": profile.designation,
        "address": profile.address,
        "date_of_joining": profile.date_of_joining,
        "specialization": profile.specialization,
        "emergency_contact": profile.emergency_contact,
        "photo_path": profile.photo_path,
        "role": target_user.role,
    }


@router.put("/profile")
def update_director_profile(
    payload: DirectorProfileUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    target_user: Optional[User] = None
    if current_user.role == "branch_director":
        target_user = current_user
    elif current_user.branch_id:
        target_user = _get_branch_director_user(db, current_user.branch_id)

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
    _assert_director_scope(current_user)

    target_user: Optional[User] = None
    if current_user.role == "branch_director":
        target_user = current_user
    elif current_user.branch_id:
        target_user = _get_branch_director_user(db, current_user.branch_id)

    if not target_user:
        raise HTTPException(status_code=404, detail="Director not found")

    profile = db.query(DirectorProfile).filter(DirectorProfile.user_id == target_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Director profile not found")

    # Keep media serving compatible with existing file serving router.
    profile.photo_path = file.filename
    db.commit()
    return {"photo_path": profile.photo_path}


@router.get("/dashboard/summary")
def director_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_director_scope(current_user)

    if not current_user.branch_id:
        return {
            "total_staff": 0,
            "pending_leave_requests": 0,
            "approved_leave_requests": 0,
        }

    try:
        total_staff = db.query(StaffProfile).filter(
            StaffProfile.branch_id == current_user.branch_id,
            StaffProfile.is_active.is_(True),
        ).count()

        pending_leave_requests = db.query(StaffLeaveRequest).filter(
            StaffLeaveRequest.branch_id == current_user.branch_id,
            StaffLeaveRequest.status == LeaveStatus.PENDING,
        ).count()

        approved_leave_requests = db.query(StaffLeaveRequest).filter(
            StaffLeaveRequest.branch_id == current_user.branch_id,
            StaffLeaveRequest.status == LeaveStatus.APPROVED,
        ).count()
    except Exception:
        db.rollback()
        return {
            "total_staff": 0,
            "pending_leave_requests": 0,
            "approved_leave_requests": 0,
        }

    return {
        "total_staff": total_staff,
        "pending_leave_requests": pending_leave_requests,
        "approved_leave_requests": approved_leave_requests,
    }


@router.get("/notifications")
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "branch_director":
        return []

    rows = db.query(DirectorNotification).filter(
        DirectorNotification.director_user_id == current_user.id
    ).order_by(DirectorNotification.created_at.desc()).limit(100).all()

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
