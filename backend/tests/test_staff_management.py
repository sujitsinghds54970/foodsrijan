from __future__ import annotations

import base64
from datetime import date, datetime, timedelta
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (
    ActivityLog,
    Branch,
    Brand,
    Company,
    LoginAttempt,
    Permission,
    ProfileMembership,
    ProfileType,
    RateLimitEntry,
    Role,
    User,
    UserCompany,
    UserRole,
)
from app.models.authority import RoleAssignment
from app.models.ceo import CeoAuditLog
from app.models.hr import StaffAttendanceLog, StaffProfile, StaffRequest, StaffTask
from app.models.payroll.models import PayrollRun, PayrollRunStatus, PayrollTransaction
from app.services import file_storage
from app.services.staff_rate_limit import reset_state as reset_staff_rate_limits
from app.services.token_revocation import reset_state as reset_token_revocations
from app.utils.auth_system import auth_guard, create_user_token


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADUlEQVR42mNk+M/wHwAEAQH/cetH5QAAAABJRU5ErkJggg=="
)

OUTLET_BASE = {
    "location": "Downtown",
    "address": "12 MG Road",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411001",
    "phone": "9876543210",
    "email": "outlet@example.com",
    "branch_code": "MAIN001",
    "code": "MAIN001",
    "status": "active",
    "address_line_1": "12 MG Road",
    "outlet_email": "outlet@example.com",
    "outlet_phone": "9876543210",
}

STAFF_CREATE_PAYLOAD = {
    "first_name": "Riya",
    "last_name": "Sharma",
    "display_name": "Riya Sharma",
    "phone": "9876501001",
    "email": "riya.sharma@example.com",
    "employee_code": "RS-001",
    "staff_role": "chef",
    "aadhaar_number": "123456789012",
    "pan_number": "ABCDE1234F",
    "ifsc_code": "HDFC0001234",
    "bank_account_name": "Riya Sharma",
    "bank_account_number": "123456789012",
    "joining_date": "2026-09-01",
    "salary_type": "monthly",
    "monthly_salary": 28000,
    "employment_type": "full_time",
    "shift_preference": "09:00-18:00",
    "weekly_off_day": "monday",
    "emergency_contact_name": "Maa",
    "emergency_contact_phone": "9876502001",
    "emergency_contact_relation": "mother",
}


def _token(user: User) -> str:
    return create_user_token(user)


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


def _make_outlet(company_id: int, index: int, *, name: str) -> Branch:
    payload = dict(OUTLET_BASE)
    payload["name"] = name
    payload["email"] = f"outlet{index}@example.com"
    payload["outlet_email"] = f"outlet{index}@example.com"
    payload["phone"] = f"9876543{index:03d}"
    payload["outlet_phone"] = f"9876543{index:03d}"
    payload["branch_code"] = f"O{index:03d}"
    payload["code"] = f"O{index:03d}"
    return Branch(company_id=company_id, **payload)


def _make_user(**kwargs) -> User:
    defaults = {
        "username": "user",
        "email": "user@example.com",
        "hashed_password": auth_guard.hash_password("SafePassword9!"),
        "role": "staff",
        "is_active": True,
        "first_name": "Test",
        "last_name": "User",
        "phone": "9876509999",
    }
    defaults.update(kwargs)
    return User(**defaults)


@pytest.fixture()
def ctx(monkeypatch, tmp_path):
    reset_staff_rate_limits()
    reset_token_revocations()

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__,
            Brand.__table__,
            Permission.__table__,
            Role.__table__,
            UserRole.__table__,
            UserCompany.__table__,
            RateLimitEntry.__table__,
            Branch.__table__,
            User.__table__,
            ProfileMembership.__table__,
            ProfileType.__table__,
            RoleAssignment.__table__,
            LoginAttempt.__table__,
            CeoAuditLog.__table__,
            ActivityLog.__table__,
            StaffProfile.__table__,
            StaffAttendanceLog.__table__,
            StaffTask.__table__,
            StaffRequest.__table__,
            PayrollRun.__table__,
            PayrollTransaction.__table__,
        ],
    )
    db = Session(engine, expire_on_commit=False)
    monkeypatch.setattr("app.main.SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    monkeypatch.setattr(file_storage, "UPLOAD_ROOT", tmp_path)

    company_a = Company(name="Foods A", slug="foods-a", is_active=True, is_deleted=False)
    company_b = Company(name="Foods B", slug="foods-b", is_active=True, is_deleted=False)
    db.add_all([company_a, company_b])
    db.flush()

    outlet_a = _make_outlet(company_a.id, 1, name="Outlet A")
    outlet_b = _make_outlet(company_a.id, 2, name="Outlet B")
    outlet_c = _make_outlet(company_b.id, 3, name="Outlet C")
    db.add_all([outlet_a, outlet_b, outlet_c])
    db.flush()

    manager_a = _make_user(
        username="manager_a",
        email="manager.a@example.com",
        role="outlet_manager",
        company_id=company_a.id,
        current_company_id=company_a.id,
        branch_id=outlet_a.id,
        outlet_id=outlet_a.id,
        is_outlet_manager=True,
        first_name="Asha",
        last_name="Manager",
        phone="9876500001",
    )
    manager_b = _make_user(
        username="manager_b",
        email="manager.b@example.com",
        role="outlet_manager",
        company_id=company_a.id,
        current_company_id=company_a.id,
        branch_id=outlet_b.id,
        outlet_id=outlet_b.id,
        is_outlet_manager=True,
        first_name="Bina",
        last_name="Manager",
        phone="9876500002",
    )
    manager_c = _make_user(
        username="manager_c",
        email="manager.c@example.com",
        role="outlet_manager",
        company_id=company_b.id,
        current_company_id=company_b.id,
        branch_id=outlet_c.id,
        outlet_id=outlet_c.id,
        is_outlet_manager=True,
        first_name="Charu",
        last_name="Manager",
        phone="9876500003",
    )
    ceo_a = _make_user(
        username="ceo_a",
        email="ceo.a@example.com",
        role="company_ceo",
        company_id=company_a.id,
        current_company_id=company_a.id,
        is_company_ceo=True,
        first_name="Ceo",
        last_name="Alpha",
        phone="9876500004",
    )
    db.add_all([manager_a, manager_b, manager_c, ceo_a])
    db.flush()

    staff_a = _make_user(
        username="staff_a",
        email="staff.a@example.com",
        hashed_password=auth_guard.hash_password("StaffPass9!A"),
        role="staff",
        company_id=company_a.id,
        current_company_id=company_a.id,
        branch_id=outlet_a.id,
        outlet_id=outlet_a.id,
        is_staff=True,
        staff_role="chef",
        employee_code="A-001",
        first_name="Riya",
        last_name="Alpha",
        display_name="Riya Alpha",
        phone="9876500101",
        aadhaar_number="111122223333",
        pan_number="AAAAA1111A",
        bank_account_number="123456789012",
        bank_account_name="Riya Alpha",
        ifsc_code="HDFC0001234",
        joining_date=date(2026, 9, 1),
        force_password_change=True,
        manager_id=manager_a.id,
        staff_assigned_by=manager_a.id,
        staff_assigned_at=datetime.utcnow(),
        created_by=manager_a.id,
    )
    staff_b = _make_user(
        username="staff_b",
        email="staff.b@example.com",
        hashed_password=auth_guard.hash_password("StaffPass9!B"),
        role="staff",
        company_id=company_a.id,
        current_company_id=company_a.id,
        branch_id=outlet_b.id,
        outlet_id=outlet_b.id,
        is_staff=True,
        staff_role="waiter",
        employee_code="B-001",
        first_name="Meena",
        last_name="Beta",
        phone="9876500102",
        aadhaar_number="111122223334",
        pan_number="BBBBB2222B",
        manager_id=manager_b.id,
        staff_assigned_by=manager_b.id,
        staff_assigned_at=datetime.utcnow(),
        created_by=manager_b.id,
    )
    staff_c = _make_user(
        username="staff_c",
        email="staff.c@example.com",
        hashed_password=auth_guard.hash_password("StaffPass9!C"),
        role="staff",
        company_id=company_b.id,
        current_company_id=company_b.id,
        branch_id=outlet_c.id,
        outlet_id=outlet_c.id,
        is_staff=True,
        staff_role="cashier",
        employee_code="C-001",
        first_name="Tina",
        last_name="Gamma",
        phone="9876500103",
        aadhaar_number="111122223335",
        pan_number="CCCCC3333C",
        manager_id=manager_c.id,
        staff_assigned_by=manager_c.id,
        staff_assigned_at=datetime.utcnow(),
        created_by=manager_c.id,
    )
    db.add_all([staff_a, staff_b, staff_c])
    db.flush()

    profile_a = StaffProfile(user_id=staff_a.id, branch_id=outlet_a.id, created_by=manager_a.id, staff_employee_id="1-A-001", is_active=True)
    profile_b = StaffProfile(user_id=staff_b.id, branch_id=outlet_b.id, created_by=manager_b.id, staff_employee_id="2-B-001", is_active=True)
    profile_c = StaffProfile(user_id=staff_c.id, branch_id=outlet_c.id, created_by=manager_c.id, staff_employee_id="3-C-001", is_active=True)
    db.add_all([profile_a, profile_b, profile_c])
    db.flush()

    now = datetime.utcnow()
    db.add_all(
        [
            StaffAttendanceLog(
                StaffEmployee_profile_id=profile_a.id,
                branch_id=outlet_a.id,
                attendance_date=now.replace(hour=9, minute=0, second=0, microsecond=0),
                clock_in_time=now.replace(hour=9, minute=5, second=0, microsecond=0),
                status="present",
                task="Opening",
            ),
            StaffTask(
                StaffEmployee_profile_id=profile_a.id,
                branch_id=outlet_a.id,
                assigned_to=staff_a.id,
                assigned_by=manager_a.id,
                task_name="Prep",
                title="Prep shift",
                status="Pending",
                priority="High",
                deadline=now + timedelta(hours=3),
            ),
            StaffRequest(
                staff_id=staff_a.id,
                company_id=company_a.id,
                outlet_id=outlet_a.id,
                type="leave",
                reason="Medical leave",
                status="pending",
            ),
        ]
    )
    db.flush()
    payroll_run = PayrollRun(branch_id=outlet_a.id, month=9, year=2026, status=PayrollRunStatus.DRAFT)
    db.add(payroll_run)
    db.flush()
    db.add(
        PayrollTransaction(
            payroll_run_id=payroll_run.id,
            staff_id=profile_a.id,
            base_salary=30000,
            total_deductions=2000,
            net_pay=28000,
        )
    )
    db.commit()

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    yield {
        "client": client,
        "db": db,
        "company_a": company_a,
        "company_b": company_b,
        "outlet_a": outlet_a,
        "outlet_b": outlet_b,
        "outlet_c": outlet_c,
        "manager_a": manager_a,
        "manager_b": manager_b,
        "manager_c": manager_c,
        "ceo_a": ceo_a,
        "staff_a": staff_a,
        "staff_b": staff_b,
        "staff_c": staff_c,
        "profile_a": profile_a,
    }
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()


def _create_staff(client: TestClient, manager: User, **overrides):
    payload = {**STAFF_CREATE_PAYLOAD, **overrides}
    return client.post("/api/manager/staff", json=payload, headers=_auth(manager))


def _create_staff_for_listing(ctx, suffix: int, **overrides):
    payload = {
        **STAFF_CREATE_PAYLOAD,
        "email": f"list{suffix}@example.com",
        "phone": f"987651{suffix:04d}",
        "employee_code": f"L-{suffix:03d}",
        "aadhaar_number": f"{123456780000 + suffix}",
        "pan_number": f"AAAPA{suffix:04d}A"[:10],
    }
    payload.update(overrides)
    return _create_staff(ctx["client"], ctx["manager_a"], **payload)


def _audit_text(db: Session) -> str:
    rows = db.query(CeoAuditLog).order_by(CeoAuditLog.id.asc()).all()
    return " ".join(str(row.request_meta) for row in rows)


def _delete(client: TestClient, path: str, headers: dict[str, str], payload: dict[str, str]):
    return client.request("DELETE", path, json=payload, headers=headers)


def _image_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), color="red").save(output, format="PNG")
    return output.getvalue()


def test_registered_staff_routes_present():
    paths = {route.path for route in app.routes}
    assert "/api/manager/staff" in paths
    assert "/api/manager/staff/stats" in paths
    assert "/api/manager/staff/{staff_id}" in paths
    assert "/api/manager/staff/{staff_id}/reveal" in paths
    assert "/api/manager/staff/{staff_id}/reset-password" in paths
    assert "/api/manager/staff/{staff_id}/photo" in paths
    assert "/api/staff/me" in paths
    assert "/api/staff/me/outlet" in paths
    assert "/api/staff/me/dashboard" in paths
    assert "/api/staff/me/attendance" in paths
    assert "/api/staff/me/tasks" in paths
    assert "/api/staff/me/payslips" in paths
    assert "/api/staff/me/requests" in paths
    assert "/api/staff/me/activity" in paths


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/manager/staff/2"),
        ("put", "/api/manager/staff/2"),
        ("delete", "/api/manager/staff/2"),
        ("post", "/api/manager/staff/2/reset-password"),
        ("get", "/api/manager/staff/2/reveal?field=aadhaar"),
    ],
)
def test_non_manager_forbidden_on_manager_routes(ctx, method, path):
    client = ctx["client"]
    kwargs = {"headers": _auth(ctx["staff_a"])}
    if method == "put":
        kwargs["json"] = {"first_name": "Nope"}
    if method == "delete":
        response = _delete(client, path, kwargs["headers"], {"deactivated_reason": "x"})
    else:
        response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/api/staff/me",
        "/api/staff/me/outlet",
        "/api/staff/me/dashboard",
        "/api/staff/me/attendance",
        "/api/staff/me/tasks",
        "/api/staff/me/payslips",
        "/api/staff/me/requests",
        "/api/staff/me/activity",
    ],
)
def test_non_staff_forbidden_on_staff_routes(ctx, path):
    response = ctx["client"].get(path, headers=_auth(ctx["manager_a"]))
    assert response.status_code == 403


def test_manager_create_staff_returns_one_time_credentials_and_hashes_password(ctx):
    response = _create_staff(ctx["client"], ctx["manager_a"])
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    created = ctx["db"].query(User).filter(User.employee_code == "rs-001").one()
    assert created.outlet_id == ctx["outlet_a"].id
    assert created.company_id == ctx["company_a"].id
    assert created.is_staff is True
    assert data["credentials"]["password"]
    assert data["credentials"]["employee_code"] == "rs-001"
    assert created.hashed_password.startswith("$2")
    assert "$2b$12$" in created.hashed_password or "$2a$12$" in created.hashed_password
    assert data["staff"]["bank_account_number"].endswith("9012")


def test_manager_create_ignores_spoofed_company_and_outlet_ids(ctx):
    response = _create_staff(
        ctx["client"],
        ctx["manager_a"],
        company_id=ctx["company_b"].id,
        outlet_id=ctx["outlet_b"].id,
        branch_id=ctx["outlet_b"].id,
        employee_code="RS-777",
        phone="9876501777",
        email="spoof@example.com",
        aadhaar_number="123456789099",
        pan_number="ABCDE1299F",
    )
    assert response.status_code == 201, response.text
    staff = ctx["db"].query(User).filter(User.employee_code == "rs-777").one()
    assert staff.company_id == ctx["company_a"].id
    assert staff.outlet_id == ctx["outlet_a"].id
    assert staff.branch_id == ctx["outlet_a"].id


@pytest.mark.parametrize(
    ("overrides", "detail"),
    [
        ({"phone": "123"}, None),
        ({"email": "not-an-email"}, None),
        ({"aadhaar_number": "1234"}, "Invalid Aadhaar number"),
        ({"pan_number": "wrongpan"}, "Invalid PAN number"),
        ({"ifsc_code": "BAD1"}, "Invalid IFSC code"),
    ],
)
def test_create_validation_errors(ctx, overrides, detail):
    response = _create_staff(
        ctx["client"],
        ctx["manager_a"],
        employee_code=f"VAL-{len(overrides)}",
        phone=overrides.get("phone", "9876501888"),
        email=overrides.get("email", "val@example.com"),
        aadhaar_number=overrides.get("aadhaar_number", "123456789188"),
        pan_number=overrides.get("pan_number", "ABCDE1888F"),
        ifsc_code=overrides.get("ifsc_code", "HDFC0001888"),
    )
    assert response.status_code == 422
    if detail:
        assert response.json()["detail"] == detail


def test_create_rejects_weak_password(ctx):
    response = _create_staff(
        ctx["client"],
        ctx["manager_a"],
        password="weakpass",
        employee_code="WEAK-1",
        phone="9876501889",
        email="weak@example.com",
        aadhaar_number="123456789189",
        pan_number="ABCDE1889F",
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("overrides", "expected_detail"),
    [
        ({"phone": "9876500101", "employee_code": "DUPE-1", "email": "new1@example.com", "aadhaar_number": "123456789190", "pan_number": "ABCDE1890F"}, "Phone already exists"),
        ({"phone": "9876501891", "employee_code": "DUPE-2", "email": "staff.a@example.com", "aadhaar_number": "123456789191", "pan_number": "ABCDE1891F"}, "Email already exists"),
        ({"phone": "9876501892", "employee_code": "A-001", "email": "new2@example.com", "aadhaar_number": "123456789192", "pan_number": "ABCDE1892F"}, "Employee code already exists"),
        ({"phone": "9876501893", "employee_code": "DUPE-4", "email": "new4@example.com", "aadhaar_number": "111122223333", "pan_number": "ABCDE1893F"}, "Aadhaar number already exists"),
    ],
)
def test_create_rejects_duplicates(ctx, overrides, expected_detail):
    response = _create_staff(ctx["client"], ctx["manager_a"], **overrides)
    assert response.status_code == 409
    assert response.json()["detail"] == expected_detail


def test_list_pagination_filter_and_search(ctx):
    assert _create_staff_for_listing(ctx, 1, staff_role="chef").status_code == 201
    assert _create_staff_for_listing(ctx, 2, staff_role="waiter").status_code == 201
    created = _create_staff_for_listing(ctx, 3, staff_role="cashier").json()["data"]["staff"]
    _delete(ctx["client"], f"/api/manager/staff/{created['id']}", _auth(ctx["manager_a"]), {"deactivated_reason": "Offboarded"})

    page = ctx["client"].get("/api/manager/staff?page=1&page_size=2", headers=_auth(ctx["manager_a"]))
    assert page.status_code == 200
    assert len(page.json()["data"]["items"]) == 2

    by_role = ctx["client"].get("/api/manager/staff?staff_role=waiter", headers=_auth(ctx["manager_a"]))
    assert all(item["staff_role"] == "waiter" for item in by_role.json()["data"]["items"])

    inactive = ctx["client"].get("/api/manager/staff?status=inactive", headers=_auth(ctx["manager_a"]))
    assert inactive.status_code == 200
    assert inactive.json()["data"]["items"]

    search = ctx["client"].get("/api/manager/staff?search=9876510002", headers=_auth(ctx["manager_a"]))
    assert search.status_code == 200
    assert search.json()["data"]["items"][0]["phone"] == "9876510002"


@pytest.mark.parametrize(
    ("path_template", "method", "payload"),
    [
        ("/api/manager/staff/{staff_id}", "get", None),
        ("/api/manager/staff/{staff_id}", "put", {"first_name": "Blocked"}),
        ("/api/manager/staff/{staff_id}", "delete", {"deactivated_reason": "Blocked"}),
        ("/api/manager/staff/{staff_id}/reset-password", "post", None),
        ("/api/manager/staff/{staff_id}/reveal?field=aadhaar", "get", None),
    ],
)
def test_manager_cannot_access_other_outlet_staff(ctx, path_template, method, payload):
    path = path_template.format(staff_id=ctx["staff_b"].id)
    kwargs = {"headers": _auth(ctx["manager_a"])}
    if payload is not None:
        kwargs["json"] = payload
    if method == "delete":
        response = _delete(ctx["client"], path, kwargs["headers"], payload)
    else:
        response = getattr(ctx["client"], method)(path, **kwargs)
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("path_template", "method", "payload"),
    [
        ("/api/manager/staff/{staff_id}", "get", None),
        ("/api/manager/staff/{staff_id}", "put", {"first_name": "Blocked"}),
        ("/api/manager/staff/{staff_id}", "delete", {"deactivated_reason": "Blocked"}),
        ("/api/manager/staff/{staff_id}/reset-password", "post", None),
        ("/api/manager/staff/{staff_id}/reveal?field=pan", "get", None),
    ],
)
def test_manager_cannot_access_other_company_staff(ctx, path_template, method, payload):
    path = path_template.format(staff_id=ctx["staff_c"].id)
    kwargs = {"headers": _auth(ctx["manager_a"])}
    if payload is not None:
        kwargs["json"] = payload
    if method == "delete":
        response = _delete(ctx["client"], path, kwargs["headers"], payload)
    else:
        response = getattr(ctx["client"], method)(path, **kwargs)
    assert response.status_code == 404


def test_manager_detail_masks_pii_and_reveal_unmasks(ctx):
    detail = ctx["client"].get(f"/api/manager/staff/{ctx['staff_a'].id}", headers=_auth(ctx["manager_a"]))
    assert detail.status_code == 200
    staff = detail.json()["data"]["staff"]
    assert staff["aadhaar_number"] == "XXXX-XXXX-3333"
    assert staff["pan_number"] == "XXXXX1111A"
    assert staff["bank_account_number"].endswith("9012")

    reveal = ctx["client"].get(f"/api/manager/staff/{ctx['staff_a'].id}/reveal?field=aadhaar", headers=_auth(ctx["manager_a"]))
    assert reveal.status_code == 200
    assert reveal.json()["data"]["reveal"]["value"] == "111122223333"


def test_staff_self_me_is_unmasked(ctx):
    response = ctx["client"].get("/api/staff/me", headers=_auth(ctx["staff_a"]))
    assert response.status_code == 200
    staff = response.json()["data"]["staff"]
    assert staff["aadhaar_number"] == "111122223333"
    assert staff["pan_number"] == "AAAAA1111A"
    assert staff["bank_account_number"] == "123456789012"


def test_staff_cannot_self_promote_or_change_scope(ctx):
    response = ctx["client"].put(
        "/api/staff/me",
        json={
            "display_name": "Updated Name",
            "staff_role": "cashier",
            "company_id": ctx["company_b"].id,
            "outlet_id": ctx["outlet_b"].id,
            "employee_code": "HACKED",
            "monthly_salary": 999999,
        },
        headers=_auth(ctx["staff_a"]),
    )
    assert response.status_code == 200, response.text
    ctx["db"].refresh(ctx["staff_a"])
    assert ctx["staff_a"].display_name == "Updated Name"
    assert ctx["staff_a"].staff_role == "chef"
    assert ctx["staff_a"].company_id == ctx["company_a"].id
    assert ctx["staff_a"].outlet_id == ctx["outlet_a"].id
    assert ctx["staff_a"].employee_code == "A-001"
    assert ctx["staff_a"].monthly_salary is None


def test_staff_me_outlet_ignores_spoofed_query_params(ctx):
    response = ctx["client"].get(
        f"/api/staff/me/outlet?outlet_id={ctx['outlet_b'].id}&id={ctx['outlet_b'].id}",
        headers=_auth(ctx["staff_a"]),
    )
    assert response.status_code == 200
    assert response.json()["data"]["outlet"]["id"] == ctx["outlet_a"].id


def test_staff_dashboard_attendance_tasks_payslips_requests_activity(ctx):
    dashboard = ctx["client"].get("/api/staff/me/dashboard", headers=_auth(ctx["staff_a"]))
    assert dashboard.status_code == 200
    assert dashboard.json()["data"]["dashboard"]["pending_requests_count"] >= 1

    attendance = ctx["client"].get("/api/staff/me/attendance", headers=_auth(ctx["staff_a"]))
    assert attendance.status_code == 200
    assert attendance.json()["data"]["items"]

    tasks = ctx["client"].get("/api/staff/me/tasks", headers=_auth(ctx["staff_a"]))
    assert tasks.status_code == 200
    assert tasks.json()["data"]["items"]

    payslips = ctx["client"].get("/api/staff/me/payslips", headers=_auth(ctx["staff_a"]))
    assert payslips.status_code == 200
    assert payslips.json()["data"]["items"]

    created_request = ctx["client"].post("/api/staff/me/requests", json={"type": "advance", "reason": "Urgent"}, headers=_auth(ctx["staff_a"]))
    assert created_request.status_code == 201
    requests = ctx["client"].get("/api/staff/me/requests", headers=_auth(ctx["staff_a"]))
    assert requests.status_code == 200
    assert all(item["id"] for item in requests.json()["data"]["items"])

    activity = ctx["client"].get("/api/staff/me/activity", headers=_auth(ctx["staff_a"]))
    assert activity.status_code == 200


@pytest.mark.parametrize("identifier_key", ["username", "phone", "email", "employee_code"])
def test_staff_can_login_with_multiple_identifiers(ctx, identifier_key):
    response = _create_staff(
        ctx["client"],
        ctx["manager_a"],
        employee_code="LOGIN-1",
        phone="9876502111",
        email="login.one@example.com",
        aadhaar_number="123456789211",
        pan_number="ABCDE2211F",
        password="SafeLoginPass9!",
    )
    assert response.status_code == 201, response.text
    created = ctx["db"].query(User).filter(User.employee_code == "login-1").one()
    identifier = getattr(created, identifier_key)
    login = ctx["client"].post("/api/auth/login", json={"username": identifier, "password": "SafeLoginPass9!"})
    assert login.status_code == 200, login.text
    assert login.json()["user"]["id"] == created.id


def test_soft_delete_only_and_restore(ctx):
    response = _delete(ctx["client"], f"/api/manager/staff/{ctx['staff_a'].id}", _auth(ctx["manager_a"]), {"deactivated_reason": "Policy breach"})
    assert response.status_code == 200, response.text
    row = ctx["db"].query(User).filter(User.id == ctx["staff_a"].id).one()
    assert row.is_deleted is True
    assert row.is_active is False
    assert row.deactivated_reason == "Policy breach"

    restored = ctx["client"].post(f"/api/manager/staff/{ctx['staff_a'].id}/restore", headers=_auth(ctx["manager_a"]))
    assert restored.status_code == 200, restored.text
    ctx["db"].refresh(row)
    assert row.is_deleted is False
    assert row.is_active is True


def test_deactivated_staff_cannot_login(ctx):
    _delete(ctx["client"], f"/api/manager/staff/{ctx['staff_a'].id}", _auth(ctx["manager_a"]), {"deactivated_reason": "Offboarded"})
    response = ctx["client"].post("/api/auth/login", json={"username": "staff_a", "password": "StaffPass9!A"})
    assert response.status_code == 401


def test_password_reset_returns_new_password_and_old_password_stops_working(ctx):
    response = ctx["client"].post(f"/api/manager/staff/{ctx['staff_a'].id}/reset-password", headers=_auth(ctx["manager_a"]))
    assert response.status_code == 200
    new_password = response.json()["data"]["credentials"]["password"]
    assert new_password

    old_login = ctx["client"].post("/api/auth/login", json={"username": "staff_a", "password": "StaffPass9!A"})
    assert old_login.status_code == 401

    new_login = ctx["client"].post("/api/auth/login", json={"username": "staff_a", "password": new_password})
    assert new_login.status_code == 200


def test_test_login_endpoint_checks_password_without_token_issuance(ctx):
    ok = ctx["client"].post(
        f"/api/manager/staff/{ctx['staff_a'].id}/test-login",
        json={"password": "StaffPass9!A"},
        headers=_auth(ctx["manager_a"]),
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["result"]["can_login"] is True

    bad = ctx["client"].post(
        f"/api/manager/staff/{ctx['staff_a'].id}/test-login",
        json={"password": "WrongPassword123!"},
        headers=_auth(ctx["manager_a"]),
    )
    assert bad.status_code == 200
    assert bad.json()["data"]["result"]["can_login"] is False


def test_audit_log_entries_created_without_password_values(ctx):
    create = _create_staff(
        ctx["client"],
        ctx["manager_a"],
        employee_code="AUD-1",
        phone="9876502991",
        email="audit1@example.com",
        aadhaar_number="123456789291",
        pan_number="ABCDE2291F",
        password="AuditedPass9!",
    )
    assert create.status_code == 201, create.text
    staff_id = create.json()["data"]["staff"]["id"]

    update = ctx["client"].put(
        f"/api/manager/staff/{staff_id}",
        json={"display_name": "Audit Updated"},
        headers=_auth(ctx["manager_a"]),
    )
    assert update.status_code == 200

    reset = ctx["client"].post(f"/api/manager/staff/{staff_id}/reset-password", headers=_auth(ctx["manager_a"]))
    assert reset.status_code == 200

    delete = _delete(ctx["client"], f"/api/manager/staff/{staff_id}", _auth(ctx["manager_a"]), {"deactivated_reason": "Audit"})
    assert delete.status_code == 200

    actions = [row.action for row in ctx["db"].query(CeoAuditLog).order_by(CeoAuditLog.id.asc()).all()]
    assert "staff.created" in actions
    assert "staff.updated" in actions
    assert "staff.deactivated" in actions
    assert "staff.password_reset" in actions
    haystack = _audit_text(ctx["db"])
    assert "AuditedPass9!" not in haystack
    assert "password" not in haystack.lower() or "force_password_change" in haystack


def test_manager_staff_stats_counts(ctx):
    response = ctx["client"].get("/api/manager/staff/stats", headers=_auth(ctx["manager_a"]))
    assert response.status_code == 200
    stats = response.json()["data"]["stats"]
    assert stats["total_staff"] >= 1
    assert stats["pending_requests"] >= 1


def test_manager_and_staff_photo_uploads_work(ctx):
    manager_photo = _create_staff(
        ctx["client"],
        ctx["manager_a"],
        employee_code="PHOTO-1",
        phone="9876503001",
        email="photo1@example.com",
        aadhaar_number="123456789301",
        pan_number="ABCDE2301F",
    )
    staff_id = manager_photo.json()["data"]["staff"]["id"]
    manager_upload = ctx["client"].post(
        f"/api/manager/staff/{staff_id}/photo",
        files={"file": ("photo.png", _image_bytes(), "image/png")},
        headers=_auth(ctx["manager_a"]),
    )
    assert manager_upload.status_code == 200, manager_upload.text
    assert manager_upload.json()["data"]["asset"]["url"].startswith("/uploads/staff-photos/")

    self_upload = ctx["client"].post(
        "/api/staff/me/photo",
        files={"file": ("self.png", _image_bytes(), "image/png")},
        headers=_auth(ctx["staff_a"]),
    )
    assert self_upload.status_code == 200, self_upload.text
    assert self_upload.json()["data"]["asset"]["url"].startswith("/uploads/staff-photos/")


def test_staff_creation_rate_limit_hits_on_thirty_first_request(ctx):
    statuses = []
    for index in range(31):
        response = _create_staff(
            ctx["client"],
            ctx["manager_a"],
            employee_code=f"RATE-{index}",
            phone=f"987652{index:04d}",
            email=f"rate{index}@example.com",
            aadhaar_number=f"{123450000000 + index:012d}",
            pan_number=f"ABCDE{index:04d}F",
        )
        statuses.append(response.status_code)
    assert statuses[:30] == [201] * 30
    assert statuses[30] == 429


def test_staff_failed_login_rate_limit_hits_on_eleventh_failure(ctx):
    response = _create_staff(
        ctx["client"],
        ctx["manager_a"],
        employee_code="LOCK-1",
        phone="9876503111",
        email="lock1@example.com",
        aadhaar_number="123456789311",
        pan_number="ABCDE2311F",
        password="LockPass9!AA",
    )
    assert response.status_code == 201
    identifier = response.json()["data"]["credentials"]["phone"]
    for _ in range(10):
        attempt = ctx["client"].post("/api/auth/login", json={"username": identifier, "password": "WrongPassword123!"})
        assert attempt.status_code == 401
    blocked = ctx["client"].post("/api/auth/login", json={"username": identifier, "password": "WrongPassword123!"})
    assert blocked.status_code == 429


def test_manager_can_read_staff_audit_feed(ctx):
    _create_staff(
        ctx["client"],
        ctx["manager_a"],
        employee_code="AUD-2",
        phone="9876503222",
        email="audit2@example.com",
        aadhaar_number="123456789322",
        pan_number="ABCDE2322F",
    )
    created = ctx["db"].query(User).filter(User.employee_code == "aud-2").one()
    response = ctx["client"].get(f"/api/manager/staff/{created.id}/audit", headers=_auth(ctx["manager_a"]))
    assert response.status_code == 200
    assert response.json()["data"]["items"]
