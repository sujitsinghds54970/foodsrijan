from sqlalchemy import text
from sqlalchemy.orm import Session


def ensure_staff_daily_ops_column(db: Session) -> None:
    """Ensure staff_profiles.can_access_daily_ops exists for non-migrated local DBs."""
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name if bind else ""

        if dialect == "sqlite":
            cols = db.execute(text("PRAGMA table_info(staff_profiles)")).fetchall()
            names = {row[1] for row in cols}
            if "can_access_daily_ops" in names:
                return
            db.execute(
                text("ALTER TABLE staff_profiles ADD COLUMN can_access_daily_ops BOOLEAN NOT NULL DEFAULT 0")
            )
            db.commit()
            return

        db.execute(
            text(
                "ALTER TABLE staff_profiles "
                "ADD COLUMN IF NOT EXISTS can_access_daily_ops BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        db.commit()
    except Exception:
        db.rollback()