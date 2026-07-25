#!/usr/bin/env python3
"""
Bootstrap patient portal profiles from existing daily entries.

Creates one profile per unique mobile number found in daily_entries_module.
Default password for newly created profiles: patient@123
"""

import os
import sys
from datetime import datetime, timezone

from sqlalchemy import func

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.daily_entry_module import DailyEntryModule
from app.models.patient import PatientProfile

DEFAULT_PASSWORD = "patient@123"


def _next_patient_code(db) -> str:
    latest = db.query(PatientProfile).order_by(PatientProfile.id.desc()).first()
    if not latest or not latest.patient_code:
        return "PTP-00001"
    try:
        suffix = int(latest.patient_code.split("-")[-1]) + 1
    except Exception:
        suffix = (latest.id or 0) + 1
    return f"PTP-{suffix:05d}"


def bootstrap_profiles() -> None:
    db = SessionLocal()
    created = 0
    skipped = 0

    try:
        rows = (
            db.query(
                DailyEntryModule.mobile,
                func.max(DailyEntryModule.patient_name).label("patient_name"),
            )
            .filter(DailyEntryModule.mobile.isnot(None), DailyEntryModule.mobile != "")
            .group_by(DailyEntryModule.mobile)
            .all()
        )

        for mobile, patient_name in rows:
            existing = db.query(PatientProfile).filter(PatientProfile.mobile == mobile).first()
            if existing:
                skipped += 1
                continue

            code = _next_patient_code(db)
            profile = PatientProfile(
                patient_code=code,
                full_name=(patient_name or f"Patient {mobile}").strip(),
                mobile=mobile.strip(),
                email=None,
                password=DEFAULT_PASSWORD,
                role="patient",
                is_active=True,
                family_group=None,
                wallet_balance=0.0,
                cashback_percent=5.0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(profile)
            db.flush()
            created += 1

        db.commit()

        print(f"✅ Patient profiles bootstrap complete. Created: {created}, Skipped(existing): {skipped}")
        print(f"ℹ️ Default password for new profiles: {DEFAULT_PASSWORD}")
    except Exception as exc:
        db.rollback()
        print(f"❌ Bootstrap failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_profiles()
