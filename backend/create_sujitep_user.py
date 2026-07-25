#!/usr/bin/env python3
"""
Create sujitep super_admin user with password #sujitep54970
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import User
from app.utils.auth_system import auth_guard
from datetime import datetime

def create_sujitep_user():
    """Create or update sujitep user with correct credentials"""
    db = SessionLocal()
    
    try:
        # Check if user exists
        user = db.query(User).filter(User.username == 'sujitep').first()
        
        # Hash the password
        hashed_password = auth_guard.hash_password('#sujitep54970')
        
        if user:
            print(f"✓ User 'sujitep' found (ID: {user.id})")
            print(f"  Current role: {user.role}")
            print(f"  Current is_active: {user.is_active}")
            
            # Update user
            user.hashed_password = hashed_password
            user.role = 'super_admin'
            user.is_active = True
            user.email = user.email or 'sujitep@vaidyavihar.com'
            user.first_name = user.first_name or 'Sujit'
            user.last_name = user.last_name or 'Singh'
            
            db.commit()
            print(f"✓ Updated user 'sujitep' - Password reset, role=super_admin, is_active=True")
            
        else:
            print("✗ User 'sujitep' NOT found - Creating new user")
            
            # Create new user
            new_user = User(
                username='sujitep',
                email='sujitep@vaidyavihar.com',
                hashed_password=hashed_password,
                role='super_admin',
                first_name='Sujit',
                last_name='Singh',
                phone='',
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            print(f"✓ Created user 'sujitep' (ID: {new_user.id}) - role=super_admin, is_active=True")
        
        # Verify password works
        final_user = db.query(User).filter(User.username == 'sujitep').first()
        password_valid = auth_guard.verify_password('#sujitep54970', final_user.hashed_password)
        
        print(f"\n{'='*60}")
        print(f"VERIFICATION:")
        print(f"  Username: {final_user.username}")
        print(f"  Role: {final_user.role}")
        print(f"  Is Active: {final_user.is_active}")
        print(f"  Password Verification: {'✓ PASS' if password_valid else '✗ FAIL'}")
        print(f"{'='*60}\n")
        
        if not password_valid:
            print("ERROR: Password verification failed!")
            return False
        
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = create_sujitep_user()
    sys.exit(0 if success else 1)
