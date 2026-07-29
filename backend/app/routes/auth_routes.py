from fastapi import APIRouter, Depends, HTTPException, Request, status
import json
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.utils.auth_system import (
    authenticate_user, create_user_token, update_last_login,
    auth_guard, TokenData, get_current_user
)
from app.models import User, Branch, ActivityLog
from app.models.staff import StaffProfile
from app.schemas.user import UserCreate, UserResponse, TokenResponse
from app.utils.auth_system import auth_guard
from app.utils.schema_compat import ensure_staff_daily_ops_column
from app.utils.schema_compat import ensure_branch_logo_column
from app.utils.schema_compat import table_exists

router = APIRouter()


def _public_file_url(path: Optional[str]) -> Optional[str]:
    raw = (path or "").strip()
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("/api/files/"):
        return f"http://localhost:8000{raw}"
    return f"http://localhost:8000/api/files/{raw.lstrip('/')}"


def _build_user_photo_payload(db: Session, user: User) -> dict:
    profile = db.query(StaffProfile).filter(StaffProfile.user_id == user.id).first()
    photo_url = _public_file_url(profile.photo_path) if profile else None
    if not photo_url and user.role == "super_admin":
        if table_exists(db, "system_settings"):
            profile_row = db.execute(
                text("SELECT setting_value FROM system_settings WHERE setting_key = 'ceo_profile' LIMIT 1")
            ).scalar()
            if isinstance(profile_row, str) and profile_row.strip():
                try:
                    parsed = json.loads(profile_row)
                    if isinstance(parsed, dict):
                        profile_photo_path = (parsed.get("profile_photo_url") or "").strip()
                        if profile_photo_path:
                            photo_url = _public_file_url(profile_photo_path)
                except json.JSONDecodeError:
                    pass
    return {
        "profilePhoto": photo_url,
        "photo": photo_url,
    }


def _fetch_company_logo_url(db: Session) -> Optional[str]:
    if not table_exists(db, "system_settings"):
        return None

    branding_row = db.execute(
        text(
            """
            SELECT setting_value
            FROM system_settings
            WHERE setting_key IN ('ceo_branding', 'branding')
            ORDER BY CASE WHEN setting_key = 'ceo_branding' THEN 0 ELSE 1 END
            LIMIT 1
            """
        )
    ).scalar()
    if not branding_row:
        return None

    try:
        parsed = json.loads(branding_row)
    except json.JSONDecodeError:
        return None

    candidates = [
        (parsed.get("assets") or {}).get("primary_logo_url"),
        (parsed.get("branding_asset_manager") or {}).get("primary_logo_web"),
        parsed.get("logo_url"),
    ]
    for candidate in candidates:
        value = (candidate or "").strip()
        if value:
            return _public_file_url(value)
    return None


def _build_company_payload(db: Session, user: User) -> dict:
    company_logo = _fetch_company_logo_url(db) if user.role == "super_admin" else None
    return {
        "companyLogo": company_logo,
    }


def _fetch_branch_logo_url(db: Session, branch_id: int) -> Optional[str]:
    ensure_branch_logo_column(db)
    logo_url = db.execute(
        text("SELECT logo_url FROM branches WHERE id = :branch_id"),
        {"branch_id": branch_id},
    ).scalar()
    normalized_logo = (logo_url or "").strip()
    if normalized_logo:
        return _public_file_url(normalized_logo)

    if not table_exists(db, "system_settings"):
        return None

    branding_row = db.execute(
        text(
            """
            SELECT setting_value
            FROM system_settings
            WHERE setting_key IN ('ceo_branding', 'branding')
            ORDER BY CASE WHEN setting_key = 'ceo_branding' THEN 0 ELSE 1 END
            LIMIT 1
            """
        )
    ).scalar()
    if not branding_row:
        return None

    try:
        parsed = json.loads(branding_row)
    except json.JSONDecodeError:
        return None

    candidates = [
        (parsed.get("assets") or {}).get("primary_logo_url"),
        (parsed.get("branding_asset_manager") or {}).get("primary_logo_web"),
        parsed.get("logo_url"),
    ]
    for candidate in candidates:
        value = (candidate or "").strip()
        if value:
            return _public_file_url(value)
    return None


def _build_branch_payload(db: Session, branch_id: Optional[int]):
    if not branch_id:
        return None
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        return None
    branch_logo = _fetch_branch_logo_url(db, branch.id)
    return {
        "id": branch.id,
        "name": branch.name,
        "logo_url": branch_logo,
    }


@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """User login endpoint with comprehensive error logging"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        # Accept both JSON and form payloads for backwards compatibility.
        content_type = request.headers.get("content-type", "")
        username = None
        password = None

        if "application/json" in content_type:
            payload = await request.json()
            if isinstance(payload, dict):
                username = payload.get("username")
                password = payload.get("password")
        else:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")

        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Both username and password are required"
            )

        # DEBUG LOGGING
        logger.info(f"🔐 LOGIN ATTEMPT - Username: {username}, Password Length: {len(password)}")
        print(f"[AUTH DEBUG] route received username={username!r}")
        
        # Check if user exists
        db_user = db.query(User).filter(User.username == username).first()
        if db_user:
            logger.info(f"✅ USER FOUND - ID: {db_user.id}, Username: {db_user.username}, Role: {db_user.role}, Active: {db_user.is_active}, Hash: {db_user.hashed_password[:20]}...")
            print(
                "[AUTH DEBUG] route fetched user="
                f"id={db_user.id}, username={db_user.username!r}, role={db_user.role!r}, is_active={db_user.is_active}"
            )
        else:
            logger.error(f"❌ USER NOT FOUND - Username: {username}")
            print("[AUTH DEBUG] route fetched user=None")
        
        user = authenticate_user(db, username, password)
        
        if not user:
            logger.error(f"❌ AUTHENTICATION FAILED - Username: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"✅ AUTHENTICATION SUCCESS - User: {user.username}, Role: {user.role}")
        
        # Create access token
        access_token = create_user_token(user)
        logger.info(f"✅ TOKEN CREATED - Length: {len(access_token)}")
        
        # Update last login
        update_last_login(db, user)
        logger.info(f"✅ LAST LOGIN UPDATED")
        
        # Log activity (wrapped in try-catch to prevent login failure)
        try:
            auth_guard.log_activity(
                db=db, 
                user=user, 
                action="login", 
                entity_type="user", 
                entity_id=user.id, 
                description=f"User {user.username} logged in"
            )
            logger.info(f"✅ ACTIVITY LOGGED")
        except Exception as log_error:
            logger.warning(f"⚠️  Failed to log activity: {log_error}")
        
        logger.info(f"✅ PREPARING RESPONSE")
        branch_payload = _build_branch_payload(db, user.branch_id)
        user_photo_payload = _build_user_photo_payload(db, user)
        company_payload = _build_company_payload(db, user)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "role": user.role,
                "branch_id": user.branch_id,
                "branch": branch_payload,
                **user_photo_payload,
                **company_payload,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "last_login": user.last_login
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 401)
        raise
    except Exception as e:
        # Catch ALL other exceptions and log them
        logger.error(f"❌❌❌ CRITICAL LOGIN ERROR ❌❌❌")
        logger.error(f"Error Type: {type(e).__name__}")
        logger.error(f"Error Message: {str(e)}")
        logger.error(f"Full Traceback:")
        logger.error(traceback.format_exc())
        
        # Also print to console for immediate visibility
        print("\n" + "="*80)
        print("❌❌❌ CRITICAL LOGIN ERROR ❌❌❌")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("Full Traceback:")
        print(traceback.format_exc())
        print("="*80 + "\n")
        
        # Return 500 with error details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during login: {str(e)}"
        )


@router.post("/public-register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def public_register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Public registration endpoint for patients and doctors - Returns auth token for auto-login"""
    
    # Check if username already exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Verify branch exists (if branch_id is provided and role is not patient)
    if user_data.branch_id and user_data.role != 'patient':
        branch = db.query(Branch).filter(Branch.id == user_data.branch_id).first()
        if not branch:
            raise HTTPException(
                status_code=404,
                detail="Branch not found"
            )
    
    # Set default role if not specified
    if not user_data.role:
        user_data.role = 'patient'
    
    # Validate role
    allowed_roles = ['patient', 'doctor']
    if user_data.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid role specified"
        )
    
    # For doctors, require branch_id
    if user_data.role == 'doctor' and not user_data.branch_id:
        raise HTTPException(
            status_code=400,
            detail="Branch selection is required for doctor role"
        )
    
    # Create new user
    hashed_password = auth_guard.hash_password(user_data.password)
    
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        branch_id=user_data.branch_id,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log activity
    try:
        auth_guard.log_activity(
            db=db,
            user=db_user,
            action="self_register",
            entity_type="user",
            entity_id=db_user.id,
            description=f"User {db_user.username} self-registered as {db_user.role}"
        )
    except Exception as log_error:
        print(f"⚠️ [PUBLIC_REGISTER] Failed to log activity: {log_error}")
    
    # Generate auth token for auto-login
    access_token = create_user_token(db_user)
    
    # Update last login
    update_last_login(db, db_user)
    branch_payload = _build_branch_payload(db, db_user.branch_id)
    company_payload = _build_company_payload(db, db_user)
    
    # Return token and user data for immediate login
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
            "first_name": db_user.first_name,
            "last_name": db_user.last_name,
            "phone": db_user.phone,
            "role": db_user.role,
            "branch_id": db_user.branch_id,
            "branch": branch_payload,
            **company_payload,
            "is_active": db_user.is_active,
            "created_at": db_user.created_at,
            "last_login": db_user.last_login
        }
    }

@router.post("/register", response_model=UserResponse)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_guard.require_role(['super_admin', 'branch_admin']))
):
    """Register new user (admin only)"""
    
    # Check if username already exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Verify branch exists (if branch_id is provided)
    if user_data.branch_id:
        branch = db.query(Branch).filter(Branch.id == user_data.branch_id).first()
        if not branch:
            raise HTTPException(
                status_code=404,
                detail="Branch not found"
            )
    
    # Create new user
    hashed_password = auth_guard.hash_password(user_data.password)
    
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        branch_id=user_data.branch_id,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log activity
    try:
        auth_guard.log_activity(
            db=db,
            user=current_user,
            action="create",
            entity_type="user",
            entity_id=db_user.id,
            description=f"Created user {db_user.username}"
        )
    except Exception as log_error:
        print(f"⚠️ [ADMIN_REGISTER] Failed to log activity: {log_error}")
    
    return UserResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        first_name=db_user.first_name,
        last_name=db_user.last_name,
        role=db_user.role,
        branch_id=db_user.branch_id,
        is_active=db_user.is_active
    )

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user information"""
    # Ensure created_at exists; if missing, fallback to now for response stability
    created_at = current_user.created_at if getattr(current_user, 'created_at', None) is not None else datetime.utcnow()
    last_login = getattr(current_user, 'last_login', None)

    can_access_daily_ops = None
    branch_payload = None
    user_photo_payload = _build_user_photo_payload(db, current_user)
    company_payload = _build_company_payload(db, current_user)
    if current_user.branch_id:
        ensure_branch_logo_column(db)
        branch = db.query(Branch).filter(Branch.id == current_user.branch_id).first()
        if branch:
            branch_logo = _fetch_branch_logo_url(db, branch.id)
            branch_payload = {
                "id": branch.id,
                "name": branch.name,
                "logo_url": branch_logo,
            }

    if current_user.role == "staff" and current_user.branch_id:
        ensure_staff_daily_ops_column(db)
        profile = (
            db.query(StaffProfile)
            .filter(StaffProfile.user_id == current_user.id, StaffProfile.branch_id == current_user.branch_id)
            .first()
        )
        can_access_daily_ops = bool(profile.can_access_daily_ops) if profile else False

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "branch_id": current_user.branch_id,
        "is_active": current_user.is_active,
        "branch": branch_payload,
        **user_photo_payload,
        **company_payload,
        "can_access_daily_ops": can_access_daily_ops,
        "created_at": created_at,
        "last_login": last_login,
    }

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """User logout endpoint"""
    
    # Log activity
    try:
        auth_guard.log_activity(
            db=db,
            user=current_user,
            action="logout",
            entity_type="user",
            entity_id=current_user.id,
            description=f"User {current_user.username} logged out"
        )
    except Exception as log_error:
        print(f"⚠️ [LOGOUT] Failed to log activity: {log_error}")
    
    return {"message": "Successfully logged out"}

@router.get("/branches")
def get_user_branches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get branches accessible to current user"""
    
    if current_user.role == 'super_admin':
        branches = db.query(Branch).filter(Branch.is_active == True).all()
    else:
        branches = db.query(Branch).filter(
            Branch.id == current_user.branch_id,
            Branch.is_active == True
        ).all()
    
    return [
        {
            "id": branch.id,
            "name": branch.name,
            "location": branch.location,
            "city": branch.city,
            "state": branch.state
        }
        for branch in branches
    ]

@router.post("/change-password")
def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    
    # Verify current password
    if not auth_guard.verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect current password"
        )
    
    # Hash new password
    hashed_new_password = auth_guard.hash_password(new_password)
    current_user.hashed_password = hashed_new_password
    
    db.commit()
    
    # Log activity
    try:
        auth_guard.log_activity(
            db=db,
            user=current_user,
            action="password_change",
            entity_type="user",
            entity_id=current_user.id,
            description=f"User {current_user.username} changed password"
        )
    except Exception as log_error:
        print(f"⚠️ [CHANGE_PASSWORD] Failed to log activity: {log_error}")
    
    return {"message": "Password changed successfully"}

@router.post("/refresh-token", response_model=TokenResponse)
def refresh_access_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    
    access_token = create_user_token(current_user)
    branch_payload = _build_branch_payload(db, current_user.branch_id)
    company_payload = _build_company_payload(db, current_user)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "role": current_user.role,
            "branch_id": current_user.branch_id,
            "branch": branch_payload,
            **company_payload,
        }
    }

@router.get("/verify-token")
def verify_token_validity(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verify if current token is valid"""
    branch_payload = _build_branch_payload(db, current_user.branch_id)
    company_payload = _build_company_payload(db, current_user)
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "role": current_user.role,
            "branch_id": current_user.branch_id,
            "branch": branch_payload,
            **company_payload,
        }
    }
