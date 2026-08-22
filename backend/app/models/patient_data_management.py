from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Date,
    Boolean,
    Numeric,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    BRANCH_ADMIN = "branch_admin"
    STAFF = "staff"


class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"


class PaymentMode(str, Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class DeliveryMode(str, Enum):
    PRINT = "print"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PORTAL = "portal"
    OTHER = "other"


# Import Branch from main models file to avoid duplicate class definition
from app.models import Branch


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_branch_username", "branch_id", "username", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.STAFF, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="users")


class Staff(Base):
    __tablename__ = "staff"
    __table_args__ = (
        UniqueConstraint("branch_id", "name", name="uq_staff_branch_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialization: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="staff")
    visits: Mapped[List["CustomerVisit"]] = relationship("CustomerVisit", back_populates="doctor")


class MenuItem(Base):
    __tablename__ = "menu_items"
    __table_args__ = (
        UniqueConstraint("branch_id", "name", name="uq_menu_items_branch_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="menu_items")
    panel_links: Mapped[List["PanelMenuItem"]] = relationship("PanelMenuItem", back_populates="test")


class PanelMenuItem(Base):
    __tablename__ = "panel_menu_items"
    __table_args__ = (
        UniqueConstraint("panel_name", "test_id", name="uq_panel_menu_items_panel_test"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    panel_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    test: Mapped["MenuItem"] = relationship("MenuItem", back_populates="panel_links")


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("branch_id", "name", "phone", name="uq_customers_branch_name_phone"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    patient_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referred_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="customers")
    visits: Mapped[List["CustomerVisit"]] = relationship("CustomerVisit", back_populates="patient")


class CustomerVisit(Base):
    __tablename__ = "patient_visits"
    __table_args__ = (
        Index("ix_patient_visits_branch_visit_date", "branch_id", "visit_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    doctor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("staff.id"), nullable=True, index=True)

    receipt_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    test_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus), default=PaymentStatus.UNPAID, nullable=False
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="visits")
    patient: Mapped["Customer"] = relationship("Customer", back_populates="visits")
    doctor: Mapped[Optional["Staff"]] = relationship("Staff", back_populates="visits")
    menu_items: Mapped[List["VisitMenuItem"]] = relationship(
        "VisitMenuItem", back_populates="visit", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="visit", cascade="all, delete-orphan"
    )
    deliveries: Mapped[List["OrderDelivery"]] = relationship(
        "OrderDelivery", back_populates="visit", cascade="all, delete-orphan"
    )


class VisitMenuItem(Base):
    __tablename__ = "visit_menu_items"
    __table_args__ = (
        UniqueConstraint("visit_id", "test_id", name="uq_visit_menu_items_visit_test"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("patient_visits.id"), nullable=False, index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False, index=True)
    fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # historical fee snapshot
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    visit: Mapped["CustomerVisit"] = relationship("CustomerVisit", back_populates="menu_items")
    test: Mapped["MenuItem"] = relationship("MenuItem")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_visit_created_at", "visit_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("patient_visits.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    mode: Mapped[PaymentMode] = mapped_column(SAEnum(PaymentMode), default=PaymentMode.CASH, nullable=False)
    reference_no: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    visit: Mapped["CustomerVisit"] = relationship("CustomerVisit", back_populates="payments")


class OrderDelivery(Base):
    __tablename__ = "report_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("patient_visits.id"), nullable=False, index=True)
    delivered_to: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    mode: Mapped[DeliveryMode] = mapped_column(SAEnum(DeliveryMode), nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    visit: Mapped["CustomerVisit"] = relationship("CustomerVisit", back_populates="deliveries")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_table_record", "table_name", "record_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_name: Mapped[str] = mapped_column(String(80), nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


