#!/usr/bin/env python3
"""
Create analytics snapshot table.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from app.models.analytics import DailyAnalyticsSnapshot


def run_migration() -> None:
    DailyAnalyticsSnapshot.__table__.create(bind=engine, checkfirst=True)
    print("✅ daily_analytics_snapshots table is ready")


if __name__ == "__main__":
    run_migration()
