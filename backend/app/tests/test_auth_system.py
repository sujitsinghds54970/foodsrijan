"""
Unit Tests for Authentication System
Tests password hashing, token generation, and user authentication
"""

import pytest
import bcrypt
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User, Branch
from app.utils.auth_system import (
    AuthGuard, authenticate_user, create_user_token,
    update_last_login
)

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_guard():
    """Create AuthGuard instance"""
    return AuthGuard()


@pytest.fixture
def test_branch(db_session):
    """Create a test branch"""
    branch = Branch(
        name="Test Branch",
        location="Test Location",
        address="123 Test St",
        city="Test City",
        state="Test State",
        pincode="123456",
        phone="1234567890",
        email="test@branch.com",
        branch_code="TEST001",
        is_active=True
    )
    db_session.add(branch)
    db_session.commit()
    db_session.refresh(branch)
    return branch


@pytest.fixture
def test_user(db_session, test_branch, auth_guard):
    """Create a test super admin user"""
    hashed_password = auth_guard.hash_password("TestPassword123!")
    user = User(
        username="testadmin",
        email="testadmin@test.com",
        hashed_password=hashed_password,
        role="super_admin",
        first_name="Test",
        last_name="Admin",
        phone="1234567890",
        is_active=True,
        branch_id=test_branch.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_hash_password_creates_valid_bcrypt_hash(self, auth_guard):
        """Test that hash_password creates a valid bcrypt hash"""
        password = "SecurePassword123!"
        hashed = auth_guard.hash_password(password)
        
        # Check bcrypt format
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # Standard bcrypt hash length
    
    def test_hash_password_different_for_same_input(self, auth_guard):
        """Test that same password produces different hashes (salt)"""
        password = "SamePassword123!"
        hash1 = auth_guard.hash_password(password)
        hash2 = auth_guard.hash_password(password)
        
        assert hash1 != hash2
    
    def test_verify_password_correct_password(self, auth_guard):
        """Test password verification with correct password"""
        password = "CorrectPassword123!"
        hashed = auth_guard.hash_password(password)
        
        assert auth_guard.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect_password(self, auth_guard):
        """Test password verification with incorrect password"""
        password = "CorrectPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = auth_guard.hash_password(password)
        
        assert auth_guard.verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty_inputs(self, auth_guard):
        """Test password verification with empty inputs"""
        assert auth_guard.verify_password("", "hash") is False
        assert auth_guard.verify_password("password", "") is False
        assert auth_guard.verify_password("", "") is False
    
    def test_verify_password_special_characters(self, auth_guard):
        """Test password with special characters"""
        password = "#Sujitvaidyavihar54970"
        hashed = auth_guard.hash_password(password)
        
        assert auth_guard.verify_password(password, hashed) is True
        assert auth_guard.verify_password("#Sujitvaidyavihar54971", hashed) is False


class TestUserAuthentication:
    """Test user authentication functionality"""
    
    def test_authenticate_user_success(self, db_session, test_user):
        """Test successful user authentication"""
        user = authenticate_user(db_session, "testadmin", "TestPassword123!")
        
        assert user is not False
        assert user.username == "testadmin"
        assert user.role == "super_admin"
    
    def test_authenticate_user_wrong_password(self, db_session, test_user):
        """Test authentication with wrong password"""
        user = authenticate_user(db_session, "testadmin", "WrongPassword123!")
        
        assert user is False
    
    def test_authenticate_user_nonexistent_user(self, db_session):
        """Test authentication with non-existent user"""
        user = authenticate_user(db_session, "nonexistent", "password")
        
        assert user is False
    
    def test_authenticate_user_inactive_user(self, db_session, test_user):
        """Test authentication with inactive user"""
        test_user.is_active = False
        db_session.commit()
        
        user = authenticate_user(db_session, "testadmin", "TestPassword123!")
        
        assert user is False
    
    def test_authenticate_super_admin_credentials(self, db_session, test_branch, auth_guard):
        """Test authentication with actual super admin credentials"""
        # Create user with actual credentials
        hashed = auth_guard.hash_password("#Sujitvaidyavihar54970")
        user = User(
            username="sujiterp",
            email="sujit@vaidyavihar.com",
            hashed_password=hashed,
            role="super_admin",
            first_name="Sujit",
            last_name="Singh",
            phone="1234567890",
            is_active=True,
            branch_id=test_branch.id
        )
        db_session.add(user)
        db_session.commit()
        
        # Test authentication
        authenticated_user = authenticate_user(db_session, "sujiterp", "#Sujitvaidyavihar54970")
        
        assert authenticated_user is not False
        assert authenticated_user.username == "sujiterp"
        assert authenticated_user.role == "super_admin"


class TestTokenGeneration:
    """Test JWT token generation and validation"""
    
    def test_create_user_token(self, test_user):
        """Test token creation for user"""
        token = create_user_token(test_user)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_token_contains_user_data(self, test_user, auth_guard):
        """Test that token contains correct user data"""
        from jose import jwt
        import os
        
        token = create_user_token(test_user)
        SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-for-vaidya-vihar-2024")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        assert payload["sub"] == test_user.username
        assert payload["role"] == test_user.role
        assert payload["user_id"] == test_user.id
        assert payload["branch_id"] == test_user.branch_id
        assert "exp" in payload
        assert "iat" in payload
    
    def test_token_expiration(self, test_user):
        """Test that token has proper expiration"""
        from jose import jwt
        import os
        
        token = create_user_token(test_user)
        SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-for-vaidya-vihar-2024")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]
        
        # Check expiration is in the future
        assert exp_timestamp > iat_timestamp


class TestLastLoginUpdate:
    """Test last login timestamp update"""
    
    def test_update_last_login(self, db_session, test_user):
        """Test updating last login timestamp"""
        original_last_login = test_user.last_login
        
        update_last_login(db_session, test_user)
        
        assert test_user.last_login is not None
        assert test_user.last_login != original_last_login
    
    def test_update_last_login_multiple_times(self, db_session, test_user):
        """Test updating last login multiple times"""
        update_last_login(db_session, test_user)
        first_login = test_user.last_login
        
        import time
        time.sleep(0.1)  # Small delay
        
        update_last_login(db_session, test_user)
        second_login = test_user.last_login
        
        assert second_login > first_login


class TestSecurityFeatures:
    """Test security features and OWASP compliance"""
    
    def test_timing_attack_prevention(self, db_session, test_user):
        """Test that authentication timing is consistent"""
        import time
        
        # Time authentication with valid user
        start = time.time()
        authenticate_user(db_session, "testadmin", "WrongPassword")
        valid_user_time = time.time() - start
        
        # Time authentication with invalid user
        start = time.time()
        authenticate_user(db_session, "nonexistent", "WrongPassword")
        invalid_user_time = time.time() - start
        
        # Times should be similar (within 50ms)
        time_difference = abs(valid_user_time - invalid_user_time)
        assert time_difference < 0.05
    
    def test_password_hash_cost_factor(self, auth_guard):
        """Test that bcrypt cost factor is appropriate"""
        password = "TestPassword123!"
        hashed = auth_guard.hash_password(password)
        
        # Extract cost factor from hash
        cost = int(hashed.split("$")[2])
        
        # Cost should be at least 12 for security
        assert cost >= 12
    
    def test_sql_injection_prevention(self, db_session, test_user):
        """Test that SQL injection attempts are handled safely"""
        malicious_username = "admin' OR '1'='1"
        result = authenticate_user(db_session, malicious_username, "password")
        
        assert result is False


class TestRoleBasedAccess:
    """Test role-based access control"""
    
    def test_require_role_super_admin(self, auth_guard):
        """Test role requirement for super admin"""
        role_checker = auth_guard.require_role(['super_admin'])
        
        assert role_checker is not None
    
    def test_require_role_multiple_roles(self, auth_guard):
        """Test role requirement with multiple allowed roles"""
        role_checker = auth_guard.require_role(['super_admin', 'branch_admin', 'staff'])
        
        assert role_checker is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
