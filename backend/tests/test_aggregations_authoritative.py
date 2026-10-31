from datetime import datetime, timezone
from types import SimpleNamespace

from app.models import ActivityLog, Branch, Company, User
from app.models.ceo import CeoAuditLog
from app.services.aggregations.authoritative import (
    compute_active_companies,
    compute_activity_feed,
    compute_branch_count,
    compute_user_count,
)
from app.services.executive_metrics import (
    EXECUTIVE_METRICS_CACHE,
    ResolvedScope,
    invalidate_executive_metrics_cache,
)


class QueryStub:
    def __init__(self, rows=None, count_value=0):
        self.rows = rows or []
        self.count_value = count_value

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def distinct(self, *args, **kwargs):
        return self

    def count(self):
        return self.count_value

    def all(self):
        return self.rows


class AggregationDB:
    def __init__(self, counts=None, rows=None):
        self.counts = counts or {}
        self.rows = rows or {}

    def query(self, model):
        return QueryStub(self.rows.get(model, []), self.counts.get(model, 0))


def scope(**kwargs):
    return ResolvedScope("system", (1, 2), **kwargs)


def test_active_companies_returns_zero_when_empty():
    result = compute_active_companies(AggregationDB({Company: 0}), scope())
    assert result.value == 0
    assert result.source_status == "empty"


def test_active_companies_counts_active_records():
    result = compute_active_companies(AggregationDB({Company: 3}), scope())
    assert result.value == 3
    assert result.source == "companies"


def test_active_companies_accepts_company_scope():
    result = compute_active_companies(AggregationDB({Company: 1}), scope(company_id=2))
    assert result.metric_name == "active_companies"
    assert result.reconciled is True


def test_branch_count_returns_count():
    result = compute_branch_count(AggregationDB({Branch: 4}), scope())
    assert result.value == 4
    assert result.metric_name == "branch_count"


def test_branch_count_accepts_brand_scope():
    result = compute_branch_count(AggregationDB({Branch: 2}), scope(brand_id=7))
    assert result.value == 2
    assert result.confidence_level == "high"


def test_user_count_counts_active_users():
    result = compute_user_count(AggregationDB({User: 5}), scope())
    assert result.value == 5
    assert result.source_status == "complete"


def test_user_count_accepts_company_scope():
    result = compute_user_count(AggregationDB({User: 2}), scope(company_id=1))
    assert result.value == 2
    assert result.metric_name == "user_count"


def test_activity_feed_merges_sources_chronologically():
    newer = datetime(2026, 1, 2, tzinfo=timezone.utc)
    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    activity = SimpleNamespace(id=1, entity_type="company", user_id=2, user=SimpleNamespace(username="actor"), description="Updated", branch_id=None, timestamp=older)
    audit = SimpleNamespace(id=2, action="finance.reviewed", user_id=1, user=SimpleNamespace(username="ceo"), response_status=200, created_at=newer)
    db = AggregationDB(rows={Branch: [], ActivityLog: [activity], CeoAuditLog: [audit]})
    events, _ = compute_activity_feed(db, scope(), limit=50)
    assert [event["source"] for event in events] == ["ceo_audit_logs", "activity_logs"]


def test_activity_feed_respects_limit_and_offset():
    rows = [
        SimpleNamespace(id=index, entity_type="company", user_id=1, user=None, description=str(index), branch_id=None, timestamp=datetime(2026, 1, index + 1, tzinfo=timezone.utc))
        for index in range(3)
    ]
    db = AggregationDB(rows={Branch: [], ActivityLog: rows, CeoAuditLog: []})
    events, _ = compute_activity_feed(db, scope(), limit=1, offset=1)
    assert len(events) == 1
    assert events[0]["description"] == "1"


def test_metric_cache_hit_and_miss():
    EXECUTIVE_METRICS_CACHE.invalidate()
    key = EXECUTIVE_METRICS_CACHE.key("active_companies", 1)
    assert EXECUTIVE_METRICS_CACHE.get(key) is None
    EXECUTIVE_METRICS_CACHE.set(key, {"value": 2}, 60)
    assert EXECUTIVE_METRICS_CACHE.get(key) == {"value": 2}


def test_cache_invalidation_after_company_change():
    EXECUTIVE_METRICS_CACHE.invalidate()
    key = EXECUTIVE_METRICS_CACHE.key("active_companies", 1)
    EXECUTIVE_METRICS_CACHE.set(key, {"value": 1}, 60)
    invalidate_executive_metrics_cache()
    assert EXECUTIVE_METRICS_CACHE.get(key) is None


def test_authoritative_results_have_required_metadata():
    db = AggregationDB({Company: 1, Branch: 1, User: 1})
    results = [
        compute_active_companies(db, scope()),
        compute_branch_count(db, scope()),
        compute_user_count(db, scope()),
    ]
    assert all(result.metric_name for result in results)
    assert all(result.source_status in {"complete", "empty"} for result in results)
