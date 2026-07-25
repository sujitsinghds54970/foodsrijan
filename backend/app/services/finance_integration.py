from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.daily_entry_module import DailyEntryModule
from app.models.finance import BranchAccount, FinanceExpense, FinanceInvoice, FinanceTransaction


def _to_decimal(value: object) -> Decimal:
    return Decimal(str(value or 0))


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


def ensure_branch_account(db: Session, branch_id: int) -> BranchAccount:
    account = db.query(BranchAccount).filter(BranchAccount.branch_id == branch_id).first()
    if account:
        return account

    account = BranchAccount(
        branch_id=branch_id,
        name="Primary Account",
        opening_balance=Decimal("0.00"),
        current_balance=Decimal("0.00"),
    )
    db.add(account)
    db.flush()
    return account


def apply_transaction_balance(account: BranchAccount, tx_type: str, amount: Decimal) -> None:
    current = _to_decimal(account.current_balance)
    if tx_type == "revenue":
        account.current_balance = current + amount
    elif tx_type == "expense":
        account.current_balance = current - amount
    else:
        account.current_balance = current


def create_transaction(
    db: Session,
    *,
    branch_id: int,
    tx_type: str,
    amount: Decimal,
    description: Optional[str],
    category: Optional[str],
    payment_method: Optional[str],
    reference_id: Optional[str],
    created_by: int,
    tx_date: Optional[datetime] = None,
) -> FinanceTransaction:
    account = ensure_branch_account(db, branch_id)

    tx = FinanceTransaction(
        branch_id=branch_id,
        date=tx_date or datetime.utcnow(),
        type=tx_type,
        amount=amount,
        description=description,
        reference_id=reference_id,
        category=category,
        payment_method=payment_method,
        created_by=created_by,
    )
    db.add(tx)
    apply_transaction_balance(account, tx_type, amount)
    db.flush()
    return tx


def ensure_daily_entry_invoice(
    db: Session,
    *,
    entry: DailyEntryModule,
    created_by: int,
) -> FinanceInvoice:
    reference_id = f"daily_entry:{entry.id}"
    existing = db.query(FinanceInvoice).filter(FinanceInvoice.reference_id == reference_id).first()
    if existing:
        return existing

    total_amount = _to_decimal(entry.total_amount)
    gst_rate = _to_decimal(entry.tax_percent)
    divisor = Decimal("100") + gst_rate
    tax_amount = (total_amount * gst_rate / divisor) if divisor > 0 else Decimal("0")

    invoice = FinanceInvoice(
        invoice_number=_generate_invoice_number(db),
        branch_id=entry.branch_id,
        patient_id=None,
        patient_name=entry.patient_name,
        date=entry.auto_entry_datetime or datetime.utcnow(),
        total_amount=total_amount,
        tax_amount=tax_amount.quantize(Decimal("0.01")),
        gst_rate=gst_rate,
        status="paid" if bool(entry.is_paid) else "pending",
        due_date=entry.auto_entry_datetime,
        pdf_url=entry.bill_pdf_url,
        reference_id=reference_id,
        created_by=created_by,
    )
    db.add(invoice)
    db.flush()
    return invoice


def ensure_daily_entry_revenue(
    db: Session,
    *,
    entry: DailyEntryModule,
    created_by: int,
) -> Optional[FinanceTransaction]:
    if not bool(entry.is_paid):
        return None

    reference_id = f"daily_entry:{entry.id}"
    existing = (
        db.query(FinanceTransaction)
        .filter(
            FinanceTransaction.reference_id == reference_id,
            FinanceTransaction.type == "revenue",
        )
        .first()
    )
    if existing:
        return existing

    return create_transaction(
        db,
        branch_id=entry.branch_id,
        tx_type="revenue",
        amount=_to_decimal(entry.total_amount),
        description=f"Daily entry payment from {entry.patient_name}",
        category="daily_entry",
        payment_method=entry.payment_method,
        reference_id=reference_id,
        created_by=created_by,
        tx_date=entry.auto_entry_datetime,
    )


def create_stock_purchase_expense(
    db: Session,
    *,
    branch_id: int,
    item_name: str,
    quantity: float,
    unit_cost: Decimal,
    notes: Optional[str],
    created_by: int,
    reference_id: str,
    payment_method: Optional[str] = None,
) -> FinanceExpense:
    amount = _to_decimal(quantity) * _to_decimal(unit_cost)

    expense = FinanceExpense(
        branch_id=branch_id,
        date=datetime.utcnow(),
        category="inventory_purchase",
        amount=amount.quantize(Decimal("0.01")),
        description=notes or f"Stock purchase for {item_name} (qty: {quantity})",
        attachment_url=None,
        approved_by=created_by,
        status="approved",
        created_by=created_by,
        payment_method=payment_method,
        reference_id=reference_id,
    )
    db.add(expense)

    create_transaction(
        db,
        branch_id=branch_id,
        tx_type="expense",
        amount=amount.quantize(Decimal("0.01")),
        description=expense.description,
        category=expense.category,
        payment_method=payment_method,
        reference_id=reference_id,
        created_by=created_by,
    )

    db.flush()
    return expense
