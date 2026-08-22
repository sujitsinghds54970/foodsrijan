from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import os
from io import BytesIO

from app.database import get_db
from app.utils.auth_system import auth_guard, require_staff, get_current_user
from app.models import User, Branch
from app.schemas.user import MonthlyOrderRequest, ExportResponse
from app.utils.excel_export import export_service

router = APIRouter()

@router.post("/export/monthly-report", response_model=ExportResponse)
def export_monthly_report(
    request: MonthlyOrderRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Generate monthly patient history Excel report"""
    
    # Check branch access
    branch_id = request.branch_id
    if current_user.role != 'super_admin':
        branch_id = current_user.branch_id
    elif branch_id:
        # Verify branch exists and user has access if not super admin
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found")
    
    # Generate report
    result = export_service.generate_monthly_patient_report(
        db=db,
        year=request.year,
        month=request.month,
        branch_id=branch_id,
        doctor_name=request.doctor_name
    )
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="export",
        entity_type="monthly_report",
        description=f"Generated monthly report for {request.year}-{request.month:02d}"
    )
    
    return result

@router.post("/export/staff-attendance")
def export_staff_attendance(
    year: int,
    month: int,
    branch_id: Optional[int] = None,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Generate staff attendance Excel report"""
    
    # Check branch access
    if current_user.role != 'super_admin':
        branch_id = current_user.branch_id
    elif branch_id:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found")
    
    # Generate report
    result = export_service.generate_staff_attendance_report(
        db=db,
        year=year,
        month=month,
        branch_id=branch_id
    )
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="export",
        entity_type="staff_attendance_report",
        description=f"Generated staff attendance report for {year}-{month:02d}"
    )
    
    return result

@router.post("/export/inventory")
def export_inventory_report(
    branch_id: Optional[int] = None,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Generate inventory status Excel report"""
    
    # Check branch access
    if current_user.role != 'super_admin':
        branch_id = current_user.branch_id
    elif branch_id:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found")
    
    # Generate report
    result = export_service.generate_inventory_report(
        db=db,
        branch_id=branch_id
    )
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="export",
        entity_type="inventory_report",
        description="Generated inventory report"
    )
    
    return result

@router.get("/export/download/{filename}")
def download_report(
    filename: str,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Download generated Excel report"""
    
    # Security check - ensure user has access to this file
    # You might want to implement additional checks here
    
    filepath = export_service.download_file(filename)
    
    if not filepath:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="download",
        entity_type="report_file",
        description=f"Downloaded report file: {filename}"
    )
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@router.delete("/export/cleanup")
def cleanup_old_exports(
    days: int = 7,
    current_user: User = Depends(auth_guard.require_role(['super_admin', 'branch_admin'])),
    db: Session = Depends(get_db)
):
    """Clean up old export files (admin only)"""
    
    export_service.cleanup_old_files(days=days)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="cleanup",
        entity_type="export_files",
        description=f"Cleaned up export files older than {days} days"
    )
    
    return {"message": f"Cleaned up files older than {days} days"}

@router.get("/export/status")
def get_export_status(
    current_user: User = Depends(require_staff)
):
    """Get status of export service"""
    
    try:
        export_dir = export_service.base_path
        if not os.path.exists(export_dir):
            os.makedirs(export_dir, exist_ok=True)
            file_count = 0
            total_size = 0
        else:
            files = [f for f in os.listdir(export_dir) if f.endswith('.xlsx')]
            file_count = len(files)
            total_size = sum(os.path.getsize(os.path.join(export_dir, f)) for f in files)
        
        return {
            "export_directory": export_dir,
            "total_files": file_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "status": "active"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking export status: {str(e)}"
        )
