from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from datetime import datetime

# Import your existing routers and components
from app.routes.auth_routes import router as auth_router
from app.routes.patient_management import router as patient_router
from app.routes.staff_management import router as staff_router
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
from app.routes.lis_routes import router as lis_router
from app.routes.patient_portal_routes import router as patient_portal_router
from app.routes.doctor_portal_routes import router as doctor_portal_router
from app.routes.ai_routes import router as ai_router
from app.routes.doctor_management import router as doctor_mgmt_router
from app.routes.report_distribution import router as report_dist_router
from app.routes.dailyentry_demo import router as dailyentry_demo_router
from app.routes.daily_entry_module import router as daily_entry_module_router
from app.routes.branch_bank_details import router as branch_bank_router
from app.routes.file_serving import router as file_serving_router

# Create FastAPI app
app = FastAPI(
    title="VaidyaVihar Diagnostic ERP API",
    description="Comprehensive ERP system for diagnostic centers",
    version="2.0.0"
)

# CORS middleware - Explicitly allow localhost origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"  # Fallback to allow all
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Include routers - Existing
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
# IMPORTANT: daily_entry_module_router MUST be registered before patient_router
# to ensure /api/daily-entries/grid is matched before /api/daily-entries/{entry_id}
app.include_router(daily_entry_module_router, tags=["Daily Entry Module"])
app.include_router(patient_router, prefix="/api", tags=["Patients"])
app.include_router(staff_router, prefix="/api/staff", tags=["Staff"])
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
app.include_router(lis_router, prefix="/api/lis", tags=["LIS"])
app.include_router(patient_portal_router, prefix="/api/patient-portal", tags=["Patient Portal"])
app.include_router(doctor_portal_router, prefix="/api/doctor-portal", tags=["Doctor Portal"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI Features"])
app.include_router(doctor_mgmt_router, prefix="/api/doctors", tags=["Doctor Management"])
app.include_router(report_dist_router, prefix="/api/reports", tags=["Report Distribution"])
app.include_router(dailyentry_demo_router, tags=["Daily Entry Demo"])
app.include_router(branch_bank_router, tags=["Branch Bank Details"])
app.include_router(file_serving_router, prefix="/api", tags=["File Serving"])

@app.get("/")
async def root():
    return {"message": "VaidyaVihar Diagnostic ERP API", "version": "2.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
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
