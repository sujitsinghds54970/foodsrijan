from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, Patient
from app.models.daily_entry_module import DailyEntryModule
from app.models.doctor import Doctor, DoctorBranch
from app.models.patient import FamilyMember, PatientProfile
from app.services.patient_portal_notify import build_patient_notify_payload
from app.utils.auth_system import ALGORITHM, SECRET_KEY, auth_guard

router = APIRouter()
patient_security = HTTPBearer()


class PatientLoginRequest(BaseModel):
    mode: str
    mobile: Optional[str] = None
    otp: Optional[str] = None
    patient_id: Optional[str] = None
    password: Optional[str] = None


class PatientNotifyRequest(BaseModel):
    report_id: int
    channel: str = "whatsapp"


class FamilyMemberRequest(BaseModel):
    name: str
    relation: str
    age: Optional[int] = None
    mobile: Optional[str] = None


class WalletRedeemRequest(BaseModel):
    amount: float


def _ensure_patient_portal_schema(db: Session = Depends(get_db)) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS patient_profiles (
                id INTEGER PRIMARY KEY,
                patient_id INTEGER,
                patient_code VARCHAR(64) NOT NULL UNIQUE,
                full_name VARCHAR(255) NOT NULL,
                mobile VARCHAR(20) NOT NULL UNIQUE,
                email VARCHAR(255),
                password VARCHAR(255) NOT NULL,
                otp_code VARCHAR(8),
                otp_expires_at DATETIME,
                role VARCHAR(32) NOT NULL DEFAULT 'patient',
                is_active BOOLEAN NOT NULL DEFAULT 1,
                family_group VARCHAR(64),
                wallet_balance FLOAT NOT NULL DEFAULT 0,
                cashback_percent FLOAT NOT NULL DEFAULT 5,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY,
                owner_profile_id INTEGER NOT NULL,
                linked_profile_id INTEGER,
                name VARCHAR(255) NOT NULL,
                relation VARCHAR(64) NOT NULL,
                age INTEGER,
                mobile VARCHAR(20),
                FOREIGN KEY(owner_profile_id) REFERENCES patient_profiles(id),
                FOREIGN KEY(linked_profile_id) REFERENCES patient_profiles(id)
            )
            """
        )
    )
    db.commit()


def _get_current_patient_profile(
    _schema_ready: None = Depends(_ensure_patient_portal_schema),
    credentials: HTTPAuthorizationCredentials = Depends(patient_security),
    db: Session = Depends(get_db),
) -> PatientProfile:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("role") != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient role required")

    profile_id = payload.get("patient_profile_id")
    if not profile_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid patient session")

    profile = db.query(PatientProfile).filter(PatientProfile.id == profile_id).first()
    if not profile or not profile.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Patient account not found")

    return profile


def _resolve_report_download_url(report_pdf_url: Optional[str]) -> Optional[str]:
    if not report_pdf_url:
        return None
    if report_pdf_url.startswith("/api/files/"):
        return report_pdf_url
    if report_pdf_url.startswith("/uploads/"):
        filename = report_pdf_url.split("/")[-1]
        return f"/api/files/daily_entry_reports/{filename}"
    return f"/api/files/{report_pdf_url.lstrip('/')}"


def _get_doctor_white_label_for_branch(branch_id: int, db: Session) -> dict:
    assignment = (
        db.query(DoctorBranch)
        .filter(DoctorBranch.branch_id == branch_id, DoctorBranch.is_active.is_(True))
        .order_by(DoctorBranch.is_primary.desc(), DoctorBranch.assigned_date.desc())
        .first()
    )
    if not assignment:
        return {}

    doctor = db.query(Doctor).filter(Doctor.id == assignment.doctor_id, Doctor.is_active.is_(True)).first()
    if not doctor or not isinstance(doctor.report_preferences, dict):
        return {}

    white_label = doctor.report_preferences.get("white_label")
    if not isinstance(white_label, dict):
        return {}

    return {
        "clinic_name": (white_label.get("clinic_name") or "").strip(),
        "clinic_address": (white_label.get("clinic_address") or "").strip(),
        "logo_url": (white_label.get("logo_url") or "").strip(),
    }


def _resolve_patient_branding(profile: PatientProfile, db: Session) -> dict:
    patient = None
    if profile.patient_id:
        patient = db.query(Patient).filter(Patient.id == profile.patient_id).first()

    branch_id = patient.branch_id if patient else None
    if not branch_id:
        latest_entry = (
            db.query(DailyEntryModule)
            .filter(DailyEntryModule.mobile == profile.mobile)
            .order_by(DailyEntryModule.auto_entry_datetime.desc())
            .first()
        )
        branch_id = latest_entry.branch_id if latest_entry else None

    branch_name = "Vaidya Vihar Diagnostic"
    branch_address = ""
    branch_logo_url = ""
    if branch_id:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if branch:
            branch_name = branch.name or branch_name
            branch_address = branch.address or ""
            branch_logo_url = branch.director_photo_url or ""

    doctor_branding = _get_doctor_white_label_for_branch(branch_id, db) if branch_id else {}
    clinic_name = doctor_branding.get("clinic_name") or branch_name
    clinic_address = doctor_branding.get("clinic_address") or branch_address
    logo_url = doctor_branding.get("logo_url") or branch_logo_url

    return {
        "clinic_name": clinic_name,
        "clinic_address": clinic_address,
        "logo_url": logo_url,
        "branch_id": branch_id,
        "report_header": {
            "title": clinic_name,
            "subtitle": clinic_address,
            "logo_url": logo_url,
        },
    }


@router.post("/api/patient/login")
async def patient_login(
    payload: PatientLoginRequest,
    db: Session = Depends(get_db),
    _schema_ready: None = Depends(_ensure_patient_portal_schema),
):
    profile: Optional[PatientProfile] = None

    if payload.mode == "otp":
        if not payload.mobile:
            raise HTTPException(status_code=400, detail="mobile is required for otp login")
        if payload.otp != "123456":
            raise HTTPException(status_code=401, detail="Invalid OTP")

        profile = db.query(PatientProfile).filter(PatientProfile.mobile == payload.mobile).first()
    elif payload.mode == "password":
        if not payload.patient_id or not payload.password:
            raise HTTPException(status_code=400, detail="patient_id and password are required")
        profile = (
            db.query(PatientProfile)
            .filter(PatientProfile.patient_code == payload.patient_id)
            .first()
        )
        if profile and profile.password != payload.password:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        raise HTTPException(status_code=400, detail="mode must be otp or password")

    if not profile or not profile.is_active:
        raise HTTPException(status_code=404, detail="Patient account not found")

    access_token = auth_guard.create_access_token(
        data={
            "sub": profile.patient_code,
            "role": "patient",
            "patient_profile_id": profile.id,
        },
        expires_delta=timedelta(days=7),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "patient": {
            "id": profile.id,
            "patient_code": profile.patient_code,
            "full_name": profile.full_name,
            "mobile": profile.mobile,
            "wallet_balance": profile.wallet_balance,
            "cashback_percent": profile.cashback_percent,
        },
    }


@router.get("/api/patient/dashboard")
async def patient_dashboard(
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_current_patient_profile),
):
    branding = _resolve_patient_branding(profile, db)
    reports_query = db.query(DailyEntryModule).filter(DailyEntryModule.mobile == profile.mobile)
    reports = reports_query.order_by(DailyEntryModule.auto_entry_datetime.desc()).all()

    total_reports = len(reports)
    completed_reports = sum(1 for row in reports if (row.status or "").lower() == "completed")
    pending_reports = total_reports - completed_reports

    family_members = (
        db.query(FamilyMember)
        .filter(FamilyMember.owner_profile_id == profile.id)
        .order_by(FamilyMember.id.desc())
        .all()
    )

    recent_reports = []
    for row in reports[:5]:
        recent_reports.append(
            {
                "id": row.id,
                "patient_id": row.auto_patient_id,
                "test_name": row.test_name,
                "status": row.status,
                "date": row.auto_entry_datetime.isoformat() if row.auto_entry_datetime else None,
                "download_url": _resolve_report_download_url(row.report_pdf_url),
            }
        )

    return {
        "branding": branding,
        "kpis": {
            "total_reports": total_reports,
            "completed_reports": completed_reports,
            "pending_reports": pending_reports,
            "wallet_balance": round(profile.wallet_balance or 0.0, 2),
            "cashback_percent": profile.cashback_percent or 0.0,
            "family_members": len(family_members),
        },
        "recent_reports": recent_reports,
        "family_members": [
            {
                "id": member.id,
                "name": member.name,
                "relation": member.relation,
                "age": member.age,
                "mobile": member.mobile,
            }
            for member in family_members
        ],
        "sample_tracking": [
            {"step": "Sample Collected", "done": total_reports > 0},
            {"step": "In Processing", "done": pending_reports > 0},
            {"step": "Report Ready", "done": completed_reports > 0},
        ],
    }


@router.get("/api/patient/reports")
async def patient_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_current_patient_profile),
):
    branding = _resolve_patient_branding(profile, db)
    base_query = db.query(DailyEntryModule).filter(DailyEntryModule.mobile == profile.mobile)
    total = base_query.count()

    rows = (
        base_query.order_by(DailyEntryModule.auto_entry_datetime.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "branding": branding,
        "page": page,
        "page_size": page_size,
        "total": total,
        "reports": [
            {
                "id": row.id,
                "patient_id": row.auto_patient_id,
                "test_name": row.test_name,
                "status": row.status,
                "amount": float(row.total_amount or 0),
                "created_at": row.auto_entry_datetime.isoformat() if row.auto_entry_datetime else None,
                "download_url": _resolve_report_download_url(row.report_pdf_url),
                "report_header": branding.get("report_header"),
            }
            for row in rows
        ],
    }


@router.get("/api/patient/reports/{report_id}/download")
async def patient_report_download(
    report_id: int,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_current_patient_profile),
):
    branding = _resolve_patient_branding(profile, db)
    row = (
        db.query(DailyEntryModule)
        .filter(
            DailyEntryModule.id == report_id,
            DailyEntryModule.mobile == profile.mobile,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    download_url = _resolve_report_download_url(row.report_pdf_url)
    if not download_url:
        raise HTTPException(status_code=404, detail="Report file not available")

    return {
        "report_id": row.id,
        "download_url": download_url,
        "report_header": branding.get("report_header"),
        "branding": branding,
    }


@router.post("/api/patient/notify")
async def patient_notify(
    payload: PatientNotifyRequest,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_current_patient_profile),
):
    row = (
        db.query(DailyEntryModule)
        .filter(
            DailyEntryModule.id == payload.report_id,
            DailyEntryModule.mobile == profile.mobile,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    notify_payload = build_patient_notify_payload(db=db, daily_entry=row, channel=payload.channel)
    if not notify_payload:
        raise HTTPException(status_code=404, detail="Patient contact not configured")

    return {
        "success": True,
        **notify_payload,
    }


@router.get("/api/patient/family-members")
async def list_family_members(
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_current_patient_profile),
):
    members = (
        db.query(FamilyMember)
        .filter(FamilyMember.owner_profile_id == profile.id)
        .order_by(FamilyMember.id.desc())
        .all()
    )
    return {
        "members": [
            {
                "id": m.id,
                "name": m.name,
                "relation": m.relation,
                "age": m.age,
                "mobile": m.mobile,
            }
            for m in members
        ]
    }


@router.post("/api/patient/family-members")
async def add_family_member(
    payload: FamilyMemberRequest,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_current_patient_profile),
):
    member = FamilyMember(
        owner_profile_id=profile.id,
        name=payload.name,
        relation=payload.relation,
        age=payload.age,
        mobile=payload.mobile,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    return {
        "id": member.id,
        "name": member.name,
        "relation": member.relation,
        "age": member.age,
        "mobile": member.mobile,
    }


@router.post("/api/patient/wallet/redeem")
async def redeem_wallet(
    payload: WalletRedeemRequest,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_current_patient_profile),
):
    amount = round(payload.amount, 2)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount should be greater than zero")
    if (profile.wallet_balance or 0.0) < amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    profile.wallet_balance = round((profile.wallet_balance or 0.0) - amount, 2)
    profile.updated_at = datetime.utcnow()
    db.commit()

    return {
        "wallet_balance": profile.wallet_balance,
        "redeemed": amount,
    }
