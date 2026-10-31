from fastapi import Depends, FastAPI, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from jose import JWTError, jwt
import uvicorn
import os
from datetime import datetime

# Import your existing routers and components
from app.routes.auth_routes import router as auth_router
from app.routes.auth_otp import router as auth_otp_router
from app.routes.patient_management import router as patient_router
from app.routes.inventory_management import router as inventory_router
from app.routes.export_routes import router as export_router
from app.routes.analytics import router as analytics_router
from app.routes.daily_entry import router as daily_entry_router
from app.routes.branch_management import router as branch_router
from app.routes.appointment import router as appointment_router
from app.routes.invoice import router as invoice_router
from app.routes.lab_result import router as lab_result_router
from app.routes.legacy_compat import router as legacy_compat_router
from app.routes.assets import router as assets_router
from app.routes.activity_logs import router as activity_logs_router

# New Feature Routers
from app.routes.payment_routes import router as payment_router
from app.routes.accounting_routes import router as accounting_router
from app.routes.hr_routes import router as hr_router
from app.routes.branch_lis import router as branch_lis_router
from app.routes.patient_portal_routes import router as patient_portal_router
from app.routes.doctor_portal_routes import router as doctor_portal_router
from app.routes.doctor_portal_api import router as doctor_portal_api_router
from app.routes.ai_routes import router as ai_router
from app.routes.staff_crm import router as staff_router
from app.routes.report_distribution import router as report_dist_router
from app.routes.dailyentry_demo import router as dailyentry_demo_router
from app.routes.daily_entry_module import router as daily_entry_module_router
from app.routes.inventory import router as inventory_v2_router
from app.routes.branch_bank_details import router as branch_bank_router
from app.routes.file_serving import router as file_serving_router
from app.routes.director_staff_routes import router as director_staff_router
from app.routes.director import director_profile_router
from app.routes.staff_api import leave_router as staff_leave_router
from app.routes.staff_api import staff_router as staff_api_router
from app.routes.accounts import router as accounts_router
from app.routes.patient_portal import router as patient_portal_v2_router
from app.routes.patient_b2c_phase1 import router as patient_b2c_phase1_router
from app.routes.patient.phase4 import router as patient_phase4_router
from app.routes.overview import router as overview_router
from app.routes.staff import router as staff_profile_router
from app.routes.payroll import router as payroll_router
from app.routes.branch_payroll import router as branch_payroll_router
from app.routes.branch_notifications import router as branch_notifications_router
from app.routes.tasks import router as tasks_router
from app.routes.ceo import router as ceo_router
from app.routes.public import router as public_router
from app.routes.search import router as search_router
from app.routes.super_admin import router as super_admin_router
from app.routes.themes import router as themes_router
from app.routes.super_ceo.metrics import router as super_ceo_metrics_router, overview_router as super_ceo_overview_metrics_router, derived_router as super_ceo_derived_router
from app.routes.super_ceo.themes import router as super_ceo_themes_router, static_router as super_ceo_themes_static_router
from app.routes.super_ceo.companies import router as super_ceo_companies_router
from app.routes.super_ceo.profile import router as super_ceo_profile_router
from app.routes.super_ceo.parent_company import router as super_ceo_parent_company_router
from app.routes.uploads import router as uploads_router
from app.routes.company_ceo import router as company_ceo_router
from app.routes.company_ceo.outlets import router as company_ceo_outlets_router
from app.routes.manager import router as manager_router
from app.routes.attendance import router as managed_attendance_router
from app.routes.branch_payments import (
    router as branch_payments_router,
    start_branch_payment_scheduler,
    stop_branch_payment_scheduler,
)
from app.utils.auth_system import require_role, auth_guard, SECRET_KEY, ALGORITHM, validate_company_access
from app.services.authority_integrity import check_canonical_super_ceo_integrity
from app.services.token_revocation import is_token_revoked
from app.services.websocket_service import (
    DomainSubscriber,
    domain_events_endpoint,
    theme_updates_endpoint,
    websocket_endpoint,
)
from app.database import Base, SessionLocal, engine, test_connection
from app.models import ProfileType, User, UserCompany
from app.models.company_structure import ensure_food_erp_seed_data, ensure_sqlite_schema_compatibility
from app.models.patient_entry import CustomerEntry
from app.models.daily_entry_module import DailyEntryModule
from app.models.lab_test import LabMenuItem
import app.models
import app.models.lis
import app.models.staff
import app.models.branch_lis

# Create FastAPI app
app = FastAPI(
    title="VaidyaVihar Diagnostic ERP API",
    description="Comprehensive ERP system for diagnostic centers",
    version="2.0.0"
)


@app.exception_handler(RequestValidationError)
async def validation_error_response(request: Request, exc: RequestValidationError):
    if request.url.path.endswith("/credentials"):
        return JSONResponse(
            status_code=422,
            headers={"Cache-Control": "no-store"},
            content={"detail": [
                {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
                for error in exc.errors()
            ]},
        )
    return await request_validation_exception_handler(request, exc)
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.websocket("/ws")
async def authenticated_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Authentication required")
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        await websocket.close(code=4401, reason="Invalid authentication token")
        return
    user_id = payload.get("user_id")
    if not user_id:
        await websocket.close(code=4401, reason="Invalid authentication token")
        return
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
        if not user:
            await websocket.close(code=4403, reason="User is inactive")
            return
        await websocket_endpoint(websocket, user.id, user.role, user.username)
    finally:
        db.close()


def _theme_socket_scope(db, user: User) -> tuple[int | None, int | None, str | None]:
    """Derive the profile type and company scope for a theme subscriber."""
    profile_key = "super_ceo" if getattr(user, "is_super_ceo", False) else str(getattr(user, "role", "") or "").strip().lower()
    profile = (
        db.query(ProfileType)
        .filter(ProfileType.code == profile_key, ProfileType.is_active.is_(True))
        .first()
        if profile_key
        else None
    )
    company_id = None if getattr(user, "is_super_ceo", False) else (user.current_company_id or user.company_id)
    return (profile.id if profile else None), company_id, (profile_key or None)


@app.websocket("/api/ws/theme-updates")
async def theme_updates_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Authentication required")
        return
    if is_token_revoked(token):
        await websocket.close(code=4401, reason="Session has been signed out")
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        await websocket.close(code=4401, reason="Invalid authentication token")
        return
    user_id = payload.get("user_id")
    if not user_id:
        await websocket.close(code=4401, reason="Invalid authentication token")
        return
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
        if not user:
            await websocket.close(code=4403, reason="User is inactive")
            return
        subscriber_id = user.id
        profile_type_id, company_id, profile_key = _theme_socket_scope(db, user)
    finally:
        db.close()

    await theme_updates_endpoint(
        websocket,
        subscriber_id,
        profile_type_id=profile_type_id,
        company_id=company_id,
        profile_type_key=profile_key,
    )


@app.websocket("/api/ws/outlet-events")
async def outlet_domain_events_websocket(websocket: WebSocket):
    """Scoped real-time outlet/manager domain event stream.

    Scope (company_id / outlet_id) is derived strictly from the
    authenticated user's own record - never from client-supplied query
    params - so a socket can only ever join its own tenant channel.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Authentication required")
        return
    if is_token_revoked(token):
        await websocket.close(code=4401, reason="Session has been signed out")
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        await websocket.close(code=4401, reason="Invalid authentication token")
        return
    user_id = payload.get("user_id")
    if not user_id:
        await websocket.close(code=4401, reason="Invalid authentication token")
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
        if not user:
            await websocket.close(code=4403, reason="User is inactive")
            return

        is_outlet_manager = bool(getattr(user, "is_outlet_manager", False))
        is_company_ceo = bool(getattr(user, "is_company_ceo", False))
        if not is_outlet_manager and not is_company_ceo:
            await websocket.close(code=4403, reason="Company CEO or Outlet Manager access required")
            return

        company_id = user.company_id
        if not company_id:
            await websocket.close(code=4403, reason="No company scope assigned")
            return

        outlet_id = user.outlet_id if is_outlet_manager else None
        if is_outlet_manager and not outlet_id:
            await websocket.close(code=4403, reason="No outlet scope assigned")
            return

        subscriber = DomainSubscriber(
            user_id=user.id,
            role=user.role,
            company_id=company_id,
            outlet_id=outlet_id,
        )
    finally:
        db.close()

    await domain_events_endpoint(websocket, subscriber)


@app.middleware("http")
async def tenant_company_middleware(request: Request, call_next):
    path = request.url.path
    if path in {"/docs", "/openapi.json", "/redoc", "/health", "/"} or path.startswith("/api/auth/") or path.startswith("/api/public"):
        return await call_next(request)

    authorization = request.headers.get("authorization")
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        return await call_next(request)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return await call_next(request)

    user_id = payload.get("user_id")
    company_id = payload.get("company_id")
    request.state.user_id = user_id
    request.state.company_id = company_id
    request.state.role = payload.get("role")
    request.state.is_super_admin = bool(payload.get("is_super_admin"))
    request.state.is_super_ceo = bool(payload.get("is_super_ceo"))

    header_company_id = request.headers.get("x-company-id")
    if header_company_id:
        try:
            requested_company_id = int(header_company_id)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "X-Company-ID must be an integer"})

        if user_id is None:
            return JSONResponse(status_code=401, content={"detail": "Authentication required for company access"})

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not validate_company_access(db, user, requested_company_id):
                return JSONResponse(status_code=403, content={"detail": "User does not have access to this company"})
            request.state.company_id = requested_company_id
            request.state.current_company_id = requested_company_id
        finally:
            db.close()

    response = await call_next(request)
    return response


# CORS middleware - Explicitly allow localhost origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://0.0.0.0",
        "https://localhost",
        "https://127.0.0.1",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://0.0.0.0:4173",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Include routers - Existing
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(auth_otp_router, tags=["OTP Authentication"])
# IMPORTANT: daily_entry_module_router MUST be registered before patient_router
# to ensure /api/daily-entries/grid is matched before /api/daily-entries/{entry_id}
app.include_router(daily_entry_module_router, tags=["Daily Entry Module"])
app.include_router(patient_router, prefix="/api", tags=["Customers"])
# Register staff self-service routes before generic /api/staff/{staff_profile_id} routes.
# This prevents 'me' from being treated as a dynamic path parameter.
app.include_router(staff_profile_router, prefix="/api", tags=["Staff Self Service"])
app.include_router(managed_attendance_router, prefix="/api")
app.include_router(staff_api_router, prefix="/api", tags=["Staff"])
app.include_router(staff_leave_router, prefix="/api", tags=["Staff Leave"])
app.include_router(inventory_router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(export_router, prefix="/api/export", tags=["Export"])
app.include_router(analytics_router, prefix="", tags=["Analytics"])
app.include_router(daily_entry_router, prefix="/api/daily-entry", tags=["Daily Entry"])
app.include_router(branch_router, prefix="/api", tags=["Branch Management"])
app.include_router(assets_router, prefix="/api", tags=["Assets"])
app.include_router(activity_logs_router, prefix="/api", tags=["Audit Logs"])
app.include_router(appointment_router, prefix="", tags=["Appointments"])
app.include_router(invoice_router, prefix="", tags=["Invoices"])
app.include_router(lab_result_router, prefix="", tags=["Lab Results"])
app.include_router(legacy_compat_router, prefix="", tags=["Legacy Compatibility"])

# New Feature Routers
app.include_router(payment_router, prefix="/api/payments", tags=["Payments"])
app.include_router(accounting_router, prefix="/api/accounting", tags=["Accounting"])
app.include_router(hr_router, prefix="/api/hr", tags=["HR & Payroll"])
app.include_router(branch_lis_router, tags=["Branch LIS"])
app.include_router(patient_portal_router, prefix="/api/patient-portal", tags=["Customer Portal"])
app.include_router(doctor_portal_router, prefix="/api/doctor-portal", tags=["Staff Portal"], dependencies=[Depends(require_role(["doctor"]))])
app.include_router(doctor_portal_api_router, prefix="/api/doctor", tags=["Staff Portal API"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI Features"])
app.include_router(staff_router, tags=["Staff Management CRM"])
app.include_router(report_dist_router, prefix="/api/orders", tags=["Order Distribution"])
app.include_router(dailyentry_demo_router, tags=["Daily Entry Demo"])
app.include_router(branch_bank_router, prefix="/api/branches", tags=["Branch Bank Details"])
app.include_router(file_serving_router, prefix="/api", tags=["File Serving"])
app.include_router(director_staff_router, prefix="/api/director", tags=["Director & Staff Management"])
app.include_router(director_profile_router, prefix="/api/director-v2", tags=["Director Management V2"])
app.include_router(inventory_v2_router, tags=["Inventory V2"])
app.include_router(accounts_router, tags=["Accounts & Finance"])
app.include_router(patient_b2c_phase1_router, tags=["Customer B2C Phase 1"])
app.include_router(patient_phase4_router, tags=["Customer Phase 4"])
app.include_router(patient_portal_v2_router, tags=["Customer Portal V2"])
app.include_router(overview_router, prefix="/api/overview", tags=["Overview Dashboard"])
app.include_router(payroll_router, prefix="/api", tags=["Payroll Management"])
app.include_router(branch_payroll_router, prefix="/api/branch/payroll", tags=["Branch Payroll Command Center"])
app.include_router(branch_notifications_router, prefix="/api", tags=["Branch Notifications"])
app.include_router(tasks_router, prefix="/api", tags=["Task Management"])
app.include_router(ceo_router, prefix="/api", tags=["CEO Security"])
app.include_router(public_router, prefix="/api", tags=["Public"])
app.include_router(search_router, tags=["Search/Autocomplete"])
app.include_router(super_ceo_companies_router, prefix="/api")
app.include_router(super_ceo_profile_router, prefix="/api")
app.include_router(super_ceo_parent_company_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
app.include_router(company_ceo_router, prefix="/api")
app.include_router(company_ceo_outlets_router, prefix="/api")
app.include_router(manager_router, prefix="/api")
app.include_router(super_admin_router, prefix="/api/super-ceo", tags=["Super CEO"])
app.include_router(super_admin_router, prefix="/api/super-admin", tags=["Legacy Super Admin Compatibility"])
app.include_router(branch_payments_router, tags=["Branch Payments Dashboard"])
app.include_router(themes_router, prefix="/api", tags=["Themes"])
app.include_router(super_ceo_themes_static_router, prefix="/api")
app.include_router(super_ceo_themes_router, prefix="/api")
app.include_router(super_ceo_metrics_router, prefix="/api")
app.include_router(super_ceo_overview_metrics_router, prefix="/api")
app.include_router(super_ceo_derived_router, prefix="/api")


@app.on_event("startup")
async def initialize_app_runtime():
    # Ensure the SQLite schema exists before any login or API request touches it.
    db = SessionLocal()
    try:
        ensure_sqlite_schema_compatibility(db)
    finally:
        db.close()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        company = ensure_food_erp_seed_data(db)

        if not db.query(User).filter(User.username == "sujitep").first():
            default_admin = User(
                username="sujitep",
                email="sujit@foodsrijan.com",
                hashed_password=auth_guard.hash_password("#sujitep54970"),
                role="super_ceo",
                company_id=company.id,
                current_company_id=company.id,
                first_name="Sujit",
                last_name="Singh",
                phone="9999999999",
                is_super_admin=True,
                is_super_ceo=True,
                is_active=True,
            )
            db.add(default_admin)
            db.commit()
            db.refresh(default_admin)
            db.add(UserCompany(user_id=default_admin.id, company_id=company.id, is_active=True))
            db.commit()
            print("[BOOTSTRAP] Seeded default Super CEO user: sujitep")
        else:
            default_admin = db.query(User).filter(User.username == "sujitep").first()
            default_admin.email = "sujit@foodsrijan.com"
            default_admin.is_super_admin = True
            default_admin.is_super_ceo = True
            default_admin.role = "super_ceo"
            default_admin.hashed_password = auth_guard.hash_password("#sujitep54970")
            if default_admin.company_id is None:
                default_admin.company_id = company.id
            if default_admin.current_company_id is None:
                default_admin.current_company_id = company.id
            if not db.query(UserCompany).filter(UserCompany.user_id == default_admin.id, UserCompany.company_id == company.id).first():
                db.add(UserCompany(user_id=default_admin.id, company_id=company.id, is_active=True))
            db.commit()

        check_canonical_super_ceo_integrity(db)
    except Exception as exc:
        db.rollback()
        print(f"[BOOTSTRAP] Failed to seed default admin user: {exc}")
    finally:
        db.close()

    start_branch_payment_scheduler()


@app.on_event("shutdown")
async def stop_branch_payments_jobs():
    stop_branch_payment_scheduler()

@app.get("/")
async def root():
    return {"message": "VaidyaVihar Diagnostic ERP API", "version": "2.0.0", "status": "running"}

@app.get("/health")
def health_check():
    database_available = test_connection()
    return JSONResponse(
        status_code=200 if database_available else 503,
        content={
            "status": "healthy" if database_available else "unhealthy",
            "database": "available" if database_available else "unavailable",
            "timestamp": datetime.now().isoformat(),
            "service": "VaidyaVihar Diagnostic ERP API"
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
