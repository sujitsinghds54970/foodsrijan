"""
Daily Entry Module Models
Branch-scoped daily patient entries and expenses
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, DECIMAL, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class PaymentMethod(str, enum.Enum):
    CASH = "Cash"
    UPI = "UPI"
    QR = "QR"
    CARD = "Card"

class TaxPercent(float, enum.Enum):
    ZERO = 0
    FIVE = 5
    TWELVE = 12
    EIGHTEEN = 18

class DailyEntryModule(Base):
    __tablename__ = "daily_entries_module"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    
    # Auto-generated fields
    auto_patient_id = Column(String(50), unique=True, nullable=False, index=True)  # PAT-YYYYMMDD-XXX
    auto_entry_datetime = Column(DateTime, default=func.now(), nullable=False)
    
    # Patient Information
    patient_name = Column(String(200), nullable=False, index=True)
    age = Column(String(20), nullable=True)
    mobile = Column(String(15), nullable=False)
    address = Column(Text, nullable=False)
    
    # Doctor Information
    referred_doctor = Column(String(200), nullable=True, index=True)
    
    # Test Information
    test_name = Column(String(500), nullable=False, index=True)
    
    # Report Management
    report_pdf_url = Column(String(500), nullable=True)
    status = Column(String(20), default="Pending")  # Pending, Completed
    
    # Financial Information
    fee_amount = Column(DECIMAL(10, 2), nullable=False)
    tax_percent = Column(Float, default=0)  # 0, 5, 12, 18
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    
    # Payment Information
    payment_method = Column(String(20), nullable=False)  # Cash, UPI, QR, Card
    upi_id = Column(String(100), nullable=True, index=True)
    is_paid = Column(Boolean, default=True)
    paid_at = Column(DateTime, nullable=True)
    bill_pdf_url = Column(String(500), nullable=True)
    
    # Additional Information
    remarks = Column(Text, nullable=True)
    consumed_inventory_items = Column(JSON, nullable=True)
    
    # Audit fields
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    branch = relationship("Branch", foreign_keys=[branch_id])
    creator = relationship("User", foreign_keys=[created_by])


class DailyExpense(Base):
    __tablename__ = "daily_expenses_module"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    
    # Expense Details
    entry_date = Column(DateTime, default=func.now(), nullable=False, index=True)
    expense_item = Column(String(200), nullable=False)
    cost = Column(DECIMAL(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    
    # Audit fields
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    branch = relationship("Branch", foreign_keys=[branch_id])
    creator = relationship("User", foreign_keys=[created_by])
