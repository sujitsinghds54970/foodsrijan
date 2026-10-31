"""Outlet Management backend tests (Parts 2-5 + real-time domain events).

Every test constructs an isolated in-memory SQLite database (StaticPool) and
mounts the real FastAPI app, so requests exercise the actual guards, schema
validation, service layer, audit logging, and rate limiting - not mocks.
"""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (
    ActivityLog,
    Brand,
    Branch,
    Company,
    Customer,
    DailyAnalyticsSnapshot,
    LoginAttempt,
    ProfileMembership,
    ProfileType,
    RateLimitEntry,
    Role,
    StaffEmployee,
    StaffProfile,
    User,
    UserCompany,
    UserRole,
)
from app.models.branch_lis import OrderQueue
from app.models.authority import RoleAssignment
from app.models.ceo import CeoAuditLog
from app.models.daily_entry_module import DailyEntryModule
from app.models.doctor_portal import Order
from app.models.hr import StaffAttendanceLog, StaffTask
from app.models.inventory import InventoryItemV2, Supplier
from app.models.patient_portal import CustomerFeedback, CustomerPortalUser
from app.services.rate_limit import RATE_LIMITS
from app.services.token_revocation import reset_state as reset_token_revocations
from app.utils.auth_system import auth_guard


def _token(user: User) -> str:
    return auth_guard.create_access_token(
        {"sub": user.username, "user_id": user.id, "role": user.role}
    )


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


VALID_OUTLET_PAYLOAD = {
    # gstin is intentionally omitted here: Branch.gstin carries a *global*
    # unique index (pre-existing legacy constraint), so tests that create
    # several outlets reuse this base payload and must not collide on it.
    # Dedicated gstin-uniqueness coverage supplies its own explicit value.
    "name": "Downtown Diner",
    "code": "DTD001",
    "outlet_type": "dine_in",
    "status": "active",
    "address_line_1": "12 MG Road",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411001",
    "fssai_license": "12345678901234",
    "ifsc_code": "HDFC0001234",
    "bank_account_number": "123456789012",
    "upi_id": "outlet@okhdfc",
    "outlet_email": "downtown@example.com",
    "outlet_phone": "9876543210",
}

VALID_MANAGER_PAYLOAD = {
    "first_name": "Asha",
    "last_name": "Rao",
    "email": "asha.manager@example.com",
    "phone": "9876500001",
}


@pytest.fixture()
def ctx(monkeypatch):
    reset_token_revocations()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__,
            Brand.__table__,
            Role.__table__,
            UserRole.__table__,
            UserCompany.__table__,
            RateLimitEntry.__table__,
            Branch.__table__,
            User.__table__,
            ProfileMembership.__table__,
            ProfileType.__table__,
            StaffEmployee.__table__,
            StaffProfile.__table__,
            DailyAnalyticsSnapshot.__table__,
            LoginAttempt.__table__,
            CeoAuditLog.__table__,
            ActivityLog.__table__,
            Order.__table__,
            Customer.__table__,
            CustomerPortalUser.__table__,
            CustomerFeedback.__table__,
            DailyEntryModule.__table__,
            Supplier.__table__,
            InventoryItemV2.__table__,
            StaffAttendanceLog.__table__,
            StaffTask.__table__,
            OrderQueue.__table__,
            RoleAssignment.__table__,
        ],
    )
    db = Session(engine, expire_on_commit=False)
    monkeypatch.setattr("app.main.SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))

    company_a = Company(name="Srijan Foods A", slug="srijan-foods-a", is_active=True)
    company_b = Company(name="Srijan Foods B", slug="srijan-foods-b", is_active=True)
    db.add_all([company_a, company_b])
    db.flush()

    ceo_a = User(
        username="ceo_alpha", email="ceo.alpha@example.com",
        hashed_password=auth_guard.hash_password("CeoAlphaPass9!"),
        role="company_ceo", is_company_ceo=True, is_active=True,
        company_id=company_a.id, current_company_id=company_a.id,
        first_name="Alpha", last_name="Ceo", phone="9000000001",
    )
    ceo_b = User(
        username="ceo_beta", email="ceo.beta@example.com",
        hashed_password=auth_guard.hash_password("CeoBetaPass9!"),
        role="company_ceo", is_company_ceo=True, is_active=True,
        company_id=company_b.id, current_company_id=company_b.id,
        first_name="Beta", last_name="Ceo", phone="9000000002",
    )
    plain_staff = User(
        username="plain_staffer", email="plain.staffer@example.com",
        hashed_password=auth_guard.hash_password("PlainStaffPass9!"),
        role="StaffEmployee", is_active=True,
        company_id=company_a.id, current_company_id=company_a.id,
        first_name="Plain", last_name="Staffer", phone="9000000003",
    )
    db.add_all([ceo_a, ceo_b, plain_staff])
    db.commit()

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    yield {
        "client": client,
        "db": db,
        "company_a": company_a,
        "company_b": company_b,
        "ceo_a": ceo_a,
        "ceo_b": ceo_b,
        "plain_staff": plain_staff,
    }
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()


def _create_outlet(client, ceo, payload=None, **overrides):
    body = {**VALID_OUTLET_PAYLOAD, **(payload or {}), **overrides}
    return client.post("/api/company-ceo/outlets", json=body, headers=_auth(ceo))


def _create_manager(client, ceo, outlet_id, payload=None, **overrides):
    body = {**VALID_MANAGER_PAYLOAD, **(payload or {}), **overrides}
    return client.post(f"/api/company-ceo/outlets/{outlet_id}/manager", json=body, headers=_auth(ceo))


# ---------------------------------------------------------------------------
# 1. Outlet CRUD (Company CEO scope)
# ---------------------------------------------------------------------------

def test_ceo_can_create_outlet(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"])
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["outlet"]["name"] == "Downtown Diner"
    assert data["outlet"]["code"] == "DTD001"
    assert data["outlet"]["company_id"] == ctx["company_a"].id


def test_outlet_create_rejects_missing_required_fields(ctx):
    response = ctx["client"].post(
        "/api/company-ceo/outlets",
        json={"name": "No Code Outlet"},
        headers=_auth(ctx["ceo_a"]),
    )
    assert response.status_code == 422


def test_outlet_create_rejects_invalid_gstin(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"], gstin="INVALIDGSTIN")
    assert response.status_code == 422


def test_outlet_create_rejects_invalid_fssai(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"], fssai_license="123")
    assert response.status_code == 422


def test_outlet_create_rejects_invalid_email(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"], outlet_email="not-an-email")
    assert response.status_code == 422


def test_outlet_create_rejects_unsafe_media_url(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"], logo_url="javascript:alert(1)")
    assert response.status_code == 422


def test_outlet_create_duplicate_code_same_company_rejected(ctx):
    first = _create_outlet(ctx["client"], ctx["ceo_a"])
    assert first.status_code == 201
    second = _create_outlet(ctx["client"], ctx["ceo_a"], name="Second Outlet")
    assert second.status_code == 409


def test_outlet_create_same_code_different_company_allowed(ctx):
    # Outlet "code" uniqueness is scoped per company. "name" remains globally
    # unique on the legacy Branch table, so use distinct names here.
    first = _create_outlet(ctx["client"], ctx["ceo_a"])
    assert first.status_code == 201
    second = _create_outlet(ctx["client"], ctx["ceo_b"], name="Company B Diner")
    assert second.status_code == 201, second.text


def test_outlet_list_scoped_to_company(ctx):
    _create_outlet(ctx["client"], ctx["ceo_a"])
    _create_outlet(ctx["client"], ctx["ceo_b"], name="Company B Diner", code="CBD001")
    response = ctx["client"].get("/api/company-ceo/outlets", headers=_auth(ctx["ceo_a"]))
    assert response.status_code == 200
    outlets = response.json()["data"]["outlets"]
    assert len(outlets) == 1
    assert outlets[0]["company_id"] == ctx["company_a"].id


def test_outlet_list_search_and_filter(ctx):
    _create_outlet(ctx["client"], ctx["ceo_a"], name="Riverside Cafe", code="RIV001")
    _create_outlet(ctx["client"], ctx["ceo_a"], name="Downtown Diner", code="DTD001")
    response = ctx["client"].get(
        "/api/company-ceo/outlets", params={"search": "riverside"}, headers=_auth(ctx["ceo_a"])
    )
    assert response.status_code == 200
    outlets = response.json()["data"]["outlets"]
    assert len(outlets) == 1
    assert outlets[0]["name"] == "Riverside Cafe"


def test_outlet_get_by_id_scoped(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = ctx["client"].get(f"/api/company-ceo/outlets/{created['id']}", headers=_auth(ctx["ceo_a"]))
    assert response.status_code == 200
    assert response.json()["data"]["outlet"]["id"] == created["id"]


def test_outlet_get_foreign_company_returns_404_not_403(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = ctx["client"].get(f"/api/company-ceo/outlets/{created['id']}", headers=_auth(ctx["ceo_b"]))
    assert response.status_code == 404


def test_outlet_update_fields(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = ctx["client"].put(
        f"/api/company-ceo/outlets/{created['id']}",
        json={"description": "Updated description", "seating_capacity": 42},
        headers=_auth(ctx["ceo_a"]),
    )
    assert response.status_code == 200, response.text
    outlet = response.json()["data"]["outlet"]
    assert outlet["description"] == "Updated description"
    assert outlet["seating_capacity"] == 42


def test_outlet_update_foreign_company_returns_404(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = ctx["client"].put(
        f"/api/company-ceo/outlets/{created['id']}",
        json={"description": "Hijack attempt"},
        headers=_auth(ctx["ceo_b"]),
    )
    assert response.status_code == 404


def test_outlet_update_requires_at_least_one_field(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = ctx["client"].put(
        f"/api/company-ceo/outlets/{created['id']}", json={}, headers=_auth(ctx["ceo_a"])
    )
    assert response.status_code == 422


def test_outlet_update_rejects_client_supplied_company_id(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = ctx["client"].put(
        f"/api/company-ceo/outlets/{created['id']}",
        json={"company_id": ctx["company_b"].id, "description": "Trying to move tenants"},
        headers=_auth(ctx["ceo_a"]),
    )
    assert response.status_code == 200, response.text
    # company_id is silently ignored (extra="ignore"); the outlet stays with its own company.
    assert response.json()["data"]["outlet"]["company_id"] == ctx["company_a"].id


def test_outlet_soft_delete_and_restore(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    delete_response = ctx["client"].delete(f"/api/company-ceo/outlets/{created['id']}", headers=_auth(ctx["ceo_a"]))
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["data"]["deleted"] is True

    listing = ctx["client"].get("/api/company-ceo/outlets", headers=_auth(ctx["ceo_a"])).json()["data"]["outlets"]
    assert listing == []

    restore_response = ctx["client"].post(
        f"/api/company-ceo/outlets/{created['id']}/restore", headers=_auth(ctx["ceo_a"])
    )
    assert restore_response.status_code == 200, restore_response.text
    assert restore_response.json()["data"]["outlet"]["is_deleted"] is False


def test_outlet_delete_blocked_by_active_manager_staff(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager_response = _create_manager(ctx["client"], ctx["ceo_a"], created["id"])
    assert manager_response.status_code == 201, manager_response.text
    # An assigned outlet manager does not itself block delete (only StaffEmployee/StaffProfile/plain
    # staff users count toward "active_staff"); add a plain staff user assigned to the branch instead.
    db = ctx["db"]
    staff = User(
        username="branch_staffer", email="branch.staffer@example.com",
        hashed_password=auth_guard.hash_password("BranchStaffPass9!"),
        role="StaffEmployee", is_active=True,
        company_id=ctx["company_a"].id, branch_id=created["id"],
        first_name="Branch", last_name="Staffer", phone="9000000099",
    )
    db.add(staff)
    db.commit()
    response = ctx["client"].delete(f"/api/company-ceo/outlets/{created['id']}", headers=_auth(ctx["ceo_a"]))
    assert response.status_code == 400
    assert "blockers" in response.json()["detail"]


def test_outlet_stats_endpoint(ctx):
    _create_outlet(ctx["client"], ctx["ceo_a"])
    response = ctx["client"].get("/api/company-ceo/outlets/stats", headers=_auth(ctx["ceo_a"]))
    assert response.status_code == 200, response.text
    stats = response.json()["data"]["stats"]
    assert stats["total_outlets"] == 1


def test_outlet_audit_log_records_creation(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = ctx["client"].get(f"/api/company-ceo/outlets/{created['id']}/audit", headers=_auth(ctx["ceo_a"]))
    assert response.status_code == 200
    events = response.json()["data"]["events"]
    assert any(event["action"] == "outlet.created" for event in events)


def test_outlet_audit_log_scoped_to_company(ctx):
    created_a = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = ctx["client"].get(f"/api/company-ceo/outlets/{created_a['id']}/audit", headers=_auth(ctx["ceo_b"]))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 2. Manager lifecycle (Company CEO scope)
# ---------------------------------------------------------------------------

def test_ceo_can_create_outlet_manager(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = _create_manager(ctx["client"], ctx["ceo_a"], created["id"])
    assert response.status_code == 201, response.text
    payload = response.json()["data"]
    assert payload["manager"]["email"] == VALID_MANAGER_PAYLOAD["email"]
    assert payload["credentials"]["username"]
    assert payload["credentials"]["password"]


def test_manager_create_rejects_duplicate_active_manager_without_replace(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    first = _create_manager(ctx["client"], ctx["ceo_a"], created["id"])
    assert first.status_code == 201
    second = _create_manager(ctx["client"], ctx["ceo_a"], created["id"], {"email": "second.manager@example.com"})
    assert second.status_code == 409


def test_manager_create_replace_existing_unassigns_previous(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    first = _create_manager(ctx["client"], ctx["ceo_a"], created["id"]).json()["data"]["manager"]
    second = _create_manager(
        ctx["client"], ctx["ceo_a"], created["id"],
        {"email": "second.manager@example.com", "replace_existing": True},
    )
    assert second.status_code == 201, second.text
    db = ctx["db"]
    db.expire_all()
    old_user = db.query(User).filter(User.id == first["id"]).first()
    assert old_user.is_outlet_manager is False
    assert old_user.outlet_id is None
    assert old_user.is_active is False


def test_manager_create_rejects_duplicate_email(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    _create_manager(ctx["client"], ctx["ceo_a"], created["id"])
    second_outlet = _create_outlet(ctx["client"], ctx["ceo_a"], name="Second Outlet", code="SEC001").json()["data"]["outlet"]
    response = _create_manager(ctx["client"], ctx["ceo_a"], second_outlet["id"])
    assert response.status_code == 409


def test_manager_create_rejects_weak_password(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = _create_manager(ctx["client"], ctx["ceo_a"], created["id"], {"password": "weak"})
    assert response.status_code == 422


def test_manager_password_hash_uses_bcrypt_12_rounds(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    _create_manager(ctx["client"], ctx["ceo_a"], created["id"])
    db = ctx["db"]
    db.expire_all()
    manager = db.query(User).filter(User.outlet_id == created["id"], User.is_outlet_manager.is_(True)).first()
    assert manager.hashed_password.startswith("$2b$12$")


def test_manager_get_scoped_to_company(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    _create_manager(ctx["client"], ctx["ceo_a"], created["id"])
    response = ctx["client"].get(f"/api/company-ceo/outlets/{created['id']}/manager", headers=_auth(ctx["ceo_b"]))
    assert response.status_code == 404


def test_manager_update_fields(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    _create_manager(ctx["client"], ctx["ceo_a"], created["id"])
    response = ctx["client"].put(
        f"/api/company-ceo/outlets/{created['id']}/manager",
        json={"phone": "9876500002"},
        headers=_auth(ctx["ceo_a"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["manager"]["phone"] == "9876500002"


def test_manager_reset_password_returns_new_credentials(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager = _create_manager(ctx["client"], ctx["ceo_a"], created["id"]).json()["data"]
    response = ctx["client"].post(
        f"/api/company-ceo/outlets/{created['id']}/manager/reset-password", headers=_auth(ctx["ceo_a"])
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["credentials"]["password"] != manager["credentials"]["password"]


def test_manager_remove_unassigns_and_deactivates(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager = _create_manager(ctx["client"], ctx["ceo_a"], created["id"]).json()["data"]["manager"]
    response = ctx["client"].delete(f"/api/company-ceo/outlets/{created['id']}/manager", headers=_auth(ctx["ceo_a"]))
    assert response.status_code == 200, response.text
    db = ctx["db"]
    db.expire_all()
    removed = db.query(User).filter(User.id == manager["id"]).first()
    assert removed.is_active is False
    assert removed.outlet_id is None


def test_manager_test_login_valid_credentials(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    creds = _create_manager(ctx["client"], ctx["ceo_a"], created["id"]).json()["data"]["credentials"]
    response = ctx["client"].post(
        f"/api/company-ceo/outlets/{created['id']}/manager/test-login",
        json={"username": creds["username"], "password": creds["password"]},
        headers=_auth(ctx["ceo_a"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["valid"] is True


def test_manager_test_login_invalid_credentials(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    creds = _create_manager(ctx["client"], ctx["ceo_a"], created["id"]).json()["data"]["credentials"]
    response = ctx["client"].post(
        f"/api/company-ceo/outlets/{created['id']}/manager/test-login",
        json={"username": creds["username"], "password": "WrongPassword123!"},
        headers=_auth(ctx["ceo_a"]),
    )
    assert response.status_code == 200
    assert response.json()["data"]["valid"] is False


# ---------------------------------------------------------------------------
# 3. Manager self-service scope
# ---------------------------------------------------------------------------

def _login_manager(ctx, created_outlet, ceo=None):
    creds = _create_manager(ctx["client"], ceo or ctx["ceo_a"], created_outlet["id"]).json()["data"]["credentials"]
    db = ctx["db"]
    db.expire_all()
    manager = db.query(User).filter(User.username == creds["username"]).first()
    return manager, creds


def _create_named_manager(ctx, ceo, outlet_id, *, first_name, last_name, email, phone):
    response = _create_manager(
        ctx["client"],
        ceo,
        outlet_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
    )
    assert response.status_code == 201, response.text
    username = response.json()["data"]["credentials"]["username"]
    ctx["db"].expire_all()
    return ctx["db"].query(User).filter(User.username == username).first()


def _seed_manager_dashboard_data(ctx):
    outlet_a = _create_outlet(
        ctx["client"],
        ctx["ceo_a"],
        name="Dashboard Alpha Outlet",
        code="DAO001",
        outlet_email="alpha.outlet@example.com",
        outlet_phone="9876543201",
    ).json()["data"]["outlet"]
    outlet_b = _create_outlet(
        ctx["client"],
        ctx["ceo_a"],
        name="Dashboard Beta Outlet",
        code="DBO001",
        outlet_email="beta.outlet@example.com",
        outlet_phone="9876543202",
    ).json()["data"]["outlet"]

    manager_a = _create_named_manager(
        ctx,
        ctx["ceo_a"],
        outlet_a["id"],
        first_name="Alpha",
        last_name="Manager",
        email="alpha.manager@example.com",
        phone="9876500011",
    )
    manager_b = _create_named_manager(
        ctx,
        ctx["ceo_a"],
        outlet_b["id"],
        first_name="Beta",
        last_name="Manager",
        email="beta.manager@example.com",
        phone="9876500012",
    )

    db = ctx["db"]
    now = datetime.utcnow()
    today_start = datetime.combine(date.today(), datetime.min.time())

    staff_user_a = User(
        username="dashboard_staff_a",
        email="dashboard.staff.a@example.com",
        hashed_password=auth_guard.hash_password("DashboardStaffPass9!"),
        role="StaffEmployee",
        is_active=True,
        company_id=ctx["company_a"].id,
        current_company_id=ctx["company_a"].id,
        branch_id=outlet_a["id"],
        first_name="Shift",
        last_name="Alpha",
        phone="9000001001",
    )
    staff_user_b = User(
        username="dashboard_staff_b",
        email="dashboard.staff.b@example.com",
        hashed_password=auth_guard.hash_password("DashboardStaffPass9!"),
        role="StaffEmployee",
        is_active=True,
        company_id=ctx["company_a"].id,
        current_company_id=ctx["company_a"].id,
        branch_id=outlet_b["id"],
        first_name="Shift",
        last_name="Beta",
        phone="9000001002",
    )
    db.add_all([staff_user_a, staff_user_b])
    db.flush()

    staff_profile_a = StaffProfile(
        user_id=staff_user_a.id,
        branch_id=outlet_a["id"],
        created_by=ctx["ceo_a"].id,
        staff_employee_id="STAFF-A-001",
        department="Kitchen",
        specialization="Line Cook",
        shift_timings="09:00-18:00",
        is_active=True,
    )
    staff_profile_b = StaffProfile(
        user_id=staff_user_b.id,
        branch_id=outlet_b["id"],
        created_by=ctx["ceo_a"].id,
        staff_employee_id="STAFF-B-001",
        department="Service",
        specialization="Dispatch",
        shift_timings="10:00-19:00",
        is_active=True,
    )
    db.add_all([staff_profile_a, staff_profile_b])
    db.flush()

    db.add_all(
        [
            StaffAttendanceLog(
                StaffEmployee_profile_id=staff_profile_a.id,
                branch_id=outlet_a["id"],
                attendance_date=today_start,
                clock_in_time=now - timedelta(hours=2),
                status="present",
                work_mode="onsite",
                task="Kitchen opening prep",
            ),
            StaffAttendanceLog(
                StaffEmployee_profile_id=staff_profile_b.id,
                branch_id=outlet_b["id"],
                attendance_date=today_start,
                clock_in_time=now - timedelta(hours=1, minutes=30),
                status="present",
                work_mode="onsite",
                task="Dispatch board",
            ),
        ]
    )

    entry_a1 = DailyEntryModule(
        branch_id=outlet_a["id"],
        auto_patient_id="PAT-ALPHA-001",
        auto_entry_datetime=now - timedelta(hours=3),
        patient_name="Alpha Customer One",
        age="29",
        mobile="9990000001",
        address="Alpha Street",
        test_name="Combo Meal",
        fee_amount=120,
        total_amount=120,
        payment_method="Cash",
        created_by=manager_a.id,
    )
    entry_a2 = DailyEntryModule(
        branch_id=outlet_a["id"],
        auto_patient_id="PAT-ALPHA-002",
        auto_entry_datetime=now - timedelta(hours=1),
        patient_name="Alpha Customer Two",
        age="35",
        mobile="9990000002",
        address="Alpha Street",
        test_name="Family Meal",
        fee_amount=80,
        total_amount=80,
        payment_method="UPI",
        created_by=manager_a.id,
    )
    entry_b = DailyEntryModule(
        branch_id=outlet_b["id"],
        auto_patient_id="PAT-BETA-001",
        auto_entry_datetime=now - timedelta(hours=2),
        patient_name="Beta Customer",
        age="31",
        mobile="9990000003",
        address="Beta Street",
        test_name="Outlet B Order",
        fee_amount=450,
        total_amount=450,
        payment_method="Card",
        created_by=manager_b.id,
    )
    db.add_all([entry_a1, entry_a2, entry_b])
    db.flush()

    customer_a = Customer(
        company_id=ctx["company_a"].id,
        branch_id=outlet_a["id"],
        patient_id="CUS-ALPHA-001",
        first_name="Alpha",
        last_name="Guest",
        date_of_birth=now - timedelta(days=365 * 30),
        gender="Other",
        phone="8000000001",
        email="alpha.guest@example.com",
        address="Alpha Locality",
        city="Pune",
        state="Maharashtra",
        pincode="411001",
        emergency_contact="8000000009",
        emergency_contact_name="Alpha Emergency",
    )
    customer_b = Customer(
        company_id=ctx["company_a"].id,
        branch_id=outlet_b["id"],
        patient_id="CUS-BETA-001",
        first_name="Beta",
        last_name="Guest",
        date_of_birth=now - timedelta(days=365 * 28),
        gender="Other",
        phone="8000000002",
        email="beta.guest@example.com",
        address="Beta Locality",
        city="Pune",
        state="Maharashtra",
        pincode="411001",
        emergency_contact="8000000010",
        emergency_contact_name="Beta Emergency",
    )
    db.add_all([customer_a, customer_b])
    db.flush()

    db.add_all(
        [
            CustomerFeedback(
                patient_id=customer_a.id,
                rating=4,
                comments="Fast service",
                created_at=now - timedelta(days=2),
            ),
            CustomerFeedback(
                patient_id=customer_a.id,
                rating=5,
                comments="Great food",
                is_resolved=True,
                resolved_at=now - timedelta(days=1),
                created_at=now - timedelta(days=1),
            ),
            CustomerFeedback(
                patient_id=customer_b.id,
                rating=1,
                comments="Outlet B issue",
                created_at=now - timedelta(days=1),
            ),
        ]
    )

    db.add_all(
        [
            InventoryItemV2(
                branch_id=outlet_a["id"],
                department="Kitchen",
                item_name="Rice",
                category="Staples",
                current_qty=12,
                min_threshold=5,
                expiry_date=date.today() + timedelta(days=90),
                unit_cost=50,
                unit="kg",
                created_by=manager_a.id,
            ),
            InventoryItemV2(
                branch_id=outlet_a["id"],
                department="Kitchen",
                item_name="Oil",
                category="Staples",
                current_qty=2,
                min_threshold=5,
                expiry_date=date.today() + timedelta(days=45),
                unit_cost=100,
                unit="ltr",
                created_by=manager_a.id,
            ),
            InventoryItemV2(
                branch_id=outlet_a["id"],
                department="Kitchen",
                item_name="Milk",
                category="Dairy",
                current_qty=6,
                min_threshold=2,
                expiry_date=date.today() + timedelta(days=7),
                unit_cost=40,
                unit="ltr",
                created_by=manager_a.id,
            ),
            InventoryItemV2(
                branch_id=outlet_b["id"],
                department="Kitchen",
                item_name="Outlet B Stock",
                category="Staples",
                current_qty=1,
                min_threshold=5,
                expiry_date=date.today() + timedelta(days=5),
                unit_cost=25,
                unit="kg",
                created_by=manager_b.id,
            ),
        ]
    )

    db.add_all(
        [
            StaffTask(
                StaffEmployee_profile_id=staff_profile_a.id,
                branch_id=outlet_a["id"],
                assigned_by=ctx["ceo_a"].id,
                assigned_to=staff_user_a.id,
                task_name="Alpha task",
                title="Alpha task",
                description="Check prep station",
                due_date=now + timedelta(hours=4),
                status="Pending",
                priority="High",
            ),
            StaffTask(
                StaffEmployee_profile_id=staff_profile_b.id,
                branch_id=outlet_b["id"],
                assigned_by=ctx["ceo_a"].id,
                assigned_to=staff_user_b.id,
                task_name="Beta task",
                title="Beta task",
                description="Beta dispatch",
                due_date=now + timedelta(hours=4),
                status="Pending",
                priority="High",
            ),
        ]
    )

    db.add_all(
        [
            OrderQueue(
                branch_id=outlet_a["id"],
                daily_entry_id=entry_a1.id,
                source="dashboard-test",
                order_number="ALPHA-ORD-001",
                patient_name="Alpha Customer One",
                patient_code="AC1",
                doctor_name="Outlet A Kitchen",
                priority="Routine",
                status="Registered",
                expected_tat_minutes=30,
                created_by=manager_a.id,
            ),
            OrderQueue(
                branch_id=outlet_a["id"],
                daily_entry_id=entry_a2.id,
                source="dashboard-test",
                order_number="ALPHA-ORD-002",
                patient_name="Alpha Customer Two",
                patient_code="AC2",
                doctor_name="Outlet A Kitchen",
                priority="Urgent",
                status="In Processing",
                expected_tat_minutes=15,
                created_by=manager_a.id,
            ),
            OrderQueue(
                branch_id=outlet_b["id"],
                daily_entry_id=entry_b.id,
                source="dashboard-test",
                order_number="BETA-ORD-001",
                patient_name="Beta Customer",
                patient_code="BC1",
                doctor_name="Outlet B Kitchen",
                priority="Routine",
                status="Ordered",
                expected_tat_minutes=20,
                created_by=manager_b.id,
            ),
        ]
    )

    db.add_all(
        [
            CeoAuditLog(
                user_id=manager_a.id,
                action="dashboard.alpha_viewed",
                http_method="GET",
                endpoint="/api/manager/dashboard/kpis",
                response_status=200,
                request_meta={
                    "actor_role": "outlet_manager",
                    "resource_type": "dashboard",
                    "resource_id": outlet_a["id"],
                    "company_id": ctx["company_a"].id,
                    "outlet_id": outlet_a["id"],
                    "changes": {},
                    "metadata": {"test": "alpha"},
                },
                previous_signature=None,
                signature="dashboard-alpha-sig-1",
                created_at=now - timedelta(minutes=5),
            ),
            CeoAuditLog(
                user_id=manager_b.id,
                action="dashboard.beta_viewed",
                http_method="GET",
                endpoint="/api/manager/dashboard/kpis",
                response_status=200,
                request_meta={
                    "actor_role": "outlet_manager",
                    "resource_type": "dashboard",
                    "resource_id": outlet_b["id"],
                    "company_id": ctx["company_a"].id,
                    "outlet_id": outlet_b["id"],
                    "changes": {},
                    "metadata": {"test": "beta"},
                },
                previous_signature=None,
                signature="dashboard-beta-sig-1",
                created_at=now - timedelta(minutes=4),
            ),
        ]
    )
    db.commit()
    return {
        "outlet_a": outlet_a,
        "outlet_b": outlet_b,
        "manager_a": manager_a,
        "manager_b": manager_b,
    }


def test_manager_can_view_own_profile(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    response = ctx["client"].get("/api/manager/me", headers=_auth(manager))
    assert response.status_code == 200, response.text
    assert response.json()["data"]["manager"]["email"] == VALID_MANAGER_PAYLOAD["email"]


def test_manager_self_update_rejects_scope_fields(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    response = ctx["client"].put(
        "/api/manager/me",
        json={"company_id": ctx["company_b"].id, "outlet_id": 99999},
        headers=_auth(manager),
    )
    assert response.status_code == 422


def test_manager_self_update_allows_own_fields(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    response = ctx["client"].put(
        "/api/manager/me", json={"bio": "Loves great food"}, headers=_auth(manager)
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["manager"]["bio"] == "Loves great food"


def test_manager_cannot_access_other_outlet_endpoints(ctx):
    created_a = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager_a, _ = _login_manager(ctx, created_a)
    # Manager A trying to hit CEO-only outlet endpoints must be forbidden.
    response = ctx["client"].get("/api/company-ceo/outlets", headers=_auth(manager_a))
    assert response.status_code == 403


def test_plain_staff_cannot_access_ceo_outlet_endpoints(ctx):
    response = ctx["client"].get("/api/company-ceo/outlets", headers=_auth(ctx["plain_staff"]))
    assert response.status_code == 403


def test_plain_staff_cannot_access_manager_endpoints(ctx):
    response = ctx["client"].get("/api/manager/me", headers=_auth(ctx["plain_staff"]))
    assert response.status_code == 403


def test_manager_can_view_own_outlet(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    response = ctx["client"].get("/api/manager/outlet", headers=_auth(manager))
    assert response.status_code == 200
    assert response.json()["data"]["outlet"]["id"] == created["id"]


def test_manager_outlet_view_hides_financial_fields(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    response = ctx["client"].get("/api/manager/outlet", headers=_auth(manager))
    outlet = response.json()["data"]["outlet"]
    assert "bank_account_number" not in outlet
    assert "rent_amount" not in outlet


def test_manager_can_update_operational_outlet_fields(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    response = ctx["client"].put(
        "/api/manager/outlet", json={"seating_capacity": 55}, headers=_auth(manager)
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["outlet"]["seating_capacity"] == 55


def test_manager_cannot_update_financial_outlet_fields(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    response = ctx["client"].put(
        "/api/manager/outlet", json={"rent_amount": 99999}, headers=_auth(manager)
    )
    assert response.status_code == 422


def test_manager_stats_endpoint(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    response = ctx["client"].get("/api/manager/me/stats", headers=_auth(manager))
    assert response.status_code == 200, response.text
    assert response.json()["data"]["stats"]["outlet_id"] == created["id"]


@pytest.mark.parametrize(
    ("path", "root_key"),
    [
        ("/api/manager/dashboard/kpis", "kpis"),
        ("/api/manager/dashboard/live-orders", "live_orders"),
        ("/api/manager/dashboard/staff-on-shift", "staff"),
        ("/api/manager/dashboard/activity", "events"),
        ("/api/manager/dashboard/health", "inventory_health"),
    ],
)
def test_manager_dashboard_endpoints_return_sane_structure(ctx, path, root_key):
    seeded = _seed_manager_dashboard_data(ctx)
    response = ctx["client"].get(path, headers=_auth(seeded["manager_a"]))
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["meta"]["scope"]["branch_id"] == seeded["outlet_a"]["id"]
    assert payload["meta"]["scope"]["company_id"] == ctx["company_a"].id
    assert root_key in payload["data"]

    if path.endswith("/kpis"):
        assert payload["data"]["kpis"] == {
            "today_sales_total": 200.0,
            "today_order_count": 2,
            "active_staff_count": 1,
            "average_customer_rating_30d": 4.5,
            "low_stock_items_count": 1,
            "pending_tasks_count": 1,
        }
    elif path.endswith("/live-orders"):
        orders = payload["data"]["live_orders"]
        assert len(orders) == 2
        assert {row["order_number"] for row in orders} == {"ALPHA-ORD-001", "ALPHA-ORD-002"}
        assert payload["data"]["source_status"] == "complete"
    elif path.endswith("/staff-on-shift"):
        staff = payload["data"]["staff"]
        assert len(staff) == 1
        assert staff[0]["department"] == "Kitchen"
        assert staff[0]["name"] == "Shift Alpha"
    elif path.endswith("/activity"):
        actions = [row["action"] for row in payload["data"]["events"]]
        assert "dashboard.alpha_viewed" in actions
        assert "dashboard.beta_viewed" not in actions
    elif path.endswith("/health"):
        inventory_health = payload["data"]["inventory_health"]
        assert inventory_health["total_items"] == 3
        assert inventory_health["low_stock_count"] == 1
        assert inventory_health["expiring_soon_count"] == 1
        assert payload["data"]["quality_food_safety_score"] is None
        assert payload["data"]["feedback_summary"]["average_rating"] == 4.5


@pytest.mark.parametrize(
    "path",
    [
        "/api/manager/dashboard/kpis",
        "/api/manager/dashboard/live-orders",
        "/api/manager/dashboard/staff-on-shift",
        "/api/manager/dashboard/activity",
        "/api/manager/dashboard/health",
    ],
)
def test_manager_dashboard_ignores_outlet_id_query_param_and_preserves_scope(ctx, path):
    seeded = _seed_manager_dashboard_data(ctx)
    response = ctx["client"].get(
        f"{path}?outlet_id={seeded['outlet_b']['id']}",
        headers=_auth(seeded["manager_a"]),
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["meta"]["scope"]["branch_id"] == seeded["outlet_a"]["id"]

    if path.endswith("/kpis"):
        assert payload["data"]["kpis"]["today_sales_total"] == 200.0
        assert payload["data"]["kpis"]["today_order_count"] == 2
    elif path.endswith("/live-orders"):
        order_numbers = {row["order_number"] for row in payload["data"]["live_orders"]}
        assert order_numbers == {"ALPHA-ORD-001", "ALPHA-ORD-002"}
        assert "BETA-ORD-001" not in order_numbers
    elif path.endswith("/staff-on-shift"):
        staff_names = {row["name"] for row in payload["data"]["staff"]}
        assert staff_names == {"Shift Alpha"}
    elif path.endswith("/activity"):
        actions = {row["action"] for row in payload["data"]["events"]}
        assert "dashboard.alpha_viewed" in actions
        assert "dashboard.beta_viewed" not in actions
    elif path.endswith("/health"):
        assert payload["data"]["inventory_health"]["total_items"] == 3
        assert payload["data"]["feedback_summary"]["average_rating"] == 4.5


@pytest.mark.parametrize(
    ("path", "actor_key"),
    [
        ("/api/manager/dashboard/kpis", "ceo_a"),
        ("/api/manager/dashboard/live-orders", "ceo_a"),
        ("/api/manager/dashboard/staff-on-shift", "ceo_a"),
        ("/api/manager/dashboard/activity", "ceo_a"),
        ("/api/manager/dashboard/health", "ceo_a"),
        ("/api/manager/dashboard/kpis", "super_ceo"),
        ("/api/manager/dashboard/live-orders", "super_ceo"),
        ("/api/manager/dashboard/staff-on-shift", "super_ceo"),
        ("/api/manager/dashboard/activity", "super_ceo"),
        ("/api/manager/dashboard/health", "super_ceo"),
    ],
)
def test_manager_dashboard_requires_outlet_manager_guard(ctx, actor_key, path):
    db = ctx["db"]
    if actor_key == "super_ceo":
        actor = User(
            username="super_dashboard_root",
            email="super.dashboard.root@example.com",
            hashed_password=auth_guard.hash_password("SuperDashboardPass9!"),
            role="super_ceo",
            is_super_ceo=True,
            is_active=True,
            first_name="Super",
            last_name="Dashboard",
            phone="9000000999",
        )
        db.add(actor)
        db.commit()
    else:
        actor = ctx[actor_key]

    response = ctx["client"].get(path, headers=_auth(actor))
    assert response.status_code == 403
    assert response.json()["detail"] == "Outlet Manager access required"


def test_removed_manager_loses_self_service_access(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    ctx["client"].delete(f"/api/company-ceo/outlets/{created['id']}/manager", headers=_auth(ctx["ceo_a"]))
    response = ctx["client"].get("/api/manager/me", headers=_auth(manager))
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 4. Tenant isolation / IDOR / privilege escalation
# ---------------------------------------------------------------------------

def test_manager_b_cannot_see_outlet_a_data(ctx):
    outlet_a = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    outlet_b = _create_outlet(ctx["client"], ctx["ceo_b"], name="Company B Diner", code="CBD001").json()["data"]["outlet"]
    manager_b, _ = _login_manager(ctx, outlet_b, ctx["ceo_b"])
    # Manager B's own outlet view must never expose outlet A's identifiers.
    response = ctx["client"].get("/api/manager/outlet", headers=_auth(manager_b))
    assert response.json()["data"]["outlet"]["id"] == outlet_b["id"]
    assert response.json()["data"]["outlet"]["id"] != outlet_a["id"]


def test_ceo_cannot_manage_manager_of_foreign_outlet(ctx):
    outlet_a = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    _create_manager(ctx["client"], ctx["ceo_a"], outlet_a["id"])
    response = ctx["client"].put(
        f"/api/company-ceo/outlets/{outlet_a['id']}/manager",
        json={"phone": "9000000111"},
        headers=_auth(ctx["ceo_b"]),
    )
    assert response.status_code == 404


def test_super_ceo_role_cannot_use_company_ceo_guard(ctx):
    db = ctx["db"]
    super_ceo = User(
        username="super_root", email="super.root@example.com",
        hashed_password=auth_guard.hash_password("SuperRootPass9!"),
        role="super_ceo", is_super_ceo=True, is_active=True,
        first_name="Super", last_name="Root", phone="9000000200",
    )
    db.add(super_ceo)
    db.commit()
    response = ctx["client"].get("/api/company-ceo/outlets", headers=_auth(super_ceo))
    assert response.status_code == 403


def test_outlet_manager_flag_without_role_string_denied(ctx):
    """A user with is_outlet_manager=True but role tampered must still be denied."""
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    db = ctx["db"]
    manager.role = "StaffEmployee"  # simulate role drift / tampering
    db.commit()
    response = ctx["client"].get("/api/manager/me", headers=_auth(manager))
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 5. Rate limiting
# ---------------------------------------------------------------------------

def test_outlet_creation_rate_limited_after_threshold(ctx):
    limit = RATE_LIMITS["create_outlet"]
    last_status = None
    for index in range(limit + 1):
        response = _create_outlet(
            ctx["client"], ctx["ceo_a"], name=f"Outlet {index}", code=f"O{index:03d}"
        )
        last_status = response.status_code
    assert last_status == 429


def test_login_lockout_after_repeated_failures(ctx):
    client = ctx["client"]
    username = ctx["ceo_a"].username
    for _ in range(5):
        client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})
    response = client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})
    assert response.status_code == 429


def test_login_success_clears_failure_counter(ctx):
    client = ctx["client"]
    username = ctx["ceo_a"].username
    for _ in range(3):
        client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})
    good = client.post("/api/auth/login", json={"username": username, "password": "CeoAlphaPass9!"})
    assert good.status_code == 200, good.text
    db = ctx["db"]
    remaining = db.query(LoginAttempt).filter(LoginAttempt.was_successful.is_(False)).count()
    assert remaining == 0


# ---------------------------------------------------------------------------
# 6. Sanitization / injection safety
# ---------------------------------------------------------------------------

def test_outlet_name_strips_script_tags(ctx):
    response = _create_outlet(
        ctx["client"], ctx["ceo_a"], name="Cafe <script>alert(1)</script>Central"
    )
    assert response.status_code == 201, response.text
    assert "<script" not in response.json()["data"]["outlet"]["name"]
    assert "Cafe" in response.json()["data"]["outlet"]["name"]


def test_outlet_description_rejects_sql_injection_pattern(ctx):
    response = _create_outlet(
        ctx["client"], ctx["ceo_a"], description="'; DROP TABLE branches; --"
    )
    assert response.status_code == 422


def test_outlet_invalid_pincode_rejected(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"], pincode="!!!")
    assert response.status_code == 422


def test_outlet_invalid_ifsc_rejected(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"], ifsc_code="BADCODE")
    assert response.status_code == 422


def test_outlet_invalid_bank_account_rejected(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"], bank_account_number="abc123")
    assert response.status_code == 422


def test_outlet_invalid_upi_rejected(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"], upi_id="not-a-upi")
    assert response.status_code == 422


def test_outlet_invalid_timezone_rejected(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"], timezone="Mars/Phobos")
    assert response.status_code == 422


def test_outlet_invalid_operating_hours_rejected(ctx):
    response = _create_outlet(ctx["client"], ctx["ceo_a"], opening_time="25:99")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 7. Password / credential safety (overlaps security scan remediation)
# ---------------------------------------------------------------------------

def test_manager_credentials_never_appear_in_audit_log(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    creds = _create_manager(ctx["client"], ctx["ceo_a"], created["id"]).json()["data"]["credentials"]
    plain_password = creds["password"]
    db = ctx["db"]
    rows = db.query(CeoAuditLog).all()
    serialized = "\n".join(str(row.request_meta) for row in rows)
    assert plain_password not in serialized
    manager = db.query(User).filter(User.outlet_id == created["id"], User.is_outlet_manager.is_(True)).first()
    assert manager.hashed_password not in serialized
    assert manager.hashed_password[:20] not in serialized


def test_manager_bank_account_masked_in_audit_log(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = _create_manager(
        ctx["client"], ctx["ceo_a"], created["id"],
        {"manager_bank_account_number": "998877665544"},
    )
    assert response.status_code == 201, response.text
    db = ctx["db"]
    rows = db.query(CeoAuditLog).all()
    serialized = "\n".join(str(row.request_meta) for row in rows)
    assert "998877665544" not in serialized


def test_manager_response_never_includes_hashed_password(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = _create_manager(ctx["client"], ctx["ceo_a"], created["id"])
    body_text = response.text
    assert "hashed_password" not in body_text


def test_manager_password_confirm_mismatch_rejected(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = _create_manager(
        ctx["client"], ctx["ceo_a"], created["id"],
        {"password": "StrongPass123!", "password_confirm": "Different123!"},
    )
    assert response.status_code == 422


def test_manager_username_format_validated(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = _create_manager(ctx["client"], ctx["ceo_a"], created["id"], {"username": "ab"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 8. Domain event emission (real-time sync) - side-effect free when no sockets
# ---------------------------------------------------------------------------

def test_outlet_create_emits_domain_event_without_crashing_when_no_subscribers(ctx):
    # No websocket clients are connected in this test; publish_domain_event must
    # be a safe no-op rather than raising or hanging the request.
    response = _create_outlet(ctx["client"], ctx["ceo_a"])
    assert response.status_code == 201


def test_manager_assignment_emits_domain_event_without_crashing(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    response = _create_manager(ctx["client"], ctx["ceo_a"], created["id"])
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# 9. Auth guard edge cases
# ---------------------------------------------------------------------------

def test_unauthenticated_request_rejected(ctx):
    response = ctx["client"].get("/api/company-ceo/outlets")
    assert response.status_code in (401, 403)


def test_ceo_without_company_assigned_rejected(ctx):
    db = ctx["db"]
    orphan_ceo = User(
        username="orphan_ceo", email="orphan.ceo@example.com",
        hashed_password=auth_guard.hash_password("OrphanCeoPass9!"),
        role="company_ceo", is_company_ceo=True, is_active=True,
        first_name="Orphan", last_name="Ceo", phone="9000000300",
    )
    db.add(orphan_ceo)
    db.commit()
    response = ctx["client"].get("/api/company-ceo/outlets", headers=_auth(orphan_ceo))
    assert response.status_code == 403


def test_ceo_with_inactive_company_rejected(ctx):
    db = ctx["db"]
    ctx["company_a"].is_active = False
    db.commit()
    response = ctx["client"].get("/api/company-ceo/outlets", headers=_auth(ctx["ceo_a"]))
    assert response.status_code == 403


def test_manager_with_deleted_outlet_rejected(ctx):
    created = _create_outlet(ctx["client"], ctx["ceo_a"]).json()["data"]["outlet"]
    manager, _ = _login_manager(ctx, created)
    ctx["client"].delete(f"/api/company-ceo/outlets/{created['id']}", headers=_auth(ctx["ceo_a"]))
    response = ctx["client"].get("/api/manager/me", headers=_auth(manager))
    assert response.status_code == 403
