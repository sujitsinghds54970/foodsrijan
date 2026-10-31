import re
from datetime import date
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationInfo, field_validator, model_validator

from app.utils.validators import (
    sanitize_text,
    validate_bank_account_number,
    validate_fssai,
    validate_gstin,
    validate_ifsc,
    validate_outlet_code,
    validate_password_strength,
    validate_phone,
    validate_slug,
    validate_time_hhmm,
    validate_upi_id,
    validate_url,
    validate_username,
)


OUTLET_TYPES = {
    "dine_in": "Dine-in",
    "takeaway": "Takeaway",
    "cloud_kitchen": "Cloud Kitchen",
    "kiosk": "Kiosk",
    "food_truck": "Food Truck",
    "cafe": "Cafe",
    "bakery": "Bakery",
    "bar": "Bar",
    "fine_dine": "Fine Dine",
    "qsr": "QSR",
    "buffet": "Buffet",
    "drive_through": "Drive-through",
    "other": "Other",
}
OUTLET_STATUSES = {
    "planning": "Planning",
    "setup": "Setup",
    "active": "Active",
    "temporarily_closed": "Temporarily Closed",
    "permanently_closed": "Permanently Closed",
}
OUTLET_REGIONS = {
    "north_india": "North India",
    "south_india": "South India",
    "east_india": "East India",
    "west_india": "West India",
    "international": "International",
}
OPERATING_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

OUTLET_TEXT_FIELDS = (
    "name", "description", "address_line_1", "address_line_2", "city", "state", "pincode",
    "trade_license", "fire_safety_certificate", "health_permit", "bank_account_name",
    "bank_name", "branch_name", "cost_center_code", "swiggy_store_id", "zomato_store_id",
)
OUTLET_URL_FIELDS = ("google_maps_url", "logo_url", "cover_photo_url")
UPLOAD_PATH_PATTERN = re.compile(r"^/(?:uploads|api/files)/[A-Za-z0-9_\-./]+$")


def normalize_choice(value: Any, choices: dict[str, str], label: str) -> str | None:
    if value is None or value == "":
        return None
    key = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
    if key not in choices:
        raise ValueError(f"Unsupported {label}")
    return key


def _valid_media_url(value: str | None) -> bool:
    if not value:
        return True
    if value.startswith("/"):
        return bool(UPLOAD_PATH_PATTERN.fullmatch(value)) and ".." not in value
    return validate_url(value)


def _sanitize(value):
    if isinstance(value, str):
        return sanitize_text(value)
    return value


class OutletFields(BaseModel):
    """Shared outlet validation. Scope fields such as company_id are never accepted."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=100)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=12)
    outlet_type: str | None = None
    status: str | None = None
    brand_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=5000)
    opening_date: date | None = None
    logo_url: str | None = Field(default=None, max_length=2048)
    cover_photo_url: str | None = Field(default=None, max_length=2048)

    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    pincode: str | None = Field(default=None, max_length=10)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    region: str | None = None
    timezone: str | None = Field(default=None, max_length=64)

    opening_time: str | None = None
    closing_time: str | None = None
    operating_days: list[str] | None = None
    seating_capacity: int | None = Field(default=None, ge=0, le=100000)
    kitchen_capacity: int | None = Field(default=None, ge=0, le=100000)
    is_delivery_enabled: bool | None = None
    is_dine_in_enabled: bool | None = None
    is_takeaway_enabled: bool | None = None
    delivery_radius_km: float | None = Field(default=None, ge=0, le=100)

    fssai_license: str | None = None
    gstin: str | None = None
    trade_license: str | None = Field(default=None, max_length=100)
    fire_safety_certificate: str | None = Field(default=None, max_length=100)
    health_permit: str | None = Field(default=None, max_length=100)
    license_expiry_date: date | None = None

    rent_amount: Decimal | None = Field(default=None, ge=0, le=999999999999)
    security_deposit: Decimal | None = Field(default=None, ge=0, le=999999999999)
    lease_start_date: date | None = None
    lease_end_date: date | None = None
    bank_account_name: str | None = Field(default=None, max_length=255)
    bank_account_number: str | None = None
    ifsc_code: str | None = None
    bank_name: str | None = Field(default=None, max_length=255)
    branch_name: str | None = Field(default=None, max_length=255)
    upi_id: str | None = Field(default=None, max_length=100)
    cost_center_code: str | None = Field(default=None, max_length=50)

    manager_contact_email: EmailStr | None = None
    manager_contact_phone: str | None = None
    outlet_email: EmailStr | None = None
    outlet_phone: str | None = None
    google_maps_url: str | None = Field(default=None, max_length=2048)
    swiggy_store_id: str | None = Field(default=None, max_length=64)
    zomato_store_id: str | None = Field(default=None, max_length=64)

    outlet_metadata: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator(*OUTLET_TEXT_FIELDS, mode="before")
    @classmethod
    def sanitize_text_fields(cls, value):
        return _sanitize(value)

    @field_validator("code", mode="before")
    @classmethod
    def valid_code(cls, value):
        if value is None:
            return None
        value = str(value).strip().upper()
        if not validate_outlet_code(value):
            raise ValueError("Outlet code must be 2-12 uppercase letters, digits or hyphens (e.g. MUM-001)")
        return value

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, value):
        if value and not validate_slug(value):
            raise ValueError("Slug must be lowercase words separated by hyphens")
        return value

    @field_validator("outlet_type", mode="before")
    @classmethod
    def valid_outlet_type(cls, value):
        return normalize_choice(value, OUTLET_TYPES, "outlet type")

    @field_validator("status", mode="before")
    @classmethod
    def valid_status(cls, value):
        return normalize_choice(value, OUTLET_STATUSES, "outlet status")

    @field_validator("region", mode="before")
    @classmethod
    def valid_region(cls, value):
        return normalize_choice(value, OUTLET_REGIONS, "region")

    @field_validator("country", mode="before")
    @classmethod
    def valid_country(cls, value):
        if value in (None, ""):
            return None
        value = str(value).strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", value):
            raise ValueError("Country must be an ISO 3166-1 alpha-2 code")
        return value

    @field_validator("pincode")
    @classmethod
    def valid_pincode(cls, value):
        if value and not re.fullmatch(r"[A-Za-z0-9 \-]{3,10}", value):
            raise ValueError("Invalid postal code")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        if not value:
            return value
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("Unknown timezone") from error
        return value

    @field_validator("opening_time", "closing_time")
    @classmethod
    def valid_time(cls, value):
        if value and not validate_time_hhmm(value):
            raise ValueError("Time must use 24-hour HH:MM format")
        return value

    @field_validator("operating_days", mode="before")
    @classmethod
    def valid_operating_days(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("Operating days must be a list")
        lookup = {day.lower(): day for day in OPERATING_DAYS}
        result = []
        for item in value:
            day = lookup.get(str(item).strip()[:3].lower())
            if day is None:
                raise ValueError("Operating days must be Mon-Sun")
            if day not in result:
                result.append(day)
        return sorted(result, key=OPERATING_DAYS.index)

    @field_validator("fssai_license", mode="before")
    @classmethod
    def valid_fssai(cls, value):
        if value in (None, ""):
            return None
        value = str(value).strip()
        if not validate_fssai(value):
            raise ValueError("FSSAI license must be exactly 14 digits")
        return value

    @field_validator("gstin", mode="before")
    @classmethod
    def valid_gstin(cls, value):
        if value in (None, ""):
            return None
        value = str(value).strip().upper()
        if not validate_gstin(value):
            raise ValueError("Invalid GSTIN format")
        return value

    @field_validator("ifsc_code", mode="before")
    @classmethod
    def valid_ifsc(cls, value):
        if value in (None, ""):
            return None
        value = str(value).strip().upper()
        if not validate_ifsc(value):
            raise ValueError("Invalid IFSC code")
        return value

    @field_validator("bank_account_number", mode="before")
    @classmethod
    def valid_bank_account(cls, value):
        if value in (None, ""):
            return None
        value = re.sub(r"\s+", "", str(value))
        if not validate_bank_account_number(value):
            raise ValueError("Bank account number must be 9-18 digits")
        return value

    @field_validator("upi_id")
    @classmethod
    def valid_upi(cls, value):
        if value and not validate_upi_id(value):
            raise ValueError("Invalid UPI ID")
        return value

    @field_validator("manager_contact_phone", "outlet_phone", mode="before")
    @classmethod
    def valid_phone_fields(cls, value):
        if value in (None, ""):
            return None
        value = re.sub(r"[\s\-()]", "", str(value))
        if not validate_phone(value):
            raise ValueError("Phone must be E.164 or a valid Indian mobile number")
        return value

    @field_validator("google_maps_url")
    @classmethod
    def valid_http_url(cls, value):
        if value and not validate_url(value):
            raise ValueError("URL must be an absolute http or https URL")
        return value

    @field_validator("logo_url", "cover_photo_url")
    @classmethod
    def valid_media(cls, value):
        if value and not _valid_media_url(value):
            raise ValueError("Media URL must be http(s) or an uploaded file path")
        return value

    @model_validator(mode="after")
    def valid_ranges(self):
        if self.lease_start_date and self.lease_end_date and self.lease_end_date < self.lease_start_date:
            raise ValueError("Lease end date must be on or after lease start date")
        return self


class OutletCreate(OutletFields):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=12)
    outlet_type: str
    address_line_1: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    pincode: str = Field(min_length=3, max_length=10)


class OutletUpdate(OutletFields):
    pass


class ManagerProfileFields(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = None
    manager_photo_url: str | None = Field(default=None, max_length=2048)
    manager_address: str | None = Field(default=None, max_length=2000)
    manager_bank_account_name: str | None = Field(default=None, max_length=255)
    manager_bank_account_number: str | None = None
    manager_ifsc_code: str | None = None
    manager_bank_name: str | None = Field(default=None, max_length=255)

    @field_validator("first_name", "last_name", "manager_address", "manager_bank_account_name", "manager_bank_name", mode="before")
    @classmethod
    def sanitize_fields(cls, value):
        return _sanitize(value)

    @field_validator("phone", mode="before")
    @classmethod
    def valid_phone(cls, value):
        if value in (None, ""):
            return None
        value = re.sub(r"[\s\-()]", "", str(value))
        if not validate_phone(value):
            raise ValueError("Phone must be E.164 or a valid Indian mobile number")
        return value

    @field_validator("manager_photo_url")
    @classmethod
    def valid_photo(cls, value):
        if value and not _valid_media_url(value):
            raise ValueError("Photo URL must be http(s) or an uploaded file path")
        return value

    @field_validator("manager_bank_account_number", mode="before")
    @classmethod
    def valid_bank_account(cls, value):
        if value in (None, ""):
            return None
        value = re.sub(r"\s+", "", str(value))
        if not validate_bank_account_number(value):
            raise ValueError("Bank account number must be 9-18 digits")
        return value

    @field_validator("manager_ifsc_code", mode="before")
    @classmethod
    def valid_ifsc(cls, value):
        if value in (None, ""):
            return None
        value = str(value).strip().upper()
        if not validate_ifsc(value):
            raise ValueError("Invalid IFSC code")
        return value


class ManagerCreate(ManagerProfileFields):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str
    username: str | None = Field(default=None, min_length=4, max_length=30)
    password: str | None = Field(default=None, min_length=1, max_length=128)
    password_confirm: str | None = Field(default=None, max_length=128)
    replace_existing: bool = False

    @field_validator("username")
    @classmethod
    def valid_username(cls, value):
        if value is not None and not validate_username(value):
            raise ValueError("Username must be 4-30 letters, digits or underscores")
        return value

    @field_validator("password")
    @classmethod
    def strong_password(cls, value):
        if value is None:
            return value
        valid, errors = validate_password_strength(value)
        if not valid:
            raise ValueError("; ".join(errors))
        return value

    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, value, info: ValidationInfo):
        password = info.data.get("password")
        if password and value != password:
            raise ValueError("Passwords do not match")
        return value


class ManagerUpdate(ManagerProfileFields):
    is_active: bool | None = None


class ManagerTestLogin(BaseModel):
    username: str = Field(min_length=4, max_length=30)
    password: str = Field(min_length=1, max_length=128)


class ManagerSelfUpdate(BaseModel):
    """Fields an outlet manager may change on their own account. Anything else is rejected."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = None
    display_name: str | None = Field(default=None, max_length=150)
    bio: str | None = Field(default=None, max_length=5000)
    manager_photo_url: str | None = Field(default=None, max_length=2048)
    profile_photo_url: str | None = Field(default=None, max_length=2048)
    cover_photo_url: str | None = Field(default=None, max_length=2048)
    manager_address: str | None = Field(default=None, max_length=2000)
    timezone: str | None = Field(default=None, max_length=64)
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = None
    preferred_contact_method: str | None = Field(default=None, pattern=r"^(email|phone|whatsapp|sms)$")
    preferences: dict[str, Any] | None = None

    @field_validator("first_name", "last_name", "display_name", "bio", "manager_address", "emergency_contact_name", mode="before")
    @classmethod
    def sanitize_fields(cls, value):
        return _sanitize(value)

    @field_validator("phone", "emergency_contact_phone", mode="before")
    @classmethod
    def valid_phone(cls, value):
        if value in (None, ""):
            return None
        value = re.sub(r"[\s\-()]", "", str(value))
        if not validate_phone(value):
            raise ValueError("Phone must be E.164 or a valid Indian mobile number")
        return value

    @field_validator("manager_photo_url", "profile_photo_url", "cover_photo_url")
    @classmethod
    def valid_photo(cls, value):
        if value and not _valid_media_url(value):
            raise ValueError("Photo URL must be http(s) or an uploaded file path")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        return OutletFields.valid_timezone(value)


class ManagerOutletUpdate(BaseModel):
    """Operational outlet fields an outlet manager may change. Identity, legal and financial data stay CEO-only."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    opening_time: str | None = None
    closing_time: str | None = None
    operating_days: list[str] | None = None
    seating_capacity: int | None = Field(default=None, ge=0, le=100000)
    kitchen_capacity: int | None = Field(default=None, ge=0, le=100000)
    is_delivery_enabled: bool | None = None
    is_dine_in_enabled: bool | None = None
    is_takeaway_enabled: bool | None = None
    delivery_radius_km: float | None = Field(default=None, ge=0, le=100)
    outlet_email: EmailStr | None = None
    outlet_phone: str | None = None
    manager_contact_email: EmailStr | None = None
    manager_contact_phone: str | None = None
    google_maps_url: str | None = Field(default=None, max_length=2048)
    description: str | None = Field(default=None, max_length=5000)

    _time = field_validator("opening_time", "closing_time")(OutletFields.valid_time.__func__)
    _days = field_validator("operating_days", mode="before")(OutletFields.valid_operating_days.__func__)
    _phones = field_validator("outlet_phone", "manager_contact_phone", mode="before")(OutletFields.valid_phone_fields.__func__)
    _url = field_validator("google_maps_url")(OutletFields.valid_http_url.__func__)
    _text = field_validator("description", mode="before")(OutletFields.sanitize_text_fields.__func__)
