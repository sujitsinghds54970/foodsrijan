from sqlalchemy import Column, Date, Float, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.database import Base


class DailyAnalyticsSnapshot(Base):
    __tablename__ = "daily_analytics_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)

    total_revenue = Column(Float, nullable=False, default=0.0)
    total_expenses = Column(Float, nullable=False, default=0.0)
    net_profit = Column(Float, nullable=False, default=0.0)

    patient_count = Column(Integer, nullable=False, default=0)
    xray_count = Column(Integer, nullable=False, default=0)
    sonography_count = Column(Integer, nullable=False, default=0)
    pathology_count = Column(Integer, nullable=False, default=0)
    ct_mri_count = Column(Integer, nullable=False, default=0)
    other_count = Column(Integer, nullable=False, default=0)
    total_menu_items = Column(Integer, nullable=False, default=0)

    avg_bill_value = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    branch = relationship("Branch")

    __table_args__ = (
        UniqueConstraint("date", "branch_id", name="uq_daily_analytics_snapshot_date_branch"),
        Index("ix_daily_analytics_snapshots_date_branch", "date", "branch_id"),
    )
