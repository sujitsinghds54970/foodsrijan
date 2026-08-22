"""
Payment Routes for VaidyaVihar Diagnostic ERP

Payment gateway integration endpoints:
- Razorpay integration
- PayU integration  
- Invoice management
- Payment processing
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, time
from decimal import Decimal, InvalidOperation
import uuid
import hashlib
import json
import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.database import get_db
from app.models.payment import (
    Payment, PaymentStatus, PaymentMode, PaymentGateway, PaymentLink, 
    Invoice, InvoiceItem, PaymentSettings
)
from app.models.daily_entry_module import DailyEntryModule
from app.services.sms_service import get_sms_service
from app.services.whatsapp_service import get_whatsapp_service

router = APIRouter()


class SoundboxWebhookPayload(BaseModel):
    transaction_id: Optional[str] = None
    amount: float
    status: str
    upi_id: Optional[str] = None
    provider: Optional[str] = None
    raw: Optional[dict] = None


def _ensure_paid_at_column(db: Session) -> None:
    # Keep webhook self-healing for existing SQLite databases where this column
    # may not exist yet (no migration executed yet).
    try:
        cols = db.execute(text("PRAGMA table_info(daily_entries_module)")).fetchall()
        col_names = {row[1] for row in cols}
        if "paid_at" not in col_names:
            db.execute(text("ALTER TABLE daily_entries_module ADD COLUMN paid_at DATETIME"))
            db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[DIGITAL WEBHOOK] Failed ensuring paid_at column: {exc}")


def _ensure_bill_pdf_url_column(db: Session) -> None:
    # Add bill_pdf_url lazily for older databases until migration is applied.
    try:
        cols = db.execute(text("PRAGMA table_info(daily_entries_module)")).fetchall()
        col_names = {row[1] for row in cols}
        if "bill_pdf_url" not in col_names:
            db.execute(text("ALTER TABLE daily_entries_module ADD COLUMN bill_pdf_url VARCHAR(500)"))
            db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[DIGITAL WEBHOOK] Failed ensuring bill_pdf_url column: {exc}")


def _ensure_daily_entry_upi_id_column(db: Session) -> None:
    # Ensure webhook can match directly by daily entry upi_id.
    try:
        cols = db.execute(text("PRAGMA table_info(daily_entries_module)")).fetchall()
        col_names = {row[1] for row in cols}
        if "upi_id" not in col_names:
            db.execute(text("ALTER TABLE daily_entries_module ADD COLUMN upi_id VARCHAR(100)"))
            db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[DIGITAL WEBHOOK] Failed ensuring upi_id column: {exc}")


def _amount_to_match_string(value: object) -> str:
    # Normalize numeric-looking values to a stable string for flexible matching.
    if value is None:
        return ""
    raw = str(value).strip()
    if raw == "":
        return ""
    try:
        dec = Decimal(raw)
        normalized = format(dec.normalize(), "f")
        return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized
    except (InvalidOperation, ValueError):
        return raw


AUTO_BILL_DIR = Path("uploads/auto_bills")
AUTO_BILL_DIR.mkdir(parents=True, exist_ok=True)


def _generate_auto_bill_pdf(entry: DailyEntryModule) -> str:
    # Backend-side auto-billing equivalent for the old hardware soundbox flow.
    # This saves a minimal bill PDF to server storage when payment gets confirmed.
    filename = f"bill_{entry.auto_patient_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath = AUTO_BILL_DIR / filename

    pdf = canvas.Canvas(str(filepath), pagesize=A4)
    _, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "Payment Bill")
    y -= 30

    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, y, f"Customer ID: {entry.auto_patient_id}")
    y -= 20
    pdf.drawString(40, y, f"Customer Name: {entry.patient_name}")
    y -= 20
    pdf.drawString(40, y, f"MenuItem: {entry.test_name}")
    y -= 20
    pdf.drawString(40, y, f"Payment Method: {entry.payment_method}")
    y -= 20
    pdf.drawString(40, y, f"Amount: INR {entry.total_amount}")
    y -= 20
    pdf.drawString(40, y, f"Paid At: {datetime.utcnow().isoformat()}")
    y -= 20
    pdf.drawString(40, y, f"Entry Date: {entry.auto_entry_datetime.isoformat() if entry.auto_entry_datetime else ''}")

    pdf.showPage()
    pdf.save()

    return f"/uploads/auto_bills/{filename}"


@router.post("/webhook")
async def soundbox_payment_webhook(payload: SoundboxWebhookPayload, db: Session = Depends(get_db)):
    """
    Public webhook endpoint for digital online/QR payment confirmations.

    Providers (HDFC/SBI/Paytm/etc.) usually call this URL server-to-server with
    payment confirmation payloads, so Bearer auth is intentionally not required.

    Expected minimum fields:
      - transaction_id: provider transaction reference (optional)
      - amount: paid amount
      - status: SUCCESS/FAILED/PENDING (SUCCESS marks paid)
      - upi_id: merchant UPI ID that received payment (optional in matching)
    """
    _ensure_paid_at_column(db)
    _ensure_bill_pdf_url_column(db)
    _ensure_daily_entry_upi_id_column(db)

    payload_dict = payload.dict()
    print(
        f"Searching for: amount={payload_dict.get('amount')} (type: {type(payload_dict.get('amount'))}), "
        f"upi_id={payload_dict.get('upi_id')}"
    )

    normalized_status = (payload.status or "").strip().upper()
    if normalized_status != "SUCCESS":
        print(f"[DIGITAL WEBHOOK] Non-success status received: {payload.status}")
        return {"message": "Webhook received (non-success status)", "updated": False}

    today = datetime.now()
    today_start = datetime.combine(today.date(), time.min)
    today_end = datetime.combine(today.date(), time.max)

    base_query = db.query(DailyEntryModule).filter(
        DailyEntryModule.auto_entry_datetime >= today_start,
        DailyEntryModule.auto_entry_datetime <= today_end,
        DailyEntryModule.payment_method == 'UPI',
        DailyEntryModule.is_paid == False,
    )

    if payload.upi_id:
        base_query = base_query.filter(DailyEntryModule.upi_id == payload.upi_id)

    entries = base_query.order_by(DailyEntryModule.created_at.asc(), DailyEntryModule.id.asc()).all()
    print(f"Found entries for today: {len(entries)}")

    payload_amount_str = _amount_to_match_string(payload.amount)
    payload_upi = (payload.upi_id or "").strip()

    matched_candidates = []
    for e in entries:
        print(f"Candidate: id={e.id}, total={e.total_amount}, upi={e.upi_id}")
        entry_amount_str = _amount_to_match_string(e.total_amount)
        entry_upi = (e.upi_id or "").strip()

        upi_match = (not payload_upi) or (entry_upi == payload_upi)
        amount_match = entry_amount_str == payload_amount_str

        if upi_match and amount_match and (e.is_paid is False):
            matched_candidates.append(e)

    matched_entry = sorted(
        matched_candidates,
        key=lambda row: (row.created_at or datetime.max, row.id)
    )[0] if matched_candidates else None

    if not matched_entry:
        print(
            "[DIGITAL WEBHOOK] No matching entry found for manual verification: "
            f"transaction_id={payload.transaction_id}, amount={payload.amount}, upi_id={payload.upi_id}"
        )
        return {"message": "Payment webhook received (no matching entry found)", "updated": False}

    try:
        matched_entry.is_paid = True
        matched_entry.status = 'Completed'

        auto_bill_path = _generate_auto_bill_pdf(matched_entry)
        previous_remarks = (matched_entry.remarks or "").strip()
        webhook_note = f"digital_webhook_confirmed txn={payload.transaction_id or 'N/A'} bill={auto_bill_path}"
        matched_entry.remarks = f"{previous_remarks} | {webhook_note}".strip(" |")

        db.execute(
            text("UPDATE daily_entries_module SET paid_at = :paid_at, bill_pdf_url = :bill_pdf_url WHERE id = :entry_id"),
            {
                "paid_at": datetime.utcnow().isoformat(),
                "bill_pdf_url": auto_bill_path,
                "entry_id": matched_entry.id,
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {exc}")

    return {
        "message": "Payment confirmed and auto-bill generated",
        "updated": True,
        "entry_id": matched_entry.id,
        "transaction_id": payload.transaction_id,
    }


# Pydantic Schemas
class InvoiceCreate(BaseModel):
    patient_id: int
    branch_id: Optional[int] = None
    items: List[dict]
    discount_amount: float = 0
    tax_amount: float = 0
    notes: Optional[str] = None
    referred_by: Optional[str] = None


class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    discount_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    notes: Optional[str] = None


class PaymentCreate(BaseModel):
    invoice_id: int
    amount: float
    payment_mode: str = "cash"
    payment_gateway: Optional[str] = None
    notes: Optional[str] = None


class PaymentGatewayCreate(BaseModel):
    gateway: str
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    payu_merchant_key: Optional[str] = None
    payu_merchant_salt: Optional[str] = None
    is_default: bool = False


class PaymentLinkCreate(BaseModel):
    invoice_id: int
    expires_in_hours: int = 24
    description: Optional[str] = None


# Helper functions
def generate_invoice_number():
    """Generate unique invoice number"""
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = str(uuid.uuid4())[:8].upper()
    return f"INV-{date_str}-{random_str}"


def generate_transaction_id():
    """Generate unique transaction ID"""
    return f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"


def generate_payment_link_id():
    """Generate unique payment link ID"""
    return f"PL-{str(uuid.uuid4())[:12].replace('-', '').upper()}"


# Invoice Endpoints
@router.post("/invoices")
async def create_invoice(invoice_data: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a new invoice"""
    # Generate invoice number
    invoice_number = generate_invoice_number()
    
    # Calculate totals
    subtotal = sum(item.get("quantity", 1) * item.get("unit_price", 0) for item in invoice_data.items)
    total_amount = subtotal
    final_amount = subtotal - invoice_data.discount_amount + invoice_data.tax_amount
    
    # Create invoice
    invoice = Invoice(
        invoice_number=invoice_number,
        patient_id=invoice_data.patient_id,
        branch_id=invoice_data.branch_id,
        total_amount=total_amount,
        discount_amount=invoice_data.discount_amount,
        tax_amount=invoice_data.tax_amount,
        final_amount=final_amount,
        notes=invoice_data.notes,
        referred_by=invoice_data.referred_by
    )
    
    db.add(invoice)
    db.flush()
    
    # Add invoice items
    for item in invoice_data.items:
        invoice_item = InvoiceItem(
            invoice_id=invoice.id,
            item_type=item.get("item_type", "test"),
            item_name=item.get("item_name"),
            item_code=item.get("item_code"),
            quantity=item.get("quantity", 1),
            unit_price=item.get("unit_price", 0),
            total_price=item.get("quantity", 1) * item.get("unit_price", 0),
            test_id=item.get("test_id"),
            product_id=item.get("product_id")
        )
        db.add(invoice_item)
    
    db.commit()
    db.refresh(invoice)
    
    return {
        "success": True,
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "patient_id": invoice.patient_id,
            "total_amount": invoice.total_amount,
            "discount_amount": invoice.discount_amount,
            "tax_amount": invoice.tax_amount,
            "final_amount": invoice.final_amount,
            "status": invoice.status,
            "created_at": invoice.created_at.isoformat()
        }
    }


@router.get("/invoices")
async def list_invoices(
    patient_id: Optional[int] = None,
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List invoices"""
    query = db.query(Invoice)
    
    if patient_id:
        query = query.filter(Invoice.patient_id == patient_id)
    if status:
        query = query.filter(Invoice.status == status)
    if branch_id:
        query = query.filter(Invoice.branch_id == branch_id)
    
    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "patient_id": inv.patient_id,
                "total_amount": inv.total_amount,
                "discount_amount": inv.discount_amount,
                "tax_amount": inv.tax_amount,
                "final_amount": inv.final_amount,
                "status": inv.status,
                "payment_status": inv.payment_status.value if inv.payment_status else None,
                "created_at": inv.created_at.isoformat()
            }
            for inv in invoices
        ]
    }


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Get invoice details"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()
    
    return {
        "success": True,
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "patient_id": invoice.patient_id,
            "branch_id": invoice.branch_id,
            "total_amount": invoice.total_amount,
            "discount_amount": invoice.discount_amount,
            "tax_amount": invoice.tax_amount,
            "final_amount": invoice.final_amount,
            "status": invoice.status,
            "payment_status": invoice.payment_status.value if invoice.payment_status else None,
            "notes": invoice.notes,
            "referred_by": invoice.referred_by,
            "created_at": invoice.created_at.isoformat(),
            "items": [
                {
                    "id": item.id,
                    "item_type": item.item_type,
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                }
                for item in items
            ]
        }
    }


@router.put("/invoices/{invoice_id}")
async def update_invoice(invoice_id: int, invoice_data: InvoiceUpdate, db: Session = Depends(get_db)):
    """Update invoice"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice_data.status:
        invoice.status = invoice_data.status
    if invoice_data.discount_amount is not None:
        invoice.discount_amount = invoice_data.discount_amount
    if invoice_data.tax_amount is not None:
        invoice.tax_amount = invoice_data.tax_amount
    if invoice_data.notes is not None:
        invoice.notes = invoice_data.notes
    
    # Recalculate final amount
    invoice.final_amount = invoice.total_amount - invoice.discount_amount + invoice.tax_amount
    
    db.commit()
    db.refresh(invoice)
    
    return {
        "success": True,
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": invoice.status,
            "final_amount": invoice.final_amount
        }
    }


# Payment Endpoints
@router.post("/payments")
async def create_payment(payment_data: PaymentCreate, db: Session = Depends(get_db)):
    """Create a new payment"""
    invoice = db.query(Invoice).filter(Invoice.id == payment_data.invoice_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Generate transaction ID
    transaction_id = generate_transaction_id()
    
    # Create payment
    payment = Payment(
        invoice_id=payment_data.invoice_id,
        patient_id=invoice.patient_id,
        branch_id=invoice.branch_id,
        amount=payment_data.amount,
        payment_mode=PaymentMode(payment_data.payment_mode) if payment_data.payment_mode else PaymentMode.CASH,
        payment_gateway=PaymentGateway(payment_data.payment_gateway) if payment_data.payment_gateway else PaymentGateway.NONE,
        transaction_id=transaction_id,
        status=PaymentStatus.COMPLETED,
        notes=payment_data.notes
    )
    
    db.add(payment)
    
    # Update invoice status
    paid_amount = sum(p.amount for p in invoice.payments if p.status == PaymentStatus.COMPLETED)
    new_paid_amount = paid_amount + payment_data.amount
    
    if new_paid_amount >= invoice.final_amount:
        invoice.payment_status = PaymentStatus.COMPLETED
        invoice.status = "paid"
        invoice.paid_date = datetime.utcnow()
    elif new_paid_amount > 0:
        invoice.payment_status = PaymentStatus.PENDING
        invoice.status = "partial"
    
    db.commit()
    db.refresh(payment)
    
    return {
        "success": True,
        "payment": {
            "id": payment.id,
            "transaction_id": payment.transaction_id,
            "amount": payment.amount,
            "payment_mode": payment.payment_mode.value if payment.payment_mode else None,
            "status": payment.status.value if payment.status else None,
            "created_at": payment.created_at.isoformat()
        }
    }


@router.get("/payments")
async def list_payments(
    invoice_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List payments"""
    query = db.query(Payment)
    
    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)
    if patient_id:
        query = query.filter(Payment.patient_id == patient_id)
    if status:
        query = query.filter(Payment.status == status)
    
    payments = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "payments": [
            {
                "id": pay.id,
                "transaction_id": pay.transaction_id,
                "invoice_id": pay.invoice_id,
                "patient_id": pay.patient_id,
                "amount": pay.amount,
                "payment_mode": pay.payment_mode.value if pay.payment_mode else None,
                "status": pay.status.value if pay.status else None,
                "created_at": pay.created_at.isoformat()
            }
            for pay in payments
        ]
    }


# Razorpay Integration
@router.post("/razorpay/create-order")
async def create_razorpay_order(
    invoice_id: int,
    amount: float,
    db: Session = Depends(get_db)
):
    """Create Razorpay order"""
    import razorpay
    
    # Get Razorpay settings
    settings = db.query(PaymentSettings).filter(
        PaymentSettings.gateway == PaymentGateway.RAZORPAY,
        PaymentSettings.is_active == True
    ).first()
    
    if not settings or not settings.razorpay_key_id:
        raise HTTPException(status_code=400, detail="Razorpay not configured")
    
    try:
        client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )
        
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        
        order_data = {
            "amount": int(amount * 100),  # Razorpay uses paise
            "currency": "INR",
            "receipt": f"inv_{invoice.invoice_number}",
            "notes": {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number
            }
        }
        
        razorpay_order = client.order.create(data=order_data)
        
        return {
            "success": True,
            "order_id": razorpay_order.get("id"),
            "amount": razorpay_order.get("amount"),
            "currency": razorpay_order.get("currency")
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Razorpay error: {str(e)}")


@router.post("/razorpay/verify-payment")
async def verify_razorpay_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Verify Razorpay payment signature"""
    import razorpay
    
    settings = db.query(PaymentSettings).filter(
        PaymentSettings.gateway == PaymentGateway.RAZORPAY,
        PaymentSettings.is_active == True
    ).first()
    
    if not settings or not settings.razorpay_key_secret:
        raise HTTPException(status_code=400, detail="Razorpay not configured")
    
    try:
        # Verify signature
        client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )
        
        # Create verification payload
        payload = f"{razorpay_order_id}|{razorpay_payment_id}"
        
        # Generate expected signature
        import hmac
        import hashlib
        expected_signature = hmac.new(
            settings.razorpay_key_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if expected_signature == razorpay_signature:
            # Payment verified, create payment record
            invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
            
            transaction_id = generate_transaction_id()
            
            payment = Payment(
                invoice_id=invoice_id,
                patient_id=invoice.patient_id,
                branch_id=invoice.branch_id,
                amount=invoice.final_amount,
                payment_mode=PaymentMode.RAZORPAY,
                payment_gateway=PaymentGateway.RAZORPAY,
                gateway_order_id=razorpay_order_id,
                gateway_payment_id=razorpay_payment_id,
                gateway_signature=razorpay_signature,
                transaction_id=transaction_id,
                status=PaymentStatus.COMPLETED
            )
            
            db.add(payment)
            
            # Update invoice
            invoice.payment_status = PaymentStatus.COMPLETED
            invoice.status = "paid"
            invoice.paid_date = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "message": "Payment verified successfully",
                "transaction_id": transaction_id
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid signature")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Verification error: {str(e)}")


# PayU Integration
@router.post("/payu/create-payment")
async def create_payu_payment(
    invoice_id: int,
    amount: float,
    customer_phone: str,
    customer_email: str,
    db: Session = Depends(get_db)
):
    """Create PayU payment"""
    settings = db.query(PaymentSettings).filter(
        PaymentSettings.gateway == PaymentGateway.PAYU,
        PaymentSettings.is_active == True
    ).first()
    
    if not settings or not settings.payu_merchant_key:
        raise HTTPException(status_code=400, detail="PayU not configured")
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    # Generate transaction ID
    txnid = generate_transaction_id()
    
    # Create payment hash
    hash_string = f"{settings.payu_merchant_key}|{txnid}|{amount}|{invoice.invoice_number}|{customer_email}|||||||||||{settings.payu_merchant_salt}"
    import hashlib
    hash_value = hashlib.sha512(hash_string.encode()).hexdigest()
    
    # PayU payment URL
    payu_url = "https://test.payu.in/_payment" if settings.payu_mode == "test" else "https://secure.payu.in/_payment"
    
    return {
        "success": True,
        "payment_url": payu_url,
        "txnid": txnid,
        "amount": amount,
        "productinfo": invoice.invoice_number,
        "firstname": customer_email.split("@")[0],
        "email": customer_email,
        "phone": customer_phone,
        "hash": hash_value,
        "merchant_key": settings.payu_merchant_key
    }


# Payment Link Endpoints
@router.post("/payment-links")
async def create_payment_link(link_data: PaymentLinkCreate, db: Session = Depends(get_db)):
    """Create payment link for invoice"""
    invoice = db.query(Invoice).filter(Invoice.id == link_data.invoice_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Generate payment link
    link_id = generate_payment_link_id()
    
    # In production, this would generate an actual payment URL
    payment_url = f"https://vaidyavihar.com/pay/{link_id}"
    
    payment_link = PaymentLink(
        invoice_id=link_data.invoice_id,
        link_id=link_id,
        payment_url=payment_url,
        amount=invoice.final_amount,
        expires_at=datetime.utcnow() + timedelta(hours=link_data.expires_in_hours),
        description=link_data.description or f"Payment for Invoice {invoice.invoice_number}"
    )
    
    db.add(payment_link)
    db.commit()
    db.refresh(payment_link)
    
    return {
        "success": True,
        "payment_link": {
            "id": payment_link.id,
            "link_id": payment_link.link_id,
            "payment_url": payment_link.payment_url,
            "amount": payment_link.amount,
            "expires_at": payment_link.expires_at.isoformat()
        }
    }


# Settings Endpoints
@router.post("/settings")
async def create_payment_settings(settings_data: PaymentGatewayCreate, db: Session = Depends(get_db)):
    """Create payment gateway settings"""
    if settings_data.is_default:
        # Reset other defaults
        db.query(PaymentSettings).update({"is_default": False})
    
    settings = PaymentSettings(
        gateway=PaymentGateway(settings_data.gateway),
        razorpay_key_id=settings_data.razorpay_key_id,
        razorpay_key_secret=settings_data.razorpay_key_secret,
        payu_merchant_key=settings_data.payu_merchant_key,
        payu_merchant_salt=settings_data.payu_merchant_salt,
        is_default=settings_data.is_default,
        is_active=True
    )
    
    db.add(settings)
    db.commit()
    db.refresh(settings)
    
    return {
        "success": True,
        "settings": {
            "id": settings.id,
            "gateway": settings.gateway.value if settings.gateway else None,
            "is_active": settings.is_active,
            "is_default": settings.is_default
        }
    }


@router.get("/settings")
async def list_payment_settings(db: Session = Depends(get_db)):
    """List payment gateway settings"""
    settings = db.query(PaymentSettings).all()
    
    return {
        "success": True,
        "settings": [
            {
                "id": s.id,
                "gateway": s.gateway.value if s.gateway else None,
                "is_active": s.is_active,
                "is_default": s.is_default
            }
            for s in settings
        ]
    }

