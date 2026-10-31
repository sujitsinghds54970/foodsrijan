import re
from urllib.parse import urlsplit


GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
FSSAI_PATTERN = re.compile(r"^[0-9]{14}$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{4,30}$")
PHONE_PATTERN = re.compile(r"^(?:\+[1-9]\d{7,14}|(?:\+?91)?[6-9]\d{9})$")
IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
BANK_ACCOUNT_PATTERN = re.compile(r"^[0-9]{9,18}$")
UPI_PATTERN = re.compile(r"^[A-Za-z0-9.\-_]{2,256}@[A-Za-z][A-Za-z0-9]{1,64}$")
OUTLET_CODE_PATTERN = re.compile(r"^[A-Z0-9](?:[A-Z0-9-]{0,10}[A-Z0-9])?$")
TIME_HHMM_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
SQL_COMMAND_PATTERN = re.compile(
    r"\b(?:SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+TABLE|"
    r"ALTER\s+TABLE|UNION\s+SELECT|EXEC(?:UTE)?)\b\s+[^.!?]*?(?:--|/\*|;)",
    re.IGNORECASE,
)
HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
ACTIVE_CONTENT_PATTERN = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]")


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    errors = []
    if len(password) < 12:
        errors.append("Password must be at least 12 characters")
    if len(password.encode("utf-8")) > 72:
        errors.append("Password must not exceed 72 UTF-8 bytes for bcrypt")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    if not re.search(r"""[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/~`';]""", password):
        errors.append("Password must contain at least one symbol")
    return not errors, errors


def validate_gstin(value: str | None) -> bool:
    return bool(GSTIN_PATTERN.fullmatch(value or ""))


def validate_pan(value: str | None) -> bool:
    return bool(PAN_PATTERN.fullmatch(value or ""))


def validate_fssai(value: str | None) -> bool:
    return bool(FSSAI_PATTERN.fullmatch(value or ""))


def validate_url(value: str | None) -> bool:
    if not value:
        return True
    try:
        parsed = urlsplit(value)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def sanitize_text(value: str | None) -> str | None:
    if value is None:
        return None
    without_active_content = ACTIVE_CONTENT_PATTERN.sub("", value)
    cleaned = CONTROL_PATTERN.sub("", HTML_TAG_PATTERN.sub("", without_active_content))
    if SQL_COMMAND_PATTERN.search(cleaned):
        raise ValueError("Text contains a disallowed SQL statement")
    return cleaned.strip()


def validate_slug(value: str | None) -> bool:
    return bool(SLUG_PATTERN.fullmatch(value or ""))


def validate_phone(value: str | None) -> bool:
    return bool(PHONE_PATTERN.fullmatch(value or ""))


def validate_username(value: str | None) -> bool:
    return bool(USERNAME_PATTERN.fullmatch(value or ""))


def validate_ifsc(value: str | None) -> bool:
    return bool(IFSC_PATTERN.fullmatch(value or ""))


def validate_bank_account_number(value: str | None) -> bool:
    return bool(BANK_ACCOUNT_PATTERN.fullmatch(value or ""))


def validate_upi_id(value: str | None) -> bool:
    return bool(UPI_PATTERN.fullmatch(value or ""))


def validate_outlet_code(value: str | None) -> bool:
    return bool(OUTLET_CODE_PATTERN.fullmatch(value or ""))


def validate_time_hhmm(value: str | None) -> bool:
    return bool(TIME_HHMM_PATTERN.fullmatch(value or ""))
