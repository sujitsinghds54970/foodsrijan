from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, User
from app.schemas.outlet import (
    OUTLET_REGIONS,
    OUTLET_STATUSES,
    OUTLET_TYPES,
    ManagerCreate,
    ManagerTestLogin,
    ManagerUpdate,
    OutletCreate,
    OutletUpdate,
    normalize_choice,
)
from app.services import outlet_service
from app.schemas.login_credentials import LoginCredentialsUpdate
from app.services.login_credentials import login_credentials, update_login_credentials
from app.services.executive_metrics import ResolvedScope, envelope
from app.services.rate_limit import record_rate_limited_attempt
from app.utils.auth_system import auth_guard
from app.utils.guards import CompanyCeoContext, company_ceo_context
from app.utils.validators import sanitize_text


router = APIRouter(prefix="/company-ceo/outlets", tags=["Company CEO Outlets"])


def _envelope(data: Any, context: CompanyCeoContext, outlet_id: int | None = None) -> dict[str, Any]:
    return envelope(
        data,
        ResolvedScope(level="branch" if outlet_id else "company", company_ids=(context.company_id,), company_id=context.company_id, branch_id=outlet_id),
        source_status="complete",
        sources=["branches", "users", "ceo_audit_logs"],
        ttl_seconds=60,
    )


def _outlet(context: CompanyCeoContext, db: Session, outlet_id: int, *, include_deleted: bool = False) -> Branch:
    return outlet_service.get_scoped_outlet(db, context.company_id, outlet_id, include_deleted=include_deleted)


def _manager_or_404(context: CompanyCeoContext, db: Session, outlet: Branch) -> User:
    manager = outlet_service.find_outlet_manager(db, context.company_id, outlet.id)
    if manager is None:
        raise HTTPException(status_code=404, detail="Outlet manager not found")
    return manager


def _choice(value: str | None, choices: dict[str, str], label: str) -> str | None:
    try:
        return normalize_choice(value, choices, label)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _payload_values(payload) -> dict[str, Any]:
    values = payload.model_dump(exclude_unset=True, by_alias=False)
    return values


@router.get("")
def list_outlets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
    city: str | None = Query(default=None, max_length=100),
    region: str | None = Query(default=None, max_length=40),
    outlet_type: str | None = Query(default=None, max_length=40),
    search: str | None = Query(default=None, max_length=100),
    include_deleted: bool = Query(default=False),
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    rows, total = outlet_service.list_outlets(
        db,
        context.company_id,
        page=page,
        page_size=page_size,
        status=_choice(status_filter, OUTLET_STATUSES, "outlet status"),
        city=sanitize_text(city) if city else None,
        region=_choice(region, OUTLET_REGIONS, "region"),
        outlet_type=_choice(outlet_type, OUTLET_TYPES, "outlet type"),
        search=sanitize_text(search) if search else None,
        include_deleted=include_deleted,
    )
    return _envelope(
        {"outlets": outlet_service.serialize_outlets(db, context.company_id, rows), "total": total, "page": page, "page_size": page_size},
        context,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_outlet(
    payload: OutletCreate,
    request: Request,
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    record_rate_limited_attempt(db, context.user, "create_outlet")
    outlet = outlet_service.create_outlet(db, context.user, context.company, request, _payload_values(payload))
    return _envelope({"outlet": outlet_service.outlet_detail(db, context.company_id, outlet)}, context, outlet.id)


@router.get("/stats")
def outlet_stats(
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    return _envelope({"stats": outlet_service.outlet_stats(db, context.company_id)}, context)


@router.get("/{outlet_id}")
def get_outlet(
    outlet_id: int,
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    outlet = _outlet(context, db, outlet_id, include_deleted=True)
    return _envelope({"outlet": outlet_service.outlet_detail(db, context.company_id, outlet)}, context, outlet.id)


@router.put("/{outlet_id}")
def update_outlet(
    outlet_id: int,
    payload: OutletUpdate,
    request: Request,
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    outlet = _outlet(context, db, outlet_id)
    changes = _payload_values(payload)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one outlet field must be provided")
    outlet = outlet_service.update_outlet(db, context.user, context.company, request, outlet, changes)
    return _envelope({"outlet": outlet_service.outlet_detail(db, context.company_id, outlet)}, context, outlet.id)


@router.delete("/{outlet_id}")
def delete_outlet(
    outlet_id: int,
    request: Request,
    reason: str | None = Query(default=None, max_length=1000),
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    outlet = _outlet(context, db, outlet_id)
    result = outlet_service.soft_delete_outlet(db, context.user, context.company, request, outlet, sanitize_text(reason))
    return _envelope(result, context, outlet.id)


@router.post("/{outlet_id}/restore")
def restore_outlet(
    outlet_id: int,
    request: Request,
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    outlet = _outlet(context, db, outlet_id, include_deleted=True)
    outlet = outlet_service.restore_outlet(db, context.user, context.company, request, outlet)
    return _envelope({"outlet": outlet_service.outlet_detail(db, context.company_id, outlet)}, context, outlet.id)


@router.get("/{outlet_id}/audit")
def outlet_audit(
    outlet_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None, max_length=80),
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    outlet = _outlet(context, db, outlet_id, include_deleted=True)
    events, total = outlet_service.outlet_audit_events(db, context.company_id, outlet.id, page=page, page_size=page_size, action=action)
    return _envelope({"outlet_id": outlet.id, "events": events, "total": total, "page": page, "page_size": page_size}, context, outlet.id)


@router.post("/{outlet_id}/manager", status_code=status.HTTP_201_CREATED)
def create_outlet_manager(
    outlet_id: int,
    payload: ManagerCreate,
    request: Request,
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    record_rate_limited_attempt(db, context.user, "create_outlet_manager")
    outlet = _outlet(context, db, outlet_id)
    manager, plain_password = outlet_service.create_manager(db, context.user, context.company, request, outlet, payload)
    return _envelope(
        {
            "manager": outlet_service.serialize_manager(manager),
            "credentials": outlet_service.credentials_payload(
                manager.username, plain_password, "Save these credentials. Password will not be shown again."
            ),
        },
        context,
        outlet.id,
    )


@router.get("/{outlet_id}/manager")
def get_outlet_manager(
    outlet_id: int,
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    outlet = _outlet(context, db, outlet_id, include_deleted=True)
    manager = _manager_or_404(context, db, outlet)
    return _envelope({"manager": outlet_service.serialize_manager(manager)}, context, outlet.id)


@router.get("/{outlet_id}/manager/credentials")
def get_manager_credentials(
    outlet_id: int, response: Response,
    context: CompanyCeoContext = Depends(company_ceo_context), db: Session = Depends(get_db),
):
    outlet = _outlet(context, db, outlet_id)
    manager = _manager_or_404(context, db, outlet)
    response.headers["Cache-Control"] = "no-store"
    return _envelope({"login": login_credentials(manager)}, context, outlet.id)


@router.patch("/{outlet_id}/manager/credentials")
def edit_manager_credentials(
    outlet_id: int, payload: LoginCredentialsUpdate, request: Request, response: Response,
    context: CompanyCeoContext = Depends(company_ceo_context), db: Session = Depends(get_db),
):
    outlet = _outlet(context, db, outlet_id)
    manager = _manager_or_404(context, db, outlet)
    response.headers["Cache-Control"] = "no-store"
    return _envelope(update_login_credentials(db, context.user, request, manager, payload, "manager"), context, outlet.id)


@router.put("/{outlet_id}/manager")
def update_outlet_manager(
    outlet_id: int,
    payload: ManagerUpdate,
    request: Request,
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    outlet = _outlet(context, db, outlet_id)
    manager = _manager_or_404(context, db, outlet)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one manager field must be provided")
    manager = outlet_service.update_manager(db, context.user, context.company, request, outlet, manager, changes)
    return _envelope({"manager": outlet_service.serialize_manager(manager)}, context, outlet.id)


@router.post("/{outlet_id}/manager/reset-password")
def reset_outlet_manager_password(
    outlet_id: int,
    request: Request,
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    record_rate_limited_attempt(db, context.user, "reset_outlet_manager_password")
    outlet = _outlet(context, db, outlet_id)
    manager = _manager_or_404(context, db, outlet)
    password = outlet_service.reset_manager_password(db, context.user, context.company, request, outlet, manager)
    return _envelope(
        {
            "manager": outlet_service.serialize_manager(manager),
            "credentials": outlet_service.credentials_payload(
                manager.username, password, "Save this password now. It will not be shown again."
            ),
        },
        context,
        outlet.id,
    )


@router.delete("/{outlet_id}/manager")
def remove_outlet_manager(
    outlet_id: int,
    request: Request,
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    outlet = _outlet(context, db, outlet_id, include_deleted=True)
    manager = _manager_or_404(context, db, outlet)
    outlet_service.remove_manager(db, context.user, context.company, request, outlet, manager)
    return _envelope({"outlet_id": outlet.id, "manager_removed": True, "manager_id": manager.id}, context, outlet.id)


@router.post("/{outlet_id}/manager/test-login")
def test_outlet_manager_login(
    outlet_id: int,
    payload: ManagerTestLogin,
    context: CompanyCeoContext = Depends(company_ceo_context),
    db: Session = Depends(get_db),
):
    record_rate_limited_attempt(db, context.user, "test_outlet_manager_login")
    outlet = _outlet(context, db, outlet_id)
    manager = _manager_or_404(context, db, outlet)
    valid = manager.username == payload.username and auth_guard.verify_password(payload.password, manager.hashed_password)
    return _envelope({"valid": bool(valid), "outlet_id": outlet.id, "manager_id": manager.id}, context, outlet.id)
