from __future__ import annotations

import hashlib
from datetime import datetime
from threading import Lock


_revoked_tokens: set[str] = set()
_revoked_user_before: dict[int, datetime] = {}
_lock = Lock()


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def revoke_token(token: str) -> None:
    with _lock:
        _revoked_tokens.add(_digest(token))


def is_token_revoked(token: str) -> bool:
    with _lock:
        return _digest(token) in _revoked_tokens


def revoke_user_sessions(user_id: int, revoked_before: datetime | None = None) -> None:
    with _lock:
        _revoked_user_before[user_id] = revoked_before or datetime.utcnow()


def is_user_session_revoked(user_id: int | None, issued_at: datetime | None) -> bool:
    if not user_id:
        return False
    with _lock:
        revoked_before = _revoked_user_before.get(user_id)
    if revoked_before is None:
        return False
    if issued_at is None:
        return True
    return issued_at <= revoked_before


def reset_state() -> None:
    with _lock:
        _revoked_tokens.clear()
        _revoked_user_before.clear()
