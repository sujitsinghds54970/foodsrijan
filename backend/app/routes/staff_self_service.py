from datetime import date, datetime, time
import json
import math
from pathlib import Path
import secrets
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, DailyEntry, User
from app.models.hr import (
    BranchNotification,
    BranchNotificationType,
    AttendanceDispute,
    AttendanceDisputeStatus,
    DirectorAttendanceType,
    LinkedDevice,
    LeaveStatus,
    LinkedDeviceType,
    StaffAttendanceLog,
    StaffAttendanceStatus,
    StaffLeaveRequest,
    StaffNotification,
    StaffProfile,
    StaffSalaryDetail,
    StaffSalaryRecord,
    StaffTask,
)
from app.utils.auth_system import get_current_user, is_super_ceo_user
from app.utils.attendance_utils import stamp_image_with_gps
from app.utils.file_utils import replace_file, storage_relative_path_from_public_url
from app.utils.schema_compat import ensure_branch_logo_column, ensure_staff_daily_ops_column

router = APIRouter(prefix="/staff", tags=["Staff Self Service"])

BASE_DIR = Path(__file__).resolve().parents[2]
STAFF_UPLOADS_DIR = BASE_DIR / "uploads" / "staff"
ATTENDANCE_UPLOADS_DIR = STAFF_UPLOADS_DIR / "attendance"
ATTENDANCE_ATTACHMENTS_DIR = STAFF_UPLOADS_DIR / "attendance_attachments"
LEAVE_UPLOADS_DIR = STAFF_UPLOADS_DIR / "leave_attachments"
LATE_MARK_TIME = time(9, 45)


class StaffMeUpdateRequest(BaseModel):
    mobile: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = None
    photo_url: Optional[str] = None
    address: Optional[str] = None
    department: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    upi_id: Optional[str] = None


class LeaveApplyRequest(BaseModel):
    leave_type: str = Field(..., min_length=2, max_length=50)
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None


class AttendanceClockRequest(BaseModel):
    action: str = Field(..., description="in or out")
    latitude: Optional[str] = None
    longitude: Optional[str] = None


class AttendanceLogUpdateRequest(BaseModel):
    task: Optional[str] = None
    task_status: Optional[str] = None
    staff_note: Optional[str] = None


class AttendanceDisputeCreateRequest(BaseModel):
    attendance_date: date
    reason: str = Field(..., min_length=3, max_length=1000)


class LeaveCancelRequest(BaseModel):
    status: str = Field(..., description="cancel")


class TaskStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Pending, In Progress, Completed")


class DirectorAttendanceReviewUpdateRequest(BaseModel):
    hr_remark: Optional[str] = None
    dispute_resolved: Optional[bool] = None
    staff_note: Optional[str] = None


def _normalize_role(role: Optional[str]) -> str:
    return (role or "").strip().lower()


def _is_global_executive_role(role: Optional[str]) -> bool:
    normalized = _normalize_role(role)
    return normalized in {"super_ceo", "super_admin"}


def _require_staff(current_user: User) -> None:
    normalized_role = _normalize_role(current_user.role)
    # Accept any staff-type role (not super_ceo/super_admin, branch_admin, branch_director, or doctor)
    non_staff_roles = ['branch_admin', 'branch_director', 'doctor']
    if normalized_role in non_staff_roles:
        raise HTTPException(status_code=403, detail="Only staff users can access this endpoint")


def _photo_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("/api/files/"):
        return path
    if path.startswith("/"):
        return path
    # Convert relative path to absolute URL
    clean_path = path.lstrip("/")
    return f"http://localhost:8000/api/files/{clean_path}"


def _resolve_uploaded_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return f"/api/files/{path}"


def _safe_parse_month(month_token: str) -> tuple[datetime, datetime]:
    try:
        year, month_num = [int(x) for x in month_token.split("-")]
        start = datetime(year, month_num, 1)
        end = datetime(year + 1, 1, 1) if month_num == 12 else datetime(year, month_num + 1, 1)
        return start, end
    except Exception:
        raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")


def _ensure_branch_notifications_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS branch_notifications (
                id INTEGER PRIMARY KEY,
                branch_id INTEGER NOT NULL,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                related_entity_id INTEGER,
                is_read BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_branch_notifications_branch_id ON branch_notifications(branch_id)"))


def _serialize_attendance_log(row: StaffAttendanceLog, absence_reason: Optional[str] = None) -> dict:
    status_value = (row.status.value if row.status else "present").lower()
    status_label_map = {
        "present": "Present",
        "late": "Late",
        "absent": "Absent",
        "approved_leave": "Leave",
        "work_from_home": "Leave",
    }

    lateness_minutes = 0
    if row.clock_in_time and row.clock_in_time.time() > LATE_MARK_TIME:
        late_delta = datetime.combine(row.clock_in_time.date(), row.clock_in_time.time()) - datetime.combine(
            row.clock_in_time.date(), LATE_MARK_TIME
        )
        lateness_minutes = max(int(late_delta.total_seconds() // 60), 0)

    return {
        "id": row.id,
        "date": (row.date.isoformat() if row.date else row.attendance_date.date().isoformat()),
        "attendance_date": row.attendance_date,
        "clock_in_time": row.clock_in_time,
        "clock_out_time": row.clock_out_time,
        "location_lat": row.location_lat,
        "location_lng": row.location_lng,
        "selfie_url": _resolve_uploaded_url(row.selfie_url),
        "clock_in_selfie_url": _resolve_uploaded_url(row.clock_in_photo_path),
        "clock_out_selfie_url": _resolve_uploaded_url(row.clock_out_photo_path),
        "status": status_label_map.get(status_value, status_value.title()),
        "work_mode": row.work_mode,
        "wfh_reason": row.wfh_reason,
        "task": row.task,
        "task_status": row.task_status or "Pending",
        "staff_note": row.staff_note,
        "attachments": [_resolve_uploaded_url(path) for path in _get_row_attachments(row)],
        "hr_remark": row.hr_remark,
        "dispute_resolved": bool(row.dispute_resolved),
        "is_remote": bool(row.is_remote),
        "distance_from_branch_meters": row.distance_from_branch_meters,
        "late_minutes": lateness_minutes,
        "absence_reason": absence_reason,
    }


def _get_row_attachments(row: StaffAttendanceLog) -> list[str]:
    raw = row.attachments
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        value = raw.strip()
        return [value] if value else []
    return []


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    d1 = math.radians(lat2 - lat1)
    d2 = math.radians(lon2 - lon1)
    a = math.sin(d1 / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d2 / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_m * c


def _normalize_task_status(raw: Optional[str]) -> str:
    normalized = (raw or "").strip().lower()
    mapping = {
        "pending": "Pending",
        "in progress": "In Progress",
        "in_progress": "In Progress",
        "completed": "Completed",
    }
    if normalized not in mapping:
        raise HTTPException(status_code=400, detail="task_status must be Pending, In Progress, or Completed")
    return mapping[normalized]


def _parse_staff_attendance_status(status: Optional[str]) -> StaffAttendanceStatus:
    normalized = (status or "").strip().lower()
    mapping = {
        "present": StaffAttendanceStatus.PRESENT,
        "late": StaffAttendanceStatus.LATE,
        "absent": StaffAttendanceStatus.ABSENT,
        "approvedleave": StaffAttendanceStatus.APPROVED_LEAVE,
        "approved_leave": StaffAttendanceStatus.APPROVED_LEAVE,
        "approved leave": StaffAttendanceStatus.APPROVED_LEAVE,
        "workfromhome": StaffAttendanceStatus.WORK_FROM_HOME,
        "work_from_home": StaffAttendanceStatus.WORK_FROM_HOME,
        "work from home": StaffAttendanceStatus.WORK_FROM_HOME,
    }
    if normalized not in mapping:
        raise HTTPException(status_code=400, detail="Invalid status")
    return mapping[normalized]


def _to_photo_path(photo_url: Optional[str]) -> Optional[str]:
    if not photo_url:
        return None
    raw = photo_url.strip()
    if not raw:
        return None
    if raw.startswith("/api/files/"):
        return raw.replace("/api/files/", "", 1)
    return raw


def _fetch_branch_logo_url(db: Session, branch_id: Optional[int]) -> Optional[str]:
    if not branch_id:
        return None
    ensure_branch_logo_column(db)
    logo_url = db.execute(
        text("SELECT logo_url FROM branches WHERE id = :branch_id"),
        {"branch_id": branch_id},
    ).scalar()
    normalized_logo = (logo_url or "").strip()
    if normalized_logo:
        return normalized_logo

    has_settings_table = db.execute(
        text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='system_settings' LIMIT 1")
    ).scalar()
    if not has_settings_table:
        return None

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
    if not branding_row:
        return None

    try:
        parsed = json.loads(branding_row)
    except json.JSONDecodeError:
        return None

    candidates = [
        (parsed.get("assets") or {}).get("primary_logo_url"),
        (parsed.get("branding_asset_manager") or {}).get("primary_logo_web"),
        parsed.get("logo_url"),
    ]
    for candidate in candidates:
        value = (candidate or "").strip()
        if value:
            return value
    return None


def _get_staff_context(db: Session, current_user: User):
    ensure_staff_daily_ops_column(db)
    ensure_branch_logo_column(db)
    profile = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff profile not found")

    branch = db.query(Branch).filter(Branch.id == profile.branch_id).first()
    salary = db.query(StaffSalaryDetail).filter(StaffSalaryDetail.staff_profile_id == profile.id).first()
    if not salary:
        salary = StaffSalaryDetail(staff_profile_id=profile.id)
        db.add(salary)
        db.flush()

    return profile, branch, salary


def _normalize_task_status(raw: Optional[str]) -> str:
    value = (raw or "").strip().lower()
    mapping = {
        "pending": "Pending",
        "in progress": "In Progress",
        "in_progress": "In Progress",
        "completed": "Completed",
    }
    if value not in mapping:
        raise HTTPException(status_code=400, detail="Invalid status. Allowed: Pending, In Progress, Completed")
    return mapping[value]


def _build_me_response(
    current_user: User,
    profile: StaffProfile,
    branch: Optional[Branch],
    salary: StaffSalaryDetail,
    db: Session,
):
    full_name = f"{(current_user.first_name or '').strip()} {(current_user.last_name or '').strip()}".strip()
    branch_logo = _fetch_branch_logo_url(db, profile.branch_id)
    return {
        "id": current_user.id,
        "staff_profile_id": profile.id,
        "full_name": full_name,
        "photo_url": _photo_url(profile.photo_path),
        "mobile": current_user.phone,
        "email": current_user.email,
        "address": profile.address,
        "role": current_user.role,
        "department": profile.department,
        "bank_name": salary.bank_name,
        "bank_account_number": salary.account_number,
        "ifsc_code": salary.ifsc_code,
        "upi_id": salary.upi_id,
        "branch_id": profile.branch_id,
        "can_access_daily_ops": bool(profile.can_access_daily_ops),
        "branch_name": branch.name if branch else None,
        "branch_logo_url": branch_logo,
    }


@router.get("/me")
def get_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_staff(current_user)
    profile, branch, salary = _get_staff_context(db, current_user)
    return _build_me_response(current_user, profile, branch, salary, db)


@router.put("/me")
def update_me(payload: StaffMeUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_staff(current_user)
    profile, branch, salary = _get_staff_context(db, current_user)

    if payload.email is not None and payload.email != current_user.email:
        duplicate = db.query(User).filter(User.email == payload.email, User.id != current_user.id).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="Email already exists")
        current_user.email = payload.email

    if payload.mobile is not None:
        current_user.phone = payload.mobile

    if payload.photo_url is not None:
        profile.photo_path = _to_photo_path(payload.photo_url)

    if payload.address is not None:
        profile.address = payload.address

    if payload.department is not None:
        profile.department = payload.department

    if payload.bank_name is not None:
        salary.bank_name = payload.bank_name

    if payload.bank_account_number is not None:
        salary.account_number = payload.bank_account_number

    if payload.ifsc_code is not None:
        salary.ifsc_code = payload.ifsc_code

    if payload.upi_id is not None:
        salary.upi_id = payload.upi_id

    db.commit()
    db.refresh(profile)
    db.refresh(current_user)
    db.refresh(salary)

    return {
        "message": "Profile updated successfully",
        "profile": _build_me_response(current_user, profile, branch, salary, db),
    }


@router.post("/me/photo")
def upload_me_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, branch, salary = _get_staff_context(db, current_user)

    suffix = Path(file.filename or "photo").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp are allowed")

    new_photo_url = replace_file(profile.photo_path, file, "staff")
    new_photo_path = storage_relative_path_from_public_url(new_photo_url)
    if not new_photo_path:
        raise HTTPException(status_code=500, detail="Unable to store uploaded photo")

    profile.photo_path = new_photo_path
    db.commit()

    return {
        "message": "Photo uploaded",
        "photo_url": _photo_url(profile.photo_path),
        "profile": _build_me_response(current_user, profile, branch, salary, db),
    }


@router.get("/me/attendance")
def get_my_attendance(
    month: Optional[str] = Query(default=None, description="Format: YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    target = month or datetime.utcnow().strftime("%Y-%m")
    try:
        year, month_num = [int(x) for x in target.split("-")]
        start = datetime(year, month_num, 1)
        end = datetime(year + 1, 1, 1) if month_num == 12 else datetime(year, month_num + 1, 1)
    except Exception:
        raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")

    rows = (
        db.query(StaffAttendanceLog)
        .filter(
            StaffAttendanceLog.staff_profile_id == profile.id,
            StaffAttendanceLog.attendance_date >= start,
            StaffAttendanceLog.attendance_date < end,
        )
        .order_by(StaffAttendanceLog.attendance_date.desc())
        .all()
    )

    items = [
        {
            "id": row.id,
            "attendance_date": row.attendance_date,
            "clock_in_time": row.clock_in_time,
            "clock_out_time": row.clock_out_time,
            "status": (row.attendance_type.value if row.attendance_type else "present").capitalize(),
        }
        for row in rows
    ]

    return {"month": target, "count": len(items), "items": items}


@router.get("/attendance")
def get_staff_attendance_month(
    month: Optional[str] = Query(default=None, description="Format: YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    target_month = month or datetime.utcnow().strftime("%Y-%m")
    start, end = _safe_parse_month(target_month)
    try:
        rows = (
            db.query(StaffAttendanceLog)
            .filter(
                StaffAttendanceLog.staff_profile_id == profile.id,
                or_(
                    and_(StaffAttendanceLog.date.isnot(None), StaffAttendanceLog.date >= start.date(), StaffAttendanceLog.date < end.date()),
                    and_(StaffAttendanceLog.date.is_(None), StaffAttendanceLog.attendance_date >= start, StaffAttendanceLog.attendance_date < end),
                ),
            )
            .order_by(StaffAttendanceLog.attendance_date.asc())
            .all()
        )

        leaves = (
            db.query(StaffLeaveRequest)
            .filter(
                StaffLeaveRequest.staff_profile_id == profile.id,
                StaffLeaveRequest.status == LeaveStatus.APPROVED,
                StaffLeaveRequest.end_date >= start,
                StaffLeaveRequest.start_date < end,
            )
            .all()
        )

        disputes = (
            db.query(AttendanceDispute)
            .filter(
                AttendanceDispute.staff_profile_id == profile.id,
                AttendanceDispute.attendance_date >= start.date(),
                AttendanceDispute.attendance_date < end.date(),
            )
            .all()
        )

        leave_reason_by_date: dict[str, str] = {}
        for leave in leaves:
            leave_type_label = (leave.leave_type or "Leave").title()
            cursor = leave.start_date.date()
            while cursor <= leave.end_date.date():
                if start.date() <= cursor < end.date():
                    leave_reason_by_date[cursor.isoformat()] = f"Approved {leave_type_label} leave"
                cursor = date.fromordinal(cursor.toordinal() + 1)

        dispute_reason_by_date = {item.attendance_date.isoformat(): item.reason for item in disputes}
        serialized = []
        for row in rows:
            date_key = row.date.isoformat() if row.date else row.attendance_date.date().isoformat()
            absence_reason = leave_reason_by_date.get(date_key) or dispute_reason_by_date.get(date_key)
            serialized.append(_serialize_attendance_log(row, absence_reason=absence_reason))

        return {"month": target_month, "count": len(serialized), "items": serialized}
    except Exception:
        traceback.print_exc()

        # Fallback path for legacy enum/string rows that can fail ORM enum decoding.
        attendance_rows = db.execute(
            text(
                """
                SELECT
                    id,
                    date,
                    attendance_date,
                    clock_in_time,
                    clock_out_time,
                    location_lat,
                    location_lng,
                    selfie_url,
                    clock_in_photo_path,
                    clock_out_photo_path,
                    status,
                    work_mode,
                    wfh_reason,
                    task,
                    task_status,
                    staff_note,
                    is_remote,
                    distance_from_branch_meters
                FROM staff_attendance_logs
                WHERE staff_profile_id = :staff_profile_id
                  AND (
                    (date IS NOT NULL AND date >= :start_date AND date < :end_date)
                    OR
                    (date IS NULL AND attendance_date >= :start_dt AND attendance_date < :end_dt)
                  )
                ORDER BY attendance_date ASC
                """
            ),
            {
                "staff_profile_id": profile.id,
                "start_date": start.date().isoformat(),
                "end_date": end.date().isoformat(),
                "start_dt": start.isoformat(sep=" "),
                "end_dt": end.isoformat(sep=" "),
            },
        ).mappings().all()

        leave_rows = db.execute(
            text(
                """
                SELECT leave_type, start_date, end_date
                FROM staff_leave_requests
                WHERE staff_profile_id = :staff_profile_id
                  AND lower(status) = 'approved'
                  AND end_date >= :start_dt
                  AND start_date < :end_dt
                """
            ),
            {
                "staff_profile_id": profile.id,
                "start_dt": start.isoformat(sep=" "),
                "end_dt": end.isoformat(sep=" "),
            },
        ).mappings().all()

        dispute_rows = db.execute(
            text(
                """
                SELECT attendance_date, reason
                FROM attendance_disputes
                WHERE staff_profile_id = :staff_profile_id
                  AND attendance_date >= :start_date
                  AND attendance_date < :end_date
                """
            ),
            {
                "staff_profile_id": profile.id,
                "start_date": start.date().isoformat(),
                "end_date": end.date().isoformat(),
            },
        ).mappings().all()

        def _coerce_date(value):
            if value is None:
                return None
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                token = value.split(" ", 1)[0].strip()
                try:
                    return date.fromisoformat(token)
                except ValueError:
                    return None
            if hasattr(value, "date"):
                return value.date()
            return None

        def _coerce_datetime(value):
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                token = value.strip().replace("Z", "+00:00")
                if " " in token and "T" not in token:
                    token = token.replace(" ", "T", 1)
                try:
                    return datetime.fromisoformat(token)
                except ValueError:
                    return None
            return None

        leave_reason_by_date: dict[str, str] = {}
        for leave in leave_rows:
            leave_type_label = ((leave.get("leave_type") or "Leave")).title()
            leave_start = _coerce_date(leave.get("start_date"))
            leave_end = _coerce_date(leave.get("end_date"))
            if not leave_start or not leave_end:
                continue
            cursor = leave_start
            leave_end_date = leave_end
            while cursor <= leave_end_date:
                if start.date() <= cursor < end.date():
                    leave_reason_by_date[cursor.isoformat()] = f"Approved {leave_type_label} leave"
                cursor = date.fromordinal(cursor.toordinal() + 1)

        dispute_reason_by_date: dict[str, str] = {}
        for item in dispute_rows:
            dispute_date = _coerce_date(item.get("attendance_date"))
            if dispute_date is None:
                continue
            dispute_reason_by_date[dispute_date.isoformat()] = item.get("reason")

        status_label_map = {
            "present": "Present",
            "late": "Late",
            "absent": "Absent",
            "approved_leave": "ApprovedLeave",
            "work_from_home": "WorkFromHome",
        }

        serialized = []
        for row in attendance_rows:
            attendance_date = _coerce_datetime(row.get("attendance_date"))
            date_value = _coerce_date(row.get("date"))
            if date_value is None and attendance_date is not None:
                date_value = attendance_date.date() if hasattr(attendance_date, "date") else attendance_date

            status_raw = (row.get("status") or "present")
            status_normalized = str(status_raw).strip().lower()
            if status_normalized in {"present", "late", "absent", "approved_leave", "work_from_home"}:
                status_value = status_normalized
            elif status_normalized in {"approved leave", "approvedleave"}:
                status_value = "approved_leave"
            elif status_normalized in {"work from home", "workfromhome"}:
                status_value = "work_from_home"
            else:
                status_value = "present"

            lateness_minutes = 0
            clock_in_time = _coerce_datetime(row.get("clock_in_time"))
            if clock_in_time is not None and hasattr(clock_in_time, "time") and clock_in_time.time() > LATE_MARK_TIME:
                late_delta = datetime.combine(clock_in_time.date(), clock_in_time.time()) - datetime.combine(
                    clock_in_time.date(), LATE_MARK_TIME
                )
                lateness_minutes = max(int(late_delta.total_seconds() // 60), 0)

            date_key = date_value.isoformat() if date_value is not None else None
            absence_reason = (
                leave_reason_by_date.get(date_key) if date_key is not None else None
            ) or (
                dispute_reason_by_date.get(date_key) if date_key is not None else None
            )

            serialized.append(
                {
                    "id": row.get("id"),
                    "date": date_key,
                    "attendance_date": attendance_date,
                    "clock_in_time": clock_in_time,
                    "clock_out_time": _coerce_datetime(row.get("clock_out_time")),
                    "location_lat": row.get("location_lat"),
                    "location_lng": row.get("location_lng"),
                    "selfie_url": _resolve_uploaded_url(row.get("selfie_url")),
                    "clock_in_selfie_url": _resolve_uploaded_url(row.get("clock_in_photo_path")),
                    "clock_out_selfie_url": _resolve_uploaded_url(row.get("clock_out_photo_path")),
                    "status": status_label_map.get(status_value, status_value.title()),
                    "work_mode": row.get("work_mode"),
                    "wfh_reason": row.get("wfh_reason"),
                    "task": row.get("task"),
                    "task_status": row.get("task_status") or "Pending",
                    "staff_note": row.get("staff_note"),
                    "is_remote": bool(row.get("is_remote")),
                    "distance_from_branch_meters": row.get("distance_from_branch_meters"),
                    "late_minutes": lateness_minutes,
                    "absence_reason": absence_reason,
                }
            )

        return {"month": target_month, "count": len(serialized), "items": serialized}


@router.post("/attendance/clock")
def staff_clock_attendance(
    action: str = Form(...),
    location_lat: Optional[float] = Form(default=None),
    location_lng: Optional[float] = Form(default=None),
    work_mode: Optional[str] = Form(default=None),
    wfh_reason: Optional[str] = Form(default=None),
    selfie: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    normalized_action = (action or "").strip().lower()
    if normalized_action not in {"in", "out"}:
        raise HTTPException(status_code=400, detail="action must be 'in' or 'out'")

    normalized_work_mode = (work_mode or "onsite").strip().lower()
    if normalized_work_mode not in {"onsite", "work_from_home"}:
        raise HTTPException(status_code=400, detail="work_mode must be onsite or work_from_home")
    if normalized_work_mode == "work_from_home" and not (wfh_reason or "").strip():
        raise HTTPException(status_code=400, detail="WFH reason is required when work_mode is work_from_home")

    now = datetime.utcnow()
    today = now.date()
    row = (
        db.query(StaffAttendanceLog)
        .filter(StaffAttendanceLog.staff_profile_id == profile.id, StaffAttendanceLog.date == today)
        .first()
    )

    if not row:
        row = StaffAttendanceLog(
            staff_profile_id=profile.id,
            branch_id=profile.branch_id,
            date=today,
            attendance_date=now,
            attendance_type=DirectorAttendanceType.PRESENT,
            status=StaffAttendanceStatus.PRESENT,
            work_mode="onsite",
        )
        db.add(row)
        db.flush()

    uploaded_path: Optional[str] = None
    if selfie is not None:
        suffix = Path(selfie.filename or "selfie.jpg").suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise HTTPException(status_code=400, detail="Selfie must be jpg, jpeg, png, or webp")
        ATTENDANCE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        raw_filename = f"attendance_raw_{profile.id}_{today.isoformat()}_{secrets.token_hex(6)}{suffix}"
        raw_destination = ATTENDANCE_UPLOADS_DIR / raw_filename
        with raw_destination.open("wb") as output:
            output.write(selfie.file.read())

        stamped_destination = stamp_image_with_gps(
            image_path=raw_destination,
            latitude=location_lat,
            longitude=location_lng,
            clock_time=now,
        )
        raw_destination.unlink(missing_ok=True)
        uploaded_path = f"staff/attendance/{stamped_destination.name}"

    row.location_lat = location_lat
    row.location_lng = location_lng
    row.work_mode = normalized_work_mode
    row.wfh_reason = (wfh_reason or None) if normalized_work_mode == "work_from_home" else None

    branch = db.query(Branch).filter(Branch.id == profile.branch_id).first()
    if (
        location_lat is not None
        and location_lng is not None
        and branch is not None
        and branch.latitude is not None
        and branch.longitude is not None
    ):
        distance_m = _haversine_meters(float(location_lat), float(location_lng), float(branch.latitude), float(branch.longitude))
        row.distance_from_branch_meters = distance_m
        row.is_remote = distance_m > 500.0
    elif normalized_action == "in":
        row.distance_from_branch_meters = None
        row.is_remote = False

    if normalized_action == "in":
        row.clock_in_time = now
        row.clock_in_latitude = str(location_lat) if location_lat is not None else None
        row.clock_in_longitude = str(location_lng) if location_lng is not None else None
        if uploaded_path:
            row.clock_in_photo_path = uploaded_path
            row.selfie_url = uploaded_path

        if normalized_work_mode == "work_from_home":
            row.status = StaffAttendanceStatus.WORK_FROM_HOME
            row.attendance_type = DirectorAttendanceType.PRESENT
        elif now.time() > LATE_MARK_TIME:
            row.status = StaffAttendanceStatus.LATE
            row.attendance_type = DirectorAttendanceType.PRESENT
            db.add(
                StaffNotification(
                    staff_profile_id=profile.id,
                    branch_id=profile.branch_id,
                    message=f"Late mark recorded for {today.isoformat()} at {now.strftime('%H:%M')}.",
                    link="/staff/attendance",
                )
            )
        else:
            row.status = StaffAttendanceStatus.PRESENT
            row.attendance_type = DirectorAttendanceType.PRESENT
    else:
        row.clock_out_time = now
        row.clock_out_latitude = str(location_lat) if location_lat is not None else None
        row.clock_out_longitude = str(location_lng) if location_lng is not None else None
        if uploaded_path:
            row.clock_out_photo_path = uploaded_path
            row.selfie_url = uploaded_path
        if row.status == StaffAttendanceStatus.APPROVED_LEAVE:
            row.attendance_type = DirectorAttendanceType.LEAVE

    db.commit()
    db.refresh(row)

    return {
        "message": f"Clock-{normalized_action} recorded",
        "attendance": _serialize_attendance_log(row),
    }


@router.put("/attendance/{attendance_id}")
def update_staff_attendance_log(
    attendance_id: int,
    payload: AttendanceLogUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    row = (
        db.query(StaffAttendanceLog)
        .filter(StaffAttendanceLog.id == attendance_id, StaffAttendanceLog.staff_profile_id == profile.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Attendance log not found")

    if payload.task_status is not None:
        row.task_status = _normalize_task_status(payload.task_status)
    if payload.task is not None:
        row.task = payload.task.strip()
    if payload.staff_note is not None:
        row.staff_note = payload.staff_note

    db.commit()
    db.refresh(row)
    return {"message": "Attendance updated", "attendance": _serialize_attendance_log(row)}


@router.post("/attendance/{attendance_id}/attachments")
def upload_staff_attendance_attachments(
    attendance_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    row = (
        db.query(StaffAttendanceLog)
        .filter(StaffAttendanceLog.id == attendance_id, StaffAttendanceLog.staff_profile_id == profile.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Attendance log not found")

    existing = _get_row_attachments(row)
    if len(existing) >= 6:
        raise HTTPException(status_code=400, detail="Maximum 6 attachments are allowed")

    allowed_suffixes = {".jpg", ".jpeg", ".pdf"}
    ATTENDANCE_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

    next_paths = list(existing)
    for upload in files:
        if len(next_paths) >= 6:
            break
        suffix = Path(upload.filename or "attachment").suffix.lower()
        if suffix not in allowed_suffixes:
            raise HTTPException(status_code=400, detail="Only JPG, JPEG, and PDF files are allowed")

        filename = f"attendance_attachment_{profile.id}_{attendance_id}_{secrets.token_hex(5)}{suffix}"
        destination = ATTENDANCE_ATTACHMENTS_DIR / filename
        with destination.open("wb") as output:
            output.write(upload.file.read())
        next_paths.append(f"staff/attendance_attachments/{filename}")

    row.attachments = next_paths
    db.commit()
    db.refresh(row)
    return {"message": "Attachments uploaded", "attendance": _serialize_attendance_log(row)}


@router.delete("/attendance/{attendance_id}/attachments")
def delete_staff_attendance_attachment(
    attendance_id: int,
    file_url: str = Query(..., description="Attachment URL or relative path to remove"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    row = (
        db.query(StaffAttendanceLog)
        .filter(StaffAttendanceLog.id == attendance_id, StaffAttendanceLog.staff_profile_id == profile.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Attendance log not found")

    normalized = file_url.strip()
    if normalized.startswith("/api/files/"):
        normalized = normalized.replace("/api/files/", "", 1)
    elif normalized.startswith("/"):
        normalized = normalized.lstrip("/")

    existing = _get_row_attachments(row)
    if normalized not in existing:
        raise HTTPException(status_code=404, detail="Attachment not found")

    row.attachments = [item for item in existing if item != normalized]
    physical = BASE_DIR / "uploads" / normalized
    if physical.exists() and physical.is_file():
        physical.unlink()

    db.commit()
    db.refresh(row)
    return {"message": "Attachment deleted", "attendance": _serialize_attendance_log(row)}


@router.get("/leaves")
def list_staff_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    rows = (
        db.query(StaffLeaveRequest)
        .filter(StaffLeaveRequest.staff_profile_id == profile.id)
        .order_by(StaffLeaveRequest.created_at.desc())
        .all()
    )

    return {
        "items": [
            {
                "id": row.id,
                "leave_type": row.leave_type,
                "start_date": row.start_date,
                "end_date": row.end_date,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "duration_days": float(row.duration_days or row.total_days or 0),
                "duration_hours": float(row.duration_hours or 0),
                "reason": row.reason,
                "attachments": _resolve_uploaded_url(row.attachments),
                "status": row.status.value.capitalize(),
                "approved_by": row.approved_by,
                "approval_date": row.approval_date,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@router.post("/leaves")
async def create_staff_leave(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    try:
        leave_type: Optional[str] = None
        start_date: Optional[str] = None
        end_date: Optional[str] = None
        start_time: Optional[str] = None
        end_time: Optional[str] = None
        duration_hours: float = 0.0
        reason: Optional[str] = None
        attachment: Optional[UploadFile] = None

        content_type = (request.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise HTTPException(status_code=400, detail="Invalid JSON payload for leave request")
            leave_type = str(payload.get("leave_type") or "").strip()
            start_date = str(payload.get("start_date") or "").strip()
            end_date = str(payload.get("end_date") or "").strip()
            reason = payload.get("reason")
        else:
            form_data = await request.form()
            leave_type = str(form_data.get("leave_type") or "").strip()
            start_date = str(form_data.get("start_date") or "").strip()
            end_date = str(form_data.get("end_date") or "").strip()
            start_time = str(form_data.get("start_time") or "").strip() or None
            end_time = str(form_data.get("end_time") or "").strip() or None
            reason = str(form_data.get("reason") or "").strip() or None
            raw_duration_hours = str(form_data.get("duration_hours") or "").strip()
            duration_hours = float(raw_duration_hours) if raw_duration_hours else 0.0
            attachment_candidate = form_data.get("attachment")
            if isinstance(attachment_candidate, UploadFile):
                attachment = attachment_candidate

        if not leave_type or not start_date or not end_date:
            raise HTTPException(status_code=400, detail="leave_type, start_date, and end_date are required")

        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except Exception as date_error:
            print(f"❌ [LEAVE_APPLY] Invalid date format: start_date={start_date}, end_date={end_date}, error={date_error}")
            raise HTTPException(status_code=400, detail="start_date and end_date must be valid ISO datetime values")

        if start_dt > end_dt:
            print(f"❌ [LEAVE_APPLY] Validation failed: start_date after end_date ({start_dt} > {end_dt})")
            raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

        start_time_dt = datetime.fromisoformat(start_time) if start_time else None
        end_time_dt = datetime.fromisoformat(end_time) if end_time else None
        duration_days = float((end_dt.date() - start_dt.date()).days + 1)
        normalized_leave_type = leave_type.lower()

        attachment_path: Optional[str] = None
        if attachment is not None:
            suffix = Path(attachment.filename or "attachment").suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".pdf", ".webp", ".doc", ".docx"}:
                raise HTTPException(status_code=400, detail="Attachment must be jpg, jpeg, png, webp, pdf, doc, or docx")
            LEAVE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"leave_{profile.id}_{secrets.token_hex(6)}{suffix}"
            destination = LEAVE_UPLOADS_DIR / filename
            with destination.open("wb") as output:
                output.write(attachment.file.read())
            attachment_path = f"staff/leave_attachments/{filename}"

        row = StaffLeaveRequest(
            staff_profile_id=profile.id,
            branch_id=profile.branch_id,
            leave_type=normalized_leave_type,
            start_date=start_dt,
            end_date=end_dt,
            start_time=start_time_dt,
            end_time=end_time_dt,
            total_days=duration_days,
            duration_days=duration_days,
            duration_hours=float(duration_hours or 0),
            reason=reason,
            attachments=attachment_path,
            status=LeaveStatus.PENDING,
        )
        db.add(row)
        db.flush()

        _ensure_branch_notifications_table(db)
        staff_display_name = (
            f"{(profile.user.first_name or '').strip()} {(profile.user.last_name or '').strip()}".strip()
            if profile.user
            else ""
        )
        if not staff_display_name:
            staff_display_name = profile.staff_id
        db.add(
            BranchNotification(
                branch_id=profile.branch_id,
                type=BranchNotificationType.LEAVE_REQUEST,
                title="New Leave Request",
                message=f"{staff_display_name} has applied for {normalized_leave_type.title()} leave.",
                related_entity_id=row.id,
                is_read=False,
            )
        )

        db.commit()
        db.refresh(row)

        return {
            "message": "Leave request submitted",
            "leave": {
                "id": row.id,
                "status": "Pending",
                "attachments": _resolve_uploaded_url(row.attachments),
            },
        }
    except HTTPException as http_error:
        print(f"❌ [LEAVE_APPLY] Request validation failed for user={current_user.id}: {http_error.detail}")
        raise
    except Exception as error:
        db.rollback()
        print(f"❌ [LEAVE_APPLY] Unexpected error for user={current_user.id}: {error}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to apply leave")


@router.put("/leaves/{leave_id}")
def cancel_staff_leave(
    leave_id: int,
    payload: LeaveCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    if (payload.status or "").strip().lower() != "cancel":
        raise HTTPException(status_code=400, detail="Only cancel action is allowed")

    row = (
        db.query(StaffLeaveRequest)
        .filter(StaffLeaveRequest.id == leave_id, StaffLeaveRequest.staff_profile_id == profile.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if row.status != LeaveStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending leave requests can be cancelled")

    row.status = LeaveStatus.CANCELLED
    row.reviewed_by = current_user.id
    row.reviewed_at = datetime.utcnow()
    row.review_comment = "Cancelled by staff"
    db.commit()

    return {"message": "Leave request cancelled"}


@router.get("/leaves/upcoming")
def get_upcoming_approved_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    month_end = datetime(now.year + 1, 1, 1) if now.month == 12 else datetime(now.year, now.month + 1, 1)

    rows = (
        db.query(StaffLeaveRequest)
        .filter(
            StaffLeaveRequest.staff_profile_id == profile.id,
            StaffLeaveRequest.status == LeaveStatus.APPROVED,
            StaffLeaveRequest.end_date >= now,
            StaffLeaveRequest.start_date < month_end,
            StaffLeaveRequest.end_date >= month_start,
        )
        .order_by(StaffLeaveRequest.start_date.asc())
        .all()
    )

    items = [
        {
            "id": row.id,
            "leave_type": row.leave_type,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "duration_days": float(row.duration_days or row.total_days or 0),
            "duration_hours": float(row.duration_hours or 0),
            "status": row.status.value.capitalize(),
        }
        for row in rows
    ]

    return {"items": items, "next_leave": items[0] if items else None}


@router.get("/linked-devices")
def list_linked_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    rows = (
        db.query(LinkedDevice)
        .filter(LinkedDevice.staff_profile_id == profile.id)
        .order_by(LinkedDevice.updated_at.desc())
        .all()
    )

    return {
        "items": [
            {
                "id": row.id,
                "device_id": row.device_id,
                "device_type": row.device_type.value.capitalize() if row.device_type else None,
                "is_active": row.is_active,
                "last_sync": row.last_sync,
            }
            for row in rows
        ]
    }


@router.post("/linked-devices/reset-token")
def reset_linked_device_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    active_device = (
        db.query(LinkedDevice)
        .filter(LinkedDevice.staff_profile_id == profile.id, LinkedDevice.is_active.is_(True))
        .first()
    )
    if not active_device:
        return {"message": "No active linked device found"}

    active_device.is_active = False
    active_device.last_sync = datetime.utcnow()
    db.commit()
    return {"message": "Device token reset. Please re-register your device."}


@router.post("/disputes")
def create_attendance_dispute(
    payload: AttendanceDisputeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    dispute = AttendanceDispute(
        staff_profile_id=profile.id,
        attendance_date=payload.attendance_date,
        reason=payload.reason,
        status=AttendanceDisputeStatus.OPEN,
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return {"message": "Dispute submitted", "id": dispute.id}


@router.get("/disputes")
def list_attendance_disputes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    rows = (
        db.query(AttendanceDispute)
        .filter(AttendanceDispute.staff_profile_id == profile.id)
        .order_by(AttendanceDispute.created_at.desc())
        .all()
    )

    return {
        "items": [
            {
                "id": row.id,
                "attendance_date": row.attendance_date,
                "reason": row.reason,
                "status": row.status.value.capitalize() if row.status else "Open",
                "resolution_notes": row.resolution_notes,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@router.post("/me/attendance/clock")
def clock_attendance(
    payload: AttendanceClockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    action = (payload.action or "").strip().lower()
    if action not in {"in", "out"}:
        raise HTTPException(status_code=400, detail="action must be 'in' or 'out'")

    now = datetime.utcnow()
    day_start = datetime(now.year, now.month, now.day)
    day_end = datetime(now.year, now.month, now.day, 23, 59, 59)

    record = (
        db.query(StaffAttendanceLog)
        .filter(
            StaffAttendanceLog.staff_profile_id == profile.id,
            StaffAttendanceLog.attendance_date >= day_start,
            StaffAttendanceLog.attendance_date <= day_end,
        )
        .first()
    )

    if not record:
        record = StaffAttendanceLog(
            staff_profile_id=profile.id,
            branch_id=profile.branch_id,
            attendance_date=now,
            attendance_type=DirectorAttendanceType.PRESENT,
        )
        db.add(record)
        db.flush()

    if action == "in":
        record.clock_in_time = now
        record.clock_in_latitude = payload.latitude
        record.clock_in_longitude = payload.longitude
    else:
        record.clock_out_time = now
        record.clock_out_latitude = payload.latitude
        record.clock_out_longitude = payload.longitude

    db.commit()
    db.refresh(record)

    return {
        "message": f"Clock-{action} recorded",
        "attendance": {
            "id": record.id,
            "attendance_date": record.attendance_date,
            "clock_in_time": record.clock_in_time,
            "clock_out_time": record.clock_out_time,
            "status": (record.attendance_type.value if record.attendance_type else "present").capitalize(),
        },
    }


@router.get("/me/salary")
def get_my_salary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_staff(current_user)
    profile, _, salary = _get_staff_context(db, current_user)

    records = (
        db.query(StaffSalaryRecord)
        .filter(StaffSalaryRecord.staff_profile_id == profile.id)
        .order_by(StaffSalaryRecord.year.desc(), StaffSalaryRecord.month.desc())
        .limit(24)
        .all()
    )

    items = [
        {
            "id": row.id,
            "month": row.month,
            "year": row.year,
            "basic": float(row.basic_salary or 0),
            "hra": float(row.hra or 0),
            "allowances": float(row.allowances or 0),
            "deductions": float(row.deductions or 0),
            "net_pay": float(row.net_pay or 0),
            "generated_at": row.generated_at,
        }
        for row in records
    ]

    return {
        "current": {
            "basic": float(salary.basic or 0),
            "hra": float(salary.hra or 0),
            "allowances": float(salary.allowances or 0),
            "deductions": float(salary.deductions or 0),
            "net_pay": float(salary.net_pay or 0),
            "bank_name": salary.bank_name,
            "account_number": salary.account_number,
            "ifsc_code": salary.ifsc_code,
            "upi_id": salary.upi_id,
        },
        "history": items,
    }


@router.get("/me/tasks")
def get_my_tasks(
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    query = db.query(StaffTask).filter(StaffTask.staff_profile_id == profile.id)
    if status:
        query = query.filter(StaffTask.status == _normalize_task_status(status))

    rows = query.order_by(StaffTask.deadline.asc(), StaffTask.updated_at.desc()).all()
    return {
        "items": [
            {
                "id": row.id,
                "task_name": row.task_name,
                "description": row.description,
                "deadline": row.deadline,
                "status": row.status,
                "priority": row.priority,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    }


@router.get("/{staff_profile_id}/attendance")
def director_attendance_detail_for_staff(
    staff_profile_id: int,
    month: Optional[str] = Query(default=None, description="Format: YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if _normalize_role(current_user.role) not in {"branch_director", "branch_admin", "super_admin", "super_ceo"}:
        raise HTTPException(status_code=403, detail="Access denied")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff profile not found")

    if not _is_global_executive_role(current_user.role) and current_user.branch_id != profile.branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    target_month = month or datetime.utcnow().strftime("%Y-%m")
    start, end = _safe_parse_month(target_month)

    def _status_label(row: StaffAttendanceLog) -> str:
        status_value = (getattr(row.attendance_type, "value", None) or getattr(row.status, "value", None) or "present").strip().lower()
        mapping = {
            "present": "Present",
            "late": "Late",
            "absent": "Absent",
            "leave": "Leave",
            "approved_leave": "Leave",
            "approvedleave": "Leave",
            "work_from_home": "Leave",
            "workfromhome": "Leave",
        }
        return mapping.get(status_value, status_value.title())

    rows = (
        db.query(StaffAttendanceLog)
        .filter(
            StaffAttendanceLog.staff_profile_id == profile.id,
            or_(
                and_(StaffAttendanceLog.date.isnot(None), StaffAttendanceLog.date >= start.date(), StaffAttendanceLog.date < end.date()),
                and_(StaffAttendanceLog.date.is_(None), StaffAttendanceLog.attendance_date >= start, StaffAttendanceLog.attendance_date < end),
            ),
        )
        .order_by(StaffAttendanceLog.attendance_date.asc())
        .all()
    )

    row_by_date: dict[str, StaffAttendanceLog] = {}
    for row in rows:
        key = row.date.isoformat() if row.date else row.attendance_date.date().isoformat()
        row_by_date[key] = row

    leave_by_date: dict[str, str] = {}
    leave_rows = (
        db.query(StaffLeaveRequest)
        .filter(
            StaffLeaveRequest.staff_profile_id == profile.id,
            StaffLeaveRequest.end_date >= start,
            StaffLeaveRequest.start_date < end,
        )
        .all()
    )
    for leave in leave_rows:
        cursor = leave.start_date.date()
        while cursor <= leave.end_date.date():
            if start.date() <= cursor < end.date():
                leave_by_date[cursor.isoformat()] = leave.status.value.capitalize()
            cursor = date.fromordinal(cursor.toordinal() + 1)

    items = []
    cursor = start.date()
    while cursor < end.date():
        day_key = cursor.isoformat()
        row = row_by_date.get(day_key)
        leave_status = leave_by_date.get(day_key)

        if row:
            serialized = _serialize_attendance_log(row)
            serialized["status"] = _status_label(row)
            serialized["leave_status"] = leave_status or "-"
        elif leave_status and leave_status.lower() == "approved":
            serialized = {
                "id": -int(cursor.strftime("%Y%m%d")),
                "date": day_key,
                "attendance_date": datetime.combine(cursor, time.min),
                "clock_in_time": None,
                "clock_out_time": None,
                "location_lat": None,
                "location_lng": None,
                "selfie_url": None,
                "clock_in_selfie_url": None,
                "clock_out_selfie_url": None,
                "status": "Leave",
                "work_mode": None,
                "wfh_reason": None,
                "task": None,
                "task_status": "Pending",
                "staff_note": None,
                "attachments": [],
                "hr_remark": None,
                "dispute_resolved": False,
                "is_remote": False,
                "distance_from_branch_meters": None,
                "late_minutes": 0,
                "absence_reason": "Approved leave",
                "leave_status": leave_status,
            }
        else:
            serialized = {
                "id": -int(cursor.strftime("%Y%m%d")),
                "date": day_key,
                "attendance_date": datetime.combine(cursor, time.min),
                "clock_in_time": None,
                "clock_out_time": None,
                "location_lat": None,
                "location_lng": None,
                "selfie_url": None,
                "clock_in_selfie_url": None,
                "clock_out_selfie_url": None,
                "status": "Absent",
                "work_mode": None,
                "wfh_reason": None,
                "task": None,
                "task_status": "Pending",
                "staff_note": None,
                "attachments": [],
                "hr_remark": None,
                "dispute_resolved": False,
                "is_remote": False,
                "distance_from_branch_meters": None,
                "late_minutes": 0,
                "absence_reason": None,
                "leave_status": leave_status or "-",
            }

        items.append(serialized)
        cursor = date.fromordinal(cursor.toordinal() + 1)

    return {"month": target_month, "count": len(items), "items": items}


class DirectorAttendanceTaskUpdateRequest(BaseModel):
    task: str
    task_status: Optional[str] = "Pending"


@router.put("/{staff_profile_id}/attendance/{attendance_id}/task")
def director_assign_task_to_attendance(
    staff_profile_id: int,
    attendance_id: int,
    payload: DirectorAttendanceTaskUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if _normalize_role(current_user.role) not in {"branch_director", "branch_admin", "super_admin", "super_ceo"}:
        raise HTTPException(status_code=403, detail="Access denied")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff profile not found")
    if not _is_global_executive_role(current_user.role) and current_user.branch_id != profile.branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    row = (
        db.query(StaffAttendanceLog)
        .filter(StaffAttendanceLog.id == attendance_id, StaffAttendanceLog.staff_profile_id == staff_profile_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Attendance log not found")

    row.task = payload.task.strip()
    row.task_status = _normalize_task_status(payload.task_status)
    _ensure_branch_notifications_table(db)
    staff_display_name = (
        f"{(profile.user.first_name or '').strip()} {(profile.user.last_name or '').strip()}".strip()
        if profile.user
        else ""
    )
    if not staff_display_name:
        staff_display_name = profile.staff_id
    db.add(
        BranchNotification(
            branch_id=profile.branch_id,
            type=BranchNotificationType.TASK_ASSIGNED,
            title="Task assignment confirmed",
            message=f"Task assigned to {staff_display_name}: {row.task}",
            related_entity_id=row.id,
            is_read=False,
        )
    )
    db.add(
        StaffNotification(
            staff_profile_id=staff_profile_id,
            branch_id=profile.branch_id,
            message=f"New task assigned for {row.date or row.attendance_date.date()}: {row.task}",
            link="/staff/attendance",
        )
    )
    db.commit()
    db.refresh(row)
    return {"message": "Task assigned", "attendance": _serialize_attendance_log(row)}


@router.put("/{staff_profile_id}/attendance/{attendance_id}/review")
def director_update_attendance_review(
    staff_profile_id: int,
    attendance_id: int,
    payload: DirectorAttendanceReviewUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if _normalize_role(current_user.role) not in {"branch_director", "branch_admin", "super_admin", "super_ceo"}:
        raise HTTPException(status_code=403, detail="Access denied")

    profile = db.query(StaffProfile).filter(StaffProfile.id == staff_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Staff profile not found")
    if not _is_global_executive_role(current_user.role) and current_user.branch_id != profile.branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    row = (
        db.query(StaffAttendanceLog)
        .filter(StaffAttendanceLog.id == attendance_id, StaffAttendanceLog.staff_profile_id == staff_profile_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Attendance log not found")

    if payload.hr_remark is not None:
        row.hr_remark = payload.hr_remark.strip() or None
    if payload.dispute_resolved is not None:
        row.dispute_resolved = bool(payload.dispute_resolved)
    if payload.staff_note is not None:
        row.staff_note = payload.staff_note

    db.commit()
    db.refresh(row)
    return {"message": "Attendance review updated", "attendance": _serialize_attendance_log(row)}


@router.put("/me/tasks/{task_id}/status")
def update_my_task_status(
    task_id: int,
    payload: TaskStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    task = db.query(StaffTask).filter(StaffTask.id == task_id, StaffTask.staff_profile_id == profile.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = _normalize_task_status(payload.status)
    db.commit()
    db.refresh(task)

    return {
        "message": "Task status updated",
        "task": {
            "id": task.id,
            "status": task.status,
            "updated_at": task.updated_at,
        },
    }


@router.get("/me/leave-balance")
def get_leave_balance(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    year_start = datetime(datetime.utcnow().year, 1, 1)
    year_end = datetime(datetime.utcnow().year + 1, 1, 1)
    approved = (
        db.query(StaffLeaveRequest)
        .filter(
            StaffLeaveRequest.staff_profile_id == profile.id,
            StaffLeaveRequest.status == LeaveStatus.APPROVED,
            StaffLeaveRequest.start_date >= year_start,
            StaffLeaveRequest.start_date < year_end,
        )
        .all()
    )

    used_casual = sum(x.total_days or 0 for x in approved if (x.leave_type or "").strip().lower() == "casual")
    used_sick = sum(x.total_days or 0 for x in approved if (x.leave_type or "").strip().lower() == "sick")
    used_earned = sum(x.total_days or 0 for x in approved if (x.leave_type or "").strip().lower() == "earned")

    casual_total = 12
    sick_total = 8
    earned_total = 15

    return {
        "casual_total": casual_total,
        "sick_total": sick_total,
        "earned_total": earned_total,
        "casual_remaining": max(casual_total - used_casual, 0),
        "sick_remaining": max(sick_total - used_sick, 0),
        "earned_remaining": max(earned_total - used_earned, 0),
    }


@router.post("/me/leave")
def apply_leave(payload: LeaveApplyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date")

    total_days = float((payload.end_date.date() - payload.start_date.date()).days + 1)
    entry = StaffLeaveRequest(
        staff_profile_id=profile.id,
        branch_id=profile.branch_id,
        leave_type=payload.leave_type.strip().lower(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        total_days=total_days,
        reason=payload.reason,
        status=LeaveStatus.PENDING,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {"message": "Leave request submitted", "leave_request_id": entry.id, "status": entry.status.value}


@router.get("/me/notifications")
def get_staff_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    rows = (
        db.query(StaffNotification)
        .filter(StaffNotification.staff_profile_id == profile.id)
        .order_by(StaffNotification.created_at.desc())
        .limit(50)
        .all()
    )

    items = [
        {
            "id": row.id,
            "title": "Important Notification",
            "message": row.message,
            "status": "read" if row.is_read else "unread",
            "link": row.link,
            "is_read": row.is_read,
            "created_at": row.created_at,
        }
        for row in rows
    ]

    unread_count = sum(1 for item in items if not item["is_read"])
    return {"items": items, "count": len(items), "unread_count": unread_count}


@router.post("/me/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    row = (
        db.query(StaffNotification)
        .filter(StaffNotification.id == notification_id, StaffNotification.staff_profile_id == profile.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")

    if not row.is_read:
        row.is_read = True
        db.commit()

    return {"message": "Notification marked as read"}


@router.get("/me/performance")
def get_my_performance(
    month: Optional[str] = Query(default=None, description="Format: YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    profile, _, _ = _get_staff_context(db, current_user)

    target = month or datetime.utcnow().strftime("%Y-%m")
    try:
        year, month_num = [int(x) for x in target.split("-")]
        month_start = datetime(year, month_num, 1)
        month_end = datetime(year + 1, 1, 1) if month_num == 12 else datetime(year, month_num + 1, 1)
    except Exception:
        raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")

    attendance_rows = (
        db.query(StaffAttendanceLog)
        .filter(
            StaffAttendanceLog.staff_profile_id == profile.id,
            StaffAttendanceLog.attendance_date >= month_start,
            StaffAttendanceLog.attendance_date < month_end,
        )
        .all()
    )
    present_count = sum(1 for row in attendance_rows if (row.attendance_type.value if row.attendance_type else "present") == "present")
    attendance_percentage = (present_count / len(attendance_rows) * 100.0) if attendance_rows else 0.0

    month_tasks = (
        db.query(StaffTask)
        .filter(
            StaffTask.staff_profile_id == profile.id,
            StaffTask.created_at >= month_start,
            StaffTask.created_at < month_end,
        )
        .all()
    )
    completed_tasks = sum(1 for row in month_tasks if (row.status or "").strip().lower() == "completed")

    revenue_total = (
        db.query(func.coalesce(func.sum(DailyEntry.total_amount), 0))
        .filter(
            DailyEntry.created_by == current_user.id,
            DailyEntry.entry_date >= month_start,
            DailyEntry.entry_date < month_end,
        )
        .scalar()
    )

    return {
        "month": target,
        "attendance_percentage": round(attendance_percentage, 2),
        "attendance_days": len(attendance_rows),
        "present_days": present_count,
        "tasks_completed": completed_tasks,
        "tasks_total": len(month_tasks),
        "revenue_generated": float(revenue_total or 0),
    }
