import json

import pytest
from fastapi import HTTPException

from app.models.ceo import CeoAuditLog
from app.services.token_revocation import reset_state
from app.utils.auth_system import TokenData, auth_guard
from test_staff_management import _auth, _make_user, ctx


@pytest.fixture
def credentials_ctx(ctx):
    super_ceo = _make_user(
        username="super_credentials", email="super.credentials@example.com",
        role="super_ceo", is_super_ceo=True, is_super_admin=True,
    )
    ctx["db"].add(super_ceo)
    ctx["db"].commit()
    ctx["super_ceo"] = super_ceo
    return ctx


def endpoint(ctx, profile):
    return {
        "ceo": f"/api/super-ceo/companies/{ctx['company_a'].id}/ceo/credentials",
        "manager": f"/api/company-ceo/outlets/{ctx['outlet_a'].id}/manager/credentials",
        "staff": f"/api/manager/staff/{ctx['staff_a'].id}/credentials",
    }[profile]


ACTORS = {"ceo": "super_ceo", "manager": "ceo_a", "staff": "manager_a"}
TARGETS = {"ceo": "ceo_a", "manager": "manager_a", "staff": "staff_a"}


@pytest.mark.parametrize("profile", ["ceo", "manager", "staff"])
def test_current_login_is_visible_without_password(credentials_ctx, profile):
    c = credentials_ctx
    response = c["client"].get(endpoint(c, profile), headers=_auth(c[ACTORS[profile]]))
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    login = response.json()["data"]["login"]
    assert login["username"] == c[TARGETS[profile]].username
    assert "password" not in login and "hashed_password" not in response.text
    assert set(login) == {"username", "user_id", "is_active", "force_password_change", "password_changed_at"}


@pytest.mark.parametrize("profile", ["ceo", "manager", "staff"])
def test_update_username_and_password_applies_immediately(credentials_ctx, profile):
    c = credentials_ctx
    target = c[TARGETS[profile]]
    previous_username = target.username
    old_auth = _auth(target)
    secret = "UpdatedLoginPass9!"
    new_username = f"updated_{profile}"
    response = c["client"].patch(
        endpoint(c, profile), headers=_auth(c[ACTORS[profile]]),
        json={"username": new_username, "password": secret, "password_confirm": secret},
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["data"]["credentials"]["password"] == secret
    c["db"].refresh(target)
    assert target.username == new_username
    assert target.hashed_password != secret
    assert auth_guard.verify_password(secret, target.hashed_password)
    assert target.force_password_change is True
    assert c["client"].get("/api/auth/me", headers=old_auth).status_code == 401
    assert c["client"].post("/api/auth/login", json={"username": previous_username, "password": secret}).status_code == 401
    signed_in = c["client"].post("/api/auth/login", json={"username": new_username, "password": secret})
    assert signed_in.status_code == 200
    assert c["client"].get("/api/auth/me", headers=_auth(target)).status_code == 200
    read = c["client"].get(endpoint(c, profile), headers=_auth(c[ACTORS[profile]]))
    assert secret not in read.text and "credentials" not in read.json()["data"]
    audits = c["db"].query(CeoAuditLog).filter_by(action=f"{profile}.login_updated").all()
    assert len(audits) == 1
    assert secret not in json.dumps(audits[0].request_meta)


@pytest.mark.parametrize("profile", ["ceo", "manager", "staff"])
def test_generated_password_returned_only_once(credentials_ctx, profile):
    c = credentials_ctx
    response = c["client"].patch(endpoint(c, profile), headers=_auth(c[ACTORS[profile]]), json={"reset_password": True})
    assert response.status_code == 200, response.text
    password = response.json()["data"]["credentials"]["password"]
    assert len(password) == 24
    assert auth_guard.verify_password(password, c[TARGETS[profile]].hashed_password)
    assert password not in c["client"].get(endpoint(c, profile), headers=_auth(c[ACTORS[profile]])).text


@pytest.mark.parametrize("profile", ["ceo", "manager", "staff"])
def test_username_only_preserves_password(credentials_ctx, profile):
    c = credentials_ctx
    previous_hash = c[TARGETS[profile]].hashed_password
    response = c["client"].patch(endpoint(c, profile), headers=_auth(c[ACTORS[profile]]), json={"username": f"rename_{profile}"})
    assert response.status_code == 200
    assert c[TARGETS[profile]].hashed_password == previous_hash
    assert "credentials" not in response.json()["data"]


@pytest.mark.parametrize("profile,actor", [
    ("ceo", "ceo_a"), ("ceo", "manager_a"), ("ceo", "staff_a"),
    ("manager", "manager_a"), ("manager", "staff_a"),
    ("staff", "staff_a"), ("staff", "ceo_a"),
])
def test_hierarchy_cannot_be_bypassed(credentials_ctx, profile, actor):
    c = credentials_ctx
    for method, body in [("get", {}), ("patch", {"json": {"reset_password": True}})]:
        response = getattr(c["client"], method)(endpoint(c, profile), headers=_auth(c[actor]), **body)
        assert response.status_code == 403


@pytest.mark.parametrize("actor", ["manager_b", "manager_c"])
def test_other_outlet_staff_is_not_found(credentials_ctx, actor):
    c = credentials_ctx
    response = c["client"].patch(endpoint(c, "staff"), headers=_auth(c[actor]), json={"reset_password": True})
    assert response.status_code == 404


def test_other_company_manager_is_not_found(credentials_ctx):
    c = credentials_ctx
    path = f"/api/company-ceo/outlets/{c['outlet_c'].id}/manager/credentials"
    assert c["client"].get(path, headers=_auth(c["ceo_a"])).status_code == 404
    assert c["client"].patch(path, headers=_auth(c["ceo_a"]), json={"reset_password": True}).status_code == 404


@pytest.mark.parametrize("payload", [
    {}, {"username": None}, {"username": "bad name"}, {"username": "x"},
    {"password": "weak", "password_confirm": "weak"},
    {"password": "UpdatedLoginPass9!", "password_confirm": "MismatchPass9!"},
    {"password_confirm": "UpdatedLoginPass9!"},
    {"reset_password": True, "password": "UpdatedLoginPass9!", "password_confirm": "UpdatedLoginPass9!"},
    {"username": "valid_name", "company_id": 999},
])
def test_invalid_changes_do_not_modify_or_echo_password(credentials_ctx, payload):
    c = credentials_ctx
    previous_hash = c["staff_a"].hashed_password
    response = c["client"].patch(endpoint(c, "staff"), headers=_auth(c["manager_a"]), json=payload)
    assert response.status_code == 422
    assert c["staff_a"].hashed_password == previous_hash
    assert "UpdatedLoginPass9!" not in response.text
    assert "weak" not in response.text


def test_duplicate_username_case_insensitive_and_atomic(credentials_ctx):
    c = credentials_ctx
    previous_hash = c["staff_a"].hashed_password
    response = c["client"].patch(
        endpoint(c, "staff"), headers=_auth(c["manager_a"]),
        json={"username": c["staff_b"].username.upper(), "reset_password": True},
    )
    assert response.status_code == 409
    assert c["staff_a"].hashed_password == previous_hash


def test_renamed_username_cannot_transfer_an_old_session(credentials_ctx):
    c = credentials_ctx
    old_token_data = TokenData(username=c["staff_a"].username, user_id=c["staff_a"].id)
    c["staff_a"].username = "renamed_staff"
    c["staff_b"].username = old_token_data.username
    c["db"].commit()
    reset_state()
    with pytest.raises(HTTPException) as error:
        auth_guard.get_current_user(old_token_data, c["db"])
    assert error.value.status_code == 401


def test_password_reset_still_rejects_old_session_after_revocation_state_reset(credentials_ctx):
    c = credentials_ctx
    old_auth = _auth(c["staff_a"])
    response = c["client"].patch(endpoint(c, "staff"), headers=_auth(c["manager_a"]), json={"reset_password": True})
    assert response.status_code == 200
    reset_state()
    assert c["client"].get("/api/auth/me", headers=old_auth).status_code == 401
    assert c["client"].get("/api/auth/me", headers=_auth(c["staff_a"])).status_code == 200
