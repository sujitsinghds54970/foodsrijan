from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator

from app.utils.validators import sanitize_text, validate_password_strength, validate_phone, validate_username


class CEOCreateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=20)
    username: str = Field(min_length=4, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=12, max_length=128)
    password_confirm: str = Field(min_length=12, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, value):
        return sanitize_text(value)

    @field_validator("username")
    @classmethod
    def valid_username(cls, value):
        if not validate_username(value):
            raise ValueError("Username must be 4-30 alphanumeric characters or underscores")
        return value

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value):
        if not validate_phone(value):
            raise ValueError("Phone must be E.164 or a valid Indian mobile number")
        return value

    @field_validator("password")
    @classmethod
    def strong_password(cls, value):
        valid, errors = validate_password_strength(value)
        if not valid:
            raise ValueError("; ".join(errors))
        return value

    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, value, info: ValidationInfo):
        if info.data.get("password") and value != info.data["password"]:
            raise ValueError("Passwords do not match")
        return value


class CEOProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    is_active: bool | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, value):
        return sanitize_text(value)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value):
        if value and not validate_phone(value):
            raise ValueError("Phone must be E.164 or a valid Indian mobile number")
        return value


class CEOTestLoginRequest(BaseModel):
    username: str = Field(min_length=4, max_length=30)
    password: str = Field(min_length=1, max_length=128)
