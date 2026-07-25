from datetime import datetime, timedelta
import secrets
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import User
from app.models.daily_entry_module import DailyEntryModule
from app.models.patient import PatientProfile
from app.models.patient_b2c import (
    DigitalConsent,
    FollowUpReminder,
    HealthGoal,
    HealthScore,
    HealthTrend,
    LoyaltyReward,
    PatientB2CAppointment,
    PatientB2CAuditLog,
    Referral,
    ReportSummary,
    TestCatalog,
)
from app.models.patient_phase4 import EmergencyAlert, PatientVaultDocument, SecondOpinionRequest, WearableSync
from app.utils.auth_system import ALGORITHM, SECRET_KEY

router = APIRouter(tags=["Patient B2C Phase 1"])
patient_security = HTTPBearer()


class OTPRequestPayload(BaseModel):
    mobile: str = Field(min_length=8, max_length=20)


class OTPVerifyPayload(BaseModel):
    mobile: str = Field(min_length=8, max_length=20)
    otp: str = Field(min_length=4, max_length=8)


class AppointmentCreatePayload(BaseModel):
    test_ids: List[int] = Field(default_factory=list)
    appointment_type: str = Field(pattern="^(Home|Center)$")
    scheduled_time: datetime


class ConsentPayload(BaseModel):
    consent_text: str = Field(min_length=10)


class ChatbotPayload(BaseModel):
    query: str = Field(min_length=2, max_length=1000)


class HealthGoalPayload(BaseModel):
    goal_type: str = Field(min_length=4, max_length=300)
    target_date: datetime
    status: str = Field(default="In Progress", min_length=2, max_length=40)


def _normalize_mobile(raw_mobile: str) -> str:
    return "".join(ch for ch in raw_mobile if ch.isdigit())


def _get_patient_profile_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(patient_security),
    db: Session = Depends(get_db),
) -> PatientProfile:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("role") != "patient":
        raise HTTPException(status_code=403, detail="Patient role required")

    profile_id = payload.get("patient_profile_id")
    if profile_id:
        profile = db.query(PatientProfile).filter(PatientProfile.id == profile_id).first()
        if profile and profile.is_active:
            return profile

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid patient session")

    user = db.query(User).filter(User.username == subject).first()
    if not user or user.role != "patient":
        raise HTTPException(status_code=401, detail="Invalid patient session")

    profile = db.query(PatientProfile).filter(PatientProfile.mobile == _normalize_mobile(user.phone or "")).first()
    if not profile or not profile.is_active:
        raise HTTPException(status_code=401, detail="Patient profile not found")
    return profile


def _ensure_patient_b2c_schema() -> None:
    # Create new B2C tables and additive columns for profile without affecting existing modules.
    Base.metadata.create_all(bind=engine, tables=[
        TestCatalog.__table__,
        PatientB2CAppointment.__table__,
        DigitalConsent.__table__,
        PatientB2CAuditLog.__table__,
        ReportSummary.__table__,
        HealthTrend.__table__,
        HealthScore.__table__,
        FollowUpReminder.__table__,
        LoyaltyReward.__table__,
        Referral.__table__,
        HealthGoal.__table__,
        WearableSync.__table__,
        SecondOpinionRequest.__table__,
        EmergencyAlert.__table__,
        PatientVaultDocument.__table__,
    ])

    with engine.begin() as conn:
        inspector = inspect(conn)
        existing_columns = {col["name"] for col in inspector.get_columns("patient_profiles")}
        dialect = conn.dialect.name

        if "otp_verification" not in existing_columns:
            if dialect == "postgresql":
                conn.execute(text("ALTER TABLE patient_profiles ADD COLUMN otp_verification BOOLEAN NOT NULL DEFAULT FALSE"))
            else:
                conn.execute(text("ALTER TABLE patient_profiles ADD COLUMN otp_verification BOOLEAN NOT NULL DEFAULT 0"))

        if "referring_doctor_id" not in existing_columns:
            conn.execute(text("ALTER TABLE patient_profiles ADD COLUMN referring_doctor_id INTEGER"))

        if "family_members_json" not in existing_columns:
            if dialect == "postgresql":
                conn.execute(text("ALTER TABLE patient_profiles ADD COLUMN family_members_json JSONB NOT NULL DEFAULT '[]'::jsonb"))
            else:
                conn.execute(text("ALTER TABLE patient_profiles ADD COLUMN family_members_json JSON NOT NULL DEFAULT '[]'"))


def _seed_test_catalog_if_empty(db: Session) -> None:
    if db.query(TestCatalog.id).first() is not None:
        return

    seed_rows = [
        TestCatalog(name="CBC", category="Hematology", price=399, preparation_instructions="No fasting required"),
        TestCatalog(name="Lipid Profile", category="Cardiac", price=899, preparation_instructions="10-12 hour fasting preferred"),
        TestCatalog(name="Thyroid Panel", category="Endocrine", price=699, preparation_instructions="Early morning sample preferred"),
        TestCatalog(name="Liver Function Test", category="Biochemistry", price=799, preparation_instructions="Avoid alcohol for 24h"),
    ]
    db.add_all(seed_rows)
    db.commit()


def _get_or_create_patient_profile(db: Session, user: User) -> PatientProfile:
    normalized_mobile = _normalize_mobile(user.phone or "")
    profile = db.query(PatientProfile).filter(PatientProfile.mobile == normalized_mobile).first()
    if profile:
        return profile

    profile = PatientProfile(
        patient_id=None,
        patient_code=f"PAT-{user.id}",
        full_name=f"{user.first_name} {user.last_name}".strip(),
        mobile=normalized_mobile,
        email=user.email,
        role="self",
        wallet_balance=0.0,
        cashback_percent=0.0,
        password="patient123",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _log_patient_audit(
    db: Session,
    patient_profile_id: int,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    event_meta: Optional[dict] = None,
) -> None:
    row = PatientB2CAuditLog(
        patient_profile_id=patient_profile_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        event_meta=event_meta or {},
    )
    db.add(row)
    db.commit()


def _resolve_patient_profile(profile: PatientProfile) -> PatientProfile:
    if not profile.mobile:
        raise HTTPException(status_code=400, detail="Patient mobile is not configured")
    return profile


@router.post("/api/patient/auth/otp")
async def request_patient_otp(
    payload: OTPRequestPayload,
    db: Session = Depends(get_db),
):
    _ensure_patient_b2c_schema()
    normalized = _normalize_mobile(payload.mobile)

    profile = db.query(PatientProfile).filter(PatientProfile.mobile == normalized).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found for this mobile")

    profile.otp_code = "123456"
    profile.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="otp_requested",
        entity_type="patient_profile",
        entity_id=str(profile.id),
        event_meta={"mobile": normalized},
    )

    return {
        "success": True,
        "message": "OTP generated successfully",
        "otp_for_dev": "123456",
    }


@router.post("/api/patient/auth/verify")
async def verify_patient_otp(
    payload: OTPVerifyPayload,
    db: Session = Depends(get_db),
):
    _ensure_patient_b2c_schema()
    normalized = _normalize_mobile(payload.mobile)

    profile = db.query(PatientProfile).filter(PatientProfile.mobile == normalized).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found for this mobile")

    if not profile.otp_code or profile.otp_code != payload.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if profile.otp_expires_at and profile.otp_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    profile.otp_verification = True
    profile.otp_code = None
    profile.otp_expires_at = None
    profile.updated_at = datetime.utcnow()
    db.commit()

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="otp_verified",
        entity_type="patient_profile",
        entity_id=str(profile.id),
        event_meta={"mobile": normalized},
    )

    return {
        "success": True,
        "message": "OTP verification successful",
    }


@router.get("/api/patient/profile")
async def get_patient_profile_phase1(
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    family_json = profile.family_members_json or []
    family_rel = [
        {
            "id": member.id,
            "name": member.name,
            "relation": member.relation,
            "mobile": member.mobile,
            "age": member.age,
        }
        for member in profile.family_members
    ]

    return {
        "id": profile.id,
        "patient_id": profile.patient_id,
        "full_name": profile.full_name,
        "mobile": profile.mobile,
        "email": profile.email,
        "otp_verification": bool(profile.otp_verification),
        "referring_doctor_id": profile.referring_doctor_id,
        "family_members": family_rel,
        "family_members_json": family_json,
    }


@router.get("/api/patient/test-catalog")
async def list_test_catalog_phase1(
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    _ = _resolve_patient_profile(profile)
    _seed_test_catalog_if_empty(db)

    tests = db.query(TestCatalog).order_by(TestCatalog.category.asc(), TestCatalog.name.asc()).all()
    return {
        "tests": [
            {
                "id": test.id,
                "name": test.name,
                "category": test.category,
                "price": test.price,
                "preparation_instructions": test.preparation_instructions,
            }
            for test in tests
        ]
    }


@router.post("/api/patient/appointments")
async def create_patient_appointment_phase1(
    payload: AppointmentCreatePayload,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    if payload.scheduled_time <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

    if not payload.test_ids:
        raise HTTPException(status_code=400, detail="At least one test must be selected")

    valid_count = (
        db.query(TestCatalog.id)
        .filter(TestCatalog.id.in_(payload.test_ids))
        .count()
    )
    if valid_count != len(set(payload.test_ids)):
        raise HTTPException(status_code=400, detail="One or more test IDs are invalid")

    appointment = PatientB2CAppointment(
        patient_profile_id=profile.id,
        test_ids=payload.test_ids,
        appointment_type=payload.appointment_type,
        scheduled_time=payload.scheduled_time,
        status="Booked",
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="appointment_created",
        entity_type="patient_b2c_appointment",
        entity_id=str(appointment.id),
        event_meta={
            "test_ids": payload.test_ids,
            "appointment_type": payload.appointment_type,
            "scheduled_time": payload.scheduled_time.isoformat(),
        },
    )

    return {
        "id": appointment.id,
        "status": appointment.status,
        "scheduled_time": appointment.scheduled_time,
        "appointment_type": appointment.appointment_type,
        "test_ids": appointment.test_ids,
    }


@router.post("/api/patient/appointments/{appointment_id}/consent")
async def add_patient_appointment_consent_phase1(
    appointment_id: int,
    payload: ConsentPayload,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    appointment = (
        db.query(PatientB2CAppointment)
        .filter(
            PatientB2CAppointment.id == appointment_id,
            PatientB2CAppointment.patient_profile_id == profile.id,
        )
        .first()
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    consent = DigitalConsent(
        appointment_id=appointment.id,
        consent_text=payload.consent_text,
        signed_at=datetime.utcnow(),
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="consent_signed",
        entity_type="patient_digital_consent",
        entity_id=str(consent.id),
        event_meta={"appointment_id": appointment.id},
    )

    return {
        "id": consent.id,
        "appointment_id": consent.appointment_id,
        "signed_at": consent.signed_at,
    }


@router.get("/api/patient/appointments/upcoming")
async def list_upcoming_patient_appointments_phase1(
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    rows = (
        db.query(PatientB2CAppointment)
        .filter(
            PatientB2CAppointment.patient_profile_id == profile.id,
            PatientB2CAppointment.scheduled_time >= datetime.utcnow(),
            PatientB2CAppointment.status.in_(["Booked", "Confirmed"]),
        )
        .order_by(PatientB2CAppointment.scheduled_time.asc())
        .all()
    )

    return {
        "appointments": [
            {
                "id": row.id,
                "test_ids": row.test_ids,
                "appointment_type": row.appointment_type,
                "scheduled_time": row.scheduled_time,
                "status": row.status,
            }
            for row in rows
        ]
    }


def _resolve_report_download_url(report_pdf_url: Optional[str]) -> Optional[str]:
    if not report_pdf_url:
        return None
    if report_pdf_url.startswith("/api/files/"):
        return report_pdf_url
    if report_pdf_url.startswith("/uploads/"):
        filename = report_pdf_url.split("/")[-1]
        return f"/api/files/daily_entry_reports/{filename}"
    return f"/api/files/{report_pdf_url.lstrip('/')}"


def _infer_abnormal_flags(test_name: str) -> Dict[str, str]:
    lowered = (test_name or "").lower()
    flags: Dict[str, str] = {}
    if "vitamin d" in lowered:
        flags["vitamin_d"] = "Low Vitamin D"
    if "hba1c" in lowered or "diabetes" in lowered:
        flags["hba1c"] = "HbA1c borderline high"
    if "lipid" in lowered or "cholesterol" in lowered:
        flags["lipid"] = "LDL needs monitoring"
    if "thyroid" in lowered or "tsh" in lowered:
        flags["thyroid"] = "Thyroid panel follow-up suggested"
    return flags


def _build_ai_summary(report: DailyEntryModule, abnormal_flags: Dict[str, str]) -> str:
    base = (
        f"Your report for {report.test_name} is currently marked as {report.status}. "
        "Most values look stable based on this preliminary AI check. "
    )
    if abnormal_flags:
        highlights = "; ".join(abnormal_flags.values())
        return base + f"Important highlights: {highlights}. Please consult your clinician for confirmation."
    return base + "No major red flags were detected from the available metadata."


def _is_critical_report(report: DailyEntryModule, abnormal_flags: Dict[str, str]) -> bool:
    lowered_name = (report.test_name or "").lower()
    lowered_status = (report.status or "").lower()
    critical_terms = ("critical", "troponin", "ecg", "d-dimer", "echo", "ct angio", "heart attack", "sepsis")
    return any(term in lowered_name for term in critical_terms) or lowered_status == "critical" or any(
        "critical" in str(value).lower() for value in abnormal_flags.values()
    )


def _auto_raise_emergency_alert(
    db: Session,
    profile: PatientProfile,
    report: DailyEntryModule,
    abnormal_flags: Dict[str, str],
) -> Optional[EmergencyAlert]:
    if not _is_critical_report(report, abnormal_flags):
        return None

    existing = (
        db.query(EmergencyAlert)
        .filter(
            EmergencyAlert.patient_id == profile.id,
            EmergencyAlert.report_id == report.id,
            EmergencyAlert.alert_type == "critical",
        )
        .first()
    )
    if existing:
        return existing

    row = EmergencyAlert(
        patient_id=profile.id,
        report_id=report.id,
        alert_type="critical",
        delivery_channels=["SMS", "In-App", "Email"],
        doctor_notified=1,
        note="Auto-triggered from critical lab report",
        triggered_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_trend_points(db: Session, profile: PatientProfile, biomarker: str) -> List[HealthTrend]:
    rows: List[HealthTrend] = []
    today = datetime.utcnow()
    for index in range(11, -1, -1):
        date_point = today - timedelta(days=index * 30)
        base_value = 6.8 if biomarker.lower() == "hba1c" else 95
        variation = (index % 4) * 0.1 if biomarker.lower() == "hba1c" else (index % 5) * 2
        value = round(base_value + variation, 2)
        graph_data = {
            "x": date_point.date().isoformat(),
            "y": value,
        }
        row = HealthTrend(
            patient_id=profile.id,
            biomarker=biomarker,
            value=str(value),
            date=date_point,
            graph_data=graph_data,
        )
        db.add(row)
        rows.append(row)
    db.commit()
    return rows


def _wallet_points_from_rewards(rows: List[LoyaltyReward]) -> int:
    total = 0
    for row in rows:
        if (row.transaction_type or "").lower() == "redemption":
            total -= abs(int(row.points or 0))
        else:
            total += abs(int(row.points or 0))
    return max(total, 0)


@router.get("/api/patient/reports")
async def list_patient_reports_phase2(
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    rows = (
        db.query(DailyEntryModule)
        .filter(DailyEntryModule.mobile == profile.mobile)
        .order_by(DailyEntryModule.auto_entry_datetime.desc())
        .all()
    )
    return {
        "reports": [
            {
                "id": row.id,
                "patient_id": row.auto_patient_id,
                "test_name": row.test_name,
                "status": row.status,
                "amount": float(row.total_amount or 0),
                "created_at": row.auto_entry_datetime.isoformat() if row.auto_entry_datetime else None,
                "download_url": _resolve_report_download_url(row.report_pdf_url),
            }
            for row in rows
        ]
    }


@router.get("/api/patient/reports/{report_id}/summary")
async def get_patient_report_summary_phase2(
    report_id: int,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    report = (
        db.query(DailyEntryModule)
        .filter(DailyEntryModule.id == report_id, DailyEntryModule.mobile == profile.mobile)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    abnormal_flags = _infer_abnormal_flags(report.test_name)
    ai_summary = _build_ai_summary(report, abnormal_flags)

    summary = (
        db.query(ReportSummary)
        .filter(ReportSummary.patient_id == profile.id, ReportSummary.report_id == report.id)
        .first()
    )
    if not summary:
        summary = ReportSummary(
            patient_id=profile.id,
            report_id=report.id,
            ai_summary=ai_summary,
            abnormal_flags=abnormal_flags,
        )
        db.add(summary)
    else:
        summary.ai_summary = ai_summary
        summary.abnormal_flags = abnormal_flags
        summary.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(summary)

    emergency_alert = _auto_raise_emergency_alert(db, profile, report, abnormal_flags)

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="report_summary_viewed",
        entity_type="patient_report_summary",
        entity_id=str(summary.id),
        event_meta={"report_id": report.id},
    )

    return {
        "report_id": report.id,
        "summary_id": summary.id,
        "ai_summary": summary.ai_summary,
        "abnormal_flags": summary.abnormal_flags,
        "critical_alert_required": bool(emergency_alert),
        "emergency_alert": None if not emergency_alert else {
            "id": emergency_alert.id,
            "alert_type": emergency_alert.alert_type,
            "triggered_at": emergency_alert.triggered_at,
            "delivery_channels": emergency_alert.delivery_channels,
        },
    }


@router.get("/api/patient/trends/{biomarker}")
async def get_patient_trends_phase2(
    biomarker: str,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    rows = (
        db.query(HealthTrend)
        .filter(HealthTrend.patient_id == profile.id, HealthTrend.biomarker.ilike(biomarker))
        .order_by(HealthTrend.date.asc())
        .all()
    )
    if not rows:
        rows = _seed_trend_points(db, profile, biomarker)

    points = [
        {
            "date": row.date.date().isoformat(),
            "value": float(row.value),
            "graph_data": row.graph_data,
        }
        for row in rows
    ]
    return {
        "biomarker": biomarker,
        "points": points,
    }


@router.get("/api/patient/health-score")
async def get_patient_health_score_phase2(
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    summaries = db.query(ReportSummary).filter(ReportSummary.patient_id == profile.id).all()
    penalty = sum(len((item.abnormal_flags or {}).keys()) * 4 for item in summaries)
    score = max(0, min(100, 92 - penalty))

    row = (
        db.query(HealthScore)
        .filter(HealthScore.patient_id == profile.id)
        .order_by(HealthScore.last_calculated.desc())
        .first()
    )
    if not row:
        row = HealthScore(patient_id=profile.id, score=score, last_calculated=datetime.utcnow())
        db.add(row)
    else:
        row.score = score
        row.last_calculated = datetime.utcnow()
    db.commit()
    db.refresh(row)

    return {
        "score": row.score,
        "last_calculated": row.last_calculated,
        "band": "Excellent" if row.score >= 85 else "Good" if row.score >= 70 else "Needs attention",
    }


@router.get("/api/patient/reminders")
async def get_patient_followup_reminders_phase2(
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    rows = (
        db.query(FollowUpReminder)
        .filter(FollowUpReminder.patient_id == profile.id)
        .order_by(FollowUpReminder.next_due_date.asc())
        .all()
    )
    if not rows:
        rows = [
            FollowUpReminder(
                patient_id=profile.id,
                test_name="HbA1c",
                next_due_date=datetime.utcnow() + timedelta(days=90),
                status="active",
            ),
            FollowUpReminder(
                patient_id=profile.id,
                test_name="Vitamin D",
                next_due_date=datetime.utcnow() + timedelta(days=60),
                status="active",
            ),
        ]
        db.add_all(rows)
        db.commit()

    reminder_payload = []
    for row in rows:
        days_left = max(0, (row.next_due_date.date() - datetime.utcnow().date()).days)
        reminder_payload.append(
            {
                "id": row.id,
                "test_name": row.test_name,
                "next_due_date": row.next_due_date,
                "status": row.status,
                "message": f"Your {row.test_name} is due in {days_left} days. Book now?",
            }
        )

    return {"reminders": reminder_payload}


@router.post("/api/patient/chatbot")
async def patient_chatbot_phase2(
    payload: ChatbotPayload,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    query = payload.query.strip().lower()
    canned_responses = {
        "hba1c": "HbA1c reflects average blood sugar over 2-3 months. Consistent exercise and low-glycemic meals can help improve it.",
        "fasting": "For fasting blood tests, avoid food for 8-12 hours unless your doctor gave different instructions.",
        "vitamin d": "Low Vitamin D is common. Morning sunlight exposure and supplementation as advised can help.",
        "lipid": "For lipid control, focus on fiber-rich meals, regular walking, and reducing trans fats.",
        "report": "You can open your report and tap Ask AI to view a plain-language summary and key flags.",
    }

    response = "I can help with test preparation, report understanding, and follow-up suggestions. Try asking about HbA1c, fasting, lipid profile, or Vitamin D."
    for keyword, text_value in canned_responses.items():
        if keyword in query:
            response = text_value
            break

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="chatbot_query",
        entity_type="patient_chatbot",
        event_meta={"query": payload.query[:200]},
    )

    return {
        "query": payload.query,
        "response": response,
    }


@router.get("/api/patient/wallet")
async def get_patient_wallet_phase3(
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    rewards = (
        db.query(LoyaltyReward)
        .filter(LoyaltyReward.patient_id == profile.id)
        .order_by(LoyaltyReward.created_at.desc())
        .all()
    )

    if not rewards:
        rewards = [
            LoyaltyReward(
                patient_id=profile.id,
                points=150,
                transaction_type="Earn",
                description="Welcome bonus for joining patient loyalty program",
            ),
            LoyaltyReward(
                patient_id=profile.id,
                points=80,
                transaction_type="Earn",
                description="Points earned for preventive test booking",
            ),
        ]
        db.add_all(rewards)
        db.commit()
        rewards = (
            db.query(LoyaltyReward)
            .filter(LoyaltyReward.patient_id == profile.id)
            .order_by(LoyaltyReward.created_at.desc())
            .all()
        )

    wallet_points = _wallet_points_from_rewards(rewards)
    payment_options = [
        {"type": "UPI", "label": "UPI (GPay/PhonePe/Paytm)"},
        {"type": "Cards", "label": "Credit/Debit Cards"},
        {"type": "Net Banking", "label": "Net Banking"},
    ]

    return {
        "available_points": wallet_points,
        "payment_history": [
            {
                "id": row.id,
                "points": row.points,
                "transaction_type": row.transaction_type,
                "description": row.description,
                "created_at": row.created_at,
            }
            for row in rewards
        ],
        "payment_options": payment_options,
    }


@router.post("/api/patient/referral")
async def create_patient_referral_phase3(
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    referral_code = f"VV-{profile.id}-{secrets.token_hex(3).upper()}"
    referral_link = f"https://vaidya-vihar.com/patient/referral/{referral_code}"

    _log_patient_audit(
        db=db,
        patient_profile_id=profile.id,
        action="referral_link_generated",
        entity_type="patient_referral",
        event_meta={"referral_code": referral_code},
    )

    return {
        "referral_code": referral_code,
        "referral_link": referral_link,
        "message": "Share this referral link with friends. Both users get loyalty points after the first completed booking.",
    }


@router.post("/api/patient/goals")
async def create_or_update_patient_goal_phase3(
    payload: HealthGoalPayload,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(_get_patient_profile_from_token),
):
    _ensure_patient_b2c_schema()
    profile = _resolve_patient_profile(profile)

    row = (
        db.query(HealthGoal)
        .filter(
            HealthGoal.patient_id == profile.id,
            HealthGoal.goal_type == payload.goal_type,
        )
        .order_by(HealthGoal.updated_at.desc())
        .first()
    )

    if not row:
        row = HealthGoal(
            patient_id=profile.id,
            goal_type=payload.goal_type,
            target_date=payload.target_date,
            status=payload.status,
        )
        db.add(row)
    else:
        row.target_date = payload.target_date
        row.status = payload.status
        row.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(row)

    challenge_reward_points = 500 if "hba1c" in payload.goal_type.lower() else 300
    return {
        "id": row.id,
        "patient_id": row.patient_id,
        "goal_type": row.goal_type,
        "target_date": row.target_date,
        "status": row.status,
        "reward_points": challenge_reward_points,
    }
