from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.models import FinanceExpense, User
from app.models.hr import LeaveRequest, LeaveStatus, StaffLeaveRequest
from app.services.aggregations.querying import branch_scoped_query
from app.services.executive_metrics import MetricResult


PRIORITY_RANK = {"urgent": 4, "high": 3, "medium": 2, "low": 1}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _status_text(value: Any) -> str:
    return getattr(value, "value", str(value)).lower()


def _item(priority: str, created_at: datetime | None, **payload: Any) -> dict[str, Any]:
    return {
        **payload,
        "priority": priority,
        "priority_rank": PRIORITY_RANK[priority],
        "created_at": _iso(created_at),
    }


def compute_decision_queue(db: Any, scope: Any, period: str | None = None) -> MetricResult:
    started = time.perf_counter()
    items: list[dict[str, Any]] = []
    for row in branch_scoped_query(db, FinanceExpense, scope).filter(FinanceExpense.status == "pending_approval").all():
        items.append(_item(
            "high",
            row.created_at or row.date,
            id=f"finance-expense-{row.id}",
            source="finance_expenses",
            type="expense_pending_approval",
            status=row.status,
            value=float(row.amount or 0),
            title=row.category,
            requested_by={"id": row.created_by, "name": row.creator.username if row.creator else None},
            company_id=row.branch.company_id if row.branch else None,
            branch_id=row.branch_id,
            due_at=None,
        ))
    leave_query = db.query(LeaveRequest).join(User, User.id == LeaveRequest.user_id)
    if scope.branch_id is not None:
        leave_query = leave_query.filter(User.branch_id == scope.branch_id)
    elif scope.company_ids:
        leave_query = leave_query.filter((User.company_id.in_(scope.company_ids)) | (User.current_company_id.in_(scope.company_ids)))
    else:
        leave_query = leave_query.filter(False)
    for row in leave_query.filter(LeaveRequest.status == LeaveStatus.PENDING).all():
        items.append(_item(
            "medium",
            row.created_at or row.start_date,
            id=f"leave-request-{row.id}",
            source="leave_requests",
            type="leave_pending",
            status=_status_text(row.status),
            value=0.0,
            title=row.leave_type.value if hasattr(row.leave_type, "value") else str(row.leave_type),
            requested_by={"id": row.user_id, "name": row.user.username if row.user else None},
            company_id=row.user.company_id if row.user else None,
            branch_id=row.user.branch_id if row.user else None,
            due_at=None,
        ))
    for row in branch_scoped_query(db, StaffLeaveRequest, scope).filter(StaffLeaveRequest.status == LeaveStatus.PENDING).all():
        items.append(_item(
            "medium",
            row.created_at or row.start_date,
            id=f"staff-leave-request-{row.id}",
            source="staff_leave_requests",
            type="staff_leave_pending",
            status=_status_text(row.status),
            value=0.0,
            title=row.leave_type,
            requested_by={"id": row.StaffEmployee_profile_id, "name": None},
            company_id=row.branch.company_id if row.branch else None,
            branch_id=row.branch_id,
            due_at=None,
        ))
    items.sort(key=lambda item: (-item["priority_rank"], item["created_at"] or ""))
    count = len(items)
    total_value = round(sum(item["value"] or 0 for item in items), 2)
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
        unit="decisions",
        metric_name="decision_queue",
        computation_time_ms=max(0, int((time.perf_counter() - started) * 1000)),
        details={"items": items[:50], "total_value": total_value},
    )

__all__ = ["compute_decision_queue"]
