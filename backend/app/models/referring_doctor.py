from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ReferringDoctor(Base):
    __tablename__ = "referring_doctors"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)

    # Personal
    full_name = Column(String(200), nullable=False, index=True)
    mobile = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True, index=True)

    # Professional
    specialization = Column(String(100), nullable=True, index=True)
    degree = Column(String(120), nullable=True)
    hospital_clinic_affiliation = Column(String(255), nullable=True)
    years_of_experience = Column(Integer, nullable=True)

    # Financial
    bank_account_number = Column(String(100), nullable=True)
    ifsc_code = Column(String(30), nullable=True)
    upi_id = Column(String(120), nullable=True)
    commission_percentage = Column(Float, nullable=False, default=0.0)

    # Optional map support
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Optional self-service auth (future scope)
    portal_username = Column(String(120), nullable=True, unique=True)
    portal_password_hash = Column(String(255), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    branch = relationship("Branch")
    creator = relationship("User")
    referral_logs = relationship("ReferralLog", back_populates="doctor", cascade="all, delete-orphan")


class ReferralLog(Base):
    __tablename__ = "referral_logs"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("referring_doctors.id"), nullable=False, index=True)

    patient_name = Column(String(200), nullable=False)
    patient_mobile = Column(String(20), nullable=True)
    referred_on = Column(DateTime, nullable=False, default=func.now(), index=True)
    revenue_amount = Column(DECIMAL(12, 2), nullable=False, default=0)
    report_sent = Column(Boolean, nullable=False, default=False)
    report_due_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    doctor = relationship("ReferringDoctor", back_populates="referral_logs")
    branch = relationship("Branch")
    creator = relationship("User")


class DoctorShareLink(Base):
    __tablename__ = "doctor_share_links"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("referring_doctors.id"), nullable=False, index=True)

    token = Column(String(64), nullable=False, unique=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(120), nullable=True)

    expires_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    doctor = relationship("ReferringDoctor")
    branch = relationship("Branch")
    creator = relationship("User")
