from __future__ import annotations

"""Per-process staff security rate limits.

These counters intentionally live in memory only, mirroring the same caveat as
in-memory token revocation: limits reset on process restart and are not shared
across workers.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock

from fastapi import HTTPException


_CREATION_WINDOW = timedelta(hours=1)
_CREATION_LIMIT = 30
_LOGIN_FAILURE_WINDOW = timedelta(minutes=15)
_LOGIN_FAILURE_LIMIT = 10

_lock = Lock()
_manager_staff_creations: dict[int, deque[datetime]] = defaultdict(deque)
_staff_login_failures: dict[str, deque[datetime]] = defaultdict(deque)


def _prune(bucket: deque[datetime], window: timedelta, now: datetime) -> None:
    cutoff = now - window
    while bucket and bucket[0] < cutoff:
        bucket.popleft()


def check_staff_creation_allowed(manager_user_id: int) -> None:
    now = datetime.utcnow()
    with _lock:
        bucket = _manager_staff_creations[manager_user_id]
        _prune(bucket, _CREATION_WINDOW, now)
        if len(bucket) >= _CREATION_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for staff creation. Try again later.",
                headers={"Retry-After": str(int(_CREATION_WINDOW.total_seconds()))},
            )


def record_staff_creation(manager_user_id: int) -> None:
    now = datetime.utcnow()
    with _lock:
        bucket = _manager_staff_creations[manager_user_id]
        _prune(bucket, _CREATION_WINDOW, now)
        bucket.append(now)


def ensure_staff_login_allowed(identifier: str) -> None:
    key = (identifier or "").strip().lower()
    now = datetime.utcnow()
    with _lock:
        bucket = _staff_login_failures[key]
        _prune(bucket, _LOGIN_FAILURE_WINDOW, now)
        if len(bucket) >= _LOGIN_FAILURE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Too many failed login attempts. Try again later.",
                headers={"Retry-After": str(int(_LOGIN_FAILURE_WINDOW.total_seconds()))},
            )


def record_staff_login_failure(identifier: str) -> None:
    key = (identifier or "").strip().lower()
    now = datetime.utcnow()
    with _lock:
        bucket = _staff_login_failures[key]
        _prune(bucket, _LOGIN_FAILURE_WINDOW, now)
        bucket.append(now)


def clear_staff_login_failures(identifier: str) -> None:
    key = (identifier or "").strip().lower()
    with _lock:
        _staff_login_failures.pop(key, None)


def reset_state() -> None:
    with _lock:
        _manager_staff_creations.clear()
        _staff_login_failures.clear()
