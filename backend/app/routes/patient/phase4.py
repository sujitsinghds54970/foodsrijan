from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Optional
import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from PIL import Image
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models.daily_entry_module import DailyEntryModule
from app.models.customer import CustomerProfile, FamilyMember
from app.models.patient_b2c import OrderSummary
from app.models.patient_phase4 import EmergencyAlert, CustomerVaultDocument, SecondOpinionRequest, WearableSync
from app.routes.patient_b2c_phase1 import (
    _build_ai_summary,
    _ensure_patient_b2c_schema,
    _get_patient_profile_from_token,
    _infer_abnormal_flags,
    _log_patient_audit,
    _resolve_report_download_url,
)

router = APIRouter(tags=["Customer Phase 4"])

BASE_DIR = Path(__file__).resolve().parents[3]
PATIENT_VAULT_DIR = BASE_DIR / "uploads" / "patient_vault"


def _ensure_phase4_schema() -> None:
    _ensure_patient_b2c_schema()
    Base.metadata.create_all(
        bind=engine,
        tables=[
            WearableSync.__table__,
            SecondOpinionRequest.__table__,
            EmergencyAlert.__table__,
            CustomerVaultDocument.__table__,
        ],
    )


class WearableConnectPayload(BaseModel):
    provider: str = Field(pattern="^(Apple Health|Google Fit|Fitbit)$")
    token: Optional[str] = Field(default=None, min_length=8, max_length=255)


class SecondOpinionPayload(BaseModel):
    report_id: int = Field(gt=0)
    specialist_panel: str = Field(default="Senior Specialist Panel", min_length=3, max_length=120)


class CriticalAlertPayload(BaseModel):
    report_id: int = Field(gt=0)
    alert_type: str = Field(default="critical", min_length=3, max_length=60)
    note: Optional[str] = Field(default=None, max_length=500)


class HomeCollectionMapResponse(BaseModel):
    patient_location: dict
    phlebotomist_location: dict
    eta_minutes: int
    route_points: list[dict]
    status: str
    message: str


def _patient_family_payload(profile: CustomerProfile) -> dict:
    members = [
        {
            "id": member.id,
            "name": member.name,
            "relation": member.relation,
            "mobile": member.mobile,
            "age": member.age,
            "linked_profile_id": member.linked_profile_id,
        }
        for member in profile.family_members
    ]

    return {
        "patient_id": profile.id,
        "patient_code": profile.patient_code,
        "family_group": profile.family_group,
        "primary_member": {
            "id": profile.id,
            "full_name": profile.full_name,
            "mobile": profile.mobile,
            "email": profile.email,
        },
        "members": members,
        "headline": "Unified Family Health Profile",
        "summary": f"Single patient account linked to {len(members)} family member(s).",
    }


def _home_collection_map(profile: CustomerProfile) -> HomeCollectionMapResponse:
    patient_lat = 28.6139
    patient_lng = 77.209
    phlebotomist_lat = 28.6201
    phlebotomist_lng = 77.2184
    route_points = [
        {"lat": patient_lat, "lng": patient_lng, "label": profile.full_name},
        {"lat": 28.6169, "lng": 77.2137, "label": "Mock midpoint"},
        {"lat": phlebotomist_lat, "lng": phlebotomist_lng, "label": "Phlebotomist"},
    ]
    return HomeCollectionMapResponse(
        patient_location={"lat": patient_lat, "lng": patient_lng, "label": profile.full_name},
        phlebotomist_location={"lat": phlebotomist_lat, "lng": phlebotomist_lng, "label": "Assigned phlebotomist", "status": "en_route"},
        eta_minutes=18,
        route_points=route_points,
        status="mock_live",
        message="Static mock coordinates enabled for demo tracking.",
    )


def _detect_critical_report(report: DailyEntryModule, abnormal_flags: dict[str, str]) -> bool:
    lowered_name = (report.test_name or "").lower()
    lowered_status = (report.status or "").lower()
    critical_terms = ("critical", "troponin", "ecg", "d-dimer", "echo", "ct angio", "heart attack", "sepsis")
    return any(term in lowered_name for term in critical_terms) or lowered_status == "critical" or any(
        "critical" in str(value).lower() for value in abnormal_flags.values()
    )


@router.get("/api/patient/family-profile")
def get_family_profile(
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()
    return _patient_family_payload(profile)


@router.get("/api/patient/home-collection/map")
def get_home_collection_map(
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()
    _ = profile
    return _home_collection_map(profile)


@router.get("/api/patient/vault")
def list_patient_vault_documents(
    db: Session = Depends(get_db),
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()
    rows = (
        db.query(CustomerVaultDocument)
        .filter(CustomerVaultDocument.patient_id == profile.id)
        .order_by(CustomerVaultDocument.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "original_filename": row.original_filename,
                "file_url": row.file_url,
                "extracted_text": row.extracted_text,
                "document_label": row.document_label,
                "file_size": row.file_size,
                "mime_type": row.mime_type,
                "created_at": row.created_at,
            }
            for row in rows
        ],
        "headline": "Centralized Health Vault",
    }


@router.post("/api/patient/vault/upload")
async def upload_patient_vault_document(
    file: UploadFile = File(...),
    document_label: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()

    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")

    allowed_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_suffixes:
        raise HTTPException(status_code=400, detail="Only PDF, PNG, JPG, JPEG, and WEBP files are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    patient_dir = PATIENT_VAULT_DIR / str(profile.id)
    patient_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4().hex}{suffix}"
    target_path = patient_dir / safe_name
    target_path.write_bytes(file_bytes)

    ocr_excerpt = _mock_ocr_text(file.filename, file.content_type, file_bytes)
    vault_row = CustomerVaultDocument(
        patient_id=profile.id,
        original_filename=file.filename,
        file_url=f"/api/files/patient_vault/{profile.id}/{safe_name}",
        extracted_text=ocr_excerpt,
        document_label=document_label or Path(file.filename).stem,
        file_size=len(file_bytes),
        mime_type=file.content_type,
    )
    db.add(vault_row)
    db.commit()
    db.refresh(vault_row)

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="vault_document_uploaded",
        entity_type="patient_vault_document",
        entity_id=str(vault_row.id),
        event_meta={"filename": file.filename, "mime_type": file.content_type},
    )

    return {
        "document": {
            "id": vault_row.id,
            "original_filename": vault_row.original_filename,
            "file_url": vault_row.file_url,
            "extracted_text": vault_row.extracted_text,
            "document_label": vault_row.document_label,
            "file_size": vault_row.file_size,
            "mime_type": vault_row.mime_type,
            "created_at": vault_row.created_at,
        },
        "message": "Document uploaded to the secure health vault",
    }


@router.post("/api/patient/alerts/critical")
def create_emergency_alert(
    payload: CriticalAlertPayload,
    db: Session = Depends(get_db),
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()

    report = (
        db.query(DailyEntryModule)
        .filter(DailyEntryModule.id == payload.report_id, DailyEntryModule.mobile == profile.mobile)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Order not found")

    abnormal_flags = _infer_abnormal_flags(report.test_name)
    if not _detect_critical_report(report, abnormal_flags) and "critical" not in payload.alert_type.lower():
        raise HTTPException(status_code=400, detail="Critical flag was not detected for this report")

    channels = ["SMS", "In-App", "Email"]
    row = EmergencyAlert(
        patient_id=profile.id,
        report_id=report.id,
        alert_type=payload.alert_type,
        delivery_channels=channels,
        doctor_notified=1,
        note=payload.note,
        triggered_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="critical_alert_triggered",
        entity_type="patient_emergency_alert",
        entity_id=str(row.id),
        event_meta={"report_id": report.id, "channels": channels},
    )

    return {
        "id": row.id,
        "report_id": row.report_id,
        "alert_type": row.alert_type,
        "triggered_at": row.triggered_at,
        "channels": channels,
        "doctor_notified": True,
        "message": "Critical alert dispatched to patient and doctor via SMS, In-App, and Email.",
    }


@router.get("/api/patient/emergency-alerts")
def list_emergency_alerts(
    db: Session = Depends(get_db),
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()
    rows = (
        db.query(EmergencyAlert)
        .filter(EmergencyAlert.patient_id == profile.id)
        .order_by(EmergencyAlert.triggered_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "report_id": row.report_id,
                "alert_type": row.alert_type,
                "triggered_at": row.triggered_at,
                "delivery_channels": row.delivery_channels or [],
                "doctor_notified": bool(row.doctor_notified),
                "note": row.note,
            }
            for row in rows
        ]
    }


@router.post("/api/patient/second-opinion")
def request_second_opinion(
    payload: SecondOpinionPayload,
    db: Session = Depends(get_db),
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()

    report = (
        db.query(DailyEntryModule)
        .filter(DailyEntryModule.id == payload.report_id, DailyEntryModule.mobile == profile.mobile)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Order not found")

    row = SecondOpinionRequest(
        patient_id=profile.id,
        report_id=report.id,
        status="Pending Payment",
        payment_reference=secrets.token_hex(8).upper(),
        specialist_panel=payload.specialist_panel,
        premium_amount=999,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="second_opinion_requested",
        entity_type="patient_second_opinion_request",
        entity_id=str(row.id),
        event_meta={"report_id": report.id, "specialist_panel": payload.specialist_panel},
    )

    return {
        "id": row.id,
        "report_id": row.report_id,
        "status": row.status,
        "payment_reference": row.payment_reference,
        "specialist_panel": row.specialist_panel,
        "premium_amount": row.premium_amount,
        "payment_url": f"https://payments.example.com/second-opinion/{row.payment_reference}",
        "message": "Second opinion request created. Complete the placeholder payment to queue your case.",
    }


@router.get("/api/patient/second-opinion")
def list_second_opinion_requests(
    db: Session = Depends(get_db),
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()
    rows = (
        db.query(SecondOpinionRequest)
        .filter(SecondOpinionRequest.patient_id == profile.id)
        .order_by(SecondOpinionRequest.created_at.desc(), SecondOpinionRequest.id.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "report_id": row.report_id,
                "status": row.status,
                "payment_reference": row.payment_reference,
                "specialist_panel": row.specialist_panel,
                "premium_amount": row.premium_amount,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    }


@router.get("/api/patient/wearables")
def list_wearables(
    db: Session = Depends(get_db),
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()
    rows = (
        db.query(WearableSync)
        .filter(WearableSync.patient_id == profile.id)
        .order_by(WearableSync.updated_at.desc())
        .all()
    )
    return {
        "headline": "Connect to Fitbit/Apple Health",
        "items": [
            {
                "id": row.id,
                "provider": row.provider,
                "status": row.status,
                "last_synced_at": row.last_synced_at,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
    }


@router.post("/api/patient/wearables/connect")
def connect_wearable(
    payload: WearableConnectPayload,
    db: Session = Depends(get_db),
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()

    token = payload.token or f"mock-{secrets.token_hex(12)}"
    row = (
        db.query(WearableSync)
        .filter(WearableSync.patient_id == profile.id, WearableSync.provider == payload.provider)
        .first()
    )
    if not row:
        row = WearableSync(patient_id=profile.id, provider=payload.provider, token=token, status="connected")
        db.add(row)
    else:
        row.token = token
        row.status = "connected"
        row.last_synced_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="wearable_connected",
        entity_type="patient_wearable_sync",
        entity_id=str(row.id),
        event_meta={"provider": payload.provider},
    )

    return {
        "id": row.id,
        "provider": row.provider,
        "status": row.status,
        "message": "Connect to Fitbit/Apple Health",
    }


@router.get("/api/patient/home-collection/summary")
def home_collection_summary(
    profile: CustomerProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_phase4_schema()
    family = _patient_family_payload(profile)
    map_data = _home_collection_map(profile)
    return {
        "family_profile": family,
        "map": map_data.model_dump(),
        "eta_minutes": map_data.eta_minutes,
    }


def _mock_ocr_text(filename: str, mime_type: Optional[str], file_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if (mime_type or "").startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            with Image.open(BytesIO(file_bytes)) as image:
                width, height = image.size
        except Exception:
            width, height = 0, 0
        return (
            f"OCR mock extracted from {filename}. Image size {width}x{height}. "
            "Detected text: blood pressure 120/80, glucose 98 mg/dL, HbA1c 6.8%, medication list, and follow-up notes."
        )

    page_count_hint = max(1, len(file_bytes) // 45000)
    return (
        f"OCR mock extracted from {filename}. Approximate pages: {page_count_hint}. "
        "Detected text: lab request form, patient identity, physician note, and diagnostic history."
    )
