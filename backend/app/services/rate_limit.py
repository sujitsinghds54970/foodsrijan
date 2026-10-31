import hashlib
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.models import LoginAttempt, RateLimitEntry, User


RATE_LIMITS = {
    "update_login_credentials": 20,
    "create_company": 5,
    "assign_company_ceo": 10,
    "reset_company_ceo_password": 10,
    "create_outlet": 20,
    "create_outlet_manager": 20,
    "reset_outlet_manager_password": 10,
    "test_outlet_manager_login": 30,
}
LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW = timedelta(minutes=15)


def record_rate_limited_attempt(db: Session, actor: User, action: str) -> None:
    limit = RATE_LIMITS[action]
    now = datetime.utcnow()
    window_start = now - timedelta(hours=1)
    retention_start = now - timedelta(hours=24)

    db.query(User).filter(User.id == actor.id).with_for_update().first()
    db.query(RateLimitEntry).filter(RateLimitEntry.occurred_at < retention_start).delete(synchronize_session=False)
    count = (
        db.query(RateLimitEntry)
        .filter(
            RateLimitEntry.actor_id == actor.id,
            RateLimitEntry.action == action,
            RateLimitEntry.occurred_at >= window_start,
            RateLimitEntry.was_allowed.is_(True),
        )
        .count()
    )
    allowed = count < limit
    db.add(RateLimitEntry(actor_id=actor.id, action=action, occurred_at=now, was_allowed=allowed))
    db.commit()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {action.replace('_', ' ')}. Try again later.",
            headers={"Retry-After": "3600"},
        )


def _login_subject_hash(identifier: str) -> str:
    return hashlib.sha256((identifier or "").strip().lower().encode("utf-8")).hexdigest()


def recent_failed_logins(db: Session, identifier: str) -> int:
    window_start = datetime.utcnow() - LOGIN_FAILURE_WINDOW
    try:
        return (
            db.query(LoginAttempt)
            .filter(
                LoginAttempt.subject_hash == _login_subject_hash(identifier),
                LoginAttempt.was_successful.is_(False),
                LoginAttempt.occurred_at >= window_start,
            )
            .count()
        )
    except (OperationalError, ProgrammingError):
        # login_attempts table not present (e.g. legacy/test DB without the
        # outlet-management migration applied yet) - fail open rather than
        # blocking authentication entirely.
        db.rollback()
        return 0


def ensure_login_allowed(db: Session, identifier: str) -> None:
    """Reject further attempts once an identifier has 5 failures inside 15 minutes."""
    if recent_failed_logins(db, identifier) >= LOGIN_FAILURE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(int(LOGIN_FAILURE_WINDOW.total_seconds()))},
        )


def record_login_attempt(db: Session, identifier: str, *, successful: bool, ip_address: str | None = None) -> None:
    now = datetime.utcnow()
    subject_hash = _login_subject_hash(identifier)
    try:
        db.query(LoginAttempt).filter(LoginAttempt.occurred_at < now - timedelta(hours=24)).delete(synchronize_session=False)
        if successful:
            db.query(LoginAttempt).filter(
                LoginAttempt.subject_hash == subject_hash,
                LoginAttempt.was_successful.is_(False),
            ).delete(synchronize_session=False)
        else:
            db.add(LoginAttempt(subject_hash=subject_hash, ip_address=(ip_address or "")[:64] or None, was_successful=False, occurred_at=now))
        db.commit()
    except (OperationalError, ProgrammingError):
        # login_attempts table not present - nothing to persist, fail open.
        db.rollback()
