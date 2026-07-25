from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class WearableSync(Base):
    __tablename__ = "patient_wearable_syncs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    provider = Column(String(60), nullable=False, index=True)
    token = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="connected", index=True)
    last_synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient_profile = relationship("PatientProfile")


class SecondOpinionRequest(Base):
    __tablename__ = "patient_second_opinion_requests"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("daily_entries_module.id"), nullable=False, index=True)
    status = Column(String(40), nullable=False, default="Pending Payment", index=True)
    payment_reference = Column(String(120), nullable=True, index=True)
    specialist_panel = Column(String(120), nullable=False, default="Senior Specialist Panel")
    premium_amount = Column(Integer, nullable=False, default=999)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient_profile = relationship("PatientProfile")


class EmergencyAlert(Base):
    __tablename__ = "patient_emergency_alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("daily_entries_module.id"), nullable=True, index=True)
    alert_type = Column(String(60), nullable=False, index=True)
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    delivery_channels = Column(JSON, nullable=False, default=list)
    doctor_notified = Column(Integer, nullable=False, default=1)
    note = Column(Text, nullable=True)

    patient_profile = relationship("PatientProfile")


class PatientVaultDocument(Base):
    __tablename__ = "patient_vault_documents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    extracted_text = Column(Text, nullable=False)
    document_label = Column(String(150), nullable=True)
    file_size = Column(Integer, nullable=False, default=0)
    mime_type = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient_profile = relationship("PatientProfile")
