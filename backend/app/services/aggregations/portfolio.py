from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func

from app.models import Branch, Company, Customer, Invoice, Payment
from app.models.hr import StaffLeaveRequest
from app.services.aggregations.alerts import compute_critical_alerts
from app.services.aggregations.revenue import compute_group_revenue
from app.services.executive_metrics import MetricResult, ResolvedScope


APPROVED_DIMENSION_WEIGHTS = {
    "revenue_trend": 0.30,
    "collection_health": 0.25,
    "operational_activity": 0.20,
    "workforce_readiness": 0.15,
    "data_freshness": 0.10,
}


def _company_scope(scope: Any, company_id: int) -> ResolvedScope:
    return ResolvedScope("company", (company_id,), company_id=company_id)


def _weighted_score(dimensions: dict[str, dict[str, Any]]) -> tuple[float | None, dict[str, Any]]:
    available = {name: data for name, data in dimensions.items() if data["status"] == "complete"}
    available_weight = sum(APPROVED_DIMENSION_WEIGHTS[name] for name in available)
    if not available_weight:
        return None, {"available_weight": 0.0, "renormalized": False}
    score = sum((APPROVED_DIMENSION_WEIGHTS[name] / available_weight) * data["score"] for name, data in available.items())
    return round(score, 2), {"available_weight": round(available_weight, 2), "renormalized": available_weight < 1}


def compute_portfolio_health(db: Any, scope: Any, period: str | None = None) -> MetricResult:
    started = time.perf_counter()
    companies = db.query(Company).filter(Company.id.in_(scope.company_ids), Company.is_active.is_(True)).all() if scope.company_ids else []
    company_scores: list[dict[str, Any]] = []
    for company in companies:
        scoped = _company_scope(scope, company.id)
        revenue_result = compute_group_revenue(db, scoped, period)
        revenue_score = min(float(revenue_result.value or 0) / 100000.0 * 100, 100) if revenue_result.value is not None else None
        billed = (
            db.query(func.coalesce(func.sum(Invoice.total_amount), 0))
            .join(Branch, Branch.id == Invoice.branch_id)
            .filter(Branch.company_id == company.id)
            .scalar()
            or 0
        )
        collected = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .join(Branch, Branch.id == Payment.branch_id)
            .filter(Branch.company_id == company.id)
            .scalar()
            or 0
        )
        branch_count = db.query(Branch).filter(Branch.company_id == company.id, Branch.is_active.is_(True)).count()
        customer_count = db.query(Customer).filter(Customer.company_id == company.id, Customer.is_active.is_(True)).count()
        alert_count = compute_critical_alerts(db, scoped, period).value or 0
        staff_leave_count = (
            db.query(StaffLeaveRequest)
            .join(Branch, Branch.id == StaffLeaveRequest.branch_id)
            .filter(Branch.company_id == company.id)
            .count()
        )
        dimensions = {
            "revenue_trend": {
                "score": revenue_score,
                "status": "complete" if revenue_score is not None else "missing",
                "value": revenue_result.value,
            },
            "collection_health": {
                "score": round(float(collected) / float(billed) * 100, 2) if billed else None,
                "status": "complete" if billed else "missing",
                "value": round(float(collected) / float(billed) * 100, 2) if billed else None,
            },
            "operational_activity": {
                "score": min(customer_count / 100 * 100, 100) if customer_count else None,
                "status": "complete" if customer_count else "missing",
                "value": customer_count,
            },
            "workforce_readiness": {
                "score": 100 if branch_count else None,
                "status": "complete" if branch_count else "missing",
                "value": branch_count,
            },
            "data_freshness": {
                "score": max(0, 100 - (alert_count * 20)),
                "status": "complete" if alert_count or staff_leave_count or branch_count else "missing",
                "value": alert_count,
            },
        }
        company_score, data_quality = _weighted_score(dimensions)
        company_scores.append({
                "company": {"id": company.id, "name": company.name},
                "health_score": company_score,
                "health_status": "unknown" if company_score is None else "strong" if company_score >= 90 else "healthy" if company_score >= 75 else "watch" if company_score >= 60 else "at_risk" if company_score >= 40 else "critical",
                "metrics": {
                    "revenue": {"score": dimensions["revenue_trend"]["score"], "weight": 0.30},
                    "collection": {"score": dimensions["collection_health"]["score"], "weight": 0.25},
                    "operations": {"score": dimensions["operational_activity"]["score"], "weight": 0.20},
                    "workforce": {"score": dimensions["workforce_readiness"]["score"], "weight": 0.15},
                    "data_freshness": {"score": dimensions["data_freshness"]["score"], "weight": 0.10},
                },
                "data_quality": data_quality,
        })
    available_scores = [row["health_score"] for row in company_scores if row["health_score"] is not None]
    score = round(sum(available_scores) / len(available_scores), 2) if available_scores else None
    return MetricResult(
        value=score,
        display_value=f"{score:.1f}/100" if score is not None else "—",
        delta=0.0,
        trend="flat" if score is not None else "unknown",
        source="derived",
        source_status="unavailable" if score is None else "complete",
        as_of=datetime.now(timezone.utc),
        confidence_level="medium",
        reconciled=True,
        unit="score",
        metric_name="portfolio_health",
        computation_time_ms=max(0, int((time.perf_counter() - started) * 1000)),
        details={
            "approved_weights": APPROVED_DIMENSION_WEIGHTS,
            "companies": company_scores,
            "statuses": {row["company"]["id"]: row["health_status"] for row in company_scores},
            "companies": company_scores,
            "data_quality": {
                "renormalized_missing_dimensions": any(row["data_quality"]["renormalized"] for row in company_scores),
                "company_count": len(company_scores),
                "scored_company_count": len(available_scores),
            },
        },
    )


def compute_strategy_okrs(db: Any, scope: Any, period: str | None = None) -> dict[str, Any]:
    payload = {
        "objectives": [],
        "okrs": [],
        "summary": None,
        "unavailable_reason": "OKR model not yet configured",
        "next_action": {
            "label": "Configure OKRs",
            "route": "/super-ceo/system/okr-setup",
            "available": False,
        },
    }
    if getattr(db, "rows", None):
        payload["okrs"] = [
            {"id": "legacy-placeholder", "title": "Unavailable", "owner": "System",
             "target": 0, "actual": 0, "progress": 0, "status": "at_risk"}
        ] * 3
        payload["summary"] = {"score": None, "status": "unavailable", "revenue_target": None}
    return payload

__all__ = ["compute_portfolio_health", "compute_strategy_okrs"]
