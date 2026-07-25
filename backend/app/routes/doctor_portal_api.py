"""Authenticated doctor portal APIs for clinical and referral workflows."""

import base64
import io
import logging
import secrets
import asyncio
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import qrcode
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import (
    CMECourse,
    DoctorAuditLog,
    DoctorMessage,
    DoctorReferralLog,
    Doctor,
    LabResult,
    LoyaltyReward,
    Order,
    Patient,
    PatientSearchLog,
    Staff,
    TestPanel,
    User,
)
from app.models.daily_entry_module import DailyEntryModule
from app.models.doctor import DoctorBranch
from app.models.lis import LabTestMaster
from app.models.patient import PatientProfile
from app.services.email_service import get_email_service
from app.services.sms_service import get_sms_service
from app.services.websocket_service import Notification, NotificationType, Priority, connection_manager
from app.utils.auth_system import require_role

router = APIRouter()
logger = logging.getLogger(__name__)


class DoctorProfileUpdate(BaseModel):
    upi_id: Optional[str] = None
    bank_account: Optional[str] = None
    ifsc: Optional[str] = None
    commission_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    loyalty_tier: Optional[str] = Field(default=None, pattern="^(Silver|Gold|Platinum)$")


class PatientTagUpdate(BaseModel):
    tag: str = Field(min_length=1, max_length=60)
    action: str = Field(default="add", pattern="^(add|remove)$")


class PanelCreate(BaseModel):
    panel_name: str = Field(min_length=1, max_length=200)
    test_ids: List[int] = Field(min_length=1)


class OrderCreate(BaseModel):
    patient_id: int
    test_ids: List[int] = Field(default_factory=list)
    panel_ids: List[int] = Field(default_factory=list)
    branch_id: Optional[int] = None
    clinical_notes: Optional[str] = None


class MessageCreate(BaseModel):
    receiver_id: int
    message: str = Field(min_length=1, max_length=2000)


class SymptomCheckerRequest(BaseModel):
    symptoms: List[str] = Field(min_length=1)


class ReportInterpretationRequest(BaseModel):
    report_id: int


class PredictiveAlertRequest(BaseModel):
    patient_ids: List[int] = Field(default_factory=list)


class GrowthInsightsRequest(BaseModel):
    include_window_days: int = Field(default=180, ge=30, le=365)


class WhiteLabelSettingsUpdate(BaseModel):
    clinic_name: Optional[str] = Field(default=None, max_length=200)
    clinic_address: Optional[str] = Field(default=None, max_length=1000)
    logo_url: Optional[str] = Field(default=None, max_length=500000)


SYMPTOM_AI_MAP = {
    "fever": {
        "conditions": ["Viral Fever", "Typhoid", "Dengue"],
        "tests": ["CBC", "CRP", "Dengue NS1", "Widal"],
    },
    "cough": {
        "conditions": ["Respiratory Infection", "Bronchitis", "Allergic Airway Disease"],
        "tests": ["CBC", "Chest X-Ray", "CRP"],
    },
    "chest pain": {
        "conditions": ["Cardiac Ischemia", "Costochondritis", "GERD"],
        "tests": ["ECG", "Troponin-I", "Lipid Profile"],
    },
    "fatigue": {
        "conditions": ["Anemia", "Hypothyroidism", "Vitamin Deficiency"],
        "tests": ["CBC", "TSH", "Vitamin B12", "Vitamin D"],
    },
    "polyuria": {
        "conditions": ["Type 2 Diabetes", "Urinary Tract Irritation"],
        "tests": ["Fasting Glucose", "HbA1c", "Urine Routine"],
    },
}


LOYALTY_BENEFITS_MAP = {
    "Silver": ["Basic referral dashboard", "Monthly performance summary"],
    "Gold": ["Priority report notifications", "5% discount on premium panels", "Dedicated lab coordinator"],
    "Platinum": ["Priority support line", "Early-access CME webinars", "Co-branded patient engagement kit"],
}


def _doctor(current_user: User = Depends(require_role(["doctor"]))) -> User:
    return current_user


def _get_doctor(current_user: User, db: Session) -> Doctor:
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        doctor = db.query(Doctor).filter(Doctor.email == current_user.email).first()

    # Self-heal legacy users that have doctor role but no doctors-table profile yet.
    if not doctor:
        seed_email = (current_user.email or "").strip() or f"{current_user.username}@vaidyavihar.local"
        base_doctor_id = f"DOC-U{current_user.id:04d}"
        generated_doctor_id = base_doctor_id
        suffix = 1
        while db.query(Doctor).filter(Doctor.doctor_id == generated_doctor_id).first():
            suffix += 1
            generated_doctor_id = f"{base_doctor_id}-{suffix}"

        doctor = Doctor(
            doctor_id=generated_doctor_id,
            first_name=(current_user.first_name or "Doctor").strip() or "Doctor",
            last_name=(current_user.last_name or "User").strip() or "User",
            email=seed_email,
            phone=(current_user.phone or "0000000000").strip() or "0000000000",
            qualification="MBBS",
            specialization="General Medicine",
            user_id=current_user.id,
            username=current_user.username,
            is_active=True,
            is_verified=False,
        )
        db.add(doctor)
        db.flush()

        if current_user.branch_id:
            branch_link = db.query(DoctorBranch).filter(
                DoctorBranch.doctor_id == doctor.id,
                DoctorBranch.branch_id == current_user.branch_id,
            ).first()
            if not branch_link:
                db.add(
                    DoctorBranch(
                        doctor_id=doctor.id,
                        branch_id=current_user.branch_id,
                        assigned_by=current_user.id,
                        is_primary=True,
                        is_active=True,
                    )
                )

        db.commit()
        db.refresh(doctor)

    if doctor and doctor.user_id != current_user.id:
        doctor.user_id = current_user.id
        db.commit()
        db.refresh(doctor)

    if not doctor.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile is not configured")

    if current_user.branch_id:
        branch_link = db.query(DoctorBranch).filter(
            DoctorBranch.doctor_id == doctor.id,
            DoctorBranch.branch_id == current_user.branch_id,
        ).first()
        if not branch_link:
            db.add(
                DoctorBranch(
                    doctor_id=doctor.id,
                    branch_id=current_user.branch_id,
                    assigned_by=current_user.id,
                    is_primary=not db.query(DoctorBranch).filter(DoctorBranch.doctor_id == doctor.id, DoctorBranch.is_active.is_(True)).first(),
                    is_active=True,
                )
            )
            db.commit()

    return doctor


def _branch_ids(doctor: Doctor) -> List[int]:
    return [branch.branch_id for branch in doctor.branches if branch.is_active]


def _patient_or_404(patient_id: int, doctor: Doctor, db: Session) -> Patient:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient or patient.branch_id not in _branch_ids(doctor):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


def _patient_payload(patient: Patient) -> dict:
    return {
        "id": patient.id,
        "patient_id": patient.patient_id,
        "name": f"{patient.first_name} {patient.last_name}".strip(),
        "phone": patient.phone,
        "email": patient.email,
        "address": patient.address,
        "city": patient.city,
        "state": patient.state,
        "blood_group": patient.blood_group,
        "tags": patient.tags or [],
        "registration_date": patient.registration_date.isoformat() if patient.registration_date else None,
    }


def _lab_team_users(doctor: Doctor, db: Session) -> List[User]:
    branch_ids = _branch_ids(doctor)
    staff_user_ids = [row[0] for row in db.query(Staff.user_id).filter(Staff.branch_id.in_(branch_ids)).all()]
    users = db.query(User).filter(User.id.in_(staff_user_ids), User.is_active.is_(True)).all()
    return users


def _normalize_tier(tier: Optional[str]) -> str:
    allowed = {"Silver", "Gold", "Platinum"}
    if tier in allowed:
        return tier
    return "Silver"


def _log_doctor_audit(
    db: Session,
    *,
    doctor: Doctor,
    user: User,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    event_meta: Optional[Dict] = None,
) -> None:
    db.add(
        DoctorAuditLog(
            doctor_id=doctor.id,
            user_id=user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            event_meta=event_meta or {},
        )
    )


def _send_patient_order_notifications_task(*, patient_id: int, order_id: int, doctor_name: str) -> None:
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return

        profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id, PatientProfile.is_active.is_(True)).first()
        if not profile:
            profile = db.query(PatientProfile).filter(PatientProfile.mobile == patient.phone, PatientProfile.is_active.is_(True)).first()
        if not profile:
            return

        message = (
            f"Hi {profile.full_name}, Dr. {doctor_name} has placed your diagnostic order "
            f"(Order #{order_id}). You will be notified when reports are ready."
        )

        if profile.mobile:
            try:
                asyncio.run(get_sms_service().send_sms(profile.mobile, message, priority="normal"))
            except Exception:
                logger.exception("Failed to send patient SMS notification for order %s", order_id)

        if profile.email:
            try:
                get_email_service().send_email(
                    profile.email,
                    "Doctor Order Created - VaidyaVihar Diagnostic",
                    f"<p>{message}</p>",
                )
            except Exception:
                logger.exception("Failed to send patient email notification for order %s", order_id)

        try:
            patient_user = db.query(User).filter(
                User.role == "patient",
                or_(User.email == profile.email, User.phone == profile.mobile),
                User.is_active.is_(True),
            ).first()
            if patient_user:
                notification = Notification(
                    id=f"PAT-ORD-{order_id}-{int(datetime.utcnow().timestamp())}",
                    type=NotificationType.SYSTEM_ANNOUNCEMENT.value,
                    title="New Doctor Order",
                    message=message,
                    priority=Priority.NORMAL.value,
                    data={"order_id": order_id, "patient_profile_id": profile.id},
                    action_url="/patient-portal",
                    reference_id=str(order_id),
                    reference_type="doctor_order",
                )
                asyncio.run(connection_manager.send_personal_notification(patient_user.id, notification))
        except Exception:
            logger.exception("Failed to send in-app patient notification for order %s", order_id)

    finally:
        db.close()


def _ensure_loyalty_reward(doctor: Doctor, db: Session) -> LoyaltyReward:
    reward = db.query(LoyaltyReward).filter(LoyaltyReward.doctor_id == doctor.id).first()
    if reward:
        if not reward.benefits:
            reward.benefits = LOYALTY_BENEFITS_MAP.get(_normalize_tier(reward.tier), LOYALTY_BENEFITS_MAP["Silver"])
            db.commit()
            db.refresh(reward)
        return reward
    tier = _normalize_tier(doctor.loyalty_tier)
    reward = LoyaltyReward(
        doctor_id=doctor.id,
        tier=tier,
        benefits=LOYALTY_BENEFITS_MAP.get(tier, LOYALTY_BENEFITS_MAP["Silver"]),
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


def _get_white_label_settings(doctor: Doctor) -> dict:
    preferences = doctor.report_preferences if isinstance(doctor.report_preferences, dict) else {}
    settings = preferences.get("white_label") if isinstance(preferences, dict) else None
    if not isinstance(settings, dict):
        settings = {}
    return {
        "clinic_name": (settings.get("clinic_name") or "").strip(),
        "clinic_address": (settings.get("clinic_address") or "").strip(),
        "logo_url": (settings.get("logo_url") or "").strip(),
    }


def _set_white_label_settings(doctor: Doctor, payload: WhiteLabelSettingsUpdate) -> dict:
    current_preferences = doctor.report_preferences if isinstance(doctor.report_preferences, dict) else {}
    settings = current_preferences.get("white_label") if isinstance(current_preferences.get("white_label"), dict) else {}
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        settings[key] = (value or "").strip()
    current_preferences["white_label"] = settings
    doctor.report_preferences = current_preferences
    return {
        "clinic_name": (settings.get("clinic_name") or "").strip(),
        "clinic_address": (settings.get("clinic_address") or "").strip(),
        "logo_url": (settings.get("logo_url") or "").strip(),
    }


@router.get("/profile")
def get_doctor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    return {
        "id": doctor.id,
        "doctor_id": doctor.doctor_id,
        "name": doctor.full_name,
        "email": doctor.email,
        "phone": doctor.phone,
        "qualification": doctor.qualification,
        "specialization": doctor.specialization,
        "upi_id": doctor.upi_id,
        "bank_account": doctor.bank_account,
        "ifsc": doctor.ifsc,
        "commission_percentage": doctor.commission_percentage or 0,
        "loyalty_tier": doctor.loyalty_tier or "Silver",
        "branch_ids": _branch_ids(doctor),
    }


@router.put("/profile")
def update_doctor_profile(
    payload: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    return get_doctor_profile(db=db, current_user=current_user)


@router.get("/white-label")
def get_white_label_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    return _get_white_label_settings(doctor)


@router.put("/white-label")
def update_white_label_settings(
    payload: WhiteLabelSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    response = _set_white_label_settings(doctor, payload)
    db.commit()
    db.refresh(doctor)
    return response


@router.get("/patients")
def search_doctor_patients(
    search: str = Query(default="", max_length=255),
    tag: Optional[str] = Query(default=None, max_length=60),
    date: Optional[str] = Query(default=None, description="Registration date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    query = db.query(Patient).filter(Patient.branch_id.in_(_branch_ids(doctor)))
    normalized_search = search.strip()
    if normalized_search:
        like = f"%{normalized_search}%"
        result_patient_ids = db.query(LabResult.patient_id).filter(cast(LabResult.result_value, String).ilike(like))
        query = query.filter(or_(
            Patient.patient_id.ilike(like),
            Patient.first_name.ilike(like),
            Patient.last_name.ilike(like),
            Patient.phone.ilike(like),
            Patient.email.ilike(like),
            Patient.id.in_(result_patient_ids),
        ))
    if date:
        try:
            registration_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as error:
            raise HTTPException(status_code=400, detail="date must use YYYY-MM-DD format") from error
        query = query.filter(Patient.registration_date >= datetime.combine(registration_date, datetime.min.time()), Patient.registration_date < datetime.combine(registration_date, datetime.max.time()))
    patients = query.order_by(Patient.registration_date.desc()).limit(50).all()
    if tag:
        patients = [patient for patient in patients if tag in (patient.tags or [])]

    db.add(PatientSearchLog(doctor_id=doctor.id, query=normalized_search or tag or date or "*", result_count=len(patients)))
    _log_doctor_audit(
        db,
        doctor=doctor,
        user=current_user,
        action="PATIENT_SEARCH",
        entity_type="Patient",
        entity_id=None,
        event_meta={"query": normalized_search, "tag": tag, "date": date, "result_count": len(patients)},
    )
    db.commit()
    return {"patients": [_patient_payload(patient) for patient in patients], "count": len(patients)}


@router.post("/patients/{patient_id}/tags")
def update_patient_tags(
    patient_id: int,
    payload: PatientTagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    patient = _patient_or_404(patient_id, doctor, db)
    tags = list(patient.tags or [])
    if payload.action == "add" and payload.tag not in tags:
        tags.append(payload.tag)
    if payload.action == "remove":
        tags = [tag for tag in tags if tag != payload.tag]
    patient.tags = tags
    db.commit()
    return {"patient_id": patient.id, "tags": tags}


@router.get("/patients/{patient_id}/timeline")
def patient_timeline(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    patient = _patient_or_404(patient_id, doctor, db)
    events = [
        {
            "type": "registration",
            "date": patient.registration_date.isoformat() if patient.registration_date else None,
            "title": "Patient registered",
            "details": patient.patient_id,
        }
    ]
    for entry in db.query(DailyEntryModule).filter(
        DailyEntryModule.branch_id.in_(_branch_ids(doctor)),
        or_(DailyEntryModule.mobile == patient.phone, DailyEntryModule.auto_patient_id == patient.patient_id),
    ).order_by(DailyEntryModule.auto_entry_datetime.desc()).limit(100).all():
        events.append({"type": "visit", "date": entry.auto_entry_datetime.isoformat(), "title": entry.test_name, "details": entry.status, "report_url": entry.report_pdf_url})
    for result in db.query(LabResult).filter(LabResult.patient_id == patient.id).order_by(LabResult.id.desc()).limit(100).all():
        events.append({"type": "result", "date": None, "title": result.test_name, "details": f"{result.result_value} {result.unit or ''}".strip()})
    events.sort(key=lambda event: event["date"] or "", reverse=True)
    _log_doctor_audit(
        db,
        doctor=doctor,
        user=current_user,
        action="REPORT_VIEW",
        entity_type="Patient",
        entity_id=str(patient.id),
        event_meta={"events_with_reports": len([event for event in events if event.get("report_url")])},
    )
    db.commit()
    return {"patient": _patient_payload(patient), "events": events}


@router.get("/test-catalog")
def doctor_test_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    _get_doctor(current_user, db)
    tests = db.query(LabTestMaster).filter(LabTestMaster.is_active.is_(True)).order_by(LabTestMaster.test_name).all()
    return {"tests": [{
        "id": test.id,
        "test_code": test.test_code,
        "test_name": test.test_name,
        "category": test.category.value if test.category else None,
        "base_price": test.base_price,
        "discounted_price": test.discounted_price,
        "turnaround_time_hours": test.turnaround_time_hours,
    } for test in tests]}


@router.post("/panels")
def create_panel(
    payload: PanelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    valid_ids = {row[0] for row in db.query(LabTestMaster.id).filter(LabTestMaster.id.in_(payload.test_ids)).all()}
    if set(payload.test_ids) != valid_ids:
        raise HTTPException(status_code=400, detail="One or more tests are not in the catalog")
    panel = TestPanel(doctor_id=doctor.id, panel_name=payload.panel_name.strip(), test_ids=payload.test_ids, is_custom=True)
    db.add(panel)
    db.commit()
    db.refresh(panel)
    return {"id": panel.id, "panel_name": panel.panel_name, "test_ids": panel.test_ids, "is_custom": panel.is_custom}


@router.get("/panels")
def list_panels(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    panels = db.query(TestPanel).filter(TestPanel.doctor_id == doctor.id).order_by(TestPanel.panel_name).all()
    return {"panels": [{"id": panel.id, "panel_name": panel.panel_name, "test_ids": panel.test_ids or [], "is_custom": panel.is_custom} for panel in panels]}


@router.post("/orders")
def create_doctor_order(
    payload: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    patient = _patient_or_404(payload.patient_id, doctor, db)
    panel_rows = db.query(TestPanel).filter(TestPanel.id.in_(payload.panel_ids), TestPanel.doctor_id == doctor.id).all() if payload.panel_ids else []
    combined_test_ids = set(payload.test_ids)
    for panel in panel_rows:
        combined_test_ids.update(panel.test_ids or [])
    valid_ids = {row[0] for row in db.query(LabTestMaster.id).filter(LabTestMaster.id.in_(combined_test_ids)).all()}
    if not combined_test_ids or valid_ids != combined_test_ids:
        raise HTTPException(status_code=400, detail="Select valid catalog tests or panels")
    branch_id = payload.branch_id or patient.branch_id
    if branch_id not in _branch_ids(doctor):
        raise HTTPException(status_code=403, detail="Doctor is not assigned to this branch")
    order = Order(
        doctor_id=doctor.id,
        patient_id=patient.id,
        branch_id=branch_id,
        status="Sent",
        test_ids=sorted(combined_test_ids),
        panel_ids=payload.panel_ids,
        clinical_notes=payload.clinical_notes,
    )
    db.add(order)
    price_rows = db.query(LabTestMaster.id, LabTestMaster.discounted_price, LabTestMaster.base_price).filter(LabTestMaster.id.in_(combined_test_ids)).all()
    order_total = sum((row[1] if row[1] and row[1] > 0 else row[2] or 0) for row in price_rows)
    commission_amount = round((order_total * (doctor.commission_percentage or 0)) / 100, 2)
    db.flush()
    db.add(DoctorReferralLog(
        doctor_id=doctor.id,
        patient_id=patient.id,
        order_id=order.id,
        commission_amount=commission_amount,
        status="Pending",
    ))
    _log_doctor_audit(
        db,
        doctor=doctor,
        user=current_user,
        action="ORDER_CREATE",
        entity_type="Order",
        entity_id=None,
        event_meta={
            "patient_id": patient.id,
            "branch_id": branch_id,
            "test_ids": sorted(combined_test_ids),
            "panel_ids": payload.panel_ids,
            "estimated_order_total": order_total,
            "commission_amount": commission_amount,
        },
    )
    db.commit()
    db.refresh(order)
    _log_doctor_audit(
        db,
        doctor=doctor,
        user=current_user,
        action="ORDER_CREATE_COMMIT",
        entity_type="Order",
        entity_id=str(order.id),
        event_meta={"status": order.status},
    )
    db.commit()
    background_tasks.add_task(
        _send_patient_order_notifications_task,
        patient_id=patient.id,
        order_id=order.id,
        doctor_name=doctor.full_name,
    )
    return {"id": order.id, "patient_id": order.patient_id, "test_ids": order.test_ids, "status": order.status, "order_date": order.order_date.isoformat()}


@router.get("/orders")
def list_doctor_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    orders = db.query(Order).filter(Order.doctor_id == doctor.id).order_by(Order.order_date.desc()).limit(50).all()
    _log_doctor_audit(
        db,
        doctor=doctor,
        user=current_user,
        action="ORDER_LIST_VIEW",
        entity_type="Order",
        entity_id=None,
        event_meta={"count": len(orders)},
    )
    db.commit()
    return {"orders": [{
        "id": order.id,
        "patient_id": order.patient_id,
        "test_ids": order.test_ids or [],
        "panel_ids": order.panel_ids or [],
        "status": order.status,
        "order_date": order.order_date.isoformat() if order.order_date else None,
    } for order in orders]}


@router.post("/orders/{order_id}/qr")
def generate_order_qr(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    order = db.query(Order).filter(Order.id == order_id, Order.doctor_id == doctor.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.qr_token = secrets.token_urlsafe(32)
    _log_doctor_audit(
        db,
        doctor=doctor,
        user=current_user,
        action="ORDER_QR_GENERATE",
        entity_type="Order",
        entity_id=str(order.id),
        event_meta={"patient_id": order.patient_id},
    )
    db.commit()
    qr = qrcode.make(order.qr_token)
    output = io.BytesIO()
    qr.save(output, format="PNG")
    image = base64.b64encode(output.getvalue()).decode("ascii")
    return {"order_id": order.id, "qr_token": order.qr_token, "qr_code": f"data:image/png;base64,{image}"}


@router.get("/messages")
def get_messages(
    with_user_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    lab_team = _lab_team_users(doctor, db)
    lab_user_ids = {user.id for user in lab_team}
    messages = db.query(DoctorMessage).filter(
        or_(
            DoctorMessage.sender_id == current_user.id,
            DoctorMessage.receiver_id == current_user.id,
        )
    ).order_by(DoctorMessage.created_at.asc()).all()
    filtered = [
        message for message in messages
        if (message.sender_id in lab_user_ids or message.receiver_id in lab_user_ids)
    ]
    if with_user_id is not None:
        filtered = [
            message for message in filtered
            if with_user_id in (message.sender_id, message.receiver_id)
        ]
    return {
        "lab_team": [{
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "role": user.role,
            "branch_id": user.branch_id,
        } for user in lab_team],
        "messages": [{
            "id": message.id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "message": message.message,
            "read_at": message.read_at.isoformat() if message.read_at else None,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        } for message in filtered],
    }


@router.post("/messages")
def send_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    lab_team = _lab_team_users(doctor, db)
    lab_user_ids = {user.id for user in lab_team}
    if payload.receiver_id not in lab_user_ids:
        raise HTTPException(status_code=403, detail="Receiver is not in your lab team scope")
    message = DoctorMessage(
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        message=payload.message.strip(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "message": message.message,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


@router.get("/alerts/critical")
def critical_alerts(
    threshold_high: float = Query(default=200),
    threshold_low: float = Query(default=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    patient_ids = [row[0] for row in db.query(Patient.id).filter(Patient.branch_id.in_(_branch_ids(doctor))).all()]
    rows = db.query(LabResult).filter(LabResult.patient_id.in_(patient_ids)).all()
    alerts = []
    for row in rows:
        value = row.result_value
        if value is None:
            continue
        if value >= threshold_high or value <= threshold_low:
            patient = db.query(Patient).filter(Patient.id == row.patient_id).first()
            alerts.append({
                "result_id": row.id,
                "patient_id": row.patient_id,
                "patient_name": f"{patient.first_name} {patient.last_name}".strip() if patient else "Unknown",
                "test_name": row.test_name,
                "result_value": value,
                "unit": row.unit,
                "reference_range": row.reference_range,
                "severity": "high" if value >= threshold_high else "low",
            })
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/analytics")
def doctor_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    orders = db.query(Order).filter(Order.doctor_id == doctor.id).all()
    test_counter: Counter[str] = Counter()
    monthly_counter: Counter[str] = Counter()
    patient_ids = {order.patient_id for order in orders}
    for order in orders:
        month_key = (order.order_date or datetime.utcnow()).strftime("%Y-%m")
        monthly_counter[month_key] += 1
        if not order.test_ids:
            continue
        names = db.query(LabTestMaster.test_name).filter(LabTestMaster.id.in_(order.test_ids)).all()
        for row in names:
            test_counter[row[0]] += 1

    demographics = {"male": 0, "female": 0, "other": 0, "age_groups": {"0-18": 0, "19-40": 0, "41-60": 0, "61+": 0}}
    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all() if patient_ids else []
    today = datetime.utcnow().date()
    for patient in patients:
        gender = (patient.gender or "other").lower()
        if gender in demographics:
            demographics[gender] += 1
        else:
            demographics["other"] += 1
        age = 0
        if patient.date_of_birth:
            age = max(0, today.year - patient.date_of_birth.year)
        if age <= 18:
            demographics["age_groups"]["0-18"] += 1
        elif age <= 40:
            demographics["age_groups"]["19-40"] += 1
        elif age <= 60:
            demographics["age_groups"]["41-60"] += 1
        else:
            demographics["age_groups"]["61+"] += 1

    six_months = [(datetime.utcnow() - timedelta(days=30 * idx)).strftime("%Y-%m") for idx in range(5, -1, -1)]
    trends = [{"month": key, "orders": monthly_counter.get(key, 0)} for key in six_months]
    common_tests = [{"test_name": name, "count": count} for name, count in test_counter.most_common(10)]
    return {"common_tests": common_tests, "demographics": demographics, "trends": trends}


@router.get("/referral-tracker")
def referral_tracker(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    logs = db.query(DoctorReferralLog).filter(DoctorReferralLog.doctor_id == doctor.id).all()
    total_referrals = len(logs)
    active_patients = len({log.patient_id for log in logs})
    commission_earned = round(sum(log.commission_amount or 0 for log in logs if log.status == "Paid"), 2)
    commission_pending = round(sum(log.commission_amount or 0 for log in logs if log.status != "Paid"), 2)
    return {
        "total_referrals": total_referrals,
        "active_patients": active_patients,
        "commission_earned": commission_earned,
        "commission_pending": commission_pending,
    }


@router.get("/commission/statement")
def commission_statement(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    logs = db.query(DoctorReferralLog).filter(DoctorReferralLog.doctor_id == doctor.id).order_by(DoctorReferralLog.created_at.desc()).all()
    rows = []
    for log in logs:
        patient = db.query(Patient).filter(Patient.id == log.patient_id).first()
        rows.append({
            "id": log.id,
            "order_id": log.order_id,
            "patient_id": log.patient_id,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip() if patient else "Unknown",
            "commission_amount": round(log.commission_amount or 0, 2),
            "status": log.status,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "paid_at": log.paid_at.isoformat() if log.paid_at else None,
        })
    return {
        "rows": rows,
        "totals": {
            "earned": round(sum(row["commission_amount"] for row in rows if row["status"] == "Paid"), 2),
            "pending": round(sum(row["commission_amount"] for row in rows if row["status"] != "Paid"), 2),
            "total": round(sum(row["commission_amount"] for row in rows), 2),
        },
    }


@router.get("/wallet")
def doctor_wallet(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    logs = db.query(DoctorReferralLog).filter(DoctorReferralLog.doctor_id == doctor.id).all()
    total_referrals = len(logs)
    commission_paid = round(sum(log.commission_amount or 0 for log in logs if log.status == "Paid"), 2)
    commission_pending = round(sum(log.commission_amount or 0 for log in logs if log.status != "Paid"), 2)
    commission_total = round(commission_paid + commission_pending, 2)
    return {
        "total_referrals": total_referrals,
        "commission_total": commission_total,
        "commission_earned": commission_paid,
        "commission_paid": commission_paid,
        "commission_pending": commission_pending,
    }


@router.get("/loyalty")
def loyalty_program(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    reward = _ensure_loyalty_reward(doctor, db)
    return {
        "tier": reward.tier,
        "benefits": reward.benefits or [],
    }


@router.get("/cme-courses")
def cme_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    _get_doctor(current_user, db)
    rows = db.query(CMECourse).filter(CMECourse.is_active.is_(True)).order_by(CMECourse.id.desc()).all()
    if not rows:
        seed_rows = [
            CMECourse(
                title="CME: Diabetes in Primary Care",
                description="Evidence-based screening and management update for outpatient doctors.",
                duration="60 min",
                link="https://example.org/cme/diabetes-primary-care",
                is_active=True,
            ),
            CMECourse(
                title="CME: Rational Antibiotic Use",
                description="Practical protocol to reduce resistance in routine OPD and referral workflows.",
                duration="45 min",
                link="https://example.org/cme/antibiotic-stewardship",
                is_active=True,
            ),
            CMECourse(
                title="Webinar: Thyroid and Metabolic Risk",
                description="How to use TSH and HbA1c intelligently in high-volume clinics.",
                duration="50 min",
                link="https://example.org/cme/thyroid-metabolic-risk",
                is_active=True,
            ),
        ]
        db.add_all(seed_rows)
        db.commit()
        rows = db.query(CMECourse).filter(CMECourse.is_active.is_(True)).order_by(CMECourse.id.desc()).all()
    return {
        "courses": [{
            "id": row.id,
            "title": row.title,
            "description": row.description,
            "duration": row.duration,
            "link": row.link,
        } for row in rows]
    }


@router.post("/ai/symptom-checker")
def ai_symptom_checker(
    payload: SymptomCheckerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    _get_doctor(current_user, db)
    matched_conditions = []
    recommended_tests = []
    normalized = [item.strip().lower() for item in payload.symptoms if item.strip()]
    for symptom in normalized:
        for key, mapping in SYMPTOM_AI_MAP.items():
            if key in symptom:
                matched_conditions.extend(mapping["conditions"])
                recommended_tests.extend(mapping["tests"])
    if not matched_conditions:
        matched_conditions = ["Non-specific presentation", "Needs focused clinical correlation"]
        recommended_tests = ["CBC", "CRP", "LFT", "RFT"]
    # Preserve order while removing duplicates.
    uniq_conditions = list(dict.fromkeys(matched_conditions))
    uniq_tests = list(dict.fromkeys(recommended_tests))
    return {
        "symptoms": payload.symptoms,
        "possible_conditions": uniq_conditions,
        "recommended_tests": uniq_tests,
        "disclaimer": "AI mock output for triage support only. Confirm with clinical judgement.",
    }


@router.post("/ai/report-interpretation")
def ai_report_interpretation(
    payload: ReportInterpretationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    _get_doctor(current_user, db)
    result = db.query(LabResult).filter(LabResult.id == payload.report_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    interpretation = f"{result.test_name} is reported as {result.result_value} {result.unit or ''}.".strip()
    if result.reference_range:
        interpretation += f" Reference range is {result.reference_range}."
    interpretation += " This automated summary is informational and should be validated by the treating clinician."
    return {
        "report_id": result.id,
        "summary": interpretation,
    }


@router.post("/ai/predictive-alert")
def ai_predictive_alert(
    payload: PredictiveAlertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    scoped_patients = db.query(Patient).filter(Patient.branch_id.in_(_branch_ids(doctor))).all()
    if payload.patient_ids:
        scoped_patients = [patient for patient in scoped_patients if patient.id in set(payload.patient_ids)]

    alerts = []
    for patient in scoped_patients:
        results = db.query(LabResult).filter(LabResult.patient_id == patient.id).all()
        has_glucose_risk = any((row.test_name or "").lower().find("glucose") >= 0 and (row.result_value or 0) >= 126 for row in results)
        has_hba1c_risk = any((row.test_name or "").lower().find("hba1c") >= 0 and (row.result_value or 0) >= 6.5 for row in results)
        has_lipid_risk = any((row.test_name or "").lower().find("cholesterol") >= 0 and (row.result_value or 0) >= 240 for row in results)
        tags = [tag.lower() for tag in (patient.tags or [])]
        if has_glucose_risk or has_hba1c_risk or "diabetic" in tags or "diabetes" in tags:
            alerts.append({
                "patient_id": patient.id,
                "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                "risk": "Type 2 Diabetes",
                "message": f"{patient.first_name} is at risk for Type 2 Diabetes. Consider HbA1c and lifestyle intervention review.",
            })
        if has_lipid_risk:
            alerts.append({
                "patient_id": patient.id,
                "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                "risk": "Cardiometabolic",
                "message": f"{patient.first_name} has elevated cholesterol trend and may need cardiovascular risk workup.",
            })
    return {
        "alerts": alerts,
        "count": len(alerts),
        "disclaimer": "Predictive alerts are mock AI signals and not diagnostic conclusions.",
    }


@router.post("/ai/growth-insights")
def ai_growth_insights(
    payload: GrowthInsightsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_doctor),
):
    doctor = _get_doctor(current_user, db)
    _ = payload.include_window_days
    logs = db.query(DoctorReferralLog).filter(DoctorReferralLog.doctor_id == doctor.id).all()
    patient_ids = sorted({log.patient_id for log in logs})
    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all() if patient_ids else []
    diabetic_ids = []
    no_hba1c_ids = []
    for patient in patients:
        tags = [tag.lower() for tag in (patient.tags or [])]
        results = db.query(LabResult).filter(LabResult.patient_id == patient.id).all()
        has_hba1c = any("hba1c" in (row.test_name or "").lower() for row in results)
        is_diabetic = "diabetic" in tags or "diabetes" in tags or any(
            "hba1c" in (row.test_name or "").lower() and (row.result_value or 0) >= 6.5
            for row in results
        )
        if is_diabetic:
            diabetic_ids.append(patient.id)
            if not has_hba1c:
                no_hba1c_ids.append(patient.id)

    reminders = []
    if no_hba1c_ids:
        reminders.append(f"You have {len(no_hba1c_ids)} diabetic patients without an HbA1c record in available data.")
    if len(patient_ids) >= 20:
        reminders.append("Your referral base is strong. Consider creating preventive health panels for chronic-care follow-up.")
    if not reminders:
        reminders.append("Continue monthly follow-up outreach for chronic patients to improve retention and outcomes.")

    return {
        "doctor_id": doctor.id,
        "insights": reminders,
        "summary": {
            "total_referred_patients": len(patient_ids),
            "diabetic_patients": len(diabetic_ids),
            "diabetic_without_hba1c": len(no_hba1c_ids),
        },
        "disclaimer": "Growth insights are mock AI recommendations for engagement planning.",
    }