from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationInfo, field_validator

from app.utils.validators import (
    sanitize_text,
    validate_fssai,
    validate_gstin,
    validate_pan,
    validate_phone,
    validate_slug,
    validate_url,
)


URL_FIELDS = (
    "logo_url",
    "favicon_url",
    "website_url",
    "linkedin_url",
    "instagram_url",
    "facebook_url",
    "twitter_url",
    "youtube_url",
    "mobile_app_url",
)
BUSINESS_DOMAINS = {
    "Restaurant",
    "Cafe",
    "Cloud Kitchen",
    "Bakery",
    "QSR",
    "Fine Dine",
    "Catering",
    "Food Manufacturing",
    "Food Delivery",
    "Other",
}
FUNDING_STAGES = {"Bootstrapped", "Seed", "Series A", "Series B", "Series C", "IPO", "Other"}


class CompanyFields(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=2, max_length=150)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    tagline: str | None = Field(default=None, max_length=255)
    description: str | None = None
    logo_url: str | None = Field(default=None, max_length=2048)
    favicon_url: str | None = Field(default=None, max_length=2048)
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    founded_date: date | None = None
    legal_name: str | None = Field(default=None, max_length=255)
    registration_number: str | None = Field(default=None, max_length=100)
    gstin: str | None = Field(default=None, max_length=15)
    pan_number: str | None = Field(default=None, max_length=10)
    fssai_license: str | None = Field(default=None, max_length=14)
    cin_number: str | None = Field(default=None, max_length=21)
    registered_address: str | None = None
    corporate_address: str | None = None
    bank_account_name: str | None = Field(default=None, max_length=255)
    bank_account_number: str | None = Field(default=None, max_length=100)
    ifsc_code: str | None = Field(default=None, max_length=11)
    bank_name: str | None = Field(default=None, max_length=255)
    annual_revenue_range: str | None = Field(default=None, pattern=r"^(<1Cr|1-10Cr|10-100Cr|100Cr\+)$")
    funding_stage: str | None = Field(default=None, max_length=40)
    headquarters_city: str | None = Field(default=None, max_length=120)
    headquarters_state: str | None = Field(default=None, max_length=120)
    headquarters_country: str | None = Field(default=None, max_length=120)
    headquarters_pincode: str | None = Field(default=None, max_length=20)
    operating_regions: list[str] | None = None
    number_of_branches: int | None = Field(default=None, ge=0)
    website_url: str | None = Field(default=None, max_length=2048)
    linkedin_url: str | None = Field(default=None, max_length=2048)
    instagram_url: str | None = Field(default=None, max_length=2048)
    facebook_url: str | None = Field(default=None, max_length=2048)
    twitter_url: str | None = Field(default=None, max_length=2048)
    youtube_url: str | None = Field(default=None, max_length=2048)
    mobile_app_url: str | None = Field(default=None, max_length=2048)
    support_email: EmailStr | None = None
    support_phone: str | None = Field(default=None, max_length=32)
    business_domain: str | None = Field(default=None, max_length=64)
    sub_domains: list[str] | None = None
    target_market: str | None = Field(default=None, pattern=r"^(B2C|B2B|Both)$")
    employee_count_estimate: str | None = Field(default=None, max_length=32)
    business_description: str | None = None
    status: str | None = Field(default=None, pattern=r"^(active|inactive|suspended|archived)$")
    onboarding_status: str | None = Field(default=None, pattern=r"^(pending|in_progress|complete)$")
    company_metadata: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator(
        "name", "tagline", "description", "legal_name", "registration_number",
        "cin_number", "registered_address", "corporate_address", "bank_account_name",
        "bank_account_number", "ifsc_code", "bank_name", "headquarters_city",
        "headquarters_state", "headquarters_country", "headquarters_pincode",
        "business_domain", "employee_count_estimate", "business_description",
        "support_phone", mode="before",
    )
    @classmethod
    def sanitize_string_fields(cls, value):
        return sanitize_text(value)

    @field_validator("gstin")
    @classmethod
    def valid_gstin(cls, value):
        if value and not validate_gstin(value):
            raise ValueError("Invalid GSTIN format")
        return value

    @field_validator("pan_number")
    @classmethod
    def valid_pan(cls, value):
        if value and not validate_pan(value):
            raise ValueError("Invalid PAN format")
        return value

    @field_validator("fssai_license")
    @classmethod
    def valid_fssai(cls, value):
        if value and not validate_fssai(value):
            raise ValueError("Invalid FSSAI license format")
        return value

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, value):
        if value and not validate_slug(value):
            raise ValueError("Slug must be lowercase words separated by hyphens")
        return value

    @field_validator(*URL_FIELDS)
    @classmethod
    def valid_http_url(cls, value):
        if value and not validate_url(value):
            raise ValueError("URL must be an absolute http or https URL")
        return value

    @field_validator("support_phone")
    @classmethod
    def valid_support_phone(cls, value):
        if value and not validate_phone(value):
            raise ValueError("Phone must be E.164 or a valid Indian mobile number")
        return value

    @field_validator("business_domain")
    @classmethod
    def valid_business_domain(cls, value):
        if value and value not in BUSINESS_DOMAINS:
            raise ValueError("Unsupported business domain")
        return value

    @field_validator("funding_stage")
    @classmethod
    def valid_funding_stage(cls, value):
        if value and value not in FUNDING_STAGES:
            raise ValueError("Unsupported funding stage")
        return value

    @field_validator("operating_regions", "sub_domains")
    @classmethod
    def sanitize_list_values(cls, value):
        return [sanitize_text(item) for item in value] if value is not None else None


class CompanyCreate(CompanyFields):
    pass


class CompanyUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=2, max_length=150)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    tagline: str | None = Field(default=None, max_length=255)
    description: str | None = None
    logo_url: str | None = Field(default=None, max_length=2048)
    favicon_url: str | None = Field(default=None, max_length=2048)
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    founded_date: date | None = None
    legal_name: str | None = Field(default=None, max_length=255)
    registration_number: str | None = Field(default=None, max_length=100)
    gstin: str | None = Field(default=None, max_length=15)
    pan_number: str | None = Field(default=None, max_length=10)
    fssai_license: str | None = Field(default=None, max_length=14)
    cin_number: str | None = Field(default=None, max_length=21)
    registered_address: str | None = None
    corporate_address: str | None = None
    bank_account_name: str | None = Field(default=None, max_length=255)
    bank_account_number: str | None = Field(default=None, max_length=100)
    ifsc_code: str | None = Field(default=None, max_length=11)
    bank_name: str | None = Field(default=None, max_length=255)
    annual_revenue_range: str | None = Field(default=None, pattern=r"^(<1Cr|1-10Cr|10-100Cr|100Cr\+)$")
    funding_stage: str | None = Field(default=None, max_length=40)
    headquarters_city: str | None = Field(default=None, max_length=120)
    headquarters_state: str | None = Field(default=None, max_length=120)
    headquarters_country: str | None = Field(default=None, max_length=120)
    headquarters_pincode: str | None = Field(default=None, max_length=20)
    operating_regions: list[str] | None = None
    number_of_branches: int | None = Field(default=None, ge=0)
    website_url: str | None = Field(default=None, max_length=2048)
    linkedin_url: str | None = Field(default=None, max_length=2048)
    instagram_url: str | None = Field(default=None, max_length=2048)
    facebook_url: str | None = Field(default=None, max_length=2048)
    twitter_url: str | None = Field(default=None, max_length=2048)
    youtube_url: str | None = Field(default=None, max_length=2048)
    mobile_app_url: str | None = Field(default=None, max_length=2048)
    support_email: EmailStr | None = None
    support_phone: str | None = Field(default=None, max_length=32)
    business_domain: str | None = Field(default=None, max_length=64)
    sub_domains: list[str] | None = None
    target_market: str | None = Field(default=None, pattern=r"^(B2C|B2B|Both)$")
    employee_count_estimate: str | None = Field(default=None, max_length=32)
    business_description: str | None = None
    status: str | None = Field(default=None, pattern=r"^(active|inactive|suspended|archived)$")
    onboarding_status: str | None = Field(default=None, pattern=r"^(pending|in_progress|complete)$")
    company_metadata: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("*", mode="before")
    @classmethod
    def sanitize_text_values(cls, value, info: ValidationInfo):
        if isinstance(value, str) and info.field_name not in URL_FIELDS and info.field_name not in {"gstin", "pan_number", "fssai_license", "primary_color", "secondary_color", "target_market", "annual_revenue_range", "status", "onboarding_status"}:
            return sanitize_text(value)
        return value

    @field_validator("gstin")
    @classmethod
    def valid_gstin(cls, value):
        if value and not validate_gstin(value):
            raise ValueError("Invalid GSTIN format")
        return value

    @field_validator("pan_number")
    @classmethod
    def valid_pan(cls, value):
        if value and not validate_pan(value):
            raise ValueError("Invalid PAN format")
        return value

    @field_validator("fssai_license")
    @classmethod
    def valid_fssai(cls, value):
        if value and not validate_fssai(value):
            raise ValueError("Invalid FSSAI license format")
        return value

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, value):
        if value and not validate_slug(value):
            raise ValueError("Slug must be lowercase words separated by hyphens")
        return value

    @field_validator(*URL_FIELDS)
    @classmethod
    def valid_http_url(cls, value):
        if value and not validate_url(value):
            raise ValueError("URL must be an absolute http or https URL")
        return value

    @field_validator("support_phone")
    @classmethod
    def valid_support_phone(cls, value):
        if value and not validate_phone(value):
            raise ValueError("Phone must be E.164 or a valid Indian mobile number")
        return value

    @field_validator("business_domain")
    @classmethod
    def valid_business_domain(cls, value):
        if value and value not in BUSINESS_DOMAINS:
            raise ValueError("Unsupported business domain")
        return value

    @field_validator("funding_stage")
    @classmethod
    def valid_funding_stage(cls, value):
        if value and value not in FUNDING_STAGES:
            raise ValueError("Unsupported funding stage")
        return value

    @field_validator("operating_regions", "sub_domains")
    @classmethod
    def sanitize_list_fields(cls, value):
        return [sanitize_text(item) for item in value] if value is not None else None

class CompanyListResponse(BaseModel):
    companies: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
