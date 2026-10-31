from datetime import datetime, timezone

from fastapi import HTTPException, Request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.login_credentials import LoginCredentialsUpdate
from app.services.company_service import generate_secure_password
from app.services.outlet_service import emit, write_audit
from app.services.rate_limit import record_rate_limited_attempt
from app.services.token_revocation import revoke_user_sessions
from app.utils.auth_system import auth_guard


def login_credentials(user: User) -> dict:
    return {
        "user_id": user.id,
        "username": user.username,
        "is_active": bool(user.is_active),
        "force_password_change": bool(user.force_password_change),
        "password_changed_at": user.password_changed_at.isoformat() if user.password_changed_at else None,
    }


def update_login_credentials(
    db: Session, actor: User, request: Request, user: User,
    payload: LoginCredentialsUpdate, profile: str,
) -> dict:
    if user.id == actor.id or user.is_super_ceo or user.is_super_admin:
        raise HTTPException(404, "Profile not found")
    record_rate_limited_attempt(db, actor, "update_login_credentials")
    username = payload.username or user.username
    if db.query(User.id).filter(
        func.lower(User.username) == username.lower(), User.id != user.id,
    ).first():
        raise HTTPException(409, "Username already exists")
    password = generate_secure_password() if payload.reset_password else payload.password
    fields = []
    previous_username = user.username
    if username != previous_username:
        user.username = username
        fields.append("username")
    if password is not None:
        user.hashed_password = auth_guard.hash_password(password)
        user.force_password_change = True
        user.password_changed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        fields.append("password_reset")
    if fields:
        write_audit(
            db, actor, request, f"{profile}.login_updated",
            resource_type="user", resource_id=user.id,
            company_id=user.company_id, outlet_id=user.outlet_id,
            changes={"fields": fields},
            extra={"previous_username": previous_username, "username": user.username},
        )
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(409, "Username already exists") from error
        db.refresh(user)
        revoke_user_sessions(user.id)
        emit(
            f"{profile}.updated", actor, company_id=user.company_id,
            outlet_id=user.outlet_id, resource_type="user", resource_id=user.id,
            data={"fields": fields}, revoke_user_ids=[user.id],
        )
    result = {"login": login_credentials(user)}
    if password is not None:
        result["credentials"] = {
            "username": user.username, "password": password,
            "note": "Save this password now. It will not be shown again.",
        }
    return result
