"""
Customer Portal Routes for VaidyaVihar Diagnostic ERP

Customer self-service endpoints:
- Customer registration and authentication
- View own orders
- Book appointments
- Profile management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
import uuid
import random
import string

from app.database import get_db
from app.models.patient_portal import (
    CustomerPortalUser, CustomerAppointment, CustomerOrderAccess,
    CustomerFeedback, CustomerFamilyMember, CustomerDocument
)

router = APIRouter()


# Pydantic Schemas
class CustomerPortalRegister(BaseModel):
    patient_id: Optional[int] = None
    username: str
    email: EmailStr
    phone: str
    password: str


class CustomerPortalLogin(BaseModel):
    username: str
    password: str


class CustomerPortalOTPRequest(BaseModel):
    phone: str


class CustomerPortalOTPVerify(BaseModel):
    phone: str
    otp: str


class AppointmentBooking(BaseModel):
    patient_id: int
    doctor_id: Optional[int] = None
    department: Optional[str] = None
    appointment_date: datetime
    appointment_time: Optional[str] = None
    appointment_type: str = "consultation"
    chief_complaint: Optional[str] = None
    branch_id: Optional[int] = None


class FeedbackCreate(BaseModel):
    feedback_type: str = "general"
    rating: Optional[int] = None
    category: Optional[str] = None
    comments: str


# Helper functions
def generate_otp(length: int = 6):
    """Generate numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))


def generate_access_token():
    """Generate unique access token"""
    return str(uuid.uuid4())


# Authentication Endpoints
@router.post("/register")
async def register_patient_portal(user_data: CustomerPortalRegister, db: Session = Depends(get_db)):
    """Register a new patient portal user"""
    # Check if username or email already exists
    existing_user = db.query(CustomerPortalUser).filter(
        (CustomerPortalUser.username == user_data.username) |
        (CustomerPortalUser.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Create user
    portal_user = CustomerPortalUser(
        patient_id=user_data.patient_id,
        username=user_data.username,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=user_data.password,  # In production, hash this!
        is_verified=False,
        verification_token=str(uuid.uuid4())
    )
    
    db.add(portal_user)
    db.commit()
    db.refresh(portal_user)
    
    return {
        "success": True,
        "message": "Registration successful. Please verify your email.",
        "user": {
            "id": portal_user.id,
            "username": portal_user.username,
            "email": portal_user.email
        }
    }


@router.post("/login")
async def login_patient_portal(credentials: CustomerPortalLogin, db: Session = Depends(get_db)):
    """Login to patient portal"""
    user = db.query(CustomerPortalUser).filter(
        CustomerPortalUser.username == credentials.username
    ).first()
    
    if not user or user.password_hash != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    # Update login info
    user.last_login = datetime.utcnow()
    user.login_count += 1
    db.commit()
    
    return {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "patient_id": user.patient_id,
            "is_verified": user.is_verified
        }
    }


@router.post("/otp/request")
async def request_otp(otp_request: CustomerPortalOTPRequest, db: Session = Depends(get_db)):
    """Request OTP for login"""
    user = db.query(CustomerPortalUser).filter(
        CustomerPortalUser.phone == otp_request.phone
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Phone number not registered")
    
    # Generate OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expires = datetime.utcnow() + timedelta(minutes=10)
    
    db.commit()
    
    # In production, send OTP via SMS
    # For now, return OTP for testing
    return {
        "success": True,
        "message": "OTP sent to registered phone number",
        "otp": otp  # Remove in production!
    }


@router.post("/otp/verify")
async def verify_otp(otp_verify: CustomerPortalOTPVerify, db: Session = Depends(get_db)):
    """Verify OTP and login"""
    user = db.query(CustomerPortalUser).filter(
        CustomerPortalUser.phone == otp_verify.phone
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Phone number not registered")
    
    if user.otp != otp_verify.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    if user.otp_expires and user.otp_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")
    
    # Clear OTP and update login
    user.otp = None
    user.otp_expires = None
    user.last_login = datetime.utcnow()
    user.login_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "patient_id": user.patient_id
        }
    }


# Customer Appointments
@router.post("/appointments")
async def book_appointment(appointment_data: AppointmentBooking, db: Session = Depends(get_db)):
    """Book an appointment"""
    # Generate appointment number
    appointment_number = f"PAT-APT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    appointment = CustomerAppointment(
        appointment_number=appointment_number,
        patient_id=appointment_data.patient_id,
        doctor_id=appointment_data.doctor_id,
        department=appointment_data.department,
        appointment_date=appointment_data.appointment_date,
        appointment_time=appointment_data.appointment_time,
        appointment_type=appointment_data.appointment_type,
        chief_complaint=appointment_data.chief_complaint,
        branch_id=appointment_data.branch_id,
        status="pending"
    )
    
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    return {
        "success": True,
        "appointment": {
            "id": appointment.id,
            "appointment_number": appointment.appointment_number,
            "appointment_date": appointment.appointment_date.isoformat(),
            "status": appointment.status
        }
    }


@router.get("/appointments")
async def list_patient_appointments(
    patient_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List patient's appointments"""
    query = db.query(CustomerAppointment).filter(
        CustomerAppointment.patient_id == patient_id
    )
    
    if status:
        query = query.filter(CustomerAppointment.status == status)
    
    appointments = query.order_by(
        CustomerAppointment.appointment_date.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "appointments": [
            {
                "id": apt.id,
                "appointment_number": apt.appointment_number,
                "appointment_date": apt.appointment_date.isoformat(),
                "appointment_time": apt.appointment_time,
                "appointment_type": apt.appointment_type,
                "status": apt.status,
                "chief_complaint": apt.chief_complaint
            }
            for apt in appointments
        ]
    }


@router.get("/appointments/{appointment_id}")
async def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    """Get appointment details"""
    appointment = db.query(CustomerAppointment).filter(
        CustomerAppointment.id == appointment_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return {
        "success": True,
        "appointment": {
            "id": appointment.id,
            "appointment_number": appointment.appointment_number,
            "appointment_date": appointment.appointment_date.isoformat(),
            "appointment_time": appointment.appointment_time,
            "appointment_type": appointment.appointment_type,
            "status": appointment.status,
            "chief_complaint": appointment.chief_complaint,
            "notes": appointment.notes
        }
    }


@router.delete("/appointments/{appointment_id}")
async def cancel_appointment(appointment_id: int, reason: str, db: Session = Depends(get_db)):
    """Cancel an appointment"""
    appointment = db.query(CustomerAppointment).filter(
        CustomerAppointment.id == appointment_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.status in ["completed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Cannot cancel this appointment")
    
    appointment.status = "cancelled"
    appointment.cancelled_at = datetime.utcnow()
    appointment.cancellation_reason = reason
    
    db.commit()
    
    return {
        "success": True,
        "message": "Appointment cancelled successfully"
    }


# Orders Access
@router.post("/orders/access")
async def request_report_access(
    patient_id: int,
    report_id: str,
    db: Session = Depends(get_db)
):
    """Request access to a report"""
    # Check if access already exists
    existing = db.query(CustomerOrderAccess).filter(
        CustomerOrderAccess.patient_id == patient_id,
        CustomerOrderAccess.report_id == report_id,
        CustomerOrderAccess.is_active == True
    ).first()
    
    if existing:
        # Return existing access
        return {
            "success": True,
            "access_token": existing.access_token,
            "expires": existing.token_expires.isoformat() if existing.token_expires else None
        }
    
    # Create new access
    access_token = generate_access_token()
    
    access = CustomerOrderAccess(
        patient_id=patient_id,
        report_id=report_id,
        access_token=access_token,
        token_expires=datetime.utcnow() + timedelta(days=7)
    )
    
    db.add(access)
    db.commit()
    
    return {
        "success": True,
        "access_token": access_token,
        "expires": access.token_expires.isoformat()
    }


@router.get("/orders/verify")
async def verify_report_access(
    access_token: str,
    db: Session = Depends(get_db)
):
    """Verify report access token"""
    access = db.query(CustomerOrderAccess).filter(
        CustomerOrderAccess.access_token == access_token,
        CustomerOrderAccess.is_active == True
    ).first()
    
    if not access:
        raise HTTPException(status_code=404, detail="Invalid access token")
    
    if access.token_expires and access.token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Access token expired")
    
    # Update access tracking
    access.access_count += 1
    access.accessed_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "report_id": access.report_id,
        "patient_id": access.patient_id
    }


# Feedback
@router.post("/feedback")
async def submit_feedback(
    patient_id: Optional[int],
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db)
):
    """Submit patient feedback"""
    feedback = CustomerFeedback(
        patient_id=patient_id,
        feedback_type=feedback_data.feedback_type,
        rating=feedback_data.rating,
        category=feedback_data.category,
        comments=feedback_data.comments,
        status="pending"
    )
    
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return {
        "success": True,
        "feedback": {
            "id": feedback.id,
            "feedback_type": feedback.feedback_type,
            "rating": feedback.rating,
            "status": feedback.status
        }
    }


# Family Members
@router.post("/family-members")
async def add_family_member(
    portal_user_id: int,
    name: str,
    relationship: str,
    date_of_birth: Optional[datetime] = None,
    gender: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Add family member"""
    member = CustomerFamilyMember(
        portal_user_id=portal_user_id,
        name=name,
        relationship=relationship,
        date_of_birth=date_of_birth,
        gender=gender,
        phone=phone,
        email=email
    )
    
    db.add(member)
    db.commit()
    db.refresh(member)
    
    return {
        "success": True,
        "member": {
            "id": member.id,
            "name": member.name,
            "relationship": member.relationship
        }
    }


@router.get("/family-members/{portal_user_id}")
async def list_family_members(portal_user_id: int, db: Session = Depends(get_db)):
    """List family members"""
    members = db.query(CustomerFamilyMember).filter(
        CustomerFamilyMember.portal_user_id == portal_user_id
    ).all()
    
    return {
        "success": True,
        "members": [
            {
                "id": m.id,
                "name": m.name,
                "relationship": m.relationship,
                "date_of_birth": m.date_of_birth.isoformat() if m.date_of_birth else None,
                "gender": m.gender
            }
            for m in members
        ]
    }


# Profile Management
@router.get("/profile/{portal_user_id}")
async def get_portal_profile(portal_user_id: int, db: Session = Depends(get_db)):
    """Get portal user profile"""
    user = db.query(CustomerPortalUser).filter(
        CustomerPortalUser.id == portal_user_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {
        "success": True,
        "profile": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "patient_id": user.patient_id,
            "is_verified": user.is_verified,
            "preferred_language": user.preferred_language,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
    }


@router.put("/profile/{portal_user_id}")
async def update_portal_profile(
    portal_user_id: int,
    preferred_language: Optional[str] = None,
    notification_preferences: Optional[dict] = None,
    db: Session = Depends(get_db)
):
    """Update portal user profile"""
    user = db.query(CustomerPortalUser).filter(
        CustomerPortalUser.id == portal_user_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if preferred_language:
        user.preferred_language = preferred_language
    if notification_preferences:
        user.notification_preferences = notification_preferences
    
    db.commit()
    
    return {
        "success": True,
        "message": "Profile updated successfully"
    }

