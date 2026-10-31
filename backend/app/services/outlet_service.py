"""Outlet and outlet-manager domain logic.

Every query in this module is constrained by the caller's company scope (and
outlet scope for managers). Callers pass the scope derived from the
authenticated user, never identifiers taken from the request.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Branch,
    Brand,
    Company,
    DailyAnalyticsSnapshot,
    ProfileMembership,
    ProfileType,
    Role,
    StaffEmployee,
    User,
    UserRole,
)
from app.models.ceo import CeoAuditLog
from app.models.doctor_portal import Order
from app.models.hr import StaffProfile
from app.schemas.outlet import OUTLET_REGIONS, OUTLET_STATUSES, OUTLET_TYPES
from app.services.company_service import generate_secure_password
from app.services.websocket_service import build_domain_event, publish_domain_event
from app.utils.auth_system import auth_guard
from app.utils.guards import COMPANY_CEO_ROLE, OUTLET_MANAGER_ROLE
from app.utils.validators import validate_slug


logger = logging.getLogger(__name__)

CLOSED_ORDER_STATUSES = ("completed", "cancelled", "canceled", "closed", "fulfilled", "delivered")
SENSITIVE_KEY_PATTERN = re.compile(r"password|hashed|secret|token|credential", re.IGNORECASE)
MASKED_KEYS = {"bank_account_number", "manager_bank_account_number"}
OUTLET_FIELDS = (
    "id", "company_id", "brand_id", "name", "slug", "code", "branch_code", "outlet_type", "status",
    "description", "opening_date", "logo_url", "cover_photo_url",
    "address_line_1", "address_line_2", "city", "state", "country", "pincode", "latitude", "longitude",
    "region", "timezone",
    "opening_time", "closing_time", "operating_days", "seating_capacity", "kitchen_capacity",
    "is_delivery_enabled", "is_dine_in_enabled", "is_takeaway_enabled", "delivery_radius_km",
    "fssai_license", "gstin", "trade_license", "fire_safety_certificate", "health_permit", "license_expiry_date",
    "rent_amount", "security_deposit", "lease_start_date", "lease_end_date", "bank_account_name",
    "bank_account_number", "ifsc_code", "bank_name", "branch_name", "upi_id", "cost_center_code",
    "manager_contact_email", "manager_contact_phone", "outlet_email", "outlet_phone", "google_maps_url",
    "swiggy_store_id", "zomato_store_id",
    "created_by", "created_at", "updated_at", "deleted_at", "is_deleted", "is_active",
)
MANAGER_HIDDEN_OUTLET_FIELDS = {
    "rent_amount", "security_deposit", "lease_start_date", "lease_end_date", "bank_account_name",
    "bank_account_number", "ifsc_code", "bank_name", "branch_name", "upi_id", "cost_center_code", "created_by",
}
REQUIRED_OUTLET_FIELDS = ("name", "code", "outlet_type", "status", "address_line_1", "city", "state", "pincode")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _mask(value: Any) -> Any:
    text = str(value or "")
    return f"{'*' * max(len(text) - 4, 0)}{text[-4:]}" if text else value


def redact(payload: Any) -> Any:
    """Strip credential-like keys and mask account numbers before audit persistence."""
    if isinstance(payload, dict):
        cleaned = {}
        for key, value in payload.items():
            if SENSITIVE_KEY_PATTERN.search(str(key)):
                continue
            cleaned[key] = _mask(value) if key in MASKED_KEYS and value else redact(value)
        return cleaned
    if isinstance(payload, (list, tuple)):
        return [redact(item) for item in payload]
    return _json_value(payload)


def _slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (value or "").lower())).strip("-")


def serialize_manager(user: User | None) -> dict[str, Any] | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "role": user.role,
        "outlet_id": user.outlet_id,
        "company_id": user.company_id,
        "is_outlet_manager": bool(user.is_outlet_manager),
        "is_active": bool(user.is_active),
        "force_password_change": bool(user.force_password_change),
        "manager_photo_url": user.manager_photo_url,
        "manager_address": user.manager_address,
        "manager_bank_account_name": user.manager_bank_account_name,
        "manager_bank_account_number": user.manager_bank_account_number,
        "manager_ifsc_code": user.manager_ifsc_code,
        "manager_bank_name": user.manager_bank_name,
        "manager_assigned_at": _json_value(user.manager_assigned_at),
        "manager_assigned_by": user.manager_assigned_by,
        "last_login": _json_value(user.last_login),
    }


def serialize_manager_summary(user: User | None) -> dict[str, Any] | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        "manager_photo_url": user.manager_photo_url,
    }


def serialize_outlet(
    outlet: Branch,
    *,
    manager: User | None = None,
    staff_count: int | None = None,
    for_manager: bool = False,
) -> dict[str, Any]:
    data = {}
    for key in OUTLET_FIELDS:
        if for_manager and key in MANAGER_HIDDEN_OUTLET_FIELDS:
            continue
        data[key] = _json_value(getattr(outlet, key))
    data["metadata"] = outlet.outlet_metadata
    data["outlet_type_label"] = OUTLET_TYPES.get(outlet.outlet_type or "")
    data["status_label"] = OUTLET_STATUSES.get(outlet.status or "")
    data["region_label"] = OUTLET_REGIONS.get(outlet.region or "")
    data["manager"] = serialize_manager_summary(manager)
    if staff_count is not None:
        data["staff_count"] = staff_count
    return data


def _actor_role(actor: User) -> str:
    if getattr(actor, "is_outlet_manager", False):
        return OUTLET_MANAGER_ROLE
    if getattr(actor, "is_company_ceo", False):
        return COMPANY_CEO_ROLE
    return (actor.role or "").strip().lower()


def write_audit(
    db: Session,
    actor: User,
    request: Request,
    action: str,
    *,
    resource_type: str,
    resource_id: int | None,
    company_id: int,
    outlet_id: int | None,
    changes: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
    response_status: int = 200,
) -> CeoAuditLog:
    previous = db.query(CeoAuditLog).order_by(CeoAuditLog.id.desc()).first()
    previous_signature = previous.signature if previous else None
    request_meta = json.loads(json.dumps({
        "action": action,
        "actor_id": actor.id,
        "actor_role": _actor_role(actor),
        "resource_type": resource_type,
        "resource_id": resource_id,
        "company_id": company_id,
        "outlet_id": outlet_id,
        "changes": redact(changes or {}),
        "metadata": redact(extra or {}),
        "ip_address": request.client.host if request.client else None,
        "user_agent": (request.headers.get("user-agent") or "")[:500],
    }, default=str))
    signature = hashlib.sha256(json.dumps({
        "actor_id": actor.id,
        "action": action,
        "request_meta": request_meta,
        "previous_signature": previous_signature,
        "occurred_at": _now().isoformat(),
    }, sort_keys=True, default=str).encode()).hexdigest()
    row = CeoAuditLog(
        user_id=actor.id,
        action=action,
        http_method=request.method,
        endpoint=request.url.path,
        response_status=response_status,
        request_meta=request_meta,
        previous_signature=previous_signature,
        signature=signature,
    )
    db.add(row)
    return row


def emit(event_type: str, actor: User, *, company_id: int, outlet_id: int | None, resource_type: str, resource_id: int | None, data: dict | None = None, revoke_user_ids: list[int] | None = None) -> None:
    event = build_domain_event(
        event_type,
        company_id=company_id,
        outlet_id=outlet_id,
        actor_id=actor.id,
        actor_role=_actor_role(actor),
        resource_type=resource_type,
        resource_id=resource_id,
        data=redact(data or {}),
    )
    publish_domain_event(event, revoke_user_ids=revoke_user_ids)


# ---------------------------------------------------------------------------
# Scoped lookups
# ---------------------------------------------------------------------------

def scoped_outlet_query(db: Session, company_id: int, *, include_deleted: bool = False):
    query = db.query(Branch).filter(Branch.company_id == company_id)
    if not include_deleted:
        query = query.filter(Branch.is_deleted.is_(False))
    return query


def get_scoped_outlet(db: Session, company_id: int, outlet_id: int, *, include_deleted: bool = False) -> Branch:
    outlet = scoped_outlet_query(db, company_id, include_deleted=include_deleted).filter(Branch.id == outlet_id).first()
    if outlet is None:
        # 404 for foreign outlets avoids confirming that another tenant's ID exists.
        raise HTTPException(status_code=404, detail="Outlet not found")
    return outlet


def find_outlet_manager(db: Session, company_id: int, outlet_id: int) -> User | None:
    return (
        db.query(User)
        .filter(
            User.company_id == company_id,
            User.outlet_id == outlet_id,
            User.is_outlet_manager.is_(True),
            User.is_active.is_(True),
        )
        .order_by(User.manager_assigned_at.desc(), User.id.desc())
        .first()
    )


def _managers_by_outlet(db: Session, company_id: int, outlet_ids: list[int]) -> dict[int, User]:
    if not outlet_ids:
        return {}
    rows = (
        db.query(User)
        .filter(
            User.company_id == company_id,
            User.outlet_id.in_(outlet_ids),
            User.is_outlet_manager.is_(True),
            User.is_active.is_(True),
        )
        .all()
    )
    return {row.outlet_id: row for row in rows}


def _staff_user_ids(db: Session, company_id: int, outlet_ids: list[int]) -> dict[int, set]:
    result: dict[int, set] = {outlet_id: set() for outlet_id in outlet_ids}
    if not outlet_ids:
        return result
    employee_rows = (
        db.query(StaffEmployee.branch_id, StaffEmployee.user_id)
        .join(Branch, Branch.id == StaffEmployee.branch_id)
        .filter(Branch.company_id == company_id, StaffEmployee.branch_id.in_(outlet_ids), StaffEmployee.is_active.is_(True))
        .all()
    )
    profile_rows = (
        db.query(StaffProfile.branch_id, StaffProfile.user_id)
        .join(Branch, Branch.id == StaffProfile.branch_id)
        .filter(Branch.company_id == company_id, StaffProfile.branch_id.in_(outlet_ids), StaffProfile.is_active.is_(True))
        .all()
    )
    user_rows = (
        db.query(User.branch_id, User.id)
        .filter(
            User.company_id == company_id,
            User.branch_id.in_(outlet_ids),
            User.is_active.is_(True),
            User.is_outlet_manager.is_(False),
            User.is_company_ceo.is_(False),
        )
        .all()
    )
    for branch_id, user_id in [*employee_rows, *profile_rows, *user_rows]:
        result.setdefault(branch_id, set()).add(user_id)
    return result


def staff_counts(db: Session, company_id: int, outlet_ids: list[int]) -> dict[int, int]:
    return {outlet_id: len(users) for outlet_id, users in _staff_user_ids(db, company_id, outlet_ids).items()}


def _pending_orders(db: Session, company_id: int, outlet_id: int) -> int:
    return (
        db.query(Order)
        .join(Branch, Branch.id == Order.branch_id)
        .filter(
            Branch.company_id == company_id,
            Order.branch_id == outlet_id,
            func.lower(Order.status).notin_(CLOSED_ORDER_STATUSES),
        )
        .count()
    )


# ---------------------------------------------------------------------------
# Outlet CRUD
# ---------------------------------------------------------------------------

def _validate_brand(db: Session, company_id: int, brand_id: int | None) -> None:
    if brand_id is None:
        return
    exists = db.query(Brand.id).filter(Brand.id == brand_id, Brand.company_id == company_id).first()
    if not exists:
        raise HTTPException(status_code=422, detail="Brand does not belong to your company")


def _unique_slug(db: Session, company_id: int, name: str, requested: str | None, outlet_id: int | None = None) -> str:
    slug = requested or _slugify(name)[:110]
    if not validate_slug(slug):
        raise HTTPException(status_code=422, detail="Outlet name cannot be converted to a valid slug")
    base, suffix = slug, 2
    while True:
        query = db.query(Branch.id).filter(Branch.company_id == company_id, Branch.slug == slug)
        if outlet_id is not None:
            query = query.filter(Branch.id != outlet_id)
        if not query.first():
            return slug
        if requested:
            raise HTTPException(status_code=409, detail="Outlet slug already exists in your company")
        slug = f"{base}-{suffix}"
        suffix += 1


def _check_uniques(db: Session, company_id: int, values: dict[str, Any], outlet_id: int | None = None) -> None:
    def taken(query):
        if outlet_id is not None:
            query = query.filter(Branch.id != outlet_id)
        return query.first() is not None

    if values.get("code") and taken(db.query(Branch.id).filter(Branch.company_id == company_id, Branch.code == values["code"])):
        raise HTTPException(status_code=409, detail="Outlet code already exists in your company")
    if values.get("name") and taken(db.query(Branch.id).filter(func.lower(Branch.name) == values["name"].lower())):
        raise HTTPException(status_code=409, detail="Outlet name already exists")
    if values.get("gstin") and taken(db.query(Branch.id).filter(Branch.gstin == values["gstin"])):
        raise HTTPException(status_code=409, detail="Outlet GSTIN already exists")
    if values.get("branch_code") and taken(db.query(Branch.id).filter(Branch.branch_code == values["branch_code"])):
        raise HTTPException(status_code=409, detail="Outlet code already exists")


def _legacy_branch_code(company_id: int, code: str) -> str:
    return f"O{company_id}-{code}"[:20]


def _sync_legacy_columns(outlet: Branch) -> None:
    outlet.location = ", ".join(part for part in (outlet.city, outlet.state) if part)[:200] or outlet.location or ""
    address = ", ".join(part for part in (outlet.address_line_1, outlet.address_line_2) if part)
    outlet.address = address or outlet.address or ""
    outlet.phone = (outlet.outlet_phone or outlet.phone or "")[:15]
    outlet.email = (outlet.outlet_email or outlet.email or "")[:100]
    outlet.is_active = not outlet.is_deleted and outlet.status != "permanently_closed"


def create_outlet(db: Session, actor: User, company: Company, request: Request, values: dict[str, Any]) -> Branch:
    values = {key: value for key, value in values.items() if value is not None}
    _validate_brand(db, company.id, values.get("brand_id"))
    values["slug"] = _unique_slug(db, company.id, values["name"], values.get("slug"))
    values["branch_code"] = _legacy_branch_code(company.id, values["code"])
    _check_uniques(db, company.id, values)
    for field in ("outlet_email", "manager_contact_email"):
        if values.get(field):
            values[field] = str(values[field])
    values.setdefault("status", "planning")
    outlet = Branch(
        **values,
        company_id=company.id,
        created_by=actor.id,
        is_deleted=False,
        location="",
        address="",
        phone="",
        email="",
    )
    _sync_legacy_columns(outlet)
    db.add(outlet)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="An outlet with one of these unique fields already exists") from error
    write_audit(
        db, actor, request, "outlet.created",
        resource_type="outlet", resource_id=outlet.id, company_id=company.id, outlet_id=outlet.id,
        changes={"after": {key: values.get(key) for key in values}},
        extra={"name": outlet.name, "code": outlet.code},
        response_status=201,
    )
    db.commit()
    db.refresh(outlet)
    emit("outlet.created", actor, company_id=company.id, outlet_id=outlet.id, resource_type="outlet", resource_id=outlet.id, data={"name": outlet.name, "code": outlet.code, "status": outlet.status})
    return outlet


def list_outlets(
    db: Session,
    company_id: int,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    city: str | None = None,
    region: str | None = None,
    outlet_type: str | None = None,
    search: str | None = None,
    include_deleted: bool = False,
) -> tuple[list[Branch], int]:
    query = scoped_outlet_query(db, company_id, include_deleted=include_deleted)
    if status:
        query = query.filter(Branch.status == status)
    if city:
        query = query.filter(func.lower(Branch.city) == city.strip().lower())
    if region:
        query = query.filter(Branch.region == region)
    if outlet_type:
        query = query.filter(Branch.outlet_type == outlet_type)
    if search:
        pattern = f"%{search.strip().lower()}%"
        query = query.filter(or_(func.lower(Branch.name).like(pattern), func.lower(Branch.code).like(pattern)))
    total = query.count()
    rows = query.order_by(Branch.name.asc(), Branch.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def serialize_outlets(db: Session, company_id: int, outlets: list[Branch]) -> list[dict[str, Any]]:
    outlet_ids = [row.id for row in outlets]
    managers = _managers_by_outlet(db, company_id, outlet_ids)
    counts = staff_counts(db, company_id, outlet_ids)
    return [serialize_outlet(row, manager=managers.get(row.id), staff_count=counts.get(row.id, 0)) for row in outlets]


def outlet_detail(db: Session, company_id: int, outlet: Branch) -> dict[str, Any]:
    return serialize_outlets(db, company_id, [outlet])[0]


def outlet_stats(db: Session, company_id: int) -> dict[str, Any]:
    live = scoped_outlet_query(db, company_id)
    outlet_ids = [row.id for row in live.with_entities(Branch.id).all()]
    by_status = dict(live.with_entities(Branch.status, func.count(Branch.id)).group_by(Branch.status).all())
    by_type = dict(live.with_entities(Branch.outlet_type, func.count(Branch.id)).group_by(Branch.outlet_type).all())
    by_region = dict(live.with_entities(Branch.region, func.count(Branch.id)).group_by(Branch.region).all())
    deleted = db.query(Branch).filter(Branch.company_id == company_id, Branch.is_deleted.is_(True)).count()
    with_manager = len(_managers_by_outlet(db, company_id, outlet_ids))
    staff_by_outlet = _staff_user_ids(db, company_id, outlet_ids)
    total_staff = len(set().union(*staff_by_outlet.values())) if staff_by_outlet else 0
    since = date.today() - timedelta(days=30)
    revenue = 0.0
    if outlet_ids:
        revenue = float(
            db.query(func.coalesce(func.sum(DailyAnalyticsSnapshot.total_revenue), 0))
            .join(Branch, Branch.id == DailyAnalyticsSnapshot.branch_id)
            .filter(Branch.company_id == company_id, DailyAnalyticsSnapshot.branch_id.in_(outlet_ids), DailyAnalyticsSnapshot.date >= since)
            .scalar()
            or 0
        )
    total = len(outlet_ids)
    return {
        "total_outlets": total,
        "active_outlets": int(by_status.get("active", 0)),
        "deleted_outlets": deleted,
        "outlets_with_manager": with_manager,
        "outlets_without_manager": total - with_manager,
        "total_staff": total_staff,
        "revenue_30d": revenue,
        "avg_revenue_30d": round(revenue / total, 2) if total else 0.0,
        "by_status": {key: int(by_status.get(key, 0)) for key in OUTLET_STATUSES},
        "by_type": {key: int(value) for key, value in by_type.items() if key},
        "by_region": {key: int(value) for key, value in by_region.items() if key},
    }


def _apply_changes(outlet: Branch, changes: dict[str, Any]) -> dict[str, dict[str, Any]]:
    before, after = {}, {}
    for key, value in changes.items():
        if key in {"outlet_email", "manager_contact_email"} and value is not None:
            value = str(value)
        current = getattr(outlet, key)
        if _json_value(current) == _json_value(value):
            continue
        before[key] = current
        setattr(outlet, key, value)
        after[key] = value
    return {"before": before, "after": after}


def update_outlet(db: Session, actor: User, company: Company, request: Request, outlet: Branch, changes: dict[str, Any]) -> Branch:
    if "brand_id" in changes:
        _validate_brand(db, company.id, changes["brand_id"])
    for required in REQUIRED_OUTLET_FIELDS:
        if required in changes and changes[required] in (None, ""):
            changes.pop(required)
    requested_slug = changes.pop("slug", None)
    if requested_slug:
        changes["slug"] = _unique_slug(db, company.id, outlet.name, requested_slug, outlet.id)
    if changes.get("code"):
        changes["branch_code"] = _legacy_branch_code(company.id, changes["code"])
    _check_uniques(db, company.id, changes, outlet.id)
    diff = _apply_changes(outlet, changes)
    if not diff["after"]:
        return outlet
    _sync_legacy_columns(outlet)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="An outlet with one of these unique fields already exists") from error
    write_audit(db, actor, request, "outlet.updated", resource_type="outlet", resource_id=outlet.id, company_id=company.id, outlet_id=outlet.id, changes=diff)
    db.commit()
    db.refresh(outlet)
    emit("outlet.updated", actor, company_id=company.id, outlet_id=outlet.id, resource_type="outlet", resource_id=outlet.id, data={"fields": sorted(diff["after"].keys())})
    return outlet


def delete_blockers(db: Session, company_id: int, outlet: Branch) -> dict[str, int]:
    return {
        "active_staff": staff_counts(db, company_id, [outlet.id]).get(outlet.id, 0),
        "pending_orders": _pending_orders(db, company_id, outlet.id),
    }


def soft_delete_outlet(db: Session, actor: User, company: Company, request: Request, outlet: Branch, reason: str | None) -> dict[str, Any]:
    blockers = delete_blockers(db, company.id, outlet)
    blocking = {key: count for key, count in blockers.items() if count}
    if blocking:
        raise HTTPException(status_code=400, detail={"message": "Outlet cannot be deleted while it has active staff or open orders", "blockers": blocking})
    before = {"status": outlet.status, "is_active": outlet.is_active, "is_deleted": outlet.is_deleted}
    outlet.is_deleted = True
    outlet.deleted_at = _now()
    _sync_legacy_columns(outlet)
    write_audit(db, actor, request, "outlet.deleted", resource_type="outlet", resource_id=outlet.id, company_id=company.id, outlet_id=outlet.id, changes={"before": before, "after": {"is_deleted": True, "is_active": outlet.is_active}}, extra={"reason": reason})
    db.commit()
    emit("outlet.deleted", actor, company_id=company.id, outlet_id=outlet.id, resource_type="outlet", resource_id=outlet.id)
    return {"outlet_id": outlet.id, "deleted": True, "deleted_at": outlet.deleted_at.isoformat()}


def restore_outlet(db: Session, actor: User, company: Company, request: Request, outlet: Branch) -> Branch:
    if not outlet.is_deleted:
        raise HTTPException(status_code=409, detail="Outlet is not deleted")
    _check_uniques(db, company.id, {"code": outlet.code, "name": outlet.name, "gstin": outlet.gstin}, outlet.id)
    outlet.is_deleted = False
    outlet.deleted_at = None
    _sync_legacy_columns(outlet)
    write_audit(db, actor, request, "outlet.restored", resource_type="outlet", resource_id=outlet.id, company_id=company.id, outlet_id=outlet.id)
    db.commit()
    db.refresh(outlet)
    emit("outlet.restored", actor, company_id=company.id, outlet_id=outlet.id, resource_type="outlet", resource_id=outlet.id)
    return outlet


def outlet_audit_events(db: Session, company_id: int, outlet_id: int, *, page: int, page_size: int, action: str | None = None) -> tuple[list[dict[str, Any]], int]:
    query = db.query(CeoAuditLog).filter(
        CeoAuditLog.request_meta["company_id"].as_integer() == company_id,
        CeoAuditLog.request_meta["outlet_id"].as_integer() == outlet_id,
    )
    if action:
        query = query.filter(CeoAuditLog.action == action)
    total = query.count()
    rows = query.order_by(CeoAuditLog.created_at.desc(), CeoAuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    events = [
        {
            "id": row.id,
            "actor_id": row.user_id,
            "actor_role": row.request_meta.get("actor_role"),
            "action": row.action,
            "resource_type": row.request_meta.get("resource_type"),
            "resource_id": row.request_meta.get("resource_id"),
            "changes": row.request_meta.get("changes", {}),
            "metadata": row.request_meta.get("metadata", {}),
            "ip_address": row.request_meta.get("ip_address"),
            "user_agent": row.request_meta.get("user_agent"),
            "created_at": _json_value(row.created_at),
        }
        for row in rows
    ]
    return events, total


# ---------------------------------------------------------------------------
# Manager lifecycle (Company CEO scope)
# ---------------------------------------------------------------------------

def _suggest_username(db: Session, outlet: Branch) -> str:
    base = re.sub(r"[^a-z0-9_]", "_", f"{(outlet.code or 'outlet').lower()}_manager")[:26]
    candidate, suffix = base, 2
    while db.query(User.id).filter(func.lower(User.username) == candidate.lower()).first():
        candidate = f"{base}_{suffix}"[:30]
        suffix += 1
    return candidate


def _assign_default_role(db: Session, user: User, company_id: int, outlet_id: int) -> None:
    role = (
        db.query(Role)
        .filter(Role.slug == OUTLET_MANAGER_ROLE, Role.is_active.is_(True), or_(Role.company_id == company_id, Role.company_id.is_(None)))
        .order_by(Role.company_id.desc())
        .first()
    )
    if role is not None:
        db.add(UserRole(user_id=user.id, role_id=role.id, company_id=company_id, branch_id=outlet_id, is_active=True))
    profile_type = db.query(ProfileType).filter(ProfileType.code == OUTLET_MANAGER_ROLE, ProfileType.is_active.is_(True)).first()
    if profile_type is not None:
        db.add(ProfileMembership(user_id=user.id, profile_type_id=profile_type.id, company_id=company_id, branch_id=outlet_id, is_active=True))


def _unassign(db: Session, user: User, company_id: int) -> dict[str, Any]:
    before = {"outlet_id": user.outlet_id, "is_outlet_manager": user.is_outlet_manager, "is_active": user.is_active, "role": user.role}
    outlet_id = user.outlet_id
    user.is_outlet_manager = False
    user.outlet_id = None
    user.branch_id = None
    user.is_active = False
    user.role = "StaffEmployee"
    user.manager_assigned_at = None
    db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.company_id == company_id, UserRole.branch_id == outlet_id).update({UserRole.is_active: False}, synchronize_session=False)
    db.query(ProfileMembership).filter(ProfileMembership.user_id == user.id, ProfileMembership.company_id == company_id, ProfileMembership.branch_id == outlet_id).update({ProfileMembership.is_active: False}, synchronize_session=False)
    return before


def create_manager(db: Session, actor: User, company: Company, request: Request, outlet: Branch, payload) -> tuple[User, str]:
    existing = find_outlet_manager(db, company.id, outlet.id)
    if existing and not payload.replace_existing:
        raise HTTPException(status_code=409, detail="Outlet already has an active manager")
    username = payload.username or _suggest_username(db, outlet)
    if db.query(User.id).filter(func.lower(User.username) == username.lower()).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    email = str(payload.email).strip()
    if db.query(User.id).filter(func.lower(User.email) == email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already exists")
    password = payload.password or generate_secure_password()

    replaced_user_id = None
    if existing:
        replaced_user_id = existing.id
        before = _unassign(db, existing, company.id)
        write_audit(db, actor, request, "manager.removed", resource_type="user", resource_id=existing.id, company_id=company.id, outlet_id=outlet.id, changes={"before": before}, extra={"reason": "replaced"})
        db.flush()

    now = _now()
    user = User(
        username=username,
        email=email,
        hashed_password=auth_guard.hash_password(password),
        role=OUTLET_MANAGER_ROLE,
        company_id=company.id,
        current_company_id=company.id,
        branch_id=outlet.id,
        outlet_id=outlet.id,
        is_outlet_manager=True,
        is_company_ceo=False,
        is_super_admin=False,
        is_super_ceo=False,
        is_active=True,
        manager_assigned_at=now,
        manager_assigned_by=actor.id,
        force_password_change=True,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        manager_photo_url=payload.manager_photo_url,
        manager_address=payload.manager_address,
        manager_bank_account_name=payload.manager_bank_account_name,
        manager_bank_account_number=payload.manager_bank_account_number,
        manager_ifsc_code=payload.manager_ifsc_code,
        manager_bank_name=payload.manager_bank_name,
    )
    db.add(user)
    try:
        db.flush()
        _assign_default_role(db, user, company.id, outlet.id)
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Manager username or email already exists") from error
    write_audit(
        db, actor, request, "manager.assigned",
        resource_type="user", resource_id=user.id, company_id=company.id, outlet_id=outlet.id,
        extra={"username": user.username, "email": user.email, "replaced_user_id": replaced_user_id},
        response_status=201,
    )
    db.commit()
    db.refresh(user)
    logger.info("Outlet manager assigned: user_id=%s outlet_id=%s company_id=%s", user.id, outlet.id, company.id)
    if replaced_user_id:
        emit("manager.removed", actor, company_id=company.id, outlet_id=outlet.id, resource_type="user", resource_id=replaced_user_id, revoke_user_ids=[replaced_user_id])
    emit("manager.assigned", actor, company_id=company.id, outlet_id=outlet.id, resource_type="user", resource_id=user.id, data={"username": user.username})
    return user, password


def update_manager(db: Session, actor: User, company: Company, request: Request, outlet: Branch, user: User, changes: dict[str, Any]) -> User:
    if changes.get("email"):
        changes["email"] = str(changes["email"]).strip()
        if db.query(User.id).filter(func.lower(User.email) == changes["email"].lower(), User.id != user.id).first():
            raise HTTPException(status_code=409, detail="Email already exists")
    for required in ("first_name", "last_name", "email", "phone", "is_active"):
        if required in changes and changes[required] is None:
            changes.pop(required)
    before, after = {}, {}
    for key, value in changes.items():
        if getattr(user, key) != value:
            before[key] = getattr(user, key)
            setattr(user, key, value)
            after[key] = value
    if not after:
        return user
    write_audit(db, actor, request, "manager.updated", resource_type="user", resource_id=user.id, company_id=company.id, outlet_id=outlet.id, changes={"before": before, "after": after})
    db.commit()
    db.refresh(user)
    revoke = [user.id] if after.get("is_active") is False else None
    emit("manager.updated", actor, company_id=company.id, outlet_id=outlet.id, resource_type="user", resource_id=user.id, data={"fields": sorted(after.keys())}, revoke_user_ids=revoke)
    return user


def reset_manager_password(db: Session, actor: User, company: Company, request: Request, outlet: Branch, user: User) -> str:
    from app.services.token_revocation import revoke_user_sessions

    password = generate_secure_password()
    user.hashed_password = auth_guard.hash_password(password)
    user.password_changed_at = _now()
    user.force_password_change = True
    write_audit(db, actor, request, "manager.password_reset", resource_type="user", resource_id=user.id, company_id=company.id, outlet_id=outlet.id, extra={"username": user.username})
    db.commit()
    revoke_user_sessions(user.id)
    emit("manager.password_reset", actor, company_id=company.id, outlet_id=outlet.id, resource_type="user", resource_id=user.id, revoke_user_ids=[user.id])
    return password


def remove_manager(db: Session, actor: User, company: Company, request: Request, outlet: Branch, user: User) -> None:
    before = _unassign(db, user, company.id)
    write_audit(db, actor, request, "manager.removed", resource_type="user", resource_id=user.id, company_id=company.id, outlet_id=outlet.id, changes={"before": before, "after": {"outlet_id": None, "is_outlet_manager": False, "is_active": False}})
    db.commit()
    emit("manager.removed", actor, company_id=company.id, outlet_id=outlet.id, resource_type="user", resource_id=user.id, revoke_user_ids=[user.id])


def credentials_payload(username: str, password: str, note: str) -> dict[str, str]:
    frontend_url = os.getenv("FRONTEND_URL", "https://vaidyavihar.com").rstrip("/")
    return {"login_url": f"{frontend_url}/login", "username": username, "password": password, "note": note}


# ---------------------------------------------------------------------------
# Manager self-service (outlet scope)
# ---------------------------------------------------------------------------

def update_manager_self(db: Session, user: User, company: Company, outlet: Branch, request: Request, changes: dict[str, Any]) -> User:
    before, after = {}, {}
    for key, value in changes.items():
        if key in {"first_name", "last_name", "phone"} and value is None:
            continue
        if getattr(user, key) != value:
            before[key] = getattr(user, key)
            setattr(user, key, value)
            after[key] = value
    if not after:
        return user
    write_audit(db, user, request, "manager.profile_updated", resource_type="user", resource_id=user.id, company_id=company.id, outlet_id=outlet.id, changes={"before": before, "after": after})
    db.commit()
    db.refresh(user)
    emit("manager.updated", user, company_id=company.id, outlet_id=outlet.id, resource_type="user", resource_id=user.id, data={"fields": sorted(after.keys())})
    return user


def update_outlet_by_manager(db: Session, user: User, company: Company, outlet: Branch, request: Request, changes: dict[str, Any]) -> Branch:
    diff = _apply_changes(outlet, changes)
    if not diff["after"]:
        return outlet
    _sync_legacy_columns(outlet)
    write_audit(db, user, request, "outlet.updated", resource_type="outlet", resource_id=outlet.id, company_id=company.id, outlet_id=outlet.id, changes=diff, extra={"source": "manager"})
    db.commit()
    db.refresh(outlet)
    emit("outlet.updated", user, company_id=company.id, outlet_id=outlet.id, resource_type="outlet", resource_id=outlet.id, data={"fields": sorted(diff["after"].keys())})
    return outlet


def manager_stats(db: Session, company_id: int, outlet: Branch) -> dict[str, Any]:
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    orders_today = (
        db.query(Order)
        .join(Branch, Branch.id == Order.branch_id)
        .filter(Branch.company_id == company_id, Order.branch_id == outlet.id, Order.order_date >= start, Order.order_date < start + timedelta(days=1))
        .count()
    )
    snapshot = (
        db.query(DailyAnalyticsSnapshot)
        .join(Branch, Branch.id == DailyAnalyticsSnapshot.branch_id)
        .filter(Branch.company_id == company_id, DailyAnalyticsSnapshot.branch_id == outlet.id, DailyAnalyticsSnapshot.date == today)
        .first()
    )
    return {
        "outlet_id": outlet.id,
        "company_id": company_id,
        "staff_count": staff_counts(db, company_id, [outlet.id]).get(outlet.id, 0),
        "orders_today": orders_today,
        "pending_orders": _pending_orders(db, company_id, outlet.id),
        "revenue_today": float(snapshot.total_revenue) if snapshot else 0.0,
        "avg_bill_value_today": float(snapshot.avg_bill_value) if snapshot else 0.0,
    }
