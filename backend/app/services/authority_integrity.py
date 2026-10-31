import logging

from sqlalchemy.orm import Session

from app.models import User

logger = logging.getLogger(__name__)


def canonical_super_ceo_count(db: Session) -> int:
    return int(
        db.query(User)
        .filter(User.is_active.is_(True), User.is_super_ceo.is_(True))
        .count()
    )


def check_canonical_super_ceo_integrity(db: Session) -> bool:
    count = canonical_super_ceo_count(db)
    if count == 1:
        logger.info("Canonical Super CEO integrity check passed")
        return True
    logger.critical(
        "Canonical Super CEO integrity check failed: active_holder_count=%s",
        count,
    )
    return False
