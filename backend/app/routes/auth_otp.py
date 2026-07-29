"""
OTP Authentication Routes
Unified OTP login system for all user roles (Patient, Staff, Director, Doctor, CEO)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from app.database import get_db
from app.models import OTPRequest, User
from app.schemas.otp import (
    OTPRequestRequest,
    OTPVerifyRequest,
    OTPRequestResponse,
    OTPVerifyResponse,
)
from app.services.otp_service import OTPService
from app.utils.auth_system import auth_guard, ALGORITHM, SECRET_KEY

router = APIRouter(prefix="/api/auth/otp", tags=["OTP Authentication"])


@router.post("/request", response_model=OTPRequestResponse)
async def request_otp(
    request: OTPRequestRequest,
    db: Session = Depends(get_db)
):
    """
    Request OTP for authentication
    
    Accepts:
    - identifier: Mobile number (e.g., +919876543210) or Email
    - role: Optional user role (patient, staff, director, doctor, super_admin)
    
    Returns:
    - OTP is generated and logged to console for testing
    - In production, it would be sent via SMS (Twilio) or Email
    """
    try:
        # Create OTP request
        otp_request = OTPService.create_otp_request(
            db=db,
            identifier=request.identifier.strip(),
            role=request.role or 'patient'
        )
        
        return OTPRequestResponse(
            status="success",
            message="OTP has been generated and sent to your registered contact",
            identifier=request.identifier,
            expires_in_seconds=OTPService.OTP_VALIDITY_MINUTES * 60
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating OTP: {str(e)}"
        )


@router.post("/verify", response_model=OTPVerifyResponse)
async def verify_otp(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and return authentication token
    
    Accepts:
    - identifier: Mobile number or Email (same as used in request)
    - otp_code: 6-digit OTP
    - role: User role
    
    Returns:
    - access_token: JWT token for authenticated requests
    - token_type: "bearer"
    - user: User information
    - is_new_user: Whether this was a new user
    """
    try:
        identifier = request.identifier.strip()
        otp_code = request.otp_code.strip()
        role = request.role or 'patient'
        
        # Verify OTP
        is_valid, message, otp_request = OTPService.verify_otp(
            db=db,
            identifier=identifier,
            otp_code=otp_code,
            role=role
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        
        # Get or create user
        try:
            user, is_new_user = OTPService.get_or_create_user_by_identifier(
                db=db,
                identifier=identifier,
                role=role,
                is_new_user=False  # For now, user should be pre-registered
            )
        except HTTPException:
            # If user doesn't exist, this is treated as a registration flow
            # For now, we'll raise an error
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Please register first or contact administrator."
            )
        
        # Create JWT token
        access_token = auth_guard.create_access_token(
            data={
                "sub": user.username,
                "user_id": user.id,
                "role": user.role,
                "identifier": identifier
            },
            expires_delta=timedelta(days=7)
        )
        
        return OTPVerifyResponse(
            status="success",
            message="OTP verified successfully. You are now authenticated.",
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "identifier": identifier
            },
            is_new_user=is_new_user
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying OTP: {str(e)}"
        )


@router.post("/resend")
async def resend_otp(
    request: OTPRequestRequest,
    db: Session = Depends(get_db)
):
    """
    Resend OTP for the same identifier
    
    Rate limited to prevent abuse
    """
    try:
        # Check if there's a recent valid OTP for this identifier
        recent_otps = db.query(OTPRequest).filter(
            OTPRequest.identifier == request.identifier.strip(),
            OTPRequest.is_active == True
        ).order_by(OTPRequest.created_at.desc()).limit(1).all()
        
        if recent_otps:
            existing_otp = recent_otps[0]
            # If OTP is still valid (not expired), return it instead of creating new one
            if not existing_otp.is_expired():
                remaining_minutes = (existing_otp.expires_at - existing_otp.created_at).seconds // 60
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"OTP already sent. Please use the existing OTP or wait {remaining_minutes} minutes to request a new one."
                )
        
        # Create new OTP
        otp_request = OTPService.create_otp_request(
            db=db,
            identifier=request.identifier.strip(),
            role=request.role or 'patient'
        )
        
        return OTPRequestResponse(
            status="success",
            message="New OTP has been sent",
            identifier=request.identifier,
            expires_in_seconds=OTPService.OTP_VALIDITY_MINUTES * 60
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resending OTP: {str(e)}"
        )


@router.get("/status/{identifier}")
async def get_otp_status(
    identifier: str,
    db: Session = Depends(get_db)
):
    """
    Check if an OTP exists for an identifier and its status
    (For debugging/testing purposes)
    """
    otp_request = db.query(OTPRequest).filter(
        OTPRequest.identifier == identifier.strip()
    ).order_by(OTPRequest.created_at.desc()).first()
    
    if not otp_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No OTP request found for this identifier"
        )
    
    return {
        "status": "found",
        "identifier": identifier,
        "is_expired": otp_request.is_expired(),
        "is_used": otp_request.is_used,
        "attempts_remaining": max(0, OTPService.MAX_ATTEMPTS - otp_request.attempt_count),
        "created_at": otp_request.created_at,
        "expires_at": otp_request.expires_at,
        # Include OTP code only for debugging (remove in production)
        "otp_code": otp_request.otp_code if not otp_request.is_used else "***"
    }
