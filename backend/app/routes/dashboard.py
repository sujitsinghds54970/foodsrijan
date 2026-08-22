from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth_guard import get_current_user
from app.models.user import User
from app.models.appointment import Appointment
from app.models.lab_test import LabMenuItem
from sqlalchemy import func

router = APIRouter()

@router.get("/dashboard/")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.role

    if role == "admin":
        total_customers = db.query(func.count(CustomerEntry.id)).scalar()
        total_appointments = db.query(func.count(Appointment.id)).scalar()
        total_menu_items = db.query(func.count(LabMenuItem.id)).scalar()
        return {
            "role": "admin",
            "total_customers": total_customers,
            "total_appointments": total_appointments,
            "total_lab_menu_items": total_menu_items
        }

    elif role == "technician":
        assigned_menu_items = db.query(LabMenuItem).filter(
            LabMenuItem.technician_id == current_user.id,
            LabMenuItem.status == "pending"
        ).count()
        completed_menu_items = db.query(LabMenuItem).filter(
            LabMenuItem.technician_id == current_user.id,
            LabMenuItem.status == "completed"
        ).count()
        return {
            "role": "technician",
            "assigned_menu_items": assigned_menu_items,
            "completed_menu_items": completed_menu_items
        }

    elif role == "reception":
        today_appointments = db.query(Appointment).filter(
            func.date(Appointment.scheduled_time) == func.current_date()
        ).count()
        return {
            "role": "reception",
            "today_appointments": today_appointments
        }

    else:
        raise HTTPException(status_code=403, detail="Role not supported")