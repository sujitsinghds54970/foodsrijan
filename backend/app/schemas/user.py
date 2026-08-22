from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, min_length=10, max_length=15, description="Phone number")
    role: str = Field(default="patient", description="User role")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128, description="Password")
    branch_id: Optional[int] = Field(None, description="Branch ID for branch users")
    
    # Override defaults for registration
    phone: Optional[str] = Field(None, min_length=10, max_length=15, description="Phone number")
    role: str = Field(default="patient", description="User role")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[int] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None  # Allow None or empty for response
    role: str
    branch_id: Optional[int]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)

class BranchResponse(BaseModel):
    id: int
    name: str
    location: str
    city: str
    state: str
    is_active: bool
    
    class Config:
        from_attributes = True

class CustomerBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: datetime
    gender: str = Field(..., pattern=r"^(Male|Female|Other)$")
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    address: str = Field(..., min_length=5)
    city: str = Field(..., min_length=2)
    state: str = Field(..., min_length=2)
    pincode: str = Field(..., min_length=6, max_length=10)
    emergency_contact: str = Field(..., min_length=10, max_length=15)
    emergency_contact_name: str = Field(..., min_length=2)
    blood_group: Optional[str] = Field(None, pattern=r"^(A\+|A-|B\+|B-|O\+|O-|AB\+|AB-)$")
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    is_active: Optional[bool] = None

class CustomerResponse(CustomerBase):
    id: int
    patient_id: str
    branch_id: int
    registration_date: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class DailyEntryBase(BaseModel):
    entry_date: datetime
    doctor_name: str = Field(..., min_length=2)
    doctor_specialization: Optional[str] = None
    consultation_fee: float = Field(..., ge=0)
    patient_name: str = Field(..., min_length=2)
    patient_mobile: str = Field(..., min_length=10)
    patient_address: str = Field(..., min_length=5)
    test_names: str = Field(..., min_length=1)
    test_cost: float = Field(default=0, ge=0)
    discount: float = Field(default=0, ge=0)
    total_amount: float = Field(..., ge=0)
    payment_status: str = Field(default="pending", pattern=r"^(pending|paid|partial)$")
    payment_mode: Optional[str] = Field(None, pattern=r"^(cash|card|online|insurance)$")
    amount_paid: float = Field(default=0, ge=0)
    notes: Optional[str] = None
    referred_by: Optional[str] = None

class DailyEntryCreate(DailyEntryBase):
    patient_id: Optional[int] = None

class DailyEntryUpdate(BaseModel):
    payment_status: Optional[str] = None
    payment_mode: Optional[str] = None
    amount_paid: Optional[float] = None
    notes: Optional[str] = None
    referred_by: Optional[str] = None

class DailyEntryResponse(DailyEntryBase):
    id: int
    branch_id: int
    patient_id: Optional[int]
    entry_time: datetime
    created_by: int
    created_at: datetime
    
    # Include patient info if available
    patient: Optional[CustomerResponse] = None
    
    class Config:
        from_attributes = True

class MonthlyOrderRequest(BaseModel):
    year: int = Field(..., ge=2020, le=2030)
    month: int = Field(..., ge=1, le=12)
    branch_id: Optional[int] = None
    doctor_name: Optional[str] = None

class ExportResponse(BaseModel):
    success: bool
    message: str
    file_path: Optional[str] = None
    download_url: Optional[str] = None
