from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True, unique=True, index=True)

    patient_code = Column(String(64), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    mobile = Column(String(20), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True)
    otp_verification = Column(Boolean, nullable=False, default=False)
    referring_doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True, index=True)
    family_members_json = Column(JSON, nullable=False, default=list)

    password = Column(String(255), nullable=False)
    otp_code = Column(String(8), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)

    role = Column(String(32), nullable=False, default="patient")
    is_active = Column(Boolean, nullable=False, default=True)

    family_group = Column(String(64), nullable=True, index=True)
    wallet_balance = Column(Float, nullable=False, default=0.0)
    cashback_percent = Column(Float, nullable=False, default=5.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    family_members = relationship(
        "FamilyMember",
        back_populates="owner_profile",
        foreign_keys="FamilyMember.owner_profile_id",
        cascade="all, delete-orphan",
    )
    referring_doctor = relationship("Doctor", foreign_keys=[referring_doctor_id])


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    owner_profile_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    linked_profile_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    relation = Column(String(64), nullable=False)
    age = Column(Integer, nullable=True)
    mobile = Column(String(20), nullable=True)

    owner_profile = relationship(
        "PatientProfile",
        back_populates="family_members",
        foreign_keys=[owner_profile_id],
    )
    linked_profile = relationship("PatientProfile", foreign_keys=[linked_profile_id])
