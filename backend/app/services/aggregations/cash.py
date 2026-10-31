from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.models import Invoice, Payment
from app.services.aggregations.customers import compute_customer_activity
from app.services.aggregations.portfolio import compute_portfolio_health
from app.services.aggregations.querying import branch_scoped_query
from app.services.executive_metrics import MetricResult


def _safe_number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match is None:
            return 0.0
        return float(match.group(0))
    return 0.0

def _sum_amount(rows: list[Any], field_names: tuple[str, ...]) -> float:
    total = 0.0
    for row in rows:
        for field_name in field_names:
            value = getattr(row, field_name, None)
            if value is None and isinstance(row, dict):
                value = row.get(field_name)
            if value is not None:
                total += _safe_number(value)
                break
    return total


def compute_cash_conversion(db: Any, scope: Any, period: str | None = None) -> MetricResult:
    started = time.perf_counter()
    invoice_rows = branch_scoped_query(db, Invoice, scope).all()
    payment_rows = branch_scoped_query(db, Payment, scope).all()
    billed = _sum_amount(invoice_rows, ("amount", "total_amount", "net_amount", "revenue"))
    collected = _sum_amount(payment_rows, ("amount", "received_amount", "paid_amount"))
    ratio = round((collected / billed * 100), 2) if billed else None
    return MetricResult(
        value=ratio,
        display_value=f"{ratio:.1f}%" if ratio is not None else "—",
        delta=0.0,
        trend="flat",
        source="invoices,payments",
        source_status="unavailable" if not billed else "complete",
        as_of=datetime.now(timezone.utc),
        confidence_level="medium",
        reconciled=False,
        unit="percent",
        metric_name="cash_conversion",
        computation_time_ms=max(0, int((time.perf_counter() - started) * 1000)),
        details={
            "billed_revenue": round(billed, 2),
            "collections": round(collected, 2),
            "conversion_ratio": ratio,
            "invoice_count": len(invoice_rows),
            "payment_count": len(payment_rows),
            "reconciled": False,
            "conversion_status": "derived_pending_reconciliation_policy",
        },
    )


def compute_performance_summary(db: Any, scope: Any, period: str | None = None) -> dict[str, Any]:
    revenue = compute_cash_conversion(db, scope, period)
    health = compute_portfolio_health(db, scope, period)
    customers = compute_customer_activity(db, scope, period)
    from app.services.aggregations.alerts import compute_critical_alerts
    alerts = compute_critical_alerts(db, scope, period)
    return {
        "period": period or "QTD",
        "metrics": {
            "revenue": revenue.value,
            "portfolio_health": health.value,
            "active_customers": (customers.value or {}).get("active_customers", 0) if isinstance(customers.value, dict) else customers.value,
            "critical_alerts": alerts.value,
            "cash_conversion": revenue.value,
        },
        "status": "healthy" if (health.value or 0) >= 70 else "watch",
        "summary": "Portfolio is stable with manageable alert pressure.",
    }

__all__ = ["compute_cash_conversion", "compute_performance_summary"]
