from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Query, Session

from app.models import Branch
from app.services.executive_metrics import ResolvedScope


def branch_scoped_query(db: Session, model: Any, scope: ResolvedScope) -> Query:
    query = db.query(model)
    if not hasattr(model, "branch_id"):
        return query.filter(False)
    if scope.branch_id is not None:
        return query.filter(model.branch_id == scope.branch_id)
    if scope.brand_id is not None:
        return query.join(Branch, Branch.id == model.branch_id).filter(Branch.brand_id == scope.brand_id)
    if scope.company_ids:
        return query.join(Branch, Branch.id == model.branch_id).filter(Branch.company_id.in_(scope.company_ids))
    return query.filter(False)


def company_scoped_query(db: Session, model: Any, scope: ResolvedScope) -> Query:
    query = db.query(model)
    if not hasattr(model, "company_id"):
        return query.filter(False)
    if scope.company_id is not None:
        return query.filter(model.company_id == scope.company_id)
    if scope.company_ids:
        return query.filter(model.company_id.in_(scope.company_ids))
    return query.filter(False)
