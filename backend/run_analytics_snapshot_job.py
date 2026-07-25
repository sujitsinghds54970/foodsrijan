#!/usr/bin/env python3
"""
Runs analytics snapshot aggregation every day at 2:00 AM.
Use --run-once to execute immediately for yesterday.
"""

import argparse
import time
from datetime import date, datetime, time as dt_time, timedelta

from app.routes.analytics import run_daily_snapshot_job


def _seconds_until_next_2am(now: datetime) -> int:
    target_date = now.date()
    target_dt = datetime.combine(target_date, dt_time(hour=2, minute=0, second=0))
    if now >= target_dt:
        target_dt = datetime.combine(target_date + timedelta(days=1), dt_time(hour=2, minute=0, second=0))
    return int((target_dt - now).total_seconds())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-once", action="store_true", help="Run one aggregation cycle for yesterday and exit")
    args = parser.parse_args()

    if args.run_once:
        total = run_daily_snapshot_job(for_date=date.today() - timedelta(days=1))
        print(f"✅ Snapshot aggregation completed. Rows upserted: {total}")
        return

    print("📊 Analytics scheduler started. Next runs daily at 02:00 AM")
    while True:
        wait_seconds = _seconds_until_next_2am(datetime.now())
        time.sleep(max(wait_seconds, 1))
        try:
            total = run_daily_snapshot_job(for_date=date.today() - timedelta(days=1))
            print(f"✅ {datetime.now().isoformat()} snapshot aggregation completed. Rows upserted: {total}")
        except Exception as exc:
            print(f"❌ {datetime.now().isoformat()} snapshot aggregation failed: {exc}")


if __name__ == "__main__":
    main()
