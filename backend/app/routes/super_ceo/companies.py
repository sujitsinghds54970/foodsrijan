import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, User
from app.services import company_service
from app.services.rate_limit import record_rate_limited_attempt
from app.utils.auth_system import auth_guard, require_super_admin
from app.utils.validators import sanitize_text
from app.schemas.ceo import CEOCreateRequest, CEOProfileUpdate, CEOTestLoginRequest
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.schemas.login_credentials import LoginCredentialsUpdate
from app.services.login_credentials import login_credentials, update_login_credentials


router = APIRouter(prefix="/super-ceo/companies", tags=["Super CEO Companies"])


def _company_or_404(db: Session, company_id: int, *, include_deleted: bool = False) -> Company:
    return company_service.get_company(db, company_id, include_deleted=include_deleted)


def _company_detail(db: Session, company: Company) -> dict[str, Any]:
    result = company_service.serialize_company(company)
    result["ceo"] = company_service.serialize_ceo(company_service.find_company_ceo(db, company.id))
    return result


@router.post("", status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    record_rate_limited_attempt(db, actor, "create_company")
    values = payload.model_dump(exclude_unset=True)
    if "metadata" in payload.model_fields_set:
        values["metadata"] = payload.company_metadata
    company = company_service.create_company(db, actor, request, values)
    return company_service.company_envelope({"company": company_service.serialize_company(company)}, company)


@router.get("")
def list_companies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status", pattern=r"^(active|inactive|suspended|archived)$"),
    business_domain: str | None = Query(default=None, max_length=64),
    search: str | None = Query(default=None, max_length=150),
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    rows, total = company_service.list_companies(
        db,
        page=page,
        page_size=page_size,
        status=status_filter,
        business_domain=business_domain,
        search=search,
        include_deleted=include_deleted,
    )
    data = {"companies": [company_service.serialize_company(row) for row in rows], "total": total, "page": page, "page_size": page_size}
    return company_service.company_envelope(data)


@router.get("/stats")
def get_company_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    return company_service.company_envelope(
        {"stats": company_service.company_portfolio_stats(db)}
    )


@router.get("/{company_id}")
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id)
    return company_service.company_envelope({"company": _company_detail(db, company)}, company)


@router.put("/{company_id}")
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id)
    changes = payload.model_dump(exclude_unset=True)
    if "metadata" in payload.model_fields_set:
        changes["metadata"] = payload.company_metadata
    if not changes:
        raise HTTPException(status_code=422, detail="At least one company field must be provided")
    company = company_service.update_company(db, actor, request, company, changes)
    return company_service.company_envelope({"company": company_service.serialize_company(company)}, company)


@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    request: Request,
    reason: str | None = Query(default=None, max_length=1000),
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id)
    result = company_service.soft_delete_company(db, actor, request, company, sanitize_text(reason))
    return company_service.company_envelope(result, company)


@router.post("/{company_id}/restore")
def restore_company(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id, include_deleted=True)
    company = company_service.restore_company(db, actor, request, company)
    return company_service.company_envelope({"company": company_service.serialize_company(company)}, company)


@router.get("/{company_id}/audit")
def get_company_audit(
    company_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id, include_deleted=True)
    events, total = company_service.company_audit_events(
        db,
        company.id,
        page=page,
        page_size=page_size,
        action=action,
    )
    return company_service.company_envelope(
        {
            "company_id": company.id,
            "events": events,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        company,
    )


@router.post("/{company_id}/ceo", status_code=status.HTTP_201_CREATED)
def create_company_ceo(
    company_id: int,
    payload: CEOCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    record_rate_limited_attempt(db, actor, "assign_company_ceo")
    company = _company_or_404(db, company_id)
    ceo, plain_password = company_service.create_company_ceo(db, actor, request, company, payload)
    frontend_url = os.getenv("FRONTEND_URL", "https://vaidyavihar.com").rstrip("/")
    return company_service.company_envelope(
        {
            "ceo": company_service.serialize_ceo(ceo),
            "credentials": {
                "login_url": f"{frontend_url}/login",
                "username": ceo.username,
                "password": plain_password,
                "note": "Save these credentials. Password will not be shown again.",
            },
        },
        company,
    )


@router.get("/{company_id}/ceo")
def get_company_ceo(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id)
    ceo = company_service.find_company_ceo(db, company.id)
    return company_service.company_envelope({"ceo": company_service.serialize_ceo(ceo)}, company)


@router.put("/{company_id}/ceo")
def update_company_ceo(
    company_id: int,
    payload: CEOProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id)
    ceo = company_service.find_company_ceo(db, company.id)
    if ceo is None:
        raise HTTPException(status_code=404, detail="Company CEO not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one CEO field must be provided")
    ceo = company_service.update_company_ceo(db, actor, request, company.id, ceo, changes)
    return company_service.company_envelope({"ceo": company_service.serialize_ceo(ceo)}, company)


@router.get("/{company_id}/ceo/credentials")
def get_ceo_credentials(
    company_id: int, response: Response,
    db: Session = Depends(get_db), _: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id)
    ceo = company_service.find_company_ceo(db, company.id)
    if ceo is None:
        raise HTTPException(404, "Company CEO not found")
    response.headers["Cache-Control"] = "no-store"
    return company_service.company_envelope({"login": login_credentials(ceo)}, company)


@router.patch("/{company_id}/ceo/credentials")
def edit_ceo_credentials(
    company_id: int, payload: LoginCredentialsUpdate, request: Request, response: Response,
    db: Session = Depends(get_db), actor: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id)
    ceo = company_service.find_company_ceo(db, company.id)
    if ceo is None:
        raise HTTPException(404, "Company CEO not found")
    response.headers["Cache-Control"] = "no-store"
    return company_service.company_envelope(
        update_login_credentials(db, actor, request, ceo, payload, "ceo"), company,
    )


@router.post("/{company_id}/ceo/reset-password")
def reset_company_ceo_password(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    record_rate_limited_attempt(db, actor, "reset_company_ceo_password")
    company = _company_or_404(db, company_id)
    ceo = company_service.find_company_ceo(db, company.id)
    if ceo is None:
        raise HTTPException(status_code=404, detail="Company CEO not found")
    password = company_service.reset_company_ceo_password(db, actor, request, company.id, ceo)
    return company_service.company_envelope(
        {
            "ceo": company_service.serialize_ceo(ceo),
            "credentials": {
                "login_url": f"{os.getenv('FRONTEND_URL', 'https://vaidyavihar.com').rstrip('/')}/login",
                "username": ceo.username,
                "password": password,
                "note": "Save this password now. It will not be shown again.",
            },
        },
        company,
    )


@router.delete("/{company_id}/ceo")
def remove_company_ceo(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id)
    ceo = company_service.find_company_ceo(db, company.id)
    if ceo is None:
        raise HTTPException(status_code=404, detail="Company CEO not found")
    company_service.remove_company_ceo(db, actor, request, company.id, ceo)
    return company_service.company_envelope({"company_id": company.id, "ceo_removed": True}, company)


@router.post("/{company_id}/ceo/test-login")
def test_company_ceo_login(
    company_id: int,
    payload: CEOTestLoginRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id)
    ceo = company_service.find_company_ceo(db, company.id)
    if ceo is None:
        raise HTTPException(status_code=404, detail="Company CEO not found")
    valid = ceo.username == payload.username and auth_guard.verify_password(payload.password, ceo.hashed_password)
    return company_service.company_envelope({"valid": bool(valid), "company_id": company.id}, company)


@router.get("/{company_id}/metrics")
def get_company_metrics(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    company = _company_or_404(db, company_id)
    metrics = company_service.company_metrics(db, company)
    return company_service.company_envelope({"metrics": metrics}, company)
