from dataclasses import replace
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.aggregations.alerts import compute_critical_alerts
from app.services.aggregations.authoritative import (
    compute_active_companies,
    compute_activity_feed,
    compute_branch_count,
    compute_user_count,
)
from app.services.aggregations.cash import compute_cash_conversion, compute_performance_summary
from app.services.aggregations.customers import compute_customer_activity
from app.services.aggregations.decisions import compute_decision_queue
from app.services.aggregations.portfolio import compute_portfolio_health, compute_strategy_okrs
from app.services.aggregations.revenue import compute_group_revenue
from app.services.aggregations.revenue import compute_revenue_trend
from app.services.executive_metrics import (
    EXECUTIVE_METRICS_CACHE,
    METRIC_DEFINITIONS,
    METRIC_REGISTRY,
    ScopeResolver,
    audit_expensive_query,
    envelope,
    query_params_hash,
)
from app.utils.auth_system import require_super_admin

router = APIRouter(prefix="/super-ceo/metrics", tags=["Super CEO Metrics"])
overview_router = APIRouter(prefix="/super-ceo/overview", tags=["Super CEO Overview"])


@router.get("/definitions")
def metric_definitions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    scope = ScopeResolver(db, current_user).resolve()
    return envelope(
        {"metrics": [definition.to_dict() for definition in METRIC_DEFINITIONS]},
        scope,
        source_status="complete",
        ttl_seconds=300,
        refresh_after_seconds=300,
    )


AUTHORITATIVE_COMPUTERS = {
    "active_companies": compute_active_companies,
    "branch_count": compute_branch_count,
    "user_count": compute_user_count,
}


def _metric_result(db: Session, scope, metric_name: str, period: str | None):
    definition = METRIC_REGISTRY[metric_name]
    key = EXECUTIVE_METRICS_CACHE.key(metric_name, scope.company_id, scope.brand_id, scope.branch_id, period)
    params_hash = query_params_hash({"metric": metric_name, "period": period, "scope": scope.to_dict()})
    cached = EXECUTIVE_METRICS_CACHE.get(key)
    if cached is not None:
        return replace(cached, cache_hit=True, query_params_hash=params_hash)
    result = AUTHORITATIVE_COMPUTERS[metric_name](db, scope, period=period)
    result.query_params_hash = params_hash
    result.cache_hit = False
    EXECUTIVE_METRICS_CACHE.set(key, result, definition.refresh_cadence_seconds)
    return result


@overview_router.get("/metrics")
def overview_metrics(
    metric: str | None = Query(default=None),
    include: str | None = Query(default=None),
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    scope = ScopeResolver(db, current_user).resolve()
    names = [metric] if metric else list(AUTHORITATIVE_COMPUTERS)
    if include == "derived" and metric is None:
        results = {name: _metric_result(db, scope, name, period) for name in names}
        derived = {
            "group_revenue": compute_group_revenue(db, scope, period),
            "revenue_trend": compute_revenue_trend(db, scope, period),
            "customer_metrics": compute_customer_activity(db, scope, period),
            "critical_alerts": compute_critical_alerts(db, scope, period),
            "cash_conversion": compute_cash_conversion(db, scope, period),
        }
        results.update(derived)
        return envelope(
            {name: result.to_dict() for name, result in results.items()},
            scope,
            source_status="partial" if any(result.source_status in {"partial", "empty"} for result in results.values()) else "complete",
            sources=sorted({result.source for result in results.values()}),
            ttl_seconds=900,
            refresh_after_seconds=900,
        )
    unknown = [name for name in names if name not in AUTHORITATIVE_COMPUTERS]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unsupported authoritative metric: {unknown[0]}")
    results = {name: _metric_result(db, scope, name, period) for name in names}
    for name, result in results.items():
        if not result.cache_hit:
            audit_expensive_query(
                db,
                actor_id=current_user.id,
                endpoint="/api/super-ceo/overview/metrics",
                metric_name=name,
                scope=scope,
                duration_ms=result.computation_time_ms or 0,
                row_count=int(result.value or 0),
                cache_hit=False,
                source_tables=list(METRIC_REGISTRY[name].source_tables),
                degradation_status=result.source_status,
            )
    hit = all(result.cache_hit for result in results.values())
    ttl = min(METRIC_REGISTRY[name].refresh_cadence_seconds for name in names)
    return envelope(
        {name: result.to_dict() for name, result in results.items()},
        scope,
        source_status="empty" if results and all(result.source_status == "empty" for result in results.values()) else "complete",
        sources=sorted({result.source for result in results.values()}),
        cache_hit=hit,
        ttl_seconds=ttl,
        refresh_after_seconds=ttl,
    )


@overview_router.get("/activity-feed")
def activity_feed(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    types: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    scope = ScopeResolver(db, current_user).resolve()
    type_set = {value.strip().lower() for value in types.split(",") if value.strip()} if types else None
    cache_key = EXECUTIVE_METRICS_CACHE.key("activity_feed", scope.company_id, scope.brand_id, scope.branch_id, f"{limit}:{offset}:{types or ''}")
    cached = EXECUTIVE_METRICS_CACHE.get(cache_key)
    if cached is None:
        events, computation_time_ms = compute_activity_feed(db, scope, limit=limit, offset=offset, types=type_set)
        cached = {"events": events, "computation_time_ms": computation_time_ms}
        EXECUTIVE_METRICS_CACHE.set(cache_key, cached, METRIC_REGISTRY["activity_feed"].refresh_cadence_seconds)
        cache_hit = False
    else:
        cache_hit = True
    if not cache_hit and cached["computation_time_ms"] > 500:
        audit_expensive_query(
            db,
            actor_id=current_user.id,
            endpoint="/api/super-ceo/overview/activity-feed",
            metric_name="activity_feed",
            scope=scope,
            duration_ms=cached["computation_time_ms"],
            row_count=len(cached["events"]),
            cache_hit=False,
            source_tables=["activity_logs", "ceo_audit_logs"],
            degradation_status="complete",
        )
    return envelope(
        cached["events"],
        scope,
        source_status="empty" if not cached["events"] else "complete",
        sources=["activity_logs", "ceo_audit_logs"],
        cache_hit=cache_hit,
        ttl_seconds=METRIC_REGISTRY["activity_feed"].refresh_cadence_seconds,
        refresh_after_seconds=METRIC_REGISTRY["activity_feed"].refresh_cadence_seconds,
    )


def _derived_bundle_payload(db: Session, scope, period: str | None = None) -> dict[str, object]:
    return {
        "group_revenue": compute_group_revenue(db, scope, period).to_dict(),
        "revenue_trend": compute_revenue_trend(db, scope, period).to_dict(),
        "customer_metrics": compute_customer_activity(db, scope, period).to_dict(),
        "critical_alerts": compute_critical_alerts(db, scope, period).to_dict(),
        "decision_queue": compute_decision_queue(db, scope, period).to_dict(),
        "portfolio_health": compute_portfolio_health(db, scope, period).to_dict(),
        "cash_conversion": compute_cash_conversion(db, scope, period).to_dict(),
    }


@router.get("/derived/bundle")
@router.get("/metrics/derived/bundle")
def derived_bundle(
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    scope = ScopeResolver(db, current_user).resolve()
    return envelope(
        _derived_bundle_payload(db, scope, period),
        scope,
        source_status="complete",
        sources=["derived_metrics"],
        ttl_seconds=900,
        refresh_after_seconds=900,
    )


@router.get("/portfolio-health")
@overview_router.get("/portfolio-health")
@router.get("/metrics/portfolio-health")
def portfolio_health_route(
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    scope = ScopeResolver(db, current_user).resolve()
    result = compute_portfolio_health(db, scope, period)
    return envelope(result.to_dict(), scope, source_status=result.source_status, sources=["portfolio"], ttl_seconds=900, refresh_after_seconds=900)


@router.get("/decision-queue")
@overview_router.get("/decision-queue")
@router.get("/metrics/decision-queue")
def decision_queue_route(
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    scope = ScopeResolver(db, current_user).resolve()
    result = compute_decision_queue(db, scope, period)
    return envelope(result.to_dict(), scope, source_status=result.source_status, sources=["decisions"], ttl_seconds=300, refresh_after_seconds=300)


@router.get("/strategy/okrs")
@overview_router.get("/strategy/okrs")
@router.get("/metrics/strategy/okrs")
def strategy_okrs_route(
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    scope = ScopeResolver(db, current_user).resolve()
    payload = compute_strategy_okrs(db, scope, period)
    return envelope(payload, scope, source_status="unavailable", sources=[], ttl_seconds=900, refresh_after_seconds=900)


@router.get("/performance/summary")
@overview_router.get("/performance/summary")
@router.get("/metrics/performance/summary")
def performance_summary_route(
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    scope = ScopeResolver(db, current_user).resolve()
    payload = compute_performance_summary(db, scope, period)
    return envelope(payload, scope, source_status="complete", sources=["performance"], ttl_seconds=900, refresh_after_seconds=900)


# /api/super-ceo direct aliases
derived_router = APIRouter(prefix="/super-ceo", tags=["Super CEO Derived Metrics"])

@derived_router.get("/derived/bundle")
@derived_router.get("/portfolio-health")
@derived_router.get("/decision-queue")
@derived_router.get("/strategy/okrs")
@derived_router.get("/performance/summary")
def derived_router_aliases(
    request: Request,
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    scope = ScopeResolver(db, current_user).resolve()
    if request.url.path.endswith("/strategy/okrs"):
        return envelope(
            compute_strategy_okrs(db, scope, period),
            scope,
            source_status="unavailable",
            sources=[],
            ttl_seconds=900,
            refresh_after_seconds=900,
        )
    if request.url.path.endswith("/performance/summary"):
        return envelope(
            compute_performance_summary(db, scope, period),
            scope,
            source_status="partial",
            sources=["performance"],
            ttl_seconds=900,
            refresh_after_seconds=900,
        )
    if request.url.path.endswith("/portfolio-health"):
        result = compute_portfolio_health(db, scope, period)
        return envelope(result.to_dict(), scope, source_status=result.source_status, sources=["portfolio"], ttl_seconds=900, refresh_after_seconds=900)
    if request.url.path.endswith("/decision-queue"):
        result = compute_decision_queue(db, scope, period)
        return envelope(result.to_dict(), scope, source_status=result.source_status, sources=["decisions"], ttl_seconds=300, refresh_after_seconds=300)
    return envelope(
        {
            "bundle": _derived_bundle_payload(db, scope, period),
            "portfolio_health": compute_portfolio_health(db, scope, period).to_dict(),
            "decision_queue": compute_decision_queue(db, scope, period).to_dict(),
            "strategy_okrs": compute_strategy_okrs(db, scope, period),
            "performance_summary": compute_performance_summary(db, scope, period),
        },
        scope,
        source_status="complete",
        sources=["derived"],
        ttl_seconds=900,
        refresh_after_seconds=900,
    )
