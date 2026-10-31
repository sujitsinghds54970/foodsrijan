import hashlib
import json
import secrets
import string
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Branch,
    Brand,
    Company,
    Customer,
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
from app.services.executive_metrics import ResolvedScope, envelope
from app.utils.auth_system import auth_guard
from app.utils.validators import validate_password_strength, validate_slug


UNIQUE_COMPANY_FIELDS = ("slug", "legal_name", "registration_number", "gstin", "pan_number")
COMPANY_SERIALIZED_FIELDS = tuple(Company.__table__.columns.keys())


def serialize_company(company: Company) -> dict[str, Any]:
    result = {}
    for key in COMPANY_SERIALIZED_FIELDS:
        value = getattr(company, "company_metadata" if key == "metadata" else key)
        result[key] = value.isoformat() if isinstance(value, (datetime,)) else value.isoformat() if hasattr(value, "isoformat") else value
    return result


def serialize_ceo(user: User | None) -> dict[str, Any] | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "company_id": user.company_id,
        "is_company_ceo": user.is_company_ceo,
        "is_active": user.is_active,
        "force_password_change": user.force_password_change,
        "ceo_assigned_at": user.ceo_assigned_at.isoformat() if user.ceo_assigned_at else None,
        "password_changed_at": user.password_changed_at.isoformat() if user.password_changed_at else None,
    }


def _slugify(name: str) -> str:
    import re

    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def _unique_slug(db: Session, name: str, requested: str | None) -> str:
    slug = requested or _slugify(name)
    if not validate_slug(slug):
        raise HTTPException(status_code=422, detail="Company name cannot be converted to a valid slug")
    base = slug
    suffix = 2
    while db.query(Company.id).filter(Company.slug == slug).first():
        if requested:
            raise HTTPException(status_code=409, detail="Company slug already exists")
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def _check_unique_company_values(db: Session, values: dict[str, Any], company_id: int | None = None) -> None:
    for field in UNIQUE_COMPANY_FIELDS:
        value = values.get(field)
        if not value:
            continue
        query = db.query(Company.id).filter(getattr(Company, field) == value)
        if company_id is not None:
            query = query.filter(Company.id != company_id)
        if query.first():
            raise HTTPException(status_code=409, detail=f"Company {field.replace('_', ' ')} already exists")


def _audit(
    db: Session,
    actor: User,
    request: Request,
    action: str,
    resource_type: str,
    resource_id: int,
    company_id: int,
    changes: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    previous = db.query(CeoAuditLog).order_by(CeoAuditLog.id.desc()).first()
    previous_signature = previous.signature if previous else None
    request_meta = {
        "actor_id": actor.id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "company_id": company_id,
        "changes": changes or {},
        "metadata": extra or {},
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
    request_meta = json.loads(json.dumps(request_meta, default=str))
    signature_payload = {
        "actor_id": actor.id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "request_meta": request_meta,
        "previous_signature": previous_signature,
    }
    signature = hashlib.sha256(json.dumps(signature_payload, sort_keys=True, default=str).encode()).hexdigest()
    db.add(
        CeoAuditLog(
            user_id=actor.id,
            action=action,
            http_method=request.method,
            endpoint=request.url.path,
            response_status=200,
            request_meta={"action": action, **request_meta},
            previous_signature=previous_signature,
            signature=signature,
        )
    )


def create_company(db: Session, actor: User, request: Request, values: dict[str, Any]) -> Company:
    values = {key: value for key, value in values.items() if value is not None}
    values["slug"] = _unique_slug(db, values["name"], values.get("slug"))
    _check_unique_company_values(db, values)
    values["created_by"] = actor.id
    values["status"] = "active"
    values["onboarding_status"] = "pending"
    values["is_deleted"] = False
    values["is_active"] = True
    company = Company(**values)
    db.add(company)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="A company with one of these unique fields already exists") from error
    _audit(db, actor, request, "company.created", "company", company.id, company.id, extra={"name": company.name})
    db.commit()
    db.refresh(company)
    return company


def list_companies(
    db: Session,
    *,
    page: int,
    page_size: int,
    status: str | None,
    business_domain: str | None,
    search: str | None,
    include_deleted: bool,
) -> tuple[list[Company], int]:
    query = db.query(Company)
    if not include_deleted:
        query = query.filter(Company.is_deleted.is_(False))
    if status:
        query = query.filter(Company.status == status)
    if business_domain:
        query = query.filter(Company.business_domain == business_domain)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Company.name.ilike(term), Company.legal_name.ilike(term), Company.slug.ilike(term)))
    total = query.count()
    rows = query.order_by(Company.created_at.desc(), Company.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def company_portfolio_stats(db: Session) -> dict[str, int]:
    active_companies = db.query(Company).filter(
        Company.is_active.is_(True),
        Company.is_deleted.is_(False),
    )
    active_company_ids = active_companies.with_entities(Company.id)
    return {
        "active_companies": active_companies.count(),
        "active_branches": int(
            active_companies.with_entities(
                func.coalesce(func.sum(Company.number_of_branches), 0)
            ).scalar()
            or 0
        ),
        "active_users": db.query(User.id).filter(
            User.is_active.is_(True),
            User.company_id.in_(active_company_ids),
        ).count(),
        "pending_onboarding": active_companies.filter(
            Company.onboarding_status == "pending"
        ).count(),
    }


def get_company(db: Session, company_id: int, *, include_deleted: bool = False) -> Company:
    query = db.query(Company).filter(Company.id == company_id)
    if not include_deleted:
        query = query.filter(Company.is_deleted.is_(False))
    company = query.first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


def update_company(db: Session, actor: User, request: Request, company: Company, changes: dict[str, Any]) -> Company:
    before = {key: getattr(company, "company_metadata" if key == "metadata" else key) for key in changes}
    if "slug" in changes and changes["slug"] != company.slug:
        changes["slug"] = _unique_slug(db, company.name, changes["slug"])
    if "name" in changes and "slug" not in changes:
        changes["slug"] = _unique_slug(db, changes["name"], None)
    _check_unique_company_values(db, changes, company.id)
    for key, value in changes.items():
        setattr(company, "company_metadata" if key == "metadata" else key, value)
    if "status" in changes:
        company.is_active = changes["status"] == "active"
    elif "is_active" in changes:
        company.status = "active" if company.is_active else "inactive"
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="A company with one of these unique fields already exists") from error
    after = {key: getattr(company, "company_metadata" if key == "metadata" else key) for key in changes}
    _audit(db, actor, request, "company.updated", "company", company.id, company.id, {"before": before, "after": after})
    db.commit()
    db.refresh(company)
    return company


def _company_blockers(db: Session, company: Company) -> dict[str, int]:
    branch_ids = db.query(Branch.id).filter(Branch.company_id == company.id)
    employees = db.query(StaffEmployee).filter(
        StaffEmployee.company_id == company.id,
        StaffEmployee.is_active.is_(True),
    ).count()
    if not employees:
        employees = db.query(StaffEmployee).filter(
            StaffEmployee.branch_id.in_(branch_ids),
            StaffEmployee.is_active.is_(True),
        ).count()
    customers = db.query(Customer).filter(
        Customer.is_active.is_(True),
        or_(Customer.company_id == company.id, Customer.branch_id.in_(branch_ids)),
    ).count()
    company_ceos = db.query(User).filter(
        User.company_id == company.id,
        User.is_company_ceo.is_(True),
        User.is_active.is_(True),
    ).count()
    branches = db.query(Branch).filter(Branch.company_id == company.id, Branch.is_active.is_(True)).count()
    pending_orders = db.query(Order).filter(
        Order.branch_id.in_(branch_ids),
        func.lower(Order.status).notin_(("completed", "cancelled", "closed", "fulfilled")),
    ).count()
    return {
        "active_employees": employees,
        "active_customers": customers,
        "active_company_ceos": company_ceos,
        "active_branches": branches,
        "pending_orders": pending_orders,
    }


def soft_delete_company(db: Session, actor: User, request: Request, company: Company, reason: str | None) -> dict[str, Any]:
    blockers = _company_blockers(db, company)
    blocking_counts = {key: count for key, count in blockers.items() if count > 0}
    if blocking_counts:
        raise HTTPException(status_code=400, detail={"message": "Company cannot be deleted while active business records exist", "blockers": blocking_counts})
    before = {"status": company.status, "is_active": company.is_active, "is_deleted": company.is_deleted}
    company.is_deleted = True
    company.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    company.is_active = False
    company.status = "archived"
    db.query(Brand).filter(Brand.company_id == company.id).update({Brand.is_active: False}, synchronize_session=False)
    _audit(db, actor, request, "company.deleted", "company", company.id, company.id, {"before": before, "after": {"status": company.status, "is_active": company.is_active, "is_deleted": True}}, {"reason": reason, "blockers": blockers})
    db.commit()
    return {"company_id": company.id, "deleted": True, "deleted_at": company.deleted_at.isoformat(), "blockers": blockers}


def restore_company(db: Session, actor: User, request: Request, company: Company) -> Company:
    if not company.is_deleted:
        raise HTTPException(status_code=409, detail="Company is not deleted")
    company.is_deleted = False
    company.deleted_at = None
    company.is_active = True
    company.status = "active"
    _audit(db, actor, request, "company.restored", "company", company.id, company.id)
    db.commit()
    db.refresh(company)
    return company


def find_company_ceo(db: Session, company_id: int) -> User | None:
    return (
        db.query(User)
        .filter(User.company_id == company_id, User.is_company_ceo.is_(True), User.is_active.is_(True))
        .order_by(User.ceo_assigned_at.desc(), User.id.desc())
        .first()
    )


def _ensure_company_admin_role(db: Session, company_id: int) -> Role:
    role = db.query(Role).filter(Role.company_id == company_id, Role.slug == "company_admin").first()
    if role is None:
        role = Role(
            company_id=company_id,
            name="Company Admin",
            slug="company_admin",
            description="Company administrator",
            is_active=True,
            is_system_role=False,
        )
        db.add(role)
        db.flush()
    return role


def _record_ceo_profile(db: Session, user: User, company_id: int) -> None:
    profile_type = db.query(ProfileType).filter(ProfileType.code == "company_ceo").first()
    if profile_type is None:
        return
    exists = db.query(ProfileMembership.id).filter(
        ProfileMembership.user_id == user.id,
        ProfileMembership.profile_type_id == profile_type.id,
        ProfileMembership.company_id == company_id,
        ProfileMembership.is_active.is_(True),
    ).first()
    if not exists:
        db.add(ProfileMembership(user_id=user.id, profile_type_id=profile_type.id, company_id=company_id, is_active=True))


def create_company_ceo(db: Session, actor: User, request: Request, company: Company, payload) -> tuple[User, str]:
    if find_company_ceo(db, company.id):
        raise HTTPException(status_code=409, detail="Company already has an active CEO")
    if db.query(User.id).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    if db.query(User.id).filter(func.lower(User.email) == str(payload.email).lower()).first():
        raise HTTPException(status_code=409, detail="Email already exists")

    now = datetime.utcnow()
    user = User(
        username=payload.username,
        email=str(payload.email),
        hashed_password=auth_guard.hash_password(payload.password),
        role="company_ceo",
        company_id=company.id,
        current_company_id=company.id,
        branch_id=None,
        is_active=True,
        is_company_ceo=True,
        ceo_assigned_at=now,
        ceo_assigned_by=actor.id,
        force_password_change=True,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
    )
    db.add(user)
    try:
        db.flush()
        role = _ensure_company_admin_role(db, company.id)
        db.add(UserRole(user_id=user.id, role_id=role.id, company_id=company.id, is_active=True))
        _record_ceo_profile(db, user, company.id)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="CEO username or email already exists") from error
    _audit(db, actor, request, "ceo.assigned", "user", user.id, company.id, extra={"username": user.username})
    db.commit()
    db.refresh(user)
    return user, payload.password


def update_company_ceo(db: Session, actor: User, request: Request, company_id: int, user: User, changes: dict[str, Any]) -> User:
    if "email" in changes and changes["email"]:
        changes["email"] = str(changes["email"])
        duplicate = db.query(User.id).filter(func.lower(User.email) == changes["email"].lower(), User.id != user.id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Email already exists")
    before = {key: getattr(user, key) for key in changes}
    for key, value in changes.items():
        setattr(user, key, value)
    after = {key: getattr(user, key) for key in changes}
    _audit(db, actor, request, "ceo.updated", "user", user.id, company_id, {"before": before, "after": after})
    db.commit()
    db.refresh(user)
    return user


def generate_secure_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(24))
        valid, _ = validate_password_strength(candidate)
        if valid:
            return candidate


def reset_company_ceo_password(db: Session, actor: User, request: Request, company_id: int, user: User) -> str:
    from app.services.token_revocation import revoke_user_sessions

    password = generate_secure_password()
    user.hashed_password = auth_guard.hash_password(password)
    user.password_changed_at = datetime.utcnow()
    user.force_password_change = True
    _audit(db, actor, request, "ceo.password_reset", "user", user.id, company_id, extra={"username": user.username})
    db.commit()
    revoke_user_sessions(user.id)
    return password


def remove_company_ceo(db: Session, actor: User, request: Request, company_id: int, user: User) -> None:
    before = {"company_id": user.company_id, "current_company_id": user.current_company_id, "is_company_ceo": user.is_company_ceo, "role": user.role}
    user.company_id = None
    user.current_company_id = None
    user.is_company_ceo = False
    user.ceo_assigned_at = None
    user.ceo_assigned_by = None
    user.role = "StaffEmployee"
    db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.company_id == company_id).update({UserRole.is_active: False}, synchronize_session=False)
    db.query(ProfileMembership).filter(ProfileMembership.user_id == user.id, ProfileMembership.company_id == company_id).update({ProfileMembership.is_active: False}, synchronize_session=False)
    _audit(db, actor, request, "ceo.removed", "user", user.id, company_id, {"before": before, "after": {"company_id": None, "is_company_ceo": False}})
    db.commit()


def company_metrics(db: Session, company: Company) -> dict[str, Any]:
    branch_query = db.query(Branch).filter(Branch.company_id == company.id)
    branch_ids = db.query(Branch.id).filter(Branch.company_id == company.id)
    branches = branch_query.filter(Branch.is_active.is_(True)).count()
    employees = db.query(StaffEmployee).filter(
        StaffEmployee.is_active.is_(True),
        or_(StaffEmployee.company_id == company.id, StaffEmployee.branch_id.in_(branch_ids)),
    ).count()
    customers = db.query(Customer).filter(
        Customer.is_active.is_(True),
        or_(Customer.company_id == company.id, Customer.branch_id.in_(branch_ids)),
    ).count()
    revenue = (
        db.query(func.coalesce(func.sum(DailyAnalyticsSnapshot.total_revenue), 0))
        .join(Branch, Branch.id == DailyAnalyticsSnapshot.branch_id)
        .filter(Branch.company_id == company.id)
        .scalar()
        or 0
    )
    return {"company_id": company.id, "branches": branches, "employees": employees, "customers": customers, "revenue": float(revenue)}


def company_audit_events(
    db: Session,
    company_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
    action: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    query = (
        db.query(CeoAuditLog)
        .filter(CeoAuditLog.request_meta["company_id"].as_integer() == company_id)
    )
    if action:
        query = query.filter(CeoAuditLog.action == action)
    total = query.count()
    rows = (
        query.order_by(CeoAuditLog.created_at.desc(), CeoAuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    events = [
        {
            "id": row.id,
            "actor_id": row.user_id,
            "action": row.action,
            "resource_id": row.request_meta.get("resource_id"),
            "changes": row.request_meta.get("changes", {}),
            "metadata": row.request_meta.get("metadata", {}),
            "ip_address": row.request_meta.get("ip_address"),
            "user_agent": row.request_meta.get("user_agent"),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    return events, total


def company_envelope(data: Any, company: Company | None = None) -> dict[str, Any]:
    scope = ResolvedScope(
        level="company" if company else "system",
        company_ids=(company.id,) if company else (),
        company_id=company.id if company else None,
    )
    return envelope(data, scope, source_status="complete")
