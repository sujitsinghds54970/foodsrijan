from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class MenuItemCatalog(Base):
    __tablename__ = "branch_lis_test_catalog"
    __table_args__ = (UniqueConstraint("branch_id", "test_code", name="uq_branch_lis_test_code"),)

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    test_code = Column(String(60), nullable=False)
    test_name = Column(String(200), nullable=False)
    department = Column(String(80), nullable=False, default="General")
    sample_type = Column(String(80), nullable=False, default="Blood")
    turnaround_minutes = Column(Integer, nullable=False, default=1440)
    normal_range_json = Column(JSON, nullable=True)
    critical_threshold_json = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MenuItemPanel(Base):
    __tablename__ = "branch_lis_test_panels"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    panel_name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    menu_items_json = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrderQueue(Base):
    __tablename__ = "branch_lis_order_queue"
    __table_args__ = (UniqueConstraint("branch_id", "daily_entry_id", name="uq_branch_lis_daily_entry"),)

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    daily_entry_id = Column(Integer, ForeignKey("daily_entries_module.id"), nullable=True, index=True)
    source = Column(String(30), nullable=False, default="manual")
    order_number = Column(String(80), nullable=False, unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    patient_name = Column(String(200), nullable=False)
    patient_code = Column(String(80), nullable=True, index=True)
    doctor_name = Column(String(200), nullable=True)
    priority = Column(String(20), nullable=False, default="Routine")
    status = Column(String(30), nullable=False, default="Registered")
    expected_tat_minutes = Column(Integer, nullable=False, default=1440)
    due_at = Column(DateTime, nullable=True)
    menu_items_json = Column(JSON, nullable=False, default=list)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    samples = relationship("app.models.branch_lis.Sample", back_populates="order", cascade="all, delete-orphan")


class Sample(Base):
    __tablename__ = "branch_lis_samples"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("branch_lis_order_queue.id"), nullable=False, index=True)
    sample_code = Column(String(80), nullable=False, unique=True, index=True)
    barcode_value = Column(String(160), nullable=False, unique=True, index=True)
    barcode_image_base64 = Column(Text, nullable=True)
    sample_type = Column(String(80), nullable=False, default="Blood")
    department = Column(String(80), nullable=False, default="General")
    analyzer_name = Column(String(120), nullable=True)
    storage_location = Column(String(120), nullable=True)
    status = Column(String(30), nullable=False, default="Registered")
    rejection_reason = Column(Text, nullable=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    reported_at = Column(DateTime, nullable=True)
    expected_completion_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("app.models.branch_lis.OrderQueue", back_populates="samples")


class Worklist(Base):
    __tablename__ = "branch_lis_worklists"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    worklist_code = Column(String(80), nullable=False, unique=True, index=True)
    department = Column(String(80), nullable=False)
    analyzer_name = Column(String(120), nullable=True)
    status = Column(String(30), nullable=False, default="Open")
    sample_ids_json = Column(JSON, nullable=False, default=list)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InstrumentCalibration(Base):
    __tablename__ = "branch_lis_instrument_calibrations"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    analyzer_name = Column(String(120), nullable=False, index=True)
    calibration_status = Column(String(30), nullable=False, default="Due")
    calibrated_at = Column(DateTime, nullable=True)
    next_due_at = Column(DateTime, nullable=True)
    maintenance_notes = Column(Text, nullable=True)
    maintenance_history_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QCResult(Base):
    __tablename__ = "branch_lis_qc_results"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    sample_id = Column(Integer, ForeignKey("branch_lis_samples.id"), nullable=True, index=True)
    analyzer_name = Column(String(120), nullable=True)
    test_code = Column(String(60), nullable=True)
    qc_status = Column(String(30), nullable=False, default="Passed")
    failure_reason = Column(Text, nullable=True)
    hil_flag = Column(Boolean, nullable=False, default=False)
    delta_check_flag = Column(Boolean, nullable=False, default=False)
    critical_value_flag = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class WestgardRule(Base):
    __tablename__ = "branch_lis_westgard_rules"
    __table_args__ = (UniqueConstraint("branch_id", "rule_code", name="uq_branch_lis_westgard_rule_code"),)

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    rule_code = Column(String(20), nullable=False)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="Warning")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProficiencyMenuItemRun(Base):
    __tablename__ = "branch_lis_proficiency_test_runs"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    program_name = Column(String(160), nullable=False)
    cycle_name = Column(String(120), nullable=False)
    department = Column(String(80), nullable=False, default="General")
    participation_status = Column(String(30), nullable=False, default="Planned")
    score = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LISOrderArchive(Base):
    __tablename__ = "branch_lis_report_archive"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("branch_lis_order_queue.id"), nullable=False, index=True)
    sample_id = Column(Integer, ForeignKey("branch_lis_samples.id"), nullable=True, index=True)
    report_number = Column(String(80), nullable=False, unique=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    template_name = Column(String(160), nullable=False, default="Default LIS Template")
    signed_by = Column(String(160), nullable=True)
    signed_at = Column(DateTime, nullable=True)
    channels_json = Column(JSON, nullable=True)
    report_payload_json = Column(JSON, nullable=True)
    report_pdf_base64 = Column(Text, nullable=True)
    status = Column(String(40), nullable=False, default="Generated")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
