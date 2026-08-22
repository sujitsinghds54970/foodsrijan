"""Initialize all database tables for SQLite."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, Base

# Import models in dependency order (referenced tables before referencing tables)
# Core models with no deps first
from app.models.patient_entry import CustomerEntry
from app.models.daily_entry_module import DailyEntryModule
from app.models.lab_test import LabMenuItem
from app.models.user import User  # noqa - triggers Branch import via models.__init__
import app.models  # imports everything in __init__.py

# Additional models not in __init__.py
import app.models.lis
import app.models.staff
import app.models.branch_lis

# Create all tables
Base.metadata.create_all(bind=engine)
print("✅ All tables created successfully!")
