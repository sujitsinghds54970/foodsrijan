from datetime import datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (
    ActivityLog,
    Branch,
    Brand,
    Company,
    Customer,
    DailyAnalyticsSnapshot,
    Department,
    Permission,
    ProfileMembership,
    ProfileType,
    RateLimitEntry,
    Role,
    StaffEmployee,
    User,
    UserCompany,
    UserRole,
)
from app.models.company_structure import role_permissions
from app.models.authority import RoleAssignment
from app.models.ceo import CeoAuditLog
from app.models.doctor_portal import Order
from app.routes.super_ceo.companies import router
from app.routes.company_ceo import require_company_ceo
from app.utils.auth_system import auth_guard, require_super_admin
from app.utils.validators import validate_password_strength


@pytest.fixture()
def test_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        Company.__table__,
        Department.__table__,
        Brand.__table__,
        Branch.__table__,
        User.__table__,
        Role.__table__,
        Permission.__table__,
        role_permissions,
        UserRole.__table__,
        UserCompany.__table__,
        Customer.__table__,
        StaffEmployee.__table__,
        DailyAnalyticsSnapshot.__table__,
        Order.__table__,
        ProfileType.__table__,
        ProfileMembership.__table__,
        RoleAssignment.__table__,
        CeoAuditLog.__table__,
        RateLimitEntry.__table__,
        ActivityLog.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    session = Session(engine, expire_on_commit=False)
    actor = User(
        username="super_ceo_test",
        email="super.ceo@example.test",
        hashed_password=auth_guard.hash_password("SafeTestPassword9!"),
        role="super_ceo",
        is_active=True,
        is_super_ceo=True,
        is_super_admin=True,
        first_name="Super",
        last_name="CEO",
        phone="+919876543210",
    )
    session.add(actor)
    session.commit()

    def override_db():
        yield session

    def override_super_ceo():
        return session.get(User, actor.id)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_super_admin] = override_super_ceo
    client = TestClient(app)
    yield client, session, actor
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def create_company(client, **values):
    body = {"name": values.pop("name", "Saffron Company"), **values}
    return client.post("/api/super-ceo/companies", json=body)


def create_ceo_payload(**updates):
    return {
        "first_name": "Rajesh",
        "last_name": "Kumar",
        "email": "rajesh.kumar@example.com",
        "phone": "+919876543210",
        "username": "rajesh_kumar",
        "password": "SecureP@ss2026!",
        "password_confirm": "SecureP@ss2026!",
        **updates,
    }


def test_create_company_with_extended_fields(test_context):
    client, _, actor = test_context
    response = create_company(
        client,
        name="Saffron Company",
        legal_name="Saffron Hospitality Pvt Ltd",
        registration_number="REG-100",
        gstin="22AAAAA0000A1Z5",
        pan_number="ABCDE1234F",
        fssai_license="12345678901234",
        website_url="https://saffron.example",
        business_domain="Restaurant",
        funding_stage="Series A",
        operating_regions=["Maharashtra", "Goa"],
        metadata={"source": "test"},
    )
    assert response.status_code == 201, response.text
    company = response.json()["data"]["company"]
    assert company["slug"] == "saffron-company"
    assert company["created_by"] == actor.id
    assert company["status"] == "active"
    assert company["gstin"] == "22AAAAA0000A1Z5"
    assert company["metadata"] == {"source": "test"}


def test_company_name_is_required(test_context):
    client, _, _ = test_context
    assert client.post("/api/super-ceo/companies", json={}).status_code == 422


def test_invalid_gstin_is_rejected(test_context):
    client, _, _ = test_context
    assert create_company(client, gstin="not-a-gstin").status_code == 422


def test_invalid_funding_stage_is_rejected(test_context):
    client, _, _ = test_context
    assert create_company(client, funding_stage="Unknown").status_code == 422


def test_invalid_pan_is_rejected(test_context):
    client, _, _ = test_context
    assert create_company(client, pan_number="BADPAN").status_code == 422


def test_duplicate_slug_returns_conflict(test_context):
    client, _, _ = test_context
    assert create_company(client, name="Company One", slug="same-slug").status_code == 201
    assert create_company(client, name="Company Two", slug="same-slug").status_code == 409


def test_duplicate_gstin_returns_conflict(test_context):
    client, _, _ = test_context
    gstin = "22AAAAA0000A1Z5"
    assert create_company(client, name="Company One", gstin=gstin).status_code == 201
    assert create_company(client, name="Company Two", gstin=gstin).status_code == 409


def test_list_companies_supports_pagination(test_context):
    client, _, _ = test_context
    for name in ("North Foods", "South Foods", "West Foods"):
        assert create_company(client, name=name).status_code == 201
    response = client.get("/api/super-ceo/companies?page=2&page_size=1")
    assert response.status_code == 200
    assert len(response.json()["data"]["companies"]) == 1
    assert response.json()["data"]["total"] == 3


def test_list_companies_filters_status(test_context):
    client, _, _ = test_context
    create_company(client, name="Active Food")
    company_id = client.get("/api/super-ceo/companies").json()["data"]["companies"][0]["id"]
    client.put(f"/api/super-ceo/companies/{company_id}", json={"status": "inactive"})
    response = client.get("/api/super-ceo/companies?status=inactive")
    assert response.status_code == 200
    assert [row["name"] for row in response.json()["data"]["companies"]] == ["Active Food"]


def test_list_companies_filters_business_domain(test_context):
    client, _, _ = test_context
    create_company(client, name="Cafe Co", business_domain="Cafe")
    create_company(client, name="Bakery Co", business_domain="Bakery")
    response = client.get("/api/super-ceo/companies?business_domain=Cafe")
    assert [row["name"] for row in response.json()["data"]["companies"]] == ["Cafe Co"]


def test_list_companies_searches_company_name(test_context):
    client, _, _ = test_context
    create_company(client, name="Urban Spice")
    create_company(client, name="Green Bowl")
    response = client.get("/api/super-ceo/companies?search=spice")
    assert [row["name"] for row in response.json()["data"]["companies"]] == ["Urban Spice"]


def test_company_stats_counts_only_active_company_scope(test_context):
    client, session, _ = test_context
    active_id = create_company(
        client,
        name="Active Portfolio Company",
        number_of_branches=4,
    ).json()["data"]["company"]["id"]
    inactive_id = create_company(
        client,
        name="Inactive Portfolio Company",
        number_of_branches=9,
    ).json()["data"]["company"]["id"]
    client.put(
        f"/api/super-ceo/companies/{inactive_id}",
        json={"status": "inactive"},
    )
    session.add_all(
        [
            User(
                username="active_company_user",
                email="active.user@example.test",
                hashed_password=auth_guard.hash_password("SafeTestPassword9!"),
                role="StaffEmployee",
                is_active=True,
                first_name="Active",
                last_name="User",
                phone="+919876543211",
                company_id=active_id,
            ),
            User(
                username="inactive_company_user",
                email="inactive.user@example.test",
                hashed_password=auth_guard.hash_password("SafeTestPassword9!"),
                role="StaffEmployee",
                is_active=True,
                first_name="Inactive",
                last_name="User",
                phone="+919876543212",
                company_id=inactive_id,
            ),
        ]
    )
    session.commit()

    response = client.get("/api/super-ceo/companies/stats")

    assert response.status_code == 200
    assert response.json()["data"]["stats"] == {
        "active_companies": 1,
        "active_branches": 4,
        "active_users": 1,
        "pending_onboarding": 1,
    }


def test_get_company_by_id(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    response = client.get(f"/api/super-ceo/companies/{company_id}")
    assert response.status_code == 200
    assert response.json()["data"]["company"]["id"] == company_id


def test_get_missing_company_returns_404(test_context):
    client, _, _ = test_context
    assert client.get("/api/super-ceo/companies/999").status_code == 404


def test_update_company_fields(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    response = client.put(f"/api/super-ceo/companies/{company_id}", json={"tagline": "Fresh every day"})
    assert response.status_code == 200
    assert response.json()["data"]["company"]["tagline"] == "Fresh every day"


def test_update_rejects_invalid_url(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    response = client.put(f"/api/super-ceo/companies/{company_id}", json={"website_url": "javascript:alert(1)"})
    assert response.status_code == 422


def test_soft_delete_and_restore_company(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    deleted = client.delete(f"/api/super-ceo/companies/{company_id}?reason=closure")
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True
    assert client.get(f"/api/super-ceo/companies/{company_id}").status_code == 404
    restored = client.post(f"/api/super-ceo/companies/{company_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["data"]["company"]["is_deleted"] is False


def test_company_delete_blocked_by_active_employees(test_context):
    client, db, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    branch = Branch(company_id=company_id, name="Branch One", location="Mumbai", address="A", city="Mumbai", state="MH", pincode="400001", phone="9876543210", email="branch@example.test", branch_code="B001")
    user = User(username="worker", email="worker@example.test", hashed_password="hash", role="staff", first_name="Work", last_name="Person", phone="9876543210", is_active=True)
    db.add_all([branch, user])
    db.flush()
    db.add(StaffEmployee(company_id=company_id, branch_id=branch.id, user_id=user.id, employee_id="E001", department="ops", position="Staff", date_of_joining=datetime.utcnow(), salary=1, date_of_birth=datetime(1990, 1, 1), is_active=True))
    db.commit()
    response = client.delete(f"/api/super-ceo/companies/{company_id}")
    assert response.status_code == 400
    assert response.json()["detail"]["blockers"]["active_employees"] == 1


def test_company_delete_blocked_by_active_customers(test_context):
    client, db, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    branch = Branch(company_id=company_id, name="Branch One", location="Mumbai", address="A", city="Mumbai", state="MH", pincode="400001", phone="9876543210", email="branch@example.test", branch_code="B001")
    db.add(branch)
    db.flush()
    db.add(Customer(company_id=company_id, branch_id=branch.id, patient_id="P001", first_name="A", last_name="B", date_of_birth=datetime(1990, 1, 1), gender="Other", phone="9876543210", address="A", city="Mumbai", state="MH", pincode="400001", emergency_contact="9876543210", emergency_contact_name="B", is_active=True))
    db.commit()
    response = client.delete(f"/api/super-ceo/companies/{company_id}")
    assert response.status_code == 400
    assert response.json()["detail"]["blockers"]["active_customers"] == 1


def test_company_delete_blocked_by_active_branches(test_context):
    client, db, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    db.add(Branch(company_id=company_id, name="Open Branch", location="Mumbai", address="A", city="Mumbai", state="MH", pincode="400001", phone="9876543210", email="branch@example.test", branch_code="B002", is_active=True))
    db.commit()
    response = client.delete(f"/api/super-ceo/companies/{company_id}")
    assert response.status_code == 400
    assert response.json()["detail"]["blockers"]["active_branches"] == 1


def test_company_delete_blocked_by_pending_orders(test_context):
    client, db, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    branch = Branch(company_id=company_id, name="Closed Branch", location="Mumbai", address="A", city="Mumbai", state="MH", pincode="400001", phone="9876543210", email="branch@example.test", branch_code="B003", is_active=False)
    db.add(branch)
    db.flush()
    db.add(Order(doctor_id=1, patient_id=1, branch_id=branch.id, status="Draft"))
    db.commit()
    response = client.delete(f"/api/super-ceo/companies/{company_id}")
    assert response.status_code == 400
    assert response.json()["detail"]["blockers"]["pending_orders"] == 1


def test_company_delete_blocked_by_active_company_ceo(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    ceo = client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload())
    assert ceo.status_code == 201

    response = client.delete(f"/api/super-ceo/companies/{company_id}")

    assert response.status_code == 400
    assert response.json()["detail"]["blockers"]["active_company_ceos"] == 1


def test_sixth_company_creation_is_rate_limited(test_context):
    client, _, _ = test_context
    statuses = [create_company(client, name=f"Limited Company {index}").status_code for index in range(1, 7)]
    assert statuses == [201, 201, 201, 201, 201, 429]


def test_create_company_ceo_bcrypt_hash_role_and_force_change(test_context):
    client, db, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    response = client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload())
    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["ceo"]["is_company_ceo"] is True
    assert body["ceo"]["force_password_change"] is True
    assert body["credentials"]["password"] == "SecureP@ss2026!"
    user = db.query(User).filter_by(username="rajesh_kumar").one()
    assert user.hashed_password.startswith("$2b$12$")
    assert user.hashed_password != body["credentials"]["password"]
    assert db.query(UserRole).filter_by(user_id=user.id, company_id=company_id, is_active=True).count() == 1


def test_weak_company_ceo_password_returns_422(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    payload = create_ceo_payload(password="weak", password_confirm="weak")
    assert client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=payload).status_code == 422


def test_password_over_bcrypt_byte_limit_is_rejected(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    password = "Aa1!" + ("x" * 80)
    payload = create_ceo_payload(password=password, password_confirm=password)
    assert client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=payload).status_code == 422


def test_mismatched_ceo_password_confirmation_returns_422(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    payload = create_ceo_payload(password_confirm="DifferentPassword9!")
    assert client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=payload).status_code == 422


def test_duplicate_ceo_username_returns_409(test_context):
    client, _, _ = test_context
    first_company = create_company(client, name="Company One").json()["data"]["company"]["id"]
    second_company = create_company(client, name="Company Two").json()["data"]["company"]["id"]
    assert client.post(f"/api/super-ceo/companies/{first_company}/ceo", json=create_ceo_payload()).status_code == 201
    payload = create_ceo_payload(email="other@example.com")
    assert client.post(f"/api/super-ceo/companies/{second_company}/ceo", json=payload).status_code == 409


def test_duplicate_ceo_email_returns_409(test_context):
    client, _, _ = test_context
    first_company = create_company(client, name="Company One").json()["data"]["company"]["id"]
    second_company = create_company(client, name="Company Two").json()["data"]["company"]["id"]
    assert client.post(f"/api/super-ceo/companies/{first_company}/ceo", json=create_ceo_payload()).status_code == 201
    payload = create_ceo_payload(username="second_user")
    assert client.post(f"/api/super-ceo/companies/{second_company}/ceo", json=payload).status_code == 409


def test_company_ceo_authenticates_through_real_login_endpoint_and_is_not_super_ceo(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload())
    response = client.post("/api/auth/login", json={"username": "rajesh_kumar", "password": "SecureP@ss2026!"})
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert token
    profile = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["is_company_ceo"] is True
    assert profile.json()["company_id"] == company_id
    app.dependency_overrides.pop(require_super_admin)
    forbidden = client.get("/api/super-ceo/companies", headers={"Authorization": f"Bearer {token}"})
    assert forbidden.status_code == 403


def test_ceo_reset_password_returns_once_and_sets_force_change(test_context):
    client, db, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload())
    response = client.post(f"/api/super-ceo/companies/{company_id}/ceo/reset-password")
    assert response.status_code == 200
    password = response.json()["data"]["credentials"]["password"]
    assert validate_password_strength(password)[0]
    ceo = db.query(User).filter_by(username="rajesh_kumar").one()
    assert ceo.force_password_change is True
    assert auth_guard.verify_password(password, ceo.hashed_password)


def test_remove_ceo_unlinks_company_scope(test_context):
    client, db, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload())
    response = client.delete(f"/api/super-ceo/companies/{company_id}/ceo")
    assert response.status_code == 200
    ceo = db.query(User).filter_by(username="rajesh_kumar").one()
    assert ceo.company_id is None and ceo.is_company_ceo is False


def test_company_ceo_get_and_update_profile(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    created = client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload())
    assert created.status_code == 201
    current = client.get(f"/api/super-ceo/companies/{company_id}/ceo")
    assert current.status_code == 200
    assert current.json()["data"]["ceo"]["username"] == "rajesh_kumar"
    updated = client.put(
        f"/api/super-ceo/companies/{company_id}/ceo",
        json={"first_name": "Raj"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["ceo"]["first_name"] == "Raj"


def test_company_cannot_have_two_active_ceos(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    assert client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload()).status_code == 201
    payload = create_ceo_payload(username="another_ceo", email="another@example.com")
    assert client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=payload).status_code == 409


def test_xss_markup_is_removed_from_text_fields(test_context):
    client, _, _ = test_context
    response = create_company(client, description="<script>alert(1)</script>Family dining")
    assert response.status_code == 201
    assert response.json()["data"]["company"]["description"] == "Family dining"


def test_sql_statement_in_text_is_rejected(test_context):
    client, _, _ = test_context
    response = create_company(client, description="SELECT * FROM users; --")
    assert response.status_code == 422


def test_audit_events_record_mutations_without_credentials(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    client.put(f"/api/super-ceo/companies/{company_id}", json={"tagline": "Changed"})
    client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload())
    events = client.get(f"/api/super-ceo/companies/{company_id}/audit").json()["data"]["events"]
    actions = {event["action"] for event in events}
    assert {"company.created", "company.updated", "ceo.assigned"} <= actions
    assert all("password" not in str(event).lower() for event in events)


def test_company_get_and_list_never_return_ceo_password(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload())
    for response in (client.get(f"/api/super-ceo/companies/{company_id}"), client.get("/api/super-ceo/companies")):
        assert response.status_code == 200
        assert "hashed_password" not in response.text
        assert "SecureP@ss2026!" not in response.text


def test_test_login_checks_credentials_without_returning_password(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload())
    good = client.post(f"/api/super-ceo/companies/{company_id}/ceo/test-login", json={"username": "rajesh_kumar", "password": "SecureP@ss2026!"})
    bad = client.post(f"/api/super-ceo/companies/{company_id}/ceo/test-login", json={"username": "rajesh_kumar", "password": "wrong"})
    assert good.json()["data"]["valid"] is True
    assert bad.json()["data"]["valid"] is False


def test_company_metrics_and_audit_endpoints_are_enveloped(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    metrics = client.get(f"/api/super-ceo/companies/{company_id}/metrics")
    audit = client.get(f"/api/super-ceo/companies/{company_id}/audit")
    assert metrics.status_code == 200 and "meta" in metrics.json()
    assert metrics.json()["data"]["metrics"]["branches"] == 0
    assert audit.status_code == 200 and "events" in audit.json()["data"]
    assert audit.json()["data"]["total"] == 1


def test_company_ceo_workspace_is_scoped_to_assigned_company(test_context):
    client, session, _ = test_context
    company_id = create_company(
        client,
        name="CEO Scoped Company",
        number_of_branches=3,
    ).json()["data"]["company"]["id"]
    other_company_id = create_company(
        client,
        name="Other Company",
        number_of_branches=8,
    ).json()["data"]["company"]["id"]
    ceo = User(
        username="scoped_company_ceo",
        email="scoped.ceo@example.test",
        hashed_password=auth_guard.hash_password("SafeTestPassword9!"),
        role="company_ceo",
        company_id=company_id,
        current_company_id=company_id,
        is_company_ceo=True,
        is_active=True,
        first_name="Scoped",
        last_name="CEO",
        phone="+919876543213",
    )
    session.add(ceo)
    session.flush()
    session.add_all(
        [
            Department(company_id=company_id, name="Operations", is_active=True),
            Department(company_id=other_company_id, name="Hidden Department", is_active=True),
        ]
    )
    session.commit()

    def override_company_ceo():
        return ceo, session.get(Company, company_id)

    app.dependency_overrides[require_company_ceo] = override_company_ceo
    response = client.get(
        "/api/company-ceo/workspace",
        headers={"X-Company-ID": str(other_company_id)},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["company"]["id"] == company_id
    assert data["executive"]["id"] == ceo.id
    assert data["metrics"]["active_users"] == 1
    assert [department["name"] for department in data["departments"]] == ["Operations"]
    assert "hashed_password" not in response.text
    assert response.json()["meta"]["scope"]["company_id"] == company_id


def test_company_ceo_workspace_rejects_non_company_ceo(test_context):
    client, _, _ = test_context

    def deny_company_ceo():
        raise HTTPException(status_code=403, detail="Company CEO access required")

    app.dependency_overrides[require_company_ceo] = deny_company_ceo
    response = client.get("/api/company-ceo/workspace")

    assert response.status_code == 403


def test_company_audit_supports_action_filter_and_pagination(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    client.put(
        f"/api/super-ceo/companies/{company_id}",
        json={"tagline": "Changed once"},
    )
    client.put(
        f"/api/super-ceo/companies/{company_id}",
        json={"tagline": "Changed twice"},
    )

    response = client.get(
        f"/api/super-ceo/companies/{company_id}/audit",
        params={"action": "company.updated", "page": 2, "page_size": 1},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert data["page"] == 2
    assert data["page_size"] == 1
    assert len(data["events"]) == 1
    assert data["events"][0]["action"] == "company.updated"


def test_non_super_ceo_dependency_is_forbidden(test_context):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]

    def deny_non_super_ceo():
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    app.dependency_overrides[require_super_admin] = deny_non_super_ceo
    response = client.get("/api/super-ceo/companies")
    ceo_response = client.post(
        f"/api/super-ceo/companies/{company_id}/ceo",
        json=create_ceo_payload(),
    )
    assert response.status_code == 403
    assert ceo_response.status_code == 403


def test_active_attempts_and_blocked_attempts_are_persistently_logged(test_context):
    client, db, actor = test_context
    statuses = [create_company(client, name=f"Rate Company {index}").status_code for index in range(1, 7)]
    entries = db.query(RateLimitEntry).filter_by(actor_id=actor.id, action="create_company").all()
    assert statuses[-1] == 429
    assert len(entries) == 6
    assert sum(entry.was_allowed for entry in entries) == 5


def test_ceo_assignment_rate_limit_blocks_eleventh_attempt(test_context):
    client, db, _ = test_context
    companies = [Company(name=f"CEO Limit {index}", slug=f"ceo-limit-{index}") for index in range(11)]
    db.add_all(companies)
    db.commit()
    statuses = []
    for index, company in enumerate(companies):
        payload = create_ceo_payload(
            username=f"ceo_{index:02d}",
            email=f"ceo{index:02d}@example.com",
        )
        statuses.append(client.post(f"/api/super-ceo/companies/{company.id}/ceo", json=payload).status_code)
    assert statuses == [201] * 10 + [429]


def test_credentials_are_not_written_to_company_audit_or_app_logs(test_context, caplog):
    client, _, _ = test_context
    company_id = create_company(client).json()["data"]["company"]["id"]
    response = client.post(f"/api/super-ceo/companies/{company_id}/ceo", json=create_ceo_payload())
    assert response.status_code == 201
    assert "SecureP@ss2026!" not in caplog.text
    events = client.get(f"/api/super-ceo/companies/{company_id}/audit").json()["data"]["events"]
    assert "SecureP@ss2026!" not in str(events)
