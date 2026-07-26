import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch

router = APIRouter()


def _request_base_url(request: Request) -> str:
    url = request.base_url
    return f"{url.scheme}://{url.netloc}".rstrip("/")


def _to_public_file_url(request: Request, path: Optional[str]) -> Optional[str]:
    raw = (path or "").strip()
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("/api/files/"):
        return f"{_request_base_url(request)}{raw}"
    return f"{_request_base_url(request)}/api/files/{raw.lstrip('/')}"


@router.get("/public/branding")
def get_public_branding(request: Request, db: Session = Depends(get_db)):
    branding_row = db.execute(
        text(
            """
            SELECT setting_value
            FROM system_settings
            WHERE setting_key IN ('ceo_branding', 'branding')
            ORDER BY CASE WHEN setting_key = 'ceo_branding' THEN 0 ELSE 1 END
            LIMIT 1
            """
        )
    ).scalar()

    branding_payload: dict = {}
    if isinstance(branding_row, str) and branding_row.strip():
        try:
            parsed = json.loads(branding_row)
            if isinstance(parsed, dict):
                branding_payload = parsed
        except json.JSONDecodeError:
            branding_payload = {}

    primary_logo_raw = (
        (branding_payload.get("assets") or {}).get("primary_logo_url")
        or (branding_payload.get("branding_asset_manager") or {}).get("primary_logo_web")
        or branding_payload.get("logo_url")
        or ""
    )

    company_name = (branding_payload.get("company_name") or "").strip()
    if not company_name:
        company_setting = db.execute(
            text("SELECT setting_value FROM system_settings WHERE setting_key = 'company_name' LIMIT 1")
        ).scalar()
        company_name = (company_setting or "").strip()

    tagline = (
        (branding_payload.get("tagline") or "").strip()
        or ((branding_payload.get("company_profile") or {}).get("tagline") or "").strip()
    )
    if not tagline:
        tagline_setting = db.execute(
            text("SELECT setting_value FROM system_settings WHERE setting_key = 'tagline' LIMIT 1")
        ).scalar()
        tagline = (tagline_setting or "").strip()

    return {
        "primary_logo_url": _to_public_file_url(request, primary_logo_raw),
        "company_name": company_name or "VaidyaVihar Diagnostic",
        "tagline": tagline,
    }


@router.get("/public/branches")
def get_public_branches(db: Session = Depends(get_db)):
    branches = (
        db.query(Branch)
        .filter(Branch.is_active == True)
        .order_by(Branch.name.asc())
        .all()
    )
    return [
        {
            "id": branch.id,
            "name": branch.name,
        }
        for branch in branches
    ]
