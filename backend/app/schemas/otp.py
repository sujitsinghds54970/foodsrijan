"""
OTP Request/Response Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OTPRequestRequest(BaseModel):
    """Request to generate OTP"""
    identifier: str = Field(..., description="Mobile number or Email")
    role: Optional[str] = Field(default='patient', description="User role: patient, staff, director, doctor, super_admin")

    class Config:
        example = {
            "identifier": "+919876543210",
            "role": "patient"
        }


class OTPVerifyRequest(BaseModel):
    """Request to verify OTP"""
    identifier: str = Field(..., description="Mobile number or Email")
    otp_code: str = Field(..., description="6-digit OTP code")
    role: Optional[str] = Field(default='patient', description="User role")

    class Config:
        example = {
            "identifier": "+919876543210",
            "otp_code": "123456",
            "role": "patient"
        }


class OTPRequestResponse(BaseModel):
    """Response after OTP request"""
    status: str
    message: str
    identifier: str
    expires_in_seconds: int = 600  # 10 minutes
    retry_after_seconds: Optional[int] = None

    class Config:
        example = {
            "status": "success",
            "message": "OTP sent to your registered mobile number",
            "identifier": "+919876543210",
            "expires_in_seconds": 600
        }


class OTPVerifyResponse(BaseModel):
    """Response after OTP verification"""
    status: str
    message: str
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    user: Optional[dict] = None
    is_new_user: Optional[bool] = None

    class Config:
        example = {
            "status": "success",
            "message": "OTP verified successfully",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user": {
                "id": 1,
                "identifier": "+919876543210",
                "role": "patient",
                "is_new_user": False
            },
            "is_new_user": False
        }


class OTPStatusResponse(BaseModel):
    """Response for OTP status check"""
    status: str
    message: str
    identifier: str
    is_expired: bool
    is_used: bool
    remaining_attempts: int


class OTPErrorResponse(BaseModel):
    """Error response"""
    status: str = "error"
    message: str
    error_code: str
    retry_after_seconds: Optional[int] = None
