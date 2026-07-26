"""
Branch Director Financial Command Center - Payment Tracking & Reconciliation APIs.

All data is strictly scoped to the authenticated user's branch_id.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import re
import threading
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Sequence, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal, get_db
from app.models import Branch, DailyEntry, Patient, User
from app.models.branch_bank_details import BranchBankDetails
from app.models.patient import PatientProfile
from app.models.payment import InsuranceClaim, Invoice, Payment, PaymentMode, PaymentReminder, PaymentStatus, ReconciliationLog, Refund
from app.services.email_service import get_email_service
from app.services.sms_service import get_sms_service
from app.utils.auth_system import get_current_user

router = APIRouter(prefix="/api/branch/payments", tags=["Branch Payments"])


COMPLETED_STATUSES = {"completed", "paid", "reconciled"}
PENDING_STATUSES = {"pending", "processing", "partial", "partially paid"}
FAILED_STATUSES = {"failed", "cancelled", "refunded"}
METHOD_LABELS = {"cash": "Cash", "upi": "UPI", "qr": "UPI", "card": "Card", "insurance": "Insurance"}
METHOD_BUCKETS = ("Cash", "UPI", "Card", "Insurance", "Other")

_reminder_scheduler_lock = threading.Lock()
_reminder_scheduler_stop = threading.Event()
_reminder_scheduler_thread: Optional[threading.Thread] = None


class AgingBreakdown(BaseModel):
    zero_to_30: float = Field(alias="0_30")
    thirty_one_to_60: float = Field(alias="31_60")
    sixty_one_to_90: float = Field(alias="61_90")
    ninety_plus: float = Field(alias="90_plus")

    class Config:
        populate_by_name = True


class HealthScoreResponse(BaseModel):
    score: int
    status: str
    collection_rate: float
    total_billed: float
    total_collected: float
    pending_dues_total: float
    aging_breakdown: Dict[str, float]
    last_updated: str
    branch_name: Optional[str] = None


class TransactionDetail(BaseModel):
    id: str
    source: str
    patient_name: str
    patient_id: Optional[str] = None
    patient_mobile: Optional[str] = None
    patient_email: Optional[str] = None
    test_name: str
    test_package: Optional[str] = None
    amount: float
    total_amount: float
    method: str
    status: str
    timestamp: str
    payment_date: str
    receipt_number: Optional[str] = None
    discount_applied: float = 0.0
    notes: Optional[str] = None
    invoice_number: Optional[str] = None
    gateway_reference: Optional[str] = None


class PaginatedTransactionsResponse(BaseModel):
    items: List[TransactionDetail]
    total: int
    skip: int
    limit: int


class TodayCollections(BaseModel):
    total: float
    cash: float
    upi: float
    card: float
    insurance: float
    other: float
    timestamp: str


class ReconciliationStatus(BaseModel):
    transaction_id: str
    status: str
    message: str
    matched_reference: Optional[str] = None


class PaymentReadinessResponse(BaseModel):
    score: int
    status: str
    branch_name: Optional[str] = None
    pending_invoices: int
    due_soon_invoices: int
    overdue_invoices: int
    blockers: List[str]
    checklist: List[str]
    last_updated: str


class SmartAlertItem(BaseModel):
    alert_id: int
    category: str
    severity: str
    title: str
    message: str
    amount: float = 0.0
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    source: Optional[str] = None
    created_at: str


class BulkReconciliationItem(BaseModel):
    transaction_id: str
    status: str
    message: str
    matched_reference: Optional[str] = None


class BulkReconciliationResponse(BaseModel):
    total_transactions: int
    reconciled: int
    pending: int
    discrepancy: int
    results: List[BulkReconciliationItem]
    created_at: str


class SettlementReport(BaseModel):
    date: str
    gateway: str
    amount_collected: float
    amount_settled: float
    discrepancy: float
    settlement_date: str
    bank_name: Optional[str] = None
    current_balance: Optional[float] = None
    status: str


class DiscrepancyAlert(BaseModel):
    alert_id: int
    type: str
    description: str
    amount: float
    related_transaction_id: Optional[str] = None
    severity: str
    created_at: str


class BankReconcileRow(BaseModel):
    row_number: int
    bank_reference: str
    bank_date: Optional[str] = None
    bank_amount: float
    system_reference: Optional[str] = None
    system_amount: Optional[float] = None
    status: str
    reason: str


class BankReconcileResponse(BaseModel):
    filename: str
    total_rows: int
    matched_rows: int
    discrepancy_rows: int
    unmatched_rows: int
    rows: List[BankReconcileRow]


def _require_branch_id(current_user: User) -> int:
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="User must be assigned to a branch")
    return int(current_user.branch_id)


def _parse_date(raw: Optional[str], field_name: str) -> Optional[date]:
    if raw is None or str(raw).strip() == "":
        return None
    value = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value).date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: {value}") from exc


def _parse_date_range(raw: Optional[str]) -> Tuple[Optional[date], Optional[date]]:
    if not raw:
        return None, None

    value = raw.strip()
    for separator in ("|", ",", " to ", " - "):
        if separator in value:
            left, right = value.split(separator, 1)
            return _parse_date(left, "start date"), _parse_date(right, "end date")

    single = _parse_date(value, "date range")
    return single, single


def _normalize_key(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, PaymentStatus):
        return value.value.lower()
    if isinstance(value, PaymentMode):
        return value.value.lower()
    return str(value).strip().lower()


def _display_method(value: object) -> str:
    key = _normalize_key(value)
    return METHOD_LABELS.get(key, str(value).strip().title() if value is not None else "Other")


def _bucket_method(value: object) -> str:
    method = _normalize_key(value)
    if method == "qr":
        return "UPI"
    if method in {"cash", "upi", "card", "insurance"}:
        return method.capitalize() if method != "upi" else "UPI"
    return "Other"


def _normalize_status(value: object, fallback: Optional[str] = None) -> str:
    key = _normalize_key(value)
    if key in {"paid", "completed", "reconciled"}:
        return "Completed"
    if key in {"partial", "partially paid"}:
        return "Partially Paid"
    if key in {"failed"}:
        return "Failed"
    if key in {"refunded"}:
        return "Refunded"
    if key in {"pending", "processing", "cancelled"}:
        return "Pending"
    if fallback:
        return fallback
    return str(value).strip().title() if value is not None else "Pending"


def _amount(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return 0.0


def _safe_date_from_datetime(value: Optional[datetime]) -> Optional[date]:
    if value is None:
        return None
    return value.date()


def _safe_datetime(value: Optional[datetime], fallback: Optional[datetime] = None) -> datetime:
    if value is not None:
        return value
    return fallback or datetime.utcnow()


def _patient_full_name(patient: Optional[Patient]) -> str:
    if not patient:
        return "Unknown Patient"
    name = f"{patient.first_name or ''} {patient.last_name or ''}".strip()
    return name or patient.patient_id or "Unknown Patient"


def _patient_identifier(patient: Optional[Patient], profile: Optional[PatientProfile]) -> Optional[str]:
    if profile and profile.patient_code:
        return profile.patient_code
    if patient and patient.patient_id:
        return patient.patient_id
    return None


def _test_name_from_invoice(invoice: Invoice) -> str:
    item_names = [item.item_name for item in (invoice.items or []) if getattr(item, "item_name", None)]
    if item_names:
        return ", ".join(item_names[:3])
    if invoice.notes:
        return invoice.notes[:80]
    return invoice.invoice_number


def _build_payment_event(payment: Payment, profile_map: Dict[int, PatientProfile]) -> Tuple[Dict[str, object], float]:
    invoice = payment.invoice
    patient = invoice.patient if invoice else None
    profile = profile_map.get(invoice.patient_id) if invoice and invoice.patient_id else None
    amount = _amount(payment.amount)
    transaction = {
        "id": f"payment-{payment.id}",
        "source": "Payment",
        "patient_name": _patient_full_name(patient),
        "patient_id": _patient_identifier(patient, profile),
        "patient_mobile": (profile.mobile if profile else getattr(patient, "phone", None)) if patient or profile else None,
        "patient_email": profile.email if profile else getattr(patient, "email", None),
        "test_name": _test_name_from_invoice(invoice) if invoice else "Invoice Payment",
        "test_package": _test_name_from_invoice(invoice) if invoice else "Invoice Payment",
        "amount": amount,
        "total_amount": _amount(invoice.final_amount if invoice else amount),
        "method": _display_method(payment.payment_mode),
        "status": _normalize_status(payment.status),
        "timestamp": _safe_datetime(payment.payment_date or payment.created_at).isoformat(),
        "payment_date": _safe_datetime(payment.payment_date or payment.created_at).date().isoformat(),
        "receipt_number": payment.reference_number or payment.transaction_id or payment.gateway_payment_id or payment.gateway_transaction_id,
        "discount_applied": _amount(invoice.discount_amount) if invoice else 0.0,
        "notes": payment.notes or (invoice.notes if invoice else None),
        "invoice_number": invoice.invoice_number if invoice else None,
        "gateway_reference": payment.gateway_transaction_id or payment.gateway_payment_id or payment.transaction_id or payment.upi_transaction_id,
    }
    return transaction, amount


def _daily_test_name(entry: DailyEntry) -> str:
    raw = entry.test_names
    if isinstance(raw, (list, tuple)):
        return ", ".join(str(item) for item in raw)
    if raw is None:
        return "Daily Entry"
    text = str(raw).strip()
    return text or "Daily Entry"


def _load_patient_profiles(db: Session, patient_ids: Sequence[int]) -> Dict[int, PatientProfile]:
    ids = [int(pid) for pid in patient_ids if pid]
    if not ids:
        return {}
    profiles = db.query(PatientProfile).filter(PatientProfile.patient_id.in_(ids)).all()
    return {int(profile.patient_id): profile for profile in profiles if profile.patient_id is not None}


def _invoice_paid_amount(invoice: Invoice) -> float:
    return sum(
        _amount(payment.amount)
        for payment in (invoice.payments or [])
        if _normalize_status(payment.status) == "Completed"
    )


def _build_daily_entry_event(entry: DailyEntry, profile_map: Dict[int, PatientProfile]) -> Tuple[Dict[str, object], float, float, Optional[date]]:
    profile = profile_map.get(entry.patient_id) if entry.patient_id else None
    patient = entry.patient
    billed_amount = _amount(entry.total_amount)
    collected_amount = min(_amount(entry.amount_paid), billed_amount) if billed_amount else _amount(entry.amount_paid)
    outstanding = max(billed_amount - collected_amount, 0.0)
    status = _normalize_status(entry.payment_status)
    if collected_amount >= billed_amount and billed_amount > 0:
        status = "Completed"
    elif collected_amount > 0:
        status = "Partially Paid"
    else:
        status = "Pending"

    transaction = {
        "id": f"daily-{entry.id}",
        "source": "Daily Entry",
        "patient_name": entry.patient_name or _patient_full_name(patient),
        "patient_id": _patient_identifier(patient, profile),
        "patient_mobile": (profile.mobile if profile else getattr(patient, "phone", None)) or entry.patient_mobile,
        "patient_email": profile.email if profile else getattr(patient, "email", None),
        "test_name": _daily_test_name(entry),
        "test_package": _daily_test_name(entry),
        "amount": collected_amount,
        "total_amount": billed_amount,
        "method": _display_method(entry.payment_mode),
        "status": status,
        "timestamp": _safe_datetime(entry.entry_time or entry.entry_date or entry.created_at).isoformat(),
        "payment_date": _safe_datetime(entry.entry_date or entry.entry_time or entry.created_at).date().isoformat(),
        "receipt_number": f"DE-{entry.id:06d}",
        "discount_applied": _amount(entry.discount),
        "notes": entry.notes,
        "invoice_number": None,
        "gateway_reference": entry.referred_by,
    }
    aging_date = _safe_date_from_datetime(entry.entry_date or entry.entry_time or entry.created_at)
    return transaction, billed_amount, collected_amount, aging_date if outstanding > 0 else None


def _collect_transactions(db: Session, branch_id: int) -> Tuple[List[Dict[str, object]], Dict[str, float]]:
    invoices = (
        db.query(Invoice)
        .filter(Invoice.branch_id == branch_id)
        .options(joinedload(Invoice.patient), joinedload(Invoice.items), joinedload(Invoice.payments))
        .order_by(Invoice.created_at.desc())
        .all()
    )
    payments = (
        db.query(Payment)
        .filter(Payment.branch_id == branch_id)
        .options(joinedload(Payment.invoice).joinedload(Invoice.patient), joinedload(Payment.invoice).joinedload(Invoice.items))
        .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        .all()
    )
    daily_entries = (
        db.query(DailyEntry)
        .filter(DailyEntry.branch_id == branch_id)
        .options(joinedload(DailyEntry.patient))
        .order_by(DailyEntry.entry_date.desc(), DailyEntry.entry_time.desc())
        .all()
    )

    profile_ids = {invoice.patient_id for invoice in invoices if invoice.patient_id}
    profile_ids.update(entry.patient_id for entry in daily_entries if entry.patient_id)
    profile_map = _load_patient_profiles(db, list(profile_ids))

    events: List[Dict[str, object]] = []
    billed_total = 0.0
    collected_total = 0.0
    aging_buckets = {"0_30": 0.0, "31_60": 0.0, "61_90": 0.0, "90_plus": 0.0}
    today = datetime.utcnow().date()

    for payment in payments:
        event, collected_amount = _build_payment_event(payment, profile_map)
        events.append(event)
        collected_total += collected_amount

    for invoice in invoices:
        billed_amount = _amount(invoice.final_amount or invoice.total_amount)
        collected_amount = _invoice_paid_amount(invoice)
        billed_total += billed_amount
        aging_date = _safe_date_from_datetime(invoice.due_date or invoice.invoice_date or invoice.created_at)
        if aging_date and billed_amount > collected_amount:
            age_days = max((today - aging_date).days, 0)
            outstanding = max(billed_amount - collected_amount, 0.0)
            if age_days <= 30:
                aging_buckets["0_30"] += outstanding
            elif age_days <= 60:
                aging_buckets["31_60"] += outstanding
            elif age_days <= 90:
                aging_buckets["61_90"] += outstanding
            else:
                aging_buckets["90_plus"] += outstanding

    for entry in daily_entries:
        event, billed_amount, collected_amount, aging_date = _build_daily_entry_event(entry, profile_map)
        events.append(event)
        billed_total += billed_amount
        collected_total += collected_amount
        if aging_date:
            age_days = max((today - aging_date).days, 0)
            if age_days <= 30:
                aging_buckets["0_30"] += max(billed_amount - collected_amount, 0.0)
            elif age_days <= 60:
                aging_buckets["31_60"] += max(billed_amount - collected_amount, 0.0)
            elif age_days <= 90:
                aging_buckets["61_90"] += max(billed_amount - collected_amount, 0.0)
            else:
                aging_buckets["90_plus"] += max(billed_amount - collected_amount, 0.0)

    events.sort(key=lambda item: item["timestamp"], reverse=True)

    metrics = {
        "billed_total": billed_total,
        "collected_total": collected_total,
        "pending_total": max(billed_total - collected_total, 0.0),
        "aging_0_30": aging_buckets["0_30"],
        "aging_31_60": aging_buckets["31_60"],
        "aging_61_90": aging_buckets["61_90"],
        "aging_90_plus": aging_buckets["90_plus"],
        "invoice_count": float(len(invoices)),
        "payment_count": float(len(payments)),
        "daily_entry_count": float(len(daily_entries)),
    }
    return events, metrics


def _collection_rate(billed_total: float, collected_total: float) -> float:
    if billed_total <= 0:
        return 0.0
    return round((collected_total / billed_total) * 100, 2)


def _score_from_metrics(collection_rate: float, pending_total: float, billed_total: float, aging_90_plus: float) -> int:
    if billed_total <= 0:
        return 100
    overdue_pressure = min(((pending_total + aging_90_plus) / billed_total) * 100, 100)
    raw_score = (collection_rate * 0.7) + ((100 - overdue_pressure) * 0.3)
    return max(0, min(100, int(round(raw_score))))


def _score_status(score: int) -> str:
    if score >= 80:
        return "Green"
    if score >= 50:
        return "Yellow"
    return "Red"


def _reconciliation_status_from_snapshot(transaction: Dict[str, object]) -> Tuple[str, str]:
    amount = _amount(transaction["amount"])
    total_amount = _amount(transaction["total_amount"])
    status = _normalize_status(transaction["status"])
    if status == "Completed" and amount >= total_amount > 0:
        return "Reconciled", "Transaction matched against billing record"
    if status == "Partially Paid" or (0 < amount < total_amount):
        return "Pending", "Partial settlement detected and awaiting balance"
    if status == "Failed":
        return "Discrepancy", "Payment failed and requires review"
    return "Pending", "Transaction awaiting settlement confirmation"


def _readiness_score_from_metrics(pending_invoices: int, due_soon_invoices: int, overdue_invoices: int, missing_due_dates: int) -> Tuple[int, str]:
    score = 100
    score -= min(pending_invoices * 4, 30)
    score -= min(due_soon_invoices * 5, 20)
    score -= min(overdue_invoices * 8, 30)
    score -= min(missing_due_dates * 3, 15)
    score = max(0, min(100, score))
    if score >= 80:
        return score, "Green"
    if score >= 50:
        return score, "Yellow"
    return score, "Red"


def _payment_readiness_summary(db: Session, branch_id: int) -> PaymentReadinessResponse:
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    invoices = (
        db.query(Invoice)
        .filter(Invoice.branch_id == branch_id)
        .options(joinedload(Invoice.payments), joinedload(Invoice.patient))
        .all()
    )
    pending_invoices = 0
    due_soon_invoices = 0
    overdue_invoices = 0
    missing_due_dates = 0
    now = datetime.utcnow()
    due_window = now + timedelta(hours=24)

    for invoice in invoices:
        billed_amount = _amount(invoice.final_amount or invoice.total_amount)
        paid_amount = _invoice_paid_amount(invoice)
        if billed_amount <= paid_amount:
            continue
        pending_invoices += 1
        due_date = invoice.due_date or invoice.invoice_date or invoice.created_at
        if not due_date:
            missing_due_dates += 1
            continue
        if due_date <= now:
            overdue_invoices += 1
        elif due_date <= due_window:
            due_soon_invoices += 1

    score, status = _readiness_score_from_metrics(pending_invoices, due_soon_invoices, overdue_invoices, missing_due_dates)
    blockers = []
    checklist = [
        "Invoices generated for current branch cycle",
        "Pending dues tracked against due dates",
        "Reminder automation enabled",
        "Reconciliation queue visible",
    ]
    if pending_invoices == 0:
        blockers.append("No pending invoices detected")
    if due_soon_invoices == 0 and overdue_invoices == 0:
        blockers.append("No dues require immediate payment cycle attention")
    if missing_due_dates > 0:
        blockers.append(f"{missing_due_dates} invoices are missing due dates")
    if overdue_invoices > 0:
        blockers.append(f"{overdue_invoices} invoice(s) are overdue")

    return PaymentReadinessResponse(
        score=score,
        status=status,
        branch_name=branch.name if branch else None,
        pending_invoices=pending_invoices,
        due_soon_invoices=due_soon_invoices,
        overdue_invoices=overdue_invoices,
        blockers=blockers,
        checklist=checklist,
        last_updated=now.isoformat(),
    )


def _smart_payment_alerts(db: Session, branch_id: int) -> List[SmartAlertItem]:
    alerts: List[SmartAlertItem] = []
    alert_id = 1
    dues = _outstanding_due_rows(db, branch_id)
    high_value_dues = [row for row in dues if row.outstanding_amount >= 25000]
    if high_value_dues:
        top_due = high_value_dues[0]
        alerts.append(
            SmartAlertItem(
                alert_id=alert_id,
                category="overdue_large_payment",
                severity="High",
                title=f"Large payment overdue for {top_due.patient_name}",
                message=f"{fmtMoney(top_due.outstanding_amount)} remains outstanding for {top_due.aging_days} days.",
                amount=top_due.outstanding_amount,
                patient_id=top_due.patient_id,
                patient_name=top_due.patient_name,
                source="outstanding-dues",
                created_at=datetime.utcnow().isoformat(),
            )
        )
        alert_id += 1

    transactions, _ = _collect_transactions(db, branch_id)
    for tx in transactions:
        if _normalize_status(tx["status"]) != "Failed":
            continue
        alerts.append(
            SmartAlertItem(
                alert_id=alert_id,
                category="reconciliation_discrepancy",
                severity="Critical",
                title=f"Reconciliation discrepancy detected for {tx['patient_name']}",
                message=f"Transaction {tx.get('receipt_number') or tx.get('invoice_number') or tx['id']} failed and needs review.",
                amount=_amount(tx["amount"]),
                patient_name=str(tx.get("patient_name") or "Unknown"),
                source="transaction-feed",
                created_at=datetime.utcnow().isoformat(),
            )
        )
        alert_id += 1
        break

    denied_claims = (
        db.query(InsuranceClaim)
        .join(Invoice, InsuranceClaim.invoice_id == Invoice.id)
        .join(Patient, InsuranceClaim.patient_id == Patient.id)
        .filter(Invoice.branch_id == branch_id, InsuranceClaim.status.in_(["rejected", "denied", "declined"]))
        .order_by(InsuranceClaim.updated_at.desc())
        .all()
    )
    for claim in denied_claims[:3]:
        patient = db.query(Patient).filter(Patient.id == claim.patient_id, Patient.branch_id == branch_id).first()
        alerts.append(
            SmartAlertItem(
                alert_id=alert_id,
                category="insurance_denied",
                severity="High",
                title=f"Insurance claim denied for { _patient_full_name(patient) }",
                message=claim.rejection_reason or f"Claim {claim.claim_number or claim.id} was denied by the insurer.",
                amount=_amount(claim.claim_amount),
                patient_id=claim.patient_id,
                patient_name=_patient_full_name(patient),
                source="insurance-claims",
                created_at=_safe_datetime(claim.updated_at or claim.created_at).isoformat(),
            )
        )
        alert_id += 1

    if not alerts:
        alerts.append(
            SmartAlertItem(
                alert_id=1,
                category="info",
                severity="Low",
                title="No urgent payment alerts",
                message="The branch payments queue is stable right now.",
                amount=0.0,
                source="system",
                created_at=datetime.utcnow().isoformat(),
            )
        )

    return alerts


def _collections_by_method(transactions: Sequence[Dict[str, object]], today: date) -> Dict[str, float]:
    buckets = {key: 0.0 for key in METHOD_BUCKETS}
    for tx in transactions:
        try:
            tx_date = datetime.fromisoformat(str(tx["payment_date"])).date()
        except ValueError:
            continue
        if tx_date != today:
            continue
        bucket = _bucket_method(tx["method"])
        buckets[bucket] += _amount(tx["amount"])
    return buckets


def _settlement_amounts(transactions: Sequence[Dict[str, object]]) -> Dict[str, float]:
    buckets = {key: 0.0 for key in METHOD_BUCKETS}
    for tx in transactions:
        if tx["status"] != "Completed":
            continue
        bucket = _bucket_method(tx["method"])
        buckets[bucket] += _amount(tx["amount"])
    return buckets


def _find_transaction(transactions: Sequence[Dict[str, object]], transaction_id: str) -> Optional[Dict[str, object]]:
    lookup = transaction_id.strip().lower()
    for tx in transactions:
        if str(tx["id"]).strip().lower() == lookup:
            return tx
        if str(tx.get("receipt_number") or "").strip().lower() == lookup:
            return tx
        if str(tx.get("invoice_number") or "").strip().lower() == lookup:
            return tx
        if str(tx.get("gateway_reference") or "").strip().lower() == lookup:
            return tx
    return None


@router.get("/health-score", response_model=HealthScoreResponse)
def get_health_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    _, metrics = _collect_transactions(db, branch_id)
    collection_rate = _collection_rate(metrics["billed_total"], metrics["collected_total"])
    score = _score_from_metrics(collection_rate, metrics["pending_total"], metrics["billed_total"], metrics["aging_90_plus"])

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    return HealthScoreResponse(
        score=score,
        status=_score_status(score),
        collection_rate=collection_rate,
        total_billed=round(metrics["billed_total"], 2),
        total_collected=round(metrics["collected_total"], 2),
        pending_dues_total=round(metrics["pending_total"], 2),
        aging_breakdown={
            "0_30": round(metrics["aging_0_30"], 2),
            "31_60": round(metrics["aging_31_60"], 2),
            "61_90": round(metrics["aging_61_90"], 2),
            "90_plus": round(metrics["aging_90_plus"], 2),
        },
        last_updated=datetime.utcnow().isoformat(),
        branch_name=branch.name if branch else None,
    )


@router.get("/readiness-score", response_model=PaymentReadinessResponse)
def get_payment_readiness_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    return _payment_readiness_summary(db, branch_id)


@router.get("/feed", response_model=List[TransactionDetail])
def get_transaction_feed(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, _ = _collect_transactions(db, branch_id)
    return [TransactionDetail(**tx) for tx in transactions[:limit]]


@router.get("/transactions", response_model=PaginatedTransactionsResponse)
def get_transactions(
    patient_name: Optional[str] = Query(None),
    date_range: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    amount: Optional[float] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, _ = _collect_transactions(db, branch_id)

    start_date, end_date = _parse_date_range(date_range)
    filtered: List[Dict[str, object]] = []
    patient_query = patient_name.strip().lower() if patient_name else ""
    method_query = _bucket_method(method) if method else ""
    status_query = _normalize_status(status) if status else ""

    for tx in transactions:
        tx_date = datetime.fromisoformat(str(tx["payment_date"])).date()
        if patient_query and patient_query not in str(tx["patient_name"]).lower():
            continue
        if start_date and tx_date < start_date:
            continue
        if end_date and tx_date > end_date:
            continue
        if method_query and _bucket_method(tx["method"]) != method_query:
            continue
        if amount is not None and abs(_amount(tx["amount"]) - float(amount)) > 0.01:
            continue
        if status_query and _normalize_status(tx["status"]) != status_query:
            continue
        filtered.append(tx)

    page_items = filtered[skip : skip + limit]
    return PaginatedTransactionsResponse(
        items=[TransactionDetail(**tx) for tx in page_items],
        total=len(filtered),
        skip=skip,
        limit=limit,
    )


@router.get("/today", response_model=TodayCollections)
def get_today_collections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, _ = _collect_transactions(db, branch_id)
    today = datetime.utcnow().date()
    buckets = _collections_by_method(transactions, today)
    total = sum(buckets.values())
    return TodayCollections(
        total=round(total, 2),
        cash=round(buckets["Cash"], 2),
        upi=round(buckets["UPI"], 2),
        card=round(buckets["Card"], 2),
        insurance=round(buckets["Insurance"], 2),
        other=round(buckets["Other"], 2),
        timestamp=datetime.utcnow().isoformat(),
    )


@router.post("/reconcile", response_model=ReconciliationStatus)
def auto_reconcile_payments(
    transaction_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, _ = _collect_transactions(db, branch_id)
    transaction = _find_transaction(transactions, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    amount = _amount(transaction["amount"])
    total_amount = _amount(transaction["total_amount"])
    status = _normalize_status(transaction["status"])
    if status == "Completed" and amount >= total_amount > 0:
        recon_status = "Reconciled"
        message = "Transaction matched against billing record"
    elif status == "Partially Paid" or (0 < amount < total_amount):
        recon_status = "Pending"
        message = "Partial settlement detected and awaiting balance"
    elif status == "Failed":
        recon_status = "Discrepancy"
        message = "Payment failed and requires review"
    else:
        recon_status = "Pending"
        message = "Transaction awaiting settlement confirmation"

    return ReconciliationStatus(
        transaction_id=str(transaction["id"]),
        status=recon_status,
        message=message,
        matched_reference=transaction.get("invoice_number") or transaction.get("receipt_number") or transaction.get("gateway_reference"),
    )


@router.post("/reconcile/all", response_model=BulkReconciliationResponse)
def auto_reconcile_all_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, _ = _collect_transactions(db, branch_id)
    results: List[BulkReconciliationItem] = []
    reconciled = 0
    pending = 0
    discrepancy = 0

    for transaction in transactions:
        status, message = _reconciliation_status_from_snapshot(transaction)
        if status == "Reconciled":
            reconciled += 1
        elif status == "Discrepancy":
            discrepancy += 1
        else:
            pending += 1
        results.append(
            BulkReconciliationItem(
                transaction_id=str(transaction["id"]),
                status=status,
                message=message,
                matched_reference=transaction.get("invoice_number") or transaction.get("receipt_number") or transaction.get("gateway_reference"),
            )
        )

    db.add(
        ReconciliationLog(
            branch_id=branch_id,
            triggered_by_user_id=current_user.id,
            run_type="one_click",
            total_transactions=len(transactions),
            reconciled_count=reconciled,
            pending_count=pending,
            discrepancy_count=discrepancy,
            metadata_json=json.dumps({"results": [item.dict() for item in results[:100]]}),
        )
    )
    db.commit()

    return BulkReconciliationResponse(
        total_transactions=len(transactions),
        reconciled=reconciled,
        pending=pending,
        discrepancy=discrepancy,
        results=results,
        created_at=datetime.utcnow().isoformat(),
    )


@router.get("/settlement", response_model=List[SettlementReport])
def get_settlement_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, _ = _collect_transactions(db, branch_id)
    settlement_amounts = _settlement_amounts(transactions)
    bank_details = db.query(BranchBankDetails).filter(BranchBankDetails.branch_id == branch_id, BranchBankDetails.is_active.is_(True)).first()

    reports: List[SettlementReport] = []
    for gateway in ("Cash", "UPI", "Card", "Insurance"):
        collected = settlement_amounts[gateway]
        discrepancy = round(collected * (0.0 if gateway == "Cash" else 0.02), 2)
        settled = round(collected - discrepancy, 2)
        reports.append(
            SettlementReport(
                date=datetime.utcnow().date().isoformat(),
                gateway=gateway,
                amount_collected=round(collected, 2),
                amount_settled=settled,
                discrepancy=discrepancy,
                settlement_date=datetime.utcnow().date().isoformat(),
                bank_name=bank_details.bank_name if bank_details else None,
                current_balance=float(bank_details.current_balance) if bank_details and bank_details.current_balance is not None else None,
                status="Settled" if settled >= 0 else "Discrepancy",
            )
        )

    return reports


@router.get("/discrepancy-alerts", response_model=List[DiscrepancyAlert])
def get_discrepancy_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, metrics = _collect_transactions(db, branch_id)
    invoices = (
        db.query(Invoice)
        .filter(Invoice.branch_id == branch_id)
        .options(joinedload(Invoice.payments), joinedload(Invoice.patient))
        .all()
    )
    alerts: List[DiscrepancyAlert] = []
    alert_id = 1
    today = datetime.utcnow().date()

    overdue_count = 0
    partial_count = 0
    failed_count = 0

    for invoice in invoices:
        billed_amount = _amount(invoice.final_amount or invoice.total_amount)
        collected_amount = _invoice_paid_amount(invoice)
        due_date = _safe_date_from_datetime(invoice.due_date or invoice.invoice_date or invoice.created_at)
        if billed_amount > collected_amount and due_date and (today - due_date).days > 0:
            overdue_count += 1
        if 0 < collected_amount < billed_amount:
            partial_count += 1

    for tx in transactions:
        status = _normalize_status(tx["status"])
        if status == "Failed":
            failed_count += 1

    if overdue_count:
        alerts.append(
            DiscrepancyAlert(
                alert_id=alert_id,
                type="missing_record",
                description=f"{overdue_count} overdue transactions remain unsettled",
                amount=round(metrics["pending_total"], 2),
                related_transaction_id=None,
                severity="Warning",
                created_at=datetime.utcnow().isoformat(),
            )
        )
        alert_id += 1

    if partial_count:
        alerts.append(
            DiscrepancyAlert(
                alert_id=alert_id,
                type="amount_mismatch",
                description=f"{partial_count} transactions are only partially paid",
                amount=round(float(partial_count), 2),
                related_transaction_id=None,
                severity="Info",
                created_at=datetime.utcnow().isoformat(),
            )
        )
        alert_id += 1

    if failed_count:
        alerts.append(
            DiscrepancyAlert(
                alert_id=alert_id,
                type="failed_payment",
                description=f"{failed_count} failed payment attempts require review",
                amount=0.0,
                related_transaction_id=None,
                severity="Critical",
                created_at=datetime.utcnow().isoformat(),
            )
        )
        alert_id += 1

    duplicate_refs = {}
    for tx in transactions:
        reference = str(tx.get("gateway_reference") or tx.get("receipt_number") or tx.get("invoice_number") or "").strip()
        if not reference:
            continue
        duplicate_refs.setdefault(reference.lower(), []).append(tx)

    for reference, rows in duplicate_refs.items():
        if len(rows) < 2:
            continue
        alerts.append(
            DiscrepancyAlert(
                alert_id=alert_id,
                type="duplicate_payment",
                description=f"Duplicate payment reference detected: {reference}",
                amount=round(sum(_amount(row["amount"]) for row in rows), 2),
                related_transaction_id=str(rows[0]["id"]),
                severity="Critical",
                created_at=datetime.utcnow().isoformat(),
            )
        )
        alert_id += 1

    return alerts


@router.get("/smart-alerts", response_model=List[SmartAlertItem])
def get_smart_payment_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    return _smart_payment_alerts(db, branch_id)


@router.post("/bank-reconcile", response_model=BankReconcileResponse)
async def bank_reconcile(
    statement: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    if not statement.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV statements are supported")

    transactions, _ = _collect_transactions(db, branch_id)
    rows = list(csv.DictReader(io.StringIO((await statement.read()).decode("utf-8-sig"))))
    matched_rows = 0
    discrepancy_rows = 0
    unmatched_rows = 0
    parsed_rows: List[BankReconcileRow] = []
    used_transaction_ids: set[str] = set()

    def row_value(row: Dict[str, str], keys: Sequence[str]) -> str:
        for key in keys:
            for candidate, value in row.items():
                if candidate and candidate.strip().lower() == key.lower():
                    return str(value or "").strip()
        return ""

    for index, row in enumerate(rows, start=1):
        reference = row_value(row, ("reference", "txn_id", "transaction_id", "utr", "utr_no", "remarks", "description"))
        amount_raw = row_value(row, ("amount", "debit", "credit", "withdrawal"))
        date_raw = row_value(row, ("date", "transaction_date", "value_date", "posted_at"))
        try:
            bank_amount = float(Decimal(amount_raw))
        except (InvalidOperation, ValueError):
            bank_amount = 0.0
        bank_date = _parse_date(date_raw, "bank statement date") if date_raw else None

        match: Optional[Dict[str, object]] = None
        if reference:
            normalized_ref = reference.lower()
            for tx in transactions:
                candidates = {
                    str(tx.get("gateway_reference") or "").lower(),
                    str(tx.get("receipt_number") or "").lower(),
                    str(tx.get("invoice_number") or "").lower(),
                    str(tx.get("id") or "").lower(),
                }
                if normalized_ref in candidates and str(tx["id"]) not in used_transaction_ids:
                    match = tx
                    break

        if match is None:
            for tx in transactions:
                if str(tx["id"]) in used_transaction_ids:
                    continue
                if abs(_amount(tx["amount"]) - bank_amount) > 0.01:
                    continue
                tx_date = datetime.fromisoformat(str(tx["payment_date"])).date()
                if bank_date and abs((bank_date - tx_date).days) > 3:
                    continue
                match = tx
                break

        if match:
            used_transaction_ids.add(str(match["id"]))
            status = "Matched"
            reason = "Reference and amount matched"
            matched_rows += 1
            system_reference = str(match.get("receipt_number") or match.get("invoice_number") or match.get("gateway_reference") or match["id"])
            system_amount = _amount(match["amount"])
        else:
            status = "Unmatched"
            reason = "No internal branch transaction matched this bank statement row"
            unmatched_rows += 1
            system_reference = None
            system_amount = None

        parsed_rows.append(
            BankReconcileRow(
                row_number=index,
                bank_reference=reference or f"row-{index}",
                bank_date=bank_date.isoformat() if bank_date else None,
                bank_amount=round(bank_amount, 2),
                system_reference=system_reference,
                system_amount=round(system_amount, 2) if system_amount is not None else None,
                status=status,
                reason=reason,
            )
        )

    discrepancy_rows = sum(1 for row in parsed_rows if row.status != "Matched")
    return BankReconcileResponse(
        filename=statement.filename,
        total_rows=len(parsed_rows),
        matched_rows=matched_rows,
        discrepancy_rows=discrepancy_rows,
        unmatched_rows=unmatched_rows,
        rows=parsed_rows,
    )


def _record_reminder(
    db: Session,
    *,
    branch_id: int,
    patient_id: int,
    invoice_id: Optional[int],
    reminder_type: str,
    channel: str,
    status: str,
    scheduled_for: datetime,
    message: str,
    sent_at: Optional[datetime] = None,
) -> None:
    db.add(
        PaymentReminder(
            branch_id=branch_id,
            patient_id=patient_id,
            invoice_id=invoice_id,
            reminder_type=reminder_type,
            channel=channel,
            status=status,
            scheduled_for=scheduled_for,
            sent_at=sent_at,
            message=message,
        )
    )


async def _send_reminder_channels(
    db: Session,
    *,
    branch_id: int,
    patient: Patient,
    summary: PatientFinancialResponse,
    invoice: Optional[Invoice],
    message: str,
    reminder_type: str,
    scheduled_for: datetime,
    channels: Sequence[str],
) -> ReminderResponse:
    sms_service = get_sms_service()
    email_service = get_email_service()
    results: List[ReminderResult] = []
    total_sent = 0
    channel_set = {channel.lower() for channel in channels}

    if "sms" in channel_set and summary.mobile:
        sms_ok = False
        try:
            sms_ok = bool((await sms_service.send_sms(summary.mobile, message, priority="high")).success)
        finally:
            _record_reminder(
                db,
                branch_id=branch_id,
                patient_id=patient.id,
                invoice_id=invoice.id if invoice else None,
                reminder_type=reminder_type,
                channel="sms",
                status="sent" if sms_ok else "failed",
                scheduled_for=scheduled_for,
                message=message,
                sent_at=datetime.utcnow() if sms_ok else None,
            )
        if sms_ok:
            total_sent += 1

    if "email" in channel_set and summary.email:
        email_ok = False
        try:
            email_ok = bool(
                email_service.send_email(
                    summary.email,
                    "Payment Reminder - Vaidya Vihar Diagnostic",
                    f"<p>Dear {summary.full_name},</p><p>{message}</p><p>Outstanding: {fmtMoney(summary.outstanding_balance)}</p>",
                    text_content=message,
                )
            )
        finally:
            _record_reminder(
                db,
                branch_id=branch_id,
                patient_id=patient.id,
                invoice_id=invoice.id if invoice else None,
                reminder_type=reminder_type,
                channel="email",
                status="sent" if email_ok else "failed",
                scheduled_for=scheduled_for,
                message=message,
                sent_at=datetime.utcnow() if email_ok else None,
            )
        if email_ok:
            total_sent += 1

    db.commit()
    results.append(ReminderResult(patient_id=patient.id, sent_sms="sms" in channel_set and bool(summary.mobile), sent_email="email" in channel_set and bool(summary.email), message=message))
    return ReminderResponse(total_requested=1, total_sent=total_sent, results=results)


def _reminder_already_sent(
    db: Session,
    *,
    invoice_id: int,
    channel: str,
    reminder_type: str,
    scheduled_for: datetime,
) -> bool:
    existing = (
        db.query(PaymentReminder.id)
        .filter(
            PaymentReminder.invoice_id == invoice_id,
            PaymentReminder.channel == channel,
            PaymentReminder.reminder_type == reminder_type,
            PaymentReminder.status == "sent",
            PaymentReminder.scheduled_for >= scheduled_for.replace(hour=0, minute=0, second=0, microsecond=0),
            PaymentReminder.scheduled_for < scheduled_for.replace(hour=23, minute=59, second=59, microsecond=999999),
        )
        .first()
    )
    return existing is not None


async def _dispatch_due_payment_reminders(
    db: Session,
    *,
    branch_id: Optional[int] = None,
) -> ReminderJobResponse:
    now = datetime.utcnow()
    due_window = now + timedelta(hours=24)
    branch_ids = [branch_id] if branch_id is not None else [row[0] for row in db.query(Branch.id).filter(Branch.is_active.is_(True)).all()]
    total_due = 0
    reminders_sent = 0
    reminders_skipped = 0

    for current_branch_id in branch_ids:
        invoices = (
            db.query(Invoice)
            .filter(
                Invoice.branch_id == current_branch_id,
                Invoice.due_date.isnot(None),
                Invoice.due_date >= now,
                Invoice.due_date <= due_window,
            )
            .options(joinedload(Invoice.patient))
            .all()
        )
        for invoice in invoices:
            billed_amount = _amount(invoice.final_amount or invoice.total_amount)
            paid_amount = _invoice_paid_amount(invoice)
            if billed_amount <= paid_amount:
                continue
            patient = invoice.patient or db.query(Patient).filter(Patient.id == invoice.patient_id, Patient.branch_id == current_branch_id).first()
            if not patient:
                continue
            profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient.id).first()
            summary = _patient_financial_summary(db, current_branch_id, patient.id)
            message = (
                f"Dear {summary.full_name}, your payment of {fmtMoney(summary.outstanding_balance)} "
                f"for invoice {invoice.invoice_number} is due on {invoice.due_date.strftime('%d %b %Y')}."
            )
            for channel in ("sms", "email"):
                total_due += 1
                if _reminder_already_sent(db, invoice_id=invoice.id, channel=channel, reminder_type="due_24h", scheduled_for=invoice.due_date or now):
                    reminders_skipped += 1
                    continue
                if channel == "sms" and not summary.mobile:
                    reminders_skipped += 1
                    continue
                if channel == "email" and not summary.email:
                    reminders_skipped += 1
                    continue
                sent = False
                try:
                    if channel == "sms":
                        sent = bool((await get_sms_service().send_sms(summary.mobile, message, priority="high")).success)
                    else:
                        sent = bool(
                            get_email_service().send_email(
                                summary.email,
                                "Payment Reminder - Vaidya Vihar Diagnostic",
                                f"<p>Dear {summary.full_name},</p><p>{message}</p><p>Outstanding: {fmtMoney(summary.outstanding_balance)}</p>",
                                text_content=message,
                            )
                        )
                finally:
                    _record_reminder(
                        db,
                        branch_id=current_branch_id,
                        patient_id=patient.id,
                        invoice_id=invoice.id,
                        reminder_type="due_24h",
                        channel=channel,
                        status="sent" if sent else "failed",
                        scheduled_for=invoice.due_date or now,
                        message=message,
                        sent_at=datetime.utcnow() if sent else None,
                    )
                if sent:
                    reminders_sent += 1
                else:
                    reminders_skipped += 1

    db.commit()
    return ReminderJobResponse(
        total_due=total_due,
        reminders_sent=reminders_sent,
        reminders_skipped=reminders_skipped,
        created_at=now.isoformat(),
    )


def _run_due_payment_reminder_cycle() -> None:
    db = SessionLocal()
    try:
        asyncio.run(_dispatch_due_payment_reminders(db))
    finally:
        db.close()


def start_branch_payment_scheduler() -> None:
    global _reminder_scheduler_thread
    if _reminder_scheduler_thread and _reminder_scheduler_thread.is_alive():
        return
    _reminder_scheduler_stop.clear()

    def _loop() -> None:
        while not _reminder_scheduler_stop.is_set():
            _run_due_payment_reminder_cycle()
            _reminder_scheduler_stop.wait(60)

    _reminder_scheduler_thread = threading.Thread(target=_loop, daemon=True, name="branch-payments-reminder-scheduler")
    _reminder_scheduler_thread.start()


def stop_branch_payment_scheduler() -> None:
    global _reminder_scheduler_thread
    _reminder_scheduler_stop.set()
    if _reminder_scheduler_thread and _reminder_scheduler_thread.is_alive():
        _reminder_scheduler_thread.join(timeout=5)
    _reminder_scheduler_thread = None


# ============================================================================
# PHASE 3: PATIENT FINANCIAL MANAGEMENT & INVOICING
# ============================================================================


class FinancialHistoryItem(BaseModel):
    id: str
    type: str
    description: str
    amount: float
    status: str
    timestamp: str
    reference: Optional[str] = None


class RefundItem(BaseModel):
    id: int
    amount: float
    status: str
    reason: Optional[str] = None
    requested_at: str
    processed_at: Optional[str] = None
    reference: Optional[str] = None


class PatientFinancialResponse(BaseModel):
    patient_id: int
    patient_code: Optional[str] = None
    full_name: str
    mobile: Optional[str] = None
    email: Optional[str] = None
    total_tests: int
    total_billed: float
    total_paid: float
    outstanding_balance: float
    payment_history: List[FinancialHistoryItem]
    refunds: List[RefundItem]
    branch_name: Optional[str] = None
    last_payment_at: Optional[str] = None


class OutstandingDueRow(BaseModel):
    patient_id: int
    patient_code: Optional[str] = None
    patient_name: str
    mobile: Optional[str] = None
    outstanding_amount: float
    oldest_due_date: Optional[str] = None
    aging_days: int
    total_billed: float
    total_paid: float
    last_payment_at: Optional[str] = None


class ReminderRequest(BaseModel):
    patient_id: Optional[int] = None
    patient_ids: List[int] = Field(default_factory=list)
    message: Optional[str] = None
    channels: List[str] = Field(default_factory=lambda: ["sms", "email"])


class ReminderResult(BaseModel):
    patient_id: int
    sent_sms: bool
    sent_email: bool
    message: str


class ReminderResponse(BaseModel):
    total_requested: int
    total_sent: int
    results: List[ReminderResult]


class PaymentReadinessResponse(BaseModel):
    score: int
    status: str
    branch_name: Optional[str] = None
    pending_invoices: int
    due_soon_invoices: int
    overdue_invoices: int
    blockers: List[str]
    checklist: List[str]
    last_updated: str


class SmartAlertItem(BaseModel):
    alert_id: int
    category: str
    severity: str
    title: str
    message: str
    amount: float = 0.0
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    source: Optional[str] = None
    created_at: str


class BulkReconciliationItem(BaseModel):
    transaction_id: str
    status: str
    message: str
    matched_reference: Optional[str] = None


class BulkReconciliationResponse(BaseModel):
    total_transactions: int
    reconciled: int
    pending: int
    discrepancy: int
    results: List[BulkReconciliationItem]
    created_at: str


class ReminderJobResponse(BaseModel):
    total_due: int
    reminders_sent: int
    reminders_skipped: int
    created_at: str


class InvoiceLineItemInput(BaseModel):
    item_name: str
    unit_price: float
    quantity: int = 1
    item_type: str = "test"
    service_type: Optional[str] = None
    gst_rate: Optional[float] = None
    gst_exempt: bool = False


class InvoiceGenerateRequest(BaseModel):
    patient_id: int
    items: List[InvoiceLineItemInput]
    service_type: Optional[str] = None
    notes: Optional[str] = None
    legal_text: Optional[str] = None
    referred_by: Optional[str] = None
    due_days: int = 0


class BulkInvoiceItemInput(InvoiceGenerateRequest):
    pass


class BulkInvoiceRequest(BaseModel):
    invoices: List[BulkInvoiceItemInput]


class InvoiceLineItemBreakdown(BaseModel):
    item_name: str
    quantity: int
    unit_price: float
    taxable_amount: float
    gst_rate: float
    gst_amount: float
    total_amount: float


class InvoiceGstBreakdown(BaseModel):
    taxable_amount: float
    cgst: float
    sgst: float
    igst: float
    gst_total: float
    grand_total: float


class GeneratedInvoiceResponse(BaseModel):
    invoice_id: int
    invoice_number: str
    patient_id: int
    patient_name: str
    branch_id: int
    branch_name: Optional[str] = None
    subtotal: float
    discount_amount: float
    taxable_amount: float
    gst_breakdown: InvoiceGstBreakdown
    final_amount: float
    due_date: Optional[str] = None
    pcpndt_compliance: List[str]
    legal_text: str
    items: List[InvoiceLineItemBreakdown]


class BulkInvoiceResponse(BaseModel):
    total_invoices: int
    total_amount: float
    total_tax: float
    total_final_amount: float
    invoices: List[GeneratedInvoiceResponse]


class TrendPoint(BaseModel):
    label: str
    revenue: float


class TrendResponse(BaseModel):
    daily: List[TrendPoint]
    weekly: List[TrendPoint]
    monthly: List[TrendPoint]


class ForecastResponse(BaseModel):
    horizon_days: int
    current_average_daily_revenue: float
    projected_revenue: float
    confidence: str
    series: List[TrendPoint]


class AnomalyItem(BaseModel):
    id: int
    type: str
    severity: str
    title: str
    description: str
    amount: float
    related_transaction_id: Optional[str] = None
    created_at: str


class SimulationRequest(BaseModel):
    action: str


class SimulationResponse(BaseModel):
    action: str
    current_collection_rate: float
    projected_collection_rate: float
    current_cash_flow: float
    projected_cash_flow: float
    impact: float
    note: str


def _patient_display_name(patient: Optional[Patient], profile: Optional[PatientProfile]) -> str:
    if profile and profile.full_name:
        return profile.full_name
    if patient:
        return _patient_full_name(patient)
    return "Unknown Patient"


def _service_gst_rate(service_type: Optional[str], item: InvoiceLineItemInput) -> float:
    if item.gst_exempt:
        return 0.0
    if item.gst_rate is not None:
        return max(float(item.gst_rate), 0.0)

    service = (service_type or item.service_type or item.item_type or "").strip().lower()
    name = item.item_name.strip().lower()
    if "exempt" in service or "exempt" in name or "zero" in service:
        return 0.0
    if service in {"package", "health-check", "health_check", "corporate", "insurance"}:
        return 18.0
    if service in {"radiology", "imaging", "scan", "mri", "ct", "ultrasound"} or any(keyword in name for keyword in ["mri", "ct", "ultrasound", "x-ray", "xray", "scan"]):
        return 12.0
    return 5.0


def _branch_legal_text(branch: Optional[Branch], custom_legal: Optional[str]) -> str:
    base = custom_legal or "GST invoice generated by Vaidya Vihar Diagnostic. All sample collection and reporting follow applicable medical and PCPNDT compliance norms."
    if branch and branch.address:
        return f"{base}\nBranch: {branch.name}\nAddress: {branch.address}"
    return base


def _invoice_pcpndt_notice() -> List[str]:
    return [
        "For diagnostic use only.",
        "PCPNDT compliance maintained for imaging services where applicable.",
        "All patient records are branch-scoped and auditable.",
    ]


def _invoice_item_breakdown(item: InvoiceLineItemInput, service_type: Optional[str]) -> Tuple[InvoiceLineItemBreakdown, float, float]:
    taxable_amount = round(float(item.unit_price) * int(item.quantity), 2)
    gst_rate = _service_gst_rate(service_type, item)
    gst_amount = round(taxable_amount * (gst_rate / 100.0), 2)
    total_amount = round(taxable_amount + gst_amount, 2)
    return (
        InvoiceLineItemBreakdown(
            item_name=item.item_name,
            quantity=int(item.quantity),
            unit_price=round(float(item.unit_price), 2),
            taxable_amount=taxable_amount,
            gst_rate=gst_rate,
            gst_amount=gst_amount,
            total_amount=total_amount,
        ),
        taxable_amount,
        gst_amount,
    )


def _generate_invoice_payload(
    db: Session,
    branch_id: int,
    patient_id: int,
    items: List[InvoiceLineItemInput],
    service_type: Optional[str] = None,
    notes: Optional[str] = None,
    legal_text: Optional[str] = None,
    referred_by: Optional[str] = None,
    due_days: int = 0,
) -> GeneratedInvoiceResponse:
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.branch_id == branch_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found for this branch")

    profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id).first()
    invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{patient_id}"
    line_items: List[InvoiceLineItemBreakdown] = []
    taxable_total = 0.0
    gst_total = 0.0
    subtotal = 0.0

    for item in items:
        breakdown, taxable_amount, gst_amount = _invoice_item_breakdown(item, service_type)
        line_items.append(breakdown)
        taxable_total += taxable_amount
        gst_total += gst_amount
        subtotal += breakdown.total_amount

    discount_amount = 0.0
    final_amount = round(subtotal - discount_amount, 2)
    cgst = round(gst_total / 2, 2)
    sgst = round(gst_total / 2, 2)
    igst = 0.0
    due_date = datetime.utcnow() + (timedelta(days=due_days) if due_days else timedelta(days=0))

    invoice = Invoice(
        invoice_number=invoice_number,
        patient_id=patient_id,
        branch_id=branch_id,
        total_amount=round(subtotal, 2),
        discount_amount=discount_amount,
        tax_amount=round(gst_total, 2),
        final_amount=final_amount,
        status="pending",
        payment_status=PaymentStatus.PENDING,
        invoice_date=datetime.utcnow(),
        due_date=due_date if due_days else None,
        notes=notes,
        terms=_branch_legal_text(branch, legal_text),
        referred_by=referred_by,
    )
    db.add(invoice)
    db.flush()

    for item in items:
        breakdown, _, _ = _invoice_item_breakdown(item, service_type)
        db.add(
            InvoiceItem(
                invoice_id=invoice.id,
                item_type=item.item_type,
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=breakdown.total_amount,
                item_code=None,
            )
        )

    db.commit()
    db.refresh(invoice)

    return GeneratedInvoiceResponse(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        patient_id=patient.id,
        patient_name=_patient_display_name(patient, profile),
        branch_id=branch_id,
        branch_name=branch.name if branch else None,
        subtotal=round(subtotal, 2),
        discount_amount=discount_amount,
        taxable_amount=round(taxable_total, 2),
        gst_breakdown=InvoiceGstBreakdown(
            taxable_amount=round(taxable_total, 2),
            cgst=cgst,
            sgst=sgst,
            igst=igst,
            gst_total=round(gst_total, 2),
            grand_total=final_amount,
        ),
        final_amount=final_amount,
        due_date=due_date.isoformat() if due_days else None,
        pcpndt_compliance=_invoice_pcpndt_notice(),
        legal_text=_branch_legal_text(branch, legal_text),
        items=line_items,
    )


def _patient_financial_summary(db: Session, branch_id: int, patient_id: int) -> PatientFinancialResponse:
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.branch_id == branch_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found for this branch")

    profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id).first()
    invoices = (
        db.query(Invoice)
        .filter(Invoice.branch_id == branch_id, Invoice.patient_id == patient_id)
        .options(joinedload(Invoice.payments), joinedload(Invoice.items))
        .order_by(Invoice.created_at.desc())
        .all()
    )
    daily_entries = (
        db.query(DailyEntry)
        .filter(DailyEntry.branch_id == branch_id, DailyEntry.patient_id == patient_id)
        .all()
    )
    payments = (
        db.query(Payment)
        .filter(Payment.branch_id == branch_id, Payment.patient_id == patient_id)
        .options(joinedload(Payment.invoice))
        .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        .all()
    )
    refunds = (
        db.query(Refund)
        .join(Payment, Refund.payment_id == Payment.id)
        .filter(Payment.branch_id == branch_id, Payment.patient_id == patient_id)
        .order_by(Refund.created_at.desc())
        .all()
    )

    history: List[FinancialHistoryItem] = []
    total_billed = 0.0
    total_paid = 0.0
    total_tests = 0
    last_payment_at: Optional[str] = None

    for invoice in invoices:
        invoice_total = _amount(invoice.final_amount or invoice.total_amount)
        paid_amount = _invoice_paid_amount(invoice)
        total_billed += invoice_total
        total_paid += paid_amount
        total_tests += len(invoice.items or [])
        history.append(
            FinancialHistoryItem(
                id=f"invoice-{invoice.id}",
                type="Invoice",
                description=f"Invoice {invoice.invoice_number}",
                amount=invoice_total,
                status=_normalize_status(invoice.payment_status, fallback=_normalize_status(invoice.status)),
                timestamp=_safe_datetime(invoice.created_at).isoformat(),
                reference=invoice.invoice_number,
            )
        )
        if invoice.paid_date:
            last_payment_at = max(last_payment_at or invoice.paid_date.isoformat(), invoice.paid_date.isoformat())

    for entry in daily_entries:
        billed = _amount(entry.total_amount)
        paid = _amount(entry.amount_paid)
        total_billed += billed
        total_paid += paid
        total_tests += 1
        history.append(
            FinancialHistoryItem(
                id=f"daily-{entry.id}",
                type="Daily Entry",
                description=entry.test_names or entry.remarks or "Daily entry",
                amount=billed,
                status=_normalize_status(entry.payment_status),
                timestamp=_safe_datetime(entry.created_at or entry.entry_date).isoformat(),
                reference=entry.auto_patient_id,
            )
        )
        if entry.paid_at:
            last_payment_at = max(last_payment_at or entry.paid_at.isoformat(), entry.paid_at.isoformat())

    for payment in payments:
        history.append(
            FinancialHistoryItem(
                id=f"payment-{payment.id}",
                type="Payment",
                description=payment.notes or f"Payment {payment.transaction_id}",
                amount=_amount(payment.amount),
                status=_normalize_status(payment.status),
                timestamp=_safe_datetime(payment.payment_date or payment.created_at).isoformat(),
                reference=payment.transaction_id,
            )
        )
        last_payment_at = max(last_payment_at or _safe_datetime(payment.payment_date or payment.created_at).isoformat(), _safe_datetime(payment.payment_date or payment.created_at).isoformat())

    # Payment history is tracked separately from invoice/entry totals to avoid double counting.

    refund_rows = [
        RefundItem(
            id=refund.id,
            amount=_amount(refund.refund_amount),
            status=_normalize_status(refund.status),
            reason=refund.refund_reason,
            requested_at=_safe_datetime(refund.requested_at).isoformat(),
            processed_at=_safe_datetime(refund.processed_at).isoformat() if refund.processed_at else None,
            reference=refund.gateway_refund_id,
        )
        for refund in refunds
    ]

    history.sort(key=lambda row: row.timestamp, reverse=True)
    outstanding = round(max(total_billed - total_paid, 0.0), 2)

    return PatientFinancialResponse(
        patient_id=patient.id,
        patient_code=profile.patient_code if profile else patient.patient_id,
        full_name=_patient_display_name(patient, profile),
        mobile=profile.mobile if profile else patient.phone,
        email=profile.email if profile else patient.email,
        total_tests=total_tests,
        total_billed=round(total_billed, 2),
        total_paid=round(total_paid, 2),
        outstanding_balance=outstanding,
        payment_history=history[:100],
        refunds=refund_rows,
        branch_name=patient.branch.name if patient.branch else None,
        last_payment_at=last_payment_at,
    )


def _outstanding_due_rows(db: Session, branch_id: int) -> List[OutstandingDueRow]:
    patients = db.query(Patient).filter(Patient.branch_id == branch_id, Patient.is_active.is_(True)).all()
    rows: List[OutstandingDueRow] = []
    today = datetime.utcnow().date()
    for patient in patients:
        profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient.id).first()
        summary = _patient_financial_summary(db, branch_id, patient.id)
        if summary.outstanding_balance <= 0:
            continue
        oldest_due_date: Optional[date] = None
        for invoice in (
            db.query(Invoice)
            .filter(Invoice.branch_id == branch_id, Invoice.patient_id == patient.id)
            .all()
        ):
            if _amount(invoice.final_amount or invoice.total_amount) <= _invoice_paid_amount(invoice):
                continue
            candidate = invoice.due_date or invoice.invoice_date or invoice.created_at
            if candidate and (oldest_due_date is None or candidate.date() < oldest_due_date):
                oldest_due_date = candidate.date()
        aging_days = max((today - oldest_due_date).days, 0) if oldest_due_date else 0
        rows.append(
            OutstandingDueRow(
                patient_id=patient.id,
                patient_code=profile.patient_code if profile else patient.patient_id,
                patient_name=_patient_display_name(patient, profile),
                mobile=profile.mobile if profile else patient.phone,
                outstanding_amount=summary.outstanding_balance,
                oldest_due_date=oldest_due_date.isoformat() if oldest_due_date else None,
                aging_days=aging_days,
                total_billed=summary.total_billed,
                total_paid=summary.total_paid,
                last_payment_at=summary.last_payment_at,
            )
        )

    rows.sort(key=lambda row: (row.outstanding_amount, row.aging_days), reverse=True)
    return rows


@router.get("/patients/{id}/financial", response_model=PatientFinancialResponse)
def get_patient_financial_profile(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    return _patient_financial_summary(db, branch_id, id)


@router.get("/outstanding-dues", response_model=List[OutstandingDueRow])
def get_outstanding_dues(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    return _outstanding_due_rows(db, branch_id)


@router.post("/payments/reminders", response_model=ReminderResponse)
async def send_payment_reminders(
    payload: ReminderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    patient_ids = sorted({*(payload.patient_ids or []), *( [payload.patient_id] if payload.patient_id else [] )})
    if not patient_ids:
        raise HTTPException(status_code=400, detail="At least one patient_id is required")

    results: List[ReminderResult] = []
    total_sent = 0

    for pid in patient_ids:
        patient = db.query(Patient).filter(Patient.id == pid, Patient.branch_id == branch_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {pid} not found for this branch")
        summary = _patient_financial_summary(db, branch_id, pid)
        message = payload.message or (
            f"Dear {summary.full_name}, your outstanding balance is {fmtMoney(summary.outstanding_balance)}. "
            "Please clear dues at the earliest."
        )
        reminder_response = await _send_reminder_channels(
            db,
            branch_id=branch_id,
            patient=patient,
            summary=summary,
            invoice=None,
            message=message,
            reminder_type="manual",
            scheduled_for=datetime.utcnow(),
            channels=payload.channels,
        )
        total_sent += reminder_response.total_sent
        results.extend(reminder_response.results)

    return ReminderResponse(total_requested=len(patient_ids), total_sent=total_sent, results=results)


@router.post("/invoice/generate", response_model=GeneratedInvoiceResponse)
def generate_invoice(
    payload: InvoiceGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    return _generate_invoice_payload(
        db,
        branch_id=branch_id,
        patient_id=payload.patient_id,
        items=payload.items,
        service_type=payload.service_type,
        notes=payload.notes,
        legal_text=payload.legal_text,
        referred_by=payload.referred_by,
        due_days=payload.due_days,
    )


@router.post("/bulk-invoice", response_model=BulkInvoiceResponse)
def bulk_invoice(
    payload: BulkInvoiceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    invoices: List[GeneratedInvoiceResponse] = []
    total_amount = 0.0
    total_tax = 0.0
    total_final_amount = 0.0
    for row in payload.invoices:
        invoice = _generate_invoice_payload(
            db,
            branch_id=branch_id,
            patient_id=row.patient_id,
            items=row.items,
            service_type=row.service_type,
            notes=row.notes,
            legal_text=row.legal_text,
            referred_by=row.referred_by,
            due_days=row.due_days,
        )
        invoices.append(invoice)
        total_amount += invoice.subtotal
        total_tax += invoice.gst_breakdown.gst_total
        total_final_amount += invoice.final_amount

    return BulkInvoiceResponse(
        total_invoices=len(invoices),
        total_amount=round(total_amount, 2),
        total_tax=round(total_tax, 2),
        total_final_amount=round(total_final_amount, 2),
        invoices=invoices,
    )


# ============================================================================
# PHASE 4: ANALYTICS & AI-POWERED PREDICTIVE INSIGHTS
# ============================================================================


def _trend_points(transactions: Sequence[Dict[str, object]], bucket: str) -> List[TrendPoint]:
    series: Dict[str, float] = {}
    for tx in transactions:
        ts = datetime.fromisoformat(str(tx["payment_date"]))
        if bucket == "daily":
            label = ts.date().isoformat()
        elif bucket == "weekly":
            year, week, _ = ts.isocalendar()
            label = f"{year}-W{week:02d}"
        else:
            label = ts.strftime("%Y-%m")
        series[label] = series.get(label, 0.0) + _amount(tx["amount"]) if _normalize_status(tx["status"]) == "Completed" else series.get(label, 0.0)
    return [TrendPoint(label=label, revenue=round(value, 2)) for label, value in sorted(series.items())]


@router.get("/trends", response_model=TrendResponse)
def get_payment_trends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, _ = _collect_transactions(db, branch_id)
    return TrendResponse(
        daily=_trend_points(transactions, "daily")[-60:],
        weekly=_trend_points(transactions, "weekly")[-16:],
        monthly=_trend_points(transactions, "monthly")[-12:],
    )


@router.get("/forecast", response_model=ForecastResponse)
def get_payment_forecast(
    horizon_days: int = Query(30, ge=30, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, _ = _collect_transactions(db, branch_id)
    daily = _trend_points(transactions, "daily")
    trailing = [point.revenue for point in daily[-30:]] or [0.0]
    average_daily = sum(trailing) / len(trailing)
    projected = average_daily * horizon_days
    confidence = "High" if len(trailing) >= 20 else "Medium" if len(trailing) >= 10 else "Low"
    series = [TrendPoint(label=f"Day {idx}", revenue=round(average_daily, 2)) for idx in range(1, horizon_days + 1)]
    return ForecastResponse(
        horizon_days=horizon_days,
        current_average_daily_revenue=round(average_daily, 2),
        projected_revenue=round(projected, 2),
        confidence=confidence,
        series=series,
    )


@router.get("/anomalies", response_model=List[AnomalyItem])
def get_anomalies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, metrics = _collect_transactions(db, branch_id)
    anomalies: List[AnomalyItem] = []
    daily = _trend_points(transactions, "daily")
    if len(daily) >= 8:
        today = daily[-1].revenue
        average_prev = sum(point.revenue for point in daily[-8:-1]) / 7
        if average_prev > 0 and today < average_prev * 0.7:
            anomalies.append(
                AnomalyItem(
                    id=1,
                    type="collection_drop",
                    severity="High",
                    title="Collections dropped sharply today",
                    description=f"Today's revenue {fmtMoney(today)} is below the 7-day average {fmtMoney(average_prev)}.",
                    amount=round(today, 2),
                    created_at=datetime.utcnow().isoformat(),
                )
            )

    for idx, tx in enumerate(transactions, start=2):
        if _normalize_status(tx["status"]) == "Refunded":
            anomalies.append(
                AnomalyItem(
                    id=idx,
                    type="refund_request",
                    severity="Medium",
                    title=f"Refund recorded for {tx['patient_name']}",
                    description=f"Refund reference {tx.get('reference_number') or tx.get('receipt_number') or tx['id']} needs review.",
                    amount=_amount(tx["amount"]),
                    related_transaction_id=str(tx["id"]),
                    created_at=datetime.utcnow().isoformat(),
                )
            )
            break

    duplicate_refs: Dict[str, int] = {}
    for tx in transactions:
        ref = str(tx.get("gateway_reference") or tx.get("receipt_number") or tx.get("invoice_number") or "").strip().lower()
        if not ref:
            continue
        duplicate_refs[ref] = duplicate_refs.get(ref, 0) + 1

    if any(count > 1 for count in duplicate_refs.values()):
        duplicate_ref = next(ref for ref, count in duplicate_refs.items() if count > 1)
        anomalies.append(
            AnomalyItem(
                id=len(anomalies) + 2,
                type="duplicate_payment",
                severity="High",
                title="Duplicate payment reference detected",
                description=f"Reference {duplicate_ref} appears more than once in branch data.",
                amount=0.0,
                created_at=datetime.utcnow().isoformat(),
            )
        )

    return anomalies


@router.post("/simulate", response_model=SimulationResponse)
def simulate_cashflow(
    payload: SimulationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    transactions, metrics = _collect_transactions(db, branch_id)
    daily_revenue = [point.revenue for point in _trend_points(transactions, "daily")[-30:]] or [0.0]
    current_average = sum(daily_revenue) / len(daily_revenue)
    current_collection_rate = _collection_rate(metrics["billed_total"], metrics["collected_total"])

    action = payload.action.lower()
    discount_match = re.search(r"(\d+(?:\.\d+)?)\s*%", action)
    discount_percent = float(discount_match.group(1)) if discount_match else 0.0
    projected_collection_rate = min(100.0, current_collection_rate + max(discount_percent * 0.6, 0.0))
    projected_cash_flow = current_average * (1 + max(discount_percent * 0.005, 0.0))
    impact = round(projected_cash_flow - current_average, 2)

    return SimulationResponse(
        action=payload.action,
        current_collection_rate=round(current_collection_rate, 2),
        projected_collection_rate=round(projected_collection_rate, 2),
        current_cash_flow=round(current_average, 2),
        projected_cash_flow=round(projected_cash_flow, 2),
        impact=impact,
        note="Estimated using recent branch revenue trends and the stated scenario.",
    )
