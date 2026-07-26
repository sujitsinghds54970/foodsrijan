from datetime import datetime, timedelta
import secrets
import string
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, User
from app.models import Modality
from app.models.hr import BranchNotification, BranchNotificationType
from app.utils.auth_system import auth_guard, get_current_user
from app.utils.onboarding_offer import run_offer_letter_workflow
from app.utils.security import hash_password


router = APIRouter()


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


class BranchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    location: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    pincode: str = Field(..., min_length=6, max_length=10)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = Field(None, max_length=200)
    address: str = Field(..., min_length=5)
    license_number: Optional[str] = Field(None, max_length=100)
    opening_hours: Optional[str] = Field(None, max_length=500)
    facilities: Optional[str] = Field(None, max_length=1000)
    modalities: Optional[List[str]] = Field(None, description="List of modality names enabled at this branch")

    # Optional branch admin bootstrap fields
    admin_first_name: str = Field(default="Branch", max_length=100)
    admin_last_name: str = Field(default="Admin", max_length=100)
    admin_phone: Optional[str] = Field(default=None, max_length=15)


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    license_number: Optional[str] = None
    opening_hours: Optional[str] = None
    facilities: Optional[str] = None
    modalities: Optional[List[str]] = None
    is_active: Optional[bool] = None


class BranchResponse(BaseModel):
    id: int
    name: str
    location: str
    city: str
    state: str
    pincode: str
    phone: str
    email: Optional[str]
    address: str
    license_number: Optional[str]
    opening_hours: Optional[str]
    facilities: Optional[str]
    branch_code: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    total_staff: Optional[int] = 0
    total_patients: Optional[int] = 0
    monthly_revenue: Optional[float] = 0.0
    modalities: Optional[List[str]] = []

    class Config:
        from_attributes = True


class BranchAdminCredentials(BaseModel):
    username: str
    email: str
    password: str
    role: str = "branch_admin"


class BranchCreateResponse(BranchResponse):
    branch_admin_credentials: BranchAdminCredentials
    offer_email_sent: bool = False
    offer_sms_sent: bool = False


class BranchStatistics(BaseModel):
    branch_id: int
    branch_name: str
    total_staff: int
    total_patients: int
    monthly_revenue: float
    total_appointments: int
    pending_payments: float
    inventory_value: float
    active_services: int

def _generate_branch_code(db: Session, branch_name: str) -> str:
    prefix = "".join(ch for ch in branch_name.upper() if ch.isalnum())[:3] or "BR"
    last_branch = db.query(Branch).order_by(desc(Branch.id)).first()
    if last_branch and last_branch.branch_code and len(last_branch.branch_code) >= 3:
        try:
            number = int(last_branch.branch_code[-3:]) + 1
        except ValueError:
            number = 1
    else:
        number = 1
    return f"VV{prefix[:2]}{number:03d}"


def _generate_admin_username(branch_name: str, branch_code: str) -> str:
    base = "".join(ch for ch in branch_name.lower() if ch.isalnum())[:6] or "branch"
    return f"{base}_{branch_code.lower()}"[:30]


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "@#_-"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post("/branches/", response_model=BranchCreateResponse)
def create_branch(
    branch_data: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if user is super admin
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admin can create branches")
    branch_name = branch_data.name.strip()
    location = branch_data.location.strip()
    city = branch_data.city.strip()
    state = branch_data.state.strip()
    pincode = branch_data.pincode.strip()
    phone = branch_data.phone.strip()
    email = branch_data.email.strip() if branch_data.email else None
    address = branch_data.address.strip()
    license_number = branch_data.license_number.strip() if branch_data.license_number else None
    opening_hours = branch_data.opening_hours.strip() if branch_data.opening_hours else None
    facilities = branch_data.facilities.strip() if branch_data.facilities else None

    existing_name = db.query(Branch).filter(Branch.name.ilike(branch_name)).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="Branch with this name already exists")

    if license_number:
        existing_license = db.query(Branch).filter(Branch.license_number == license_number).first()
        if existing_license:
            raise HTTPException(status_code=400, detail="Branch with this license number already exists")

    branch_code = _generate_branch_code(db, branch_name)

    db_branch = Branch(
        name=branch_name,
        location=location,
        city=city,
        state=state,
        pincode=pincode,
        phone=phone,
        email=email or f"{branch_code.lower()}@vaidyavihar.local",
        address=address,
        license_number=license_number,
        opening_hours=opening_hours,
        facilities=facilities,
        branch_code=branch_code,
        is_active=True,
    )
    # attach modalities if provided
    if branch_data.modalities:
        for mname in [m.strip() for m in branch_data.modalities if m and m.strip()]:
            modality = db.query(Modality).filter(Modality.name == mname).first()
            if not modality:
                modality = Modality(name=mname)
                db.add(modality)
                db.flush()
            db_branch.modalities.append(modality)
    db.add(db_branch)
    db.flush()

    username = _generate_admin_username(branch_data.name, branch_code)
    email = f"{username}@vaidyavihar.com"
    existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        username = f"{username}{db_branch.id}"
        email = f"{username}@vaidyavihar.com"

    temp_password = _generate_temp_password()
    branch_admin = User(
        username=username,
        email=email,
        hashed_password=hash_password(temp_password),
        role="branch_admin",
        branch_id=db_branch.id,
        is_active=True,
        first_name=branch_data.admin_first_name or "Branch",
        last_name=branch_data.admin_last_name or "Admin",
        phone=branch_data.admin_phone or branch_data.phone,
    )
    db.add(branch_admin)
    _ensure_branch_notifications_table(db)
    db.add(
        BranchNotification(
            branch_id=db_branch.id,
            type=BranchNotificationType.SYSTEM_ALERT,
            title="Branch Admin Assigned",
            message=f"{branch_admin.first_name} {branch_admin.last_name} assigned as branch admin.",
            related_entity_id=branch_admin.id,
            is_read=False,
        )
    )
    db.commit()
    db.refresh(db_branch)

    onboarding_delivery = {"offer_email_sent": False, "offer_sms_sent": False}
    try:
        delivery_result = run_offer_letter_workflow(
            user_data={
                "first_name": branch_admin.first_name,
                "last_name": branch_admin.last_name,
                "full_name": f"{(branch_admin.first_name or '').strip()} {(branch_admin.last_name or '').strip()}".strip(),
                "email": branch_admin.email,
                "phone": branch_admin.phone,
                "joining_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "reporting_manager": "Regional Operations Head",
                "salary": "As per management compensation policy",
            },
            branch_data={
                "name": db_branch.name,
                "address": db_branch.address,
                "city": db_branch.city,
                "state": db_branch.state,
                "phone": db_branch.phone,
                "email": db_branch.email,
                "logo_url": getattr(db_branch, "logo_url", None),
                "director_photo_url": getattr(db_branch, "director_photo_url", None),
            },
            role=branch_admin.role or "branch_admin",
        )
        onboarding_delivery["offer_email_sent"] = bool(delivery_result.get("email_sent", False))
        onboarding_delivery["offer_sms_sent"] = bool(delivery_result.get("sms_sent", False))
    except Exception as onboarding_exc:
        print(f"OFFER_WORKFLOW_WARNING(branch_create): {onboarding_exc}")

    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="create",
        entity_type="branch",
        entity_id=db_branch.id,
        branch_id=db_branch.id,
        description=f"Created branch {db_branch.name} and branch admin {branch_admin.username}",
    )

    result = {
        "id": db_branch.id,
        "name": db_branch.name,
        "location": db_branch.location,
        "city": db_branch.city,
        "state": db_branch.state,
        "pincode": db_branch.pincode,
        "phone": db_branch.phone,
        "email": db_branch.email,
        "address": db_branch.address,
        "license_number": db_branch.license_number,
        "opening_hours": db_branch.opening_hours,
        "facilities": db_branch.facilities,
        "branch_code": db_branch.branch_code,
        "is_active": db_branch.is_active,
        "created_at": db_branch.created_at,
        "updated_at": db_branch.updated_at,
        "modalities": [m.name for m in (db_branch.modalities or [])],
        "branch_admin_credentials": {
            "username": branch_admin.username,
            "email": branch_admin.email,
            "password": temp_password,
            "role": branch_admin.role,
        },
        "offer_email_sent": onboarding_delivery["offer_email_sent"],
        "offer_sms_sent": onboarding_delivery["offer_sms_sent"],
    }
    print("CREATE_RESPONSE:", result)
    return result


@router.get("/branches/")
def get_branches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    active_only: bool = Query(True),
    include_stats: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Super admins can see all branches, others see only their own
    if current_user.role == "super_admin":
        query = db.query(Branch)
    else:
        if not current_user.branch_id:
            raise HTTPException(status_code=400, detail="branch_id is required for your role")
        query = db.query(Branch).filter(Branch.id == current_user.branch_id)

    if search:
        query = query.filter(
            Branch.name.ilike(f"%{search}%")
            | Branch.location.ilike(f"%{search}%")
            | Branch.city.ilike(f"%{search}%")
            | Branch.branch_code.ilike(f"%{search}%")
        )

    if city:
        query = query.filter(Branch.city == city)
    if state:
        query = query.filter(Branch.state == state)
    if active_only:
        query = query.filter(Branch.is_active.is_(True))

    branches = query.order_by(desc(Branch.created_at)).offset(skip).limit(limit).all()

    results = []
    from app.models import DailyEntry, Patient, Staff

    current_month = datetime.now().replace(day=1)
    for branch in branches:
        b = {
            "id": branch.id,
            "name": branch.name,
            "location": branch.location,
            "city": branch.city,
            "state": branch.state,
            "pincode": branch.pincode,
            "phone": branch.phone,
            "email": branch.email,
            "address": branch.address,
            "license_number": branch.license_number,
            "opening_hours": branch.opening_hours,
            "facilities": branch.facilities,
            "branch_code": branch.branch_code,
            "is_active": branch.is_active,
            "created_at": branch.created_at,
            "updated_at": branch.updated_at,
            "logo_url": branch.logo_url,
            "modalities": [m.name for m in (branch.modalities or [])],
        }

        if include_stats:
            b["total_staff"] = db.query(Staff).filter(Staff.branch_id == branch.id, Staff.is_active.is_(True)).count()
            b["total_patients"] = db.query(Patient).filter(Patient.branch_id == branch.id, Patient.is_active.is_(True)).count()
            monthly_entries = db.query(DailyEntry).filter(
                DailyEntry.branch_id == branch.id,
                DailyEntry.entry_date >= current_month,
            ).all()
            b["monthly_revenue"] = float(sum(float(e.total_amount) for e in monthly_entries))

        results.append(b)

    return results


@router.get("/branches/{branch_id}", response_model=BranchResponse)
def get_branch(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    if current_user.role != "super_admin" and current_user.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this branch")

    from app.models import DailyEntry, Patient, Staff

    monthly_revenue = float(
        sum(
            float(e.total_amount)
            for e in db.query(DailyEntry)
            .filter(DailyEntry.branch_id == branch.id, DailyEntry.entry_date >= datetime.now().replace(day=1))
            .all()
        )
    )

    return {
        "id": branch.id,
        "name": branch.name,
        "location": branch.location,
        "city": branch.city,
        "state": branch.state,
        "pincode": branch.pincode,
        "phone": branch.phone,
        "email": branch.email,
        "address": branch.address,
        "license_number": branch.license_number,
        "opening_hours": branch.opening_hours,
        "facilities": branch.facilities,
        "branch_code": branch.branch_code,
        "is_active": branch.is_active,
        "created_at": branch.created_at,
        "updated_at": branch.updated_at,
        "logo_url": branch.logo_url,
        "modalities": [m.name for m in (branch.modalities or [])],
        "total_staff": db.query(Staff).filter(Staff.branch_id == branch.id, Staff.is_active.is_(True)).count(),
        "total_patients": db.query(Patient).filter(Patient.branch_id == branch.id, Patient.is_active.is_(True)).count(),
        "monthly_revenue": monthly_revenue,
    }


@router.put("/branches/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: int,
    branch_data: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if user has permission
    if current_user.role not in ["super_admin", "branch_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    if current_user.role == "branch_admin" and current_user.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this branch")

    for field, value in branch_data.model_dump(exclude_unset=True).items():
        if field == 'modalities' and isinstance(value, list):
            # replace modalities
            branch.modalities = []
            for mname in value:
                modality = db.query(Modality).filter(Modality.name == mname).first()
                if not modality:
                    modality = Modality(name=mname)
                    db.add(modality)
                    db.flush()
                branch.modalities.append(modality)
        else:
            setattr(branch, field, value)

    branch.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(branch)

    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="update",
        entity_type="branch",
        entity_id=branch.id,
        branch_id=branch.id,
        description=f"Updated branch {branch.name}",
    )

    # return serialized branch with modalities
    return {
        "id": branch.id,
        "name": branch.name,
        "location": branch.location,
        "city": branch.city,
        "state": branch.state,
        "pincode": branch.pincode,
        "phone": branch.phone,
        "email": branch.email,
        "address": branch.address,
        "license_number": branch.license_number,
        "opening_hours": branch.opening_hours,
        "facilities": branch.facilities,
        "branch_code": branch.branch_code,
        "is_active": branch.is_active,
        "created_at": branch.created_at,
        "updated_at": branch.updated_at,
        "logo_url": branch.logo_url,
        "modalities": [m.name for m in (branch.modalities or [])],
    }


@router.delete("/branches/{branch_id}")
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if user is super admin
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admin can delete branches")
    
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    branch_name = branch.name
    
    try:
        # Cascading hard delete with transaction
        from app.models import Patient, Staff, User, DailyEntry, InventoryItem, Asset
        
        # Delete all associated records
        db.query(Staff).filter(Staff.branch_id == branch_id).delete(synchronize_session=False)
        db.query(Patient).filter(Patient.branch_id == branch_id).delete(synchronize_session=False)
        db.query(DailyEntry).filter(DailyEntry.branch_id == branch_id).delete(synchronize_session=False)
        db.query(InventoryItem).filter(InventoryItem.branch_id == branch_id).delete(synchronize_session=False)
        
        # Delete assets if Asset model exists
        try:
            db.query(Asset).filter(Asset.branch_id == branch_id).delete(synchronize_session=False)
        except:
            pass
        
        # Delete branch admin users
        db.query(User).filter(User.branch_id == branch_id).delete(synchronize_session=False)
        
        # Delete the branch itself
        db.delete(branch)
        
        # Commit transaction
        db.commit()
        
        auth_guard.log_activity(
            db=db,
            user=current_user,
            action="delete",
            entity_type="branch",
            entity_id=branch_id,
            description=f"Permanently deleted branch {branch_name} and all associated data",
        )
        
        return {"message": "Branch permanently deleted along with all associated data"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete branch: {str(e)}"
        )


@router.delete("/branches/{branch_id}/permanent")
def delete_branch_permanent(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a branch - archives associated data instead of hard delete"""
    # Check if user is super admin
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admin can delete branches")
    
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Check for dependencies
    from app.models import Patient, Staff, User, DailyEntry, InventoryItem
    
    staff_count = db.query(Staff).filter(Staff.branch_id == branch_id).count()
    patient_count = db.query(Patient).filter(Patient.branch_id == branch_id).count()
    user_count = db.query(User).filter(User.branch_id == branch_id).count()
    entry_count = db.query(DailyEntry).filter(DailyEntry.branch_id == branch_id).count()
    inventory_count = db.query(InventoryItem).filter(InventoryItem.branch_id == branch_id).count()
    
    total_dependencies = staff_count + patient_count + user_count + entry_count + inventory_count
    
    if total_dependencies > 0:
        # Soft-archive: deactivate branch and all associated records
        branch.is_active = False
        
        # Archive associated records
        db.query(Staff).filter(Staff.branch_id == branch_id).update({"is_active": False})
        db.query(Patient).filter(Patient.branch_id == branch_id).update({"is_active": False})
        db.query(User).filter(User.branch_id == branch_id).update({"is_active": False})
        db.query(InventoryItem).filter(InventoryItem.branch_id == branch_id).update({"is_active": False})
        
        db.commit()
        
        auth_guard.log_activity(
            db=db,
            user=current_user,
            action="archive",
            entity_type="branch",
            entity_id=branch.id,
            branch_id=branch.id,
            description=f"Archived branch {branch.name} and {total_dependencies} associated records (soft-delete)",
        )
        
        return {
            "message": "Branch and associated data archived successfully",
            "archived_records": {
                "staff": staff_count,
                "patients": patient_count,
                "users": user_count,
                "entries": entry_count,
                "inventory": inventory_count
            }
        }
    else:
        # No dependencies - safe to hard delete
        db.delete(branch)
        db.commit()
        
        auth_guard.log_activity(
            db=db,
            user=current_user,
            action="delete",
            entity_type="branch",
            entity_id=branch_id,
            description=f"Permanently deleted branch {branch.name} (no dependencies)",
        )
        
        return {"message": "Branch permanently deleted successfully"}


@router.post("/branches/{branch_id}/activate", response_model=BranchResponse)
def activate_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admin can activate branches")
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    branch.is_active = True
    branch.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(branch)

    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="activate",
        entity_type="branch",
        entity_id=branch.id,
        branch_id=branch.id,
        description=f"Activated branch {branch.name}",
    )

    return {
        "id": branch.id,
        "name": branch.name,
        "location": branch.location,
        "city": branch.city,
        "state": branch.state,
        "pincode": branch.pincode,
        "phone": branch.phone,
        "email": branch.email,
        "address": branch.address,
        "license_number": branch.license_number,
        "opening_hours": branch.opening_hours,
        "facilities": branch.facilities,
        "branch_code": branch.branch_code,
        "is_active": branch.is_active,
        "created_at": branch.created_at,
        "updated_at": branch.updated_at,
        "modalities": [m.name for m in (branch.modalities or [])],
    }


@router.get("/branches/{branch_id}/admin-credentials")
def reset_branch_admin_credentials(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admin can access branch admin credentials")

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    branch_admin = (
        db.query(User)
        .filter(User.branch_id == branch_id, User.role == "branch_admin")
        .order_by(desc(User.id))
        .first()
    )
    if not branch_admin:
        raise HTTPException(status_code=404, detail="Branch admin user not found")

    new_temp_password = _generate_temp_password()
    branch_admin.hashed_password = hash_password(new_temp_password)
    db.commit()
    db.refresh(branch_admin)

    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="reset_credentials",
        entity_type="user",
        entity_id=branch_admin.id,
        branch_id=branch_id,
        description=f"Reset branch admin credentials for branch {branch.name} ({branch_admin.username})",
    )

    response_data = {
        "branch_id": branch.id,
        "branch_name": branch.name,
        "branch_admin_credentials": {
            "username": branch_admin.username,
            "email": branch_admin.email,
            "password": new_temp_password,
            "role": branch_admin.role,
        },
    }
    print("ADMIN_CREDENTIALS_RESPONSE:", response_data)
    return response_data


@router.get("/branches/{branch_id}/statistics")
def get_branch_statistics(
    branch_id: int,
    year: int = Query(datetime.now().year, ge=2020, le=2035),
    month: int = Query(datetime.now().month, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    if current_user.role != "super_admin" and current_user.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this branch")

    from app.models import DailyEntry, InventoryItem, Patient, Staff

    start_date = datetime(year, month, 1)
    end_date = datetime(year + 1, 1, 1) - timedelta(days=1) if month == 12 else datetime(year, month + 1, 1) - timedelta(days=1)

    total_staff = db.query(Staff).filter(Staff.branch_id == branch_id, Staff.is_active.is_(True)).count()
    total_patients = db.query(Patient).filter(Patient.branch_id == branch_id, Patient.is_active.is_(True)).count()
    daily_entries = db.query(DailyEntry).filter(
        DailyEntry.branch_id == branch_id,
        DailyEntry.entry_date >= start_date,
        DailyEntry.entry_date <= end_date,
    ).all()

    monthly_revenue = float(sum(float(entry.total_amount) for entry in daily_entries))
    total_appointments = len(daily_entries)
    pending_payments = float(
        sum(float(entry.total_amount) - float(entry.amount_paid or 0) for entry in daily_entries if entry.payment_status != "paid")
    )

    inventory_items = db.query(InventoryItem).filter(
        InventoryItem.branch_id == branch_id,
        InventoryItem.is_active.is_(True),
    ).all()
    inventory_value = float(sum(float(item.current_stock or 0) * float(item.purchase_price or 0) for item in inventory_items))
    active_services = len({entry.test_names for entry in daily_entries if entry.test_names})

    return BranchStatistics(
        branch_id=branch.id,
        branch_name=branch.name,
        total_staff=total_staff,
        total_patients=total_patients,
        monthly_revenue=monthly_revenue,
        total_appointments=total_appointments,
        pending_payments=pending_payments,
        inventory_value=inventory_value,
        active_services=active_services,
    )
