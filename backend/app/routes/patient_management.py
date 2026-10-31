from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.utils.auth_system import auth_guard, require_staff, get_current_user, is_super_ceo_user
from app.models import User, Customer, DailyEntry, Branch
from app.schemas.user import CustomerCreate, CustomerUpdate, CustomerResponse, DailyEntryCreate, DailyEntryUpdate, DailyEntryResponse

router = APIRouter()

@router.post("/customers/", response_model=CustomerResponse)
def create_patient(
    patient_data: CustomerCreate,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Create a new patient record"""
    
    # Ensure branch access
    if not is_super_ceo_user(current_user):
        patient_data.branch_id = current_user.branch_id
    
    # Check for duplicate patient (same phone number in same branch)
    existing_patient = db.query(Customer).filter(
        and_(
            Customer.phone == patient_data.phone,
            Customer.branch_id == patient_data.branch_id
        )
    ).first()
    
    if existing_patient:
        raise HTTPException(
            status_code=400,
            detail="Customer with this phone number already exists in this branch"
        )
    
    # Generate patient ID
    branch = db.query(Branch).filter(Branch.id == patient_data.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Generate patient ID (VV + Branch Code + Sequential Number)
    branch_code = branch.name[:2].upper()
    last_patient = db.query(Customer).filter(
        Customer.branch_id == patient_data.branch_id
    ).order_by(desc(Customer.id)).first()
    
    if last_patient:
        try:
            last_number = int(last_patient.patient_id[-4:])
            new_number = last_number + 1
        except:
            new_number = 1
    else:
        new_number = 1
    
    patient_id = f"VV{branch_code}{new_number:04d}"
    
    # Create patient
    db_patient = Customer(
        patient_id=patient_id,
        branch_id=patient_data.branch_id,
        first_name=patient_data.first_name,
        last_name=patient_data.last_name,
        date_of_birth=patient_data.date_of_birth,
        gender=patient_data.gender,
        phone=patient_data.phone,
        email=patient_data.email,
        address=patient_data.address,
        city=patient_data.city,
        state=patient_data.state,
        pincode=patient_data.pincode,
        emergency_contact=patient_data.emergency_contact,
        emergency_contact_name=patient_data.emergency_contact_name,
        blood_group=patient_data.blood_group,
        allergies=patient_data.allergies,
        chronic_conditions=patient_data.chronic_conditions,
        current_medications=patient_data.current_medications
    )
    
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="create",
        entity_type="patient",
        entity_id=db_patient.id,
        description=f"Created patient {db_patient.first_name} {db_patient.last_name}"
    )
    
    return db_patient

@router.get("/customers/", response_model=List[CustomerResponse])
def get_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Search by name or phone"),
    branch_id: Optional[int] = Query(None),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get list of customers with search and filtering"""
    
    # Filter by branch access
    if is_super_ceo_user(current_user):
        query = db.query(Customer)
        if branch_id:
            query = query.filter(Customer.branch_id == branch_id)
    else:
        query = db.query(Customer).filter(Customer.branch_id == current_user.branch_id)
    
    # Search functionality
    if search:
        search_filter = or_(
            Customer.first_name.ilike(f"%{search}%"),
            Customer.last_name.ilike(f"%{search}%"),
            Customer.phone.ilike(f"%{search}%"),
            Customer.patient_id.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Only active customers
    query = query.filter(Customer.is_active == True)
    
    # Order by registration date
    customers = query.order_by(desc(Customer.registration_date)).offset(skip).limit(limit).all()
    
    return customers

@router.get("/customers/{patient_id}", response_model=CustomerResponse)
def get_patient(
    patient_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get patient by ID"""
    
    patient = db.query(Customer).filter(Customer.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and patient.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this patient")
    
    return patient

@router.put("/customers/{patient_id}", response_model=CustomerResponse)
def update_patient(
    patient_id: int,
    patient_data: CustomerUpdate,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Update patient information"""
    
    patient = db.query(Customer).filter(Customer.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and patient.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this patient")
    
    # Update fields
    for field, value in patient_data.dict(exclude_unset=True).items():
        setattr(patient, field, value)
    
    db.commit()
    db.refresh(patient)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="update",
        entity_type="patient",
        entity_id=patient.id,
        description=f"Updated patient {patient.first_name} {patient.last_name}"
    )
    
    return patient

@router.get("/customers/{patient_id}/history")
def get_patient_history(
    patient_id: int,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get patient history (daily entries, appointments, invoices)"""
    
    patient = db.query(Customer).filter(Customer.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and patient.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this patient")
    
    # Get date range (default: last 30 days)
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Get daily entries
    daily_entries = db.query(DailyEntry).filter(
        and_(
            DailyEntry.patient_id == patient_id,
            DailyEntry.entry_date >= start_date,
            DailyEntry.entry_date <= end_date
        )
    ).order_by(desc(DailyEntry.entry_date)).all()
    
    # Format response
    history = {
        "patient": {
            "id": patient.id,
            "patient_id": patient.patient_id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "phone": patient.phone,
            "email": patient.email
        },
        "date_range": {
            "start_date": start_date,
            "end_date": end_date
        },
        "daily_entries": [
            {
                "id": entry.id,
                "entry_date": entry.entry_date,
                "entry_time": entry.entry_time,
                "doctor_name": entry.doctor_name,
                "doctor_specialization": entry.doctor_specialization,
                "consultation_fee": float(entry.consultation_fee),
                "test_names": entry.test_names,
                "test_cost": float(entry.test_cost),
                "total_amount": float(entry.total_amount),
                "payment_status": entry.payment_status,
                "payment_mode": entry.payment_mode,
                "amount_paid": float(entry.amount_paid),
                "notes": entry.notes
            }
            for entry in daily_entries
        ],
        "summary": {
            "total_visits": len(daily_entries),
            "total_amount": sum(float(entry.total_amount) for entry in daily_entries),
            "total_paid": sum(float(entry.amount_paid) for entry in daily_entries),
            "pending_amount": sum(float(entry.total_amount - entry.amount_paid) for entry in daily_entries)
        }
    }
    
    return history

@router.delete("/customers/{patient_id}")
def deactivate_patient(
    patient_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Deactivate patient (soft delete)"""
    
    patient = db.query(Customer).filter(Customer.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and patient.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this patient")
    
    # Deactivate patient
    patient.is_active = False
    db.commit()
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="deactivate",
        entity_type="patient",
        entity_id=patient.id,
        description=f"Deactivated patient {patient.first_name} {patient.last_name}"
    )
    
    return {"message": "Customer deactivated successfully"}

# Daily Entry Management
@router.post("/daily-entries/", response_model=DailyEntryResponse)
def create_daily_entry(
    entry_data: DailyEntryCreate,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Create a new daily entry"""
    
    # Ensure branch access
    if not is_super_ceo_user(current_user):
        entry_data.branch_id = current_user.branch_id
    
    # Validate branch exists
    branch = db.query(Branch).filter(Branch.id == entry_data.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # If patient_id provided, validate patient exists and belongs to branch
    patient = None
    if entry_data.patient_id:
        patient = db.query(Customer).filter(
            and_(
                Customer.id == entry_data.patient_id,
                Customer.branch_id == entry_data.branch_id
            )
        ).first()
        
        if not patient:
            raise HTTPException(status_code=404, detail="Customer not found in this branch")
    
    # Create daily entry
    db_entry = DailyEntry(
        branch_id=entry_data.branch_id,
        patient_id=entry_data.patient_id,
        entry_date=entry_data.entry_date,
        doctor_name=entry_data.doctor_name,
        doctor_specialization=entry_data.doctor_specialization,
        consultation_fee=entry_data.consultation_fee,
        patient_name=entry_data.patient_name,
        patient_mobile=entry_data.patient_mobile,
        patient_address=entry_data.patient_address,
        test_names=entry_data.test_names,
        test_cost=entry_data.test_cost,
        discount=entry_data.discount,
        total_amount=entry_data.total_amount,
        payment_status=entry_data.payment_status,
        payment_mode=entry_data.payment_mode,
        amount_paid=entry_data.amount_paid,
        notes=entry_data.notes,
        referred_by=entry_data.referred_by,
        created_by=current_user.id
    )
    
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="create",
        entity_type="daily_entry",
        entity_id=db_entry.id,
        description=f"Created daily entry for {entry_data.patient_name}"
    )
    
    return db_entry

@router.get("/daily-entries/", response_model=List[DailyEntryResponse])
def get_daily_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    doctor_name: Optional[str] = Query(None),
    patient_name: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get daily entries with filtering"""
    
    # Filter by branch access
    if is_super_ceo_user(current_user):
        query = db.query(DailyEntry)
        if branch_id:
            query = query.filter(DailyEntry.branch_id == branch_id)
    else:
        query = db.query(DailyEntry).filter(DailyEntry.branch_id == current_user.branch_id)
    
    # Date range filter
    if start_date:
        query = query.filter(DailyEntry.entry_date >= start_date)
    if end_date:
        query = query.filter(DailyEntry.entry_date <= end_date)
    
    # Other filters
    if doctor_name:
        query = query.filter(DailyEntry.doctor_name.ilike(f"%{doctor_name}%"))
    if patient_name:
        query = query.filter(DailyEntry.patient_name.ilike(f"%{patient_name}%"))
    if payment_status:
        query = query.filter(DailyEntry.payment_status == payment_status)
    
    entries = query.order_by(desc(DailyEntry.entry_date)).offset(skip).limit(limit).all()
    
    return entries

@router.get("/daily-entries/{entry_id}", response_model=DailyEntryResponse)
def get_daily_entry(
    entry_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get daily entry by ID"""
    
    entry = db.query(DailyEntry).filter(DailyEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Daily entry not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and entry.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")
    
    return entry

@router.put("/daily-entries/{entry_id}", response_model=DailyEntryResponse)
def update_daily_entry(
    entry_id: int,
    entry_data: DailyEntryUpdate,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Update daily entry"""
    
    entry = db.query(DailyEntry).filter(DailyEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Daily entry not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and entry.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")
    
    # Update fields
    for field, value in entry_data.dict(exclude_unset=True).items():
        setattr(entry, field, value)
    
    db.commit()
    db.refresh(entry)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="update",
        entity_type="daily_entry",
        entity_id=entry.id,
        description=f"Updated daily entry {entry.id}"
    )
    
    return entry

@router.delete("/daily-entries/{entry_id}")
def delete_daily_entry(
    entry_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Delete daily entry"""
    
    entry = db.query(DailyEntry).filter(DailyEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Daily entry not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and entry.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")
    
    db.delete(entry)
    db.commit()
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="delete",
        entity_type="daily_entry",
        entity_id=entry_id,
        description=f"Deleted daily entry {entry_id}"
    )
    
    return {"message": "Daily entry deleted successfully"}
