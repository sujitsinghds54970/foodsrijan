"""
Unified Database Configuration for VaidyaVihar Diagnostic ERP
This is the single source of truth for database configuration
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
backend_root = Path(__file__).resolve().parent.parent
default_sqlite_path = backend_root / "vaidya_vihar.db"
raw_database_url = os.getenv("DATABASE_URL")

if raw_database_url:
    if raw_database_url.startswith("sqlite:///./"):
        relative_part = raw_database_url.replace("sqlite:///./", "", 1)
        DATABASE_URL = f"sqlite:///{(backend_root / relative_part).resolve()}"
    else:
        DATABASE_URL = raw_database_url
else:
    DATABASE_URL = f"sqlite:///{default_sqlite_path}"

# Create SQLAlchemy engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models - SINGLE SOURCE OF TRUTH
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database connection test
def test_connection():
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
