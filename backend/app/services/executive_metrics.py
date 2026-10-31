from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.ceo import CeoAuditLog
from app.models import Brand, Branch, Company, Department, User
from app.utils.authority_resolver import is_super_ceo

logger = logging.getLogger(__name__)


@dataclass
class MetricResult:
    value: Any
    display_value: Optional[str]
    delta: Optional[float]
    trend: Optional[str]
    source: str
    source_status: str
    as_of: datetime
    sparkline_points: list[dict[str, Any]] = field(default_factory=list)
    confidence_level: str = "high"
    reconciled: Optional[bool] = None
    missing_sources: list[str] = field(default_factory=list)
    unavailable_reason: Optional[str] = None
    unit: Optional[str] = None
    metric_name: str = ""
    computation_time_ms: Optional[int] = None
    cache_hit: bool = False
    query_params_hash: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    deduplication_status: Optional[str] = None

    def __post_init__(self) -> None:
        if self.source_status not in {"complete", "partial", "empty", "unavailable", "error"}:
            raise ValueError(f"Unsupported metric source status: {self.source_status}")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["as_of"] = self.as_of.isoformat()
        return payload


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    label: str
    description: str
    authority: str
    source_tables: tuple[str, ...]
    refresh_cadence_seconds: int
    required_scopes: tuple[str, ...]
    owner: str
    unit: str
    supports_delta: bool
    supports_sparkline: bool
    unavailable_reason: Optional[str] = None
    depends_on: tuple[str, ...] = ()
    related_metrics: tuple[str, ...] = ()
    sample_query: Optional[str] = None
    icon_hint: str = "metric"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("source_tables", "required_scopes", "depends_on", "related_metrics"):
            payload[key] = list(payload[key])
        return payload


def _definition(name: str, label: str, description: str, authority: str, sources: tuple[str, ...], cadence: int, scopes: tuple[str, ...], unit: str, *, delta: bool = False, sparkline: bool = False, unavailable_reason: str | None = None, depends_on: tuple[str, ...] = (), related: tuple[str, ...] = (), icon: str = "metric") -> MetricDefinition:
    return MetricDefinition(name, label, description, authority, sources, cadence, scopes, "executive_metrics", unit, delta, sparkline, unavailable_reason, depends_on, related, f"/api/super-ceo/overview/metrics?metric={name}", icon)


METRIC_DEFINITIONS = (
    _definition("group_revenue", "Group Revenue", "Consolidated revenue from daily analytics snapshots.", "derived", ("daily_analytics_snapshots", "branches", "companies"), 900, ("system", "company", "brand", "branch"), "currency", delta=True, sparkline=True, depends_on=("active_companies", "branch_count"), related=("revenue_trend", "cash_conversion"), icon="revenue"),
    _definition("operating_margin", "Operating Margin", "Operating margin pending an approved accounting policy.", "unavailable", ("daily_analytics_snapshots", "daily_expenses", "finance_expenses", "payroll_runs"), 86400, ("system", "company", "brand", "branch"), "percent", unavailable_reason="Pending accounting policy definition", icon="margin"),
    _definition("active_companies", "Active Companies", "Count of active companies visible to the Super CEO.", "authoritative", ("companies",), 300, ("system",), "companies", delta=True, related=("portfolio_health",), icon="company"),
    _definition("branch_count", "Active Branches", "Count of active branches in the authorized scope.", "authoritative", ("branches",), 300, ("system", "company", "brand"), "branches", delta=True, related=("portfolio_health",), icon="branch"),
    _definition("user_count", "Active Users", "Count of active users in the authorized scope.", "authoritative", ("users", "user_companies"), 300, ("system", "company", "brand", "branch"), "users", delta=True, related=("portfolio_health",), icon="users"),
    _definition("critical_alerts", "Critical Alerts", "Normalized high-priority alerts from supported workflow and financial sources.", "derived", ("invoices", "finance_expenses", "leave_requests", "staff_leave_requests", "payroll_locks"), 300, ("system", "company", "brand", "branch", "department"), "alerts", delta=True, related=("decision_queue",), icon="alert"),
    _definition("portfolio_health", "Portfolio Health", "Weighted company health score across approved operational dimensions.", "derived", ("companies", "branches", "daily_analytics_snapshots", "invoices", "payments", "employee_profiles", "staff_leave_requests"), 900, ("system", "company", "brand", "branch"), "score", delta=True, sparkline=True, depends_on=("group_revenue", "revenue_trend", "branch_count", "user_count"), related=("performance_summary",), icon="health"),
    _definition("decision_queue", "Decision Queue", "Normalized pending decisions from supported approval records.", "derived", ("leave_requests", "finance_expenses", "staff_leave_requests"), 120, ("system", "company", "brand", "branch", "department"), "decisions", related=("critical_alerts",), icon="decision"),
    _definition("customer_metrics", "Customer Activity", "Per-company customer counts without global deduplication.", "derived", ("customers", "invoices", "payments", "appointments", "patient_feedbacks"), 900, ("system", "company", "brand", "branch"), "customers", delta=True, sparkline=True, related=("performance_summary", "cash_conversion"), icon="customer"),
    _definition("cash_conversion", "Cash Conversion", "Collections and billed revenue with a derived, unreconciled ratio.", "derived", ("invoices", "payments", "finance_invoices", "finance_transactions"), 900, ("system", "company", "brand", "branch"), "percent", delta=True, sparkline=True, related=("group_revenue", "customer_metrics"), icon="cash"),
    _definition("activity_feed", "Executive Activity Feed", "Merged activity and executive audit events.", "authoritative", ("activity_logs", "ceo_audit_logs"), 60, ("system", "company", "brand", "branch"), "events", icon="activity"),
    _definition("leadership_pulse_nps", "NPS", "Formal NPS is unavailable; average rating is a secondary signal.", "unavailable", ("patient_feedbacks",), 86400, ("system", "company", "brand", "branch"), "score", unavailable_reason="Survey definition not approved", icon="feedback"),
    _definition("leadership_pulse_exit_risk", "Exit Risk", "Employee exit-risk scoring is not yet defined.", "unavailable", ("employee_profiles", "attendance", "leave_requests", "staff_performance_notes"), 86400, ("system", "company", "brand", "branch", "department"), "score", unavailable_reason="HR risk model not yet defined", icon="people"),
    _definition("okr_progress", "OKR Progress", "Objective and key-result tracking is not yet configured.", "unavailable", (), 300, ("system", "company", "brand", "department"), "percent", unavailable_reason="OKR model not yet configured", icon="okr"),
    _definition("department_kpis", "Department KPIs", "Department KPI definitions and targets are not yet configured.", "unavailable", ("departments",), 86400, ("system", "company", "brand", "department"), "mixed", unavailable_reason="Department KPI definitions not yet configured", icon="department"),
    _definition("revenue_trend", "Revenue Trend", "Revenue trend used by Portfolio Health.", "derived", ("daily_analytics_snapshots", "branches", "companies"), 900, ("system", "company", "brand", "branch"), "percent", delta=True, sparkline=True, related=("group_revenue", "portfolio_health"), icon="trend"),
    _definition("performance_summary", "Cross-Company Performance", "Cross-company operational, revenue, collection, and customer summary.", "derived", ("companies", "branches", "daily_analytics_snapshots", "invoices", "payments", "customers"), 900, ("system", "company", "brand", "branch"), "mixed", delta=True, sparkline=True, depends_on=("group_revenue", "customer_metrics", "cash_conversion"), icon="performance"),
)
METRIC_REGISTRY = {definition.name: definition for definition in METRIC_DEFINITIONS}


@dataclass(frozen=True)
class ResolvedScope:
    level: str
    company_ids: tuple[int, ...]
    company_id: int | None = None
    brand_id: int | None = None
    branch_id: int | None = None
    department_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "company_id": self.company_id, "brand_id": self.brand_id, "branch_id": self.branch_id, "department_id": self.department_id, "company_ids": list(self.company_ids)}


class ScopeResolver:
    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.current_user = current_user
        self._accessible_company_ids: tuple[int, ...] | None = None
        self._resolved: dict[tuple[int | None, int | None, int | None, int | None], ResolvedScope] = {}

    def accessible_company_ids(self) -> list[int]:
        if self._accessible_company_ids is None:
            if is_super_ceo(self.current_user):
                rows = self.db.query(Company.id).filter(Company.is_active.is_(True)).all()
                ids = [row[0] for row in rows]
            else:
                ids = [company.id for company in getattr(self.current_user, "companies", ()) if getattr(company, "is_active", False)]
            self._accessible_company_ids = tuple(sorted({int(value) for value in ids}))
            logger.info("Resolved executive company scope user_id=%s company_ids=%s", self.current_user.id, self._accessible_company_ids)
        return list(self._accessible_company_ids)

    def resolve(self, company_id: int | None = None, brand_id: int | None = None, branch_id: int | None = None, department_id: int | None = None) -> ResolvedScope:
        key = (company_id, brand_id, branch_id, department_id)
        if key in self._resolved:
            return self._resolved[key]
        accessible = set(self.accessible_company_ids())
        company_ids = accessible
        if company_id is not None:
            company = self.db.query(Company).filter(Company.id == company_id, Company.is_active.is_(True)).first()
            if not company or company.id not in accessible:
                raise HTTPException(status_code=403, detail="Requested company is not accessible")
            company_ids = {company.id}
        if brand_id is not None:
            brand = self.db.query(Brand).filter(Brand.id == brand_id, Brand.is_active.is_(True)).first()
            if not brand or brand.company_id not in company_ids:
                raise HTTPException(status_code=403, detail="Requested brand is not accessible")
            company_ids = {brand.company_id}
        if branch_id is not None:
            branch = self.db.query(Branch).filter(Branch.id == branch_id, Branch.is_active.is_(True)).first()
            if not branch or branch.company_id not in company_ids:
                raise HTTPException(status_code=403, detail="Requested branch is not accessible")
            company_ids = {branch.company_id}
        if department_id is not None:
            department = self.db.query(Department).filter(Department.id == department_id, Department.is_active.is_(True)).first()
            if not department or department.company_id not in company_ids:
                raise HTTPException(status_code=403, detail="Requested department is not accessible")
            company_ids = {department.company_id}
        level = "department" if department_id is not None else "branch" if branch_id is not None else "brand" if brand_id is not None else "company" if company_id is not None else "system"
        result = ResolvedScope(level, tuple(sorted(company_ids)), company_id, brand_id, branch_id, department_id)
        self._resolved[key] = result
        logger.info("Resolved executive scope user_id=%s scope=%s", self.current_user.id, result.to_dict())
        return result


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class ExecutiveMetricsCache:
    def __init__(self) -> None:
        self._entries: dict[str, _CacheEntry] = {}
        self._lock = Lock()

    @staticmethod
    def key(metric_name: str, company_id: Any = None, brand_id: Any = None, branch_id: Any = None, period: str | None = None, from_value: str | None = None, to_value: str | None = None, query_version: str = "v1") -> str:
        return f"{metric_name}:{company_id}:{brand_id}:{branch_id}:{period}:{from_value}:{to_value}:{query_version}"

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)
            if not entry or entry.expires_at <= time.monotonic():
                self._entries.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._entries[key] = _CacheEntry(value, time.monotonic() + ttl_seconds)

    def invalidate(self, prefix: str | None = None) -> None:
        with self._lock:
            if prefix is None:
                self._entries.clear()
            else:
                for key in [key for key in self._entries if key.startswith(prefix)]:
                    del self._entries[key]


EXECUTIVE_METRICS_CACHE = ExecutiveMetricsCache()


def invalidate_executive_metrics_cache() -> None:
    EXECUTIVE_METRICS_CACHE.invalidate()


def _invalidate_after_write(_mapper: Any, _connection: Any, _target: Any) -> None:
    invalidate_executive_metrics_cache()


for _model in (Company, Branch, User):
    for _event_name in ("after_insert", "after_update", "after_delete"):
        event.listen(_model, _event_name, _invalidate_after_write)


def query_params_hash(params: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()[:16]


def degradation_level(source_status: str, missing_sources: list[str] | None = None) -> str:
    if source_status == "error":
        return "critical"
    if source_status == "unavailable":
        return "major"
    if source_status == "partial" or missing_sources:
        return "minor"
    return "none"


def envelope(data: Any, scope: ResolvedScope, *, as_of: datetime | None = None, source_status: str = "complete", sources: list[str] | None = None, missing_sources: list[str] | None = None, cache_hit: bool = False, ttl_seconds: int = 900, errors: list[dict[str, Any]] | None = None, refresh_after_seconds: int | None = None) -> dict[str, Any]:
    missing = missing_sources or []
    return {
        "data": data,
        "meta": {
            "as_of": (as_of or datetime.now(timezone.utc)).isoformat(),
            "scope": scope.to_dict(),
            "source_status": source_status,
            "degradation_level": degradation_level(source_status, missing),
            "cache": {"hit": cache_hit, "ttl_seconds": ttl_seconds},
            "sources": sources or [],
            "missing_sources": missing,
            "refresh_after_seconds": refresh_after_seconds if refresh_after_seconds is not None else ttl_seconds,
        },
        "errors": errors or [],
    }


def audit_expensive_query(
    db: Session,
    *,
    actor_id: int,
    endpoint: str,
    metric_name: str,
    scope: ResolvedScope,
    duration_ms: int,
    row_count: int,
    cache_hit: bool,
    source_tables: list[str],
    degradation_status: str,
) -> None:
    """Persist an audit event only for expensive or unusually large reads."""
    if duration_ms <= 500 and row_count <= 10000:
        return
    previous = db.query(CeoAuditLog).order_by(CeoAuditLog.id.desc()).first()
    previous_signature = previous.signature if previous else None
    payload = {
        "actor": actor_id,
        "endpoint": endpoint,
        "metric_name": metric_name,
        "scope": scope.to_dict(),
        "duration_ms": duration_ms,
        "row_count": row_count,
        "cache_hit": cache_hit,
        "source_tables": source_tables,
        "degradation_status": degradation_status,
    }
    signature = hashlib.sha256(
        f"{previous_signature or ''}:{json.dumps(payload, sort_keys=True, default=str)}".encode()
    ).hexdigest()
    db.add(
        CeoAuditLog(
            user_id=actor_id,
            action="executive_metric.query",
            http_method="GET",
            endpoint=endpoint,
            response_status=200,
            request_meta=payload,
            previous_signature=previous_signature,
            signature=signature,
        )
    )
    db.commit()
