from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.billing_entry import BillingEntry
from app.utils.auth_guard import get_current_user
from app.models.user import User
from fastapi import HTTPException

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/billing/")
def create_bill(patient_id: int, total_amount: float, paid_amount: float, status: str = "pending", db: Session = Depends(get_db)):
    bill = BillingEntry(patient_id=patient_id, total_amount=total_amount, paid_amount=paid_amount, status=status)
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill

@router.get("/billing/")
def list_bills(db: Session = Depends(get_db)):
    return db.query(BillingEntry).all()
from app.utils.auth_guard import get_current_user
@router.delete("/billing/{bill_id}")
def delete_bill(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    bill = db.query(BillingEntry).filter(BillingEntry.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    db.delete(bill)
    db.commit()
    return {"message": "Bill deleted"}
from fastapi.responses import Response
from app.utils.pdf_generator import generate_invoice_pdf
from app.models.test_entry import MenuItemEntry

@router.get("/billing/{bill_id}/invoice")
def download_invoice_pdf(bill_id: int, db: Session = Depends(get_db)):
    bill = db.query(BillingEntry).filter(BillingEntry.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    patient = db.query(CustomerEntry).filter(CustomerEntry.id == bill.patient_id).first()
    menu_items = db.query(MenuItemEntry).filter(MenuItemEntry.patient_id == patient.id).all()

    invoice_data = {
        "patient": patient,
        "date": str(patient.created_at.date()) if hasattr(patient, "created_at") else "N/A",
        "menu_items": menu_items,
        "total": bill.total_amount,
        "paid": bill.paid_amount,
        "status": bill.status
    }

    pdf_bytes = generate_invoice_pdf(invoice_data)
    return Response(content=pdf_bytes, media_type="application/pdf")