from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
import csv
from io import StringIO
from app.models.user import User
from app.database import get_db
from app.utils.auth_guard import get_current_user

router = APIRouter()

@router.get("/export/customers/")
def export_customers_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can export data")

    customers = db.query(CustomerEntry).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Age", "Gender", "Branch ID"])

    for p in customers:
        writer.writerow([p.id, p.name, p.age, p.gender, p.branch_id])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=customers.csv"
    })