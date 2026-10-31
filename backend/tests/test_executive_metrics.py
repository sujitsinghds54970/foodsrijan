from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.models import Brand, Branch, Company, Department
from app.services.executive_metrics import (
    METRIC_DEFINITIONS,
    METRIC_REGISTRY,
    ExecutiveMetricsCache,
    MetricResult,
    ResolvedScope,
    ScopeResolver,
    envelope,
    query_params_hash,
)


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return [(row.id,) for row in self.rows]

    def first(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, companies):
        self.companies = companies

    def query(self, model):
        if model is Company or model is Company.id:
            return FakeQuery(self.companies)
        return FakeQuery([])


class SuperCEO:
    id = 1
    is_active = True
    is_super_ceo = True
    is_super_admin = False
    role = "super_ceo"


def test_registry_contains_approved_metrics():
    expected = {
        "group_revenue", "operating_margin", "active_companies",
        "branch_count", "user_count", "critical_alerts", "portfolio_health",
        "decision_queue", "customer_metrics", "cash_conversion", "activity_feed",
        "leadership_pulse_nps", "leadership_pulse_exit_risk", "okr_progress",
        "department_kpis", "revenue_trend", "performance_summary",
    }
    assert expected == set(METRIC_REGISTRY)
    assert len(METRIC_DEFINITIONS) == len(expected)
    assert all(definition.name.isidentifier() for definition in METRIC_DEFINITIONS)


def test_metric_result_serializes_traceability_fields():
    result = MetricResult(
        1, "1", 0, "flat", "companies", "complete",
        datetime.now(timezone.utc),
        metric_name="active_companies",
        computation_time_ms=4,
        cache_hit=True,
        query_params_hash="abc",
    )
    payload = result.to_dict()
    assert payload["metric_name"] == "active_companies"
    assert payload["computation_time_ms"] == 4
    assert payload["cache_hit"] is True
    assert payload["as_of"].endswith("+00:00")


def test_scope_resolves_all_active_companies():
    db = FakeDB([Company(id=1, is_active=True), Company(id=2, is_active=True)])
    scope = ScopeResolver(db, SuperCEO()).resolve()
    assert scope.level == "system"
    assert scope.company_ids == (1, 2)
    assert scope.to_dict()["company_ids"] == [1, 2]


def test_scope_resolves_zero_companies_without_error():
    scope = ScopeResolver(FakeDB([]), SuperCEO()).resolve()
    assert scope.company_ids == ()


def test_scope_rejects_invalid_company():
    with pytest.raises(HTTPException) as error:
        ScopeResolver(FakeDB([]), SuperCEO()).resolve(company_id=999)
    assert error.value.status_code == 403


def test_cache_key_and_query_hash_are_stable():
    cache = ExecutiveMetricsCache()
    assert cache.key("revenue", 1, None, None, "month") == cache.key("revenue", 1, None, None, "month")
    assert query_params_hash({"b": 2, "a": 1}) == query_params_hash({"a": 1, "b": 2})


def test_envelope_serialization_and_degradation():
    scope = ResolvedScope("system", (1,))
    payload = envelope({}, scope, source_status="partial", missing_sources=["secondary"])
    assert payload["meta"]["degradation_level"] == "minor"
    assert payload["meta"]["refresh_after_seconds"] == 900
    assert payload["meta"]["scope"]["company_ids"] == [1]
