"""
Run Daily Entry Module Migration
"""
from sqlalchemy import create_engine, text
from app.database import DATABASE_URL, Base
from app.models.daily_entry_module import DailyEntryModule, DailyExpense


def _ensure_daily_entry_columns(engine) -> None:
    with engine.begin() as conn:
        cols = conn.execute(text("PRAGMA table_info(daily_entries_module)")).fetchall()
        col_names = {row[1] for row in cols}

        if "age" not in col_names:
            conn.execute(text("ALTER TABLE daily_entries_module ADD COLUMN age INTEGER"))
            print("✅ Added daily_entries_module.age")

        if "upi_id" not in col_names:
            conn.execute(text("ALTER TABLE daily_entries_module ADD COLUMN upi_id VARCHAR(100)"))
            print("✅ Added daily_entries_module.upi_id")

def run_migration():
    """Create tables for Daily Entry Module"""
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
    
    # Import all models to ensure they're registered
    from app.models import Branch, User
    
    # Create tables
    Base.metadata.create_all(bind=engine, tables=[DailyEntryModule.__table__, DailyExpense.__table__])
    _ensure_daily_entry_columns(engine)
    
    print("✅ Daily Entry Module tables created successfully!")
    print("   - daily_entries_module")
    print("   - daily_expenses_module")

if __name__ == "__main__":
    run_migration()
