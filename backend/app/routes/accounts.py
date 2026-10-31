from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import case, extract, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, User
from app.models.finance import BranchAccount, FinanceExpense, FinanceInvoice, FinanceTransaction
from app.services.finance_integration import create_transaction, ensure_branch_account
from app.utils.auth_system import get_current_user, is_super_ceo_user

router = APIRouter()
UPLOAD_DIR = Path("uploads/finance")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _generate_invoice_pdf_file(invoice: FinanceInvoice) -> str:
    file_name = f"invoice-{invoice.invoice_number}.pdf"
    output_path = UPLOAD_DIR / file_name

    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "Vaidya Vihar Diagnostic")
    y -= 28

    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Invoice Number: {invoice.invoice_number}")
    y -= 18
    c.drawString(50, y, f"Invoice Date: {invoice.date.strftime('%Y-%m-%d %H:%M')}")
    y -= 18
    c.drawString(50, y, f"Customer Name: {invoice.patient_name or '-'}")
    y -= 18
    c.drawString(50, y, f"Status: {invoice.status}")
    y -= 30

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Amount Summary")
    y -= 20

    c.setFont("Helvetica", 11)
    total_amount = Decimal(str(invoice.total_amount or 0))
    tax_amount = Decimal(str(invoice.tax_amount or 0))
    taxable_amount = total_amount - tax_amount

    c.drawString(50, y, f"Taxable Amount: Rs {float(taxable_amount):,.2f}")
    y -= 18
    c.drawString(50, y, f"GST ({float(invoice.gst_rate or 0):.2f}%): Rs {float(tax_amount):,.2f}")
    y -= 18
    c.drawString(50, y, f"Total Amount: Rs {float(total_amount):,.2f}")
    y -= 30

    if invoice.due_date:
        c.drawString(50, y, f"Due Date: {invoice.due_date.strftime('%Y-%m-%d')}")
        y -= 18

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 40, "This is a system-generated invoice.")

    c.showPage()
    c.save()
    return f"/api/files/finance/{file_name}"


def _require_finance_role(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["branch_admin", "branch_director"] and not is_super_ceo_user(current_user):
        raise HTTPException(status_code=403, detail="Finance access denied")
    return current_user


def _resolve_branch_id(db: Session, current_user: User, requested_branch_id: Optional[int]) -> int:
    if is_super_ceo_user(current_user):
        if requested_branch_id is None:
            first_branch = db.query(Branch).order_by(Branch.id.asc()).first()
            if not first_branch:
                raise HTTPException(status_code=404, detail="Branch not found")
            return first_branch.id
        return requested_branch_id

    if not current_user.branch_id:
        raise HTTPException(status_code=403, detail="User is not assigned to a branch")

    if requested_branch_id and requested_branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied for requested branch")

    return int(current_user.branch_id)


class BranchAccountOut(BaseModel):
    id: int
    branch_id: int
    name: str
    opening_balance: Decimal
    current_balance: Decimal

    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    branch_id: Optional[int] = None
    date: Optional[datetime] = None
    type: str = Field(..., pattern="^(revenue|expense|transfer)$")
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    reference_id: Optional[str] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None


class TransactionOut(BaseModel):
    id: int
    branch_id: int
    date: datetime
    type: str
    amount: Decimal
    description: Optional[str]
    reference_id: Optional[str]
    category: Optional[str]
    payment_method: Optional[str]
    created_by: int

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    branch_id: Optional[int] = None
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    date: Optional[datetime] = None
    total_amount: Decimal = Field(..., gt=0)
    tax_amount: Decimal = Field(0, ge=0)
    gst_rate: Decimal = Field(0, ge=0)
    status: str = Field("pending", pattern="^(pending|paid|cancelled)$")
    due_date: Optional[datetime] = None
    pdf_url: Optional[str] = None
    reference_id: Optional[str] = None


class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    patient_id: Optional[int]
    patient_name: Optional[str]
    branch_id: int
    date: datetime
    total_amount: Decimal
    tax_amount: Decimal
    gst_rate: Decimal
    status: str
    due_date: Optional[datetime]
    pdf_url: Optional[str]
    reference_id: Optional[str]

    class Config:
        from_attributes = True


class ExpenseCreate(BaseModel):
    branch_id: Optional[int] = None
    date: Optional[datetime] = None
    category: str
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    attachment_url: Optional[str] = None
    status: str = Field("pending", pattern="^(pending|approved|rejected)$")
    payment_method: Optional[str] = None
    reference_id: Optional[str] = None


class ExpenseOut(BaseModel):
    id: int
    branch_id: int
    date: datetime
    category: str
    amount: Decimal
    description: Optional[str]
    attachment_url: Optional[str]
    approved_by: Optional[int]
    status: str
    payment_method: Optional[str]
    reference_id: Optional[str]

    class Config:
        from_attributes = True


@router.get("/api/branch-accounts", response_model=List[BranchAccountOut])
def list_branch_accounts(
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    resolved_branch = _resolve_branch_id(db, current_user, branch_id) if branch_id or not is_super_ceo_user(current_user) else None

    query = db.query(BranchAccount)
    if resolved_branch:
        query = query.filter(BranchAccount.branch_id == resolved_branch)
    return query.order_by(BranchAccount.id.desc()).all()


@router.get("/api/transactions", response_model=List[TransactionOut])
def list_transactions(
    branch_id: Optional[int] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    resolved_branch = _resolve_branch_id(db, current_user, branch_id)
    query = db.query(FinanceTransaction).filter(FinanceTransaction.branch_id == resolved_branch)

    if start:
        query = query.filter(FinanceTransaction.date >= start)
    if end:
        query = query.filter(FinanceTransaction.date <= end)
    if type:
        query = query.filter(FinanceTransaction.type == type)

    return query.order_by(FinanceTransaction.date.desc()).all()


@router.post("/api/transactions", response_model=TransactionOut, status_code=201)
def create_manual_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    resolved_branch = _resolve_branch_id(db, current_user, payload.branch_id)
    tx = create_transaction(
        db,
        branch_id=resolved_branch,
        tx_type=payload.type,
        amount=payload.amount,
        description=payload.description,
        category=payload.category,
        payment_method=payload.payment_method,
        reference_id=payload.reference_id,
        created_by=current_user.id,
        tx_date=payload.date,
    )
    db.commit()
    db.refresh(tx)
    return tx


def _generate_invoice_number(db: Session) -> str:
    stamp = datetime.utcnow().strftime("%Y%m")
    prefix = f"FIN-INV-{stamp}-"
    latest = (
        db.query(FinanceInvoice)
        .filter(FinanceInvoice.invoice_number.like(f"{prefix}%"))
        .order_by(FinanceInvoice.id.desc())
        .first()
    )
    if not latest:
        seq = 1
    else:
        try:
            seq = int(latest.invoice_number.split("-")[-1]) + 1
        except Exception:
            seq = latest.id + 1
    return f"{prefix}{seq:04d}"


@router.get("/api/invoices", response_model=List[InvoiceOut])
def list_invoices(
    branch_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    resolved_branch = _resolve_branch_id(db, current_user, branch_id)
    query = db.query(FinanceInvoice).filter(FinanceInvoice.branch_id == resolved_branch)
    if status:
        query = query.filter(FinanceInvoice.status == status)
    return query.order_by(FinanceInvoice.date.desc()).all()


@router.post("/api/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    resolved_branch = _resolve_branch_id(db, current_user, payload.branch_id)

    invoice = FinanceInvoice(
        invoice_number=_generate_invoice_number(db),
        branch_id=resolved_branch,
        patient_id=payload.patient_id,
        patient_name=payload.patient_name,
        date=payload.date or datetime.utcnow(),
        total_amount=payload.total_amount,
        tax_amount=payload.tax_amount,
        gst_rate=payload.gst_rate,
        status=payload.status,
        due_date=payload.due_date,
        pdf_url=payload.pdf_url,
        reference_id=payload.reference_id,
        created_by=current_user.id,
    )
    db.add(invoice)

    if payload.status == "paid":
        create_transaction(
            db,
            branch_id=resolved_branch,
            tx_type="revenue",
            amount=payload.total_amount,
            description=f"Invoice paid: {invoice.invoice_number}",
            category="invoice",
            payment_method="invoice",
            reference_id=f"invoice:{invoice.invoice_number}",
            created_by=current_user.id,
            tx_date=payload.date,
        )

    db.commit()
    db.refresh(invoice)
    return invoice


@router.put("/api/invoices/{invoice_id}/mark-paid", response_model=InvoiceOut)
def mark_invoice_paid(
    invoice_id: int,
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    invoice = db.query(FinanceInvoice).filter(FinanceInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    resolved_branch = _resolve_branch_id(db, current_user, branch_id or invoice.branch_id)
    if invoice.branch_id != resolved_branch:
        raise HTTPException(status_code=403, detail="Access denied")

    invoice.status = "paid"

    tx_ref = f"invoice:{invoice.invoice_number}"
    existing_tx = (
        db.query(FinanceTransaction)
        .filter(FinanceTransaction.reference_id == tx_ref, FinanceTransaction.type == "revenue")
        .first()
    )
    if not existing_tx:
        create_transaction(
            db,
            branch_id=resolved_branch,
            tx_type="revenue",
            amount=invoice.total_amount,
            description=f"Invoice paid: {invoice.invoice_number}",
            category="invoice",
            payment_method="invoice",
            reference_id=tx_ref,
            created_by=current_user.id,
            tx_date=datetime.utcnow(),
        )

    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/api/invoices/{invoice_id}/generate-pdf")
def generate_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    invoice = db.query(FinanceInvoice).filter(FinanceInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    _resolve_branch_id(db, current_user, invoice.branch_id)
    invoice.pdf_url = _generate_invoice_pdf_file(invoice)
    db.commit()
    db.refresh(invoice)
    return {"message": "Invoice PDF generated", "pdf_url": invoice.pdf_url}


@router.post("/api/invoices/{invoice_id}/send")
def send_invoice(
    invoice_id: int,
    request: Request,
    channel: str = Query(..., pattern="^(email|whatsapp)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    invoice = db.query(FinanceInvoice).filter(FinanceInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    _resolve_branch_id(db, current_user, invoice.branch_id)

    if not invoice.pdf_url:
        invoice.pdf_url = _generate_invoice_pdf_file(invoice)
        db.commit()
        db.refresh(invoice)

    public_base_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    request_base_url = str(request.base_url).rstrip("/") if request else ""
    base_url = public_base_url or request_base_url

    if invoice.pdf_url.startswith("http"):
        full_pdf_url = invoice.pdf_url
    else:
        full_pdf_url = f"{base_url}{invoice.pdf_url}" if base_url else invoice.pdf_url

    body_text = (
        f"Invoice {invoice.invoice_number} for {invoice.patient_name or 'Customer'} is ready.\n"
        f"Download PDF: {full_pdf_url}"
    )

    if channel == "email":
        channel_url = f"mailto:?subject={quote(f'Invoice {invoice.invoice_number}')}&body={quote(body_text)}"
    else:
        channel_url = f"https://wa.me/?text={quote(body_text)}"

    return {
        "message": f"Invoice link prepared for {channel}",
        "invoice_id": invoice.id,
        "channel": channel,
        "channel_url": channel_url,
        "pdf_url": invoice.pdf_url,
        "full_pdf_url": full_pdf_url,
    }


@router.get("/api/expenses", response_model=List[ExpenseOut])
def list_expenses(
    branch_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    resolved_branch = _resolve_branch_id(db, current_user, branch_id)
    query = db.query(FinanceExpense).filter(FinanceExpense.branch_id == resolved_branch)
    if status:
        query = query.filter(FinanceExpense.status == status)
    return query.order_by(FinanceExpense.date.desc()).all()


@router.post("/api/expenses", response_model=ExpenseOut, status_code=201)
async def create_expense(
    branch_id: Optional[int] = Form(None),
    date: Optional[str] = Form(None),
    category: str = Form(...),
    amount: Decimal = Form(...),
    description: Optional[str] = Form(None),
    status: str = Form("pending"),
    payment_method: Optional[str] = Form(None),
    reference_id: Optional[str] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    resolved_branch = _resolve_branch_id(db, current_user, branch_id)
    expense_date = datetime.fromisoformat(date) if date else datetime.utcnow()

    attachment_url = None
    if attachment:
        suffix = Path(attachment.filename or "receipt").suffix or ".bin"
        file_name = f"receipt-{uuid4().hex}{suffix}"
        output = UPLOAD_DIR / file_name
        payload = await attachment.read()
        output.write_bytes(payload)
        attachment_url = f"/uploads/finance/{file_name}"

    expense = FinanceExpense(
        branch_id=resolved_branch,
        date=expense_date,
        category=category,
        amount=amount,
        description=description,
        attachment_url=attachment_url,
        approved_by=current_user.id if status == "approved" else None,
        status=status,
        created_by=current_user.id,
        payment_method=payment_method,
        reference_id=reference_id,
    )
    db.add(expense)

    if status == "approved":
        create_transaction(
            db,
            branch_id=resolved_branch,
            tx_type="expense",
            amount=amount,
            description=description or f"Expense: {category}",
            category=category,
            payment_method=payment_method,
            reference_id=reference_id or f"expense:{uuid4().hex[:8]}",
            created_by=current_user.id,
            tx_date=expense_date,
        )

    db.commit()
    db.refresh(expense)
    return expense


@router.put("/api/expenses/{expense_id}/approve", response_model=ExpenseOut)
def approve_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    expense = db.query(FinanceExpense).filter(FinanceExpense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    _resolve_branch_id(db, current_user, expense.branch_id)
    expense.status = "approved"
    expense.approved_by = current_user.id

    tx_ref = expense.reference_id or f"expense:{expense.id}"
    existing_tx = (
        db.query(FinanceTransaction)
        .filter(FinanceTransaction.reference_id == tx_ref, FinanceTransaction.type == "expense")
        .first()
    )
    if not existing_tx:
        create_transaction(
            db,
            branch_id=expense.branch_id,
            tx_type="expense",
            amount=expense.amount,
            description=expense.description or f"Expense approved: {expense.category}",
            category=expense.category,
            payment_method=expense.payment_method,
            reference_id=tx_ref,
            created_by=current_user.id,
            tx_date=expense.date,
        )

    db.commit()
    db.refresh(expense)
    return expense


@router.get("/api/orders/profit-loss")
def profit_loss_report(
    start: datetime = Query(...),
    end: datetime = Query(...),
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    resolved_branch = _resolve_branch_id(db, current_user, branch_id)

    totals = (
        db.query(
            func.coalesce(func.sum(case((FinanceTransaction.type == "revenue", FinanceTransaction.amount), else_=0)), 0).label("revenue"),
            func.coalesce(func.sum(case((FinanceTransaction.type == "expense", FinanceTransaction.amount), else_=0)), 0).label("expense"),
        )
        .filter(
            FinanceTransaction.branch_id == resolved_branch,
            FinanceTransaction.date >= start,
            FinanceTransaction.date <= end,
        )
        .first()
    )

    revenue = Decimal(str(totals.revenue or 0))
    expense = Decimal(str(totals.expense or 0))
    net = revenue - expense

    return {
        "branch_id": resolved_branch,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "revenue": float(revenue),
        "expense": float(expense),
        "net_profit": float(net),
    }


@router.get("/api/orders/gst")
def gst_report(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_finance_role),
):
    resolved_branch = _resolve_branch_id(db, current_user, branch_id)

    invoices = (
        db.query(FinanceInvoice)
        .filter(
            FinanceInvoice.branch_id == resolved_branch,
            extract("month", FinanceInvoice.date) == month,
            extract("year", FinanceInvoice.date) == year,
        )
        .all()
    )

    taxable_amount = sum(Decimal(str(item.total_amount or 0)) - Decimal(str(item.tax_amount or 0)) for item in invoices)
    gst_amount = sum(Decimal(str(item.tax_amount or 0)) for item in invoices)

    return {
        "branch_id": resolved_branch,
        "month": month,
        "year": year,
        "invoice_count": len(invoices),
        "taxable_amount": float(taxable_amount),
        "gst_amount": float(gst_amount),
    }
