from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routes.super_ceo.profile import resolve_profile_actor
from app.services.audit_service import write_ceo_audit
from app.services.file_storage import save_upload
from app.utils.auth_system import require_super_admin


router = APIRouter(prefix="/uploads", tags=["Super CEO Uploads"])


async def _upload(file: UploadFile, category: str, request: Request, db: Session, actor: User):
    result = await save_upload(file, category, actor.id)
    write_ceo_audit(db, actor, request, f"upload.{category}", {"asset": result})
    db.commit()
    return {"data": result, "errors": []}


@router.post("/profile-photo")
async def upload_profile_photo(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db), actor: User = Depends(resolve_profile_actor)):
    return await _upload(file, "profile-photos", request, db, actor)


@router.post("/cover-photo")
async def upload_cover_photo(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db), actor: User = Depends(resolve_profile_actor)):
    return await _upload(file, "cover-photos", request, db, actor)


@router.post("/company-logo")
async def upload_company_logo(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    return await _upload(file, "company-logos", request, db, actor)


@router.post("/company-banner")
async def upload_company_banner(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db), actor: User = Depends(require_super_admin)):
    return await _upload(file, "company-banners", request, db, actor)
