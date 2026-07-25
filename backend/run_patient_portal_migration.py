#!/usr/bin/env python3
"""
Create patient portal tables required by Patient Portal V2.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from app.models.patient import FamilyMember, PatientProfile


def run_migration() -> None:
    PatientProfile.__table__.create(bind=engine, checkfirst=True)
    FamilyMember.__table__.create(bind=engine, checkfirst=True)
    print("✅ patient_profiles table is ready")
    print("✅ family_members table is ready")


if __name__ == "__main__":
    run_migration()
