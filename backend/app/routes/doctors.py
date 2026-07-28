import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import User
from app.models.daily_entry_module import DailyEntryModule
from app.models.referring_doctor import DoctorShareLink, ReferralLog, ReferringDoctor
from app.utils.auth_system import get_current_user


router = APIRouter()

UPLOAD_ROOT = Path("uploads/doctor_shares")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

DOCTOR_PORTAL_TOKENS: Dict[str, Dict[str, object]] = {}


def _ensure_tables() -> None:
    """Ensure tables exist. Call this lazily only when needed, not at import time."""
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ReferringDoctor.__table__,
            ReferralLog.__table__,
            DoctorShareLink.__table__,
        ],
    )


def _require_branch_director(current_user: User) -> None:
    if current_user.role not in ["super_admin", "branch_director", "branch_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin, branch_director or branch_admin can access this module",
        )


class DoctorCreatePayload(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    mobile: str = Field(..., min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = None

    specialization: Optional[str] = None
    degree: Optional[str] = None
    hospital_clinic_affiliation: Optional[str] = None
    years_of_experience: Optional[int] = Field(None, ge=0, le=70)

    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    upi_id: Optional[str] = None

    commission_percentage: float = Field(0, ge=0, le=100)

    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    portal_username: Optional[str] = None
    portal_password: Optional[str] = Field(None, min_length=6, max_length=64)


class DoctorUpdatePayload(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    mobile: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = None

    specialization: Optional[str] = None
    degree: Optional[str] = None
    hospital_clinic_affiliation: Optional[str] = None
    years_of_experience: Optional[int] = Field(None, ge=0, le=70)

    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    upi_id: Optional[str] = None

    commission_percentage: Optional[float] = Field(None, ge=0, le=100)

    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    portal_username: Optional[str] = None
    portal_password: Optional[str] = Field(None, min_length=6, max_length=64)
    is_active: Optional[bool] = None


class BroadcastPayload(BaseModel):
    message: str = Field(..., min_length=5)
    doctor_ids: Optional[List[int]] = None
    specialization: Optional[str] = None
    city: Optional[str] = None
    channels: List[str] = Field(default_factory=lambda: ["email", "whatsapp"])


class PortalLoginPayload(BaseModel):
    username: str
    password: str


def _hash_password(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


def _doctor_message(name: str) -> str:
    return (
        f"Dear Dr. {name}, Please find attached patient reports and referral updates "
        "from VaidyaVihar Diagnostic."
    )


def _monthly_window(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def _doctor_revenue_from_entries(db: Session, branch_id: int, doctor_name: str, start: datetime, end: datetime) -> Decimal:
    value = (
        db.query(func.coalesce(func.sum(DailyEntryModule.total_amount), 0))
        .filter(
            and_(
                DailyEntryModule.branch_id == branch_id,
                DailyEntryModule.referred_doctor.isnot(None),
                func.lower(DailyEntryModule.referred_doctor) == doctor_name.lower(),
                DailyEntryModule.auto_entry_datetime >= start,
                DailyEntryModule.auto_entry_datetime < end,
            )
        )
        .scalar()
    )
    return Decimal(value or 0)


@router.get("/api/doctors")
def list_doctors(
    specialization: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_branch_director(current_user)

    query = db.query(ReferringDoctor).filter(
        ReferringDoctor.branch_id == current_user.branch_id,
        ReferringDoctor.is_active == True,
    )
    if specialization:
        query = query.filter(ReferringDoctor.specialization.ilike(f"%{specialization}%"))
    if city:
        query = query.filter(ReferringDoctor.city.ilike(f"%{city}%"))

    doctors = query.order_by(ReferringDoctor.full_name.asc()).all()

    now = datetime.utcnow()
    start, end = _monthly_window(now.year, now.month)

    result = []
    for doctor in doctors:
        referral_count = (
            db.query(func.count(ReferralLog.id))
            .filter(
                ReferralLog.branch_id == current_user.branch_id,
                ReferralLog.doctor_id == doctor.id,
                ReferralLog.referred_on >= start,
                ReferralLog.referred_on < end,
            )
            .scalar()
            or 0
        )
        monthly_revenue = _doctor_revenue_from_entries(db, current_user.branch_id, doctor.full_name, start, end)
        commission = (monthly_revenue * Decimal(doctor.commission_percentage or 0)) / Decimal(100)

        result.append(
            {
                "id": doctor.id,
                "full_name": doctor.full_name,
                "mobile": doctor.mobile,
                "email": doctor.email,
                "address": doctor.address,
                "specialization": doctor.specialization,
                "degree": doctor.degree,
                "hospital_clinic_affiliation": doctor.hospital_clinic_affiliation,
                "years_of_experience": doctor.years_of_experience,
                "bank_account_number": doctor.bank_account_number,
                "ifsc_code": doctor.ifsc_code,
                "upi_id": doctor.upi_id,
                "commission_percentage": doctor.commission_percentage,
                "city": doctor.city,
                "latitude": doctor.latitude,
                "longitude": doctor.longitude,
                "portal_username": doctor.portal_username,
                "monthly_referrals": int(referral_count),
                "monthly_revenue": float(monthly_revenue),
                "monthly_commission": float(commission),
                "created_at": doctor.created_at,
            }
        )

    return result


@router.post("/api/doctors", status_code=201)
def create_doctor(
    payload: DoctorCreatePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_branch_director(current_user)

    duplicate = (
        db.query(ReferringDoctor)
        .filter(
            ReferringDoctor.branch_id == current_user.branch_id,
            or_(ReferringDoctor.mobile == payload.mobile, ReferringDoctor.email == payload.email),
            ReferringDoctor.is_active == True,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="Doctor with same mobile/email already exists")

    portal_password_hash = _hash_password(payload.portal_password) if payload.portal_password else None

    row = ReferringDoctor(
        branch_id=current_user.branch_id,
        full_name=payload.full_name,
        mobile=payload.mobile,
        email=payload.email,
        address=payload.address,
        specialization=payload.specialization,
        degree=payload.degree,
        hospital_clinic_affiliation=payload.hospital_clinic_affiliation,
        years_of_experience=payload.years_of_experience,
        bank_account_number=payload.bank_account_number,
        ifsc_code=payload.ifsc_code,
        upi_id=payload.upi_id,
        commission_percentage=payload.commission_percentage,
        city=payload.city,
        latitude=payload.latitude,
        longitude=payload.longitude,
        portal_username=payload.portal_username,
        portal_password_hash=portal_password_hash,
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {"id": row.id, "message": "Doctor created successfully"}


@router.put("/api/doctors/{doctor_id}")
def update_doctor(
    doctor_id: int,
    payload: DoctorUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_branch_director(current_user)

    row = (
        db.query(ReferringDoctor)
        .filter(
            ReferringDoctor.id == doctor_id,
            ReferringDoctor.branch_id == current_user.branch_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Doctor not found")

    data = payload.dict(exclude_unset=True)
    if "portal_password" in data:
        portal_password = data.pop("portal_password")
        row.portal_password_hash = _hash_password(portal_password)

    for key, value in data.items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return {"id": row.id, "message": "Doctor updated successfully"}


@router.delete("/api/doctors/{doctor_id}")
def delete_doctor(
    doctor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_branch_director(current_user)

    row = (
        db.query(ReferringDoctor)
        .filter(
            ReferringDoctor.id == doctor_id,
            ReferringDoctor.branch_id == current_user.branch_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Doctor not found")

    row.is_active = False
    db.commit()
    return {"message": "Doctor deleted successfully"}


@router.get("/api/doctors/performance")
def doctors_performance(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_branch_director(current_user)

    now = datetime.utcnow()
    target_month = month or now.month
    target_year = year or now.year
    start, end = _monthly_window(target_year, target_month)

    doctors = (
        db.query(ReferringDoctor)
        .filter(
            ReferringDoctor.branch_id == current_user.branch_id,
            ReferringDoctor.is_active == True,
        )
        .all()
    )

    doctor_rows = []
    total_revenue = Decimal(0)
    total_commission = Decimal(0)

    for doctor in doctors:
        referrals = (
            db.query(func.count(ReferralLog.id))
            .filter(
                ReferralLog.branch_id == current_user.branch_id,
                ReferralLog.doctor_id == doctor.id,
                ReferralLog.referred_on >= start,
                ReferralLog.referred_on < end,
            )
            .scalar()
            or 0
        )
        revenue = _doctor_revenue_from_entries(db, current_user.branch_id, doctor.full_name, start, end)
        commission = (revenue * Decimal(doctor.commission_percentage or 0)) / Decimal(100)

        total_revenue += revenue
        total_commission += commission

        doctor_rows.append(
            {
                "doctor_id": doctor.id,
                "doctor_name": doctor.full_name,
                "specialization": doctor.specialization,
                "referrals": int(referrals),
                "revenue": float(revenue),
                "commission_percentage": doctor.commission_percentage,
                "commission": float(commission),
            }
        )

    doctor_rows.sort(key=lambda row: row["revenue"], reverse=True)

    pending_reports = (
        db.query(func.count(ReferralLog.id))
        .filter(
            ReferralLog.branch_id == current_user.branch_id,
            ReferralLog.report_sent == False,
            ReferralLog.referred_on >= start,
            ReferralLog.referred_on < end,
        )
        .scalar()
        or 0
    )

    return {
        "month": target_month,
        "year": target_year,
        "top_5_referring_doctors": doctor_rows[:5],
        "doctor_performance": doctor_rows,
        "total_revenue_from_referrals": float(total_revenue),
        "total_commission_payable": float(total_commission),
        "pending_reports_to_send": int(pending_reports),
    }


@router.post("/api/doctors/broadcast")
def broadcast_message(
    payload: BroadcastPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_branch_director(current_user)

    query = db.query(ReferringDoctor).filter(
        ReferringDoctor.branch_id == current_user.branch_id,
        ReferringDoctor.is_active == True,
    )

    if payload.doctor_ids:
        query = query.filter(ReferringDoctor.id.in_(payload.doctor_ids))
    if payload.specialization:
        query = query.filter(ReferringDoctor.specialization.ilike(f"%{payload.specialization}%"))
    if payload.city:
        query = query.filter(ReferringDoctor.city.ilike(f"%{payload.city}%"))

    doctors = query.all()

    sent = []
    for doctor in doctors:
        doctor_message = f"Dear Dr. {doctor.full_name},\n\n{payload.message}\n\n- VaidyaVihar Diagnostic"

        email_link = ""
        whatsapp_link = ""

        if "email" in payload.channels and doctor.email:
            subject = quote("Marketing Update from VaidyaVihar Diagnostic")
            body = quote(doctor_message)
            email_link = f"mailto:{doctor.email}?subject={subject}&body={body}"

        if "whatsapp" in payload.channels and doctor.mobile:
            whatsapp_link = f"https://wa.me/{doctor.mobile}?text={quote(doctor_message)}"

        sent.append(
            {
                "doctor_id": doctor.id,
                "doctor_name": doctor.full_name,
                "email_link": email_link,
                "whatsapp_link": whatsapp_link,
            }
        )

    return {
        "message": "Broadcast links generated",
        "total_recipients": len(sent),
        "items": sent,
    }


@router.post("/api/doctors/send-pdfs")
async def send_pdfs_to_doctors(
    doctor_ids: str = Form(...),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_branch_director(current_user)

    try:
        if doctor_ids.strip().startswith("["):
            parsed_ids = [int(x) for x in json.loads(doctor_ids)]
        else:
            parsed_ids = [int(x.strip()) for x in doctor_ids.split(",") if x.strip()]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid doctor_ids: {exc}")

    doctors = (
        db.query(ReferringDoctor)
        .filter(
            ReferringDoctor.branch_id == current_user.branch_id,
            ReferringDoctor.id.in_(parsed_ids),
            ReferringDoctor.is_active == True,
        )
        .all()
    )

    if not doctors:
        raise HTTPException(status_code=404, detail="No doctors found for selected IDs")

    expiry = datetime.utcnow() + timedelta(hours=24)

    # Save each uploaded file once, then create tokenized links per doctor.
    stored_files = []
    for file in files:
        unique_name = f"{uuid.uuid4().hex}_{file.filename}"
        abs_path = UPLOAD_ROOT / unique_name
        content = await file.read()
        with open(abs_path, "wb") as out:
            out.write(content)
        stored_files.append(
            {
                "filename": file.filename,
                "file_path": str(abs_path.resolve()),
                "mime_type": file.content_type or "application/octet-stream",
            }
        )

    results = []
    for doctor in doctors:
        links = []
        for sf in stored_files:
            token = uuid.uuid4().hex
            row = DoctorShareLink(
                branch_id=current_user.branch_id,
                doctor_id=doctor.id,
                token=token,
                filename=sf["filename"],
                file_path=sf["file_path"],
                mime_type=sf["mime_type"],
                expires_at=expiry,
                created_by=current_user.id,
            )
            db.add(row)
            links.append(f"{os.getenv('PUBLIC_BASE_URL', 'http://localhost:8000')}/api/doctors/file/{token}")

        msg = _doctor_message(doctor.full_name)
        links_block = "\n".join(links)
        full_message = f"{msg}\n\nDownload Links:\n{links_block}"

        email_link = ""
        whatsapp_link = ""
        if doctor.email:
            email_link = f"mailto:{doctor.email}?subject={quote('Patient Reports and Referral Updates')}&body={quote(full_message)}"
        if doctor.mobile:
            whatsapp_link = f"https://wa.me/{doctor.mobile}?text={quote(full_message)}"

        results.append(
            {
                "doctor_id": doctor.id,
                "doctor_name": doctor.full_name,
                "email": doctor.email,
                "mobile": doctor.mobile,
                "share_links": links,
                "email_link": email_link,
                "whatsapp_link": whatsapp_link,
                "expires_at": expiry.isoformat(),
            }
        )

    db.commit()

    return {
        "message": "Temporary file links generated for selected doctors",
        "valid_for_hours": 24,
        "items": results,
    }


@router.get("/api/doctors/file/{token}")
def get_temporary_file(
    token: str,
    db: Session = Depends(get_db),
):
    row = (
        db.query(DoctorShareLink)
        .filter(
            DoctorShareLink.token == token,
            DoctorShareLink.is_active == True,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    if row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Link has expired")

    file_path = Path(row.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=str(file_path), filename=row.filename, media_type=row.mime_type)


@router.post("/api/doctors/referrals")
def add_referral_log(
    doctor_id: int = Form(...),
    patient_name: str = Form(...),
    patient_mobile: Optional[str] = Form(None),
    revenue_amount: float = Form(0),
    report_due_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_branch_director(current_user)

    doctor = (
        db.query(ReferringDoctor)
        .filter(
            ReferringDoctor.id == doctor_id,
            ReferringDoctor.branch_id == current_user.branch_id,
        )
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    due_dt = None
    if report_due_date:
        try:
            due_dt = datetime.fromisoformat(report_due_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid report_due_date format")

    row = ReferralLog(
        branch_id=current_user.branch_id,
        doctor_id=doctor_id,
        patient_name=patient_name,
        patient_mobile=patient_mobile,
        revenue_amount=Decimal(str(revenue_amount)),
        report_due_date=due_dt,
        notes=notes,
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {"message": "Referral log created", "id": row.id}


@router.post("/api/doctors/portal/login")
def doctor_portal_login(payload: PortalLoginPayload, db: Session = Depends(get_db)):
    doctor = (
        db.query(ReferringDoctor)
        .filter(ReferringDoctor.portal_username == payload.username, ReferringDoctor.is_active == True)
        .first()
    )
    if not doctor or not doctor.portal_password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if doctor.portal_password_hash != _hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = uuid.uuid4().hex
    DOCTOR_PORTAL_TOKENS[token] = {
        "doctor_id": doctor.id,
        "expires_at": datetime.utcnow() + timedelta(hours=12),
    }

    return {
        "token": token,
        "doctor_id": doctor.id,
        "full_name": doctor.full_name,
        "expires_in_hours": 12,
    }


def _get_portal_doctor(token: str, db: Session) -> ReferringDoctor:
    record = DOCTOR_PORTAL_TOKENS.get(token)
    if not record:
        raise HTTPException(status_code=401, detail="Invalid token")
    if record["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")

    doctor = db.query(ReferringDoctor).filter(ReferringDoctor.id == int(record["doctor_id"])).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.get("/api/doctors/portal/me")
def doctor_portal_me(token: str = Query(...), db: Session = Depends(get_db)):
    doctor = _get_portal_doctor(token, db)
    return {
        "doctor_id": doctor.id,
        "full_name": doctor.full_name,
        "specialization": doctor.specialization,
        "city": doctor.city,
        "commission_percentage": doctor.commission_percentage,
    }


@router.get("/api/doctors/portal/referrals")
def doctor_portal_referrals(token: str = Query(...), db: Session = Depends(get_db)):
    doctor = _get_portal_doctor(token, db)

    rows = (
        db.query(ReferralLog)
        .filter(ReferralLog.doctor_id == doctor.id)
        .order_by(ReferralLog.referred_on.desc())
        .limit(200)
        .all()
    )

    return [
        {
            "id": r.id,
            "patient_name": r.patient_name,
            "patient_mobile": r.patient_mobile,
            "referred_on": r.referred_on,
            "revenue_amount": float(r.revenue_amount or 0),
            "report_sent": r.report_sent,
            "report_due_date": r.report_due_date,
        }
        for r in rows
    ]
