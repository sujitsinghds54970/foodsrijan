from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Brand, Branch, Company, Department, User
from app.services import company_service
from app.services.executive_metrics import ResolvedScope, envelope
from app.utils.auth_system import get_current_user


router = APIRouter(prefix="/company-ceo", tags=["Company CEO"])


def require_company_ceo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> tuple[User, Company]:
    if current_user.role.strip().lower() != "company_ceo" or not current_user.is_company_ceo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company CEO access required",
        )
    company_id = current_user.current_company_id or current_user.company_id
    if not company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active company assignment is required",
        )
    company = (
        db.query(Company)
        .filter(
            Company.id == company_id,
            Company.is_active.is_(True),
            Company.is_deleted.is_(False),
        )
        .first()
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The assigned company is not active",
        )
    return current_user, company


def _company_ceo_envelope(data: Any, company: Company) -> dict[str, Any]:
    return envelope(
        data,
        ResolvedScope(
            level="company",
            company_ids=(company.id,),
            company_id=company.id,
        ),
        source_status="complete",
        sources=[
            "companies",
            "branches",
            "brands",
            "departments",
            "users",
            "ceo_audit_logs",
        ],
        ttl_seconds=120,
    )


@router.get("/workspace")
def get_company_ceo_workspace(
    context: tuple[User, Company] = Depends(require_company_ceo),
    db: Session = Depends(get_db),
):
    current_user, company = context
    branches = (
        db.query(Branch)
        .filter(Branch.company_id == company.id)
        .order_by(Branch.is_active.desc(), Branch.name.asc())
        .all()
    )
    brands = (
        db.query(Brand)
        .filter(Brand.company_id == company.id)
        .order_by(Brand.is_active.desc(), Brand.name.asc())
        .all()
    )
    departments = (
        db.query(Department)
        .filter(Department.company_id == company.id)
        .order_by(Department.is_active.desc(), Department.name.asc())
        .all()
    )
    active_users = (
        db.query(func.count(User.id))
        .filter(User.company_id == company.id, User.is_active.is_(True))
        .scalar()
        or 0
    )
    audit_events, audit_total = company_service.company_audit_events(
        db,
        company.id,
        page=1,
        page_size=20,
    )
    metrics = company_service.company_metrics(db, company)
    return _company_ceo_envelope(
        {
            "executive": company_service.serialize_ceo(current_user),
            "company": company_service.serialize_company(company),
            "metrics": {**metrics, "active_users": int(active_users)},
            "branches": [
                {
                    "id": branch.id,
                    "name": branch.name,
                    "branch_code": branch.branch_code,
                    "city": branch.city,
                    "state": branch.state,
                    "is_active": branch.is_active,
                }
                for branch in branches
            ],
            "brands": [
                {
                    "id": brand.id,
                    "name": brand.name,
                    "slug": brand.slug,
                    "description": brand.description,
                    "is_active": brand.is_active,
                }
                for brand in brands
            ],
            "departments": [
                {
                    "id": department.id,
                    "name": department.name,
                    "code": department.code,
                    "description": department.description,
                    "is_active": department.is_active,
                }
                for department in departments
            ],
            "audit": {"events": audit_events, "total": audit_total},
        },
        company,
    )
