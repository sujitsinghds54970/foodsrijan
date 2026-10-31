from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import ProfileType
from app.models.themes import Theme, ThemeAssignment, ThemeVersion
from app.services.theme_tokens import default_tokens, merge_tokens


def resolve_theme(db: Session, user, profile_type_key: str, mode: str = "dark") -> dict:
    profile = db.query(ProfileType).filter(ProfileType.code == profile_type_key, ProfileType.is_active.is_(True)).first()
    if not profile:
        return {"tokens": default_tokens(), "source": "platform_fallback", "version_id": None, "degraded": True}
    now = datetime.utcnow()
    company_id = getattr(user, "current_company_id", None) or getattr(user, "company_id", None)
    brand_id = getattr(user, "brand_id", None)
    branch_id = getattr(user, "branch_id", None)
    assignments = db.query(ThemeAssignment).join(Theme).join(
        ThemeVersion, Theme.current_version_id == ThemeVersion.id,
    ).filter(
        ThemeAssignment.profile_type_id == profile.id,
        ThemeAssignment.is_active.is_(True),
        Theme.status == "published",
        ThemeVersion.status == "published",
        or_(ThemeAssignment.user_id == getattr(user, "id", None), ThemeAssignment.user_id.is_(None)),
        ThemeAssignment.role_id.is_(None),
        or_(ThemeAssignment.company_id == company_id, ThemeAssignment.company_id.is_(None)) if company_id else ThemeAssignment.company_id.is_(None),
        or_(ThemeAssignment.brand_id == brand_id, ThemeAssignment.brand_id.is_(None)) if brand_id else ThemeAssignment.brand_id.is_(None),
        or_(ThemeAssignment.branch_id == branch_id, ThemeAssignment.branch_id.is_(None)) if branch_id else ThemeAssignment.branch_id.is_(None),
        ThemeAssignment.department_id.is_(None),
        or_(ThemeAssignment.starts_at.is_(None), ThemeAssignment.starts_at <= now),
        or_(ThemeAssignment.ends_at.is_(None), ThemeAssignment.ends_at >= now),
    ).order_by(ThemeAssignment.priority.desc(), ThemeAssignment.user_id.desc().nullslast()).all()
    scope_filters = [
        or_(Theme.company_id == company_id, Theme.company_id.is_(None)) if company_id else Theme.company_id.is_(None),
        or_(Theme.brand_id == brand_id, Theme.brand_id.is_(None)) if brand_id else Theme.brand_id.is_(None),
    ]
    published_themes = db.query(Theme).join(
        ThemeVersion, Theme.current_version_id == ThemeVersion.id,
    ).filter(
        Theme.profile_type_id == profile.id,
        Theme.status == "published",
        ThemeVersion.status == "published",
        *scope_filters,
    ).order_by(
        Theme.company_id.desc().nullslast(),
        Theme.brand_id.desc().nullslast(),
    )
    theme = assignments[0].theme if assignments else published_themes.filter(Theme.is_default.is_(True)).first()
    if not theme:
        theme = published_themes.first()
    if not theme or not theme.current_version_id:
        return {"tokens": default_tokens(), "source": "platform_fallback", "version_id": None, "degraded": True}
    chain = []
    current = theme
    while current:
        chain.append(current)
        current = current.parent_theme
    tokens = default_tokens()
    for item in reversed(chain):
        version = next((version for version in item.versions if version.id == item.current_version_id), None)
        if version and version.status == "published":
            tokens = merge_tokens(tokens, version.tokens)
    return {"tokens": tokens, "source": f"theme:{theme.id}", "version_id": theme.current_version_id, "degraded": False, "mode": mode}
