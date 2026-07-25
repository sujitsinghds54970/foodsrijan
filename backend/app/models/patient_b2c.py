from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class TestCatalog(Base):
    __tablename__ = "patient_test_catalog"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(120), nullable=False, index=True)
    price = Column(Integer, nullable=False)
    preparation_instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PatientB2CAppointment(Base):
    __tablename__ = "patient_b2c_appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_profile_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    test_ids = Column(JSON, nullable=False, default=list)
    appointment_type = Column(String(20), nullable=False)  # Home/Center
    scheduled_time = Column(DateTime, nullable=False, index=True)
    status = Column(String(30), nullable=False, default="Booked", index=True)
    phlebotomist_id = Column(Integer, ForeignKey("staff.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient_profile = relationship("PatientProfile")


class DigitalConsent(Base):
    __tablename__ = "patient_digital_consents"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("patient_b2c_appointments.id"), nullable=False, index=True)
    consent_text = Column(Text, nullable=False)
    signed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    appointment = relationship("PatientB2CAppointment")


class PatientB2CAuditLog(Base):
    __tablename__ = "patient_b2c_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    patient_profile_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    action = Column(String(120), nullable=False, index=True)
    entity_type = Column(String(120), nullable=False)
    entity_id = Column(String(120), nullable=True, index=True)
    event_meta = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    patient_profile = relationship("PatientProfile")


class ReportSummary(Base):
    __tablename__ = "patient_report_summaries"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("daily_entries_module.id"), nullable=False, index=True)
    ai_summary = Column(Text, nullable=False)
    abnormal_flags = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient_profile = relationship("PatientProfile")


class HealthTrend(Base):
    __tablename__ = "patient_health_trends"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    biomarker = Column(String(120), nullable=False, index=True)
    value = Column(String(50), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    graph_data = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient_profile = relationship("PatientProfile")


class HealthScore(Base):
    __tablename__ = "patient_health_scores"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    last_calculated = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    patient_profile = relationship("PatientProfile")


class FollowUpReminder(Base):
    __tablename__ = "patient_followup_reminders"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    test_name = Column(String(200), nullable=False, index=True)
    next_due_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(40), nullable=False, default="active", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient_profile = relationship("PatientProfile")


class LoyaltyReward(Base):
    __tablename__ = "patient_loyalty_rewards"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    points = Column(Integer, nullable=False, default=0)
    transaction_type = Column(String(40), nullable=False, index=True)  # Earn/Redemption
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    patient_profile = relationship("PatientProfile")


class Referral(Base):
    __tablename__ = "patient_referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    referee_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    bonus_earned = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    referrer = relationship("PatientProfile", foreign_keys=[referrer_id])
    referee = relationship("PatientProfile", foreign_keys=[referee_id])


class HealthGoal(Base):
    __tablename__ = "patient_health_goals"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    goal_type = Column(String(300), nullable=False, index=True)
    target_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(40), nullable=False, default="In Progress", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient_profile = relationship("PatientProfile")
