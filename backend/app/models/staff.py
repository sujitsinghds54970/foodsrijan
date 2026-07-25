from enum import Enum

from app.models.hr import (
    DirectorAttendanceType,
    DirectorStaffStatus,
    LeaveStatus,
    StaffAttendanceLog,
    StaffLeaveRequest,
    StaffProfile,
    StaffSalaryDetail,
)


class StaffRole(str, Enum):
    TECHNICIAN = "technician"
    RECEPTIONIST = "receptionist"
    LAB_ASSISTANT = "lab assistant"
    RADIOLOGIST = "radiologist"


# Canonical names used by the rebuilt staff API.
StaffStatus = DirectorStaffStatus
AttendanceStatus = DirectorAttendanceType
LeaveApprovalStatus = LeaveStatus

__all__ = [
    "AttendanceStatus",
    "DirectorAttendanceType",
    "DirectorStaffStatus",
    "LeaveApprovalStatus",
    "LeaveStatus",
    "StaffRole",
    "StaffStatus",
    "StaffAttendanceLog",
    "StaffLeaveRequest",
    "StaffProfile",
    "StaffSalaryDetail",
]
