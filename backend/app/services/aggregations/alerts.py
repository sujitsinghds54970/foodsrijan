from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.models import FinanceExpense, Invoice, User
from app.models.hr import LeaveRequest, LeaveStatus, StaffLeaveRequest
from app.services.aggregations.querying import branch_scoped_query
from app.services.executive_metrics import MetricResult


SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _status_text(value: Any) -> str:
    return getattr(value, "value", str(value)).lower()


def _sort_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        alerts,
        key=lambda item: (SEVERITY_RANK.get(item["severity"], 0), item.get("date") or ""),
        reverse=True,
    )


def compute_critical_alerts(db: Any, scope: Any, period: str | None = None) -> MetricResult:
    started = time.perf_counter()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    alerts: list[dict[str, Any]] = []
    overdue_invoices = (
        branch_scoped_query(db, Invoice, scope)
        .filter(Invoice.due_date.isnot(None), Invoice.due_date < now, ~Invoice.status.in_(("paid", "cancelled")))
        .all()
    )
    for row in overdue_invoices:
        alerts.append({
            "id": f"invoice:{row.id}",
            "source": "invoices",
            "type": "invoice_overdue",
            "severity": "high",
            "date": _iso(row.due_date or row.invoice_date),
            "amount": row.total_amount,
            "status": row.status,
        })
    for row in branch_scoped_query(db, FinanceExpense, scope).filter(FinanceExpense.status == "pending_approval").all():
        alerts.append({
            "id": f"finance_expense:{row.id}",
            "source": "finance_expenses",
            "type": "expense_pending_approval",
            "severity": "medium",
            "date": _iso(row.date or row.created_at),
            "amount": float(row.amount or 0),
            "status": row.status,
        })
    leave_query = db.query(LeaveRequest).join(User, User.id == LeaveRequest.user_id)
    if scope.branch_id is not None:
        leave_query = leave_query.filter(User.branch_id == scope.branch_id)
    elif scope.company_ids:
        leave_query = leave_query.filter((User.company_id.in_(scope.company_ids)) | (User.current_company_id.in_(scope.company_ids)))
    else:
        leave_query = leave_query.filter(False)
    for row in leave_query.filter(LeaveRequest.status == LeaveStatus.PENDING).all():
        alerts.append({
            "id": f"leave_request:{row.id}",
            "source": "leave_requests",
            "type": "leave_pending",
            "severity": "low",
            "date": _iso(row.created_at or row.start_date),
            "amount": None,
            "status": _status_text(row.status),
        })
    for row in branch_scoped_query(db, StaffLeaveRequest, scope).filter(StaffLeaveRequest.status == LeaveStatus.PENDING).all():
        alerts.append({
            "id": f"staff_leave_request:{row.id}",
            "source": "staff_leave_requests",
            "type": "staff_leave_pending",
            "severity": "low",
            "date": _iso(row.created_at or row.start_date),
            "amount": None,
            "status": _status_text(row.status),
        })
    sorted_alerts = _sort_alerts(alerts)
    count = len(alerts)
    return MetricResult(
        value=count,
        display_value=str(count),
        delta=0.0,
        trend="flat",
        source="derived",
        source_status="empty" if count == 0 else "complete",
        as_of=datetime.now(timezone.utc),
        confidence_level="medium",
        reconciled=True,
        unit="alerts",
        metric_name="critical_alerts",
        computation_time_ms=max(0, int((time.perf_counter() - started) * 1000)),
        details={"alerts": sorted_alerts[:20], "total_alerts": count},
    )

__all__ = ["compute_critical_alerts"]
