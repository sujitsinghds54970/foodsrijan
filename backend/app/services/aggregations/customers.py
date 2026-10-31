from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func

from app.models import Customer, CustomerProfile, Invoice, Payment
from app.models.patient_portal import CustomerFeedback
from app.services.aggregations.querying import branch_scoped_query, company_scoped_query
from app.services.executive_metrics import MetricResult


def compute_customer_activity(db: Any, scope: Any, period: str | None = None) -> MetricResult:
    started = time.perf_counter()
    customer_rows = company_scoped_query(db, Customer, scope).all()
    customer_ids = [row.id for row in customer_rows]
    count = len(customer_rows)
    profile_count = (
        db.query(CustomerProfile)
        .filter(CustomerProfile.patient_id.in_(customer_ids))
        .count()
        if customer_ids
        else 0
    )
    invoice_query = branch_scoped_query(db, Invoice, scope)
    invoice_count = invoice_query.count()
    invoice_revenue = float(invoice_query.with_entities(func.coalesce(func.sum(Invoice.total_amount), 0)).scalar() or 0)
    payment_total = float(branch_scoped_query(db, Payment, scope).with_entities(func.coalesce(func.sum(Payment.amount), 0)).scalar() or 0)
    feedback_rows = (
        db.query(CustomerFeedback)
        .filter(CustomerFeedback.patient_id.in_(customer_ids), CustomerFeedback.rating.isnot(None))
        .all()
        if customer_ids
        else []
    )
    paying_customer_count = invoice_query.with_entities(Invoice.patient_id).distinct().count() if invoice_count else 0
    repeat_customer_count = 0
    if invoice_count:
        repeat_customer_count = sum(
            1
            for (patient_id,) in invoice_query.with_entities(Invoice.patient_id).group_by(Invoice.patient_id).having(func.count(Invoice.id) > 1).all()
            if patient_id is not None
        )
    value = {
        "total_customers": count,
        "active_customers": sum(1 for row in customer_rows if row.is_active),
        "profile_count": profile_count,
        "new_customers_this_period": None,
        "invoice_count": invoice_count if invoice_count else None,
        "revenue_per_customer": round(invoice_revenue / count, 2) if count and invoice_count else None,
        "collection_per_customer": round(payment_total / count, 2) if count and payment_total else None,
        "feedback_count": len(feedback_rows) if feedback_rows else None,
        "average_rating": round(sum(row.rating for row in feedback_rows if row.rating is not None) / len(feedback_rows), 2) if feedback_rows else None,
        "repeat_rate": round(repeat_customer_count / paying_customer_count * 100, 2) if paying_customer_count else None,
        "deduplication_status": "per_company_only",
    }
    missing_sources = []
    if not invoice_count:
        missing_sources.append("invoices")
    if not payment_total:
        missing_sources.append("payments")
    if not feedback_rows:
        missing_sources.append("patient_feedbacks")
    return MetricResult(
        value=value,
        display_value=str(count),
        delta=0.0,
        trend="flat",
        source="derived",
        source_status="empty" if count == 0 else "partial" if missing_sources else "complete",
        as_of=datetime.now(timezone.utc),
        confidence_level="medium",
        reconciled=False,
        unit="customers",
        metric_name="customer_metrics",
        computation_time_ms=max(0, int((time.perf_counter() - started) * 1000)),
        deduplication_status="per_company_only",
        missing_sources=missing_sources,
        details={"deduplication": "per_company_only", "missing_submetrics_are_null": True},
    )

__all__ = ["compute_customer_activity"]
