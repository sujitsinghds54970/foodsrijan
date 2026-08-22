"""
LIS (Laboratory Information System) Models for VaidyaVihar Diagnostic ERP

Enhanced lab testing with:
- MenuItem ordering workflow
- Sample collection tracking
- Result entry and validation
- Order generation
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum


class MenuItemStatus(str, enum.Enum):
    """MenuItem status enumeration"""
    ORDERED = "ordered"
    SAMPLE_COLLECTED = "sample_collected"
    SAMPLE_RECEIVED = "sample_received"
    IN_PROGRESS = "in_progress"
    RESULT_ENTERED = "result_entered"
    VERIFIED = "verified"
    REPORT_GENERATED = "report_generated"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class SampleType(str, enum.Enum):
    """Sample type enumeration"""
    BLOOD = "blood"
    URINE = "urine"
    STOOL = "stool"
    SPUTUM = "sputum"
    SWAB = "swab"
    CSF = "csf"
    PLEURAL_FLUID = "pleural_fluid"
    ASCITIC_FLUID = "ascitic_fluid"
    SEMEN = "semen"
    BIOPSY = "biopsy"
    OTHER = "other"


class ResultFlag(str, enum.Enum):
    """Result flag for abnormal values"""
    NORMAL = "normal"
    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"
    ABNORMAL = "abnormal"


class MenuItemCategory(str, enum.Enum):
    """MenuItem category"""
    HEMATOLOGY = "hematology"
    BIOCHEMISTRY = "biochemistry"
    MICROBIOLOGY = "microbiology"
    SEROLOGY = "serology"
    PATHOLOGY = "pathology"
    RADIOLOGY = "radiology"
    CARDIOLOGY = "cardiology"
    ENDOCRINOLOGY = "endocrinology"
    IMMUNOLOGY = "immunology"
    MOLECULAR = "molecular"
    OTHER = "other"


class LabMenuItemMaster(Base):
    """Master list of available lab menu_items"""
    __tablename__ = "lab_test_master"

    id = Column(Integer, primary_key=True, index=True)
    test_code = Column(String, nullable=False, unique=True)
    test_name = Column(String, nullable=False)
    test_name_hindi = Column(String, nullable=True)
    
    # Category
    category = Column(SQLEnum(MenuItemCategory), nullable=False)
    subcategory = Column(String, nullable=True)
    
    # Sample requirements
    sample_type = Column(SQLEnum(SampleType), nullable=False)
    sample_volume = Column(String, nullable=True)
    sample_container = Column(String, nullable=True)
    sample_instructions = Column(Text, nullable=True)
    
    # Pricing
    base_price = Column(Float, default=0)
    discounted_price = Column(Float, default=0)
    gst_percent = Column(Float, default=18)
    
    # Timing
    turnaround_time_hours = Column(Integer, default=24)
    is_urgent_available = Column(Boolean, default=True)
    urgent_additional_charge = Column(Float, default=0)
    
    # Parameters
    parameters = Column(JSON, nullable=True)  # List of parameters for this test
    
    # Reference ranges
    reference_ranges = Column(JSON, nullable=True)  # Age/gender specific ranges
    
    # Methods
    method = Column(String, nullable=True)
    equipment = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_package = Column(Boolean, default=False)
    package_menu_items = Column(JSON, nullable=True)  # List of test IDs if package
    
    # Pre-test requirements
    fasting_required = Column(Boolean, default=False)
    fasting_hours = Column(Integer, default=0)
    special_instructions = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MenuItemOrder(Base):
    """MenuItem order for a patient"""
    __tablename__ = "test_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, nullable=False, unique=True, index=True)
    
    # Customer
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Visit
    visit_id = Column(Integer, nullable=True)  # Link to appointment/visit
    
    # Ordering
    referred_by = Column(String, nullable=True)  # Staff name
    referred_by_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    
    # Priority
    priority = Column(String, default="routine")  # routine, urgent, emergency
    
    # Status
    status = Column(SQLEnum(MenuItemStatus), default=MenuItemStatus.ORDERED)
    
    # Financial
    total_amount = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    final_amount = Column(Float, default=0)
    payment_status = Column(String, default="pending")  # pending, partial, paid
    
    # Dates
    order_date = Column(DateTime, default=datetime.utcnow)
    sample_collection_date = Column(DateTime, nullable=True)
    sample_received_date = Column(DateTime, nullable=True)
    expected_delivery_date = Column(DateTime, nullable=True)
    delivery_date = Column(DateTime, nullable=True)
    
    # Branch
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Notes
    clinical_history = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Customer")
    referred_doctor = relationship("Staff")
    branch = relationship("Branch")
    menu_items = relationship("MenuItemOrderItem", back_populates="order", cascade="all, delete-orphan")


class MenuItemOrderItem(Base):
    """Individual test items in an order"""
    __tablename__ = "test_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("test_orders.id"), nullable=False)
    test_master_id = Column(Integer, ForeignKey("lab_test_master.id"), nullable=False)
    
    # MenuItem details
    test_name = Column(String, nullable=False)
    test_code = Column(String, nullable=False)
    
    # Pricing
    price = Column(Float, default=0)
    discount = Column(Float, default=0)
    final_price = Column(Float, default=0)
    
    # Status
    status = Column(SQLEnum(MenuItemStatus), default=MenuItemStatus.ORDERED)
    
    # Sample
    sample_type = Column(SQLEnum(SampleType), nullable=True)
    sample_id = Column(String, nullable=True)  # Barcode/sample ID
    
    # Results
    result_entered_at = Column(DateTime, nullable=True)
    result_verified_at = Column(DateTime, nullable=True)
    
    # Technician
    sample_collected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    result_entered_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    result_verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order = relationship("MenuItemOrder", back_populates="menu_items")
    test_master = relationship("LabMenuItemMaster")
    sample_collector = relationship("User", foreign_keys=[sample_collected_by])
    result_enterer = relationship("User", foreign_keys=[result_entered_by])
    result_verifier = relationship("User", foreign_keys=[result_verified_by])


class Sample(Base):
    """Sample tracking"""
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, index=True)
    sample_id = Column(String, nullable=False, unique=True, index=True)  # Barcode
    
    # Order
    order_id = Column(Integer, ForeignKey("test_orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("test_order_items.id"), nullable=True)
    
    # Sample details
    sample_type = Column(SQLEnum(SampleType), nullable=False)
    sample_volume = Column(String, nullable=True)
    
    # Collection
    collected_at = Column(DateTime, nullable=True)
    collected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    collection_notes = Column(Text, nullable=True)
    
    # Reception
    received_at = Column(DateTime, nullable=True)
    received_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reception_condition = Column(String, nullable=True)  # good, hemolyzed, lipemic, etc.
    
    # Storage
    storage_location = Column(String, nullable=True)
    storage_condition = Column(String, nullable=True)  # room_temp, refrigerated, frozen
    
    # Processing
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Status
    status = Column(String, default="collected")  # collected, received, processed, disposed
    
    # Disposal
    disposed_at = Column(DateTime, nullable=True)
    disposal_method = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order = relationship("MenuItemOrder")
    order_item = relationship("MenuItemOrderItem")
    collector = relationship("User", foreign_keys=[collected_by])
    receiver = relationship("User", foreign_keys=[received_by])
    processor = relationship("User", foreign_keys=[processed_by])


class MenuItemResult(Base):
    """MenuItem result entries"""
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    order_item_id = Column(Integer, ForeignKey("test_order_items.id"), nullable=False)
    
    # Parameter
    parameter_name = Column(String, nullable=False)
    parameter_code = Column(String, nullable=True)
    
    # Value
    result_value = Column(String, nullable=True)  # Can be string for non-numeric
    numeric_value = Column(Float, nullable=True)
    
    # Unit
    unit = Column(String, nullable=True)
    
    # Flag
    flag = Column(SQLEnum(ResultFlag), default=ResultFlag.NORMAL)
    
    # Reference range
    reference_range = Column(String, nullable=True)
    reference_range_low = Column(Float, nullable=True)
    reference_range_high = Column(Float, nullable=True)
    
    # Method
    method = Column(String, nullable=True)
    equipment = Column(String, nullable=True)
    
    # Status
    is_verified = Column(Boolean, default=False)
    verification_notes = Column(Text, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    abnormal_notes = Column(Text, nullable=True)
    
    # Timestamps
    entered_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order_item = relationship("MenuItemOrderItem")


class LISOrderTemplate(Base):
    """Order templates for different test types"""
    __tablename__ = "lis_report_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String, nullable=False)
    
    # Associated menu_items
    test_category = Column(SQLEnum(MenuItemCategory), nullable=False)
    
    # Template content (JSON structure)
    template_content = Column(JSON, nullable=False)
    
    # Layout
    header_content = Column(JSON, nullable=True)
    footer_content = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GeneratedOrder(Base):
    """Generated orders"""
    __tablename__ = "generated_orders"

    id = Column(Integer, primary_key=True, index=True)
    report_number = Column(String, nullable=False, unique=True, index=True)
    
    # Order
    order_id = Column(Integer, ForeignKey("test_orders.id"), nullable=False)
    
    # Order details
    report_type = Column(String, nullable=False)
    template_id = Column(Integer, ForeignKey("lis_report_templates.id"), nullable=True)
    
    # File
    file_path = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Status
    status = Column(String, default="generated")  # generated, printed, delivered
    
    # Delivery
    delivered_at = Column(DateTime, nullable=True)
    delivered_via = Column(String, nullable=True)  # print, email, whatsapp, portal
    
    # Sign-off
    authorized_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    authorized_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order = relationship("MenuItemOrder")
    template = relationship("LISOrderTemplate")
    authorizer = relationship("User")


class QualityControl(Base):
    """Quality control tracking"""
    __tablename__ = "quality_controls"

    id = Column(Integer, primary_key=True, index=True)
    
    # Control details
    control_name = Column(String, nullable=False)
    control_lot_number = Column(String, nullable=True)
    control_expiry_date = Column(DateTime, nullable=True)
    
    # MenuItem
    test_master_id = Column(Integer, ForeignKey("lab_test_master.id"), nullable=True)
    
    # Values
    target_value = Column(Float, nullable=True)
    target_range_low = Column(Float, nullable=True)
    target_range_high = Column(Float, nullable=True)
    
    # Run
    run_date = Column(DateTime, default=datetime.utcnow)
    run_value = Column(Float, nullable=True)
    deviation = Column(Float, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # passed, failed, warning
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Technician
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    test_master = relationship("LabMenuItemMaster")
    performer = relationship("User", foreign_keys=[performed_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class InstrumentCalibration(Base):
    """Equipment calibration tracking"""
    __tablename__ = "instrument_calibrations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Instrument
    instrument_name = Column(String, nullable=False)
    instrument_id = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    
    # Calibration
    calibration_date = Column(DateTime, default=datetime.utcnow)
    next_calibration_date = Column(DateTime, nullable=True)
    
    # Results
    calibration_status = Column(String, default="pending")  # passed, failed
    calibration_values = Column(JSON, nullable=True)
    
    # Technician
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    performer = relationship("User")

