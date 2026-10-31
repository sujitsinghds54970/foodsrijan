from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, User
from app.models.ceo import CeoAuditLog
from app.services.audit_service import write_ceo_audit
from app.services.executive_metrics import ResolvedScope, envelope
from app.services.websocket_service import connection_manager
from app.utils.auth_system import require_super_admin


router = APIRouter(prefix="/super-ceo/parent-company", tags=["Super CEO Parent Company"])


class ParentCompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    tagline: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    logo_url: str | None = Field(default=None, max_length=2048)
    banner_url: str | None = Field(default=None, max_length=2048)
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    display_font: str | None = Field(default=None, max_length=100)
    body_font: str | None = Field(default=None, max_length=100)
    founded_date: str | None = None
    legal_name: str | None = Field(default=None, max_length=255)
    registration_number: str | None = Field(default=None, max_length=100)
    gstin: str | None = Field(default=None, pattern=r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]$")
    pan_number: str | None = Field(default=None, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]$")
    fssai_license: str | None = Field(default=None, pattern=r"^[0-9]{14}$")
    cin_number: str | None = Field(default=None, pattern=r"^[A-Z0-9]{21}$")
    registered_address: str | None = Field(default=None, max_length=2000)
    corporate_address: str | None = Field(default=None, max_length=2000)
    bank_account_name: str | None = Field(default=None, max_length=255)
    bank_account_number: str | None = Field(default=None, max_length=100)
    ifsc_code: str | None = Field(default=None, pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")
    bank_name: str | None = Field(default=None, max_length=255)
    annual_revenue_range: str | None = Field(default=None, max_length=20)
    funding_stage: str | None = Field(default=None, max_length=40)
    last_funding_round_date: str | None = None
    total_funding_raised: Decimal | None = Field(default=None, ge=0)
    headquarters_city: str | None = Field(default=None, max_length=120)
    headquarters_state: str | None = Field(default=None, max_length=120)
    headquarters_country: str | None = Field(default=None, max_length=120)
    headquarters_pincode: str | None = Field(default=None, max_length=20)
    website_url: str | None = Field(default=None, max_length=2048)
    linkedin_url: str | None = Field(default=None, max_length=2048)
    instagram_url: str | None = Field(default=None, max_length=2048)
    facebook_url: str | None = Field(default=None, max_length=2048)
    twitter_url: str | None = Field(default=None, max_length=2048)
    youtube_url: str | None = Field(default=None, max_length=2048)
    ios_app_url: str | None = Field(default=None, max_length=2048)
    android_app_url: str | None = Field(default=None, max_length=2048)
    support_email: EmailStr | None = None
    support_phone: str | None = Field(default=None, pattern=r"^\+?[0-9][0-9\s-]{7,20}$")
    whatsapp_business_number: str | None = Field(default=None, pattern=r"^\+?[0-9][0-9\s-]{7,20}$")
    business_domain: str | None = Field(default=None, max_length=64)
    sub_domains: list[str] | None = None
    target_market: str | None = Field(default=None, max_length=16)
    employee_count_estimate: str | None = Field(default=None, max_length=32)

    @field_validator(
        "logo_url", "banner_url", "website_url", "linkedin_url", "instagram_url",
        "facebook_url", "twitter_url", "youtube_url", "ios_app_url", "android_app_url",
    )
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value and not (
            value.startswith("http://")
            or value.startswith("https://")
            or value.startswith("/uploads/")
        ):
            raise ValueError("URL must use http, https, or an uploaded asset path")
        return value


PUBLISHABLE_FIELDS = tuple(ParentCompanyUpdate.model_fields)


def _parent_company(db: Session, actor: User) -> Company:
    company = db.query(Company).filter(Company.is_parent.is_(True)).order_by(Company.id).first()
    if company:
        return company
    company = db.query(Company).filter(Company.name == "FoodSrijan Group").first()
    if company:
        company.is_parent = True
    else:
        company = Company(
            name="FoodSrijan Group",
            slug="foodsrijan-group",
            tagline="Food & Hospitality Holding Company",
            is_parent=True,
            created_by=actor.id,
        )
        db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _serialize(company: Company) -> dict[str, Any]:
    result: dict[str, Any] = {"id": company.id, "slug": company.slug, "is_parent": company.is_parent}
    for field in PUBLISHABLE_FIELDS:
        value = getattr(company, field, None)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        result[field] = value
    result["published_at"] = company.published_at.isoformat() if company.published_at else None
    result["published_by"] = company.published_by
    return result


def _scope(company: Company) -> ResolvedScope:
    return ResolvedScope("company", (company.id,), company_id=company.id)


@router.get("")
def get_parent_company(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    existing_parent = db.query(Company.id).filter(Company.is_parent.is_(True)).first()
    company = _parent_company(db, actor)
    if existing_parent is None:
        write_ceo_audit(db, actor, request, "parent_company.initialized", {"company_id": company.id})
        db.commit()
    return envelope(
        {
            "published": _serialize(company),
            "draft": company.profile_draft,
            "has_draft": bool(company.profile_draft),
        },
        _scope(company),
        sources=["companies"],
    )


@router.put("")
def save_parent_company_draft(
    payload: ParentCompanyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    company = _parent_company(db, actor)
    incoming = payload.model_dump(mode="json", exclude_unset=True)
    draft = dict(company.profile_draft or {})
    changes = {field: {"old": draft.get(field, getattr(company, field, None)), "new": value} for field, value in incoming.items()}
    draft.update(incoming)
    company.profile_draft = draft
    write_ceo_audit(db, actor, request, "parent_company.draft_saved", {"company_id": company.id, "changes": changes})
    db.commit()
    return envelope({"draft": draft, "has_draft": True}, _scope(company), sources=["companies", "ceo_audit_logs"])


@router.delete("/draft")
def discard_parent_company_draft(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    company = _parent_company(db, actor)
    discarded = company.profile_draft
    company.profile_draft = None
    write_ceo_audit(db, actor, request, "parent_company.draft_discarded", {"company_id": company.id, "discarded": discarded})
    db.commit()
    return envelope({"has_draft": False}, _scope(company), sources=["companies", "ceo_audit_logs"])


@router.post("/publish")
async def publish_parent_company(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    company = _parent_company(db, actor)
    draft = dict(company.profile_draft or {})
    if not draft:
        raise HTTPException(status_code=409, detail="There is no parent company draft to publish")
    changes: dict[str, dict[str, Any]] = {}
    for field, value in draft.items():
        old_value = getattr(company, field)
        if field in {"founded_date", "last_funding_round_date"} and value:
            value = datetime.fromisoformat(value).date()
        if field == "total_funding_raised" and value is not None:
            value = Decimal(str(value))
        if old_value != value:
            changes[field] = {"old": old_value, "new": value}
            setattr(company, field, value)
    company.profile_draft = None
    company.published_at = datetime.now(timezone.utc).replace(tzinfo=None)
    company.published_by = actor.id
    write_ceo_audit(db, actor, request, "parent_company.published", {"company_id": company.id, "changes": changes})
    db.commit()
    event = {
        "event": "parent_company.published",
        "resource": {"company_id": company.id},
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "actor": {"user_id": actor.id, "authority": "super_ceo"},
    }
    await connection_manager.broadcast_event(event)
    return envelope({"published": _serialize(company), "has_draft": False, "event": event}, _scope(company), sources=["companies", "ceo_audit_logs"])


@router.get("/audit")
def get_parent_company_audit(
    field: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    company = _parent_company(db, actor)
    query = db.query(CeoAuditLog).filter(CeoAuditLog.action.like("parent_company.%"))
    rows = query.order_by(CeoAuditLog.created_at.desc()).all()
    if field:
        rows = [row for row in rows if field in (row.request_meta or {}).get("changes", {})]
    total = len(rows)
    rows = rows[(page - 1) * page_size:page * page_size]
    entries = [
        {
            "id": row.id,
            "action": row.action,
            "actor_id": row.user_id,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
            "changes": (row.request_meta or {}).get("changes", {}),
        }
        for row in rows
    ]
    return envelope(
        {"audit": entries, "total": total, "page": page, "page_size": page_size},
        _scope(company),
        sources=["ceo_audit_logs"],
    )
