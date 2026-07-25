from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, Date, DateTime, DECIMAL, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class InventoryDepartment(str, enum.Enum):
    XRAY = "X-Ray"
    SONOGRAPHY = "Sonography"
    PATHOLOGY = "Pathology"
    CT_SCAN = "CT Scan"
    MRI = "MRI"
    OTHER = "Other Consumables"


class Supplier(Base):
    __tablename__ = "inventory_suppliers"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    contact_person = Column(String(200), nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    gstin = Column(String(30), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class InventoryItemV2(Base):
    __tablename__ = "inventory_items_v2"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    department = Column(String(30), nullable=False, index=True)
    item_name = Column(String(255), nullable=False, index=True)
    category = Column(String(120), nullable=True, index=True)
    current_qty = Column(Float, nullable=False, default=0)
    min_threshold = Column(Float, nullable=False, default=0)
    expiry_date = Column(Date, nullable=True)
    unit_cost = Column(DECIMAL(12, 2), nullable=False, default=0)
    unit = Column(String(50), nullable=False, default="units")
    supplier_id = Column(Integer, ForeignKey("inventory_suppliers.id"), nullable=True, index=True)
    barcode_number = Column(String(120), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    supplier = relationship(Supplier)


class InventoryEquipment(Base):
    __tablename__ = "inventory_equipment"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    department = Column(String(30), nullable=False, index=True)
    machine_name = Column(String(200), nullable=False)
    brand_model = Column(String(200), nullable=True)
    serial_number = Column(String(150), nullable=True, index=True)
    purchase_date = Column(Date, nullable=True)
    warranty_end_date = Column(Date, nullable=True)
    amc_company = Column(String(200), nullable=True)
    dealer_contact = Column(String(100), nullable=True)
    last_service_date = Column(Date, nullable=True)
    next_service_due_date = Column(Date, nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class EquipmentServiceLog(Base):
    __tablename__ = "equipment_service_logs"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("inventory_equipment.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    service_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())


class InventoryConsumptionHistory(Base):
    __tablename__ = "inventory_consumption_history"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items_v2.id"), nullable=False, index=True)
    daily_entry_id = Column(Integer, ForeignKey("daily_entries_module.id"), nullable=True, index=True)
    patient_identifier = Column(String(60), nullable=True, index=True)
    test_name = Column(String(500), nullable=True)
    quantity = Column(Float, nullable=False, default=0)
    consumed_on = Column(DateTime, nullable=False, default=func.now(), index=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    item = relationship(InventoryItemV2)


class InventoryStockAudit(Base):
    __tablename__ = "inventory_stock_audits"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items_v2.id"), nullable=False, index=True)
    expected_qty = Column(Float, nullable=False)
    physical_qty = Column(Float, nullable=False)
    discrepancy = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    audited_on = Column(DateTime, nullable=False, default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)


class InventoryStockMovement(Base):
    __tablename__ = "inventory_stock_movements_v2"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items_v2.id"), nullable=False, index=True)
    movement_type = Column(String(30), nullable=False)  # add_stock, consume, audit_adjustment
    quantity = Column(Float, nullable=False)
    previous_qty = Column(Float, nullable=False)
    new_qty = Column(Float, nullable=False)
    meta = Column(JSON, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    item = relationship(InventoryItemV2)
