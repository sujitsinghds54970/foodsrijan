"""
Doctor Management Models for VaidyaVihar Diagnostic ERP

This module contains models for managing doctors across all branches
in the city, including their patient report distribution preferences.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, DECIMAL, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Doctor(Base):
    """
    Doctor model for managing doctors across all branches.
    Doctors can be assigned to multiple branches and receive reports
    from any diagnostic test performed at any branch.
    """
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(String(20), unique=True, nullable=False)  # DOC-XXXX format
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(15), nullable=False)
    alternate_phone = Column(String(15), nullable=True)
    
    # Professional Information
    qualification = Column(String(200), nullable=False)  # MBBS, MD, DM, etc.
    specialization = Column(String(100), nullable=False)  # Cardiology, Neurology, etc.
    registration_number = Column(String(50), nullable=True)  # Medical council registration
    years_of_experience = Column(Integer, default=0)
    
    # Practice Details
    clinic_name = Column(String(200), nullable=True)
    clinic_address = Column(Text, nullable=True)
    clinic_city = Column(String(100), nullable=True)
    
    # Account Information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Link to system user
    username = Column(String(100), nullable=True)  # For portal access
    hashed_password = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Preferences
    notification_preferences = Column(JSON, default={
        "email": True,
        "sms": True,
        "whatsapp": True,
        "push": True,
        "report_ready": True,
        "appointment_reminder": True,
        "urgent_alerts": True
    })

    # Doctor portal profile and referral settings
    upi_id = Column(String(120), nullable=True)
    bank_account = Column(String(100), nullable=True)
    ifsc = Column(String(30), nullable=True)
    commission_percentage = Column(Float, default=0)
    loyalty_tier = Column(String(20), default="Silver")
    
    # Report Preferences
    report_preferences = Column(JSON, default={
        "auto_receive_reports": True,
        "pdf_format": True,
        "dicom_format": False,
        "email_delivery": True,
        "whatsapp_delivery": True,
        "portal_access": True,
        "report_retention_days": 365
    })
    
    # Dashboard Access
    can_access_dashboard = Column(Boolean, default=True)
    can_view_patient_history = Column(Boolean, default=True)
    can_download_reports = Column(Boolean, default=True)
    can_print_reports = Column(Boolean, default=True)
    
    # Audit Fields
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    branches = relationship("DoctorBranch", back_populates="doctor", cascade="all, delete-orphan")
    user = relationship("User", foreign_keys=[user_id])
    received_reports = relationship("ReportDistribution", back_populates="doctor", foreign_keys="ReportDistribution.doctor_id")
    notifications = relationship("DoctorNotification", back_populates="doctor")
    
    def __repr__(self):
        return f"<Doctor {self.doctor_id}: {self.first_name} {self.last_name} - {self.specialization}>"
    
    @property
    def full_name(self):
        return f"Dr. {self.first_name} {self.last_name}"
    
    @property
    def active_branches(self):
        return [db for db in self.branches if db.is_active]
    
    def get_all_branch_ids(self):
        return [db.branch_id for db in self.branches]


class DoctorBranch(Base):
    """
    Junction table linking doctors to branches.
    A doctor can be associated with multiple branches.
    """
    __tablename__ = "doctor_branches"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    
    # Assignment Details
    assigned_date = Column(DateTime, default=func.now())
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Branch-specific settings
    is_primary = Column(Boolean, default=False)  # Primary branch for this doctor
    can_receive_reports = Column(Boolean, default=True)
    receive_all_reports = Column(Boolean, default=True)  # Or specific test types
    
    # Test type preferences (if not receiving all)
    preferred_test_types = Column(JSON, default=[
        "blood_test",
        "urine_test",
        "xray",
        "ultrasound",
        "ct_scan",
        "mri",
        "ecg",
        "echo",
        "pathology",
        "microbiology"
    ])
    
    # Status
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    deactivated_at = Column(DateTime, nullable=True)
    deactivated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    doctor = relationship("Doctor", back_populates="branches")
    branch = relationship("Branch")
    assigner = relationship("User", foreign_keys=[assigned_by])
    deactivator = relationship("User", foreign_keys=[deactivated_by])

    def __repr__(self):
        return f"<DoctorBranch: Doctor {self.doctor_id} -> Branch {self.branch_id}>"


class ReportDistribution(Base):
    """
    Tracks report distribution to doctors.
    Records which reports were sent to which doctors and delivery status.
    """
    __tablename__ = "report_distributions"

    id = Column(Integer, primary_key=True, index=True)
    distribution_id = Column(String(30), unique=True, nullable=False)  # RD-XXXXXXXX format
    
    # Report Reference
    lab_result_id = Column(Integer, ForeignKey("lab_results.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    
    # Doctor Reference
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    
    # Delivery Details
    report_type = Column(String(50), nullable=False)  # blood_test, xray, ultrasound, etc.
    report_name = Column(String(200), nullable=False)
    
    # File Information
    file_path = Column(String(500), nullable=True)
    file_format = Column(String(20), default="pdf")  # pdf, dicom, jpg, etc.
    file_size = Column(Integer, nullable=True)  # in bytes
    
    # Delivery Status
    delivery_status = Column(String(20), default="pending")  # pending, sent, delivered, read, failed
    delivery_method = Column(String(50), nullable=True)  # email, whatsapp, portal, fax
    
    # Notification Tracking
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    sms_sent = Column(Boolean, default=False)
    sms_sent_at = Column(DateTime, nullable=True)
    whatsapp_sent = Column(Boolean, default=False)
    whatsapp_sent_at = Column(DateTime, nullable=True)
    push_sent = Column(Boolean, default=False)
    push_sent_at = Column(DateTime, nullable=True)
    
    # Doctor Action
    viewed_at = Column(DateTime, nullable=True)
    downloaded_at = Column(DateTime, nullable=True)
    printed_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    feedback = Column(Text, nullable=True)  # Doctor's feedback on report
    
    # Priority
    priority = Column(String(20), default="normal")  # urgent, high, normal, low
    is_urgent = Column(Boolean, default=False)
    
    # Expiry
    expires_at = Column(DateTime, nullable=True)  # When doctor access expires
    
    # Audit
    created_at = Column(DateTime, default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    doctor = relationship("Doctor", back_populates="received_reports", foreign_keys=[doctor_id])
    lab_result = relationship("LabResult")
    patient = relationship("Patient")
    branch = relationship("Branch")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ReportDistribution {self.distribution_id}: {self.report_name} -> Dr. {self.doctor_id}>"
    
    @property
    def is_delivered(self):
        return self.delivery_status in ["delivered", "read"]
    
    @property
    def is_read(self):
        return self.delivery_status == "read"


class ReportTemplate(Base):
    """
    Templates for generating reports.
    Supports different templates for different test types.
    """
    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(100), nullable=False)
    template_type = Column(String(50), nullable=False)  # blood_test, xray, ultrasound, etc.
    
    # Template Content (HTML/Jinja2)
    header_template = Column(Text, nullable=True)
    body_template = Column(Text, nullable=True)
    footer_template = Column(Text, nullable=True)
    
    # Branding
    logo_path = Column(String(500), nullable=True)
    primary_color = Column(String(10), default="#2563eb")
    secondary_color = Column(String(10), default="#10b981")
    
    # Settings
    include_branding = Column(Boolean, default=True)
    includeWatermark = Column(Boolean, default=False)
    watermark_text = Column(String(100), nullable=True)
    
    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Audit
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<ReportTemplate {self.template_name}: {self.template_type}>"


class DoctorNotification(Base):
    """
    Notifications sent to doctors.
    Tracks all notification delivery and engagement.
    """
    __tablename__ = "doctor_notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(30), unique=True, nullable=False)  # NT-XXXXXXXX format
    
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    
    # Notification Details
    notification_type = Column(String(50), nullable=False)  # report_ready, appointment, reminder, urgent
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Action
    action_url = Column(String(500), nullable=True)  # Link to relevant page
    reference_id = Column(String(50), nullable=True)  # Report ID, Appointment ID, etc.
    reference_type = Column(String(50), nullable=True)  # lab_result, appointment, etc.
    
    # Delivery Status
    channel = Column(String(20), nullable=True)  # email, sms, whatsapp, push, portal
    status = Column(String(20), default="pending")  # pending, sent, delivered, read, failed
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    # Content
    short_message = Column(String(200), nullable=True)  # For SMS/Push
    html_content = Column(Text, nullable=True)  # For Email
    
    # Priority
    priority = Column(String(20), default="normal")  # urgent, high, normal, low
    expires_at = Column(DateTime, nullable=True)
    
    # Engagement
    action_taken = Column(String(50), nullable=True)  # clicked, dismissed, etc.
    action_at = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=func.now())

    # Relationships
    doctor = relationship("Doctor", back_populates="notifications")

    def __repr__(self):
        return f"<DoctorNotification {self.notification_id}: {self.title}>"


class DoctorSchedule(Base):
    """
    Doctor availability schedule for appointments.
    """
    __tablename__ = "doctor_schedules"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    
    # Day and Time
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(String(10), nullable=False)  # HH:MM format
    end_time = Column(String(10), nullable=False)  # HH:MM format
    
    # Slot Details
    slot_duration = Column(Integer, default=30)  # minutes
    max_appointments = Column(Integer, default=20)
    
    # Break Time
    break_start = Column(String(10), nullable=True)
    break_end = Column(String(10), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    doctor = relationship("Doctor")
    branch = relationship("Branch")

    def __repr__(self):
        return f"<DoctorSchedule: Dr. {self.doctor_id} - Day {self.day_of_week}>"
