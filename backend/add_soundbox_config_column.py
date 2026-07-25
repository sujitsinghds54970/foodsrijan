#!/usr/bin/env python3
"""
Add soundbox_config JSON column to branch_bank_details table
This migration adds a flexible JSON field for storing payment device configurations
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

def run_migration():
    print("🔧 Adding soundbox_config column to branch_bank_details...")
    
    try:
        from app.database import engine
        
        print(f"📂 Database: {engine.url}")
        
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(branch_bank_details)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'soundbox_config' in columns:
                print("⚠️  Column 'soundbox_config' already exists. Skipping migration.")
                return
            
            # Add the soundbox_config column
            print("📋 Adding soundbox_config JSON column...")
            conn.execute(text("""
                ALTER TABLE branch_bank_details 
                ADD COLUMN soundbox_config TEXT
            """))
            conn.commit()
            
            print("✅ Migration completed successfully!")
            print("\n📝 The soundbox_config column has been added.")
            print("   You can now store flexible JSON data like:")
            print('   {"provider": "SBI", "device_id": "SB-12345", "merchant_id": "M-5678"}')
            print("\n🔄 Restart your backend server to use the new field.")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
