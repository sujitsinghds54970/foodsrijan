from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, DECIMAL, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class PayrollRunStatus(str, enum.Enum):
    DRAFT = "Draft"
    READY = "Ready"
    APPROVED = "Approved"
    LOCKED = "Locked"


class AdvanceStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    DISBURSED = "Disbursed"


class ReimbursementStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PAID = "Paid"


class PayrollDisputeStatus(str, enum.Enum):
    OPEN = "Open"
    RESOLVED = "Resolved"


class EarningHead(Base):
    __tablename__ = "earning_heads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    is_fixed = Column(Boolean, nullable=False, default=True)
    taxable = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SalaryGrade(Base):
    __tablename__ = "salary_grades"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(120), nullable=False, index=True)
    grade_level = Column(Integer, nullable=False, index=True)
    base_salary = Column(DECIMAL(12, 2), nullable=False, default=0)
    min_salary = Column(DECIMAL(12, 2), nullable=False, default=0)
    max_salary = Column(DECIMAL(12, 2), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class StaffSalaryConfig(Base):
    __tablename__ = "staff_salary_configs"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False, unique=True, index=True)
    grade_id = Column(Integer, ForeignKey("salary_grades.id"), nullable=False)
    bank_account_number = Column(String(64), nullable=True)
    ifsc = Column(String(20), nullable=True)
    upi_id = Column(String(100), nullable=True)
    date_of_joining = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")
    grade = relationship("SalaryGrade")


class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    status = Column(SQLEnum(PayrollRunStatus), nullable=False, default=PayrollRunStatus.DRAFT)
    total_gross_pay = Column(DECIMAL(14, 2), nullable=False, default=0)
    total_deductions = Column(DECIMAL(14, 2), nullable=False, default=0)
    total_net_pay = Column(DECIMAL(14, 2), nullable=False, default=0)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    branch = relationship("Branch")
    approver = relationship("User", foreign_keys=[approved_by])
    transactions = relationship("PayrollTransaction", back_populates="payroll_run", cascade="all, delete-orphan")
    locks = relationship("PayrollLock", back_populates="payroll_run", cascade="all, delete-orphan")


class PayrollTransaction(Base):
    __tablename__ = "payroll_transactions"

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False, index=True)
    base_salary = Column(DECIMAL(12, 2), nullable=False, default=0)
    overtime_hours = Column(DECIMAL(8, 2), nullable=False, default=0)
    lop_days = Column(DECIMAL(8, 2), nullable=False, default=0)
    incentive_amount = Column(DECIMAL(12, 2), nullable=False, default=0)
    reimbursement_amount = Column(DECIMAL(12, 2), nullable=False, default=0)
    total_deductions = Column(DECIMAL(12, 2), nullable=False, default=0)
    net_pay = Column(DECIMAL(12, 2), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    payroll_run = relationship("PayrollRun", back_populates="transactions")
    staff_profile = relationship("StaffProfile")


class AdvanceRequest(Base):
    __tablename__ = "advance_requests"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False, index=True)
    amount = Column(DECIMAL(12, 2), nullable=False)
    reason = Column(Text, nullable=True)
    tenure_months = Column(Integer, nullable=False, default=1)
    repaid_months = Column(Integer, nullable=False, default=0)
    status = Column(SQLEnum(AdvanceStatus), nullable=False, default=AdvanceStatus.PENDING)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")
    approver = relationship("User", foreign_keys=[approved_by])


class ReimbursementClaim(Base):
    __tablename__ = "reimbursement_claims"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False, index=True)
    category = Column(String(60), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    file_url = Column(String(500), nullable=True)
    status = Column(SQLEnum(ReimbursementStatus), nullable=False, default=ReimbursementStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")


class PayrollLock(Base):
    __tablename__ = "payroll_locks"

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=False, index=True)
    unlocked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    unlock_reason = Column(Text, nullable=True)
    unlocked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    payroll_run = relationship("PayrollRun", back_populates="locks")
    unlocker = relationship("User", foreign_keys=[unlocked_by])


class StaffTaxDeclaration(Base):
    __tablename__ = "staff_tax_declarations"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False, unique=True, index=True)
    declaration_year = Column(Integer, nullable=False)
    section_80c = Column(DECIMAL(12, 2), nullable=False, default=0)
    medical = Column(DECIMAL(12, 2), nullable=False, default=0)
    rent_allowance = Column(DECIMAL(12, 2), nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    staff_profile = relationship("StaffProfile")


class PayrollDispute(Base):
    __tablename__ = "payroll_disputes"

    id = Column(Integer, primary_key=True, index=True)
    payroll_transaction_id = Column(Integer, ForeignKey("payroll_transactions.id"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    status = Column(SQLEnum(PayrollDisputeStatus), nullable=False, default=PayrollDisputeStatus.OPEN)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    payroll_transaction = relationship("PayrollTransaction")
    staff_profile = relationship("StaffProfile")
