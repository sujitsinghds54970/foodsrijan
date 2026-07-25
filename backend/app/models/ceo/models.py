from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CeoSecurityProfile(Base):
    __tablename__ = "ceo_security_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    webauthn_user_handle = Column(String(255), nullable=True, unique=True)
    webauthn_registration_challenge = Column(String(255), nullable=True)
    webauthn_registration_origin = Column(String(255), nullable=True)
    webauthn_registration_expires_at = Column(DateTime, nullable=True)
    totp_secret = Column(String(255), nullable=True)
    totp_enabled = Column(Boolean, nullable=False, default=False)
    last_otp_sent_at = Column(DateTime, nullable=True)
    last_otp_verified_at = Column(DateTime, nullable=True)
    behavioral_baseline = Column(JSON, nullable=False, default=dict)
    behavioral_last_deviation = Column(Float, nullable=True)
    behavioral_step_up_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    credentials = relationship("CeoWebAuthnCredential", back_populates="security_profile", cascade="all, delete-orphan")


class CeoWebAuthnCredential(Base):
    __tablename__ = "ceo_webauthn_credentials"

    id = Column(Integer, primary_key=True, index=True)
    security_profile_id = Column(Integer, ForeignKey("ceo_security_profiles.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    credential_id = Column(String(512), nullable=False, unique=True, index=True)
    public_key = Column(Text, nullable=True)
    attestation_object = Column(Text, nullable=True)
    sign_count = Column(Integer, nullable=False, default=0)
    transports = Column(JSON, nullable=False, default=list)
    device_label = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    last_used_at = Column(DateTime, nullable=True)

    security_profile = relationship("CeoSecurityProfile", back_populates="credentials")
    user = relationship("User")


class CeoAuditLog(Base):
    __tablename__ = "ceo_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(120), nullable=False, index=True)
    http_method = Column(String(16), nullable=False)
    endpoint = Column(String(255), nullable=False, index=True)
    response_status = Column(Integer, nullable=False)
    request_meta = Column(JSON, nullable=False, default=dict)
    previous_signature = Column(String(128), nullable=True)
    signature = Column(String(128), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    user = relationship("User")


class CeoBreakGlassGrant(Base):
    __tablename__ = "ceo_break_glass_grants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    approver_1_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    approver_2_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    approved = Column(Boolean, nullable=False, default=False)
    temp_auth_token_hash = Column(String(128), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    user = relationship("User", foreign_keys=[user_id])
    approver_1 = relationship("User", foreign_keys=[approver_1_id])
    approver_2 = relationship("User", foreign_keys=[approver_2_id])