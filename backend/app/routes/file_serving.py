"""
File Serving Routes
Serves uploaded files (PDFs, images, etc.) from the uploads directory
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
import os
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Doctor, User
from app.models.daily_entry_module import DailyEntryModule
from app.models.doctor import DoctorBranch
from app.models.doctor_portal import DoctorAuditLog
from app.utils.auth_system import auth_guard

router = APIRouter()

ALLOWED_FILE_ROLES = {"super_admin", "branch_admin", "branch_director", "staff", "patient"}

# Get the uploads directory path - try multiple possible locations
BASE_DIR = Path(__file__).parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"

# Also check for daily_entry_reports subdirectory
DAILY_ENTRY_REPORTS_DIR = UPLOADS_DIR / "daily_entry_reports"


def _doctor_for_user(current_user: User, db: Session) -> Optional[Doctor]:
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if doctor:
        return doctor
    if current_user.email:
        return db.query(Doctor).filter(Doctor.email == current_user.email).first()
    return None


def _doctor_branch_ids(doctor_id: int, db: Session) -> set[int]:
    rows = db.query(DoctorBranch.branch_id).filter(DoctorBranch.doctor_id == doctor_id, DoctorBranch.is_active.is_(True)).all()
    return {row[0] for row in rows}


def _extract_daily_report_filename(filename: str) -> Optional[str]:
    normalized = filename.lstrip("/")
    if normalized.startswith("uploads/daily_entry_reports/"):
        return normalized.split("uploads/daily_entry_reports/", 1)[1]
    if normalized.startswith("daily_entry_reports/"):
        return normalized.split("daily_entry_reports/", 1)[1]
    if normalized.lower().endswith(".pdf"):
        return os.path.basename(normalized)
    return None


def _enforce_doctor_report_access(filename: str, current_user: User, db: Session) -> None:
    if current_user.role != "doctor":
        return

    doctor = _doctor_for_user(current_user, db)
    if not doctor or not doctor.is_active:
        raise HTTPException(status_code=403, detail="Doctor profile is not configured")

    report_file = _extract_daily_report_filename(filename)
    if not report_file:
        return

    branch_ids = _doctor_branch_ids(doctor.id, db)
    if not branch_ids:
        raise HTTPException(status_code=403, detail="Doctor branch access not configured")

    report_entry = db.query(DailyEntryModule).filter(
        DailyEntryModule.branch_id.in_(branch_ids),
        DailyEntryModule.report_pdf_url.isnot(None),
    ).all()

    matched_entry = None
    for entry in report_entry:
        raw = (entry.report_pdf_url or "").strip()
        if not raw:
            continue
        raw_name = os.path.basename(raw)
        if raw_name == report_file:
            matched_entry = entry
            break

    if not matched_entry:
        raise HTTPException(status_code=403, detail="You do not have access to this report")

    db.add(
        DoctorAuditLog(
            doctor_id=doctor.id,
            user_id=current_user.id,
            action="REPORT_FILE_VIEW",
            entity_type="DailyEntryModule",
            entity_id=str(matched_entry.id),
            event_meta={"filename": report_file, "branch_id": matched_entry.branch_id},
            created_at=datetime.utcnow(),
        )
    )
    db.commit()


def _resolve_current_user(
    db: Session,
    authorization: Optional[str],
    access_token: Optional[str],
) -> User:
    bearer_token: Optional[str] = None

    if authorization:
        scheme, _, raw_token = authorization.partition(" ")
        if scheme.lower() == "bearer" and raw_token.strip():
            bearer_token = raw_token.strip()

    if bearer_token is None and access_token:
        candidate = access_token.strip()
        if candidate:
            bearer_token = candidate

    if not bearer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = auth_guard.verify_token(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=bearer_token)
    )
    current_user = auth_guard.get_current_user(token_data=token_data, db=db)

    if current_user.role not in ALLOWED_FILE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return current_user

@router.get("/files/{filename:path}")
async def serve_file(
    filename: str,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    access_token: Optional[str] = Query(default=None),
):
    """
    Serve a file from the uploads directory
    
    Args:
        filename: The name of the file to serve (can include subdirectory)
        
    Returns:
        FileResponse with the requested file
        
    Raises:
        HTTPException: If file not found or invalid filename
    """
    # Security: Prevent directory traversal attacks
    if ".." in filename or filename.startswith("/"):
        print(f"❌ [FILE_SERVING] Invalid filename attempted: {filename}")
        raise HTTPException(status_code=400, detail="Invalid filename")

    current_user = _resolve_current_user(db, authorization, access_token)

    _enforce_doctor_report_access(filename, current_user, db)
    
    # Build the absolute path to the requested file
    # Ensure we construct the absolute path correctly
    abs_uploads_dir = UPLOADS_DIR.resolve()
    requested_file_path = (abs_uploads_dir / filename).resolve()
    
    # Security: Ensure the resolved path is within uploads directory (prevent directory traversal)
    try:
        requested_file_path.relative_to(abs_uploads_dir)
    except ValueError:
        print(f"❌ [FILE_SERVING] Path traversal attempt detected: {filename}")
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    # Debug log: Print exact absolute path being searched
    print(f"🔍 Attempting to serve file from: {requested_file_path}")
    
    # Check if file exists at the resolved path
    if not requested_file_path.exists() or not requested_file_path.is_file():
        print(f"❌ [FILE_SERVING] File not found: {filename}")
        print(f"   Absolute path searched: {requested_file_path}")
        print(f"   UPLOADS_DIR: {abs_uploads_dir}")
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    # Determine media type based on file extension
    media_type = "application/octet-stream"
    if filename.lower().endswith('.pdf'):
        media_type = "application/pdf"
    elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        ext = filename.split('.')[-1].lower()
        media_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"
    elif filename.lower().endswith('.txt'):
        media_type = "text/plain"
    
    print(f"✅ [FILE_SERVING] Serving file: {requested_file_path} as {media_type}")
    
    # Return the file with CORS headers for cross-origin image requests
    return FileResponse(
        path=str(requested_file_path),
        media_type=media_type,
        filename=os.path.basename(filename),
        headers={
            "Content-Disposition": f'inline; filename="{os.path.basename(filename)}"',
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )
