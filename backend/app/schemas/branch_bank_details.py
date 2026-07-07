"""
Branch Bank Details Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class BranchBankDetailsBase(BaseModel):
    account_holder_name: str = Field(..., min_length=1, max_length=255)
    account_number: str = Field(..., min_length=1, max_length=50)
    ifsc_code: str = Field(..., min_length=11, max_length=11, description="IFSC code must be 11 characters")
    bank_name: str = Field(..., min_length=1, max_length=255)
    upi_id: str = Field(..., min_length=1, max_length=100, description="UPI ID for QR payments")
    soundbox_config: Optional[Dict[str, Any]] = Field(None, description="Flexible JSON config for payment devices (soundbox, etc.)")
    is_active: bool = True


class BranchBankDetailsCreate(BranchBankDetailsBase):
    pass


class BranchBankDetailsUpdate(BaseModel):
    account_holder_name: Optional[str] = Field(None, min_length=1, max_length=255)
    account_number: Optional[str] = Field(None, min_length=1, max_length=50)
    ifsc_code: Optional[str] = Field(None, min_length=11, max_length=11)
    bank_name: Optional[str] = Field(None, min_length=1, max_length=255)
    upi_id: Optional[str] = Field(None, min_length=1, max_length=100)
    soundbox_config: Optional[Dict[str, Any]] = Field(None, description="Flexible JSON config for payment devices")
    is_active: Optional[bool] = None


class BranchBankDetailsResponse(BranchBankDetailsBase):
    id: int
    branch_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
