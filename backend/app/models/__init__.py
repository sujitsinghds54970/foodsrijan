from app.models.staff import Staff
from app.models.doctor_portal import CMECourse, StaffAuditLog, StaffMessage, StaffReferralLog, LoyaltyReward, Order, CustomerSearchLog, MenuItemPanel
from app.models.referring_doctor import ReferringStaff, ReferralLog, StaffShareLink
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
from app.models.customer import CustomerProfile, FamilyMember
from app.models.patient_b2c import (
    DigitalConsent,
    FollowUpReminder,
    HealthScore,
    HealthGoal,
    HealthTrend,
    LoyaltyReward,
    CustomerB2CAppointment,
    CustomerB2CAuditLog,
    Referral,
    OrderSummary,
    MenuItemCatalog,
)
from app.models.patient_phase4 import EmergencyAlert, CustomerVaultDocument, SecondOpinionRequest, WearableSync
from app.models.payment import Invoice, InvoiceItem, Payment
from app.models.lab_result import LabResult
from app.models.appointment import Appointment
from app.models.calendar_day import CalendarDay
from app.models.release_day import ReleaseDay
from app.models.ceo import CeoAuditLog, CeoBreakGlassGrant, CeoSecurityProfile, CeoWebAuthnCredential
from app.models.hr import StaffProfile, StaffRequest
from app.models import attendance  # Register the managed ledger without replacing legacy AttendanceRecord.
from app.models.otp import OTPRequest
from app.models.company_structure import Company, Brand, Department, Role, Permission, UserRole, UserCompany, RateLimitEntry
from app.models.authority import ProfileMembership, ProfileType, RoleAssignment
from app.models.themes import Theme, ThemeAssignment, ThemeVersion
from app.models.auth_security import LoginAttempt
import json
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Text, Float, DECIMAL, JSON, Index, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (
        Index("uq_branches_company_code", "company_id", "code", unique=True),
        Index("uq_branches_company_slug", "company_id", "slug", unique=True),
        Index("uq_branches_gstin", "gstin", unique=True),
        Index("ix_branches_company_status", "company_id", "status"),
        Index("ix_branches_is_deleted", "is_deleted"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
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

    # Outlet identity
    slug = Column(String(120), nullable=True)
    code = Column(String(20), nullable=True)
    outlet_type = Column(String(32), nullable=True)
    status = Column(String(32), nullable=True, default="active", server_default="active")
    description = Column(Text, nullable=True)
    opening_date = Column(Date, nullable=True)
    cover_photo_url = Column(String(2048), nullable=True)

    # Outlet location
    address_line_1 = Column(String(255), nullable=True)
    address_line_2 = Column(String(255), nullable=True)
    country = Column(String(2), nullable=True)
    region = Column(String(32), nullable=True)
    timezone = Column(String(64), nullable=True)

    # Outlet operations
    opening_time = Column(String(5), nullable=True)
    closing_time = Column(String(5), nullable=True)
    operating_days = Column(JSON, nullable=True)
    seating_capacity = Column(Integer, nullable=True)
    kitchen_capacity = Column(Integer, nullable=True)
    is_delivery_enabled = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    is_dine_in_enabled = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    is_takeaway_enabled = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    delivery_radius_km = Column(Float, nullable=True)

    # Outlet legal & compliance
    fssai_license = Column(String(14), nullable=True)
    gstin = Column(String(15), nullable=True)
    trade_license = Column(String(100), nullable=True)
    fire_safety_certificate = Column(String(100), nullable=True)
    health_permit = Column(String(100), nullable=True)
    license_expiry_date = Column(Date, nullable=True)

    # Outlet financial
    rent_amount = Column(DECIMAL(14, 2), nullable=True)
    security_deposit = Column(DECIMAL(14, 2), nullable=True)
    lease_start_date = Column(Date, nullable=True)
    lease_end_date = Column(Date, nullable=True)
    bank_account_name = Column(String(255), nullable=True)
    bank_account_number = Column(String(34), nullable=True)
    ifsc_code = Column(String(11), nullable=True)
    bank_name = Column(String(255), nullable=True)
    branch_name = Column(String(255), nullable=True)
    upi_id = Column(String(100), nullable=True)
    cost_center_code = Column(String(50), nullable=True)

    # Outlet digital
    manager_contact_email = Column(String(254), nullable=True)
    manager_contact_phone = Column(String(32), nullable=True)
    outlet_email = Column(String(254), nullable=True)
    outlet_phone = Column(String(32), nullable=True)
    google_maps_url = Column(String(2048), nullable=True)
    swiggy_store_id = Column(String(64), nullable=True)
    zomato_store_id = Column(String(64), nullable=True)

    # Outlet metadata
    created_by = Column(Integer, ForeignKey("users.id", name="fk_branches_created_by_users"), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    outlet_metadata = Column("metadata", JSON, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    company = relationship("Company", back_populates="branches")
    brand = relationship("Brand", back_populates="branches")
    users = relationship("User", foreign_keys="User.branch_id", back_populates="branch")
    customers = relationship("Customer", back_populates="branch")
    daily_entries = relationship("DailyEntry", back_populates="branch")
    StaffEmployee = relationship("StaffEmployee", back_populates="branch")
    inventory_items = relationship("InventoryItem", back_populates="branch")
    invoices = relationship("Invoice", back_populates="branch")
    calendar_days = relationship("CalendarDay", back_populates="branch")
    assets = relationship("Asset", back_populates="branch")
    bank_details = relationship("BranchBankDetails", back_populates="branch", uselist=False)
    branch_accounts = relationship("BranchAccount", back_populates="branch")

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_active_super_ceo",
            "is_super_ceo",
            unique=True,
            sqlite_where=text("is_super_ceo = 1 AND is_active = 1"),
            postgresql_where=text("is_super_ceo AND is_active"),
        ),
        Index("ix_users_is_company_ceo", "is_company_ceo"),
        Index("ix_users_company_id_ceo", "company_id", "is_company_ceo"),
        Index("ix_users_outlet_id", "outlet_id"),
        Index("ix_users_company_outlet_manager", "company_id", "is_outlet_manager"),
        Index("ix_users_company_outlet_staff", "company_id", "outlet_id", "is_staff"),
        Index(
            "uq_users_active_outlet_manager",
            "outlet_id",
            unique=True,
            sqlite_where=text("is_outlet_manager = 1 AND is_active = 1"),
            postgresql_where=text("is_outlet_manager AND is_active"),
        ),
        Index(
            "uq_users_staff_phone_active",
            "phone",
            unique=True,
            sqlite_where=text("is_staff = 1 AND is_deleted = 0"),
            postgresql_where=text("is_staff AND NOT is_deleted"),
        ),
        Index(
            "uq_users_staff_outlet_employee_code",
            "outlet_id",
            "employee_code",
            unique=True,
            sqlite_where=text("is_staff = 1 AND is_deleted = 0 AND employee_code IS NOT NULL"),
            postgresql_where=text("is_staff AND NOT is_deleted AND employee_code IS NOT NULL"),
        ),
        Index(
            "uq_users_staff_aadhaar_active",
            "aadhaar_number",
            unique=True,
            sqlite_where=text("is_staff = 1 AND is_deleted = 0 AND aadhaar_number IS NOT NULL"),
            postgresql_where=text("is_staff AND NOT is_deleted AND aadhaar_number IS NOT NULL"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="StaffEmployee")  # super_admin, branch_admin, StaffEmployee, patient
    current_company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_super_admin = Column(Boolean, default=False, nullable=False)
    is_super_ceo = Column(Boolean, default=False, nullable=False)
    is_company_ceo = Column(Boolean, default=False, nullable=False, server_default=text("0"))
    ceo_assigned_at = Column(DateTime, nullable=True)
    ceo_assigned_by = Column(Integer, ForeignKey("users.id", name="fk_users_ceo_assigned_by_users"), nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    force_password_change = Column(Boolean, default=False, nullable=False, server_default=text("0"))
    display_name = Column(String(150), nullable=True)
    bio = Column(Text, nullable=True)
    profile_photo_url = Column(String(2048), nullable=True)
    cover_photo_url = Column(String(2048), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(32), nullable=True)
    location_city = Column(String(120), nullable=True)
    location_state = Column(String(120), nullable=True)
    location_country = Column(String(120), nullable=True)
    timezone = Column(String(64), nullable=True)
    emergency_contact_name = Column(String(150), nullable=True)
    emergency_contact_phone = Column(String(32), nullable=True)
    assistant_name = Column(String(150), nullable=True)
    assistant_email = Column(String(254), nullable=True)
    assistant_phone = Column(String(32), nullable=True)
    preferred_contact_method = Column(String(20), nullable=True)
    qualifications = Column(JSON, nullable=True)
    certifications = Column(JSON, nullable=True)
    achievements = Column(JSON, nullable=True)
    preferences = Column(JSON, nullable=True)
    recovery_email = Column(String(254), nullable=True)
    recovery_phone = Column(String(32), nullable=True)
    is_outlet_manager = Column(Boolean, default=False, nullable=False, server_default=text("0"))
    outlet_id = Column(Integer, ForeignKey("branches.id", name="fk_users_outlet_id_branches"), nullable=True)
    manager_assigned_at = Column(DateTime, nullable=True)
    manager_assigned_by = Column(Integer, ForeignKey("users.id", name="fk_users_manager_assigned_by_users"), nullable=True)
    manager_photo_url = Column(String(2048), nullable=True)
    manager_address = Column(Text, nullable=True)
    manager_bank_account_name = Column(String(255), nullable=True)
    manager_bank_account_number = Column(String(34), nullable=True)
    manager_ifsc_code = Column(String(11), nullable=True)
    manager_bank_name = Column(String(255), nullable=True)
    is_staff = Column(Boolean, default=False, nullable=False, server_default=text("0"))
    staff_role = Column(String(40), nullable=True)
    employee_code = Column(String(40), nullable=True)
    manager_id = Column(Integer, ForeignKey("users.id", name="fk_users_manager_id_users"), nullable=True)
    staff_assigned_at = Column(DateTime, nullable=True)
    staff_assigned_by = Column(Integer, ForeignKey("users.id", name="fk_users_staff_assigned_by_users"), nullable=True)
    alternate_phone = Column(String(32), nullable=True)
    blood_group = Column(String(10), nullable=True)
    marital_status = Column(String(32), nullable=True)
    current_address = Column(Text, nullable=True)
    permanent_address = Column(Text, nullable=True)
    emergency_contact_relation = Column(String(100), nullable=True)
    aadhaar_number = Column(String(32), nullable=True)
    pan_number = Column(String(16), nullable=True)
    voter_id = Column(String(32), nullable=True)
    driving_license = Column(String(32), nullable=True)
    passport_number = Column(String(32), nullable=True)
    bank_account_name = Column(String(255), nullable=True)
    bank_account_number = Column(String(34), nullable=True)
    ifsc_code = Column(String(11), nullable=True)
    bank_name = Column(String(255), nullable=True)
    branch_name = Column(String(255), nullable=True)
    upi_id = Column(String(100), nullable=True)
    experience_years = Column(Float, nullable=True)
    previous_employer = Column(String(255), nullable=True)
    skills = Column(JSON, nullable=True)
    joining_date = Column(Date, nullable=True)
    employment_type = Column(String(20), nullable=True)
    probation_end_date = Column(Date, nullable=True)
    salary_type = Column(String(20), nullable=True)
    monthly_salary = Column(DECIMAL(12, 2), nullable=True)
    daily_wage = Column(DECIMAL(12, 2), nullable=True)
    hourly_rate = Column(DECIMAL(12, 2), nullable=True)
    shift_preference = Column(String(100), nullable=True)
    weekly_off_day = Column(String(20), nullable=True)
    pf_applicable = Column(Boolean, default=False, nullable=False, server_default=text("0"))
    esi_applicable = Column(Boolean, default=False, nullable=False, server_default=text("0"))
    tds_applicable = Column(Boolean, default=False, nullable=False, server_default=text("0"))
    deactivated_at = Column(DateTime, nullable=True)
    deactivated_reason = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", name="fk_users_created_by_users"), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime)
    
    # Personal details
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(15), nullable=False)
    
    # Relationships
    current_company = relationship("Company", foreign_keys=[current_company_id], back_populates="current_users")
    company = relationship("Company", foreign_keys=[company_id], back_populates="users")
    brand = relationship("Brand")
    branch = relationship("Branch", foreign_keys=[branch_id], back_populates="users")
    outlet = relationship("Branch", foreign_keys=[outlet_id], viewonly=True)
    companies = relationship("Company", secondary="user_companies", back_populates="users")
    role_assignments = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    profile_memberships = relationship("ProfileMembership", back_populates="user", cascade="all, delete-orphan")
    canonical_role_assignments = relationship("RoleAssignment", back_populates="user", cascade="all, delete-orphan")
    roles = relationship("Role", secondary="user_roles", viewonly=True, overlaps="role_assignments")
    activity_logs = relationship("ActivityLog", back_populates="user")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
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
    branch = relationship("Branch", back_populates="customers")
    daily_entries = relationship("DailyEntry", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    invoices = relationship("Invoice", back_populates="patient")
    lab_results = relationship("LabResult", back_populates="patient")

class DailyEntry(Base):
    __tablename__ = "daily_entries"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    # Entry Details
    entry_date = Column(DateTime, nullable=False)
    entry_time = Column(DateTime, default=func.now())
    
    # StaffEmployee Information
    doctor_name = Column(String(200), nullable=False)
    doctor_specialization = Column(String(100), nullable=True)
    consultation_fee = Column(DECIMAL(10, 2), nullable=False)
    
    # Customer Information
    patient_name = Column(String(200), nullable=False)
    patient_mobile = Column(String(15), nullable=False)
    patient_address = Column(Text, nullable=False)
    
    # MenuItem Information
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
    patient = relationship("Customer", back_populates="daily_entries")
    creator = relationship("User")

class StaffEmployee(Base):
    __tablename__ = "staff_employees"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
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
    branch = relationship("Branch", back_populates="StaffEmployee")
    user = relationship("User")
    attendance_records = relationship("AttendanceRecord", back_populates="StaffEmployee_employee")
    salary_records = relationship("SalaryRecord", back_populates="StaffEmployee_employee")

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    staff_employee_id = Column(Integer, ForeignKey("staff_employees.id"), nullable=False)
    
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
    StaffEmployee_employee = relationship("StaffEmployee", back_populates="attendance_records")
    approver = relationship("User")

class SalaryRecord(Base):
    __tablename__ = "salary_records"

    id = Column(Integer, primary_key=True, index=True)
    staff_employee_id = Column(Integer, ForeignKey("staff_employees.id"), nullable=False)
    
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
    StaffEmployee_employee = relationship("StaffEmployee", back_populates="salary_records")

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
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
