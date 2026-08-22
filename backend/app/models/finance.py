from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BranchAccount(Base):
    __tablename__ = "branch_accounts"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False, default="Primary Account")
    opening_balance = Column(DECIMAL(12, 2), nullable=False, default=0)
    current_balance = Column(DECIMAL(12, 2), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    branch = relationship("Branch", back_populates="branch_accounts")


class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    type = Column(String(20), nullable=False, index=True)  # revenue, expense, transfer
    amount = Column(DECIMAL(12, 2), nullable=False)
    description = Column(Text, nullable=True)
    reference_id = Column(String(120), nullable=True, index=True)
    category = Column(String(100), nullable=True, index=True)
    payment_method = Column(String(30), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    branch = relationship("Branch")
    creator = relationship("User")


class FinanceInvoice(Base):
    __tablename__ = "finance_invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), nullable=False, unique=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    patient_name = Column(String(200), nullable=True)
    date = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    total_amount = Column(DECIMAL(12, 2), nullable=False)
    tax_amount = Column(DECIMAL(12, 2), nullable=False, default=0)
    gst_rate = Column(DECIMAL(5, 2), nullable=False, default=0)
    status = Column(String(20), nullable=False, default="pending", index=True)
    due_date = Column(DateTime, nullable=True)
    pdf_url = Column(String(500), nullable=True)
    reference_id = Column(String(120), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    branch = relationship("Branch")
    patient = relationship("Customer")
    creator = relationship("User")


class FinanceExpense(Base):
    __tablename__ = "finance_expenses"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    category = Column(String(100), nullable=False, index=True)
    amount = Column(DECIMAL(12, 2), nullable=False)
    description = Column(Text, nullable=True)
    attachment_url = Column(String(500), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_method = Column(String(30), nullable=True)
    reference_id = Column(String(120), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    branch = relationship("Branch")
    approver = relationship("User", foreign_keys=[approved_by])
    creator = relationship("User", foreign_keys=[created_by])
