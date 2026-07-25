from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from datetime import datetime


# Import your existing routers and components
from app.routes.auth_routes import router as auth_router
from app.routes.patient_management import router as patient_router
from app.routes.staff_api import leave_router as staff_leave_router
from app.routes.staff_api import staff_router as staff_api_router
from app.routes.inventory_management import router as inventory_router
from app.routes.export_routes import router as export_router
from app.routes.analytics import router as analytics_router
from app.routes.daily_entry import router as daily_entry_router

# Import NEW modern feature routers
from app.routes.doctor_management import router as doctor_router
from app.routes.report_distribution import router as report_distribution_router
from app.routes.ai_routes import router as ai_router

# Create FastAPI app
app = FastAPI(
    title="VaidyaVihar Diagnostic ERP API",
    description="Comprehensive ERP system for diagnostic centers with AI-powered features",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:51394",
        "http://localhost:51394",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://0.0.0.0:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://0.0.0.0:5173",
    ],
    allow_origin_regex=r"https?://(localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0)(:\\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include EXISTING routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(patient_router, prefix="/api/patients", tags=["Patients"])
app.include_router(staff_api_router, prefix="/api", tags=["Staff"])
app.include_router(staff_leave_router, prefix="/api", tags=["Staff Leave"])
app.include_router(inventory_router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(export_router, prefix="/api/export", tags=["Export"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(daily_entry_router, prefix="/api/daily-entry", tags=["Daily Entry"])

# Include NEW modern feature routers
app.include_router(doctor_router, prefix="/api/doctors", tags=["Doctor Management"])
app.include_router(report_distribution_router, prefix="/api/reports", tags=["Report Distribution"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI & Recommendations"])


@app.get("/")
async def root():
    return {
        "message": "VaidyaVihar Diagnostic ERP API", 
        "version": "2.0.0", 
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "VaidyaVihar Diagnostic ERP API",
            "version": "2.0.0"
        }
    )

@app.get("/api-info")
async def api_info():
    return {
        "name": "VaidyaVihar Diagnostic ERP API",
        "version": "2.0.0",
        "modules": [
            {"name": "Authentication", "endpoints": ["POST /api/auth/login", "POST /api/auth/register"]},
            {"name": "Patients", "endpoints": ["GET/POST /api/patients/", "GET/PUT/DELETE /api/patients/{id}"]},
            {"name": "Doctors (NEW)", "endpoints": ["GET/POST /api/doctors/", "City-wide doctor search"]},
            {"name": "Report Distribution (NEW)", "endpoints": ["POST /api/reports/distribute", "GET /api/reports/pending-for-doctor/{id}"]},
            {"name": "AI & Recommendations (NEW)", "endpoints": ["POST /api/ai/test-recommendations", "POST /api/ai/risk-assessment"]}
        ]
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

