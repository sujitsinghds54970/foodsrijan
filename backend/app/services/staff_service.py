from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
import re
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Branch, User
from app.models.hr import StaffProfile
from app.services.company_service import generate_secure_password
from app.services.outlet_service import credentials_payload, write_audit
from app.utils.auth_system import auth_guard
from app.utils.validators import validate_ifsc, validate_pan, validate_phone, validate_password_strength, validate_upi_id


STAFF_ROLES = {
    "chef",
    "sous_chef",
    "kitchen_helper",
    "waiter",
    "cashier",
    "barista",
    "delivery_rider",
    "cleaner",
    "store_keeper",
    "shift_supervisor",
    "other",
}
EMPLOYMENT_TYPES = {"full_time", "part_time", "contract", "intern", "probation"}
SALARY_TYPES = {"monthly", "daily", "hourly"}
PII_FIELDS = {
    "aadhaar_number",
    "pan_number",
    "voter_id",
    "driving_license",
    "passport_number",
    "bank_account_name",
    "bank_account_number",
    "ifsc_code",
    "bank_name",
    "branch_name",
    "upi_id",
    "monthly_salary",
    "daily_wage",
    "hourly_rate",
}
STAFF_MUTABLE_MANAGER_FIELDS = {
    "first_name",
    "last_name",
    "display_name",
    "email",
    "phone",
    "alternate_phone",
    "date_of_birth",
    "gender",
    "blood_group",
    "marital_status",
    "profile_photo_url",
    "current_address",
    "permanent_address",
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relation",
    "aadhaar_number",
    "pan_number",
    "voter_id",
    "driving_license",
    "passport_number",
    "bank_account_name",
    "bank_account_number",
    "ifsc_code",
    "bank_name",
    "branch_name",
    "upi_id",
    "qualifications",
    "certifications",
    "experience_years",
    "previous_employer",
    "skills",
    "joining_date",
    "employment_type",
    "probation_end_date",
    "salary_type",
    "monthly_salary",
    "daily_wage",
    "hourly_rate",
    "shift_preference",
    "weekly_off_day",
    "pf_applicable",
    "esi_applicable",
    "tds_applicable",
    "staff_role",
    "employee_code",
    "manager_id",
    "is_active",
}
STAFF_MUTABLE_SELF_FIELDS = {
    "first_name",
    "last_name",
    "display_name",
    "email",
    "phone",
    "alternate_phone",
    "date_of_birth",
    "gender",
    "blood_group",
    "marital_status",
    "profile_photo_url",
    "current_address",
    "permanent_address",
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relation",
    "bank_account_name",
    "bank_account_number",
    "ifsc_code",
    "bank_name",
    "branch_name",
    "upi_id",
    "qualifications",
    "certifications",
    "experience_years",
    "previous_employer",
    "skills",
    "shift_preference",
    "weekly_off_day",
}
SELF_PROTECTED_FIELDS = {"staff_role", "salary_type", "monthly_salary", "daily_wage", "hourly_rate", "employment_type", "company_id", "outlet_id", "employee_code", "manager_id"}
PLACEHOLDER_EMAIL_DOMAIN = "local.staff.invalid"
AADHAAR_PATTERN = re.compile(r"^\d{12}$")


def _now() -> datetime:
    return datetime.utcnow()


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().lower()
    return cleaned or None


def public_email(user: User) -> str | None:
    email = normalize_email(getattr(user, "email", None))
    if email and email.endswith(f"@{PLACEHOLDER_EMAIL_DOMAIN}") and user.is_staff:
        return None
    return getattr(user, "email", None)


def synthesized_staff_email(company_id: int, outlet_id: int, employee_code: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", employee_code.strip().lower()).strip("-") or "staff"
    return f"staff-{company_id}-{outlet_id}-{token}@{PLACEHOLDER_EMAIL_DOMAIN}"


def validate_staff_pii(changes: dict[str, Any]) -> None:
    if "phone" in changes and changes["phone"] and not validate_phone(str(changes["phone"])):
        raise HTTPException(status_code=422, detail="Invalid phone number")
    if "alternate_phone" in changes and changes["alternate_phone"] and not validate_phone(str(changes["alternate_phone"])):
        raise HTTPException(status_code=422, detail="Invalid alternate phone number")
    if "emergency_contact_phone" in changes and changes["emergency_contact_phone"] and not validate_phone(str(changes["emergency_contact_phone"])):
        raise HTTPException(status_code=422, detail="Invalid emergency contact phone number")
    if "aadhaar_number" in changes and changes["aadhaar_number"] and not AADHAAR_PATTERN.fullmatch(str(changes["aadhaar_number"]).strip()):
        raise HTTPException(status_code=422, detail="Invalid Aadhaar number")
    if "pan_number" in changes and changes["pan_number"] and not validate_pan(str(changes["pan_number"]).strip().upper()):
        raise HTTPException(status_code=422, detail="Invalid PAN number")
    if "ifsc_code" in changes and changes["ifsc_code"] and not validate_ifsc(str(changes["ifsc_code"]).strip().upper()):
        raise HTTPException(status_code=422, detail="Invalid IFSC code")
    if "upi_id" in changes and changes["upi_id"] and not validate_upi_id(str(changes["upi_id"]).strip()):
        raise HTTPException(status_code=422, detail="Invalid UPI ID")
    if "staff_role" in changes and changes["staff_role"] and str(changes["staff_role"]).strip().lower() not in STAFF_ROLES:
        raise HTTPException(status_code=422, detail="Invalid staff role")
    if "employment_type" in changes and changes["employment_type"] and str(changes["employment_type"]).strip().lower() not in EMPLOYMENT_TYPES:
        raise HTTPException(status_code=422, detail="Invalid employment type")
    if "salary_type" in changes and changes["salary_type"] and str(changes["salary_type"]).strip().lower() not in SALARY_TYPES:
        raise HTTPException(status_code=422, detail="Invalid salary type")


def _normalize_changes(changes: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(changes)
    for key in ("email", "phone", "alternate_phone", "emergency_contact_phone", "upi_id"):
        if key in normalized and isinstance(normalized[key], str):
            normalized[key] = normalized[key].strip() or None
    for key in ("pan_number", "ifsc_code"):
        if key in normalized and isinstance(normalized[key], str) and normalized[key].strip():
            normalized[key] = normalized[key].strip().upper()
    for key in ("employee_code", "staff_role", "employment_type", "salary_type", "weekly_off_day"):
        if key in normalized and isinstance(normalized[key], str) and normalized[key].strip():
            normalized[key] = normalized[key].strip().lower()
    for key in ("aadhaar_number", "voter_id", "driving_license", "passport_number"):
        if key in normalized and isinstance(normalized[key], str):
            normalized[key] = normalized[key].strip() or None
    return normalized


def _query_scoped_staff(db: Session, company_id: int, outlet_id: int):
    return db.query(User).filter(
        User.company_id == company_id,
        User.outlet_id == outlet_id,
        User.is_staff.is_(True),
    )


def get_scoped_staff(db: Session, company_id: int, outlet_id: int, staff_id: int, *, include_deleted: bool = False) -> User:
    query = _query_scoped_staff(db, company_id, outlet_id).filter(User.id == staff_id)
    if not include_deleted:
        query = query.filter(User.is_deleted.is_(False))
    staff = query.first()
    if staff is None:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return staff


def list_scoped_staff(db: Session, company_id: int, outlet_id: int):
    return _query_scoped_staff(db, company_id, outlet_id).filter(User.is_deleted.is_(False))


def _mask_keep_last(value: Any, visible: int = 4, prefix: str = "*") -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    keep = text[-visible:] if len(text) > visible else text
    return f"{prefix * max(len(text) - len(keep), 4)}{keep}"


def mask_aadhaar(value: Any) -> str | None:
    text = re.sub(r"\D", "", str(value or ""))
    if not text:
        return None
    last4 = text[-4:]
    return f"XXXX-XXXX-{last4}"


def mask_pan(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    return f"XXXXX{text[-5:]}"


def mask_money(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return "******"


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def serialize_staff(staff: User, *, masked: bool, include_private_email: bool = False, include_sensitive_fields: bool = True) -> dict[str, Any]:
    data = {
        "id": staff.id,
        "username": staff.username,
        "email": staff.email if include_private_email else public_email(staff),
        "phone": staff.phone,
        "first_name": staff.first_name,
        "last_name": staff.last_name,
        "display_name": staff.display_name,
        "company_id": staff.company_id,
        "outlet_id": staff.outlet_id,
        "branch_id": staff.branch_id,
        "manager_id": staff.manager_id,
        "is_staff": bool(staff.is_staff),
        "staff_role": staff.staff_role,
        "employee_code": staff.employee_code,
        "staff_assigned_at": _json_value(staff.staff_assigned_at),
        "staff_assigned_by": staff.staff_assigned_by,
        "alternate_phone": staff.alternate_phone,
        "date_of_birth": _json_value(staff.date_of_birth),
        "gender": staff.gender,
        "blood_group": staff.blood_group,
        "marital_status": staff.marital_status,
        "profile_photo_url": staff.profile_photo_url,
        "current_address": staff.current_address,
        "permanent_address": staff.permanent_address,
        "emergency_contact_name": staff.emergency_contact_name,
        "emergency_contact_phone": staff.emergency_contact_phone,
        "emergency_contact_relation": staff.emergency_contact_relation,
        "qualifications": staff.qualifications or [],
        "certifications": staff.certifications or [],
        "experience_years": staff.experience_years,
        "previous_employer": staff.previous_employer,
        "skills": staff.skills or [],
        "joining_date": _json_value(staff.joining_date),
        "employment_type": staff.employment_type,
        "probation_end_date": _json_value(staff.probation_end_date),
        "salary_type": staff.salary_type,
        "shift_preference": staff.shift_preference,
        "weekly_off_day": staff.weekly_off_day,
        "pf_applicable": bool(staff.pf_applicable),
        "esi_applicable": bool(staff.esi_applicable),
        "tds_applicable": bool(staff.tds_applicable),
        "is_active": bool(staff.is_active),
        "force_password_change": bool(staff.force_password_change),
        "password_changed_at": _json_value(staff.password_changed_at),
        "deactivated_at": _json_value(staff.deactivated_at),
        "deactivated_reason": staff.deactivated_reason,
        "created_by": staff.created_by,
        "created_at": _json_value(staff.created_at),
        "updated_at": _json_value(staff.updated_at),
        "deleted_at": _json_value(staff.deleted_at),
        "is_deleted": bool(staff.is_deleted),
    }
    if include_sensitive_fields:
        if masked:
            data.update(
                {
                    "aadhaar_number": mask_aadhaar(staff.aadhaar_number),
                    "pan_number": mask_pan(staff.pan_number),
                    "voter_id": _mask_keep_last(staff.voter_id),
                    "driving_license": _mask_keep_last(staff.driving_license),
                    "passport_number": _mask_keep_last(staff.passport_number),
                    "bank_account_name": _mask_keep_last(staff.bank_account_name, visible=2),
                    "bank_account_number": _mask_keep_last(staff.bank_account_number),
                    "ifsc_code": _mask_keep_last(staff.ifsc_code, visible=4),
                    "bank_name": staff.bank_name,
                    "branch_name": staff.branch_name,
                    "upi_id": _mask_keep_last(staff.upi_id),
                    "monthly_salary": mask_money(staff.monthly_salary),
                    "daily_wage": mask_money(staff.daily_wage),
                    "hourly_rate": mask_money(staff.hourly_rate),
                }
            )
        else:
            data.update(
                {
                    "aadhaar_number": staff.aadhaar_number,
                    "pan_number": staff.pan_number,
                    "voter_id": staff.voter_id,
                    "driving_license": staff.driving_license,
                    "passport_number": staff.passport_number,
                    "bank_account_name": staff.bank_account_name,
                    "bank_account_number": staff.bank_account_number,
                    "ifsc_code": staff.ifsc_code,
                    "bank_name": staff.bank_name,
                    "branch_name": staff.branch_name,
                    "upi_id": staff.upi_id,
                    "monthly_salary": _json_value(staff.monthly_salary),
                    "daily_wage": _json_value(staff.daily_wage),
                    "hourly_rate": _json_value(staff.hourly_rate),
                }
            )
    return data


def serialize_staff_list_item(staff: User) -> dict[str, Any]:
    row = serialize_staff(staff, masked=True, include_sensitive_fields=True)
    for key in ("current_address", "permanent_address", "emergency_contact_name", "emergency_contact_phone", "emergency_contact_relation"):
        row.pop(key, None)
    return row


def _ensure_staff_uniques(db: Session, *, phone: str, email: str | None, employee_code: str, outlet_id: int, aadhaar_number: str | None, exclude_user_id: int | None = None) -> None:
    phone_query = db.query(User.id).filter(User.phone == phone, User.is_staff.is_(True), User.is_deleted.is_(False))
    if exclude_user_id is not None:
        phone_query = phone_query.filter(User.id != exclude_user_id)
    if phone_query.first():
        raise HTTPException(status_code=409, detail="Phone already exists")

    if email:
        email_query = db.query(User.id).filter(func.lower(User.email) == email.lower())
        if exclude_user_id is not None:
            email_query = email_query.filter(User.id != exclude_user_id)
        if email_query.first():
            raise HTTPException(status_code=409, detail="Email already exists")

    code_query = db.query(User.id).filter(
        User.outlet_id == outlet_id,
        func.lower(User.employee_code) == employee_code.lower(),
        User.is_staff.is_(True),
        User.is_deleted.is_(False),
    )
    if exclude_user_id is not None:
        code_query = code_query.filter(User.id != exclude_user_id)
    if code_query.first():
        raise HTTPException(status_code=409, detail="Employee code already exists")

    if aadhaar_number:
        aadhaar_query = db.query(User.id).filter(
            User.aadhaar_number == aadhaar_number,
            User.is_staff.is_(True),
            User.is_deleted.is_(False),
        )
        if exclude_user_id is not None:
            aadhaar_query = aadhaar_query.filter(User.id != exclude_user_id)
        if aadhaar_query.first():
            raise HTTPException(status_code=409, detail="Aadhaar number already exists")


def _suggest_staff_username(db: Session, outlet: Branch, first_name: str, last_name: str, employee_code: str) -> str:
    seed = "_".join(part for part in [first_name, last_name, employee_code] if part).lower()
    base = re.sub(r"[^a-z0-9_]+", "_", seed).strip("_")[:24] or re.sub(r"[^a-z0-9_]+", "_", (outlet.code or "staff").lower())
    candidate = base
    suffix = 2
    while db.query(User.id).filter(func.lower(User.username) == candidate.lower()).first():
        candidate = f"{base[:20]}_{suffix}"[:30]
        suffix += 1
    return candidate[:30]


def _profile_employee_id(user: User) -> str:
    return f"{user.outlet_id}-{user.employee_code}"[:30]


def sync_staff_profile(db: Session, staff: User, actor_id: int) -> StaffProfile:
    profile = db.query(StaffProfile).filter(StaffProfile.user_id == staff.id).first()
    if profile is None:
        profile = StaffProfile(
            user_id=staff.id,
            branch_id=staff.outlet_id,
            created_by=actor_id,
            staff_employee_id=_profile_employee_id(staff),
        )
        db.add(profile)
    profile.branch_id = staff.outlet_id
    profile.reporting_manager_id = staff.manager_id
    profile.staff_employee_id = _profile_employee_id(staff)
    profile.photo_path = staff.profile_photo_url
    profile.department = (staff.staff_role or "").replace("_", " ").title() or None
    profile.specialization = staff.staff_role
    profile.shift_timings = staff.shift_preference
    profile.date_of_joining = datetime.combine(staff.joining_date, time.min) if staff.joining_date else None
    profile.address = staff.current_address
    profile.emergency_contact = staff.emergency_contact_phone
    profile.is_active = staff.is_active and not staff.is_deleted
    return profile


def create_staff(db: Session, actor: User, outlet: Branch, request: Request, payload: dict[str, Any]) -> tuple[User, str]:
    values = _normalize_changes(payload)
    validate_staff_pii(values)
    password = values.pop("password", None) or generate_secure_password()
    valid_password, password_errors = validate_password_strength(password)
    if not valid_password:
        raise HTTPException(status_code=422, detail=password_errors)
    email = normalize_email(values.get("email"))
    employee_code = str(values.get("employee_code") or "").strip().lower()
    if not employee_code:
        raise HTTPException(status_code=422, detail="employee_code is required")
    phone = str(values.get("phone") or "").strip()
    if not phone:
        raise HTTPException(status_code=422, detail="phone is required")
    _ensure_staff_uniques(
        db,
        phone=phone,
        email=email,
        employee_code=employee_code,
        outlet_id=outlet.id,
        aadhaar_number=values.get("aadhaar_number"),
    )
    username = str(values.get("username") or _suggest_staff_username(db, outlet, values["first_name"], values["last_name"], employee_code)).strip()
    if db.query(User.id).filter(func.lower(User.username) == username.lower()).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    stored_email = email or synthesized_staff_email(actor.company_id, outlet.id, employee_code)
    now = _now()
    user_values = {
        key: value
        for key, value in values.items()
        if key
        not in {"username", "email", "phone", "employee_code", "password"}
        and (key in STAFF_MUTABLE_MANAGER_FIELDS or key in {"first_name", "last_name", "display_name", "date_of_birth", "gender", "qualifications", "certifications"})
    }
    staff = User(
        username=username,
        email=stored_email,
        hashed_password=auth_guard.hash_password(password),
        role="staff",
        company_id=actor.company_id,
        current_company_id=actor.company_id,
        branch_id=outlet.id,
        outlet_id=outlet.id,
        is_staff=True,
        is_active=True,
        force_password_change=True,
        password_changed_at=None,
        staff_assigned_at=now,
        staff_assigned_by=actor.id,
        manager_id=actor.id,
        created_by=actor.id,
        employee_code=employee_code,
        **user_values,
    )
    staff.email = stored_email
    staff.phone = phone
    staff.employee_code = employee_code
    staff.staff_role = values.get("staff_role")
    db.add(staff)
    try:
        db.flush()
        sync_staff_profile(db, staff, actor.id)
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Staff username, email, phone, or employee code already exists") from exc
    write_audit(
        db,
        actor,
        request,
        "staff.created",
        resource_type="user",
        resource_id=staff.id,
        company_id=actor.company_id,
        outlet_id=outlet.id,
        changes={"fields": sorted(k for k, v in values.items() if v is not None)},
        extra={"username": staff.username, "employee_code": staff.employee_code},
        response_status=201,
    )
    db.commit()
    db.refresh(staff)
    return staff, password


def update_staff(db: Session, actor: User, request: Request, staff: User, changes: dict[str, Any], *, self_service: bool = False) -> User:
    allowed_fields = STAFF_MUTABLE_SELF_FIELDS if self_service else STAFF_MUTABLE_MANAGER_FIELDS
    filtered = {key: value for key, value in _normalize_changes(changes).items() if key in allowed_fields}
    validate_staff_pii(filtered)

    if "password" in filtered:
        filtered.pop("password", None)

    if "email" in filtered:
        filtered["email"] = normalize_email(filtered["email"])
    employee_code = filtered.get("employee_code", staff.employee_code)
    phone = filtered.get("phone", staff.phone)
    aadhaar_number = filtered.get("aadhaar_number", staff.aadhaar_number)
    _ensure_staff_uniques(
        db,
        phone=phone,
        email=filtered.get("email") if "email" in filtered else public_email(staff),
        employee_code=employee_code,
        outlet_id=staff.outlet_id,
        aadhaar_number=aadhaar_number,
        exclude_user_id=staff.id,
    )

    changed_fields: list[str] = []
    for key, value in filtered.items():
        if key == "email" and value is None:
            value = synthesized_staff_email(staff.company_id, staff.outlet_id, staff.employee_code)
        if getattr(staff, key) != value:
            setattr(staff, key, value)
            changed_fields.append(key)

    if not changed_fields:
        return staff

    if self_service:
        for protected in SELF_PROTECTED_FIELDS:
            changes.pop(protected, None)
    sync_staff_profile(db, staff, actor.id)
    write_audit(
        db,
        actor,
        request,
        "staff.updated",
        resource_type="user",
        resource_id=staff.id,
        company_id=staff.company_id,
        outlet_id=staff.outlet_id,
        changes={"fields": sorted(changed_fields)},
        extra={"self_service": self_service},
    )
    db.commit()
    db.refresh(staff)
    return staff


def deactivate_staff(db: Session, actor: User, request: Request, staff: User, reason: str | None) -> User:
    now = _now()
    staff.is_active = False
    staff.is_deleted = True
    staff.deleted_at = now
    staff.deactivated_at = now
    staff.deactivated_reason = (reason or "").strip() or None
    profile = sync_staff_profile(db, staff, actor.id)
    profile.is_active = False
    write_audit(
        db,
        actor,
        request,
        "staff.deactivated",
        resource_type="user",
        resource_id=staff.id,
        company_id=staff.company_id,
        outlet_id=staff.outlet_id,
        changes={"fields": ["is_active", "is_deleted", "deleted_at", "deactivated_at", "deactivated_reason"]},
        extra={"reason": staff.deactivated_reason},
    )
    db.commit()
    db.refresh(staff)
    return staff


def restore_staff(db: Session, actor: User, request: Request, staff: User) -> User:
    staff.is_active = True
    staff.is_deleted = False
    staff.deleted_at = None
    staff.deactivated_at = None
    staff.deactivated_reason = None
    sync_staff_profile(db, staff, actor.id).is_active = True
    write_audit(
        db,
        actor,
        request,
        "staff.restored",
        resource_type="user",
        resource_id=staff.id,
        company_id=staff.company_id,
        outlet_id=staff.outlet_id,
        changes={"fields": ["is_active", "is_deleted", "deleted_at", "deactivated_at", "deactivated_reason"]},
    )
    db.commit()
    db.refresh(staff)
    return staff


def reset_staff_password(db: Session, actor: User, request: Request, staff: User) -> str:
    password = generate_secure_password()
    staff.hashed_password = auth_guard.hash_password(password)
    staff.password_changed_at = _now()
    staff.force_password_change = True
    write_audit(
        db,
        actor,
        request,
        "staff.password_reset",
        resource_type="user",
        resource_id=staff.id,
        company_id=staff.company_id,
        outlet_id=staff.outlet_id,
        changes={"fields": ["hashed_password", "password_changed_at", "force_password_change"]},
        extra={"username": staff.username},
    )
    db.commit()
    return password


def reveal_staff_field(db: Session, actor: User, request: Request, staff: User, field_name: str) -> dict[str, Any]:
    aliases = {
        "aadhaar": "aadhaar_number",
        "aadhaar_number": "aadhaar_number",
        "pan": "pan_number",
        "pan_number": "pan_number",
        "bank_account_number": "bank_account_number",
        "ifsc_code": "ifsc_code",
        "upi_id": "upi_id",
        "monthly_salary": "monthly_salary",
        "daily_wage": "daily_wage",
        "hourly_rate": "hourly_rate",
        "passport_number": "passport_number",
        "driving_license": "driving_license",
        "voter_id": "voter_id",
    }
    resolved = aliases.get((field_name or "").strip().lower())
    if not resolved or resolved not in PII_FIELDS:
        raise HTTPException(status_code=422, detail="Unsupported PII field")
    write_audit(
        db,
        actor,
        request,
        "staff.pii_revealed",
        resource_type="user",
        resource_id=staff.id,
        company_id=staff.company_id,
        outlet_id=staff.outlet_id,
        changes={"fields": [resolved]},
        extra={"field": resolved},
    )
    db.commit()
    return {"field": resolved, "value": _json_value(getattr(staff, resolved))}


def staff_credentials_response(staff: User, password: str, note: str) -> dict[str, Any]:
    return {
        **credentials_payload(staff.username, password, note),
        "email": public_email(staff),
        "phone": staff.phone,
        "employee_code": staff.employee_code,
    }


def get_staff_profile(db: Session, staff_user_id: int) -> StaffProfile | None:
    return db.query(StaffProfile).filter(StaffProfile.user_id == staff_user_id).first()


def masked_audit_fields(changes: dict[str, Any]) -> list[str]:
    return sorted({key for key, value in changes.items() if value is not None})
