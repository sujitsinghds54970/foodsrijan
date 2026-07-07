"""
Pydantic Schemas for Daily Entry Module
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal

class DailyEntryBase(BaseModel):
    patient_name: str = Field(..., min_length=1, max_length=200)
    mobile: str = Field(..., min_length=10, max_length=15)
    address: str = Field(..., min_length=1)
    referred_doctor: Optional[str] = Field(None, max_length=200)
    test_name: str = Field(..., min_length=1, max_length=500)
    fee_amount: Decimal = Field(..., gt=0)
    tax_percent: float = Field(0, ge=0, le=100)
    payment_method: str = Field(..., pattern="^(Cash|UPI|QR|Card|Online)$")
    is_paid: bool = True
    remarks: Optional[str] = None

    @validator('mobile')
    def validate_mobile(cls, v):
        if not v.isdigit():
            raise ValueError('Mobile must contain only digits')
        return v

    @validator('tax_percent')
    def validate_tax(cls, v):
        if v not in [0, 5, 12, 18]:
            raise ValueError('Tax percent must be 0, 5, 12, or 18')
        return v


class DailyEntryCreate(DailyEntryBase):
    auto_entry_datetime: Optional[str] = None


class DailyEntryUpdate(BaseModel):
    patient_name: Optional[str] = Field(None, min_length=1, max_length=200)
    mobile: Optional[str] = Field(None, min_length=10, max_length=15)
    address: Optional[str] = None
    referred_doctor: Optional[str] = Field(None, max_length=200)
    test_name: Optional[str] = Field(None, min_length=1, max_length=500)
    fee_amount: Optional[Decimal] = Field(None, gt=0)
    tax_percent: Optional[float] = Field(None, ge=0, le=100)
    payment_method: Optional[str] = Field(None, pattern="^(Cash|UPI|QR|Card|Online)$")
    is_paid: Optional[bool] = None
    remarks: Optional[str] = None
    report_pdf_url: Optional[str] = None
    auto_entry_datetime: Optional[str] = None


class DailyEntryResponse(DailyEntryBase):
    id: int
    branch_id: int
    auto_patient_id: str
    auto_entry_datetime: datetime
    total_amount: Decimal
    report_pdf_url: Optional[str]
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DailyExpenseBase(BaseModel):
    expense_item: str = Field(..., min_length=1, max_length=200)
    cost: Decimal = Field(..., gt=0)
    description: Optional[str] = None


class DailyExpenseCreate(DailyExpenseBase):
    entry_date: Optional[datetime] = None


class DailyExpenseUpdate(BaseModel):
    expense_item: Optional[str] = Field(None, min_length=1, max_length=200)
    cost: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None
    entry_date: Optional[datetime] = None


class DailyExpenseResponse(DailyExpenseBase):
    id: int
    branch_id: int
    entry_date: datetime
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DailyStatsResponse(BaseModel):
    total_revenue: Decimal
    total_expense: Decimal
    net_profit: Decimal
    patient_count: int
    date: str
