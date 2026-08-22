from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.test_entry import MenuItemEntry

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/menu_items/")
def create_test(test_name: str, price: float, patient_id: int, result: str = "", db: Session = Depends(get_db)):
    test = MenuItemEntry(test_name=test_name, price=price, patient_id=patient_id, result=result)
    db.add(test)
    db.commit()
    db.refresh(test)
    return test

@router.get("/menu_items/")
def list_menu_items(db: Session = Depends(get_db)):
    return db.query(MenuItemEntry).all()