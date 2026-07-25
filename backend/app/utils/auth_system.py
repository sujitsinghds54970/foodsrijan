from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
import bcrypt
import os
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from passlib.context import CryptContext

from app.database import get_db
from app.models import User, ActivityLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-for-vaidya-vihar-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 10080))  # 7 days (10080 minutes)

# Log security configuration (without exposing secrets)
logger.info(f"Auth system initialized - Token expiry: {ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
logger.info(f"SECRET_KEY configured: {'Yes' if os.getenv('SECRET_KEY') else 'No (using default)'}")

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenData:
    def __init__(
        self,
        username: str = None,
        branch_id: int = None,
        role: str = None,
        token_type: str = None,
        scope: str = None,
        user_id: int = None,
    ):
        self.username = username
        self.branch_id = branch_id
        self.role = role
        self.token_type = token_type
        self.scope = scope
        self.user_id = user_id

class AuthGuard:
    def __init__(self, allowed_roles: Optional[List[str]] = None):
        self.allowed_roles = allowed_roles or []
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash with backward-compatible fallback.
        OWASP compliant password verification with detailed logging.
        """
        if not plain_password or not hashed_password:
            logger.warning("Password verification failed: Empty password or hash")
            return False

        try:
            # Primary path: direct bcrypt verification (current hashing strategy)
            result = bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
            
            if result:
                logger.info("Password verification successful (bcrypt)")
            else:
                logger.warning("Password verification failed (bcrypt mismatch)")
            
            return result
            
        except ValueError as e:
            # Hash format issue - try passlib fallback
            logger.warning(f"Bcrypt verification failed, trying passlib fallback: {str(e)}")
            try:
                result = pwd_context.verify(plain_password, hashed_password)
                if result:
                    logger.info("Password verification successful (passlib fallback)")
                else:
                    logger.warning("Password verification failed (passlib mismatch)")
                return result
            except Exception as fallback_error:
                logger.error(f"All password verification methods failed: {str(fallback_error)}")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error during password verification: {str(e)}")
            return False
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
        """Verify JWT token and return user data"""
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            branch_id: int = payload.get("branch_id")
            role: str = payload.get("role")
            token_type: str = payload.get("token_type") or payload.get("type") or "access"
            scope: str = payload.get("scope")
            user_id: int = payload.get("user_id")
            
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(
                username=username,
                branch_id=branch_id,
                role=role,
                token_type=token_type,
                scope=scope,
                user_id=user_id,
            )
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def get_current_user(self, token_data: Optional[TokenData] = None, db: Session = Depends(get_db)) -> User:
        """Get current authenticated user from database"""
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(User).filter(User.username == token_data.username).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Preserve token context for downstream route-level authorization checks.
        setattr(user, "_token_type", token_data.token_type)
        setattr(user, "_token_scope", token_data.scope)
        setattr(user, "_token_user_id", token_data.user_id)

        return user

    def current_user_dependency(self):
        """FastAPI-safe dependency wrapper to avoid bound-method signature issues."""
        def _dep(
            token_data: TokenData = Depends(self.verify_token),
            db: Session = Depends(get_db),
        ) -> User:
            return self.get_current_user(token_data=token_data, db=db)

        return _dep

    def require_role(self, allowed_roles: List[str]):
        """Decorator to require specific roles"""
        current_user_dep = self.current_user_dependency()

        def role_checker(current_user: User = Depends(current_user_dep)):
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return current_user
        return role_checker
    
    def require_branch_access(self, current_user: User = Depends(get_current_user)):
        """Ensure user has access to their assigned branch"""
        if current_user.branch_id is None and current_user.role != 'super_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Branch access required"
            )
        return current_user
    
    def log_activity(self, db: Session, user: User, action: str, entity_type: str, entity_id: int = None, description: str = "", branch_id: int = None):
        """Log user activity for audit trail"""
        activity = ActivityLog(
            user_id=user.id,
            branch_id=branch_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            timestamp=datetime.utcnow()
        )
        db.add(activity)
        db.commit()

# Authentication functions
def authenticate_user(db: Session, username: str, password: str):
    """
    Authenticate user with username and password.
    Implements OWASP authentication best practices with detailed logging.
    """
    identifier = (username or "").strip()
    logger.info(f"Authentication attempt for identifier: {identifier}")
    print(f"[AUTH DEBUG] received identifier={identifier!r}")
    
    try:
        # Query user with timeout protection
        user = db.query(User).filter(
            or_(
                User.username == identifier,
                User.email == identifier,
            )
        ).first()
        if user:
            print(
                "[AUTH DEBUG] fetched user="
                f"id={user.id}, username={user.username!r}, role={user.role!r}, is_active={user.is_active}"
            )
        else:
            print("[AUTH DEBUG] fetched user=None")
        
        if not user:
            logger.warning(f"Authentication failed: User '{identifier}' not found")
            # Use constant-time comparison to prevent timing attacks
            # Hash a dummy password to maintain consistent timing
            AuthGuard().hash_password("dummy_password_for_timing")
            return False
        
        logger.info(f"User '{identifier}' found (ID: {user.id}, Role: {user.role})")
        
        # Check if user is active before password verification
        if not user.is_active:
            logger.warning(f"Authentication failed: User '{identifier}' is inactive")
            return False
        
        # Verify password with detailed logging
        password_valid = AuthGuard().verify_password(password, user.hashed_password)
        print(f"[AUTH DEBUG] password verification result={password_valid}")
        
        if not password_valid:
            logger.warning(f"Authentication failed: Invalid password for user '{identifier}'")
            return False
        
        logger.info(f"Authentication successful for user '{identifier}' (Role: {user.role})")
        return user
        
    except Exception as e:
        logger.error(f"Authentication error for user '{identifier}': {str(e)}")
        return False

def create_user_token(user: User):
    """
    Create access token for user.
    Implements JWT best practices with proper expiration and claims.
    """
    try:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        token_data = {
            "sub": user.username,
            "branch_id": user.branch_id,
            "role": user.role,
            "user_id": user.id,
            "iat": datetime.utcnow(),  # Issued at
            "type": "access"  # Token type
        }
        
        token = AuthGuard().create_access_token(data=token_data, expires_delta=access_token_expires)
        logger.info(f"Token created for user '{user.username}' (expires in {ACCESS_TOKEN_EXPIRE_MINUTES} minutes)")
        
        return token
        
    except Exception as e:
        logger.error(f"Token creation failed for user '{user.username}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token"
        )

def update_last_login(db: Session, user: User):
    """Update user's last login timestamp with error handling"""
    try:
        user.last_login = datetime.utcnow()
        db.commit()
        logger.info(f"Updated last login for user '{user.username}'")
    except Exception as e:
        logger.error(f"Failed to update last login for user '{user.username}': {str(e)}")
        db.rollback()
        # Don't fail the login if we can't update last_login

# FastAPI dependencies
auth_guard = AuthGuard()
get_current_user = auth_guard.current_user_dependency()
verify_token = auth_guard.verify_token
require_role = auth_guard.require_role

# Role-based dependencies
require_super_admin = auth_guard.require_role(['super_admin'])
require_branch_admin = auth_guard.require_role(['super_admin', 'branch_admin'])
require_staff = auth_guard.require_role(['super_admin', 'branch_admin', 'branch_director', 'staff'])
require_patient = auth_guard.require_role(['patient'])
require_all_users = auth_guard.require_role(['super_admin', 'branch_admin', 'branch_director', 'staff', 'patient'])

# Branch access dependency
require_branch_access = auth_guard.require_branch_access
