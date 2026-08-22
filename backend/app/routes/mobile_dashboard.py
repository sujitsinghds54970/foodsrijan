from fastapi import APIRouter
from fastapi import Depends
from app.database import get_db
from app.utils.auth_guard import get_current_user
from sqlalchemy.orm import Session
from app.models.user import User
router = APIRouter()
@router.get("/mobile/dashboard/")
def mobile_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.role

    if role == "technician":
        pending_menu_items = db.query(LabMenuItem).filter(
            LabMenuItem.technician_id == current_user.id,
            LabMenuItem.status == "pending"
        ).count()
        return {"role": "technician", "pending_menu_items": pending_menu_items}

    elif role == "admin":
        total_customers = db.query(CustomerEntry).count()
        return {"role": "admin", "total_customers": total_customers}

    return {"role": role, "message": "No dashboard available"}