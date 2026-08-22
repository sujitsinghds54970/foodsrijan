"""
OTP Request Model for Multi-Role Authentication
Supports Customer, Staff, Director, Staff, CEO OTP verification
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from app.database import Base


class OTPRequest(Base):
    __tablename__ = "otp_requests"

    id = Column(Integer, primary_key=True, index=True)
    
    # Nullable - used for new users registering or users without user_id
    user_id = Column(Integer, nullable=True)
    
    # The identifier (mobile number or email) for OTP verification
    identifier = Column(String(255), nullable=False, index=True)
    
    # Role for multi-role OTP system (patient, staff, director, doctor, super_admin)
    role = Column(String(50), nullable=True, default='patient')
    
    # 6-digit OTP code
    otp_code = Column(String(6), nullable=False)
    
    # Expiry timestamp (usually 10 minutes from creation)
    expires_at = Column(DateTime, nullable=False)
    
    # Whether the OTP has been used
    is_used = Column(Boolean, default=False, index=True)
    
    # Used OTP timestamp
    used_at = Column(DateTime, nullable=True)
    
    # Attempt count (for rate limiting)
    attempt_count = Column(Integer, default=0)
    
    # Whether OTP request is still active
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def is_expired(self) -> bool:
        """Check if OTP has expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if OTP is valid (not expired, not used, is active)"""
        return self.is_active and not self.is_expired() and not self.is_used
