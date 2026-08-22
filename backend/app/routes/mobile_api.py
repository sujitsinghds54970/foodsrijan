from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth_guard import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/mobile/customers/")
def get_customers_for_mobile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0
):
    customers = db.query(CustomerEntry).filter(
        CustomerEntry.branch_id == current_user.branch_id
    ).offset(offset).limit(limit).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "age": p.age,
            "gender": p.gender
        }
        for p in customers
    ]