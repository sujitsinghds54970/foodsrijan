"""
OTP Service for Multi-Role Authentication
Handles OTP generation, verification, and expiry management
"""

import secrets
import random
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import OTPRequest, User, Branch
from app.utils.auth_system import auth_guard
from fastapi import HTTPException, status


class OTPService:
    """Service for managing OTP requests and verification"""
    
    # OTP validity period (10 minutes)
    OTP_VALIDITY_MINUTES = 10
    
    # Maximum OTP attempts before rate limiting
    MAX_ATTEMPTS = 5
    
    # Rate limit window (in minutes)
    RATE_LIMIT_WINDOW_MINUTES = 5
    
    # Possible roles
    VALID_ROLES = ['patient', 'staff', 'director', 'doctor', 'super_admin']
    
    @staticmethod
    def generate_otp_code() -> str:
        """
        Generate a 6-digit OTP code
        In production, this should be sent via SMS/Email
        For now, we log it to console for testing
        """
        # Generate random 6-digit code
        otp_code = str(random.randint(100000, 999999))
        return otp_code
    
    @staticmethod
    def create_otp_request(
        db: Session,
        identifier: str,
        role: str = 'patient',
        user_id: Optional[int] = None
    ) -> OTPRequest:
        """
        Create a new OTP request
        
        Args:
            db: Database session
            identifier: Mobile number or Email
            role: User role (patient, staff, director, doctor, super_admin)
            user_id: Optional user ID if already registered
            
        Returns:
            OTPRequest object
        """
        # Validate role
        if role not in OTPService.VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(OTPService.VALID_ROLES)}"
            )
        
        # Check for rate limiting
        recent_requests = db.query(OTPRequest).filter(
            and_(
                OTPRequest.identifier == identifier,
                OTPRequest.created_at > datetime.utcnow() - timedelta(minutes=OTPService.RATE_LIMIT_WINDOW_MINUTES),
                OTPRequest.is_active == True
            )
        ).count()
        
        if recent_requests >= OTPService.MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many OTP requests. Please try again after 5 minutes."
            )
        
        # Generate OTP
        otp_code = OTPService.generate_otp_code()
        expires_at = datetime.utcnow() + timedelta(minutes=OTPService.OTP_VALIDITY_MINUTES)
        
        # Create OTP request
        otp_request = OTPRequest(
            user_id=user_id,
            identifier=identifier,
            role=role,
            otp_code=otp_code,
            expires_at=expires_at,
            is_active=True
        )
        
        db.add(otp_request)
        db.commit()
        db.refresh(otp_request)
        
        # Log OTP for testing (in production, this would be sent via SMS/Email)
        print(f"\n{'='*60}")
        print(f"OTP for {identifier} (Role: {role}): {otp_code}")
        print(f"Expires at: {expires_at}")
        print(f"{'='*60}\n")
        
        # Mock SMS notification (for testing)
        OTPService._mock_send_otp(identifier, otp_code, role)
        
        return otp_request
    
    @staticmethod
    def _mock_send_otp(identifier: str, otp_code: str, role: str):
        """
        Mock OTP sending via SMS/Email
        In production, this would integrate with Twilio, AWS SNS, or similar services
        """
        if '@' in identifier:
            # Email
            print(f"[MOCK EMAIL] Sending OTP {otp_code} to {identifier} for role {role}")
        else:
            # SMS
            print(f"[MOCK SMS] Sending OTP {otp_code} to {identifier} for role {role}")
    
    @staticmethod
    def verify_otp(
        db: Session,
        identifier: str,
        otp_code: str,
        role: str = 'patient'
    ) -> Tuple[bool, str, Optional[OTPRequest]]:
        """
        Verify OTP and return validation status
        
        Args:
            db: Database session
            identifier: Mobile number or Email
            otp_code: OTP code to verify
            role: User role
            
        Returns:
            Tuple of (is_valid, message, otp_request_object)
        """
        # Find the most recent OTP request for this identifier
        otp_request = db.query(OTPRequest).filter(
            and_(
                OTPRequest.identifier == identifier,
                OTPRequest.role == role,
                OTPRequest.is_active == True
            )
        ).order_by(OTPRequest.created_at.desc()).first()
        
        if not otp_request:
            return False, "No active OTP request found for this identifier", None
        
        if otp_request.is_expired():
            otp_request.is_active = False
            db.commit()
            return False, "OTP has expired. Please request a new one.", otp_request
        
        if otp_request.is_used:
            return False, "OTP has already been used.", otp_request
        
        # Check attempt count
        if otp_request.attempt_count >= OTPService.MAX_ATTEMPTS:
            otp_request.is_active = False
            db.commit()
            return False, "Maximum OTP verification attempts exceeded.", otp_request
        
        # Verify OTP code
        if otp_request.otp_code != otp_code:
            otp_request.attempt_count += 1
            db.commit()
            remaining = OTPService.MAX_ATTEMPTS - otp_request.attempt_count
            return False, f"Invalid OTP. {remaining} attempts remaining.", otp_request
        
        # Mark OTP as used
        otp_request.is_used = True
        otp_request.used_at = datetime.utcnow()
        db.commit()
        
        return True, "OTP verified successfully", otp_request
    
    @staticmethod
    def get_or_create_user_by_identifier(
        db: Session,
        identifier: str,
        role: str = 'patient',
        is_new_user: bool = False
    ) -> Tuple[User, bool]:
        """
        Get existing user or create new one based on identifier
        
        Args:
            db: Database session
            identifier: Mobile number or Email
            role: User role
            is_new_user: Whether this is a new user registration
            
        Returns:
            Tuple of (User object, is_newly_created)
        """
        # Try to find user by email or phone
        user = None
        if '@' in identifier:
            # Email-based lookup
            user = db.query(User).filter(User.email == identifier).first()
        else:
            # Phone-based lookup
            user = db.query(User).filter(User.phone == identifier).first()
        
        if user:
            return user, False
        
        if not is_new_user:
            # User doesn't exist and not registering
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Please register first."
            )
        
        # Create new user
        # Get or create a default branch
        branch = db.query(Branch).first()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No branch available for registration"
            )
        
        # Generate username from identifier
        username = OTPService._generate_username_from_identifier(db, identifier)
        
        # Create new user
        new_user = User(
            username=username,
            email=identifier if '@' in identifier else f"user_{identifier}@vaidyavihar.local",
            phone=identifier if '@' not in identifier else None,
            role=role,
            branch_id=branch.id,
            is_active=True,
            hashed_password=auth_guard.hash_password(secrets.token_urlsafe(16))  # Random password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user, True
    
    @staticmethod
    def _generate_username_from_identifier(db: Session, identifier: str) -> str:
        """
        Generate a unique username from identifier
        """
        if '@' in identifier:
            # Email
            base_username = identifier.split('@')[0]
        else:
            # Phone - use last 8 digits
            base_username = f"user_{identifier[-8:]}"
        
        # Ensure uniqueness
        username = base_username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}_{counter}"
            counter += 1
        
        return username
    
    @staticmethod
    def cleanup_expired_otps(db: Session):
        """
        Mark expired OTPs as inactive (for maintenance)
        """
        expired_count = db.query(OTPRequest).filter(
            and_(
                OTPRequest.is_active == True,
                OTPRequest.expires_at < datetime.utcnow()
            )
        ).update({"is_active": False})
        
        db.commit()
        return expired_count
