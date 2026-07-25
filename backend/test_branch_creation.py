#!/usr/bin/env python3
"""
Test script to create a branch directly
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models import Branch, User
from app.utils.security import hash_password
import secrets
import string

def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits + "@#_-"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def create_test_branch():
    db = next(get_db())
    
    try:
        # Create branch
        branch = Branch(
            name="Maa Mundeshwari Diagnostic",
            location="India",
            city="Bhabua",
            state="Bihar",
            pincode="821101",
            phone="9876543210",
            email="bhabua@vaidyavihar.com",
            address="Main Road, Bhabua, Bihar",
            branch_code="VVMM001",
            is_active=True
        )
        db.add(branch)
        db.flush()
        
        # Create branch admin
        password = generate_temp_password()
        admin = User(
            username=f"bhabua_admin",
            email="bhabua_admin@vaidyavihar.com",
            hashed_password=hash_password(password),
            role="branch_admin",
            branch_id=branch.id,
            is_active=True,
            first_name="Branch",
            last_name="Admin",
            phone="9876543210"
        )
        db.add(admin)
        db.commit()
        
        print("✅ Branch created successfully!")
        print(f"\n🏢 Branch Details:")
        print(f"   ID: {branch.id}")
        print(f"   Name: {branch.name}")
        print(f"   Code: {branch.branch_code}")
        print(f"   City: {branch.city}, {branch.state}")
        
        print(f"\n👤 Branch Admin Credentials:")
        print(f"   Username: {admin.username}")
        print(f"   Email: {admin.email}")
        print(f"   Password: {password}")
        print(f"   Role: {admin.role}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_branch()
