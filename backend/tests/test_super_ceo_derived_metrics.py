from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Branch, Company, Customer, DailyAnalyticsSnapshot, FinanceExpense, Invoice, Payment, User
from app.models.customer import CustomerProfile
from app.models.daily_entry_module import DailyEntryModule
from app.models.hr import LeaveRequest, LeaveStatus, StaffLeaveRequest, StaffProfile
from app.models.patient_portal import CustomerFeedback
from app.services.aggregations.alerts import compute_critical_alerts
from app.services.aggregations.cash import compute_cash_conversion, compute_performance_summary
from app.services.aggregations.customers import compute_customer_activity
from app.services.aggregations.decisions import compute_decision_queue
from app.services.aggregations.portfolio import compute_portfolio_health, compute_strategy_okrs
from app.services.aggregations.revenue import compute_group_revenue, compute_revenue_trend
from app.services.executive_metrics import EXECUTIVE_METRICS_CACHE, METRIC_REGISTRY, ResolvedScope
from app.utils.auth_system import require_super_admin


SUPER_USER = User(
    id=999,
    username="super",
    email="super@example.com",
    hashed_password="x",
    role="super_ceo",
    is_super_admin=True,
    is_super_ceo=True,
    is_active=True,
    first_name="Super",
    last_name="CEO",
    phone="9999999999",
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    seed_foundation(db)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        EXECUTIVE_METRICS_CACHE.invalidate()


@pytest.fixture()
def client(db_session):
    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_super_admin] = lambda: SUPER_USER
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def seed_foundation(db):
    db.add_all(
        [
            Company(id=1, name="Alpha Foods", slug="alpha", is_active=True),
            Company(id=2, name="Beta Foods", slug="beta", is_active=True),
            Branch(
                id=1,
                company_id=1,
                name="Alpha Central",
                location="Mumbai",
                address="A1",
                city="Mumbai",
                state="MH",
                pincode="400001",
                phone="1111111111",
                email="alpha@example.com",
                license_number="LIC-A",
                branch_code="ALPHA",
                is_active=True,
            ),
            Branch(
                id=2,
                company_id=2,
                name="Beta Central",
                location="Pune",
                address="B1",
                city="Pune",
                state="MH",
                pincode="411001",
                phone="2222222222",
                email="beta@example.com",
                license_number="LIC-B",
                branch_code="BETA",
                is_active=True,
            ),
            User(
                id=1,
                username="alpha-user",
                email="alpha-user@example.com",
                hashed_password="x",
                role="staff",
                current_company_id=1,
                company_id=1,
                branch_id=1,
                is_active=True,
                first_name="Alpha",
                last_name="User",
                phone="1111111111",
            ),
            User(
                id=2,
                username="beta-user",
                email="beta-user@example.com",
                hashed_password="x",
                role="staff",
                current_company_id=2,
                company_id=2,
                branch_id=2,
                is_active=True,
                first_name="Beta",
                last_name="User",
                phone="2222222222",
            ),
        ]
    )
    db.commit()


def scope(company_id: int | None = 1, company_ids: tuple[int, ...] | None = None, branch_id: int | None = None) -> ResolvedScope:
    ids = company_ids if company_ids is not None else ((company_id,) if company_id is not None else (1, 2))
    level = "branch" if branch_id is not None else "company" if company_id is not None else "system"
    return ResolvedScope(level, ids, company_id=company_id, branch_id=branch_id)


def add_customer(db, *, id: int = 1, company_id: int = 1, branch_id: int = 1, active: bool = True):
    row = Customer(
        id=id,
        company_id=company_id,
        patient_id=f"PAT-{id}",
        branch_id=branch_id,
        first_name=f"Customer{id}",
        last_name="Test",
        date_of_birth=datetime(1990, 1, 1),
        gender="Other",
        phone=f"900000000{id}",
        email=f"customer{id}@example.com",
        address="Address",
        city="City",
        state="State",
        pincode="000000",
        emergency_contact="9999999999",
        emergency_contact_name="Contact",
        is_active=active,
    )
    db.add(row)
    db.commit()
    return row


def add_invoice(db, *, id: int = 1, patient_id: int = 1, branch_id: int = 1, total: float = 100.0, status: str = "pending", due_date: datetime | None = None):
    row = Invoice(
        id=id,
        invoice_number=f"INV-{id}",
        patient_id=patient_id,
        branch_id=branch_id,
        total_amount=total,
        final_amount=total,
        status=status,
        invoice_date=datetime(2026, 9, 1),
        due_date=due_date,
    )
    db.add(row)
    db.commit()
    return row


def add_payment(db, *, id: int = 1, invoice_id: int = 1, patient_id: int = 1, branch_id: int = 1, amount: float = 50.0):
    row = Payment(
        id=id,
        invoice_id=invoice_id,
        patient_id=patient_id,
        branch_id=branch_id,
        amount=amount,
        transaction_id=f"TXN-{id}",
        payment_date=datetime(2026, 9, 2),
    )
    db.add(row)
    db.commit()
    return row


def add_staff_profile(db, *, id: int = 1, user_id: int = 1, branch_id: int = 1):
    row = StaffProfile(id=id, user_id=user_id, branch_id=branch_id, created_by=user_id, staff_employee_id=f"EMP-{id}")
    db.add(row)
    db.commit()
    return row


def test_group_revenue_prefers_snapshots_and_never_combines_daily_entries(db_session):
    db_session.add(DailyAnalyticsSnapshot(branch_id=1, date=date(2026, 9, 25), total_revenue=100.0))
    db_session.add(
        DailyEntryModule(
            branch_id=1,
            auto_patient_id="D-1",
            auto_entry_datetime=datetime(2026, 9, 25, 10),
            patient_name="A",
            mobile="1",
            address="x",
            test_name="T",
            fee_amount=900,
            total_amount=900,
            payment_method="Cash",
            created_by=1,
        )
    )
    db_session.commit()
    result = compute_group_revenue(db_session, scope())
    assert result.value == 100.0
    assert result.source == "daily_analytics_snapshots"
    assert result.reconciled is True


def test_group_revenue_falls_back_to_daily_entry_module_when_snapshots_absent(db_session):
    db_session.add(
        DailyEntryModule(
            branch_id=1,
            auto_patient_id="D-2",
            auto_entry_datetime=datetime(2026, 9, 25, 10),
            patient_name="A",
            mobile="1",
            address="x",
            test_name="T",
            fee_amount=20,
            total_amount=250.25,
            payment_method="Cash",
            created_by=1,
        )
    )
    db_session.commit()
    result = compute_group_revenue(db_session, scope())
    assert result.value == 250.25
    assert result.source == "daily_entry_modules"
    assert result.source_status == "partial"
    assert result.reconciled is False


def test_group_revenue_unavailable_has_null_value(db_session):
    result = compute_group_revenue(db_session, scope())
    assert result.value is None
    assert result.source_status == "unavailable"
    assert result.missing_sources == ["daily_analytics_snapshots", "daily_entry_modules"]


def test_group_revenue_scope_excludes_other_companies(db_session):
    db_session.add(DailyAnalyticsSnapshot(branch_id=2, date=date(2026, 9, 25), total_revenue=500.0))
    db_session.commit()
    assert compute_group_revenue(db_session, scope(company_id=1)).value is None


def test_revenue_trend_uses_same_snapshot_source_and_same_length_previous_period(db_session):
    for offset, revenue in enumerate([50, 50, 100, 150]):
        db_session.add(DailyAnalyticsSnapshot(branch_id=1, date=date(2026, 9, 22 + offset), total_revenue=revenue))
    db_session.commit()
    result = compute_revenue_trend(db_session, scope(), period="2d")
    assert result.source == "daily_analytics_snapshots"
    assert result.value == 150.0
    assert result.details["same_length_previous_period"] is True
    assert result.details["previous_period"]["days"] == result.details["current_period"]["days"] == 2


def test_revenue_trend_falls_back_to_daily_entry_module_source(db_session):
    for day, amount in [(24, 100), (25, 200)]:
        db_session.add(
            DailyEntryModule(
                branch_id=1,
                auto_patient_id=f"D-{day}",
                auto_entry_datetime=datetime(2026, 9, day, 10),
                patient_name="A",
                mobile=str(day),
                address="x",
                test_name="T",
                fee_amount=amount,
                total_amount=amount,
                payment_method="Cash",
                created_by=1,
            )
        )
    db_session.commit()
    result = compute_revenue_trend(db_session, scope(), period="1d")
    assert result.source == "daily_entry_modules"
    assert result.value == 100.0


def test_revenue_trend_unavailable_has_null_value(db_session):
    result = compute_revenue_trend(db_session, scope())
    assert result.value is None
    assert result.source_status == "unavailable"


def test_customer_metrics_are_rich_dict_with_per_company_deduplication(db_session):
    add_customer(db_session, id=1)
    add_customer(db_session, id=2, active=False)
    db_session.add(CustomerProfile(patient_id=1, patient_code="P1", full_name="Customer 1", mobile="7000000001", password="x"))
    add_invoice(db_session, id=1, patient_id=1, total=120)
    add_invoice(db_session, id=2, patient_id=1, total=80)
    add_payment(db_session, id=1, invoice_id=1, patient_id=1, amount=100)
    db_session.add(CustomerFeedback(patient_id=1, rating=4, status="reviewed"))
    db_session.add(CustomerFeedback(patient_id=2, rating=2, status="reviewed"))
    db_session.commit()
    result = compute_customer_activity(db_session, scope())
    assert isinstance(result.value, dict)
    assert result.value["total_customers"] == 2
    assert result.value["active_customers"] == 1
    assert result.value["profile_count"] == 1
    assert result.value["invoice_count"] == 2
    assert result.value["revenue_per_customer"] == 100.0
    assert result.value["collection_per_customer"] == 50.0
    assert result.value["average_rating"] == 3.0
    assert result.value["repeat_rate"] == 100.0
    assert result.deduplication_status == "per_company_only"


def test_customer_metrics_missing_submetrics_are_null(db_session):
    add_customer(db_session, id=1)
    result = compute_customer_activity(db_session, scope())
    assert result.value["invoice_count"] is None
    assert result.value["feedback_count"] is None
    assert result.value["average_rating"] is None
    assert result.details["missing_submetrics_are_null"] is True


def test_customer_metrics_scope_does_not_globally_deduplicate(db_session):
    add_customer(db_session, id=1, company_id=1, branch_id=1)
    add_customer(db_session, id=2, company_id=2, branch_id=2)
    assert compute_customer_activity(db_session, scope(company_id=1)).value["total_customers"] == 1
    assert compute_customer_activity(db_session, scope(company_id=2)).value["total_customers"] == 1


def test_cash_conversion_includes_details_and_is_unreconciled(db_session):
    add_customer(db_session, id=1)
    add_invoice(db_session, id=1, total=200)
    add_payment(db_session, id=1, amount=50)
    result = compute_cash_conversion(db_session, scope())
    assert result.value == 25.0
    assert result.reconciled is False
    assert result.details["billed_revenue"] == 200.0
    assert result.details["collections"] == 50.0
    assert result.details["reconciled"] is False


def test_cash_conversion_without_billed_revenue_is_unavailable_null(db_session):
    result = compute_cash_conversion(db_session, scope())
    assert result.value is None
    assert result.source_status == "unavailable"


def test_critical_alerts_use_only_approved_b3_sources(db_session):
    add_customer(db_session, id=1)
    add_invoice(db_session, id=1, status="pending", due_date=datetime(2026, 1, 1))
    add_invoice(db_session, id=2, status="paid", due_date=datetime(2026, 1, 1))
    db_session.add(FinanceExpense(branch_id=1, category="Ops", amount=10, status="pending_approval", created_by=1))
    db_session.add(FinanceExpense(branch_id=1, category="Ops", amount=10, status="approved", created_by=1))
    db_session.add(LeaveRequest(user_id=1, leave_type="casual", start_date=datetime(2026, 9, 1), end_date=datetime(2026, 9, 2), status=LeaveStatus.PENDING))
    add_staff_profile(db_session)
    db_session.add(StaffLeaveRequest(StaffEmployee_profile_id=1, branch_id=1, leave_type="casual", start_date=datetime(2026, 9, 1), end_date=datetime(2026, 9, 2), status=LeaveStatus.PENDING))
    db_session.commit()
    result = compute_critical_alerts(db_session, scope())
    assert result.value == 4
    assert {item["source"] for item in result.details["alerts"]} == {"invoices", "finance_expenses", "leave_requests", "staff_leave_requests"}


def test_critical_alert_details_are_sorted_by_severity_then_date_and_capped(db_session):
    add_customer(db_session, id=1)
    for idx in range(25):
        add_invoice(db_session, id=idx + 1, status="pending", due_date=datetime(2026, 1, 1) + timedelta(days=idx))
    db_session.add(FinanceExpense(branch_id=1, category="Ops", amount=10, status="pending_approval", created_by=1, date=datetime(2026, 9, 1)))
    db_session.commit()
    result = compute_critical_alerts(db_session, scope())
    alerts = result.details["alerts"]
    assert len(alerts) == 20
    assert alerts[0]["severity"] == "high"
    assert alerts[0]["date"] > alerts[1]["date"]
    assert result.details["total_alerts"] == 26


def test_critical_alerts_respect_company_scope(db_session):
    add_customer(db_session, id=1)
    add_customer(db_session, id=2, company_id=2, branch_id=2)
    add_invoice(db_session, id=1, patient_id=1, branch_id=1, due_date=datetime(2026, 1, 1))
    add_invoice(db_session, id=2, patient_id=2, branch_id=2, due_date=datetime(2026, 1, 1))
    assert compute_critical_alerts(db_session, scope(company_id=1)).value == 1


def test_decision_queue_normalizes_items_sorted_priority_desc_then_oldest(db_session):
    db_session.add(FinanceExpense(branch_id=1, category="Newer", amount=20, status="pending_approval", created_by=1, created_at=datetime(2026, 9, 2)))
    db_session.add(FinanceExpense(branch_id=1, category="Older", amount=30, status="pending_approval", created_by=1, created_at=datetime(2026, 9, 1)))
    db_session.add(LeaveRequest(user_id=1, leave_type="casual", start_date=datetime(2026, 9, 1), end_date=datetime(2026, 9, 2), status=LeaveStatus.PENDING, created_at=datetime(2026, 8, 1)))
    db_session.commit()
    result = compute_decision_queue(db_session, scope())
    items = result.details["items"]
    assert [item["title"] for item in items[:2]] == ["Older", "Newer"]
    assert items[0]["priority"] == "high"
    assert items[-1]["priority"] == "medium"


def test_decision_queue_total_value_sums_financial_items(db_session):
    db_session.add(FinanceExpense(branch_id=1, category="A", amount=20, status="pending_approval", created_by=1))
    db_session.add(FinanceExpense(branch_id=1, category="B", amount=30.5, status="pending_approval", created_by=1))
    db_session.commit()
    result = compute_decision_queue(db_session, scope())
    assert result.value == 2
    assert result.details["total_value"] == 50.5


def test_portfolio_health_reports_weights_statuses_and_data_quality(db_session):
    add_customer(db_session, id=1)
    add_invoice(db_session, id=1, total=100)
    add_payment(db_session, id=1, amount=80)
    db_session.add(DailyAnalyticsSnapshot(branch_id=1, date=date(2026, 9, 25), total_revenue=100000))
    db_session.commit()
    result = compute_portfolio_health(db_session, scope())
    assert 0 <= result.value <= 100
    assert "approved_weights" in result.details
    assert result.details["statuses"][1] in {"healthy", "watch", "critical"}
    assert result.details["data_quality"]["scored_company_count"] == 1


def test_portfolio_health_renormalizes_missing_dimensions(db_session):
    db_session.add(DailyAnalyticsSnapshot(branch_id=1, date=date(2026, 9, 25), total_revenue=50000))
    db_session.commit()
    result = compute_portfolio_health(db_session, scope())
    assert result.value is not None
    assert result.details["data_quality"]["renormalized_missing_dimensions"] is True


def test_portfolio_health_unavailable_without_companies(db_session):
    result = compute_portfolio_health(db_session, ResolvedScope("system", ()))
    assert result.value is None
    assert result.source_status == "unavailable"


def test_strategy_okrs_remains_unavailable_payload(db_session):
    payload = compute_strategy_okrs(db_session, scope())
    assert payload["summary"] is None
    assert payload["unavailable_reason"] == "OKR model not yet configured"


def test_performance_summary_preserves_required_metric_keys(db_session):
    payload = compute_performance_summary(db_session, scope())
    assert set(payload["metrics"]) == {"revenue", "portfolio_health", "active_customers", "critical_alerts", "cash_conversion"}
    assert payload["status"] in {"healthy", "watch"}


def test_derived_bundle_route_returns_envelope_and_revenue_trend(client):
    response = client.get("/api/super-ceo/metrics/derived/bundle")
    assert response.status_code == 200
    payload = response.json()
    assert "data" in payload and "meta" in payload
    assert "revenue_trend" in payload["data"]


def test_direct_derived_bundle_alias_is_preserved(client):
    response = client.get("/api/super-ceo/derived/bundle")
    assert response.status_code == 200
    assert "bundle" in response.json()["data"]


def test_portfolio_health_route_returns_envelope(client):
    response = client.get("/api/super-ceo/portfolio-health")
    assert response.status_code == 200
    assert "data" in response.json()


def test_decision_queue_route_returns_envelope(client):
    response = client.get("/api/super-ceo/decision-queue")
    assert response.status_code == 200
    assert "items" in response.json()["data"]["details"]


def test_strategy_okrs_route_returns_envelope(client):
    response = client.get("/api/super-ceo/strategy/okrs")
    assert response.status_code == 200
    assert response.json()["meta"]["source_status"] == "unavailable"


def test_performance_summary_route_returns_envelope(client):
    response = client.get("/api/super-ceo/performance/summary")
    assert response.status_code == 200
    assert "metrics" in response.json()["data"]


def test_legacy_metric_registry_still_available_and_revenue_trend_registered():
    assert "group_revenue" in METRIC_REGISTRY
    assert "portfolio_health" in METRIC_REGISTRY
    assert "revenue_trend" in METRIC_REGISTRY
