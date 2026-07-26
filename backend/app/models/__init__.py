from app.models.doctor import Doctor
from app.models.doctor_portal import CMECourse, DoctorAuditLog, DoctorMessage, DoctorReferralLog, LoyaltyReward, Order, PatientSearchLog, TestPanel
from app.models.referring_doctor import ReferringDoctor, ReferralLog, DoctorShareLink
from app.models.branch_bank_details import BranchBankDetails
from app.models.inventory import (
    InventoryItemV2,
    InventoryEquipment,
    EquipmentServiceLog,
    InventoryConsumptionHistory,
    InventoryStockAudit,
    InventoryStockMovement as InventoryStockMovementV2,
    Supplier,
)
from app.models.finance import BranchAccount, FinanceExpense, FinanceInvoice, FinanceTransaction
from app.models.analytics import DailyAnalyticsSnapshot
from app.models.payroll import (
    AdvanceRequest,
    AdvanceStatus,
    EarningHead,
    PayrollDispute,
    PayrollDisputeStatus,
    PayrollAuditLog,
    PayrollLock,
    PayrollRun,
    PayrollRunStatus,
    PayrollTransaction,
    ReimbursementClaim,
    ReimbursementStatus,
    SalaryGrade,
    StaffSalaryConfig,
    StaffTaxDeclaration,
)
from app.models.patient import PatientProfile, FamilyMember
from app.models.patient_b2c import (
    DigitalConsent,
    FollowUpReminder,
    HealthScore,
    HealthGoal,
    HealthTrend,
    LoyaltyReward,
    PatientB2CAppointment,
    PatientB2CAuditLog,
    Referral,
    ReportSummary,
    TestCatalog,
)
from app.models.patient_phase4 import EmergencyAlert, PatientVaultDocument, SecondOpinionRequest, WearableSync
from app.models.payment import Invoice, InvoiceItem, Payment
from app.models.lab_result import LabResult
from app.models.appointment import Appointment
from app.models.calendar_day import CalendarDay
from app.models.release_day import ReleaseDay
from app.models.ceo import CeoAuditLog, CeoBreakGlassGrant, CeoSecurityProfile, CeoWebAuthnCredential
import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, DECIMAL, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    location = Column(String(200), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)
    phone = Column(String(15), nullable=False)
    email = Column(String(100), nullable=False)
    license_number = Column(String(100), unique=True)
    branch_code = Column(String(20), unique=True, nullable=False)
    opening_hours = Column(String(500), nullable=True)
    facilities = Column(Text, nullable=True)
    director_photo_url = Column(Text, nullable=True)
    logo_url = Column(Text, nullable=True)
    director_age = Column(String(50), nullable=True)
    director_credentials_username = Column(String(100), nullable=True)
    director_credentials_password = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    established_date = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="branch")
    patients = relationship("Patient", back_populates="branch")
    daily_entries = relationship("DailyEntry", back_populates="branch")
    staff = relationship("Staff", back_populates="branch")
    inventory_items = relationship("InventoryItem", back_populates="branch")
    invoices = relationship("Invoice", back_populates="branch")
    calendar_days = relationship("CalendarDay", back_populates="branch")
    assets = relationship("Asset", back_populates="branch")
    bank_details = relationship("BranchBankDetails", back_populates="branch", uselist=False)
    branch_accounts = relationship("BranchAccount", back_populates="branch")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="staff")  # super_admin, branch_admin, staff, patient
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime)
    
    # Personal details
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(15), nullable=False)
    
    # Relationships
    branch = relationship("Branch", back_populates="users")
    activity_logs = relationship("ActivityLog", back_populates="user")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), unique=True, nullable=False)  # Auto-generated
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(DateTime, nullable=False)
    gender = Column(String(10), nullable=False)  # Male, Female, Other
    phone = Column(String(15), nullable=False)
    email = Column(String(100), nullable=True)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)
    emergency_contact = Column(String(15), nullable=False)
    emergency_contact_name = Column(String(200), nullable=False)
    
    # Medical Information
    blood_group = Column(String(5), nullable=True)
    allergies = Column(Text, nullable=True)
    chronic_conditions = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    
    # Registration Details
    registration_date = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    branch = relationship("Branch", back_populates="patients")
    daily_entries = relationship("DailyEntry", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    invoices = relationship("Invoice", back_populates="patient")
    lab_results = relationship("LabResult", back_populates="patient")

class DailyEntry(Base):
    __tablename__ = "daily_entries"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    
    # Entry Details
    entry_date = Column(DateTime, nullable=False)
    entry_time = Column(DateTime, default=func.now())
    
    # Doctor Information
    doctor_name = Column(String(200), nullable=False)
    doctor_specialization = Column(String(100), nullable=True)
    consultation_fee = Column(DECIMAL(10, 2), nullable=False)
    
    # Patient Information
    patient_name = Column(String(200), nullable=False)
    patient_mobile = Column(String(15), nullable=False)
    patient_address = Column(Text, nullable=False)
    
    # Test Information
    test_names = Column(Text, nullable=False)  # JSON or comma-separated
    test_cost = Column(DECIMAL(10, 2), default=0)
    discount = Column(DECIMAL(10, 2), default=0)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    
    # Payment Information
    payment_status = Column(String(20), default="pending")  # pending, paid, partial
    payment_mode = Column(String(20))  # cash, card, online, insurance
    amount_paid = Column(DECIMAL(10, 2), default=0)
    
    # Additional Information
    notes = Column(Text, nullable=True)
    referred_by = Column(String(200), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    branch = relationship("Branch", back_populates="daily_entries")
    patient = relationship("Patient", back_populates="daily_entries")
    creator = relationship("User")

class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Employee Details
    employee_id = Column(String(20), unique=True, nullable=False)
    department = Column(String(100), nullable=False)  # reception, lab, billing, admin
    position = Column(String(100), nullable=False)
    date_of_joining = Column(DateTime, nullable=False)
    salary = Column(DECIMAL(12, 2), nullable=False)
    
    # Personal Information
    date_of_birth = Column(DateTime, nullable=False)
    qualification = Column(String(200), nullable=True)
    experience_years = Column(Integer, default=0)
    
    # Attendance & Performance
    total_leaves = Column(Integer, default=0)
    leaves_taken = Column(Integer, default=0)
    performance_rating = Column(Integer, default=5)  # 1-5 scale
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    branch = relationship("Branch", back_populates="staff")
    user = relationship("User")
    attendance_records = relationship("AttendanceRecord", back_populates="staff")
    salary_records = relationship("SalaryRecord", back_populates="staff")

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    
    # Date & Time
    attendance_date = Column(DateTime, nullable=False)
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(20), default="present")  # present, absent, late, half_day, leave
    late_minutes = Column(Integer, default=0)
    overtime_minutes = Column(Integer, default=0)
    
    # Additional Info
    notes = Column(Text, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    staff = relationship("Staff", back_populates="attendance_records")
    approver = relationship("User")

class SalaryRecord(Base):
    __tablename__ = "salary_records"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    
    # Salary Details
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    base_salary = Column(DECIMAL(12, 2), nullable=False)
    bonus = Column(DECIMAL(10, 2), default=0)
    deductions = Column(DECIMAL(10, 2), default=0)
    
    # Calculated Fields
    gross_salary = Column(DECIMAL(12, 2), nullable=False)
    net_salary = Column(DECIMAL(12, 2), nullable=False)
    
    # Payment Details
    payment_date = Column(DateTime, nullable=True)
    payment_status = Column(String(20), default="pending")  # pending, paid, processed
    payment_mode = Column(String(20), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    staff = relationship("Staff", back_populates="salary_records")

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    
    # Item Details
    item_code = Column(String(50), unique=True, nullable=False)
    item_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)  # reagent, equipment, consumable, medicine
    subcategory = Column(String(100), nullable=True)
    unit = Column(String(50), nullable=False)  # pieces, ml, kg, etc.
    
    # Stock Information
    current_stock = Column(Integer, default=0)
    minimum_stock = Column(Integer, default=0)
    maximum_stock = Column(Integer, default=0)
    reorder_level = Column(Integer, default=0)
    
    # Financial Information
    purchase_price = Column(DECIMAL(10, 2), nullable=False)
    selling_price = Column(DECIMAL(10, 2), nullable=False)
    supplier = Column(String(200), nullable=True)
    supplier_contact = Column(String(15), nullable=True)
    
    # Expiry & Batch Information
    batch_number = Column(String(100), nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    manufacture_date = Column(DateTime, nullable=True)
    
    # Status & Tracking
    is_active = Column(Boolean, default=True)
    last_restocked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    branch = relationship("Branch", back_populates="inventory_items")
    stock_movements = relationship("StockMovement", back_populates="item")

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    
    # Movement Details
    movement_type = Column(String(20), nullable=False)  # purchase, consumption, wastage, adjustment
    quantity = Column(Integer, nullable=False)
    previous_stock = Column(Integer, nullable=False)
    new_stock = Column(Integer, nullable=False)
    
    # Reference Information
    reference_number = Column(String(100), nullable=True)  # PO number, invoice number, etc.
    movement_date = Column(DateTime, default=func.now())
    notes = Column(Text, nullable=True)
    
    # User Information
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    item = relationship("InventoryItem", back_populates="stock_movements")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])



from .activity_log import ActivityLog


# Multi-modality support
from sqlalchemy import Table

branch_modalities = Table(
    "branch_modalities",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("branch_id", Integer, ForeignKey("branches.id"), nullable=False),
    Column("modality_id", Integer, ForeignKey("modalities.id"), nullable=False),
)


class Modality(Base):
    __tablename__ = "modalities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    branches = relationship("Branch", secondary=branch_modalities, backref="modalities")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    asset_name = Column(String(200), nullable=False)
    model = Column(String(200), nullable=True)
    serial_no = Column(String(200), nullable=True)
    purchase_date = Column(DateTime, nullable=True)
    last_maintenance_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="active")  # active, under_repair, retired
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    branch = relationship("Branch", back_populates="assets")

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text, nullable=False)
    setting_type = Column(String(50), default="string")  # string, integer, boolean, json
    description = Column(Text, nullable=True)
    is_editable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    @property
    def tagline(self) -> str:
        if self.setting_key not in {"branding", "ceo_branding"}:
            return ""
        try:
            payload = json.loads(self.setting_value or "{}")
        except (TypeError, json.JSONDecodeError):
            return ""
        if not isinstance(payload, dict):
            return ""
        return (
            (payload.get("tagline") or "").strip()
            or ((payload.get("company_profile") or {}).get("tagline") or "").strip()
        )

    @tagline.setter
    def tagline(self, value: str) -> None:
        if self.setting_key not in {"branding", "ceo_branding"}:
            return
        try:
            payload = json.loads(self.setting_value or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        clean = (value or "").strip()
        payload["tagline"] = clean
        company_profile = dict(payload.get("company_profile") or {})
        company_profile["tagline"] = clean
        payload["company_profile"] = company_profile
        self.setting_value = json.dumps(payload)
