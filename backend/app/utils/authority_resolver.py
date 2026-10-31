from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from fastapi import Depends, HTTPException, status


SYSTEM_ADMIN_ROLE = "super_ceo"
LEGACY_SYSTEM_ADMIN_ROLE = "super_admin"


def normalize_role_name(role_name: str | None) -> str:
    """Normalize legacy Super Admin role labels to the canonical Super CEO name."""
    value = (role_name or "").strip()
    if not value:
        return ""
    lowered = value.lower().replace("-", "_").replace(" ", "_")
    return {
        LEGACY_SYSTEM_ADMIN_ROLE: SYSTEM_ADMIN_ROLE,
        SYSTEM_ADMIN_ROLE: SYSTEM_ADMIN_ROLE,
        "super_ceo_role": SYSTEM_ADMIN_ROLE,
    }.get(lowered, lowered)


def is_super_ceo(user: Any | None) -> bool:
    """Resolve system authority while honoring legacy Super Admin records."""
    if user is None or not getattr(user, "is_active", False):
        return False
    return bool(
        getattr(user, "is_super_ceo", False)
        or getattr(user, "is_super_admin", False)
        or normalize_role_name(getattr(user, "role", "")) == SYSTEM_ADMIN_ROLE
    )


def get_permission_codes(user: Any | None) -> set[str]:
    """Return permission codes from canonical and legacy active role assignments."""
    if user is None:
        return set()

    permission_codes: set[str] = set()
    assignments = (
        list(getattr(user, "canonical_role_assignments", ()) or ())
        + list(getattr(user, "role_assignments", ()) or ())
    )
    for assignment in assignments:
        if not getattr(assignment, "is_active", False):
            continue
        role = getattr(assignment, "role", None)
        if role is None or not getattr(role, "is_active", False):
            continue
        for permission in getattr(role, "permissions", ()) or ():
            code = getattr(permission, "code", None)
            if code:
                permission_codes.add(code)
    return permission_codes


def require_permissions(
    required_permissions: Iterable[str],
    current_user_dependency: Callable[..., Any],
):
    """Build a FastAPI dependency that accepts Super CEO or assigned permissions."""
    required = frozenset(required_permissions)

    def permission_checker(current_user: Any = Depends(current_user_dependency)):
        if is_super_ceo(current_user) or required.intersection(get_permission_codes(current_user)):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return permission_checker
