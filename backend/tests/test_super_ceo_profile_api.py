import io

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.routes.super_ceo.profile import resolve_profile_actor
from app.models import Company, User
from app.models.ceo import CeoAuditLog
from app.services.token_revocation import is_token_revoked
from app.utils.auth_system import auth_guard, require_super_admin, security


@pytest.fixture()
def profile_context(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[Company.__table__, User.__table__, CeoAuditLog.__table__])
    db = Session(engine, expire_on_commit=False)
    actor = User(
        username="profile_ceo",
        email="profile@example.test",
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
    app.dependency_overrides[resolve_profile_actor] = lambda: actor
    app.dependency_overrides[security] = lambda: HTTPAuthorizationCredentials(scheme="Bearer", credentials="profile-test-token")
    monkeypatch.setattr("app.services.file_storage.UPLOAD_ROOT", tmp_path)
    yield TestClient(app), db, actor
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()


def test_get_profile_returns_identity_and_stats(profile_context):
    client, db, _ = profile_context
    db.add(Company(name="Active Co", slug="active-co", is_active=True))
    db.commit()
    response = client.get("/api/super-ceo/profile")
    assert response.status_code == 200
    assert response.json()["data"]["profile"]["stats"]["companies_overseen"] == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("display_name", "Executive Sujit"),
        ("bio", "Building the FoodSrijan portfolio."),
        ("phone", "+919999999999"),
        ("location_city", "Mumbai"),
        ("timezone", "Asia/Kolkata"),
        ("preferred_contact_method", "whatsapp"),
        ("qualifications", [{"degree": "MBA"}]),
        ("certifications", [{"name": "Board Director"}]),
        ("achievements", [{"title": "Hospitality Leader"}]),
        ("preferences", {"language": "en", "currency": "INR"}),
        ("profile_photo_url", "/uploads/profile-photos/1/photo.png"),
        ("cover_photo_url", "https://example.test/cover.jpg"),
    ],
)
def test_profile_partial_updates(profile_context, field, value):
    client, db, actor = profile_context
    response = client.put("/api/super-ceo/profile", json={field: value})
    assert response.status_code == 200
    assert response.json()["data"]["profile"][field] == value
    assert db.query(CeoAuditLog).filter(CeoAuditLog.user_id == actor.id).count() == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email"},
        {"phone": "abc"},
        {"assistant_email": "invalid"},
        {"recovery_phone": "12"},
        {"profile_photo_url": "javascript:alert(1)"},
        {"cover_photo_url": "ftp://example.test/a.jpg"},
        {"bio": "x" * 2001},
        {"preferred_contact_method": "telegram"},
    ],
)
def test_profile_validation_errors(profile_context, payload):
    client, _, _ = profile_context
    assert client.put("/api/super-ceo/profile", json=payload).status_code == 422


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (400, 300), "#d6a84f").save(buffer, "PNG")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "endpoint",
    ["profile-photo", "cover-photo", "company-logo", "company-banner"],
)
def test_valid_image_uploads_generate_variants(profile_context, endpoint):
    client, _, _ = profile_context
    response = client.post(
        f"/api/uploads/{endpoint}",
        files={"file": ("test.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["data"]["url"].startswith("/uploads/")


def test_upload_rejects_invalid_mime(profile_context):
    client, _, _ = profile_context
    response = client.post("/api/uploads/profile-photo", files={"file": ("x.txt", b"text", "text/plain")})
    assert response.status_code == 415


def test_upload_rejects_oversized_file(profile_context):
    client, _, _ = profile_context
    response = client.post(
        "/api/uploads/profile-photo",
        files={"file": ("x.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
    )
    assert response.status_code == 413


def test_upload_rejects_scripted_svg(profile_context):
    client, _, _ = profile_context
    response = client.post(
        "/api/uploads/profile-photo",
        files={"file": ("x.svg", b"<svg onload='alert(1)'></svg>", "image/svg+xml")},
    )
    assert response.status_code == 422


def test_activity_is_paginated(profile_context):
    client, db, actor = profile_context
    client.put("/api/super-ceo/profile", json={"bio": "First"})
    client.put("/api/super-ceo/profile", json={"bio": "Second"})
    response = client.get("/api/super-ceo/profile/activity?page=1&page_size=1")
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 2
    assert len(response.json()["data"]["activity"]) == 1


def test_logout_revokes_current_token(profile_context):
    client, _, _ = profile_context
    response = client.post("/api/super-ceo/profile/logout")
    assert response.status_code == 200
    assert is_token_revoked("profile-test-token")


def test_non_super_ceo_cannot_upload_company_assets(profile_context):
    client, _, _ = profile_context

    def forbidden():
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    app.dependency_overrides[require_super_admin] = forbidden
    response = client.post(
        "/api/uploads/company-logo",
        files={"file": ("x.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/super-ceo/profile"),
        ("put", "/api/super-ceo/profile"),
        ("get", "/api/super-ceo/profile/activity"),
        ("post", "/api/super-ceo/profile/logout"),
    ],
)
def test_profile_requires_authentication(profile_context, method, path):
    client, _, _ = profile_context
    app.dependency_overrides.pop(resolve_profile_actor)
    kwargs = {"json": {}} if method == "put" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401
