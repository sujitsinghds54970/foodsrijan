from fastapi import APIRouter, Depends

from app.models import User
from app.database import get_db
from app.services.theme_resolver import resolve_theme
from sqlalchemy.orm import Session
from app.utils.auth_system import get_current_user


router = APIRouter()

PLATFORM_FALLBACK_THEME = {
    "id": "platform-fallback",
    "source": "platform_fallback",
    "mode": "light",
    "tokens": {
        "primary_color": "#4F46E5",
        "secondary_color": "#111827",
        "background_color": "#F9FAFB",
        "surface_color": "#FFFFFF",
        "text_color": "#111827",
    },
}


@router.get("/themes/resolved")
def get_resolved_theme(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile_key = "super_ceo" if getattr(current_user, "is_super_ceo", False) else str(getattr(current_user, "role", "")).lower()
    resolved = resolve_theme(db, current_user, profile_key)
    return {
        "theme": resolved if not resolved["degraded"] else PLATFORM_FALLBACK_THEME | {"source": resolved["source"]},
        "profile_type": profile_key if profile_key else None,
        "refresh_after_seconds": 60,
    }
