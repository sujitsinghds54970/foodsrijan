"""
Search endpoints for autocomplete functionality in Daily Operations.
Provides lightweight search APIs for Staffs, MenuItems, and Customers.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth_system import get_current_user
from app.models import User
from app.models.daily_entry_module import DailyEntryModule

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/staff/search")
def search_staff(
    q: str = Query("", min_length=0, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search for staff by name, filtered to the user's branch.
    Searches referred_doctor field in DailyEntryModule.
    Returns: List of {id, name}
    """
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="User must be assigned to a branch")
    
    query = db.query(distinct(DailyEntryModule.referred_doctor)).filter(
        DailyEntryModule.branch_id == current_user.branch_id,
        DailyEntryModule.referred_doctor.isnot(None),
        DailyEntryModule.referred_doctor != ""
    )
    
    if q.strip():
        query = query.filter(DailyEntryModule.referred_doctor.ilike(f"%{q}%"))
    
    staff = query.order_by(DailyEntryModule.referred_doctor).limit(10).all()
    
    # Return as list of {id, name} where id is the doctor name itself
    return [{"id": doctor[0], "name": doctor[0]} for doctor in staff]


@router.get("/menu_items/search")
def search_menu_items(
    q: str = Query("", min_length=0, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search for menu_items by name, filtered to the user's branch.
    Searches test_name field in DailyEntryModule.
    Returns: List of {id, name} (id is the test_name for consistency)
    """
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="User must be assigned to a branch")
    
    query = db.query(distinct(DailyEntryModule.test_name)).filter(
        DailyEntryModule.branch_id == current_user.branch_id,
        DailyEntryModule.test_name.isnot(None),
        DailyEntryModule.test_name != ""
    )
    
    if q.strip():
        query = query.filter(DailyEntryModule.test_name.ilike(f"%{q}%"))
    
    menu_items = query.order_by(DailyEntryModule.test_name).limit(10).all()
    
    # Return as list of {id, name} where id is the test_name itself
    return [{"id": test[0], "name": test[0]} for test in menu_items]


@router.get("/customers/search")
def search_customers(
    q: str = Query("", min_length=0, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search for customers by name or auto_patient_id, filtered to the user's branch.
    Searches patient_name and auto_patient_id fields in DailyEntryModule.
    Returns: List of {id, name, auto_patient_id}
    """
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="User must be assigned to a branch")
    
    query = db.query(
        DailyEntryModule.auto_patient_id,
        DailyEntryModule.patient_name
    ).filter(
        DailyEntryModule.branch_id == current_user.branch_id,
        DailyEntryModule.patient_name.isnot(None),
        DailyEntryModule.patient_name != ""
    ).distinct()
    
    if q.strip():
        search_term = f"%{q}%"
        query = query.filter(
            (DailyEntryModule.patient_name.ilike(search_term)) |
            (DailyEntryModule.auto_patient_id.ilike(search_term))
        )
    
    customers = query.order_by(DailyEntryModule.patient_name).limit(10).all()
    
    return [
        {
            "id": patient[0],  # auto_patient_id
            "name": patient[1],  # patient_name
            "patient_id": patient[0]
        }
        for patient in customers
    ]
