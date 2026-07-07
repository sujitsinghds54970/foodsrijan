"""
Branch Bank Details Model
Stores bank account and UPI information for each branch
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class BranchBankDetails(Base):
    __tablename__ = "branch_bank_details"
    
    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), unique=True, nullable=False)
    
    # Bank Account Details
    account_holder_name = Column(String(255), nullable=False)
    account_number = Column(String(50), nullable=False)
    ifsc_code = Column(String(20), nullable=False)
    bank_name = Column(String(255), nullable=False)
    
    # UPI Details (Critical for QR payments)
    upi_id = Column(String(100), nullable=False, index=True)
    
    # Soundbox/Payment Device Configuration (Flexible JSON)
    # Stores any payment confirmation device config like:
    # {"provider": "SBI", "device_id": "SB-12345", "merchant_id": "M-5678", "webhook": "https://..."}
    soundbox_config = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    branch = relationship("Branch", back_populates="bank_details")
    
    def __repr__(self):
        return f"<BranchBankDetails(branch_id={self.branch_id}, upi_id={self.upi_id})>"
