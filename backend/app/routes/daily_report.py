from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.calendar_day import CalendarDay
from app.models.expense_entry import ExpenseEntry
from app.models.note_entry import NoteEntry

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/daily-report/{calendar_day_id}")
def generate_daily_report(calendar_day_id: int, db: Session = Depends(get_db)):
    day = db.query(CalendarDay).filter(CalendarDay.id == calendar_day_id).first()
    if not day:
        return {"error": "Calendar day not found"}

    customers = db.query(CustomerEntry).filter(CustomerEntry.calendar_day_id == calendar_day_id).all()
    expenses = db.query(ExpenseEntry).filter(ExpenseEntry.calendar_day_id == calendar_day_id).all()
    notes = db.query(NoteEntry).filter(NoteEntry.calendar_day_id == calendar_day_id).all()

    total_expense = sum(e.amount for e in expenses)
    report = {
        "branch": day.branch.name,
        "date": str(day.date),
        "status": day.status,
        "summary": day.summary,
        "customers": [{"name": p.name, "age": p.age, "gender": p.gender} for p in customers],
        "expenses": [{"amount": e.amount, "category": e.category, "notes": e.notes} for e in expenses],
        "notes": [{"author": n.author, "content": n.content} for n in notes],
        "total_expense": total_expense
    }
    return report
from fastapi.responses import Response
from app.utils.pdf_generator import generate_daily_report_pdf

@router.get("/daily-report/{calendar_day_id}/pdf")
def download_daily_report_pdf(calendar_day_id: int, db: Session = Depends(get_db)):
    # Fetch data same as your JSON report
    day = db.query(CalendarDay).filter(CalendarDay.id == calendar_day_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="Calendar day not found")

    customers = db.query(CustomerEntry).filter(CustomerEntry.calendar_day_id == calendar_day_id).all()
    expenses = db.query(ExpenseEntry).filter(ExpenseEntry.calendar_day_id == calendar_day_id).all()
    notes = db.query(NoteEntry).filter(NoteEntry.calendar_day_id == calendar_day_id).all()

    report_data = {
        "branch": day.branch.name,
        "date": str(day.date),
        "status": day.status,
        "summary": day.summary,
        "customers": customers,
        "expenses": expenses,
        "notes": notes,
        "total_expense": sum(e.amount for e in expenses)
    }

    pdf_bytes = generate_daily_report_pdf(report_data)
    return Response(content=pdf_bytes, media_type="application/pdf")