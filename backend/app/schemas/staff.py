from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class StaffCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    mobile: str = Field(..., min_length=6, max_length=20)
    department: Optional[str] = None
    designation: Optional[str] = None
    specialization: Optional[str] = None
    shift_timings: Optional[str] = None
    date_of_joining: Optional[datetime] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    can_access_daily_ops: bool = False
    temporary_password: Optional[str] = None


class StaffUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    role: Optional[str] = None
    specialization: Optional[str] = None
    shift_timings: Optional[str] = None
    date_of_joining: Optional[datetime] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    can_access_daily_ops: Optional[bool] = None
    status: Optional[str] = None


class StaffBulkToggleDailyOpsRequest(BaseModel):
    staff_profile_ids: List[int] = Field(..., min_length=1)
    can_access_daily_ops: bool


class StaffCredentialsUpdateRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class StaffSalaryUpdateRequest(BaseModel):
    basic: float = 0
    da: float = 0
    hra: float = 0
    shift_allowance: float = 0
    ot: float = 0
    incentives: float = 0
    lop: float = 0
    statutory_deductions: float = 0
    allowances: float = 0
    deductions: float = 0
    net_pay: Optional[float] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    upi_id: Optional[str] = None


class StaffAttendanceCreateRequest(BaseModel):
    attendance_date: date
    attendance_type: str = Field(..., pattern="^(present|absent|leave|holiday)$")
    clock_in_time: Optional[datetime] = None
    clock_out_time: Optional[datetime] = None


class StaffLeaveCreateRequest(BaseModel):
    leave_type: str = Field(..., min_length=2, max_length=50)
    start_date: date
    end_date: date
    reason: Optional[str] = None


class StaffLeaveDecisionRequest(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected|cancelled)$")
    review_comment: Optional[str] = None
