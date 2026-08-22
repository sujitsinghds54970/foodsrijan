"""
Accounting Models for VaidyaVihar Diagnostic ERP

Expense tracking and accounting module:
- Expense categories
- Expense entries
- Income tracking
- Financial orders
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum


class ExpenseCategory(str, enum.Enum):
    """Expense category enumeration"""
    LABORATORY = "laboratory"
    SALARIES = "salaries"
    RENT = "rent"
    UTILITIES = "utilities"
    EQUIPMENT = "equipment"
    SUPPLIES = "supplies"
    MARKETING = "marketing"
    MAINTENANCE = "maintenance"
    INSURANCE = "insurance"
    PROFESSIONAL_FEES = "professional_fees"
    TRAVEL = "travel"
    COMMUNICATION = "communication"
    IT_EXPENSES = "it_expenses"
    MISCELLANEOUS = "miscellaneous"


class PaymentStatus(str, enum.Enum):
    """Payment status for expenses"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class ExpenseEntry(Base):
    """Expense entry model"""
    __tablename__ = "expense_entries"

    id = Column(Integer, primary_key=True, index=True)
    expense_date = Column(DateTime, default=datetime.utcnow)
    
    # Category
    category = Column(SQLEnum(ExpenseCategory), nullable=False)
    subcategory = Column(String, nullable=True)
    
    # Details
    description = Column(String, nullable=False)
    vendor_name = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True)
    
    # Amount
    amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)
    
    # Payment
    payment_mode = Column(String, default="cash")  # cash, card, bank_transfer, upi
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Status
    status = Column(String, default="pending")  # pending, approved, rejected, paid
    
    # References
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Approval
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Due date for payment
    due_date = Column(DateTime, nullable=True)
    paid_date = Column(DateTime, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Attachments (file paths)
    receipt_path = Column(String, nullable=True)
    invoice_path = Column(String, nullable=True)
    
    # Recurring expense
    is_recurring = Column(Boolean, default=False)
    recurring_frequency = Column(String, nullable=True)  # daily, weekly, monthly
    recurring_end_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch")
    staff = relationship("User", foreign_keys=[staff_id])
    approver = relationship("User", foreign_keys=[approved_by])


class IncomeEntry(Base):
    """Income entry model for tracking revenue"""
    __tablename__ = "income_entries"

    id = Column(Integer, primary_key=True, index=True)
    income_date = Column(DateTime, default=datetime.utcnow)
    
    # Category
    category = Column(String, nullable=False)  # lab_menu_items, packages, consultations, other
    subcategory = Column(String, nullable=True)
    
    # Details
    description = Column(String, nullable=False)
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    
    # Amount
    amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)
    
    # Payment
    payment_mode = Column(String, default="cash")
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PAID)
    
    # References
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Customer")
    invoice = relationship("Invoice")
    branch = relationship("Branch")


class CategoryBudget(Base):
    """Budget allocation for expense categories"""
    __tablename__ = "category_budgets"

    id = Column(Integer, primary_key=True, index=True)
    
    # Category
    category = Column(SQLEnum(ExpenseCategory), nullable=False)
    subcategory = Column(String, nullable=True)
    
    # Budget details
    budget_amount = Column(Float, nullable=False)
    spent_amount = Column(Float, default=0)
    
    # Period
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Branch
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Alerts
    alert_threshold_percent = Column(Integer, default=80)  # Alert when % spent
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch")


class FinancialSummary(Base):
    """Daily financial summary"""
    __tablename__ = "financial_summaries"

    id = Column(Integer, primary_key=True, index=True)
    
    # Date
    summary_date = Column(DateTime, nullable=False, unique=True)
    
    # Income
    total_income = Column(Float, default=0)
    income_count = Column(Integer, default=0)
    cash_income = Column(Float, default=0)
    card_income = Column(Float, default=0)
    upi_income = Column(Float, default=0)
    bank_income = Column(Float, default=0)
    
    # Expenses
    total_expenses = Column(Float, default=0)
    expense_count = Column(Integer, default=0)
    cash_expenses = Column(Float, default=0)
    card_expenses = Column(Float, default=0)
    bank_expenses = Column(Float, default=0)
    
    # Net
    net_profit = Column(Float, default=0)
    
    # Branch
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch")


class Account(Base):
    """Chart of accounts"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Account details
    account_code = Column(String, nullable=False, unique=True)
    account_name = Column(String, nullable=False)
    account_type = Column(String, nullable=False)  # asset, liability, income, expense
    account_group = Column(String, nullable=True)
    
    # Parent account for sub-accounts
    parent_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System accounts can't be deleted
    
    # Balance
    opening_balance = Column(Float, default=0)
    current_balance = Column(Float, default=0)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = relationship("Account", remote_side=[id])


class Transaction(Base):
    """General ledger transactions"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    
    # Transaction details
    transaction_type = Column(String, nullable=False)  # debit, credit
    transaction_mode = Column(String, nullable=False)  # journal, payment, receipt
    
    # Amount
    debit_amount = Column(Float, default=0)
    credit_amount = Column(Float, default=0)
    
    # References
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    reference_type = Column(String, nullable=True)  # expense, income, payment, etc.
    reference_id = Column(Integer, nullable=True)
    
    # Description
    description = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Branch
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("Account")
    branch = relationship("Branch")

