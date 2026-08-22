"""
Staff Management Routes for VaidyaVihar Diagnostic ERP

Provides comprehensive doctor management including:
- Staff registration and profile management
- Multi-branch assignment across city
- City-wide patient report distribution
- Staff portal access
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import random

from app.database import get_db
from app.utils.auth_system import auth_guard, require_staff, get_current_user, require_role
from app.models import User, Branch, Customer, LabResult, Staff as StaffModel
from app.models.staff import (
    Staff, StaffBranch, OrderDistribution, OrderTemplate, 
    StaffNotification, StaffSchedule
)
from pydantic import BaseModel, Field, EmailStr
from enum import Enum

router = APIRouter()


# ============ Pydantic Schemas ============

class StaffCreate(BaseModel):
    """Schema for creating a new doctor"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    alternate_phone: Optional[str] = Field(None, max_length=15)
    
    qualification: str = Field(..., min_length=1, max_length=200)
    specialization: str = Field(..., min_length=1, max_length=100)
    registration_number: Optional[str] = Field(None, max_length=50)
    years_of_experience: int = Field(0, ge=0)
    
    clinic_name: Optional[str] = Field(None, max_length=200)
    clinic_address: Optional[str] = None
    clinic_city: Optional[str] = Field(None, max_length=100)
    
    # Portal access
    create_portal_account: bool = False
    username: Optional[str] = Field(None, max_length=100)
    
    # Notification preferences
    notification_preferences: Optional[dict] = {
        "email": True,
        "sms": True,
        "whatsapp": True,
        "push": True,
        "report_ready": True,
        "appointment_reminder": True,
        "urgent_alerts": True
    }
    
    # Order preferences
    report_preferences: Optional[dict] = {
        "auto_receive_orders": True,
        "pdf_format": True,
        "dicom_format": False,
        "email_delivery": True,
        "whatsapp_delivery": True,
        "portal_access": True
    }


class StaffUpdate(BaseModel):
    """Schema for updating doctor"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=15)
    alternate_phone: Optional[str] = Field(None, max_length=15)
    
    qualification: Optional[str] = Field(None, max_length=200)
    specialization: Optional[str] = Field(None, max_length=100)
    registration_number: Optional[str] = Field(None, max_length=50)
    years_of_experience: Optional[int] = Field(None, ge=0)
    
    clinic_name: Optional[str] = Field(None, max_length=200)
    clinic_address: Optional[str] = None
    clinic_city: Optional[str] = Field(None, max_length=100)
    
    notification_preferences: Optional[dict] = None
    report_preferences: Optional[dict] = None
    
    can_access_dashboard: Optional[bool] = None
    can_view_patient_history: Optional[bool] = None
    can_download_orders: Optional[bool] = None
    can_print_orders: Optional[bool] = None
    
    is_active: Optional[bool] = None


class StaffBranchAssign(BaseModel):
    """Schema for assigning doctor to branch"""
    branch_id: int
    is_primary: bool = False
    receive_all_orders: bool = True
    preferred_test_types: Optional[List[str]] = [
        "blood_test", "urine_test", "xray", "ultrasound", "ct_scan", 
        "mri", "ecg", "echo", "pathology", "microbiology"
    ]
    notes: Optional[str] = None


class StaffResponse(BaseModel):
    """Staff response schema"""
    id: int
    doctor_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    qualification: str
    specialization: str
    years_of_experience: int
    clinic_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    # Branch information
    branches: List[dict] = []
    
    class Config:
        from_attributes = True


class StaffListResponse(BaseModel):
    """Paginated doctor list response"""
    staff: List[StaffResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# ============ Helper Functions ============

def generate_doctor_id():
    """Generate unique doctor ID"""
    number = random.randint(1, 99999)
    return f"DOC-{number:05d}"


# ============ Staff CRUD Routes ============

@router.post("/staff/", response_model=StaffResponse, status_code=201)
def create_doctor(
    doctor_data: StaffCreate,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Create a new doctor record"""
    
    # Check for duplicate email
    existing = db.query(Staff).filter(Staff.email == doctor_data.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Staff with this email already exists"
        )
    
    # Check for duplicate phone
    existing = db.query(Staff).filter(Staff.phone == doctor_data.phone).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Staff with this phone number already exists"
        )
    
    # Generate doctor ID
    doctor_id = generate_doctor_id()
    
    # Create doctor
    db_doctor = Staff(
        doctor_id=doctor_id,
        first_name=doctor_data.first_name,
        last_name=doctor_data.last_name,
        email=doctor_data.email,
        phone=doctor_data.phone,
        alternate_phone=doctor_data.alternate_phone,
        qualification=doctor_data.qualification,
        specialization=doctor_data.specialization,
        registration_number=doctor_data.registration_number,
        years_of_experience=doctor_data.years_of_experience,
        clinic_name=doctor_data.clinic_name,
        clinic_address=doctor_data.clinic_address,
        clinic_city=doctor_data.clinic_city,
        notification_preferences=doctor_data.notification_preferences,
        report_preferences=doctor_data.report_preferences,
        create_portal_account=doctor_data.create_portal_account,
        username=doctor_data.username,
        created_by=current_user.id,
        is_active=True,
        is_verified=True
    )
    
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="create",
        entity_type="doctor",
        entity_id=db_doctor.id,
        description=f"Created doctor {db_doctor.first_name} {db_doctor.last_name}"
    )
    
    return db_doctor


@router.get("/staff/", response_model=StaffListResponse)
def get_staff(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    specialization: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    branch_id: Optional[int] = Query(None),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Get list of all staff across all branches.
    Supports city-wide search and filtering.
    """
    query = db.query(Staff)
    
    # Search filter
    if search:
        search_filter = or_(
            Staff.first_name.ilike(f"%{search}%"),
            Staff.last_name.ilike(f"%{search}%"),
            Staff.email.ilike(f"%{search}%"),
            Staff.phone.ilike(f"%{search}%"),
            Staff.specialization.ilike(f"%{search}%"),
            Staff.qualification.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Specialization filter
    if specialization:
        query = query.filter(Staff.specialization == specialization)
    
    # City filter
    if city:
        query = query.filter(Staff.clinic_city.ilike(f"%{city}%"))
    
    # Active filter
    if is_active is not None:
        query = query.filter(Staff.is_active == is_active)
    
    # Branch filter (staff assigned to specific branch)
    if branch_id:
        query = query.join(StaffBranch).filter(
            and_(
                StaffBranch.branch_id == branch_id,
                StaffBranch.is_active == True
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    staff = query.order_by(desc(Staff.created_at)).offset(skip).limit(limit).all()
    
    # Calculate pagination
    total_pages = (total + limit - 1) // limit
    page = (skip // limit) + 1
    
    return {
        "staff": staff,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


@router.get("/staff/{doctor_id}", response_model=StaffResponse)
def get_doctor(
    doctor_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get doctor details by ID"""
    doctor = db.query(Staff).filter(Staff.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Get branch information
    branches = []
    for db_branch in doctor.branches:
        if db_branch.is_active:
            branches.append({
                "branch_id": db_branch.branch_id,
                "branch_name": db_branch.branch.name if db_branch.branch else None,
                "is_primary": db_branch.is_primary,
                "assigned_date": db_branch.assigned_date
            })
    
    response_data = doctor.__dict__.copy()
    response_data["branches"] = branches
    
    return response_data


@router.put("/staff/{doctor_id}", response_model=StaffResponse)
def update_doctor(
    doctor_id: int,
    doctor_data: StaffUpdate,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Update doctor information"""
    doctor = db.query(Staff).filter(Staff.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Update fields
    update_data = doctor_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doctor, field, value)
    
    db.commit()
    db.refresh(doctor)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="update",
        entity_type="doctor",
        entity_id=doctor.id,
        description=f"Updated doctor {doctor.first_name} {doctor.last_name}"
    )
    
    return doctor


@router.delete("/staff/{doctor_id}")
def deactivate_doctor(
    doctor_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Deactivate a doctor"""
    doctor = db.query(Staff).filter(Staff.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Deactivate doctor
    doctor.is_active = False
    db.commit()
    
    # Deactivate all branch assignments
    for db_branch in doctor.branches:
        db_branch.is_active = False
    
    db.commit()
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="deactivate",
        entity_type="doctor",
        entity_id=doctor.id,
        description=f"Deactivated doctor {doctor.first_name} {doctor.last_name}"
    )
    
    return {"message": "Staff deactivated successfully"}


# ============ Staff Branch Assignment Routes ============

@router.post("/staff/{doctor_id}/branches")
def assign_doctor_to_branch(
    doctor_id: int,
    assignment: StaffBranchAssign,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Assign a doctor to a branch"""
    doctor = db.query(Staff).filter(Staff.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Validate branch exists
    branch = db.query(Branch).filter(Branch.id == assignment.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Check if already assigned
    existing = db.query(StaffBranch).filter(
        and_(
            StaffBranch.doctor_id == doctor_id,
            StaffBranch.branch_id == assignment.branch_id
        )
    ).first()
    
    if existing:
        # Reactivate if already exists
        existing.is_active = True
        existing.receive_all_orders = assignment.receive_all_orders
        existing.preferred_test_types = assignment.preferred_test_types
        existing.notes = assignment.notes
        existing.assigned_by = current_user.id
        db.commit()
        return {"message": "Staff assignment updated", "assignment": existing.id}
    
    # Create new assignment
    db_assignment = StaffBranch(
        doctor_id=doctor_id,
        branch_id=assignment.branch_id,
        is_primary=assignment.is_primary,
        receive_all_orders=assignment.receive_all_orders,
        preferred_test_types=assignment.preferred_test_types,
        notes=assignment.notes,
        assigned_by=current_user.id,
        is_active=True
    )
    
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="assign",
        entity_type="doctor_branch",
        entity_id=db_assignment.id,
        description=f"Assigned Dr. {doctor.first_name} {doctor.last_name} to {branch.name}"
    )
    
    return {"message": "Staff assigned to branch successfully", "assignment_id": db_assignment.id}


@router.delete("/staff/{doctor_id}/branches/{branch_id}")
def remove_doctor_from_branch(
    doctor_id: int,
    branch_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Remove a doctor from a branch"""
    assignment = db.query(StaffBranch).filter(
        and_(
            StaffBranch.doctor_id == doctor_id,
            StaffBranch.branch_id == branch_id
        )
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Deactivate assignment
    assignment.is_active = False
    assignment.deactivated_at = datetime.utcnow()
    assignment.deactivated_by = current_user.id
    
    db.commit()
    
    return {"message": "Staff removed from branch"}


@router.get("/staff/{doctor_id}/branches")
def get_doctor_branches(
    doctor_id: int,
    include_inactive: bool = False,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get all branches a doctor is assigned to"""
    doctor = db.query(Staff).filter(Staff.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    query = db.query(StaffBranch).filter(StaffBranch.doctor_id == doctor_id)
    
    if not include_inactive:
        query = query.filter(StaffBranch.is_active == True)
    
    assignments = query.order_by(desc(StaffBranch.is_primary)).all()
    
    result = []
    for assignment in assignments:
        branch = db.query(Branch).filter(Branch.id == assignment.branch_id).first()
        result.append({
            "id": assignment.id,
            "branch_id": assignment.branch_id,
            "branch_name": branch.name if branch else None,
            "branch_location": branch.location if branch else None,
            "is_primary": assignment.is_primary,
            "receive_all_orders": assignment.receive_all_orders,
            "preferred_test_types": assignment.preferred_test_types,
            "assigned_date": assignment.assigned_date,
            "is_active": assignment.is_active
        })
    
    return result


# ============ City-Wide Staff Search ============

@router.get("/staff/search/city-wide")
def search_staff_city_wide(
    q: str = Query(..., min_length=2),
    specialization: Optional[str] = Query(None),
    test_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Search staff across all branches in the city.
    Returns staff who can receive specific test types.
    """
    query = db.query(Staff).filter(Staff.is_active == True)
    
    # Text search
    search_filter = or_(
        Staff.first_name.ilike(f"%{q}%"),
        Staff.last_name.ilike(f"%{q}%"),
        Staff.email.ilike(f"%{q}%"),
        Staff.specialization.ilike(f"%{q}%"),
        Staff.qualification.ilike(f"%{q}%")
    )
    query = query.filter(search_filter)
    
    # Specialization filter
    if specialization:
        query = query.filter(Staff.specialization == specialization)
    
    # Get staff
    staff = query.limit(limit).all()
    
    result = []
    for doctor in staff:
        # Check if doctor can receive specific test type
        can_receive = True
        if test_type:
            can_receive = False
            for branch_assignment in doctor.branches:
                if branch_assignment.is_active and branch_assignment.receive_all_orders:
                    can_receive = True
                    break
                if branch_assignment.is_active and test_type in (branch_assignment.preferred_test_types or []):
                    can_receive = True
                    break
        
        if can_receive:
            result.append({
                "id": doctor.id,
                "doctor_id": doctor.doctor_id,
                "name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "email": doctor.email,
                "phone": doctor.phone,
                "qualification": doctor.qualification,
                "specialization": doctor.specialization,
                "years_of_experience": doctor.years_of_experience,
                "clinic_name": doctor.clinic_name,
                "branches_count": len([b for b in doctor.branches if b.is_active])
            })
    
    return {"staff": result, "total": len(result)}


@router.get("/specializations")
def get_specializations(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get list of all specializations"""
    specializations = db.query(
        Staff.specialization,
        func.count(Staff.id).label("doctor_count")
    ).filter(
        Staff.is_active == True
    ).group_by(Staff.specialization).all()
    
    return [
        {"specialization": s, "doctor_count": c}
        for s, c in specializations
    ]


# ============ Staff Portal Authentication ============

@router.post("/staff/{doctor_id}/generate-portal-access")
def generate_doctor_portal_access(
    doctor_id: int,
    current_user: User = Depends(require_role(["admin", "branch_admin"])),
    db: Session = Depends(get_db)
):
    """Generate portal access credentials for a doctor"""
    from passlib.context import CryptContext
    import secrets
    
    doctor = db.query(Staff).filter(Staff.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Generate password
    password = secrets.token_urlsafe(8)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash(password)
    
    # Update doctor
    doctor.username = doctor.email.split("@")[0] if not doctor.username else doctor.username
    doctor.hashed_password = hashed
    doctor.can_access_dashboard = True
    doctor.can_view_patient_history = True
    doctor.can_download_orders = True
    doctor.can_print_orders = True
    
    db.commit()
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="generate_portal_access",
        entity_type="doctor",
        entity_id=doctor.id,
        description=f"Generated portal access for Dr. {doctor.first_name} {doctor.last_name}"
    )
    
    return {
        "message": "Portal access generated",
        "username": doctor.username,
        "temporary_password": password,
        "portal_url": "/doctor-portal/login"
    }


@router.get("/staff/{doctor_id}/portal-dashboard")
def get_doctor_portal_dashboard(
    doctor_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get dashboard data for doctor portal"""
    doctor = db.query(Staff).filter(Staff.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get branch IDs doctor is assigned to
    branch_ids = [db.branch_id for db in doctor.branches if db.is_active]
    
    # Get received orders count
    received_orders = db.query(func.count(OrderDistribution.id)).filter(
        and_(
            OrderDistribution.doctor_id == doctor_id,
            OrderDistribution.created_at >= start_date,
            OrderDistribution.created_at <= end_date
        )
    ).scalar()
    
    # Get unread orders count
    unread_orders = db.query(func.count(OrderDistribution.id)).filter(
        and_(
            OrderDistribution.doctor_id == doctor_id,
            OrderDistribution.delivery_status.in_(["pending", "sent", "delivered"])
        )
    ).scalar()
    
    # Get orders by type
    orders_by_type = db.query(
        OrderDistribution.report_type,
        func.count(OrderDistribution.id)
    ).filter(
        OrderDistribution.doctor_id == doctor_id
    ).group_by(OrderDistribution.report_type).all()
    
    # Get recent orders
    recent_orders = db.query(OrderDistribution).filter(
        OrderDistribution.doctor_id == doctor_id
    ).order_by(desc(OrderDistribution.created_at)).limit(10).all()
    
    return {
        "doctor": {
            "id": doctor.id,
            "name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "specialization": doctor.specialization
        },
        "statistics": {
            "total_orders_received": received_orders or 0,
            "unread_orders": unread_orders or 0,
            "orders_this_month": received_orders or 0
        },
        "orders_by_type": [
            {"type": rpt_type, "count": count}
            for rpt_type, count in orders_by_type
        ],
        "recent_orders": [
            {
                "id": r.id,
                "distribution_id": r.distribution_id,
                "patient_name": r.lab_result.patient.first_name if r.lab_result and r.lab_result.patient else "N/A",
                "report_type": r.report_type,
                "delivery_status": r.delivery_status,
                "created_at": r.created_at
            }
            for r in recent_orders
        ],
        "assigned_branches": [
            {
                "branch_id": db.branch_id,
                "branch_name": db.branch.name if db.branch else None
            }
            for db in doctor.branches if db.is_active
        ]
    }


# ============ Analytics ============

@router.get("/staff/analytics/overview")
def get_staff_analytics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    branch_id: Optional[int] = Query(None),
    current_user: User = Depends(require_role(["admin", "branch_admin"])),
    db: Session = Depends(get_db)
):
    """Get analytics overview for staff"""
    
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Build base query for staff
    query = db.query(Staff).filter(Staff.is_active == True)
    
    # If branch specified, filter staff assigned to that branch
    if branch_id:
        query = query.join(StaffBranch).filter(
            and_(
                StaffBranch.branch_id == branch_id,
                StaffBranch.is_active == True
            )
        )
    
    total_staff = query.count()
    
    # Get specialization distribution
    specialization_stats = db.query(
        Staff.specialization,
        func.count(Staff.id)
    ).filter(
        Staff.is_active == True
    ).group_by(Staff.specialization).all()
    
    # Get branch distribution
    branch_distribution = db.query(
        StaffBranch.branch_id,
        func.count(StaffBranch.doctor_id)
    ).filter(
        StaffBranch.is_active == True
    ).group_by(StaffBranch.branch_id).all()
    
    branches = {b.id: b.name for b in db.query(Branch).all()}
    
    # Get report distribution stats
    if branch_id:
        report_stats = db.query(
            OrderDistribution.report_type,
            func.count(OrderDistribution.id)
        ).filter(
            and_(
                OrderDistribution.created_at >= start_date,
                OrderDistribution.created_at <= end_date,
                OrderDistribution.branch_id == branch_id
            )
        ).group_by(OrderDistribution.report_type).all()
    else:
        report_stats = db.query(
            OrderDistribution.report_type,
            func.count(OrderDistribution.id)
        ).filter(
            and_(
                OrderDistribution.created_at >= start_date,
                OrderDistribution.created_at <= end_date
            )
        ).group_by(OrderDistribution.report_type).all()
    
    return {
        "total_staff": total_staff,
        "specialization_distribution": [
            {"specialization": s, "count": c}
            for s, c in specialization_stats
        ],
        "branch_distribution": [
            {"branch_id": bid, "branch_name": branches.get(bid, "Unknown"), "doctor_count": count}
            for bid, count in branch_distribution
        ],
        "report_distribution": [
            {"report_type": rpt_type, "count": count}
            for rpt_type, count in report_stats
        ],
        "date_range": {
            "start_date": start_date,
            "end_date": end_date
        }
    }


# ============ Export ============

@router.get("/staff/export")
def export_staff(
    format: str = Query("excel", pattern="^(excel|csv|pdf)$"),
    current_user: User = Depends(require_role(["admin", "branch_admin"])),
    db: Session = Depends(get_db)
):
    """Export doctor list to Excel, CSV, or PDF"""
    staff = db.query(Staff).filter(Staff.is_active == True).all()
    
    # Prepare data for export
    data = []
    for doctor in staff:
        branch_names = ", ".join([
            db_branch.branch.name if db_branch.branch else ""
            for db_branch in doctor.branches if db_branch.is_active
        ])
        
        data.append({
            "Staff ID": doctor.doctor_id,
            "Name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "Email": doctor.email,
            "Phone": doctor.phone,
            "Qualification": doctor.qualification,
            "Specialization": doctor.specialization,
            "Experience (Years)": doctor.years_of_experience,
            "Clinic": doctor.clinic_name or "",
            "Assigned Branches": branch_names,
            "Status": "Active" if doctor.is_active else "Inactive",
            "Created At": doctor.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    # Note: Actual file generation would use Excel/CSV libraries
    return {
        "message": f"Export initiated in {format} format",
        "record_count": len(data),
        "download_url": f"/api/export/download/staff.{format}"
    }

