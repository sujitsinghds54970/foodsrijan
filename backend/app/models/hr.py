"""
HR/Payroll Models for VaidyaVihar Diagnostic ERP

Leave management and HR module:
- Leave types and policies
- Leave requests and approvals
- Leave balance tracking
- Staff attendance
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, DECIMAL, JSON
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum


class CompatEnum(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, enum_cls, length: int = 50):
        super().__init__()
        self.enum_cls = enum_cls
        self.impl = String(length)

    def _coerce(self, value):
        if value is None:
            return None
        if isinstance(value, self.enum_cls):
            return value

        text_value = str(value).strip()
        if not text_value:
            return None

        candidates = [text_value, text_value.lower(), text_value.upper()]
        for candidate in candidates:
            try:
                return self.enum_cls(candidate)
            except ValueError:
                pass
        for member in self.enum_cls:
            if member.name == text_value or member.name.lower() == text_value.lower():
                return member
        raise ValueError(f"Invalid value '{value}' for enum {self.enum_cls.__name__}")

    def process_bind_param(self, value, dialect):
        coerced = self._coerce(value)
        return coerced.value if coerced is not None else None

    def process_result_value(self, value, dialect):
        return self._coerce(value)


class LeaveType(str, enum.Enum):
    """Leave type enumeration"""
    CASUAL = "casual"
    SICK = "sick"
    PRIVILEGED = "privileged"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    BEREAVEMENT = "bereavement"
    UNPAID = "unpaid"
    WORK_FROM_HOME = "work_from_home"
    COMPENSATORY = "compensatory"
    OTHER = "other"


class LeaveStatus(str, enum.Enum):
    """Leave status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AttendanceStatus(str, enum.Enum):
    """Attendance status enumeration"""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    HALF_DAY = "half_day"
    LEAVE = "leave"
    HOLIDAY = "holiday"
    WEEKOFF = "weekoff"


class LeavePolicy(Base):
    """Leave policy configuration"""
    __tablename__ = "leave_policies"

    id = Column(Integer, primary_key=True, index=True)
    leave_type = Column(CompatEnum(LeaveType), nullable=False, unique=True)
    
    # Allowance
    annual_quota = Column(Integer, default=0)  # Days per year
    monthly_quota = Column(Float, default=0)  # Days per month
    max_consecutive_days = Column(Integer, default=0)
    
    # Rules
    requires_approval = Column(Boolean, default=True)
    requires_document = Column(Boolean, default=False)
    can_carry_forward = Column(Boolean, default=False)
    max_carry_forward = Column(Integer, default=0)
    carry_forward_expiry_days = Column(Integer, default=0)
    
    # Encashment
    can_encash = Column(Boolean, default=False)
    max_encash_per_year = Column(Integer, default=0)
    
    # Probation rules
    applicable_after_days = Column(Integer, default=0)  # Days after joining
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeaveBalance(Base):
    """Leave balance tracking per employee"""
    __tablename__ = "leave_balances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leave_type = Column(CompatEnum(LeaveType), nullable=False)
    
    # Balance
    total_quota = Column(Integer, default=0)
    available = Column(Integer, default=0)
    used = Column(Integer, default=0)
    pending = Column(Integer, default=0)
    carried_forward = Column(Integer, default=0)
    
    # Period
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")


class LeaveRequest(Base):
    """Leave request model"""
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leave_type = Column(CompatEnum(LeaveType), nullable=False)
    
    # Dates
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    total_days = Column(Float, default=0)
    
    # Half day options
    is_half_day = Column(Boolean, default=False)
    half_day_session = Column(String, nullable=True)  # morning, afternoon
    
    # Reason
    reason = Column(Text, nullable=True)
    emergency_contact = Column(String, nullable=True)
    
    # Document
    document_path = Column(String, nullable=True)
    
    # Status
    status = Column(CompatEnum(LeaveStatus), default=LeaveStatus.PENDING)
    
    # Approval
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Alternate arrangement
    alternate_arrangement = Column(Text, nullable=True)
    handover_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])


class Holiday(Base):
    """Company holidays"""
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    holiday_date = Column(DateTime, nullable=False)
    holiday_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Type
    is_national_holiday = Column(Boolean, default=False)
    is_optional_holiday = Column(Boolean, default=False)
    
    # Branch specific
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Recurring
    is_recurring = Column(Boolean, default=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch")


class Attendance(Base):
    """Daily attendance tracking"""
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    attendance_date = Column(DateTime, nullable=False)
    
    # Status
    status = Column(CompatEnum(AttendanceStatus), default=AttendanceStatus.ABSENT)
    
    # Check-in/Check-out
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    work_duration_hours = Column(Float, default=0)
    
    # Late arrival
    is_late = Column(Boolean, default=False)
    late_minutes = Column(Integer, default=0)
    
    # Overtime
    overtime_hours = Column(Float, default=0)
    overtime_approved = Column(Boolean, default=False)
    
    # Location (for remote/work from home)
    work_location = Column(String, nullable=True)  # office, home, field
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Approved by
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])


class AttendanceRegularization(Base):
    """Attendance correction requests"""
    __tablename__ = "attendance_regularizations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    attendance_id = Column(Integer, ForeignKey("attendances.id"), nullable=True)
    
    # Original data
    original_date = Column(DateTime, nullable=False)
    original_status = Column(String, nullable=True)
    original_check_in = Column(DateTime, nullable=True)
    original_check_out = Column(DateTime, nullable=True)
    
    # Requested data
    requested_status = Column(String, nullable=False)
    requested_check_in = Column(DateTime, nullable=True)
    requested_check_out = Column(DateTime, nullable=True)
    
    # Reason
    reason = Column(Text, nullable=True)
    
    # Status
    status = Column(CompatEnum(LeaveStatus), default=LeaveStatus.PENDING)
    
    # Approval
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    attendance = relationship("Attendance")
    approver = relationship("User", foreign_keys=[approved_by])


class WorkShift(Base):
    """Work shift configurations"""
    __tablename__ = "work_shifts"

    id = Column(Integer, primary_key=True, index=True)
    shift_name = Column(String, nullable=False)
    shift_code = Column(String, nullable=False, unique=True)
    
    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    break_start = Column(DateTime, nullable=True)
    break_end = Column(DateTime, nullable=True)
    break_duration_minutes = Column(Integer, default=0)
    
    # Working hours
    total_hours = Column(Float, default=0)
    flexible_timing = Column(Boolean, default=False)
    late_mark_threshold_minutes = Column(Integer, default=0)
    
    # Days
    working_days = Column(String, nullable=True)  # JSON array of days
    
    # Status
    is_active = Column(Boolean, default=True)
    is_night_shift = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmployeeProfile(Base):
    """Extended employee profile for HR"""
    __tablename__ = "employee_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Personal details
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String, nullable=True)
    blood_group = Column(String, nullable=True)
    marital_status = Column(String, nullable=True)
    
    # Employment details
    employee_id = Column(String, nullable=False, unique=True)
    department = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    date_of_joining = Column(DateTime, nullable=True)
    probation_end_date = Column(DateTime, nullable=True)
    confirmation_date = Column(DateTime, nullable=True)
    
    # Work details
    shift_id = Column(Integer, ForeignKey("work_shifts.id"), nullable=True)
    reporting_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Salary details (encrypted in production)
    bank_name = Column(String, nullable=True)
    bank_account_number = Column(String, nullable=True)
    ifsc_code = Column(String, nullable=True)
    pan_number = Column(String, nullable=True)
    aadhar_number = Column(String, nullable=True)
    
    # Emergency contact
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_number = Column(String, nullable=True)
    emergency_contact_relation = Column(String, nullable=True)
    
    # Documents
    photo_path = Column(String, nullable=True)
    resume_path = Column(String, nullable=True)
    
    # Status
    employment_status = Column(String, default="active")  # active, on_leave, terminated
    is_rotational = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    shift = relationship("WorkShift")
    manager = relationship("User", foreign_keys=[reporting_to])


class LeaveApprovalWorkflow(Base):
    """Custom approval workflows for leave"""
    __tablename__ = "leave_approval_workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Leave types this workflow applies to
    leave_types = Column(String, nullable=True)  # JSON array
    
    # Approval levels
    approval_levels = Column(String, nullable=True)  # JSON array of user IDs
    
    # Conditions
    min_days_for_approval = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DirectorStaffStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class DirectorAttendanceType(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LEAVE = "leave"
    HOLIDAY = "holiday"


class StaffAttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"
    APPROVED_LEAVE = "approved_leave"
    WORK_FROM_HOME = "work_from_home"


class AttendanceDisputeStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"


class LinkedDeviceType(str, enum.Enum):
    BIOMETRIC = "biometric"
    RFID = "rfid"
    MOBILE = "mobile"


class StaffTaskPriority(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class StaffTaskStatus(str, enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"


class DirectorProfile(Base):
    __tablename__ = "director_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    photo_path = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    date_of_joining = Column(DateTime, nullable=True)
    specialization = Column(String, nullable=True)
    emergency_contact = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    branch = relationship("Branch", foreign_keys=[branch_id])


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    staff_id = Column(String(30), nullable=False, unique=True)
    photo_path = Column(String, nullable=True)
    department = Column(String, nullable=True)
    specialization = Column(String, nullable=True)
    shift_timings = Column(String, nullable=True)
    reporting_manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date_of_joining = Column(DateTime, nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact = Column(String, nullable=True)
    can_access_daily_ops = Column(Boolean, nullable=False, default=False)
    status = Column(CompatEnum(DirectorStaffStatus), default=DirectorStaffStatus.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    branch = relationship("Branch", foreign_keys=[branch_id])
    manager = relationship("User", foreign_keys=[reporting_manager_id])
    attendance_disputes = relationship("AttendanceDispute", back_populates="staff_profile")
    linked_devices = relationship("LinkedDevice", back_populates="staff_profile")


class StaffSalaryDetail(Base):
    __tablename__ = "staff_salary_details"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False, unique=True)
    basic = Column(DECIMAL(12, 2), default=0)
    hra = Column(DECIMAL(12, 2), default=0)
    allowances = Column(DECIMAL(12, 2), default=0)
    deductions = Column(DECIMAL(12, 2), default=0)
    net_pay = Column(DECIMAL(12, 2), default=0)
    bank_name = Column(String, nullable=True)
    account_number = Column(String, nullable=True)
    ifsc_code = Column(String, nullable=True)
    upi_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")


class StaffSalaryRecord(Base):
    __tablename__ = "staff_salary_records"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    basic_salary = Column(DECIMAL(12, 2), default=0)
    hra = Column(DECIMAL(12, 2), default=0)
    allowances = Column(DECIMAL(12, 2), default=0)
    deductions = Column(DECIMAL(12, 2), default=0)
    net_pay = Column(DECIMAL(12, 2), default=0)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

    staff_profile = relationship("StaffProfile")
    branch = relationship("Branch", foreign_keys=[branch_id])
    generator = relationship("User", foreign_keys=[generated_by])


class StaffAttendanceLog(Base):
    __tablename__ = "staff_attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    date = Column(Date, nullable=True)
    attendance_date = Column(DateTime, nullable=False)
    attendance_type = Column(CompatEnum(DirectorAttendanceType), default=DirectorAttendanceType.PRESENT, nullable=False)
    status = Column(CompatEnum(StaffAttendanceStatus), default=StaffAttendanceStatus.PRESENT, nullable=False)
    clock_in_time = Column(DateTime, nullable=True)
    clock_out_time = Column(DateTime, nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    selfie_url = Column(String, nullable=True)
    clock_in_latitude = Column(String, nullable=True)
    clock_in_longitude = Column(String, nullable=True)
    clock_out_latitude = Column(String, nullable=True)
    clock_out_longitude = Column(String, nullable=True)
    clock_in_photo_path = Column(String, nullable=True)
    clock_out_photo_path = Column(String, nullable=True)
    work_mode = Column(String(30), nullable=False, default="onsite")
    wfh_reason = Column(Text, nullable=True)
    task = Column(Text, nullable=True)
    task_status = Column(String(40), nullable=False, default="Pending")
    staff_note = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)
    hr_remark = Column(Text, nullable=True)
    dispute_resolved = Column(Boolean, nullable=False, default=False)
    is_remote = Column(Boolean, nullable=False, default=False)
    distance_from_branch_meters = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")
    branch = relationship("Branch")


class StaffLeaveRequest(Base):
    __tablename__ = "staff_leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    leave_type = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    total_days = Column(Float, default=0)
    duration_days = Column(Float, default=0)
    duration_hours = Column(Float, default=0)
    reason = Column(Text, nullable=True)
    attachments = Column(String, nullable=True)
    status = Column(CompatEnum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approval_date = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    approver = relationship("User", foreign_keys=[approved_by])
    branch = relationship("Branch")


class AttendanceDispute(Base):
    __tablename__ = "attendance_disputes"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(SQLEnum(AttendanceDisputeStatus), default=AttendanceDisputeStatus.OPEN, nullable=False)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    staff_profile = relationship("StaffProfile", back_populates="attendance_disputes")


class LinkedDevice(Base):
    __tablename__ = "linked_devices"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    device_id = Column(String(120), nullable=False)
    device_type = Column(SQLEnum(LinkedDeviceType), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile", back_populates="linked_devices")


class StaffPerformanceNote(Base):
    __tablename__ = "staff_performance_notes"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    director_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")
    director = relationship("User", foreign_keys=[director_user_id])


class StaffTask(Base):
    __tablename__ = "staff_tasks"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    task_name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(40), nullable=False, default="Pending")
    priority = Column(String(20), nullable=False, default="Medium")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")
    branch = relationship("Branch", foreign_keys=[branch_id])
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])
    assigned_to_user = relationship("User", foreign_keys=[assigned_to])
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")


class TaskComment(Base):
    __tablename__ = "task_comments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("staff_tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("StaffTask", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])


class TaskAttachment(Base):
    __tablename__ = "task_attachments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("staff_tasks.id"), nullable=False)
    file_url = Column(String, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("StaffTask", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])


class StaffNotification(Base):
    __tablename__ = "staff_notifications"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")
    branch = relationship("Branch", foreign_keys=[branch_id])


class StaffDocument(Base):
    __tablename__ = "staff_documents"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    document_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    staff_profile = relationship("StaffProfile")
    uploader = relationship("User", foreign_keys=[uploaded_by])


class StaffWeeklyRoster(Base):
    __tablename__ = "staff_weekly_rosters"

    id = Column(Integer, primary_key=True, index=True)
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    week_start_date = Column(DateTime, nullable=False)
    week_end_date = Column(DateTime, nullable=False)
    schedule_json = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")
    branch = relationship("Branch", foreign_keys=[branch_id])
    creator = relationship("User", foreign_keys=[created_by])


class DirectorNotification(Base):
    __tablename__ = "director_notifications"

    id = Column(Integer, primary_key=True, index=True)
    director_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    director = relationship("User", foreign_keys=[director_user_id])
    branch = relationship("Branch")

