from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
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
from app.models import ActivityLog, Company, Role, User, UserCompany
from app.utils.authority_resolver import (
    SYSTEM_ADMIN_ROLE,
    get_permission_codes,
    is_super_ceo,
    normalize_role_name,
    require_permissions,
)
from app.services.authority_integrity import canonical_super_ceo_count

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_super_ceo_user(user: User | None) -> bool:
    """Backward-compatible alias for canonical Super CEO authority resolution."""
    return is_super_ceo(user)


# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-for-vaidya-vihar-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 10080))  # 7 days (10080 minutes)
SYSTEM_PERMISSIONS = [
    "create_company",
    "edit_company",
    "delete_company",
    "view_all_companies",
    "assign_company_admin",
    "view_system_dashboard",
    "manage_system_settings",
    "view_audit_logs",
]
COMPANY_PERMISSIONS = [
    "manage_brands",
    "manage_branches",
    "manage_company_users",
    "view_company_settings",
    "manage_company_settings",
    "view_customers",
    "manage_inventory",
    "manage_orders",
    "manage_staff",
]

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
        issued_at: datetime | None = None,
    ):
        self.username = username
        self.branch_id = branch_id
        self.role = role
        self.token_type = token_type
        self.scope = scope
        self.user_id = user_id
        self.issued_at = issued_at

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
            # Hash format issue - try passlib fallback. Log the exception type only:
            # library ValueErrors can otherwise echo hash/salt fragments.
            logger.warning(f"Bcrypt verification failed ({type(e).__name__}), trying passlib fallback")
            try:
                result = pwd_context.verify(plain_password, hashed_password)
                if result:
                    logger.info("Password verification successful (passlib fallback)")
                else:
                    logger.warning("Password verification failed (passlib mismatch)")
                return result
            except Exception as fallback_error:
                logger.error(f"All password verification methods failed ({type(fallback_error).__name__})")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error during password verification ({type(e).__name__})")
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
            from app.services.token_revocation import is_token_revoked, is_user_session_revoked

            if is_token_revoked(credentials.credentials):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session has been signed out",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            branch_id: int = payload.get("branch_id")
            role: str = payload.get("role")
            token_type: str = payload.get("token_type") or payload.get("type") or "access"
            scope: str = payload.get("scope")
            user_id: int = payload.get("user_id")
            issued_at_raw = payload.get("iat")
            issued_at = None
            if isinstance(issued_at_raw, (int, float)):
                issued_at = datetime.utcfromtimestamp(issued_at_raw)
            elif isinstance(issued_at_raw, str):
                try:
                    issued_at = datetime.fromisoformat(issued_at_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    issued_at = None
            elif isinstance(issued_at_raw, datetime):
                issued_at = issued_at_raw.replace(tzinfo=None)
            
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if is_user_session_revoked(user_id, issued_at):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session has been signed out",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(
                username=username,
                branch_id=branch_id,
                role=role,
                token_type=token_type,
                scope=scope,
                user_id=user_id,
                issued_at=issued_at,
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

        if user is None or (token_data.user_id is not None and user.id != token_data.user_id):
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

        if user.password_changed_at and (
            token_data.issued_at is None or token_data.issued_at <= user.password_changed_at
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Login credentials changed. Please sign in again.",
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
        normalized_allowed = {normalize_role_name(role) for role in allowed_roles}

        def role_checker(current_user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
            if SYSTEM_ADMIN_ROLE in normalized_allowed and canonical_super_ceo_count(db) != 1:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Canonical Super CEO integrity check failed",
                )
            normalized_user_role = normalize_role_name(current_user.role)
            if (
                normalized_user_role not in normalized_allowed
                and not (SYSTEM_ADMIN_ROLE in normalized_allowed and is_super_ceo(current_user))
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return current_user
        return role_checker
    
    def require_branch_access(self, current_user: User = Depends(get_current_user)):
        """Ensure user has access to their assigned branch"""
        if current_user.branch_id is None and normalize_role_name(current_user.role) != SYSTEM_ADMIN_ROLE:
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
def resolve_login_user(db: Session, identifier: str) -> User | None:
    normalized = (identifier or "").strip()
    if not normalized:
        return None

    staff_phone = (
        db.query(User)
        .filter(
            User.is_staff.is_(True),
            User.is_deleted.is_(False),
            User.phone == normalized,
        )
        .first()
    )
    if staff_phone is not None:
        return staff_phone

    direct_match = db.query(User).filter(or_(User.username == normalized, User.email == normalized)).first()
    if direct_match is not None:
        return direct_match

    staff_email = (
        db.query(User)
        .filter(
            User.is_staff.is_(True),
            User.is_deleted.is_(False),
            func.lower(User.email) == normalized.lower(),
        )
        .first()
    )
    if staff_email is not None:
        return staff_email

    staff_code_matches = (
        db.query(User)
        .filter(
            User.is_staff.is_(True),
            User.is_deleted.is_(False),
            func.lower(User.employee_code) == normalized.lower(),
        )
        .order_by(User.id.asc())
        .all()
    )
    if len(staff_code_matches) == 1:
        return staff_code_matches[0]
    if len(staff_code_matches) > 1:
        raise HTTPException(status_code=401, detail="Ambiguous staff login identifier")
    return None


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
        user = resolve_login_user(db, identifier)
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error for user '{identifier}': {str(e)}")
        return False

def get_user_permissions(user: User) -> list[str]:
    """Return a flattened list of permission codes for the current user."""
    if is_super_ceo(user):
        return list(dict.fromkeys(SYSTEM_PERMISSIONS + COMPANY_PERMISSIONS))

    canonical_permissions = get_permission_codes(user)
    if canonical_permissions:
        return sorted(canonical_permissions)
    role_name = normalize_role_name(getattr(user, "role", ""))
    if role_name in {"company_admin", "branch_admin", "branch_director"}:
        return list(dict.fromkeys(COMPANY_PERMISSIONS))
    return []


def require_permission(required_permissions: list[str] | str):
    """FastAPI dependency that enforces a permission set for the current user."""
    required = [required_permissions] if isinstance(required_permissions, str) else required_permissions
    return require_permissions(required, get_current_user)


def get_user_company_context(db: Session, user: User):
    """Build the list of companies the user can access and the active company context."""
    company_records = []
    if is_super_ceo(user):
        all_companies = db.query(Company).order_by(Company.name.asc()).all()
        for company in all_companies:
            company_records.append({
                "id": company.id,
                "name": company.name,
                "role": SYSTEM_ADMIN_ROLE,
            })
        active_company_id = user.current_company_id or user.company_id or (all_companies[0].id if all_companies else None)
        return company_records, active_company_id

    assignments = db.query(UserCompany).filter(UserCompany.user_id == user.id, UserCompany.is_active.is_(True)).all()
    for assignment in assignments:
        company = db.query(Company).filter(Company.id == assignment.company_id).first()
        if not company:
            continue
        role_name = "staff"
        if assignment.role_id:
            role_obj = db.query(Role).filter(Role.id == assignment.role_id).first()
            if role_obj:
                role_name = role_obj.slug
        company_records.append({
            "id": company.id,
            "name": company.name,
            "role": role_name,
        })

    if not company_records and user.company_id:
        company = db.query(Company).filter(Company.id == user.company_id).first()
        if company:
            company_records.append({"id": company.id, "name": company.name, "role": user.role or "staff"})

    active_company_id = user.current_company_id or user.company_id or (company_records[0]["id"] if company_records else None)
    return company_records, active_company_id


def validate_company_access(db: Session, user: User, company_id: int | None) -> bool:
    """Ensure the user may access the requested company."""
    if company_id is None:
        return True
    if is_super_ceo(user):
        return db.query(Company).filter(Company.id == company_id).first() is not None
    if user.company_id == company_id or user.current_company_id == company_id:
        return True
    assignment = db.query(UserCompany).filter(
        UserCompany.user_id == user.id,
        UserCompany.company_id == company_id,
        UserCompany.is_active.is_(True),
    ).first()
    return assignment is not None


def create_user_token(user: User):
    """
    Create access token for user.
    Implements JWT best practices with proper expiration and claims.
    """
    try:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        company_id = getattr(user, "current_company_id", None) or getattr(user, "company_id", None)
        normalized_role = normalize_role_name(getattr(user, "role", "")) or getattr(user, "role", "")
        token_data = {
            "sub": user.username,
            "branch_id": user.branch_id,
            "company_id": company_id,
            "role": normalized_role,
            "user_id": user.id,
            "is_super_admin": bool(getattr(user, "is_super_admin", False)),
            "is_super_ceo": is_super_ceo(user),
            "is_company_ceo": bool(getattr(user, "is_company_ceo", False)),
            "is_outlet_manager": bool(getattr(user, "is_outlet_manager", False)),
            "outlet_id": getattr(user, "outlet_id", None) if getattr(user, "is_outlet_manager", False) else None,
            "permissions": get_user_permissions(user),
            "iat": datetime.now(timezone.utc).timestamp(),
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
require_super_admin = auth_guard.require_role(['super_ceo'])
require_branch_admin = auth_guard.require_role(['super_ceo', 'branch_admin'])
require_staff = auth_guard.require_role(['super_ceo', 'branch_admin', 'branch_director', 'staff'])
require_patient = auth_guard.require_role(['patient'])
require_all_users = auth_guard.require_role(['super_ceo', 'branch_admin', 'branch_director', 'staff', 'patient'])

# Branch access dependency
require_branch_access = auth_guard.require_branch_access
