"""Managed attendance API. Legacy HR endpoints remain unchanged."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, Company, User
from app.models.attendance import (
    AttendanceCorrectionRequest, AttendanceRecord, LeaveRequest,
    OutletGeoFence, Shift, StaffShiftAssignment,
)
from app.services import attendance_service as service
from app.services.executive_metrics import ResolvedScope, envelope
from app.services.outlet_service import emit, write_audit
from app.services.staff_service import get_scoped_staff
from app.utils.auth_system import require_super_admin
from app.utils.guards import (
    CompanyCeoContext, OutletManagerContext, StaffContext,
    company_ceo_context, outlet_manager_context, staff_context,
)

router = APIRouter(tags=["Managed Attendance"])


class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float = Field(ge=0, le=10000)
    device_id: str = Field(min_length=8, max_length=256)
    mock_location: bool = False


class GeofencePayload(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_meters: float = Field(gt=0, le=5000)
    enabled: bool = True


class ShiftPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    grace_minutes: int = Field(default=0, ge=0, le=120)


class AssignmentPayload(BaseModel):
    staff_id: int
    shift_id: int
    work_date: date


class LeavePayload(BaseModel):
    start_date: date
    end_date: date
    leave_type: str = Field(min_length=2, max_length=40)
    reason: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_date < self.start_date or (self.end_date - self.start_date).days > 365:
            raise ValueError("Leave date range must be ordered and at most 366 days")
        return self


class CorrectionPayload(BaseModel):
    record_id: int
    requested_clock_in: datetime | None = None
    requested_clock_out: datetime | None = None
    reason: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def valid_times(self):
        if self.requested_clock_in is None and self.requested_clock_out is None:
            raise ValueError("At least one corrected time is required")
        if any(value.tzinfo is not None for value in (self.requested_clock_in, self.requested_clock_out) if value):
            raise ValueError("Correction timestamps must be naive UTC")
        return self


class ReviewPayload(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(min_length=3, max_length=2000)


def wrap(data: dict, company_id: int, outlet_id: int | None = None):
    return envelope(data, ResolvedScope(level="branch" if outlet_id else "company",
                    company_ids=(company_id,), company_id=company_id, branch_id=outlet_id),
                    sources=["managed_attendance_records", "managed_leave_requests"], ttl_seconds=60)


def mutate(db: Session, actor: User, request: Request, event: str, row, *, details: dict | None = None):
    write_audit(db, actor, request, event, resource_type=type(row).__tablename__, resource_id=row.id,
                company_id=row.company_id, outlet_id=row.outlet_id, changes=details or {})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Conflicting attendance operation") from exc
    emit(event, actor, company_id=row.company_id, outlet_id=row.outlet_id,
         resource_type=type(row).__tablename__, resource_id=row.id, data=details or {})


def outlet_or_404(db: Session, company_id: int, outlet_id: int) -> Branch:
    outlet = db.query(Branch).filter_by(id=outlet_id, company_id=company_id, is_deleted=False).first()
    if outlet is None:
        raise HTTPException(404, "Outlet not found")
    return outlet


def records(db: Session, company_id: int, start: date, end: date, outlet_id: int | None = None, staff_id: int | None = None):
    query = db.query(AttendanceRecord).filter(
        AttendanceRecord.company_id == company_id,
        AttendanceRecord.work_date >= start, AttendanceRecord.work_date <= end,
    )
    if outlet_id is not None:
        query = query.filter(AttendanceRecord.outlet_id == outlet_id)
    if staff_id is not None:
        query = query.filter(AttendanceRecord.staff_id == staff_id)
    return query.order_by(AttendanceRecord.work_date.desc(), AttendanceRecord.id.desc()).limit(1000).all()


def _dates(start: date, end: date):
    if end < start or (end - start).days > 366:
        raise HTTPException(422, "Date range must be ordered and at most 367 days")


@router.post("/staff/attendance/clock-in")
def clock_in(payload: Location, request: Request, ctx: StaffContext = Depends(staff_context), db: Session = Depends(get_db)):
    row = service.punch(db, ctx.user, ctx.outlet, request, kind="in", **payload.model_dump())
    return wrap({"record": service.record_dict(row)}, ctx.company_id, ctx.outlet_id)


@router.post("/staff/attendance/clock-out")
def clock_out(payload: Location, request: Request, ctx: StaffContext = Depends(staff_context), db: Session = Depends(get_db)):
    row = service.punch(db, ctx.user, ctx.outlet, request, kind="out", **payload.model_dump())
    return wrap({"record": service.record_dict(row)}, ctx.company_id, ctx.outlet_id)


@router.get("/staff/attendance")
def my_attendance(start: date, end: date, ctx: StaffContext = Depends(staff_context), db: Session = Depends(get_db)):
    _dates(start, end)
    return wrap({"records": [service.record_dict(row) for row in records(db, ctx.company_id, start, end, ctx.outlet_id, ctx.user.id)]}, ctx.company_id, ctx.outlet_id)


@router.post("/staff/attendance/corrections", status_code=201)
def request_correction(payload: CorrectionPayload, request: Request, ctx: StaffContext = Depends(staff_context), db: Session = Depends(get_db)):
    record = service.scoped_record(db, ctx.company_id, ctx.outlet_id, payload.record_id, ctx.user.id)
    start = payload.requested_clock_in or record.clock_in
    end = payload.requested_clock_out or record.clock_out
    if start > service.utc_now() or (end is not None and (end <= start or end > service.utc_now())):
        raise HTTPException(422, "Corrected timestamps must be chronological and not in the future")
    if db.query(AttendanceCorrectionRequest).filter_by(record_id=record.id, status="pending").first():
        raise HTTPException(409, "A correction is already pending")
    row = AttendanceCorrectionRequest(company_id=ctx.company_id, outlet_id=ctx.outlet_id, staff_id=ctx.user.id, **payload.model_dump())
    db.add(row)
    db.flush()
    mutate(db, ctx.user, request, "attendance.correction_requested", row)
    return wrap({"id": row.id, "status": row.status}, ctx.company_id, ctx.outlet_id)


@router.get("/staff/attendance/corrections")
def my_corrections(ctx: StaffContext = Depends(staff_context), db: Session = Depends(get_db)):
    rows = db.query(AttendanceCorrectionRequest).filter_by(company_id=ctx.company_id, outlet_id=ctx.outlet_id, staff_id=ctx.user.id).order_by(AttendanceCorrectionRequest.id.desc()).limit(100).all()
    return wrap({"corrections": [{"id": row.id, "record_id": row.record_id, "status": row.status, "reason": row.reason} for row in rows]}, ctx.company_id, ctx.outlet_id)


@router.post("/staff/attendance/leaves", status_code=201)
def request_leave(payload: LeavePayload, request: Request, ctx: StaffContext = Depends(staff_context), db: Session = Depends(get_db)):
    overlap = db.query(LeaveRequest).filter(
        LeaveRequest.staff_id == ctx.user.id, LeaveRequest.company_id == ctx.company_id,
        LeaveRequest.status.in_(("pending", "approved")),
        LeaveRequest.start_date <= payload.end_date, LeaveRequest.end_date >= payload.start_date,
    ).first()
    if overlap:
        raise HTTPException(409, "Overlapping leave request")
    row = LeaveRequest(company_id=ctx.company_id, outlet_id=ctx.outlet_id, staff_id=ctx.user.id, **payload.model_dump())
    db.add(row)
    db.flush()
    mutate(db, ctx.user, request, "attendance.leave_requested", row)
    return wrap({"id": row.id, "status": row.status}, ctx.company_id, ctx.outlet_id)


@router.get("/staff/attendance/leaves")
def my_leaves(ctx: StaffContext = Depends(staff_context), db: Session = Depends(get_db)):
    rows = db.query(LeaveRequest).filter_by(company_id=ctx.company_id, outlet_id=ctx.outlet_id, staff_id=ctx.user.id).order_by(LeaveRequest.id.desc()).limit(100).all()
    return wrap({"leaves": [leave_dict(row) for row in rows]}, ctx.company_id, ctx.outlet_id)


def leave_dict(row: LeaveRequest):
    return {"id": row.id, "staff_id": row.staff_id, "outlet_id": row.outlet_id,
            "start_date": row.start_date.isoformat(), "end_date": row.end_date.isoformat(),
            "leave_type": row.leave_type, "reason": row.reason, "status": row.status}


@router.get("/staff/attendance/shifts")
def my_shifts(start: date, end: date, ctx: StaffContext = Depends(staff_context), db: Session = Depends(get_db)):
    _dates(start, end)
    rows = db.query(StaffShiftAssignment).filter(
        StaffShiftAssignment.company_id == ctx.company_id, StaffShiftAssignment.outlet_id == ctx.outlet_id,
        StaffShiftAssignment.staff_id == ctx.user.id,
        StaffShiftAssignment.work_date.between(start, end),
    ).order_by(StaffShiftAssignment.work_date).all()
    return wrap({"assignments": [{"id": row.id, "shift_id": row.shift_id, "work_date": row.work_date.isoformat()} for row in rows]}, ctx.company_id, ctx.outlet_id)


@router.put("/manager/attendance/geofence")
def configure_geofence(payload: GeofencePayload, request: Request, ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    row = db.query(OutletGeoFence).filter_by(company_id=ctx.company_id, outlet_id=ctx.outlet_id).first()
    if row is None:
        row = OutletGeoFence(company_id=ctx.company_id, outlet_id=ctx.outlet_id)
        db.add(row)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.flush()
    mutate(db, ctx.user, request, "attendance.geofence_updated", row)
    return wrap({"geofence": {"id": row.id, **payload.model_dump()}}, ctx.company_id, ctx.outlet_id)


@router.get("/manager/attendance/geofence")
def get_geofence(ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    row = db.query(OutletGeoFence).filter_by(company_id=ctx.company_id, outlet_id=ctx.outlet_id).first()
    return wrap({"geofence": {"id": row.id, "latitude": row.latitude, "longitude": row.longitude,
                 "radius_meters": row.radius_meters, "enabled": row.enabled} if row else None}, ctx.company_id, ctx.outlet_id)


@router.post("/manager/attendance/shifts", status_code=201)
def create_shift(payload: ShiftPayload, request: Request, ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    row = Shift(company_id=ctx.company_id, outlet_id=ctx.outlet_id, **payload.model_dump())
    db.add(row)
    db.flush()
    mutate(db, ctx.user, request, "attendance.shift_created", row)
    return wrap({"shift": shift_dict(row)}, ctx.company_id, ctx.outlet_id)


def shift_dict(row: Shift):
    return {"id": row.id, "name": row.name, "start_time": row.start_time, "end_time": row.end_time,
            "grace_minutes": row.grace_minutes, "active": row.active}


@router.get("/manager/attendance/shifts")
def list_shifts(ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    rows = db.query(Shift).filter_by(company_id=ctx.company_id, outlet_id=ctx.outlet_id).order_by(Shift.id).limit(100).all()
    return wrap({"shifts": [shift_dict(row) for row in rows]}, ctx.company_id, ctx.outlet_id)


@router.post("/manager/attendance/assignments", status_code=201)
def assign_shift(payload: AssignmentPayload, request: Request, ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    get_scoped_staff(db, ctx.company_id, ctx.outlet_id, payload.staff_id)
    shift = db.query(Shift).filter_by(id=payload.shift_id, company_id=ctx.company_id, outlet_id=ctx.outlet_id, active=True).first()
    if shift is None:
        raise HTTPException(404, "Shift not found")
    if db.query(StaffShiftAssignment).filter_by(staff_id=payload.staff_id, work_date=payload.work_date).first():
        raise HTTPException(409, "Staff already assigned for this work date")
    row = StaffShiftAssignment(company_id=ctx.company_id, outlet_id=ctx.outlet_id,
                               assigned_by=ctx.user.id, **payload.model_dump())
    db.add(row)
    db.flush()
    mutate(db, ctx.user, request, "attendance.shift_assigned", row, details={"staff_id": row.staff_id})
    return wrap({"id": row.id, "shift_id": row.shift_id}, ctx.company_id, ctx.outlet_id)


@router.get("/manager/attendance")
def manager_records(start: date, end: date, staff_id: int | None = None, ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    _dates(start, end)
    return wrap({"records": [service.record_dict(row) for row in records(db, ctx.company_id, start, end, ctx.outlet_id, staff_id)]}, ctx.company_id, ctx.outlet_id)


@router.get("/manager/attendance/leaves")
def manager_leaves(status: Literal["pending", "approved", "rejected"] | None = None, ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    query = db.query(LeaveRequest).filter_by(company_id=ctx.company_id, outlet_id=ctx.outlet_id)
    if status:
        query = query.filter_by(status=status)
    return wrap({"leaves": [leave_dict(row) for row in query.order_by(LeaveRequest.id.desc()).limit(100).all()]}, ctx.company_id, ctx.outlet_id)


@router.post("/manager/attendance/leaves/{request_id}/review")
def review_leave(request_id: int, payload: ReviewPayload, request: Request, ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    row = service.scoped_request(db, LeaveRequest, ctx.company_id, ctx.outlet_id, request_id)
    if row.status != "pending":
        raise HTTPException(409, "Request already reviewed")
    row.status, row.reviewed_by, row.reviewed_at, row.review_note = payload.decision, ctx.user.id, service.utc_now(), payload.note
    mutate(db, ctx.user, request, "attendance.leave_reviewed", row, details={"status": row.status})
    return wrap({"leave": leave_dict(row)}, ctx.company_id, ctx.outlet_id)


@router.get("/manager/attendance/corrections")
def manager_corrections(status: Literal["pending", "approved", "rejected"] | None = None, ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    query = db.query(AttendanceCorrectionRequest).filter_by(company_id=ctx.company_id, outlet_id=ctx.outlet_id)
    if status:
        query = query.filter_by(status=status)
    rows = query.order_by(AttendanceCorrectionRequest.id.desc()).limit(100).all()
    return wrap({"corrections": [{"id": row.id, "record_id": row.record_id, "staff_id": row.staff_id,
                                  "status": row.status, "reason": row.reason} for row in rows]}, ctx.company_id, ctx.outlet_id)


@router.post("/manager/attendance/corrections/{request_id}/review")
def review_correction(request_id: int, payload: ReviewPayload, request: Request, ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    row = service.scoped_request(db, AttendanceCorrectionRequest, ctx.company_id, ctx.outlet_id, request_id)
    if row.status != "pending":
        raise HTTPException(409, "Request already reviewed")
    record = service.scoped_record(db, ctx.company_id, ctx.outlet_id, row.record_id, row.staff_id)
    if payload.decision == "approved":
        start = row.requested_clock_in or record.clock_in
        end = row.requested_clock_out or record.clock_out
        if start > service.utc_now() or (end is not None and (end <= start or end > service.utc_now())):
            raise HTTPException(422, "Corrected timestamps must be chronological and not in the future")
        record.clock_in, record.clock_out = start, end
        record.flags = list(dict.fromkeys([*(record.flags or []), "manager_corrected"]))
    row.status, row.reviewed_by, row.reviewed_at, row.review_note = payload.decision, ctx.user.id, service.utc_now(), payload.note
    mutate(db, ctx.user, request, "attendance.correction_reviewed", row, details={"status": row.status, "record_id": row.record_id})
    return wrap({"id": row.id, "status": row.status, "record": service.record_dict(record)}, ctx.company_id, ctx.outlet_id)


def _payroll(db: Session, company_id: int, start: date, end: date, outlet_id: int | None):
    _dates(start, end)
    query = db.query(LeaveRequest).filter(
        LeaveRequest.company_id == company_id, LeaveRequest.status == "approved",
        LeaveRequest.start_date >= start, LeaveRequest.end_date <= end,
    )
    if outlet_id is not None:
        query = query.filter(LeaveRequest.outlet_id == outlet_id)
    return service.payroll_summary(records(db, company_id, start, end, outlet_id), query.all())


@router.get("/manager/attendance/payroll")
def manager_payroll(start: date, end: date, ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    return wrap({"summary": _payroll(db, ctx.company_id, start, end, ctx.outlet_id)}, ctx.company_id, ctx.outlet_id)


@router.get("/manager/attendance/payroll/export")
def manager_payroll_export(start: date, end: date, ctx: OutletManagerContext = Depends(outlet_manager_context), db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["staff_id", "days_present", "minutes_worked", "late_days", "approved_leave_days"])
    writer.writeheader()
    writer.writerows(_payroll(db, ctx.company_id, start, end, ctx.outlet_id))
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="attendance-payroll.csv"'})


@router.get("/company-ceo/attendance")
def ceo_records(start: date, end: date, outlet_id: int | None = None, ctx: CompanyCeoContext = Depends(company_ceo_context), db: Session = Depends(get_db)):
    _dates(start, end)
    if outlet_id is not None:
        outlet_or_404(db, ctx.company_id, outlet_id)
    return wrap({"records": [service.record_dict(row) for row in records(db, ctx.company_id, start, end, outlet_id)]}, ctx.company_id, outlet_id)


@router.get("/company-ceo/attendance/payroll")
def ceo_payroll(start: date, end: date, outlet_id: int | None = None, ctx: CompanyCeoContext = Depends(company_ceo_context), db: Session = Depends(get_db)):
    if outlet_id is not None:
        outlet_or_404(db, ctx.company_id, outlet_id)
    return wrap({"summary": _payroll(db, ctx.company_id, start, end, outlet_id)}, ctx.company_id, outlet_id)


@router.get("/super-ceo/attendance")
def super_ceo_records(company_id: int, start: date, end: date, outlet_id: int | None = None,
                      _: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter_by(id=company_id, is_deleted=False).first()
    if company is None:
        raise HTTPException(404, "Company not found")
    if outlet_id is not None:
        outlet_or_404(db, company_id, outlet_id)
    _dates(start, end)
    return wrap({"records": [service.record_dict(row) for row in records(db, company_id, start, end, outlet_id)]}, company_id, outlet_id)
