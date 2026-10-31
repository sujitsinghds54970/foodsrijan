from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.lab_test import LabMenuItem
from app.models.user import User
from app.database import get_db
from app.utils.auth_guard import get_current_user

router = APIRouter()

@router.post("/lab-menu_items/")
def assign_lab_test(
    patient_id: int,
    technician_id: int,
    test_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "technician"]:
        raise HTTPException(status_code=403, detail="Access denied")

    test = LabMenuItem(
        patient_id=patient_id,
        technician_id=technician_id,
        test_type=test_type
    )
    db.add(test)
    db.commit()
    db.refresh(test)

    return {
        "id": test.id,
        "test_type": test.test_type,
        "status": test.status,
        "created_at": test.created_at.isoformat()
    }
@router.put("/lab-menu_items/{test_id}/result/")
def submit_lab_result(
    test_id: int,
    result: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "technician":
        raise HTTPException(status_code=403, detail="Only technicians can submit results")

    test = db.query(LabMenuItem).filter(LabMenuItem.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="MenuItem not found")

    test.result = result
    test.status = "completed"
    db.commit()
    db.refresh(test)

    return {
        "id": test.id,
        "status": test.status,
        "result": test.result
    }
try:
    from weasyprint import HTML
except Exception:  # pragma: no cover - native PDF library may be unavailable in some environments
    HTML = None
from fastapi.responses import Response

@router.get("/lab-menu_items/{test_id}/pdf/")
def generate_lab_report_pdf(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    test = db.query(LabMenuItem).filter(LabMenuItem.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="MenuItem not found")

    html_content = f"""
    <html>
    <head><title>Lab Order #{test.id}</title></head>
    <body>
        <h1>Lab Order</h1>
        <p><strong>MenuItem ID:</strong> {test.id}</p>
        <p><strong>Customer ID:</strong> {test.patient_id}</p>
        <p><strong>Technician ID:</strong> {test.technician_id}</p>
        <p><strong>MenuItem Type:</strong> {test.test_type}</p>
        <p><strong>Status:</strong> {test.status}</p>
        <p><strong>Result:</strong><br>{test.result}</p>
        <p><strong>Created At:</strong> {test.created_at.strftime('%Y-%m-%d %H:%M')}</p>
    </body>
    </html>
    """

    if HTML is None:
        raise HTTPException(status_code=503, detail="PDF export is unavailable because the required native libraries are not installed")
    pdf = HTML(string=html_content).write_pdf()
    return Response(content=pdf, media_type="application/pdf")