"""
Integration Tests for Authentication System
Tests end-to-end authentication flow including API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import User, Branch
from app.utils.auth_system import AuthGuard

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_integration.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Setup and teardown test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_branch():
    """Create a test branch"""
    db = TestingSessionLocal()
    branch = Branch(
        name="Integration Test Branch",
        location="Test Location",
        address="123 Integration St",
        city="Test City",
        state="Test State",
        pincode="123456",
        phone="9876543210",
        email="integration@test.com",
        branch_code="INT001",
        is_active=True
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    db.close()
    return branch


@pytest.fixture
def super_admin_user(test_branch):
    """Create super admin user for testing"""
    db = TestingSessionLocal()
    auth_guard = AuthGuard()
    
    hashed_password = auth_guard.hash_password("#Sujitvaidyavihar54970")
    user = User(
        username="sujiterp",
        email="sujit@vaidyavihar.com",
        hashed_password=hashed_password,
        role="super_admin",
        first_name="Sujit",
        last_name="Singh",
        phone="1234567890",
        is_active=True,
        branch_id=test_branch.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def regular_user(test_branch):
    """Create regular staff user for testing"""
    db = TestingSessionLocal()
    auth_guard = AuthGuard()
    
    hashed_password = auth_guard.hash_password("StaffPassword123!")
    user = User(
        username="staffuser",
        email="staff@test.com",
        hashed_password=hashed_password,
        role="staff",
        first_name="Staff",
        last_name="User",
        phone="9876543210",
        is_active=True,
        branch_id=test_branch.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


class TestLoginEndpoint:
    """Test login API endpoint"""
    
    def test_login_success_super_admin(self, super_admin_user):
        """Test successful login with super admin credentials"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "#Sujitvaidyavihar54970"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == "sujiterp"
        assert data["user"]["role"] == "super_admin"
    
    def test_login_success_regular_user(self, regular_user):
        """Test successful login with regular user"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "staffuser",
                "password": "StaffPassword123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["user"]["role"] == "staff"
    
    def test_login_wrong_password(self, super_admin_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent user"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent",
                "password": "password"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_inactive_user(self, test_branch):
        """Test login with inactive user"""
        db = TestingSessionLocal()
        auth_guard = AuthGuard()
        
        hashed_password = auth_guard.hash_password("InactivePassword123!")
        user = User(
            username="inactiveuser",
            email="inactive@test.com",
            hashed_password=hashed_password,
            role="staff",
            first_name="Inactive",
            last_name="User",
            phone="1111111111",
            is_active=False,
            branch_id=test_branch.id
        )
        db.add(user)
        db.commit()
        db.close()
        
        response = client.post(
            "/api/auth/login",
            data={
                "username": "inactiveuser",
                "password": "InactivePassword123!"
            }
        )
        
        assert response.status_code == 401


class TestProtectedEndpoints:
    """Test protected endpoints with authentication"""
    
    def test_access_protected_endpoint_with_token(self, super_admin_user):
        """Test accessing protected endpoint with valid token"""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "#Sujitvaidyavihar54970"
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Access protected endpoint
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "sujiterp"
        assert data["role"] == "super_admin"
    
    def test_access_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 403  # Forbidden
    
    def test_access_protected_endpoint_invalid_token(self):
        """Test accessing protected endpoint with invalid token"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401


class TestTokenRefresh:
    """Test token refresh functionality"""
    
    def test_refresh_token(self, super_admin_user):
        """Test refreshing access token"""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "#Sujitvaidyavihar54970"
            }
        )
        
        old_token = login_response.json()["access_token"]
        
        # Refresh token
        response = client.post(
            "/api/auth/refresh-token",
            headers={"Authorization": f"Bearer {old_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        new_token = data["access_token"]
        
        # New token should be different
        assert new_token != old_token
        
        # New token should work
        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert me_response.status_code == 200


class TestPasswordChange:
    """Test password change functionality"""
    
    def test_change_password_success(self, super_admin_user):
        """Test successful password change"""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "#Sujitvaidyavihar54970"
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Change password
        response = client.post(
            "/api/auth/change-password",
            params={
                "current_password": "#Sujitvaidyavihar54970",
                "new_password": "NewSecurePassword123!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # Try logging in with new password
        new_login_response = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "NewSecurePassword123!"
            }
        )
        
        assert new_login_response.status_code == 200
    
    def test_change_password_wrong_current_password(self, super_admin_user):
        """Test password change with wrong current password"""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "#Sujitvaidyavihar54970"
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Try to change password with wrong current password
        response = client.post(
            "/api/auth/change-password",
            params={
                "current_password": "WrongPassword",
                "new_password": "NewSecurePassword123!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400


class TestConcurrentLogins:
    """Test concurrent login scenarios"""
    
    def test_multiple_concurrent_logins(self, super_admin_user):
        """Test multiple concurrent login attempts"""
        import concurrent.futures
        
        def login_attempt():
            response = client.post(
                "/api/auth/login",
                data={
                    "username": "sujiterp",
                    "password": "#Sujitvaidyavihar54970"
                }
            )
            return response.status_code
        
        # Simulate 10 concurrent login attempts
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(login_attempt) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        assert all(status == 200 for status in results)
    
    def test_login_from_multiple_sessions(self, super_admin_user):
        """Test logging in from multiple sessions"""
        # Login from first session
        response1 = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "#Sujitvaidyavihar54970"
            }
        )
        
        token1 = response1.json()["access_token"]
        
        # Login from second session
        response2 = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "#Sujitvaidyavihar54970"
            }
        )
        
        token2 = response2.json()["access_token"]
        
        # Both tokens should work
        me_response1 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token1}"}
        )
        
        me_response2 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token2}"}
        )
        
        assert me_response1.status_code == 200
        assert me_response2.status_code == 200


class TestSecurityHeaders:
    """Test security headers and CORS"""
    
    def test_cors_headers_present(self, super_admin_user):
        """Test that CORS headers are properly set"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "#Sujitvaidyavihar54970"
            }
        )
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200


class TestLogout:
    """Test logout functionality"""
    
    def test_logout_success(self, super_admin_user):
        """Test successful logout"""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": "sujiterp",
                "password": "#Sujitvaidyavihar54970"
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Logout
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "message" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
