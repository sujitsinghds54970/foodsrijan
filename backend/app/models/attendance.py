"""Tenant-scoped attendance ledger, separate from legacy HR attendance tables."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint

from app.database import Base


class ManagedAttendanceRecord(Base):
    __tablename__ = "managed_attendance_records"
    __table_args__ = (
        UniqueConstraint("staff_id", "work_date", name="uq_managed_attendance_staff_date"),
        Index("ix_managed_attendance_scope_date", "company_id", "outlet_id", "work_date"),
    )

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    outlet_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    work_date = Column(Date, nullable=False)
    shift_id = Column(Integer, ForeignKey("attendance_shifts.id"), nullable=True)
    clock_in = Column(DateTime, nullable=False)
    clock_out = Column(DateTime, nullable=True)
    in_latitude = Column(Float, nullable=False)
    in_longitude = Column(Float, nullable=False)
    out_latitude = Column(Float, nullable=True)
    out_longitude = Column(Float, nullable=True)
    device_hash = Column(String(64), nullable=False)
    flags = Column(JSON, nullable=False, default=list)
    status = Column(String(24), nullable=False, default="present")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


AttendanceRecord = ManagedAttendanceRecord


class Shift(Base):
    __tablename__ = "attendance_shifts"
    __table_args__ = (UniqueConstraint("outlet_id", "name", name="uq_attendance_shift_outlet_name"),)

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    outlet_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    name = Column(String(100), nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    grace_minutes = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class StaffShiftAssignment(Base):
    __tablename__ = "staff_shift_assignments"
    __table_args__ = (
        UniqueConstraint("staff_id", "work_date", name="uq_staff_shift_date"),
        Index("ix_staff_shift_scope_date", "company_id", "outlet_id", "work_date"),
    )

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    outlet_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("attendance_shifts.id"), nullable=False)
    work_date = Column(Date, nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ManagedLeaveRequest(Base):
    __tablename__ = "managed_leave_requests"
    __table_args__ = (Index("ix_managed_leave_scope_status", "company_id", "outlet_id", "status"),)

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    outlet_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    leave_type = Column(String(40), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


LeaveRequest = ManagedLeaveRequest


class OutletGeoFence(Base):
    __tablename__ = "outlet_geofences"
    __table_args__ = (
        UniqueConstraint("outlet_id", name="uq_outlet_geofence"),
        CheckConstraint("radius_meters > 0", name="ck_geofence_radius_positive"),
    )

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    outlet_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Float, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AttendanceCorrectionRequest(Base):
    __tablename__ = "attendance_correction_requests"
    __table_args__ = (Index("ix_attendance_correction_scope_status", "company_id", "outlet_id", "status"),)

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    outlet_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    record_id = Column(Integer, ForeignKey("managed_attendance_records.id"), nullable=False)
    requested_clock_in = Column(DateTime, nullable=True)
    requested_clock_out = Column(DateTime, nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
