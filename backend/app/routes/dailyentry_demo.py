"""
Demo routes for the new dailyentry.py module
This provides a simple interface to test the Excel-based daily entry system
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import date, datetime
import os

# Import the new dailyentry module
try:
    from app.services.dailyentry import (
        create_daily_entry_manager,
        DataValidationError,
        CustomerNotFoundError,
        DailyEntryError
    )
    DAILYENTRY_AVAILABLE = True
except ImportError as e:
    DAILYENTRY_AVAILABLE = False
    print(f"Warning: dailyentry module not available: {e}")

router = APIRouter(prefix="/api/dailyentry-demo", tags=["Daily Entry Demo"])

# Create a demo manager instance
demo_manager = None

def get_demo_manager():
    """Get or create demo manager"""
    global demo_manager
    if demo_manager is None and DAILYENTRY_AVAILABLE:
        # Use /tmp for demo to avoid permission issues
        demo_manager = create_daily_entry_manager(
            branch_id="DEMO_BRANCH",
            branch_name="Demo Diagnostic Center",
            branch_code="DEMO",
            base_path="/tmp/erp_demo_data/"
        )
    return demo_manager

@router.get("/status")
async def get_status():
    """Check if dailyentry module is available"""
    return {
        "available": DAILYENTRY_AVAILABLE,
        "module_location": "backend/app/services/dailyentry.py",
        "demo_data_path": "/tmp/erp_demo_data/",
        "message": "Daily Entry Excel Manager is ready!" if DAILYENTRY_AVAILABLE else "Module not loaded"
    }

@router.post("/initialize")
async def initialize_demo():
    """Initialize the demo branch structure"""
    if not DAILYENTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Daily entry module not available")
    
    try:
        manager = get_demo_manager()
        folders = manager.initialize_branch_structure()
        return {
            "success": True,
            "message": "Demo branch initialized successfully",
            "folders": folders
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-patient")
async def add_demo_patient(patient_data: dict):
    """Add a demo patient record"""
    if not DAILYENTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Daily entry module not available")
    
    try:
        manager = get_demo_manager()
        
        # Ensure required fields
        required_fields = ['patient_name', 'age', 'gender', 'test_type', 'contact_number']
        for field in required_fields:
            if field not in patient_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        record = manager.add_patient_record(patient_data, created_by="Demo User")
        
        return {
            "success": True,
            "message": "Customer added successfully",
            "patient_id": record.patient_id,
            "patient_data": record.to_dict()
        }
    except DataValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customers/today")
async def get_todays_customers():
    """Get all customers from today"""
    if not DAILYENTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Daily entry module not available")
    
    try:
        manager = get_demo_manager()
        customers = manager.get_todays_customers()
        
        return {
            "success": True,
            "count": len(customers),
            "customers": [p.to_dict() for p in customers]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_statistics():
    """Get branch statistics"""
    if not DAILYENTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Daily entry module not available")
    
    try:
        manager = get_demo_manager()
        stats = manager.get_branch_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_daily_summary():
    """Get daily summary"""
    if not DAILYENTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Daily entry module not available")
    
    try:
        manager = get_demo_manager()
        summary = manager.generate_daily_summary()
        
        return {
            "success": True,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_customers(q: str):
    """Search for customers"""
    if not DAILYENTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Daily entry module not available")
    
    try:
        manager = get_demo_manager()
        results = manager.search_customers(q)
        
        return {
            "success": True,
            "query": q,
            "count": len(results),
            "results": [p.to_dict() for p in results]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/excel-file")
async def get_excel_file_info():
    """Get information about the current Excel file"""
    if not DAILYENTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Daily entry module not available")
    
    try:
        manager = get_demo_manager()
        filepath = manager.get_current_excel_file()
        
        file_exists = os.path.exists(filepath)
        file_size = os.path.getsize(filepath) if file_exists else 0
        
        return {
            "success": True,
            "filepath": filepath,
            "exists": file_exists,
            "size_bytes": file_size,
            "size_kb": round(file_size / 1024, 2) if file_exists else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-sample-data")
async def add_sample_data():
    """Add sample patient data for testing"""
    if not DAILYENTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Daily entry module not available")
    
    sample_customers = [
        {
            "patient_name": "John Doe",
            "age": 35,
            "gender": "Male",
            "test_type": "Blood MenuItem",
            "referring_doctor": "Dr. Smith",
            "status": "Pending",
            "contact_number": "9876543210",
            "notes": "Routine checkup"
        },
        {
            "patient_name": "Jane Smith",
            "age": 28,
            "gender": "Female",
            "test_type": "X-Ray",
            "referring_doctor": "Dr. Johnson",
            "status": "Completed",
            "contact_number": "9876543211",
            "notes": "Follow-up required"
        },
        {
            "patient_name": "Bob Wilson",
            "age": 45,
            "gender": "Male",
            "test_type": "ECG",
            "referring_doctor": "Dr. Brown",
            "status": "In Progress",
            "contact_number": "9876543212",
            "notes": "Cardiac evaluation"
        }
    ]
    
    try:
        manager = get_demo_manager()
        added_customers = []
        
        for patient_data in sample_customers:
            record = manager.add_patient_record(patient_data, created_by="Demo System")
            added_customers.append({
                "patient_id": record.patient_id,
                "name": record.patient_name
            })
        
        return {
            "success": True,
            "message": f"Added {len(added_customers)} sample customers",
            "customers": added_customers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
