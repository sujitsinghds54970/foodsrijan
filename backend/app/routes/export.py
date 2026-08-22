from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.invoice import Invoice
import csv
import io
import json

router = APIRouter()

@router.get("/export/invoices/csv")
def export_invoices_csv(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Customer ID", "Branch ID", "Amount", "Status", "Created At"])

    for invoice in invoices:
        writer.writerow([
            invoice.id,
            invoice.patient_id,
            invoice.branch_id,
            invoice.total_amount,
            invoice.status,
            invoice.created_at
        ])

    return Response(content=output.getvalue(), media_type="text/csv")


@router.get("/export/invoices/json")
def export_invoices_json(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).all()
    data = [
        {
            "id": i.id,
            "patient_id": i.patient_id,
            "branch_id": i.branch_id,
            "total_amount": i.total_amount,
            "status": i.status,
            "created_at": str(i.created_at)
        }
        for i in invoices
    ]
    return Response(content=json.dumps(data), media_type="application/json")