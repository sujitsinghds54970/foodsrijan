import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProfileType, User
from app.models.ceo import CeoAuditLog
from app.models.themes import Theme, ThemeAssignment, ThemeVersion
from app.services.contrast import check_contrast
from app.services.theme_tokens import default_tokens, merge_tokens, validate_tokens
from app.services.theme_resolver import resolve_theme
from app.services.websocket_service import publish_theme_event
from app.utils.auth_system import require_super_admin

router = APIRouter(prefix="/super-ceo/themes", tags=["Super CEO Themes"])
static_router = APIRouter(prefix="/super-ceo/themes", tags=["Super CEO Themes"])


class ProfileTypeInput(BaseModel):
    key: str = Field(min_length=2, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(min_length=1, max_length=150)
    description: str | None = None


class ThemeInput(BaseModel):
    profile_type_key: str
    name: str
    slug: str | None = None
    company_id: int | None = None
    brand_id: int | None = None
    parent_theme_id: int | None = None
    is_default: bool = False


class VersionInput(BaseModel):
    tokens: dict[str, Any]
    change_summary: str | None = None
    schema_version: str = "1.0"


class AssignmentInput(BaseModel):
    profile_type_id: int
    user_id: int | None = None
    role_id: int | None = None
    company_id: int | None = None
    brand_id: int | None = None
    branch_id: int | None = None
    department_id: int | None = None
    priority: int = 0
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class ImportInput(BaseModel):
    theme: ThemeInput
    tokens: dict[str, Any]


def _audit(db: Session, actor: User, action: str, request: Request, status: int, meta: dict[str, Any]) -> None:
    previous = db.query(CeoAuditLog).order_by(CeoAuditLog.id.desc()).first()
    previous_signature = previous.signature if previous else None
    payload = json.dumps({"action": action, "actor": actor.id, "meta": meta, "previous": previous_signature}, sort_keys=True, default=str)
    signature = hashlib.sha256(payload.encode()).hexdigest()
    db.add(CeoAuditLog(user_id=actor.id, action=action, http_method=request.method, endpoint=request.url.path, response_status=status, request_meta=meta, previous_signature=previous_signature, signature=signature))


def _profile_payload(profile: ProfileType) -> dict[str, Any]:
    return {"id": profile.id, "key": profile.code, "display_name": profile.name, "description": profile.description, "is_system": profile.code in SYSTEM_PROFILE_KEYS, "is_active": profile.is_active, "created_at": profile.created_at.isoformat() if profile.created_at else None}


SYSTEM_PROFILE_KEYS = {
    "super_ceo", "company_ceo", "branch_manager", "chef", "kitchen_manager", "inventory_manager",
    "cashier", "customer_service", "delivery_partner", "customer", "supplier", "investor",
    "department_head", "brand_director", "regional_manager", "admin",
}


@router.get("/profile-types")
def list_profile_types(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return {"profile_types": [_profile_payload(row) for row in db.query(ProfileType).filter(ProfileType.is_active.is_(True)).order_by(ProfileType.name).all()]}


@router.get("/profile-types/{key}")
def get_profile_type(key: str, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    row = db.query(ProfileType).filter(ProfileType.code == key).first()
    if not row:
        raise HTTPException(404, "Profile type not found")
    return _profile_payload(row)


@router.post("/profile-types", status_code=201)
def create_profile_type(payload: ProfileTypeInput, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    if db.query(ProfileType).filter(ProfileType.code == payload.key).first():
        raise HTTPException(409, "Profile type key already exists")
    row = ProfileType(code=payload.key, name=payload.display_name, description=payload.description)
    db.add(row)
    db.flush()
    _audit(db, actor, "theme.profile_type.created", request, 201, {"profile_type_id": row.id, "key": row.code})
    db.commit()
    return _profile_payload(row)


@router.put("/profile-types/{key}")
def update_profile_type(key: str, payload: ProfileTypeInput, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    row = db.query(ProfileType).filter(ProfileType.code == key).first()
    if not row:
        raise HTTPException(404, "Profile type not found")
    if row.code in SYSTEM_PROFILE_KEYS and payload.key != row.code:
        raise HTTPException(400, "System profile type keys are immutable")
    row.name, row.description = payload.display_name, payload.description
    _audit(db, actor, "theme.profile_type.updated", request, 200, {"profile_type_id": row.id})
    db.commit()
    return _profile_payload(row)


@router.delete("/profile-types/{key}", status_code=204)
def archive_profile_type(key: str, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    row = db.query(ProfileType).filter(ProfileType.code == key).first()
    if not row:
        raise HTTPException(404, "Profile type not found")
    if db.query(Theme).filter(Theme.profile_type_id == row.id, Theme.status != "archived").first():
        raise HTTPException(409, "Profile type has active themes")
    row.is_active = False
    _audit(db, actor, "theme.profile_type.archived", request, 204, {"profile_type_id": row.id})
    db.commit()
    return None


@static_router.get("/presets")
def presets(_: User = Depends(require_super_admin)):
    return {"presets": [
        {"id": "executive-gold", "name": "Executive Gold", "tokens": default_tokens()},
        {"id": "modern-minimal", "name": "Modern Minimal", "tokens": merge_tokens(default_tokens(), {"color": {"semantic": {"primary": "#4F46E5"}, "surface": {"default": "#F8FAFC", "panel": "#FFFFFF"}, "text": {"primary": "#111827", "secondary": "#475569"}}})},
        {"id": "warm-hospitality", "name": "Warm Hospitality", "tokens": merge_tokens(default_tokens(), {"color": {"semantic": {"primary": "#EA580C", "accent": "#FDBA74"}}})},
        {"id": "dark-command", "name": "Dark Command", "tokens": default_tokens()},
    ]}


@static_router.post("/presets/{preset_id}/clone", status_code=201)
def clone_preset(preset_id: str, payload: ThemeInput, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    available = {item["id"]: item for item in presets(actor)["presets"]}
    preset = available.get(preset_id)
    if not preset:
        raise HTTPException(404, "Preset not found")
    profile = db.query(ProfileType).filter(ProfileType.code == payload.profile_type_key).first()
    if not profile:
        raise HTTPException(404, "Profile type not found")
    theme = Theme(profile_type_id=profile.id, company_id=payload.company_id, brand_id=payload.brand_id, name=payload.name or preset["name"], slug=payload.slug or payload.name.lower().replace(" ", "-"), parent_theme_id=payload.parent_theme_id, is_default=payload.is_default, created_by=actor.id, updated_by=actor.id)
    db.add(theme)
    db.flush()
    version = ThemeVersion(theme_id=theme.id, version_number=1, status="draft", tokens=preset["tokens"], schema_version="1.0", contrast_report=check_contrast(preset["tokens"]), change_summary=f"Cloned preset: {preset['name']}", created_by=actor.id)
    db.add(version)
    _audit(db, actor, "theme.preset.cloned", request, 201, {"theme_id": theme.id, "preset_id": preset_id})
    db.commit()
    return _theme_payload(theme)


@static_router.post("/import", status_code=201)
def import_theme(payload: ImportInput, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    validation = validate_tokens(payload.tokens)
    if not validation["valid"]:
        raise HTTPException(422, {"validation": validation})
    profile = db.query(ProfileType).filter(ProfileType.code == payload.theme.profile_type_key).first()
    if not profile:
        raise HTTPException(404, "Profile type not found")
    theme = Theme(profile_type_id=profile.id, company_id=payload.theme.company_id, brand_id=payload.theme.brand_id, name=payload.theme.name, slug=payload.theme.slug or payload.theme.name.lower().replace(" ", "-"), created_by=actor.id, updated_by=actor.id)
    db.add(theme)
    db.flush()
    db.add(ThemeVersion(theme_id=theme.id, version_number=1, status="draft", tokens=payload.tokens, schema_version="1.0", contrast_report=check_contrast(payload.tokens), change_summary="Imported theme", created_by=actor.id))
    _audit(db, actor, "theme.imported", request, 201, {"theme_id": theme.id})
    db.commit()
    return _theme_payload(theme)


@router.get("")
def list_themes(profile_type_key: str | None = Query(None), status: str | None = Query(None), db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    query = db.query(Theme)
    if profile_type_key:
        query = query.join(ProfileType).filter(ProfileType.code == profile_type_key)
    if status:
        query = query.filter(Theme.status == status)
    return {"themes": [_theme_payload(theme) for theme in query.order_by(Theme.updated_at.desc()).all()]}


def _theme_payload(theme: Theme) -> dict[str, Any]:
    return {"id": theme.id, "profile_type_id": theme.profile_type_id, "profile_type_key": theme.profile_type.code if theme.profile_type else None, "company_id": theme.company_id, "brand_id": theme.brand_id, "name": theme.name, "slug": theme.slug, "status": theme.status, "is_default": theme.is_default, "current_version_id": theme.current_version_id, "created_at": theme.created_at.isoformat() if theme.created_at else None, "updated_at": theme.updated_at.isoformat() if theme.updated_at else None}


@router.post("", status_code=201)
def create_theme(payload: ThemeInput, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    profile = db.query(ProfileType).filter(ProfileType.code == payload.profile_type_key, ProfileType.is_active.is_(True)).first()
    if not profile:
        raise HTTPException(404, "Profile type not found")
    theme = Theme(profile_type_id=profile.id, company_id=payload.company_id, brand_id=payload.brand_id, name=payload.name, slug=payload.slug or payload.name.lower().replace(" ", "-"), parent_theme_id=payload.parent_theme_id, is_default=payload.is_default, created_by=actor.id, updated_by=actor.id)
    db.add(theme)
    db.flush()
    _audit(db, actor, "theme.created", request, 201, {"theme_id": theme.id})
    db.commit()
    return _theme_payload(theme)


@router.get("/{theme_id}")
def get_theme(theme_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    theme = db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(404, "Theme not found")
    return _theme_payload(theme)


@router.put("/{theme_id}")
def update_theme(theme_id: int, payload: ThemeInput, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    theme = db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(404, "Theme not found")
    theme.name, theme.slug, theme.company_id, theme.brand_id, theme.parent_theme_id, theme.updated_by = payload.name, payload.slug or theme.slug, payload.company_id, payload.brand_id, payload.parent_theme_id, actor.id
    _audit(db, actor, "theme.updated", request, 200, {"theme_id": theme_id})
    db.commit()
    return _theme_payload(theme)


@router.delete("/{theme_id}", status_code=204)
def archive_theme(theme_id: int, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    theme = db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(404, "Theme not found")
    theme.status, theme.updated_by = "archived", actor.id
    _audit(db, actor, "theme.archived", request, 204, {"theme_id": theme_id})
    db.commit()


@router.post("/{theme_id}/versions", status_code=201)
def save_version(theme_id: int, payload: VersionInput, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    theme = db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(404, "Theme not found")
    validation = validate_tokens(payload.tokens)
    if not validation["valid"]:
        raise HTTPException(422, {"validation": validation})
    number = (db.query(ThemeVersion).filter(ThemeVersion.theme_id == theme.id).order_by(ThemeVersion.version_number.desc()).first().version_number if theme.versions else 0) + 1
    version = ThemeVersion(theme_id=theme.id, version_number=number, tokens=payload.tokens, schema_version=payload.schema_version, contrast_report=check_contrast(payload.tokens), change_summary=payload.change_summary, created_by=actor.id)
    db.add(version)
    _audit(db, actor, "theme.version.draft_saved", request, 201, {"theme_id": theme.id, "version_number": number})
    db.commit()
    db.refresh(version)
    return _version_payload(version)


def _version_payload(version: ThemeVersion) -> dict[str, Any]:
    return {"id": version.id, "theme_id": version.theme_id, "version_number": version.version_number, "status": version.status, "tokens": version.tokens, "schema_version": version.schema_version, "contrast_report": version.contrast_report, "change_summary": version.change_summary, "created_at": version.created_at.isoformat() if version.created_at else None, "published_at": version.published_at.isoformat() if version.published_at else None}


@router.get("/{theme_id}/versions")
def list_versions(theme_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return {"versions": [_version_payload(row) for row in db.query(ThemeVersion).filter(ThemeVersion.theme_id == theme_id).order_by(ThemeVersion.version_number.desc()).all()]}


@router.get("/{theme_id}/versions/{version_id}")
def get_version(theme_id: int, version_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    version = db.get(ThemeVersion, version_id)
    if not version or version.theme_id != theme_id:
        raise HTTPException(404, "Theme version not found")
    return _version_payload(version)


@router.get("/{theme_id}/versions/{version_id}/diff")
def version_diff(theme_id: int, version_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    versions = db.query(ThemeVersion).filter(ThemeVersion.theme_id == theme_id, ThemeVersion.version_number <= db.get(ThemeVersion, version_id).version_number).order_by(ThemeVersion.version_number.desc()).limit(2).all()
    if not versions or versions[0].id != version_id:
        raise HTTPException(404, "Theme version not found")
    current = versions[0].tokens
    previous = versions[1].tokens if len(versions) > 1 else {}
    return {"theme_id": theme_id, "version_id": version_id, "changed_token_paths": changed_token_paths(previous, current)}


def _flatten(document: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    output = {}
    for key, value in document.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            output.update(_flatten(value, path))
        else:
            output[path] = value
    return output


def _safe_flatten(document: Any) -> dict[str, Any]:
    return _flatten(document) if isinstance(document, dict) else {}


def changed_token_paths(previous: Any, current: Any) -> list[str]:
    """Token paths that differ between two token documents.

    Tolerates missing or non-mapping token documents so realtime metadata can
    never break a publish.
    """
    previous_flat, current_flat = _safe_flatten(previous), _safe_flatten(current)
    return sorted(
        {path for path, value in current_flat.items() if previous_flat.get(path) != value}
        | {path for path in previous_flat if path not in current_flat}
    )


@router.post("/{theme_id}/versions/{version_id}/publish")
def publish_version(theme_id: int, version_id: int, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    theme, version = db.get(Theme, theme_id), db.get(ThemeVersion, version_id)
    if not theme or not version or version.theme_id != theme.id:
        raise HTTPException(404, "Theme version not found")
    report = check_contrast(version.tokens)
    if not report["passed"]:
        raise HTTPException(422, {"message": "Contrast validation failed", "contrast_report": report})
    previous_tokens = _previously_live_tokens(db, theme, version)
    db.query(ThemeVersion).filter(ThemeVersion.theme_id == theme.id, ThemeVersion.status == "published").update({"status": "superseded"})
    version.status, version.published_by, version.published_at = "published", actor.id, datetime.utcnow()
    theme.current_version_id, theme.status, theme.updated_by = version.id, "published", actor.id
    _audit(db, actor, "theme.version.published", request, 200, {"theme_id": theme.id, "version_id": version.id})
    db.commit()
    publish_theme_event(theme_published_event(theme, version, previous_tokens))
    return _version_payload(version)


def _previously_live_tokens(db: Session, theme: Theme, version: ThemeVersion) -> Any:
    """Tokens of the version this publish replaces, when one exists."""
    previous = None
    if theme.current_version_id and theme.current_version_id != version.id:
        previous = db.get(ThemeVersion, theme.current_version_id)
    if previous is None:
        previous = (
            db.query(ThemeVersion)
            .filter(ThemeVersion.theme_id == theme.id, ThemeVersion.id != version.id, ThemeVersion.status == "published")
            .order_by(ThemeVersion.version_number.desc())
            .first()
        )
    return previous.tokens if previous is not None else None


def theme_published_event(theme: Theme, version: ThemeVersion, previous_tokens: Any = None) -> dict[str, Any]:
    return {
        "event": "theme.published",
        "event_version": 1,
        "theme_id": theme.id,
        "profile_type_id": theme.profile_type_id,
        "version_id": version.id,
        "company_id": theme.company_id,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "changed_token_paths": changed_token_paths(previous_tokens, version.tokens),
    }


@router.post("/{theme_id}/versions/{version_id}/rollback")
def rollback_version(theme_id: int, version_id: int, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    theme, source = db.get(Theme, theme_id), db.get(ThemeVersion, version_id)
    if not theme or not source or source.theme_id != theme.id:
        raise HTTPException(404, "Theme version not found")
    number = max((version.version_number for version in theme.versions), default=0) + 1
    version = ThemeVersion(theme_id=theme.id, version_number=number, status="published", tokens=source.tokens, schema_version=source.schema_version, contrast_report=check_contrast(source.tokens), change_summary=f"Rollback to version {source.version_number}", created_by=actor.id, published_by=actor.id, published_at=datetime.utcnow(), rolled_back_from_version_id=source.id)
    db.add(version)
    db.flush()
    db.query(ThemeVersion).filter(ThemeVersion.theme_id == theme.id, ThemeVersion.id != version.id, ThemeVersion.status == "published").update({"status": "rolled_back"})
    theme.current_version_id, theme.status = version.id, "published"
    _audit(db, actor, "theme.version.rolled_back", request, 200, {"theme_id": theme.id, "source_version_id": source.id, "new_version_id": version.id})
    db.commit()
    return _version_payload(version)


@router.post("/{theme_id}/validate")
def validate_theme(theme_id: int, payload: VersionInput, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    if not db.get(Theme, theme_id):
        raise HTTPException(404, "Theme not found")
    schema = validate_tokens(payload.tokens)
    contrast = check_contrast(payload.tokens)
    return {"valid": schema["valid"] and contrast["passed"], "schema": schema, "contrast": contrast}


@router.post("/{theme_id}/assign", status_code=201)
def assign_theme(theme_id: int, payload: AssignmentInput, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    theme = db.get(Theme, theme_id)
    if not theme or theme.profile_type_id != payload.profile_type_id:
        raise HTTPException(404, "Theme not found for profile type")
    assignment = ThemeAssignment(theme_id=theme_id, created_by=actor.id, **payload.dict())
    db.add(assignment)
    _audit(db, actor, "theme.assignment.created", request, 201, {"theme_id": theme_id, "assignment_id": assignment.id})
    db.commit()
    db.refresh(assignment)
    return {"id": assignment.id, "theme_id": assignment.theme_id, "priority": assignment.priority, "is_active": assignment.is_active}


@static_router.get("/assignments")
def list_assignments(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return {"assignments": [{"id": row.id, "theme_id": row.theme_id, "profile_type_id": row.profile_type_id, "user_id": row.user_id, "role_id": row.role_id, "company_id": row.company_id, "brand_id": row.brand_id, "priority": row.priority, "is_active": row.is_active} for row in db.query(ThemeAssignment).order_by(ThemeAssignment.priority.desc()).all()]}


@static_router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: int, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    row = db.get(ThemeAssignment, assignment_id)
    if not row:
        raise HTTPException(404, "Assignment not found")
    row.is_active = False
    _audit(db, actor, "theme.assignment.removed", request, 204, {"assignment_id": assignment_id})
    db.commit()


@router.get("/{theme_id}/export")
def export_theme(theme_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    theme = db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(404, "Theme not found")
    version = db.get(ThemeVersion, theme.current_version_id) if theme.current_version_id else None
    return {"schema_version": version.schema_version if version else "1.0", "theme": _theme_payload(theme), "tokens": version.tokens if version else default_tokens()}


@static_router.get("/resolved")
def resolved_theme(db: Session = Depends(get_db), current_user: User = Depends(require_super_admin)):
    profile_key = "super_ceo" if getattr(current_user, "is_super_ceo", False) else str(getattr(current_user, "role", "")).lower()
    return {"theme": resolve_theme(db, current_user, profile_key), "profile_type": profile_key, "refresh_after_seconds": 60}
