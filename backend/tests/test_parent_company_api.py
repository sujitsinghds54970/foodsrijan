import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Company, User
from app.models.ceo import CeoAuditLog
from app.services.websocket_service import connection_manager
from app.utils.auth_system import auth_guard, require_super_admin


@pytest.fixture()
def parent_context(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[Company.__table__, User.__table__, CeoAuditLog.__table__])
    db = Session(engine, expire_on_commit=False)
    actor = User(
        username="parent_ceo",
        email="parent@example.test",
        hashed_password=auth_guard.hash_password("SafePassword9!"),
        role="super_ceo",
        is_active=True,
        is_super_ceo=True,
        first_name="Sujit",
        last_name="Singh",
        phone="+919876543210",
    )
    db.add(actor)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_super_admin] = lambda: actor
    events = []

    async def capture(event):
        events.append(event)
        return 1

    monkeypatch.setattr(connection_manager, "broadcast_event", capture)
    yield TestClient(app), db, actor, events
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()


def test_get_creates_parent_company(parent_context):
    client, db, _, _ = parent_context
    response = client.get("/api/super-ceo/parent-company")
    assert response.status_code == 200
    assert response.json()["data"]["published"]["name"] == "FoodSrijan Group"
    assert db.query(Company).filter(Company.is_parent.is_(True)).count() == 1


def test_authenticated_websocket_accepts_super_ceo(parent_context):
    client, _, actor, _ = parent_context
    token = auth_guard.create_access_token(
        {"sub": actor.username, "user_id": actor.id, "role": actor.role}
    )
    with client.websocket_connect(f"/ws?token={token}") as websocket:
        websocket.send_json({"type": "ping"})
        assert websocket.receive_json()["type"] == "pong"


def test_multiple_websocket_tabs_remain_connected(parent_context):
    client, _, actor, _ = parent_context
    token = auth_guard.create_access_token(
        {"sub": actor.username, "user_id": actor.id, "role": actor.role}
    )
    with client.websocket_connect(f"/ws?token={token}") as first:
        with client.websocket_connect(f"/ws?token={token}") as second:
            first.send_json({"type": "ping"})
            second.send_json({"type": "ping"})
            assert first.receive_json()["type"] == "pong"
            assert second.receive_json()["type"] == "pong"
        first.send_json({"type": "ping"})
        assert first.receive_json()["type"] == "pong"


def test_websocket_rejects_missing_token(parent_context):
    client, _, _, _ = parent_context
    with pytest.raises(Exception):
        with client.websocket_connect("/ws"):
            pass


def test_get_reuses_existing_foodsrijan_company(parent_context):
    client, db, actor, _ = parent_context
    db.add(Company(name="FoodSrijan Group", slug="foodsrijan-group", created_by=actor.id))
    db.commit()
    client.get("/api/super-ceo/parent-company")
    assert db.query(Company).count() == 1
    assert db.query(Company).one().is_parent is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "FoodSrijan Holdings"),
        ("tagline", "Hospitality, elevated"),
        ("primary_color", "#D6A84F"),
        ("secondary_color", "#7C3AED"),
        ("accent_color", "#14B8A6"),
        ("display_font", "Fraunces"),
        ("body_font", "Manrope"),
        ("sub_domains", ["restaurants", "cloud-kitchens"]),
        ("total_funding_raised", "25000000.00"),
        ("website_url", "https://foodsrijan.example"),
    ],
)
def test_save_draft_fields(parent_context, field, value):
    client, db, _, _ = parent_context
    response = client.put("/api/super-ceo/parent-company", json={field: value})
    assert response.status_code == 200
    assert response.json()["data"]["draft"][field] == value
    assert db.query(CeoAuditLog).filter(CeoAuditLog.action == "parent_company.draft_saved").count() == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"primary_color": "gold"},
        {"website_url": "javascript:alert(1)"},
        {"support_email": "bad"},
        {"support_phone": "123"},
        {"gstin": "bad"},
        {"pan_number": "bad"},
        {"fssai_license": "123"},
        {"ifsc_code": "bad"},
    ],
)
def test_draft_validation_errors(parent_context, payload):
    client, _, _, _ = parent_context
    assert client.put("/api/super-ceo/parent-company", json=payload).status_code == 422


def test_publish_applies_and_clears_draft(parent_context):
    client, db, actor, _ = parent_context
    client.put("/api/super-ceo/parent-company", json={"tagline": "Published identity"})
    response = client.post("/api/super-ceo/parent-company/publish")
    company = db.query(Company).filter(Company.is_parent.is_(True)).one()
    assert response.status_code == 200
    assert company.tagline == "Published identity"
    assert company.profile_draft is None
    assert company.published_by == actor.id


def test_publish_emits_domain_event(parent_context):
    client, _, actor, events = parent_context
    client.put("/api/super-ceo/parent-company", json={"tagline": "Published identity"})
    client.post("/api/super-ceo/parent-company/publish")
    assert events == [
        {
            "event": "parent_company.published",
            "resource": {"company_id": 1},
            "occurred_at": events[0]["occurred_at"],
            "actor": {"user_id": actor.id, "authority": "super_ceo"},
        }
    ]


def test_publish_without_draft_returns_conflict(parent_context):
    client, _, _, _ = parent_context
    client.get("/api/super-ceo/parent-company")
    assert client.post("/api/super-ceo/parent-company/publish").status_code == 409


def test_discard_clears_draft_and_audits(parent_context):
    client, db, _, _ = parent_context
    client.put("/api/super-ceo/parent-company", json={"tagline": "Discard me"})
    response = client.delete("/api/super-ceo/parent-company/draft")
    assert response.status_code == 200
    assert db.query(Company).one().profile_draft is None
    assert db.query(CeoAuditLog).filter(CeoAuditLog.action == "parent_company.draft_discarded").count() == 1


def test_audit_filters_by_changed_field(parent_context):
    client, _, _, _ = parent_context
    client.put("/api/super-ceo/parent-company", json={"tagline": "A"})
    client.put("/api/super-ceo/parent-company", json={"primary_color": "#D6A84F"})
    response = client.get("/api/super-ceo/parent-company/audit?field=tagline")
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/super-ceo/parent-company"),
        ("put", "/api/super-ceo/parent-company"),
        ("post", "/api/super-ceo/parent-company/publish"),
        ("delete", "/api/super-ceo/parent-company/draft"),
        ("get", "/api/super-ceo/parent-company/audit"),
    ],
)
def test_non_super_ceo_is_forbidden(parent_context, method, path):
    client, _, _, _ = parent_context

    def forbidden():
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    app.dependency_overrides[require_super_admin] = forbidden
    kwargs = {"json": {}} if method == "put" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 403
