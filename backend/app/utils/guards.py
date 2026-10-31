"""Tenant-scoped authorization guards.

Scope is always derived from the authenticated user record, never from
client-supplied identifiers.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, Company, User
from app.utils.auth_system import get_current_user


COMPANY_CEO_ROLE = "company_ceo"
OUTLET_MANAGER_ROLE = "outlet_manager"
STAFF_ROLE = "staff"


@dataclass(frozen=True)
class CompanyCeoContext:
    user: User
    company: Company

    @property
    def company_id(self) -> int:
        return self.company.id


@dataclass(frozen=True)
class OutletManagerContext:
    user: User
    outlet: Branch
    company: Company

    @property
    def company_id(self) -> int:
        return self.company.id

    @property
    def outlet_id(self) -> int:
        return self.outlet.id


@dataclass(frozen=True)
class StaffContext:
    user: User
    outlet: Branch
    company: Company

    @property
    def company_id(self) -> int:
        return self.company.id

    @property
    def outlet_id(self) -> int:
        return self.outlet.id


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _active_company(db: Session, company_id: int | None) -> Company:
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.is_active.is_(True), Company.is_deleted.is_(False))
        .first()
        if company_id
        else None
    )
    if company is None:
        raise _forbidden("The assigned company is not active")
    return company


def require_company_ceo(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_company_ceo or (current_user.role or "").strip().lower() != COMPANY_CEO_ROLE:
        raise _forbidden("Company CEO access required")
    if getattr(current_user, "is_outlet_manager", False):
        raise _forbidden("Company CEO access required")
    if not current_user.company_id:
        raise _forbidden("No company assigned")
    return current_user


def require_outlet_manager(current_user: User = Depends(get_current_user)) -> User:
    if not getattr(current_user, "is_outlet_manager", False) or (current_user.role or "").strip().lower() != OUTLET_MANAGER_ROLE:
        raise _forbidden("Outlet Manager access required")
    if current_user.is_company_ceo or getattr(current_user, "is_super_ceo", False):
        raise _forbidden("Outlet Manager access required")
    if not current_user.outlet_id:
        raise _forbidden("No outlet assigned")
    if not current_user.company_id:
        raise _forbidden("No company assigned")
    return current_user


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    if not getattr(current_user, "is_staff", False) or (current_user.role or "").strip().lower() != STAFF_ROLE:
        raise _forbidden("Staff access required")
    if current_user.is_company_ceo or getattr(current_user, "is_super_ceo", False) or getattr(current_user, "is_outlet_manager", False):
        raise _forbidden("Staff access required")
    outlet_id = current_user.outlet_id or current_user.branch_id
    if not outlet_id:
        raise _forbidden("No outlet assigned")
    if not current_user.company_id:
        raise _forbidden("No company assigned")
    if not current_user.is_active or getattr(current_user, "is_deleted", False):
        raise _forbidden("Staff account is inactive")
    return current_user


def company_ceo_context(
    current_user: User = Depends(require_company_ceo),
    db: Session = Depends(get_db),
) -> CompanyCeoContext:
    # CEO scope is the company the CEO is assigned to; current_company_id must not widen it.
    return CompanyCeoContext(user=current_user, company=_active_company(db, current_user.company_id))


def outlet_manager_context(
    current_user: User = Depends(require_outlet_manager),
    db: Session = Depends(get_db),
) -> OutletManagerContext:
    company = _active_company(db, current_user.company_id)
    outlet = (
        db.query(Branch)
        .filter(
            Branch.id == current_user.outlet_id,
            Branch.company_id == company.id,
            Branch.is_deleted.is_(False),
        )
        .first()
    )
    if outlet is None:
        raise _forbidden("The assigned outlet is not available")
    return OutletManagerContext(user=current_user, outlet=outlet, company=company)


def staff_context(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> StaffContext:
    company = _active_company(db, current_user.company_id)
    resolved_outlet_id = current_user.outlet_id or current_user.branch_id
    outlet = (
        db.query(Branch)
        .filter(
            Branch.id == resolved_outlet_id,
            Branch.company_id == company.id,
            Branch.is_deleted.is_(False),
        )
        .first()
    )
    if outlet is None:
        raise _forbidden("The assigned outlet is not available")
    return StaffContext(user=current_user, outlet=outlet, company=company)
