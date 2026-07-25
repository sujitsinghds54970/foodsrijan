#!/usr/bin/env python3
"""
Run Branch Bank Details Migration
Creates the branch_bank_details table
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Table, MetaData, text
from datetime import datetime

def run_migration():
    print("🔧 Starting Branch Bank Details Migration...")
    
    try:
        from app.database import engine
        
        print(f"📂 Database: {engine.url}")
        
        # Create metadata
        metadata = MetaData()
        
        # Load the existing branches table
        print("📋 Loading existing branches table...")
        branches_table = Table('branches', metadata, autoload_with=engine)
        
        # Define the branch_bank_details table
        print("📋 Creating branch_bank_details table...")
        branch_bank_details = Table(
            'branch_bank_details',
            metadata,
            Column('id', Integer, primary_key=True, index=True),
            Column('branch_id', Integer, ForeignKey(branches_table.c.id), unique=True, nullable=False),
            Column('account_holder_name', String(255), nullable=False),
            Column('account_number', String(50), nullable=False),
            Column('ifsc_code', String(20), nullable=False),
            Column('bank_name', String(255), nullable=False),
            Column('upi_id', String(100), nullable=False, index=True),
            Column('is_active', Boolean, default=True, nullable=False),
            Column('created_at', DateTime, default=datetime.utcnow, nullable=False),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
        )
        
        # Create the table
        metadata.create_all(bind=engine, tables=[branch_bank_details])

        # Ensure daily_entries_module has upi_id for webhook matching
        print("📋 Ensuring daily_entries_module.upi_id column exists...")
        with engine.begin() as conn:
            cols = conn.execute(text("PRAGMA table_info(daily_entries_module)")).fetchall()
            col_names = {row[1] for row in cols}
            if 'upi_id' not in col_names:
                conn.execute(text("ALTER TABLE daily_entries_module ADD COLUMN upi_id VARCHAR(100)"))
                print("✅ Added daily_entries_module.upi_id")
            else:
                print("ℹ️ daily_entries_module.upi_id already exists")
        
        print("✅ Migration completed successfully!")
        print("\n📝 Next steps:")
        print("1. Restart the backend server: cd backend && ./start_backend.sh")
        print("2. Use the cURL command to add bank details:")
        print("\n   curl -X POST 'http://localhost:8000/api/branches/6/bank-details' \\")
        print("     -H 'Authorization: Bearer YOUR_TOKEN' \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{")
        print('       "account_holder_name": "Vaidya Vihar Diagnostic Center",')
        print('       "account_number": "1234567890",')
        print('       "ifsc_code": "SBIN0001234",')
        print('       "bank_name": "State Bank of India",')
        print('       "upi_id": "vaidyavihar@paytm"')
        print("     }'")
        print("\n3. Test the QR code in Daily Operations")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
