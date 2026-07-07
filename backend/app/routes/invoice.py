from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.payment import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.database import get_db

router = APIRouter()


def _generate_invoice_number(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"INV-{today}"
    latest = (
        db.query(Invoice)
        .filter(Invoice.invoice_number.like(f"{prefix}-%"))
        .order_by(Invoice.id.desc())
        .first()
    )
    if latest and latest.invoice_number:
        try:
            last_seq = int(latest.invoice_number.split("-")[-1])
            seq = last_seq + 1
        except Exception:
            seq = 1
    else:
        seq = 1
    return f"{prefix}-{seq:04d}"


@router.post("/invoices/", response_model=InvoiceResponse, status_code=201)
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    payload = invoice.model_dump()
    payload["invoice_number"] = _generate_invoice_number(db)
    new_invoice = Invoice(**payload)
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)
    return new_invoice

@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice