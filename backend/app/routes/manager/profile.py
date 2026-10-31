from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.outlet import ManagerOutletUpdate, ManagerSelfUpdate
from app.services import outlet_service
from app.services.company_service import serialize_company
from app.services.executive_metrics import ResolvedScope, envelope
from app.utils.guards import OutletManagerContext, outlet_manager_context


router = APIRouter(prefix="/manager", tags=["Outlet Manager"])

COMPANY_PUBLIC_FIELDS = ("id", "name", "slug", "tagline", "logo_url", "primary_color", "secondary_color", "accent_color")


def _envelope(data: Any, context: OutletManagerContext) -> dict[str, Any]:
    return envelope(
        data,
        ResolvedScope(level="branch", company_ids=(context.company_id,), company_id=context.company_id, branch_id=context.outlet_id),
        source_status="complete",
        sources=["users", "branches"],
        ttl_seconds=60,
    )


def _self_profile(context: OutletManagerContext) -> dict[str, Any]:
    user = context.user
    company = serialize_company(context.company)
    return {
        "manager": {
            **outlet_service.serialize_manager(user),
            "display_name": user.display_name,
            "bio": user.bio,
            "profile_photo_url": user.profile_photo_url,
            "cover_photo_url": user.cover_photo_url,
            "timezone": user.timezone,
            "emergency_contact_name": user.emergency_contact_name,
            "emergency_contact_phone": user.emergency_contact_phone,
            "preferred_contact_method": user.preferred_contact_method,
            "preferences": user.preferences,
        },
        "outlet": outlet_service.serialize_outlet(context.outlet, for_manager=True),
        "company": {key: company.get(key) for key in COMPANY_PUBLIC_FIELDS},
    }


@router.get("/me")
def get_me(context: OutletManagerContext = Depends(outlet_manager_context)):
    return _envelope(_self_profile(context), context)


@router.put("/me")
def update_me(
    payload: ManagerSelfUpdate,
    request: Request,
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one profile field must be provided")
    outlet_service.update_manager_self(db, context.user, context.company, context.outlet, request, changes)
    return _envelope(_self_profile(context), context)


@router.get("/outlet")
def get_outlet(context: OutletManagerContext = Depends(outlet_manager_context)):
    return _envelope({"outlet": outlet_service.serialize_outlet(context.outlet, for_manager=True)}, context)


@router.put("/outlet")
def update_outlet(
    payload: ManagerOutletUpdate,
    request: Request,
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one outlet field must be provided")
    outlet = outlet_service.update_outlet_by_manager(db, context.user, context.company, context.outlet, request, changes)
    return _envelope({"outlet": outlet_service.serialize_outlet(outlet, for_manager=True)}, context)


@router.get("/me/stats")
def get_my_stats(
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    return _envelope({"stats": outlet_service.manager_stats(db, context.company_id, context.outlet)}, context)
