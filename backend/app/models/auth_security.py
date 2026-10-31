from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class LoginAttempt(Base):
    """Persistent login attempt ledger keyed by a hash of the submitted identifier."""

    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_subject_time", "subject_hash", "occurred_at"),
    )

    id = Column(Integer, primary_key=True)
    subject_hash = Column(String(64), nullable=False)
    ip_address = Column(String(64), nullable=True)
    was_successful = Column(Boolean, nullable=False, default=False)
    occurred_at = Column(DateTime, nullable=False, default=func.now(), index=True)
