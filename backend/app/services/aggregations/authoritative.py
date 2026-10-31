from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import ActivityLog, Branch, Company, User
from app.models.ceo import CeoAuditLog
from app.services.executive_metrics import MetricResult, ResolvedScope


def _result(metric_name: str, value: Any, source: str, started: float, *, empty: bool = False) -> MetricResult:
    return MetricResult(
        value=value,
        display_value=str(value),
        delta=None,
        trend="unknown",
        source=source,
        source_status="empty" if empty else "complete",
        as_of=datetime.now(timezone.utc),
        confidence_level="high",
        reconciled=True,
        unit="count",
        metric_name=metric_name,
        computation_time_ms=max(0, int((time.perf_counter() - started) * 1000)),
    )


def compute_active_companies(db: Session, scope: ResolvedScope, period: str | None = None) -> MetricResult:
    started = time.perf_counter()
    count = db.query(Company).filter(Company.id.in_(scope.company_ids), Company.is_active.is_(True)).count() if scope.company_ids else 0
    return _result("active_companies", count, "companies", started, empty=count == 0)


def compute_branch_count(db: Session, scope: ResolvedScope, period: str | None = None) -> MetricResult:
    started = time.perf_counter()
    query = db.query(Branch).filter(Branch.company_id.in_(scope.company_ids), Branch.is_active.is_(True)) if scope.company_ids else db.query(Branch).filter(False)
    if scope.brand_id is not None:
        query = query.filter(Branch.brand_id == scope.brand_id)
    if scope.branch_id is not None:
        query = query.filter(Branch.id == scope.branch_id)
    count = query.count()
    return _result("branch_count", count, "branches", started, empty=count == 0)


def compute_user_count(db: Session, scope: ResolvedScope, period: str | None = None) -> MetricResult:
    started = time.perf_counter()
    if not scope.company_ids:
        count = 0
    else:
        query = db.query(User).filter(
            User.is_active.is_(True),
            or_(User.company_id.in_(scope.company_ids), User.current_company_id.in_(scope.company_ids)),
        )
        if scope.branch_id is not None:
            query = query.filter(User.branch_id == scope.branch_id)
        if hasattr(query, "distinct"):
            count = query.distinct(User.id).count()
        else:
            rows = query.all() if hasattr(query, "all") else []
            seen = set()
            for row in rows:
                if getattr(row, "id", None) is not None:
                    seen.add(row.id)
            count = len(seen)
    return _result("user_count", count, "users", started, empty=count == 0)


def compute_activity_feed(
    db: Session,
    scope: ResolvedScope,
    *,
    limit: int = 50,
    offset: int = 0,
    types: set[str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    started = time.perf_counter()
    branch_ids = []
    if scope.company_ids:
        branch_query = db.query(Branch.id).filter(Branch.company_id.in_(scope.company_ids))
        if scope.brand_id is not None:
            branch_query = branch_query.filter(Branch.brand_id == scope.brand_id)
        if scope.branch_id is not None:
            branch_query = branch_query.filter(Branch.id == scope.branch_id)
        branch_ids = [row[0] for row in branch_query.all()]

    activity_query = db.query(ActivityLog)
    if scope.company_ids:
        activity_query = activity_query.filter(or_(ActivityLog.branch_id.in_(branch_ids), ActivityLog.branch_id.is_(None)))
    else:
        activity_query = activity_query.filter(False)
    audit_query = db.query(CeoAuditLog)
    activity_rows = activity_query.order_by(ActivityLog.timestamp.desc()).limit(1000).all()
    audit_rows = audit_query.order_by(CeoAuditLog.created_at.desc()).limit(1000).all()

    events: list[dict[str, Any]] = []
    for row in activity_rows:
        event_type = (row.entity_type or "system").lower()
        if types and event_type not in types:
            continue
        events.append({
            "id": f"activity:{row.id}",
            "type": event_type,
            "actor": {"id": row.user_id, "name": row.user.username if row.user else None},
            "description": row.description,
            "scope": {"branch_id": row.branch_id},
            "timestamp": row.timestamp,
            "source": "activity_logs",
            "severity": "info",
        })
    for row in audit_rows:
        event_type = (row.action or "system").split(".")[0].lower()
        if types and event_type not in types:
            continue
        events.append({
            "id": f"audit:{row.id}",
            "type": event_type,
            "actor": {"id": row.user_id, "name": row.user.username if row.user else None},
            "description": row.action,
            "scope": {},
            "timestamp": row.created_at,
            "source": "ceo_audit_logs",
            "severity": "high" if row.response_status >= 400 else "info",
        })
    events.sort(key=lambda event: event["timestamp"] or datetime.min, reverse=True)
    total = len(events)
    return events[offset:offset + limit], max(0, int((time.perf_counter() - started) * 1000))
