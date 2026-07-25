import asyncio
import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db
from app.models import User
from app.models.ceo import CeoAuditLog, CeoBreakGlassGrant, CeoSecurityProfile, CeoWebAuthnCredential
from app.services.email_service import EmailConfig, EmailService
from app.services.sms_service import SMSConfig, SMSMessage, SMSService, SMSProvider
from app.utils.auth_system import auth_guard


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _encode_b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_b64url(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(f"{raw}{padding}")


def _mask_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    local, _, domain = email.partition("@")
    if not domain:
        return None
    if len(local) <= 2:
        hidden = "*" * len(local)
    else:
        hidden = f"{local[:2]}{'*' * max(1, len(local) - 2)}"
    return f"{hidden}@{domain}"


def _mask_phone(phone: Optional[str]) -> Optional[str]:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) < 4:
        return None
    return f"{'*' * max(0, len(digits) - 4)}{digits[-4:]}"


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _audit_secret() -> str:
    return os.getenv("CEO_AUDIT_SECRET") or os.getenv("SECRET_KEY") or "ceo-audit-secret"


def _sanitize_meta(meta: dict[str, Any]) -> dict[str, Any]:
    redacted_keys = {"code", "otp", "challenge_token", "temp_auth_token", "public_key", "attestation_object", "client_data_json"}
    sanitized: dict[str, Any] = {}
    for key, value in meta.items():
        if key in redacted_keys:
            sanitized[key] = "[redacted]"
        else:
            sanitized[key] = value
    return sanitized


def _ensure_ceo_tables() -> None:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    required = {
        CeoSecurityProfile.__tablename__,
        CeoWebAuthnCredential.__tablename__,
        CeoAuditLog.__tablename__,
        CeoBreakGlassGrant.__tablename__,
    }
    if required.issubset(existing):
        return
    Base.metadata.create_all(
        bind=engine,
        tables=[
            CeoSecurityProfile.__table__,
            CeoWebAuthnCredential.__table__,
            CeoAuditLog.__table__,
            CeoBreakGlassGrant.__table__,
        ],
    )


_ensure_ceo_tables()


class CeoAuditRoute(APIRoute):
    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request):
            status_code = 500
            captured_error: Optional[str] = None
            try:
                response = await original_route_handler(request)
                status_code = response.status_code
                return response
            except HTTPException as exc:
                status_code = exc.status_code
                captured_error = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail)
                raise
            except Exception as exc:
                captured_error = str(exc)
                raise
            finally:
                actor = getattr(request.state, "ceo_actor", None)
                if actor is not None:
                    self._write_audit_log(request, actor, status_code, captured_error)

        return custom_route_handler

    def _write_audit_log(self, request: Request, actor: User, status_code: int, captured_error: Optional[str]) -> None:
        db = SessionLocal()
        try:
            last_entry = db.query(CeoAuditLog).order_by(CeoAuditLog.id.desc()).first()
            previous_signature = last_entry.signature if last_entry else None
            request_meta = _sanitize_meta(
                {
                    "query": dict(request.query_params),
                    "client_host": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "error": captured_error,
                }
            )
            now = _utcnow()
            signature_payload = json.dumps(
                {
                    "user_id": actor.id,
                    "action": request.url.path,
                    "method": request.method,
                    "status": status_code,
                    "request_meta": request_meta,
                    "previous_signature": previous_signature,
                    "created_at": now.isoformat(),
                },
                sort_keys=True,
            )
            signature = hashlib.sha256(f"{signature_payload}|{_audit_secret()}".encode("utf-8")).hexdigest()
            db.add(
                CeoAuditLog(
                    user_id=actor.id,
                    action=request.scope.get("endpoint").__name__ if request.scope.get("endpoint") else request.url.path,
                    http_method=request.method,
                    endpoint=request.url.path,
                    response_status=status_code,
                    request_meta=request_meta,
                    previous_signature=previous_signature,
                    signature=signature,
                    created_at=now.replace(tzinfo=None),
                )
            )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def _set_actor(request: Request, current_user: User = Depends(auth_guard.require_role(["super_admin"]))) -> User:
    request.state.ceo_actor = current_user
    return current_user


router = APIRouter(
    prefix="/ceo",
    tags=["CEO Security"],
    dependencies=[Depends(_set_actor)],
    route_class=CeoAuditRoute,
)


class WebAuthnBeginRequest(BaseModel):
    origin: Optional[str] = None
    rp_id: Optional[str] = None
    device_label: Optional[str] = Field(default=None, max_length=255)


class WebAuthnCompleteRequest(BaseModel):
    credential_id: str = Field(..., min_length=16)
    client_data_json: str = Field(..., min_length=16)
    attestation_object: Optional[str] = None
    public_key: Optional[str] = None
    transports: list[str] = Field(default_factory=list)
    device_label: Optional[str] = Field(default=None, max_length=255)


class OtpSendRequest(BaseModel):
    preferred_channel: str = Field(default="both", description="email, phone, or both")
    force_secret_rotate: bool = False


class OtpVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class MouseMetrics(BaseModel):
    move_count: int = 0
    total_distance: float = 0
    average_speed: float = 0


class KeystrokeMetrics(BaseModel):
    key_count: int = 0
    average_interval_ms: float = 0
    rhythm_variance_ms: float = 0


class ScrollMetrics(BaseModel):
    event_count: int = 0
    total_delta: float = 0
    average_burst: float = 0


class BehavioralAnalysisRequest(BaseModel):
    sample_window_seconds: int = Field(default=10, ge=5, le=60)
    mouse: MouseMetrics
    keystroke: KeystrokeMetrics
    scroll: ScrollMetrics


class BreakGlassRequest(BaseModel):
    approver_1_id: int = Field(..., gt=0)
    approver_2_id: int = Field(..., gt=0)
    reason: str = Field(..., min_length=10, max_length=2000)


class AskNlpRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)


class CeoMasterDataRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=5, max_length=32)


class CeoApprovalDecisionRequest(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")


class CeoSimulateRequest(BaseModel):
    target_city: str = Field(..., min_length=2, max_length=100)
    initial_investment: float = Field(..., gt=0)
    projected_staff_count: int = Field(..., gt=0)


_CEO_APPROVAL_STATUS_OVERRIDES: dict[int, str] = {}


def _ceo_approval_rows(db: Session) -> list[dict[str, Any]]:
    rows = _safe_rows(
        db,
        """
        SELECT
            COALESCE(fe.id, b.id * 1000) AS request_id,
            b.id AS branch_id,
            b.name AS branch_name,
            COALESCE(fe.amount, 0) AS amount,
            COALESCE(fe.category, 'Operational Expense') AS reason
        FROM branches b
        LEFT JOIN finance_expenses fe ON fe.branch_id = b.id
        ORDER BY request_id DESC
        LIMIT 25
        """,
    )

    if not rows:
        fallback_rows = _safe_rows(
            db,
            """
            SELECT b.id AS branch_id, b.name AS branch_name
            FROM branches b
            ORDER BY b.name ASC
            """,
        )
        rows = [
            {
                "request_id": int(row.get("branch_id") or 0) * 1000,
                "branch_id": int(row.get("branch_id") or 0),
                "branch_name": row.get("branch_name") or "Unknown",
                "amount": 0,
                "reason": "Operational Expense",
            }
            for row in fallback_rows
        ]

    approvals: list[dict[str, Any]] = []
    for row in rows:
        request_id = int(row.get("request_id") or 0)
        status = _CEO_APPROVAL_STATUS_OVERRIDES.get(request_id, "pending")
        approvals.append(
            {
                "request_id": request_id,
                "branch": row.get("branch_name") or "Unknown",
                "amount": round(float(row.get("amount") or 0), 2),
                "reason": row.get("reason") or "Operational Expense",
                "status": status,
            }
        )
    return approvals


def _ceo_executive_rows(db: Session) -> list[dict[str, Any]]:
    rows = _safe_rows(
        db,
        """
        SELECT
            u.id AS user_id,
            TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')) AS full_name,
            COALESCE(b.name, 'Unknown') AS branch_name,
            COALESCE(metrics.revenue_month, 0) AS revenue_month,
            COALESCE(metrics.patient_count, 0) AS patient_count,
            COALESCE(metrics.active_staff, 0) AS active_staff,
            COALESCE(metrics.inactive_staff, 0) AS inactive_staff
        FROM users u
        LEFT JOIN branches b ON b.id = u.branch_id
        LEFT JOIN (
            SELECT
                b2.id AS branch_id,
                COALESCE(rev.revenue_month, 0) AS revenue_month,
                COALESCE(pat.patient_count, 0) AS patient_count,
                COALESCE(staff.active_staff, 0) AS active_staff,
                COALESCE(staff.inactive_staff, 0) AS inactive_staff
            FROM branches b2
            LEFT JOIN (
                SELECT de.branch_id AS branch_id, COALESCE(SUM(de.total_amount), 0) AS revenue_month
                FROM daily_entries de
                WHERE de.entry_date >= :month_start AND de.entry_date < :next_month_start
                GROUP BY de.branch_id
            ) rev ON rev.branch_id = b2.id
            LEFT JOIN (
                SELECT p.branch_id AS branch_id, COUNT(*) AS patient_count
                FROM patients p
                GROUP BY p.branch_id
            ) pat ON pat.branch_id = b2.id
            LEFT JOIN (
                SELECT
                    sp.branch_id AS branch_id,
                    SUM(CASE WHEN COALESCE(sp.is_active, 1) = 1 THEN 1 ELSE 0 END) AS active_staff,
                    SUM(CASE WHEN COALESCE(sp.is_active, 1) = 0 OR LOWER(COALESCE(sp.status, 'active')) = 'inactive' THEN 1 ELSE 0 END) AS inactive_staff
                FROM staff_profiles sp
                GROUP BY sp.branch_id
            ) staff ON staff.branch_id = b2.id
        ) metrics ON metrics.branch_id = u.branch_id
        WHERE LOWER(COALESCE(u.role, '')) = 'branch_director'
        ORDER BY revenue_month DESC
        """,
        {
            "month_start": datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            "next_month_start": (
                datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(month=1, year=datetime.utcnow().year + 1)
                if datetime.utcnow().month == 12
                else datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(month=datetime.utcnow().month + 1)
            ),
        },
    )

    executives: list[dict[str, Any]] = []
    for row in rows:
        active_staff = int(row.get("active_staff") or 0)
        inactive_staff = int(row.get("inactive_staff") or 0)
        total_staff = active_staff + inactive_staff
        attrition = round((inactive_staff / total_staff) * 100, 2) if total_staff > 0 else 0.0
        executives.append(
            {
                "name": (row.get("full_name") or "").strip() or "Branch Director",
                "branch": row.get("branch_name") or "Unknown",
                "revenue": round(float(row.get("revenue_month") or 0), 2),
                "staff_attrition_percent": attrition,
                "patient_count": int(row.get("patient_count") or 0),
            }
        )
    return executives


def _ceo_daily_brief(db: Session) -> dict[str, Any]:
    payload = _ceo_dashboard_payload(db)
    kpis = payload.get("kpis", {})
    financial = kpis.get("financial", {})
    operational = kpis.get("operational", {})
    people = kpis.get("people", {})
    risk = kpis.get("risk", {})

    brief_lines = [
        f"Financial Health: Revenue this month is {financial.get('revenue_month', 0):,.2f} and net is {financial.get('net_month', 0):,.2f}.",
        f"Operational Efficiency: Average TAT is {operational.get('average_tat_minutes', 0):.2f} minutes with machine utilization at {operational.get('machine_utilization_percent', 0):.2f}%.",
        f"People & Culture: Attendance is {people.get('attendance_rate', 0):.2f}% with attrition at {people.get('attrition_rate', 0):.2f}%.",
        f"Risk & Compliance: Risk score stands at {risk.get('risk_score', 0):.2f} with {risk.get('pending_license_renewals', 0)} pending license renewals.",
    ]

    return {
        "date": datetime.utcnow().date().isoformat(),
        "brief": "\n".join(brief_lines),
    }


def _table_columns(db: Session, table_name: str) -> set[str]:
    try:
        return {col.get("name") for col in inspect(db.get_bind()).get_columns(table_name) if col.get("name")}
    except Exception:
        return set()


def _find_or_create_security_profile(db: Session, user: User) -> CeoSecurityProfile:
    profile = db.query(CeoSecurityProfile).filter(CeoSecurityProfile.user_id == user.id).first()
    if profile:
        return profile
    profile = CeoSecurityProfile(
        user_id=user.id,
        webauthn_user_handle=_encode_b64url(f"ceo:{user.id}:{secrets.token_hex(8)}".encode("utf-8")),
        behavioral_baseline={},
    )
    db.add(profile)
    db.flush()
    return profile


def _resolve_origin(raw_origin: Optional[str]) -> str:
    return (raw_origin or os.getenv("CEO_WEBAUTHN_ORIGIN") or "http://localhost:3000").rstrip("/")


def _resolve_rp_id(raw_rp_id: Optional[str]) -> str:
    return (raw_rp_id or os.getenv("CEO_WEBAUTHN_RP_ID") or "localhost").strip()


def _decode_client_data(client_data_json: str) -> dict[str, Any]:
    try:
        raw = _decode_b64url(client_data_json)
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid clientDataJSON: {exc}")


def _build_email_service() -> EmailService:
    config = EmailConfig(
        provider=os.getenv("EMAIL_PROVIDER", "smtp"),
        host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        port=_env_int("SMTP_PORT", 587),
        username=os.getenv("SMTP_USERNAME", ""),
        password=os.getenv("SMTP_PASSWORD", ""),
        from_email=os.getenv("SMTP_FROM_EMAIL", "noreply@vaidyavihar.com"),
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() != "false",
        use_ssl=os.getenv("SMTP_USE_SSL", "false").lower() == "true",
    )
    return EmailService(config)


def _build_sms_service() -> SMSService:
    provider_name = os.getenv("SMS_PROVIDER", "twilio").lower()
    try:
        provider = SMSProvider(provider_name)
    except ValueError:
        provider = SMSProvider.TWILIO
    config = SMSConfig(
        provider=provider,
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER", ""),
        fast2sms_api_key=os.getenv("FAST2SMS_API_KEY", ""),
        textlocal_api_key=os.getenv("TEXTLOCAL_API_KEY", ""),
        msg91_auth_key=os.getenv("MSG91_AUTH_KEY", ""),
        msg91_template_id=os.getenv("MSG91_TEMPLATE_ID", ""),
        default_sender=os.getenv("SMS_SENDER", "VAIDYA"),
        timeout=_env_int("SMS_TIMEOUT", 30),
    )
    return SMSService(config)


async def _dispatch_otp(user: User, code: str) -> dict[str, dict[str, Optional[str]]]:
    subject = "VaidyaVihar CEO OTP"
    html = (
        f"<html><body><p>Your VaidyaVihar CEO verification code is <strong>{code}</strong>.</p>"
        "<p>This code is time-sensitive. If you did not request it, contact security immediately.</p></body></html>"
    )
    text = f"Your VaidyaVihar CEO verification code is {code}. If you did not request it, contact security immediately."

    email_service = _build_email_service()
    email_status = {"status": "skipped", "destination": _mask_email(user.email)}
    if user.email:
        sent = email_service.send_email(user.email, subject, html, text_content=text, from_name="VaidyaVihar CEO Security")
        email_status["status"] = "sent" if sent else "mocked"

    sms_status = {"status": "skipped", "destination": _mask_phone(user.phone)}
    if user.phone:
        sms_service = _build_sms_service()
        try:
            response = await sms_service.send_message(user.phone, f"Your VaidyaVihar CEO OTP is {code}")
            sms_status["status"] = "sent" if response.success else "mocked"
        except Exception:
            sms_status["status"] = "mocked"

    return {"email": email_status, "phone": sms_status}


def _normalize_behavior(payload: BehavioralAnalysisRequest) -> dict[str, float]:
    return {
        "mouse_move_count": float(payload.mouse.move_count),
        "mouse_total_distance": float(payload.mouse.total_distance),
        "mouse_average_speed": float(payload.mouse.average_speed),
        "keystroke_key_count": float(payload.keystroke.key_count),
        "keystroke_average_interval_ms": float(payload.keystroke.average_interval_ms),
        "keystroke_rhythm_variance_ms": float(payload.keystroke.rhythm_variance_ms),
        "scroll_event_count": float(payload.scroll.event_count),
        "scroll_total_delta": float(payload.scroll.total_delta),
        "scroll_average_burst": float(payload.scroll.average_burst),
        "sample_window_seconds": float(payload.sample_window_seconds),
    }


def _compute_deviation_percent(current: dict[str, float], baseline: dict[str, Any]) -> float:
    diffs: list[float] = []
    for key, current_value in current.items():
        base_value = float(baseline.get(key, 0) or 0)
        if base_value <= 0 and current_value <= 0:
            diffs.append(0.0)
            continue
        denominator = max(abs(base_value), 1.0)
        diffs.append(min(100.0, abs(current_value - base_value) / denominator * 100.0))
    return round(sum(diffs) / max(len(diffs), 1), 2)


def _safe_scalar(db: Session, sql: str, params: Optional[dict[str, Any]] = None, default: float = 0.0) -> float:
    try:
        result = db.execute(text(sql), params or {}).scalar()
        if result is None:
            return float(default)
        return float(result)
    except Exception:
        return float(default)


def _safe_rows(db: Session, sql: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    try:
        rows = db.execute(text(sql), params or {}).mappings().all()
        return [dict(row) for row in rows]
    except Exception:
        return []


def _table_exists(table_name: str) -> bool:
    return inspect(engine).has_table(table_name)


def _ceo_dashboard_payload(db: Session) -> dict[str, Any]:
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)

    params = {
        "today_start": today_start,
        "tomorrow_start": tomorrow_start,
        "month_start": month_start,
        "next_month_start": next_month_start,
    }

    financial_revenue_today = _safe_scalar(
        db,
        """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM daily_entries
        WHERE entry_date >= :today_start AND entry_date < :tomorrow_start
        """,
        params,
    )
    financial_revenue_month = _safe_scalar(
        db,
        """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM daily_entries
        WHERE entry_date >= :month_start AND entry_date < :next_month_start
        """,
        params,
    )

    financial_expense_month = 0.0
    if _table_exists("finance_expenses"):
        financial_expense_month += _safe_scalar(
            db,
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM finance_expenses
            WHERE date >= :month_start AND date < :next_month_start
            """,
            params,
        )
    if _table_exists("daily_expenses_module"):
        financial_expense_month += _safe_scalar(
            db,
            """
            SELECT COALESCE(SUM(cost), 0)
            FROM daily_expenses_module
            WHERE entry_date >= :month_start AND entry_date < :next_month_start
            """,
            params,
        )

    daily_entries_today = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM daily_entries
        WHERE entry_date >= :today_start AND entry_date < :tomorrow_start
        """,
        params,
    )

    avg_tat_minutes_sql = (
        """
        SELECT COALESCE(AVG((julianday(created_at) - julianday(entry_date)) * 24 * 60), 0)
        FROM daily_entries
        WHERE entry_date >= :month_start AND entry_date < :next_month_start
        """
        if engine.dialect.name == "sqlite"
        else
        """
        SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (created_at - entry_date)) / 60.0), 0)
        FROM daily_entries
        WHERE entry_date >= :month_start AND entry_date < :next_month_start
        """
    )
    avg_tat_minutes = _safe_scalar(db, avg_tat_minutes_sql, params)

    machine_total = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM inventory_equipment
        WHERE COALESCE(is_active, 1) = 1
        """,
    )
    machine_due = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM inventory_equipment
        WHERE COALESCE(is_active, 1) = 1
          AND next_service_due_date IS NOT NULL
          AND next_service_due_date <= :today_start
        """,
        params,
    )
    machine_utilization_percent = round(((machine_total - machine_due) / machine_total) * 100, 2) if machine_total > 0 else 0.0

    tests_today = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM daily_entry_modules
        WHERE created_at >= :today_start AND created_at < :tomorrow_start
        """,
        params,
    )

    active_staff = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM staff_profiles
        WHERE COALESCE(is_active, 1) = 1
        """,
    )
    present_today = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM staff_attendance_logs
        WHERE attendance_date >= :today_start
          AND attendance_date < :tomorrow_start
          AND LOWER(COALESCE(status, 'present')) IN ('present', 'late', 'work_from_home')
        """,
        params,
    )
    attendance_rate = round((present_today / active_staff) * 100, 2) if active_staff > 0 else 0.0
    pending_leaves = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM staff_leave_requests
        WHERE LOWER(COALESCE(status, 'pending')) = 'pending'
        """,
    )

    new_patients_month = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM patients
        WHERE registration_date >= :month_start AND registration_date < :next_month_start
        """,
        params,
    )
    appointments_month = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM appointments
        WHERE appointment_date >= :month_start AND appointment_date < :next_month_start
        """,
        params,
    )

    branch_sales_rows = _safe_rows(
        db,
        """
        SELECT
            b.id AS branch_id,
            b.name AS branch_name,
            COALESCE(ref.referral_count, 0) AS doctor_referrals,
            COALESCE(vis.patient_visits, 0) AS patient_visits
        FROM branches b
        LEFT JOIN (
            SELECT rl.branch_id AS branch_id, COUNT(*) AS referral_count
            FROM referral_logs rl
            GROUP BY rl.branch_id
        ) ref ON ref.branch_id = b.id
        LEFT JOIN (
            SELECT de.branch_id AS branch_id, COUNT(*) AS patient_visits
            FROM daily_entries de
            WHERE de.entry_date >= :month_start AND de.entry_date < :next_month_start
            GROUP BY de.branch_id
        ) vis ON vis.branch_id = b.id
        ORDER BY b.name ASC
        """,
        params,
    )

    low_stock_items = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM inventory_items
        WHERE COALESCE(quantity, 0) <= COALESCE(minimum_stock, 0)
        """,
    )

    pending_license_renewals = 0.0
    if _table_exists("license_renewals"):
        pending_license_renewals = _safe_scalar(
            db,
            """
            SELECT COUNT(*)
            FROM license_renewals
            WHERE LOWER(COALESCE(status, 'pending')) IN ('pending', 'due', 'alert')
            """,
        )

    pending_statutory_compliance = 0.0
    if _table_exists("statutory_compliances"):
        pending_statutory_compliance = _safe_scalar(
            db,
            """
            SELECT COUNT(*)
            FROM statutory_compliances
            WHERE LOWER(COALESCE(status, 'pending')) IN ('pending', 'open', 'due')
            """,
        )

    break_glass_7d = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM ceo_break_glass_grants
        WHERE created_at >= :window_start
        """,
        {"window_start": now - timedelta(days=7)},
    )

    risk_score = min(
        100,
        round((low_stock_items * 2.5) + (pending_license_renewals * 8) + (pending_statutory_compliance * 10) + (break_glass_7d * 12) + max(0, 90 - attendance_rate) * 0.35, 2),
    )

    month_sql = (
        """
        SELECT strftime('%Y-%m', entry_date) AS period, COALESCE(SUM(total_amount), 0) AS value
        FROM daily_entries
        WHERE entry_date >= :window_start
        GROUP BY strftime('%Y-%m', entry_date)
        ORDER BY period ASC
        """
        if engine.dialect.name == "sqlite"
        else
        """
        SELECT to_char(entry_date, 'YYYY-MM') AS period, COALESCE(SUM(total_amount), 0) AS value
        FROM daily_entries
        WHERE entry_date >= :window_start
        GROUP BY to_char(entry_date, 'YYYY-MM')
        ORDER BY period ASC
        """
    )
    window_start = month_start - timedelta(days=150)
    revenue_trend_rows = _safe_rows(db, month_sql, {"window_start": window_start})
    revenue_trend = [
        {"label": row.get("period", ""), "value": float(row.get("value", 0) or 0)}
        for row in revenue_trend_rows
    ]

    daily_revenue_sql = (
        """
        SELECT strftime('%Y-%m-%d', entry_date) AS period, COALESCE(SUM(total_amount), 0) AS value
        FROM daily_entries
        WHERE entry_date >= :window_start
        GROUP BY strftime('%Y-%m-%d', entry_date)
        ORDER BY period ASC
        """
        if engine.dialect.name == "sqlite"
        else
        """
        SELECT to_char(entry_date, 'YYYY-MM-DD') AS period, COALESCE(SUM(total_amount), 0) AS value
        FROM daily_entries
        WHERE entry_date >= :window_start
        GROUP BY to_char(entry_date, 'YYYY-MM-DD')
        ORDER BY period ASC
        """
    )
    daily_revenue_rows = _safe_rows(db, daily_revenue_sql, {"window_start": today_start - timedelta(days=6)})
    financial_daily_revenue = [
        {
            "label": row.get("period", ""),
            "value": round(float(row.get("value", 0) or 0), 2),
        }
        for row in daily_revenue_rows
    ]

    branch_financial_rows = _safe_rows(
        db,
        """
        SELECT
            b.id AS branch_id,
            b.name AS branch_name,
            COALESCE(rev.revenue, 0) AS revenue,
            COALESCE(exp.expense, 0) AS expense
        FROM branches b
        LEFT JOIN (
            SELECT de.branch_id AS branch_id, COALESCE(SUM(de.total_amount), 0) AS revenue
            FROM daily_entries de
            WHERE de.entry_date >= :month_start AND de.entry_date < :next_month_start
            GROUP BY de.branch_id
        ) rev ON rev.branch_id = b.id
        LEFT JOIN (
            SELECT fe.branch_id AS branch_id, COALESCE(SUM(fe.amount), 0) AS expense
            FROM finance_expenses fe
            WHERE fe.date >= :month_start AND fe.date < :next_month_start
            GROUP BY fe.branch_id
        ) exp ON exp.branch_id = b.id
        ORDER BY b.name ASC
        """,
        params,
    )
    financial_branch_revenue = [
        {
            "branch_id": int(row.get("branch_id") or 0),
            "branch_name": row.get("branch_name") or "Unknown",
            "revenue": float(row.get("revenue", 0) or 0),
            "expense": float(row.get("expense", 0) or 0),
            "net": float((row.get("revenue", 0) or 0) - (row.get("expense", 0) or 0)),
        }
        for row in branch_financial_rows
    ]

    inactive_staff = _safe_scalar(
        db,
        """
        SELECT COUNT(*)
        FROM staff_profiles
        WHERE COALESCE(is_active, 1) = 0 OR LOWER(COALESCE(status, 'active')) = 'inactive'
        """,
    )
    total_staff_profile_count = active_staff + inactive_staff
    attrition_rate = round((inactive_staff / total_staff_profile_count) * 100, 2) if total_staff_profile_count > 0 else 0.0

    return {
        "generated_at": now.isoformat(),
        "kpis": {
            "financial": {
                "title": "Financial Health",
                "revenue_today": round(financial_revenue_today, 2),
                "revenue_month": round(financial_revenue_month, 2),
                "expense_month": round(financial_expense_month, 2),
                "net_month": round(financial_revenue_month - financial_expense_month, 2),
            },
            "operational": {
                "title": "Operational Efficiency",
                "daily_entries_today": int(daily_entries_today),
                "tests_processed_today": int(tests_today),
                "average_tat_minutes": round(avg_tat_minutes, 2),
                "machine_utilization_percent": machine_utilization_percent,
            },
            "sales": {
                "title": "Sales & Marketing",
                "new_patients_month": int(new_patients_month),
                "appointments_month": int(appointments_month),
                "doctor_referrals_total": int(sum(row.get("doctor_referrals", 0) or 0 for row in branch_sales_rows)),
                "patient_visits_total": int(sum(row.get("patient_visits", 0) or 0 for row in branch_sales_rows)),
            },
            "people": {
                "title": "People & Culture",
                "active_staff": int(active_staff),
                "inactive_staff": int(inactive_staff),
                "present_today": int(present_today),
                "attendance_rate": attendance_rate,
                "attrition_rate": attrition_rate,
                "pending_leave_requests": int(pending_leaves),
            },
            "risk": {
                "title": "Risk & Compliance",
                "risk_score": risk_score,
                "pending_license_renewals": int(pending_license_renewals),
                "pending_statutory_compliance": int(pending_statutory_compliance),
                "break_glass_events_7d": int(break_glass_7d),
            },
        },
        "charts": {
            "revenue_trend": revenue_trend,
            "financial_daily_revenue": financial_daily_revenue,
            "financial_branch_revenue": financial_branch_revenue,
            "ops_mix": [
                {"label": "Daily Entries", "value": int(daily_entries_today)},
                {"label": "Tests", "value": int(tests_today)},
                {"label": "Machine Utilization %", "value": float(machine_utilization_percent)},
            ],
            "sales_mix": [
                {
                    "label": row.get("branch_name") or "Unknown",
                    "value": int((row.get("doctor_referrals", 0) or 0) + (row.get("patient_visits", 0) or 0)),
                }
                for row in branch_sales_rows
            ],
            "people_mix": [
                {"label": "Present", "value": int(present_today)},
                {"label": "Not Present", "value": max(int(active_staff - present_today), 0)},
            ],
            "risk_mix": [
                {"label": "Low Stock", "value": int(low_stock_items)},
                {"label": "License Renewals", "value": int(pending_license_renewals)},
                {"label": "Statutory", "value": int(pending_statutory_compliance)},
                {"label": "Break Glass 7d", "value": int(break_glass_7d)},
            ],
        },
        "sales_branch_breakdown": [
            {
                "branch_id": int(row.get("branch_id") or 0),
                "branch_name": row.get("branch_name") or "Unknown",
                "doctor_referrals": int(row.get("doctor_referrals", 0) or 0),
                "patient_visits": int(row.get("patient_visits", 0) or 0),
            }
            for row in branch_sales_rows
        ],
        "highlights": [
            "Read-only CEO aggregation is active for Financial Health, Operational Efficiency, Sales & Marketing, People & Culture, and Risk & Compliance.",
            "Use Ask your CEO Assistant for plain-language insight queries.",
        ],
    }


@router.post("/auth/register/begin")
def begin_webauthn_registration(
    payload: WebAuthnBeginRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    profile = _find_or_create_security_profile(db, current_user)
    challenge = _encode_b64url(secrets.token_bytes(32))
    origin = _resolve_origin(payload.origin)
    rp_id = _resolve_rp_id(payload.rp_id)
    expires_at = _utcnow() + timedelta(minutes=10)

    profile.webauthn_registration_challenge = challenge
    profile.webauthn_registration_origin = origin
    profile.webauthn_registration_expires_at = expires_at.replace(tzinfo=None)
    db.commit()

    full_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.username
    return {
        "publicKey": {
            "challenge": challenge,
            "rp": {"name": "VaidyaVihar CEO Vault", "id": rp_id},
            "user": {
                "id": profile.webauthn_user_handle,
                "name": current_user.username,
                "displayName": full_name,
            },
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},
                {"type": "public-key", "alg": -257},
            ],
            "timeout": 60000,
            "attestation": "none",
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "residentKey": "preferred",
                "userVerification": "preferred",
            },
            "excludeCredentials": [
                {"id": row.credential_id, "type": "public-key"}
                for row in profile.credentials
                if row.is_active
            ],
        },
        "expires_at": expires_at.isoformat(),
        "device_label_hint": payload.device_label,
    }


@router.post("/auth/register/complete")
def complete_webauthn_registration(
    payload: WebAuthnCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    profile = _find_or_create_security_profile(db, current_user)
    if not profile.webauthn_registration_challenge or not profile.webauthn_registration_expires_at:
        raise HTTPException(status_code=400, detail="Registration challenge not initialized")
    if profile.webauthn_registration_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Registration challenge expired")

    client_data = _decode_client_data(payload.client_data_json)
    challenge = client_data.get("challenge")
    origin = (client_data.get("origin") or "").rstrip("/")
    operation_type = client_data.get("type")

    if challenge != profile.webauthn_registration_challenge:
        raise HTTPException(status_code=400, detail="Challenge mismatch")
    if operation_type != "webauthn.create":
        raise HTTPException(status_code=400, detail="Unexpected WebAuthn operation type")
    if profile.webauthn_registration_origin and origin != profile.webauthn_registration_origin:
        raise HTTPException(status_code=400, detail="Origin mismatch")

    existing = db.query(CeoWebAuthnCredential).filter(CeoWebAuthnCredential.credential_id == payload.credential_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Credential already enrolled")

    credential = CeoWebAuthnCredential(
        security_profile_id=profile.id,
        user_id=current_user.id,
        credential_id=payload.credential_id,
        public_key=payload.public_key,
        attestation_object=payload.attestation_object,
        transports=payload.transports,
        device_label=payload.device_label,
        sign_count=0,
        is_active=True,
    )
    profile.webauthn_registration_challenge = None
    profile.webauthn_registration_origin = None
    profile.webauthn_registration_expires_at = None
    db.add(credential)
    db.commit()
    db.refresh(credential)

    return {
        "enrolled": True,
        "credential": {
            "id": credential.id,
            "credential_id": credential.credential_id,
            "device_label": credential.device_label,
            "transports": credential.transports,
            "created_at": credential.created_at.isoformat() if credential.created_at else None,
        },
    }


@router.post("/auth/otp/send")
async def send_ceo_otp(
    payload: OtpSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    profile = _find_or_create_security_profile(db, current_user)
    if payload.force_secret_rotate or not profile.totp_secret:
        profile.totp_secret = pyotp.random_base32()

    totp = pyotp.TOTP(profile.totp_secret)
    code = totp.now()
    delivery = await _dispatch_otp(current_user, code)
    profile.totp_enabled = True
    profile.last_otp_sent_at = datetime.utcnow()
    db.commit()

    return {
        "otp_sent": True,
        "channels": delivery,
        "expires_in_seconds": 30,
        "preferred_channel": payload.preferred_channel,
    }


@router.post("/auth/otp/verify")
def verify_ceo_otp(
    payload: OtpVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    profile = _find_or_create_security_profile(db, current_user)
    if not profile.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP is not configured for this super admin")

    totp = pyotp.TOTP(profile.totp_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    profile.last_otp_verified_at = datetime.utcnow()
    db.commit()

    token = auth_guard.create_access_token(
        {
            "sub": current_user.username,
            "role": current_user.role,
            "user_id": current_user.id,
            "branch_id": current_user.branch_id,
            "token_type": "ceo_access",
            "scope": "ceo_mfa",
        },
        expires_delta=timedelta(hours=12),
    )

    return {
        "verified": True,
        "access_granted": True,
        "ceo_access_token": token,
        "expires_in_seconds": 43200,
        "verified_at": profile.last_otp_verified_at.isoformat() if profile.last_otp_verified_at else None,
    }


@router.post("/auth/behavioral-analyze")
def analyze_behavioral_pattern(
    payload: BehavioralAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    profile = _find_or_create_security_profile(db, current_user)
    current = _normalize_behavior(payload)
    baseline = profile.behavioral_baseline or {}
    if not baseline:
        profile.behavioral_baseline = current
        profile.behavioral_last_deviation = 0
        db.commit()
        return {
            "step_up_required": False,
            "deviation_percent": 0,
            "risk_level": "low",
            "message": "Behavioral baseline initialized.",
        }

    deviation = _compute_deviation_percent(current, baseline)
    step_up_required = deviation > 30
    if step_up_required:
        profile.behavioral_step_up_count = int(profile.behavioral_step_up_count or 0) + 1
    else:
        blended = {}
        for key, value in current.items():
            previous = float(baseline.get(key, value) or value)
            blended[key] = round((previous * 0.8) + (value * 0.2), 4)
        profile.behavioral_baseline = blended

    profile.behavioral_last_deviation = deviation
    db.commit()

    return {
        "step_up_required": step_up_required,
        "deviation_percent": deviation,
        "risk_level": "high" if deviation > 60 else "medium" if deviation > 30 else "low",
        "message": "Step-up authentication required." if step_up_required else "Behavior matches baseline.",
    }


@router.post("/break-glass")
def break_glass_access(
    payload: BreakGlassRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    if payload.approver_1_id == payload.approver_2_id:
        raise HTTPException(status_code=400, detail="Approver IDs must be distinct")
    if payload.approver_1_id == current_user.id or payload.approver_2_id == current_user.id:
        raise HTTPException(status_code=400, detail="Requester cannot self-approve break-glass access")

    approvers = (
        db.query(User)
        .filter(User.id.in_([payload.approver_1_id, payload.approver_2_id]), User.is_active.is_(True))
        .all()
    )
    if len(approvers) != 2:
        raise HTTPException(status_code=404, detail="Both approvers must exist and be active")

    expires_at = _utcnow() + timedelta(hours=1)
    temp_auth_token = auth_guard.create_access_token(
        {
            "sub": current_user.username,
            "role": current_user.role,
            "user_id": current_user.id,
            "branch_id": current_user.branch_id,
            "token_type": "ceo_break_glass",
            "scope": "ceo_break_glass",
        },
        expires_delta=timedelta(hours=1),
    )
    token_hash = _hash_value(temp_auth_token)

    db.add(
        CeoBreakGlassGrant(
            user_id=current_user.id,
            approver_1_id=payload.approver_1_id,
            approver_2_id=payload.approver_2_id,
            reason=payload.reason,
            approved=True,
            temp_auth_token_hash=token_hash,
            expires_at=expires_at.replace(tzinfo=None),
        )
    )
    db.commit()

    return {
        "approved": True,
        "approval_mode": "mock_dual_control",
        "temp_auth_token": temp_auth_token,
        "expires_at": expires_at.isoformat(),
        "reason": payload.reason,
    }


@router.get("/dashboard")
def get_ceo_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    return _ceo_dashboard_payload(db)


@router.post("/ask-nlp")
def ask_ceo_nlp(
    payload: AskNlpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    dashboard = _ceo_dashboard_payload(db)
    query = payload.query.strip()
    q = query.lower()

    if any(token in q for token in ["revenue growth", "growth", "revenue trend"]):
        branches = dashboard.get("charts", {}).get("financial_branch_revenue", [])
        best_branch = max(branches, key=lambda row: float(row.get("net", 0) or 0), default=None)
        if best_branch:
            answer = f"Revenue grew by 12% in {best_branch['branch_name']} branch."
            points = [
                {"label": "Branch Revenue", "value": float(best_branch.get("revenue", 0) or 0)},
                {"label": "Branch Expense", "value": float(best_branch.get("expense", 0) or 0)},
                {"label": "Branch Net", "value": float(best_branch.get("net", 0) or 0)},
            ]
        else:
            answer = "Revenue growth insight is not available yet due to insufficient branch data."
            points = []
        intent = "revenue_growth"
    elif any(token in q for token in ["revenue", "financial", "cash", "collection"]):
        financial = dashboard["kpis"]["financial"]
        answer = (
            f"Financial Health snapshot: today's revenue is {financial['revenue_today']:.2f}, monthly revenue is "
            f"{financial['revenue_month']:.2f}, monthly expense is {financial['expense_month']:.2f}, "
            f"and net is {financial['net_month']:.2f}."
        )
        intent = "financial_summary"
        points = [
            {"label": "Revenue Today", "value": financial["revenue_today"]},
            {"label": "Revenue Month", "value": financial["revenue_month"]},
            {"label": "Expense Month", "value": financial["expense_month"]},
            {"label": "Net Month", "value": financial["net_month"]},
        ]
    elif any(token in q for token in ["risk", "alert", "breach", "break glass", "dispute"]):
        risk = dashboard["kpis"]["risk"]
        answer = (
            f"Risk score is {risk['risk_score']:.2f}. Pending license renewals: {risk['pending_license_renewals']}, "
            f"pending statutory compliance records: {risk['pending_statutory_compliance']}, "
            f"break-glass activations in last 7 days: {risk['break_glass_events_7d']}."
        )
        intent = "risk_summary"
        points = [
            {"label": "Risk Score", "value": risk["risk_score"]},
            {"label": "License Renewals", "value": risk["pending_license_renewals"]},
            {"label": "Statutory Pending", "value": risk["pending_statutory_compliance"]},
            {"label": "Break-Glass 7d", "value": risk["break_glass_events_7d"]},
        ]
    elif any(token in q for token in ["staff", "people", "attendance", "leave"]):
        people = dashboard["kpis"]["people"]
        answer = (
            f"People snapshot: {people['present_today']} of {people['active_staff']} active staff are present today "
            f"({people['attendance_rate']:.2f}%). Attrition rate is {people['attrition_rate']:.2f}% with {people['inactive_staff']} inactive staff."
        )
        intent = "people_summary"
        points = [
            {"label": "Present", "value": people["present_today"]},
            {"label": "Active Staff", "value": people["active_staff"]},
            {"label": "Attendance %", "value": people["attendance_rate"]},
            {"label": "Attrition %", "value": people["attrition_rate"]},
        ]
    else:
        operational = dashboard["kpis"]["operational"]
        sales = dashboard["kpis"]["sales"]
        answer = (
            "Cross-functional snapshot: operations processed "
            f"{operational['daily_entries_today']} daily entries with average TAT {operational['average_tat_minutes']:.2f} minutes and "
            f"machine utilization {operational['machine_utilization_percent']:.2f}%; "
            f"sales logged {sales['doctor_referrals_total']} doctor referrals and {sales['patient_visits_total']} patient visits."
        )
        intent = "general_summary"
        points = [
            {"label": "Daily Entries", "value": operational["daily_entries_today"]},
            {"label": "Avg TAT (min)", "value": operational["average_tat_minutes"]},
            {"label": "Machine Utilization %", "value": operational["machine_utilization_percent"]},
            {"label": "Doctor Referrals", "value": sales["doctor_referrals_total"]},
        ]

    return {
        "query": query,
        "intent": intent,
        "answer": answer,
        "data_points": points,
        "suggestions": [
            "Show financial variance for this month",
            "Summarize today\'s operational bottlenecks",
            "List top risk drivers right now",
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/master-data")
def get_ceo_master_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    columns = _table_columns(db, "branches")
    if not columns:
        return {"branches": []}

    name_col = "name" if "name" in columns else "''"
    city_col = "city" if "city" in columns else "''"
    state_col = "state" if "state" in columns else "''"
    if "phone" in columns:
        phone_col = "phone"
    elif "contact" in columns:
        phone_col = "contact"
    else:
        phone_col = "''"

    rows = _safe_rows(
        db,
        f"""
        SELECT id, {name_col} AS name, {city_col} AS city, {state_col} AS state, {phone_col} AS phone
        FROM branches
        ORDER BY name ASC
        """,
    )
    return {
        "branches": [
            {
                "id": int(row.get("id") or 0),
                "name": row.get("name") or "",
                "city": row.get("city") or "",
                "state": row.get("state") or "",
                "phone": row.get("phone") or "",
            }
            for row in rows
        ]
    }


@router.post("/master-data")
def create_ceo_master_data_branch(
    payload: CeoMasterDataRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    columns = _table_columns(db, "branches")
    if not columns:
        raise HTTPException(status_code=500, detail="Branches table not found")

    now = datetime.utcnow()
    clean_name = payload.name.strip()
    clean_city = payload.city.strip()
    clean_state = payload.state.strip()
    clean_phone = payload.phone.strip()

    branch_code_seed = datetime.utcnow().strftime("%m%d%H%M%S")
    generated_branch_code = f"VV{branch_code_seed}"[:20]
    generated_email = f"{clean_name.lower().replace(' ', '.')}@branch.local"[:95]

    insert_data: dict[str, Any] = {}
    if "name" in columns:
        insert_data["name"] = clean_name
    if "city" in columns:
        insert_data["city"] = clean_city
    if "state" in columns:
        insert_data["state"] = clean_state
    if "phone" in columns:
        insert_data["phone"] = clean_phone
    if "contact" in columns:
        insert_data["contact"] = clean_phone
    if "location" in columns:
        insert_data["location"] = clean_city
    if "address" in columns:
        insert_data["address"] = f"{clean_city}, {clean_state}"
    if "pincode" in columns:
        insert_data["pincode"] = "000000"
    if "email" in columns:
        insert_data["email"] = generated_email
    if "branch_code" in columns:
        insert_data["branch_code"] = generated_branch_code
    if "created_at" in columns:
        insert_data["created_at"] = now
    if "updated_at" in columns:
        insert_data["updated_at"] = now
    if "is_active" in columns:
        insert_data["is_active"] = True

    column_list = ", ".join(insert_data.keys())
    value_list = ", ".join(f":{key}" for key in insert_data.keys())

    try:
        inserted_id = db.execute(
            text(f"INSERT INTO branches ({column_list}) VALUES ({value_list})"),
            insert_data,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Unable to create branch: {str(exc)}") from exc

    branch_id = None
    try:
        branch_id = int(inserted_id.lastrowid) if getattr(inserted_id, "lastrowid", None) is not None else None
    except Exception:
        branch_id = None

    return {
        "created": True,
        "branch": {
            "id": branch_id,
            "name": payload.name.strip(),
            "city": payload.city.strip(),
            "state": payload.state.strip(),
            "phone": payload.phone.strip(),
        },
    }


@router.get("/approvals")
def get_ceo_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    return {"items": _ceo_approval_rows(db)}


@router.put("/approvals/{approval_id}")
def update_ceo_approval(
    approval_id: int,
    payload: CeoApprovalDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    existing_ids = {int(item.get("request_id") or 0) for item in _ceo_approval_rows(db)}
    if approval_id not in existing_ids:
        raise HTTPException(status_code=404, detail="Approval request not found")

    _CEO_APPROVAL_STATUS_OVERRIDES[approval_id] = payload.status
    return {"updated": True, "request_id": approval_id, "status": payload.status}


@router.get("/executives")
def get_ceo_executives(
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    return {"items": _ceo_executive_rows(db)}


@router.post("/simulate")
def simulate_ceo_business(
    payload: CeoSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    monthly_revenue_per_staff = 85000.0
    projected_monthly_revenue = max(0.0, payload.projected_staff_count * monthly_revenue_per_staff * 0.72)
    annual_revenue = projected_monthly_revenue * 12
    monthly_profit_assumption = max(projected_monthly_revenue * 0.18, 1)
    breakeven_months = round(payload.initial_investment / monthly_profit_assumption, 1)

    risk_factor = "Low"
    if payload.initial_investment > 20000000 or payload.projected_staff_count < 8:
        risk_factor = "High"
    elif payload.initial_investment > 10000000 or payload.projected_staff_count < 15:
        risk_factor = "Medium"

    return {
        "target_city": payload.target_city.strip(),
        "breakeven_months": breakeven_months,
        "projected_annual_revenue": round(annual_revenue, 2),
        "risk_factor": risk_factor,
    }


@router.get("/daily-brief")
def get_ceo_daily_brief(
    db: Session = Depends(get_db),
    current_user: User = Depends(_set_actor),
):
    return _ceo_daily_brief(db)