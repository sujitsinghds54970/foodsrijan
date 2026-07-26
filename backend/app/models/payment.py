"""
Payment Models for VaidyaVihar Diagnostic ERP

Enhanced payment tracking with support for:
- Razorpay integration
- PayU integration
- Multiple payment modes
- Invoice generation
- Payment status tracking
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum


class PaymentStatus(str, enum.Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMode(str, enum.Enum):
    """Payment mode enumeration"""
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    RAZORPAY = "razorpay"
    PAYU = "payu"
    WALLET = "wallet"
    INSURANCE = "insurance"


class PaymentGateway(str, enum.Enum):
    """Payment gateway enumeration"""
    RAZORPAY = "razorpay"
    PAYU = "payu"
    NONE = "none"


class Invoice(Base):
    """Invoice model for billing"""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Invoice details
    total_amount = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    final_amount = Column(Float, default=0)
    
    # Status
    status = Column(String, default="pending")  # pending, paid, partial, cancelled
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Dates
    invoice_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    paid_date = Column(DateTime, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)
    
    # Reference
    referred_by = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="invoices")
    branch = relationship("Branch")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    lab_results = relationship("LabResult", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    """Individual items in an invoice"""
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    
    # Item details
    item_type = Column(String, nullable=False)  # test, package, product, service
    item_name = Column(String, nullable=False)
    item_code = Column(String, nullable=True)
    
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Reference to test/product
    test_id = Column(Integer, nullable=True)
    product_id = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="items")


class Payment(Base):
    """Payment model for tracking all transactions"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Payment details
    amount = Column(Float, nullable=False)
    payment_mode = Column(SQLEnum(PaymentMode), default=PaymentMode.CASH)
    payment_gateway = Column(SQLEnum(PaymentGateway), default=PaymentGateway.NONE)
    
    # Gateway specific
    gateway_transaction_id = Column(String, nullable=True, index=True)
    gateway_order_id = Column(String, nullable=True)
    gateway_payment_id = Column(String, nullable=True)
    gateway_signature = Column(String, nullable=True)
    
    # Status
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Payment reference
    transaction_id = Column(String, unique=True, nullable=False, index=True)
    reference_number = Column(String, nullable=True)
    
    # Card details (for record only, never store full card numbers)
    card_last_4 = Column(String, nullable=True)
    card_type = Column(String, nullable=True)
    
    # UPI details
    upi_transaction_id = Column(String, nullable=True)
    upi_id = Column(String, nullable=True)
    
    # Bank transfer details
    bank_name = Column(String, nullable=True)
    cheque_number = Column(String, nullable=True)
    transaction_date = Column(DateTime, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Dates
    payment_date = Column(DateTime, default=datetime.utcnow)
    
    # Refund details
    refund_amount = Column(Float, default=0)
    refund_date = Column(DateTime, nullable=True)
    refund_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
    patient = relationship("Patient")
    branch = relationship("Branch")


class Refund(Base):
    """Refund tracking model"""
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    
    # Refund details
    refund_amount = Column(Float, nullable=False)
    refund_reason = Column(Text, nullable=True)
    refund_mode = Column(String, default="original")  # original, bank, cash
    
    # Gateway specific
    gateway_refund_id = Column(String, nullable=True)
    gateway_response = Column(Text, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, processed, failed
    
    # Dates
    requested_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Admin notes
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    payment = relationship("Payment")
    approver = relationship("User")


class PaymentSettings(Base):
    """Payment gateway configuration"""
    __tablename__ = "payment_settings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Gateway settings
    gateway = Column(SQLEnum(PaymentGateway), nullable=False)
    
    # Razorpay settings
    razorpay_key_id = Column(String, nullable=True)
    razorpay_key_secret = Column(String, nullable=True)
    razorpay_webhook_secret = Column(String, nullable=True)
    
    # PayU settings
    payu_merchant_key = Column(String, nullable=True)
    payu_merchant_salt = Column(String, nullable=True)
    payu_auth_header = Column(String, nullable=True)
    payu_mode = Column(String, default="test")  # test, production
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Default settings
    is_default = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentLink(Base):
    """Payment link for sharing with patients"""
    __tablename__ = "payment_links"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    
    # Link details
    link_id = Column(String, unique=True, nullable=False, index=True)
    short_url = Column(String, nullable=True)
    payment_url = Column(String, nullable=False)
    
    # Amount
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    
    # Expiry
    expires_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String, default="active")  # active, expired, used
    times_viewed = Column(Integer, default=0)
    times_paid = Column(Integer, default=0)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice")


class InsuranceClaim(Base):
    """Insurance claim tracking"""
    __tablename__ = "insurance_claims"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    
    # Insurance details
    insurance_provider = Column(String, nullable=True)
    policy_number = Column(String, nullable=True)
    member_id = Column(String, nullable=True)
    
    # Claim details
    claim_amount = Column(Float, default=0)
    approved_amount = Column(Float, default=0)
    settled_amount = Column(Float, default=0)
    
    # Status
    status = Column(String, default="pending")  # pending, submitted, approved, rejected, settled
    claim_number = Column(String, nullable=True)
    
    # Dates
    claim_date = Column(DateTime, default=datetime.utcnow)
    submitted_date = Column(DateTime, nullable=True)
    settlement_date = Column(DateTime, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient")
    invoice = relationship("Invoice")


class ReconciliationLog(Base):
    """Audit trail for reconciliation runs"""
    __tablename__ = "reconciliation_logs"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    triggered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    run_type = Column(String, default="bulk")
    total_transactions = Column(Integer, default=0)
    reconciled_count = Column(Integer, default=0)
    pending_count = Column(Integer, default=0)
    discrepancy_count = Column(Integer, default=0)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    branch = relationship("Branch")
    triggered_by = relationship("User")


class PaymentReminder(Base):
    """Reminder audit trail for SMS/email payment nudges"""
    __tablename__ = "payment_reminders"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    reminder_type = Column(String, default="due_24h")
    channel = Column(String, nullable=False)
    status = Column(String, default="queued")
    scheduled_for = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    branch = relationship("Branch")
    patient = relationship("Patient")
    invoice = relationship("Invoice")
