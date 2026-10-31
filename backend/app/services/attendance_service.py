"""Server-authoritative, scoped attendance operations."""
from __future__ import annotations

import hashlib
import hmac
import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attendance import (
    AttendanceCorrectionRequest, AttendanceRecord, LeaveRequest,
    OutletGeoFence, Shift, StaffShiftAssignment,
)
from app.services.outlet_service import emit, write_audit
from app.utils.auth_system import SECRET_KEY


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_date(now: datetime, timezone_name: str | None) -> date:
    try:
        zone = ZoneInfo(timezone_name or "UTC")
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(422, "Outlet timezone is invalid") from exc
    return now.replace(tzinfo=timezone.utc).astimezone(zone).date()


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371000 * math.asin(min(1, math.sqrt(a)))


def device_fingerprint(staff_id: int, device_id: str) -> str:
    return hmac.new(SECRET_KEY.encode(), f"{staff_id}:{device_id}".encode(), hashlib.sha256).hexdigest()


def scoped_record(db: Session, company_id: int, outlet_id: int, record_id: int, staff_id: int | None = None) -> AttendanceRecord:
    query = db.query(AttendanceRecord).filter_by(id=record_id, company_id=company_id, outlet_id=outlet_id)
    if staff_id is not None:
        query = query.filter_by(staff_id=staff_id)
    record = query.first()
    if record is None:
        raise HTTPException(404, "Attendance record not found")
    return record


def scoped_request(db: Session, model, company_id: int, outlet_id: int, request_id: int, staff_id: int | None = None):
    query = db.query(model).filter_by(id=request_id, company_id=company_id, outlet_id=outlet_id)
    if staff_id is not None:
        query = query.filter_by(staff_id=staff_id)
    row = query.first()
    if row is None:
        raise HTTPException(404, "Request not found")
    return row


def punch(db: Session, actor, outlet, request: Request, *, kind: str, latitude: float, longitude: float,
          accuracy_meters: float, device_id: str, mock_location: bool) -> AttendanceRecord:
    now = utc_now()
    work_date = local_date(now, outlet.timezone)
    fence = db.query(OutletGeoFence).filter_by(company_id=actor.company_id, outlet_id=outlet.id, enabled=True).first()
    if fence is None:
        raise HTTPException(409, "Attendance geofence is not configured")
    distance = haversine_meters(latitude, longitude, fence.latitude, fence.longitude)
    if mock_location:
        raise HTTPException(422, "Mock locations cannot be used for attendance")
    if distance > fence.radius_meters:
        raise HTTPException(403, "Location outside outlet geofence")
    fingerprint = device_fingerprint(actor.id, device_id)
    row = db.query(AttendanceRecord).filter_by(staff_id=actor.id, work_date=work_date).first()
    flags = []
    if accuracy_meters > min(fence.radius_meters, 100):
        flags.append("low_location_accuracy")
    previous = (
        db.query(AttendanceRecord).filter(
            AttendanceRecord.staff_id == actor.id, AttendanceRecord.clock_in < now
        ).order_by(AttendanceRecord.clock_in.desc()).first()
    )
    if previous is not None and previous.clock_out is not None:
        elapsed = (now - previous.clock_out).total_seconds()
        if elapsed > 0 and haversine_meters(
            previous.out_latitude or previous.in_latitude,
            previous.out_longitude or previous.in_longitude,
            latitude, longitude,
        ) / elapsed > 83.33:
            flags.append("impossible_travel")
    if kind == "in":
        if row is not None:
            raise HTTPException(409, "Already clocked in for this work date")
        if previous is not None and previous.clock_out is None:
            raise HTTPException(409, "Previous shift has not been clocked out")
        assignment = db.query(StaffShiftAssignment).filter_by(
            staff_id=actor.id, company_id=actor.company_id, outlet_id=outlet.id, work_date=work_date
        ).first()
        shift = db.query(Shift).filter_by(id=assignment.shift_id, company_id=actor.company_id, outlet_id=outlet.id, active=True).first() if assignment else None
        if shift is not None:
            local_time = now.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(outlet.timezone or "UTC"))
            start_hour, start_minute = map(int, shift.start_time.split(":"))
            if local_time.hour * 60 + local_time.minute > start_hour * 60 + start_minute + shift.grace_minutes:
                flags.append("late")
        row = AttendanceRecord(
            company_id=actor.company_id, outlet_id=outlet.id, staff_id=actor.id,
            work_date=work_date, shift_id=shift.id if shift else None,
            clock_in=now, in_latitude=latitude, in_longitude=longitude,
            device_hash=fingerprint, flags=flags, status="late" if "late" in flags else "present",
        )
        db.add(row)
    else:
        if row is None or row.clock_out is not None:
            raise HTTPException(409, "No open attendance record for this work date")
        if row.device_hash != fingerprint:
            raise HTTPException(403, "Punch device does not match the bound device")
        row.clock_out = now
        row.out_latitude = latitude
        row.out_longitude = longitude
        row.flags = list(dict.fromkeys([*(row.flags or []), *flags]))
    db.flush()
    write_audit(db, actor, request, f"attendance.clock_{kind}", resource_type="attendance",
                resource_id=row.id, company_id=actor.company_id, outlet_id=outlet.id,
                changes={"flags": row.flags, "work_date": work_date.isoformat()})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Attendance punch conflicts with an existing record") from exc
    emit(f"attendance.clock_{kind}", actor, company_id=actor.company_id, outlet_id=outlet.id,
         resource_type="attendance", resource_id=row.id, data={"staff_id": actor.id, "flags": row.flags})
    return row


def record_dict(row: AttendanceRecord) -> dict:
    return {
        "id": row.id, "company_id": row.company_id, "outlet_id": row.outlet_id,
        "staff_id": row.staff_id, "work_date": row.work_date.isoformat(),
        "shift_id": row.shift_id, "clock_in": row.clock_in.isoformat(),
        "clock_out": row.clock_out.isoformat() if row.clock_out else None,
        "status": row.status, "flags": row.flags or [],
        "minutes_worked": max(0, int((row.clock_out - row.clock_in).total_seconds() // 60)) if row.clock_out else None,
    }


def payroll_summary(rows: list[AttendanceRecord], leaves: list[LeaveRequest]) -> list[dict]:
    staff: dict[int, dict] = {}
    for row in rows:
        result = staff.setdefault(row.staff_id, {"staff_id": row.staff_id, "days_present": 0,
                                                   "minutes_worked": 0, "late_days": 0, "approved_leave_days": 0})
        result["days_present"] += 1
        result["late_days"] += int(row.status == "late")
        if row.clock_out:
            result["minutes_worked"] += max(0, int((row.clock_out - row.clock_in).total_seconds() // 60))
    for leave in leaves:
        result = staff.setdefault(leave.staff_id, {"staff_id": leave.staff_id, "days_present": 0,
                                                     "minutes_worked": 0, "late_days": 0, "approved_leave_days": 0})
        result["approved_leave_days"] += (leave.end_date - leave.start_date).days + 1
    return sorted(staff.values(), key=lambda item: item["staff_id"])
