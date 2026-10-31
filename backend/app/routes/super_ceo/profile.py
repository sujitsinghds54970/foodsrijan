from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, User
from app.models.ceo import CeoAuditLog
from app.services.audit_service import write_ceo_audit
from app.services.executive_metrics import ResolvedScope, envelope
from app.services.authority_integrity import canonical_super_ceo_count
from app.services.token_revocation import revoke_token
from app.utils.auth_system import get_current_user, is_super_ceo_user, security


router = APIRouter(prefix="/super-ceo/profile", tags=["Super CEO Profile"])
SYSTEM_SCOPE = ResolvedScope("system", ())


def resolve_profile_actor(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Authenticated owner of the requested profile.

    Every profile endpoint acts on the caller's own record, so any active
    authenticated user is allowed. Super CEO callers keep the canonical
    authority integrity guarantee applied to the rest of their surface.
    """
    if is_super_ceo_user(current_user) and canonical_super_ceo_count(db) != 1:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Canonical Super CEO integrity check failed",
        )
    return current_user


def _actor_company_id(user: User) -> int | None:
    return getattr(user, "current_company_id", None) or getattr(user, "company_id", None)


def _profile_scope(user: User) -> ResolvedScope:
    if is_super_ceo_user(user):
        return SYSTEM_SCOPE
    company_id = _actor_company_id(user)
    if company_id:
        return ResolvedScope("company", (company_id,), company_id=company_id)
    return ResolvedScope("user", ())


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9][0-9\s-]{7,20}$")
    bio: str | None = Field(default=None, max_length=2000)
    profile_photo_url: str | None = Field(default=None, max_length=2048)
    cover_photo_url: str | None = Field(default=None, max_length=2048)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=32)
    location_city: str | None = Field(default=None, max_length=120)
    location_state: str | None = Field(default=None, max_length=120)
    location_country: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, pattern=r"^\+?[0-9][0-9\s-]{7,20}$")
    assistant_name: str | None = Field(default=None, max_length=150)
    assistant_email: EmailStr | None = None
    assistant_phone: str | None = Field(default=None, pattern=r"^\+?[0-9][0-9\s-]{7,20}$")
    preferred_contact_method: Literal["email", "phone", "whatsapp"] | None = None
    qualifications: list[dict[str, Any]] | None = None
    certifications: list[dict[str, Any]] | None = None
    achievements: list[dict[str, Any]] | None = None
    preferences: dict[str, Any] | None = None
    recovery_email: EmailStr | None = None
    recovery_phone: str | None = Field(default=None, pattern=r"^\+?[0-9][0-9\s-]{7,20}$")

    @field_validator("profile_photo_url", "cover_photo_url")
    @classmethod
    def validate_asset_url(cls, value: str | None) -> str | None:
        if value and not (
            value.startswith("http://")
            or value.startswith("https://")
            or value.startswith("/uploads/")
        ):
            raise ValueError("URL must use http, https, or an uploaded asset path")
        return value


PROFILE_FIELDS = tuple(ProfileUpdate.model_fields)


def _profile_stats(db: Session, user: User) -> tuple[int, int]:
    """Companies overseen and team size for the caller's own scope."""
    if is_super_ceo_user(user):
        companies = db.query(Company).filter(
            Company.is_active.is_(True),
            Company.is_deleted.is_(False),
        ).count()
        team_size = db.query(User).filter(User.is_active.is_(True), User.company_id.is_not(None)).count()
        return companies, team_size

    company_id = _actor_company_id(user)
    if not company_id:
        return 0, 0
    companies = db.query(Company).filter(
        Company.id == company_id,
        Company.is_active.is_(True),
        Company.is_deleted.is_(False),
    ).count()
    team_size = db.query(User).filter(
        User.is_active.is_(True),
        or_(User.company_id == company_id, User.current_company_id == company_id),
    ).count()
    return companies, team_size


def _serialize_profile(db: Session, user: User) -> dict[str, Any]:
    companies, team_size = _profile_stats(db, user)
    decisions = db.query(CeoAuditLog).filter(CeoAuditLog.user_id == user.id).count()
    created_at = user.created_at or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    values = {field: getattr(user, field, None) for field in PROFILE_FIELDS}
    values["date_of_birth"] = user.date_of_birth.isoformat() if user.date_of_birth else None
    values.update(
        {
            "id": user.id,
            "username": user.username,
            "is_verified": True,
            "stats": {
                "companies_overseen": companies,
                "decisions_made": decisions,
                "team_size": team_size,
                "tenure_days": max(0, (datetime.now(timezone.utc) - created_at).days),
            },
        }
    )
    return values


@router.get("")
def get_profile(
    db: Session = Depends(get_db),
    actor: User = Depends(resolve_profile_actor),
):
    return envelope(
        {"profile": _serialize_profile(db, actor)},
        _profile_scope(actor),
        sources=["users", "companies", "ceo_audit_logs"],
    )


@router.put("")
def update_profile(
    payload: ProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(resolve_profile_actor),
):
    submitted = payload.model_dump(exclude_unset=True)
    requested_email = submitted.get("email")
    if requested_email and requested_email != actor.email:
        duplicate = db.query(User.id).filter(User.email == requested_email, User.id != actor.id).first()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email address is already in use")
    changes: dict[str, dict[str, Any]] = {}
    for field, value in submitted.items():
        old_value = getattr(actor, field)
        if old_value != value:
            changes[field] = {"old": old_value, "new": value}
            setattr(actor, field, value)
    if changes:
        write_ceo_audit(
            db,
            actor,
            request,
            "profile.updated",
            {"changes": changes, "user_id": actor.id, "company_id": _actor_company_id(actor)},
        )
        db.commit()
        db.refresh(actor)
    return envelope(
        {"profile": _serialize_profile(db, actor), "updated_fields": list(changes)},
        _profile_scope(actor),
        sources=["users", "companies", "ceo_audit_logs"],
    )


@router.get("/activity")
def get_profile_activity(
    action: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: User = Depends(resolve_profile_actor),
):
    query = db.query(CeoAuditLog).filter(CeoAuditLog.user_id == actor.id)
    if action:
        query = query.filter(CeoAuditLog.action == action)
    total = query.count()
    rows = query.order_by(CeoAuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    activity = [
        {
            "id": row.id,
            "action": row.action,
            "resource": row.endpoint,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
            "changes": row.request_meta,
        }
        for row in rows
    ]
    return envelope(
        {"activity": activity, "total": total, "page": page, "page_size": page_size},
        _profile_scope(actor),
        sources=["ceo_audit_logs"],
    )


@router.post("/logout")
def logout_profile(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    actor: User = Depends(resolve_profile_actor),
):
    write_ceo_audit(
        db,
        actor,
        request,
        "profile.logout",
        {"user_id": actor.id, "company_id": _actor_company_id(actor)},
    )
    db.commit()
    revoke_token(credentials.credentials)
    return envelope({"logged_out": True}, _profile_scope(actor), sources=["ceo_audit_logs"])
