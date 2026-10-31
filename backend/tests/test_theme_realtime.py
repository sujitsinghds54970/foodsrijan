import asyncio
import io
import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from app.database import Base, get_db
from app.main import app
from app.models import Company, ProfileType, User
from app.models.ceo import CeoAuditLog
from app.models.themes import Theme, ThemeAssignment, ThemeVersion
from app.routes.super_ceo.profile import resolve_profile_actor
from app.routes.super_ceo.themes import changed_token_paths
from app.services.contrast import check_contrast
from app.services.theme_tokens import default_tokens
from app.services.theme_resolver import resolve_theme
from app.services.websocket_service import ThemeSubscriber, connection_manager
from app.utils.auth_system import auth_guard, require_super_admin


def _token(user: User) -> str:
    return auth_guard.create_access_token(
        {"sub": user.username, "user_id": user.id, "role": user.role, "jti": str(time.time_ns())},
        timedelta(minutes=5),
    )


@pytest.fixture()
def realtime_context(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__,
            User.__table__,
            ProfileType.__table__,
            Theme.__table__,
            ThemeVersion.__table__,
            ThemeAssignment.__table__,
            CeoAuditLog.__table__,
        ],
    )
    db = Session(engine, expire_on_commit=False)
    monkeypatch.setattr("app.main.SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))

    company = Company(name="Srijan Foods", slug="srijan-foods", is_active=True)
    other_company = Company(name="Rival Foods", slug="rival-foods", is_active=True)
    db.add_all([company, other_company])
    db.flush()

    super_profile = ProfileType(code="super_ceo", name="Super CEO", is_active=True)
    ceo_profile = ProfileType(code="company_ceo", name="Company CEO", is_active=True)
    chef_profile = ProfileType(code="chef", name="Chef", is_active=True)
    db.add_all([super_profile, ceo_profile, chef_profile])
    db.flush()

    password = auth_guard.hash_password("SafePassword9!")
    super_ceo = User(
        username="realtime_super",
        email="super@example.test",
        hashed_password=password,
        role="super_ceo",
        is_active=True,
        is_super_ceo=True,
        first_name="Sujit",
        phone="+919000000001",
        last_name="Singh",
    )
    company_ceo = User(
        username="realtime_ceo",
        email="ceo@example.test",
        hashed_password=password,
        role="company_ceo",
        is_active=True,
        is_company_ceo=True,
        company_id=company.id,
        current_company_id=company.id,
        first_name="Nita",
        phone="+919000000002",
        last_name="Rao",
    )
    other_ceo = User(
        username="rival_ceo",
        email="rival@example.test",
        hashed_password=password,
        role="company_ceo",
        is_active=True,
        is_company_ceo=True,
        company_id=other_company.id,
        current_company_id=other_company.id,
        first_name="Ravi",
        phone="+919000000003",
        last_name="Kumar",
    )
    chef = User(
        username="realtime_chef",
        email="chef@example.test",
        hashed_password=password,
        role="chef",
        is_active=True,
        company_id=company.id,
        current_company_id=company.id,
        first_name="Asha",
        phone="+919000000004",
        last_name="Menon",
    )
    inactive = User(
        username="realtime_inactive",
        email="inactive@example.test",
        hashed_password=password,
        role="company_ceo",
        is_active=False,
        company_id=company.id,
        first_name="Ex",
        phone="+919000000005",
        last_name="Ceo",
    )
    db.add_all([super_ceo, company_ceo, other_ceo, chef, inactive])
    db.commit()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_super_admin] = lambda: super_ceo
    connection_manager.theme_connections.clear()

    context = {
        "db": db,
        "company": company,
        "other_company": other_company,
        "profiles": {"super_ceo": super_profile, "company_ceo": ceo_profile, "chef": chef_profile},
        "users": {
            "super_ceo": super_ceo,
            "company_ceo": company_ceo,
            "other_ceo": other_ceo,
            "chef": chef,
            "inactive": inactive,
        },
    }
    with TestClient(app) as client:
        yield client, context
    app.dependency_overrides.clear()
    connection_manager.theme_connections.clear()
    db.close()
    engine.dispose()


def _draft_version(db: Session, profile: ProfileType, company_id: int | None, tokens: dict) -> tuple[Theme, ThemeVersion]:
    theme = Theme(
        profile_type_id=profile.id,
        company_id=company_id,
        name=f"{profile.code}-theme-{company_id}",
        slug=f"{profile.code}-theme-{company_id}",
        status="draft",
    )
    db.add(theme)
    db.flush()
    version = ThemeVersion(
        theme_id=theme.id,
        version_number=1,
        status="draft",
        tokens=tokens,
        schema_version="1.0",
        contrast_report=check_contrast(tokens),
    )
    db.add(version)
    db.commit()
    return theme, version


# --- WebSocket authentication -------------------------------------------------

def test_theme_socket_rejects_missing_token(realtime_context):
    client, _ = realtime_context
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/api/ws/theme-updates"):
            pass
    assert error.value.code == 4401


def test_theme_socket_rejects_invalid_token(realtime_context):
    client, _ = realtime_context
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/api/ws/theme-updates?token=not-a-jwt"):
            pass
    assert error.value.code == 4401


def test_theme_socket_rejects_inactive_user(realtime_context):
    client, context = realtime_context
    token = _token(context["users"]["inactive"])
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"/api/ws/theme-updates?token={token}"):
            pass
    assert error.value.code == 4403


def test_theme_socket_accepts_valid_token_and_answers_ping(realtime_context):
    client, context = realtime_context
    token = _token(context["users"]["company_ceo"])
    with client.websocket_connect(f"/api/ws/theme-updates?token={token}") as socket:
        socket.send_json({"type": "ping"})
        assert socket.receive_json()["type"] == "pong"


def test_theme_socket_derives_profile_type_and_company_scope(realtime_context):
    client, context = realtime_context
    token = _token(context["users"]["company_ceo"])
    with client.websocket_connect(f"/api/ws/theme-updates?token={token}"):
        subscriber = next(iter(connection_manager.theme_connections.values()))
        assert subscriber.user_id == context["users"]["company_ceo"].id
        assert subscriber.profile_type_id == context["profiles"]["company_ceo"].id
        assert subscriber.company_id == context["company"].id


def test_super_ceo_socket_has_no_company_scope(realtime_context):
    client, context = realtime_context
    token = _token(context["users"]["super_ceo"])
    with client.websocket_connect(f"/api/ws/theme-updates?token={token}"):
        subscriber = next(iter(connection_manager.theme_connections.values()))
        assert subscriber.profile_type_id == context["profiles"]["super_ceo"].id
        assert subscriber.company_id is None


def test_socket_is_unregistered_on_disconnect(realtime_context):
    client, context = realtime_context
    token = _token(context["users"]["chef"])
    with client.websocket_connect(f"/api/ws/theme-updates?token={token}") as socket:
        socket.send_json({"type": "ping"})
        socket.receive_json()
        assert connection_manager.theme_connection_count() == 1
    for _ in range(50):
        if connection_manager.theme_connection_count() == 0:
            break
        time.sleep(0.02)
    assert connection_manager.theme_connection_count() == 0


# --- Scoped broadcast ---------------------------------------------------------

class _RecordingSocket:
    def __init__(self):
        self.messages = []

    async def send_json(self, payload):
        self.messages.append(payload)


def _register(socket, **kwargs):
    connection_manager.theme_connections[socket] = ThemeSubscriber(**kwargs)


def test_company_scoped_event_reaches_only_matching_company(realtime_context):
    _, _ = realtime_context
    matching, other_company, other_profile = _RecordingSocket(), _RecordingSocket(), _RecordingSocket()
    _register(matching, user_id=1, profile_type_id=2, company_id=10)
    _register(other_company, user_id=2, profile_type_id=2, company_id=11)
    _register(other_profile, user_id=3, profile_type_id=3, company_id=10)

    event = {"event": "theme.published", "profile_type_id": 2, "company_id": 10}
    assert asyncio.run(connection_manager.broadcast_theme_event(event)) == 1
    assert matching.messages == [event]
    assert other_company.messages == []
    assert other_profile.messages == []


def test_platform_event_reaches_every_company_for_that_profile(realtime_context):
    _, _ = realtime_context
    company_scoped, platform_scoped, other_profile = _RecordingSocket(), _RecordingSocket(), _RecordingSocket()
    _register(company_scoped, user_id=1, profile_type_id=2, company_id=10)
    _register(platform_scoped, user_id=2, profile_type_id=2, company_id=None)
    _register(other_profile, user_id=3, profile_type_id=9, company_id=None)

    event = {"event": "theme.published", "profile_type_id": 2, "company_id": None}
    assert asyncio.run(connection_manager.broadcast_theme_event(event)) == 2
    assert company_scoped.messages == [event]
    assert platform_scoped.messages == [event]
    assert other_profile.messages == []


def test_broken_socket_is_dropped_without_failing_broadcast(realtime_context):
    _, _ = realtime_context

    class _BrokenSocket(_RecordingSocket):
        async def send_json(self, payload):
            raise RuntimeError("socket closed")

    healthy, broken = _RecordingSocket(), _BrokenSocket()
    _register(healthy, user_id=1, profile_type_id=2, company_id=10)
    _register(broken, user_id=2, profile_type_id=2, company_id=10)

    sent = asyncio.run(connection_manager.broadcast_theme_event({"profile_type_id": 2, "company_id": 10}))
    assert sent == 1
    assert broken not in connection_manager.theme_connections


# --- Published event payload --------------------------------------------------

def test_publish_emits_theme_published_event_to_scoped_socket(realtime_context):
    client, context = realtime_context
    db = context["db"]
    tokens = default_tokens()
    theme, version = _draft_version(db, context["profiles"]["company_ceo"], context["company"].id, tokens)

    ceo_token = _token(context["users"]["company_ceo"])
    rival_token = _token(context["users"]["other_ceo"])
    with client.websocket_connect(f"/api/ws/theme-updates?token={ceo_token}") as socket, \
            client.websocket_connect(f"/api/ws/theme-updates?token={rival_token}") as rival_socket:
        response = client.post(f"/api/super-ceo/themes/{theme.id}/versions/{version.id}/publish")
        assert response.status_code == 200
        event = socket.receive_json()
        rival_socket.send_json({"type": "ping"})
        assert rival_socket.receive_json()["type"] == "pong"

    assert event["event"] == "theme.published"
    assert event["event_version"] == 1
    assert event["theme_id"] == theme.id
    assert event["profile_type_id"] == context["profiles"]["company_ceo"].id
    assert event["version_id"] == version.id
    assert event["company_id"] == context["company"].id
    assert event["occurred_at"]
    assert set(event) == {
        "event",
        "event_version",
        "theme_id",
        "profile_type_id",
        "version_id",
        "company_id",
        "occurred_at",
        "changed_token_paths",
    }


def test_published_event_reports_changed_token_paths(realtime_context):
    client, context = realtime_context
    db = context["db"]
    theme, first = _draft_version(db, context["profiles"]["chef"], context["company"].id, default_tokens())
    client.post(f"/api/super-ceo/themes/{theme.id}/versions/{first.id}/publish")

    updated = default_tokens()
    updated["color"]["semantic"]["primary"] = "#4F46E5"
    second = ThemeVersion(
        theme_id=theme.id,
        version_number=2,
        status="draft",
        tokens=updated,
        schema_version="1.0",
        contrast_report=check_contrast(updated),
    )
    db.add(second)
    db.commit()

    token = _token(context["users"]["chef"])
    with client.websocket_connect(f"/api/ws/theme-updates?token={token}") as socket:
        assert client.post(f"/api/super-ceo/themes/{theme.id}/versions/{second.id}/publish").status_code == 200
        event = socket.receive_json()
    assert event["changed_token_paths"] == ["color.semantic.primary"]


def test_first_publish_reports_every_token_path(realtime_context):
    client, context = realtime_context
    db = context["db"]
    tokens = default_tokens()
    theme, version = _draft_version(db, context["profiles"]["chef"], None, tokens)
    token = _token(context["users"]["chef"])
    with client.websocket_connect(f"/api/ws/theme-updates?token={token}") as socket:
        assert client.post(f"/api/super-ceo/themes/{theme.id}/versions/{version.id}/publish").status_code == 200
        event = socket.receive_json()
    assert event["changed_token_paths"] == changed_token_paths(None, tokens)
    assert "color.semantic.primary" in event["changed_token_paths"]


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        (None, {"a": 1}, ["a"]),
        ("not-a-mapping", {"a": 1}, ["a"]),
        ({"a": {"b": 1}}, {"a": {"b": 2}}, ["a.b"]),
        ({"a": 1, "b": 2}, {"a": 1}, ["b"]),
        ({"a": 1}, None, ["a"]),
    ],
)
def test_changed_token_paths_is_defensive(previous, current, expected):
    assert changed_token_paths(previous, current) == expected


# --- Company CEO self-profile -------------------------------------------------

def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


def test_company_ceo_reads_own_profile_with_company_scope(realtime_context):
    client, context = realtime_context
    app.dependency_overrides.pop(resolve_profile_actor, None)
    response = client.get("/api/super-ceo/profile", headers=_auth(context["users"]["company_ceo"]))
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["profile"]["username"] == "realtime_ceo"
    assert body["meta"]["scope"]["level"] == "company"
    assert body["meta"]["scope"]["company_id"] == context["company"].id


def test_company_ceo_stats_are_scoped_to_current_company(realtime_context):
    client, context = realtime_context
    response = client.get("/api/super-ceo/profile", headers=_auth(context["users"]["company_ceo"]))
    stats = response.json()["data"]["profile"]["stats"]
    assert stats["companies_overseen"] == 1
    assert stats["team_size"] == 2


def test_super_ceo_profile_keeps_system_scope_and_stats(realtime_context):
    client, context = realtime_context
    db = context["db"]
    expected_companies = db.query(Company).filter(
        Company.is_active.is_(True), Company.is_deleted.is_(False)
    ).count()
    expected_team = db.query(User).filter(User.is_active.is_(True), User.company_id.is_not(None)).count()
    response = client.get("/api/super-ceo/profile", headers=_auth(context["users"]["super_ceo"]))
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["scope"]["level"] == "system"
    assert body["data"]["profile"]["stats"]["companies_overseen"] == expected_companies
    assert body["data"]["profile"]["stats"]["team_size"] == expected_team
    assert expected_companies >= 2


def test_company_ceo_updates_own_profile_and_is_audited(realtime_context):
    client, context = realtime_context
    actor = context["users"]["company_ceo"]
    response = client.put(
        "/api/super-ceo/profile",
        json={"display_name": "Chief Nita"},
        headers=_auth(actor),
    )
    assert response.status_code == 200
    assert response.json()["data"]["profile"]["display_name"] == "Chief Nita"
    audit = (
        context["db"].query(CeoAuditLog)
        .filter(CeoAuditLog.user_id == actor.id, CeoAuditLog.action == "profile.updated")
        .one()
    )
    assert audit.request_meta["company_id"] == context["company"].id
    assert audit.request_meta["changes"]["display_name"]["new"] == "Chief Nita"


def test_company_ceo_activity_lists_only_own_entries(realtime_context):
    client, context = realtime_context
    client.put("/api/super-ceo/profile", json={"bio": "Leading the kitchen."}, headers=_auth(context["users"]["company_ceo"]))
    client.put("/api/super-ceo/profile", json={"bio": "Super entry."}, headers=_auth(context["users"]["super_ceo"]))
    response = client.get("/api/super-ceo/profile/activity", headers=_auth(context["users"]["company_ceo"]))
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1


def test_company_ceo_logout_revokes_own_token(realtime_context):
    from app.services.token_revocation import is_token_revoked

    client, context = realtime_context
    token = _token(context["users"]["company_ceo"])
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/super-ceo/profile/logout", headers=headers).status_code == 200
    assert is_token_revoked(token)
    assert client.get("/api/super-ceo/profile", headers=headers).status_code == 401


def _published_theme(db, profile, name, color, company_id=None):
    tokens = default_tokens()
    tokens["color"]["semantic"]["primary"] = color
    theme = Theme(
        profile_type_id=profile.id,
        company_id=company_id,
        name=name,
        slug=name.lower().replace(" ", "-"),
        status="published",
        is_default=True,
    )
    db.add(theme)
    db.flush()
    version = ThemeVersion(
        theme_id=theme.id,
        version_number=1,
        status="published",
        tokens=tokens,
        schema_version="1.0",
        contrast_report=check_contrast(tokens),
    )
    db.add(version)
    db.flush()
    theme.current_version_id = version.id
    return theme


def test_theme_resolution_prefers_matching_company_and_never_leaks_other_company(realtime_context):
    _, context = realtime_context
    db = context["db"]
    profile = context["profiles"]["company_ceo"]
    _published_theme(db, profile, "Platform CEO", "#8B5E17")
    _published_theme(db, profile, "Srijan CEO", "#2563EB", context["company"].id)
    _published_theme(db, profile, "Rival CEO", "#DC2626", context["other_company"].id)
    db.commit()

    own = resolve_theme(db, context["users"]["company_ceo"], "company_ceo")
    rival = resolve_theme(db, context["users"]["other_ceo"], "company_ceo")

    assert own["tokens"]["color"]["semantic"]["primary"] == "#2563EB"
    assert rival["tokens"]["color"]["semantic"]["primary"] == "#DC2626"


def test_theme_resolution_ignores_assignment_to_unpublished_theme(realtime_context):
    _, context = realtime_context
    db = context["db"]
    profile = context["profiles"]["company_ceo"]
    published = _published_theme(db, profile, "Published CEO", "#8B5E17")
    draft = Theme(profile_type_id=profile.id, name="Draft CEO", slug="draft-ceo", status="draft")
    db.add(draft)
    db.flush()
    draft_tokens = default_tokens()
    draft_tokens["color"]["semantic"]["primary"] = "#DC2626"
    draft_version = ThemeVersion(
        theme_id=draft.id,
        version_number=1,
        status="draft",
        tokens=draft_tokens,
        schema_version="1.0",
        contrast_report=check_contrast(draft_tokens),
    )
    db.add(draft_version)
    db.flush()
    draft.current_version_id = draft_version.id
    db.add(ThemeAssignment(
        theme_id=draft.id,
        profile_type_id=profile.id,
        user_id=context["users"]["company_ceo"].id,
        priority=100,
        is_active=True,
    ))
    db.commit()

    resolved = resolve_theme(db, context["users"]["company_ceo"], "company_ceo")

    assert resolved["source"] == f"theme:{published.id}"
    assert resolved["tokens"]["color"]["semantic"]["primary"] == "#8B5E17"


def test_profile_update_rejects_duplicate_email(realtime_context):
    client, context = realtime_context
    context["users"]["other_ceo"].email = "taken@example.com"
    context["db"].commit()
    actor = context["users"]["company_ceo"]
    response = client.put(
        "/api/super-ceo/profile",
        json={"email": "taken@example.com"},
        headers=_auth(actor),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email address is already in use"
    assert actor.email == "ceo@example.test"


def test_company_ceo_uploads_personal_profile_photo_to_own_folder(realtime_context, monkeypatch, tmp_path):
    client, context = realtime_context
    actor = context["users"]["company_ceo"]
    monkeypatch.setattr("app.services.file_storage.UPLOAD_ROOT", tmp_path)
    image = io.BytesIO()
    Image.new("RGB", (12, 12), "#8B5E17").save(image, format="PNG")

    response = client.post(
        "/api/uploads/profile-photo",
        files={"file": ("profile.png", image.getvalue(), "image/png")},
        headers=_auth(actor),
    )

    assert response.status_code == 200
    asset = response.json()["data"]
    assert asset["url"].startswith(f"/uploads/profile-photos/{actor.id}/")
    assert (tmp_path / "profile-photos" / str(actor.id) / asset["filename"]).is_file()
    audit = context["db"].query(CeoAuditLog).filter(
        CeoAuditLog.user_id == actor.id,
        CeoAuditLog.action == "upload.profile-photos",
    ).one()
    assert audit.request_meta["asset"]["url"] == asset["url"]


def test_profile_requires_authentication(realtime_context):
    client, _ = realtime_context
    assert client.get("/api/super-ceo/profile").status_code == 403


def test_theme_socket_rejects_revoked_token(realtime_context):
    from app.services.token_revocation import revoke_token

    client, context = realtime_context
    token = _token(context["users"]["company_ceo"])
    revoke_token(token)
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"/api/ws/theme-updates?token={token}"):
            pass
    assert error.value.code == 4401
