"""
Customer Portal Models for VaidyaVihar Diagnostic ERP

Customer self-service module:
- Customer self-registration
- Customer dashboard
- View own orders
- Appointment booking
- Profile management
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class CustomerPortalUser(Base):
    """Customer portal user for self-service"""
    __tablename__ = "patient_portal_users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to main patient record
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=True, unique=True)
    
    # Portal credentials
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    phone = Column(String, nullable=True)
    
    # Authentication
    password_hash = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # OTP for login
    otp = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    
    # Password reset
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    # Access
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    
    # Preferences
    preferred_language = Column(String, default="en")
    notification_preferences = Column(JSON, nullable=True)
    
    # Privacy
    show_orders = Column(Boolean, default=True)
    show_appointments = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Customer")


class CustomerAppointment(Base):
    """Customer self-service appointments"""
    __tablename__ = "patient_appointments"

    id = Column(Integer, primary_key=True, index=True)
    appointment_number = Column(String, nullable=False, unique=True, index=True)
    
    # Customer
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    patient_portal_user_id = Column(Integer, ForeignKey("patient_portal_users.id"), nullable=True)
    
    # Staff
    doctor_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    department = Column(String, nullable=True)
    
    # Schedule
    appointment_date = Column(DateTime, nullable=False)
    appointment_time = Column(String, nullable=True)
    slot_id = Column(Integer, nullable=True)
    
    # Type
    appointment_type = Column(String, default="consultation")  # consultation, followup, checkup
    is_online = Column(Boolean, default=False)
    meeting_link = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, confirmed, completed, cancelled, no_show
    check_in_time = Column(DateTime, nullable=True)
    
    # Reason
    chief_complaint = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Branch
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Reminders
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime, nullable=True)
    
    # Cancellation
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Customer")
    doctor = relationship("Staff")
    branch = relationship("Branch")
    portal_user = relationship("CustomerPortalUser")


class CustomerOrderAccess(Base):
    """Track patient access to their orders"""
    __tablename__ = "patient_report_access"

    id = Column(Integer, primary_key=True, index=True)
    
    # Customer
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    portal_user_id = Column(Integer, ForeignKey("patient_portal_users.id"), nullable=True)
    
    # Order
    report_id = Column(String, nullable=False)
    report_type = Column(String, nullable=True)
    
    # Access
    access_token = Column(String, nullable=False, unique=True)
    token_expires = Column(DateTime, nullable=True)
    
    # Tracking
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    accessed_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Customer")
    portal_user = relationship("CustomerPortalUser")


class CustomerFeedback(Base):
    """Customer feedback and ratings"""
    __tablename__ = "patient_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    
    # Customer
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    portal_user_id = Column(Integer, ForeignKey("patient_portal_users.id"), nullable=True)
    
    # Feedback type
    feedback_type = Column(String, default="general")  # general, service, doctor, lab, suggestion
    
    # Rating (1-5)
    rating = Column(Integer, nullable=True)
    
    # Details
    category = Column(String, nullable=True)  # staff, cleanliness, wait_time, etc.
    comments = Column(Text, nullable=True)
    
    # Follow-up
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, reviewed, resolved
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Customer")
    portal_user = relationship("CustomerPortalUser")


class CustomerFamilyMember(Base):
    """Family members linked to patient portal"""
    __tablename__ = "patient_family_members"

    id = Column(Integer, primary_key=True, index=True)
    
    # Primary user
    portal_user_id = Column(Integer, ForeignKey("patient_portal_users.id"), nullable=False)
    
    # Family member details
    name = Column(String, nullable=False)
    relation = Column(String, nullable=False)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String, nullable=True)
    
    # Contact
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    
    # Medical info (optional)
    blood_group = Column(String, nullable=True)
    allergies = Column(Text, nullable=True)
    
    # Access
    can_view_orders = Column(Boolean, default=True)
    can_book_appointments = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portal_user = relationship("CustomerPortalUser")


class CustomerDocument(Base):
    """Customer documents (prescriptions, previous orders, etc.)"""
    __tablename__ = "patient_documents"

    id = Column(Integer, primary_key=True, index=True)
    
    # Customer
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    portal_user_id = Column(Integer, ForeignKey("patient_portal_users.id"), nullable=True)
    
    # Document
    document_type = Column(String, nullable=False)  # prescription, report, id, other
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # File
    file_path = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Upload
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Status
    is_verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Customer")
    portal_user = relationship("CustomerPortalUser")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    verifier = relationship("User", foreign_keys=[verified_by])


class CustomerPrescription(Base):
    """Customer prescriptions for portal access"""
    __tablename__ = "patient_prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Customer
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Appointment
    appointment_id = Column(Integer, ForeignKey("patient_appointments.id"), nullable=True)
    
    # Staff
    doctor_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    doctor_name = Column(String, nullable=True)
    
    # Prescription
    prescription_date = Column(DateTime, default=datetime.utcnow)
    diagnosis = Column(Text, nullable=True)
    
    # Follow-up
    follow_up_date = Column(DateTime, nullable=True)
    next_visit_instructions = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Customer")
    appointment = relationship("CustomerAppointment")
    doctor = relationship("Staff")
    medications = relationship("PrescriptionMedication", cascade="all, delete-orphan")


class PrescriptionMedication(Base):
    """Medications in a prescription"""
    __tablename__ = "prescription_medications"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("patient_prescriptions.id"), nullable=False)
    
    # Medication
    medicine_name = Column(String, nullable=False)
    dosage = Column(String, nullable=True)
    frequency = Column(String, nullable=True)  # 1-0-1, etc.
    duration = Column(String, nullable=True)
    instructions = Column(Text, nullable=True)
    
    # Type
    medicine_type = Column(String, nullable=True)  # tablet, syrup, injection, etc.
    is_continuing = Column(Boolean, default=False)  # Continuing from previous
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    prescription = relationship("CustomerPrescription")

