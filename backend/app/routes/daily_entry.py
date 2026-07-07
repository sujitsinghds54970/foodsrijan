from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date
from pydantic import BaseModel
from fastapi import Body

from app.database import get_db
from app.utils.auth_system import get_current_user

router = APIRouter(prefix="/daily-entries", tags=["daily_entries"])

class DailyEntryCreate(BaseModel):
    patient_id: int
    doctor_id: int
    visit_date: date
    consultation_fee: float = 0
    test_fee: float = 0
    test_type: str = ""
    notes: str = ""
    payment_status: str = "paid"
    branch_id: int

class DailyEntryUpdate(BaseModel):
    patient_id: int | None = None
    doctor_id: int | None = None
    visit_date: date | None = None
    consultation_fee: float | None = None
    test_fee: float | None = None
    test_type: str | None = None
    notes: str | None = None
    payment_status: str | None = None

class BulkUpdate(BaseModel):
    updates: List[DailyEntryUpdate]

class DailyEntryResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    visit_date: date
    consultation_fee: float
    test_fee: float
    total_amount: float
    test_type: str
    notes: str
    payment_status: str
    branch_id: int
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("/daily-entries", response_model=DailyEntryResponse)
async def create_daily_entry(entry: DailyEntryCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Create a new daily entry for patient visit"""
    
    # Verify user has access to this branch
    if current_user.branch_id != entry.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this branch")
    
    # Create the daily entry
    query = """
    INSERT INTO daily_entries (patient_id, doctor_id, visit_date, consultation_fee, 
                             test_fee, total_amount, test_type, notes, payment_status, 
                             branch_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    total_amount = entry.consultation_fee + entry.test_fee
    
    db.execute(query, (
        entry.patient_id, entry.doctor_id, entry.visit_date,
        entry.consultation_fee, entry.test_fee, total_amount,
        entry.test_type, entry.notes, entry.payment_status,
        entry.branch_id, datetime.now()
    ))
    
    # Get the created entry
    entry_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    result = db.execute("SELECT * FROM daily_entries WHERE id = ?", (entry_id,)).fetchone()
    
    db.commit()
    
    return DailyEntryResponse(**result._asdict())

@router.get("/daily-entries", response_model=List[DailyEntryResponse])
async def get_daily_entries(
    date: str = None,
    branch_id: int = None,
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """Get daily entries with optional date and branch filtering"""
    
    query = "SELECT * FROM daily_entries WHERE 1=1"
    params = []
    
    if date:
        query += " AND visit_date = ?"
        params.append(date)
    
    if branch_id:
        query += " AND branch_id = ?"
        params.append(branch_id)
    else:
        # Default to user's branch
        query += " AND branch_id = ?"
        params.append(current_user.branch_id)
    
    query += " ORDER BY visit_date DESC, created_at DESC"
    
    results = db.execute(query, params).fetchall()
    
    return [DailyEntryResponse(**row._asdict()) for row in results]

@router.get("/daily-entries/{entry_id}", response_model=DailyEntryResponse)
async def get_daily_entry(entry_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get a specific daily entry"""
    
    result = db.execute("SELECT * FROM daily_entries WHERE id = ?", (entry_id,)).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    if result.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")
    
    return DailyEntryResponse(**result._asdict())

@router.put("/daily-entries/{entry_id}", response_model=DailyEntryResponse)
async def update_daily_entry(
    entry_id: int, 
    entry_update: DailyEntryCreate,
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """Update a daily entry"""
    
    # Check if entry exists and user has access
    existing = db.execute("SELECT * FROM daily_entries WHERE id = ?", (entry_id,)).fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    if existing.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")
    
    # Update the entry
    total_amount = entry_update.consultation_fee + entry_update.test_fee
    
    db.execute("""
    UPDATE daily_entries SET 
        patient_id = ?, doctor_id = ?, visit_date = ?, consultation_fee = ?,
        test_fee = ?, total_amount = ?, test_type = ?, notes = ?,
        payment_status = ?, updated_at = ?
    WHERE id = ?
    """, (
        entry_update.patient_id, entry_update.doctor_id, entry_update.visit_date,
        entry_update.consultation_fee, entry_update.test_fee, total_amount,
        entry_update.test_type, entry_update.notes, entry_update.payment_status,
        datetime.now(), entry_id
    ))
    
    db.commit()
    
    # Get updated entry
    result = db.execute("SELECT * FROM daily_entries WHERE id = ?", (entry_id,)).fetchone()
    
    return DailyEntryResponse(**result._asdict())

@router.delete("/daily-entries/{entry_id}")
async def delete_daily_entry(entry_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Delete a daily entry"""
    
    # Check if entry exists and user has access
    existing = db.execute("SELECT * FROM daily_entries WHERE id = ?", (entry_id,)).fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    if existing.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")
    
    db.execute("DELETE FROM daily_entries WHERE id = ?", (entry_id,))
    db.commit()
    
    return {"message": "Entry deleted successfully"}

@router.get("/daily-summary")
async def get_daily_summary(
    date: str = None,
    branch_id: int = None,
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """Get daily summary statistics"""
    
    if not date:
        date = datetime.now().date().isoformat()
    
    if not branch_id:
        branch_id = current_user.branch_id
    
    # Get summary statistics
    summary = db.execute("""
    SELECT 
        COUNT(*) as total_patients,
        SUM(consultation_fee) as total_consultation_fee,
        SUM(test_fee) as total_test_fee,
        SUM(total_amount) as total_revenue,
        AVG(total_amount) as avg_revenue_per_patient
    FROM daily_entries 
    WHERE visit_date = ? AND branch_id = ?
    """, (date, branch_id)).fetchone()
    
    # Get pending amount
    pending = db.execute("""
    SUM(total_amount) FROM daily_entries 
    WHERE visit_date = ? AND branch_id = ? AND payment_status != 'paid'
    """, (date, branch_id)).fetchone()[0] or 0
    
    return {
        "date": date,
        "branch_id": branch_id,
        "total_patients": summary.total_patients or 0,
        "total_revenue": float(summary.total_revenue or 0),
        "pending_amount": float(pending),
    }

@router.get("/grid")
async def get_grid_data(
    date: str,
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Grid data with joined patient/doctor names and history"""
    if not branch_id:
        branch_id = current_user.branch_id
    
    rows = db.execute("""
        SELECT 
            de.id, de.patient_id, de.doctor_id, de.visit_date,
            de.consultation_fee, de.test_fee, de.total_amount,
            de.test_type, de.notes, de.payment_status, de.branch_id,
            p.first_name || ' ' || p.last_name as patient_name,
            p.phone as patient_phone,
            u.first_name || ' ' || u.last_name as doctor_name,
            (SELECT COUNT(*) FROM daily_entries de2 WHERE de2.patient_id = de.patient_id AND de2.branch_id = de.branch_id) as history_count
        FROM daily_entries de
        JOIN patients p ON de.patient_id = p.id
        LEFT JOIN users u ON de.doctor_id = u.id
        WHERE de.visit_date = ? AND de.branch_id = ?
        ORDER BY de.created_at DESC
    """, (date, branch_id)).fetchall()
    
    entries = []
    for row in rows:
        entries.append({
            'id': row.id,
            'patient_id': row.patient_id,
            'patient_name': row.patient_name,
            'patient_phone': row.patient_phone or '',
            'doctor_id': row.doctor_id,
            'doctor_name': row.doctor_name or 'Unknown',
            'visit_date': row.visit_date.isoformat(),
            'consultation_fee': float(row.consultation_fee or 0),
            'test_fee': float(row.test_fee or 0),
            'total_amount': float(row.total_amount or 0),
            'test_type': row.test_type or '',
            'notes': row.notes or '',
            'payment_status': row.payment_status,
            'branch_id': row.branch_id,
            'history_count': row.history_count,
        })
    
    summary = await get_daily_summary(date=date, branch_id=branch_id, db=db, current_user=current_user)
    
    return {
        "entries": entries,
        "summary": summary
    }

@router.put("/bulk")
async def bulk_update_entries(updates: BulkUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Bulk update multiple entries"""
    for update in updates.updates:
        if update.id is None:
            continue
        
        existing = db.execute("SELECT branch_id FROM daily_entries WHERE id = ?", (update.id,)).fetchone()
        if not existing or existing[0] != current_user.branch_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        fields = []
        params = []
        if update.patient_id is not None:
            fields.append("patient_id = ?")
            params.append(update.patient_id)
        if update.doctor_id is not None:
            fields.append("doctor_id = ?")
            params.append(update.doctor_id)
        if update.visit_date is not None:
            fields.append("visit_date = ?")
            params.append(update.visit_date)
        if update.consultation_fee is not None:
            fields.append("consultation_fee = ?")
            params.append(update.consultation_fee)
        if update.test_fee is not None:
            fields.append("test_fee = ?")
            params.append(update.test_fee)
        if update.test_type is not None:
            fields.append("test_type = ?")
            params.append(update.test_type)
        if update.notes is not None:
            fields.append("notes = ?")
            params.append(update.notes)
        if update.payment_status is not None:
            fields.append("payment_status = ?")
            params.append(update.payment_status)
        
        fields.append("total_amount = consultation_fee + test_fee")
        fields.append("updated_at = datetime('now')")
        params.append(update.id)
        
        if fields:
            query = f"UPDATE daily_entries SET {', '.join(fields)} WHERE id = ?"
            db.execute(query, params)
    
    db.commit()
    return {"message": f"Updated {len(updates.updates)} entries"}

@router.post("/invoice")
async def create_invoice_from_entries(
    entry_ids: List[int] = Body(embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create invoice from selected daily entries"""
    # Verify access
    placeholders = ','.join(['?' for _ in entry_ids])
    entries = db.execute(f"""
        SELECT * FROM daily_entries WHERE id IN ({placeholders}) AND branch_id = ?
    """, [*entry_ids, current_user.branch_id]).fetchall()
    
    if len(entries) != len(entry_ids):
        raise HTTPException(status_code=400, detail="Some entries not found or access denied")
    
    total = sum(float(e.total_amount) for e in entries)
    
    # Create invoice (integrate with payment_routes logic)
    # For now, mock response
    invoice_number = f"INV-DE-{datetime.now().strftime('%Y%m%d')}-{len(entry_ids):03d}"
    
    return {
        "invoice_number": invoice_number,
        "total_amount": total,
        "entries_count": len(entries),
        "message": "Invoice created successfully (payment_routes integration pending)"
    }
