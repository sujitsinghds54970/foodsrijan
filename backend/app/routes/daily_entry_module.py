"""
Daily Entry Module API Routes
Branch-scoped daily patient entries and expenses management
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
from sqlalchemy import text
from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
import os
import uuid
from pathlib import Path

from app.database import get_db
from app.models.daily_entry_module import DailyEntryModule, DailyExpense
from app.models.inventory import InventoryConsumptionHistory, InventoryItemV2 as InventoryItem
from app.models.branch_bank_details import BranchBankDetails
from app.models import User, Branch
from app.models.doctor import Doctor, DoctorBranch
from app.models.staff import StaffProfile
from app.schemas.daily_entry_module import (
    DailyEntryCreate, DailyEntryUpdate, DailyEntryResponse,
    DailyExpenseCreate, DailyExpenseUpdate, DailyExpenseResponse,
    DailyStatsResponse
)
from app.utils.auth_system import get_current_user
from app.utils.schema_compat import ensure_staff_daily_ops_column
from app.services.qrcode_service import generate_qr_code
from app.services.finance_integration import ensure_daily_entry_invoice, ensure_daily_entry_revenue
from app.services.patient_portal_notify import notify_on_daily_entry_completion
from fastapi.responses import FileResponse, StreamingResponse
import csv
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Upload directory for PDFs
UPLOAD_DIR = Path("uploads/daily_entry_reports")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _is_staff_role(role: str) -> bool:
    """Check if role is a staff type role (not admin or doctor)."""
    non_staff_roles = ['super_admin', 'branch_admin', 'branch_director', 'doctor']
    return role not in non_staff_roles


def _normalize_is_paid(entries: List[DailyEntryModule]) -> List[DailyEntryModule]:
    for entry in entries:
        entry.is_paid = bool(entry.is_paid)
    return entries


def _ensure_daily_entry_age_column(db: Session) -> None:
    try:
        cols = db.execute(text("PRAGMA table_info(daily_entries_module)")).fetchall()
        col_names = {row[1] for row in cols}
        if "age" not in col_names:
            db.execute(text("ALTER TABLE daily_entries_module ADD COLUMN age INTEGER"))
            db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[CREATE ENTRY] Failed ensuring age column: {exc}")


def _ensure_daily_entry_upi_id_column(db: Session) -> None:
    # Keep create flow resilient for DBs that predate upi_id column.
    try:
        cols = db.execute(text("PRAGMA table_info(daily_entries_module)")).fetchall()
        col_names = {row[1] for row in cols}
        if "upi_id" not in col_names:
            db.execute(text("ALTER TABLE daily_entries_module ADD COLUMN upi_id VARCHAR(100)"))
            db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[CREATE ENTRY] Failed ensuring upi_id column: {exc}")


def _ensure_daily_entry_consumed_items_column(db: Session) -> None:
    try:
        cols = db.execute(text("PRAGMA table_info(daily_entries_module)")).fetchall()
        col_names = {row[1] for row in cols}
        if "consumed_inventory_items" not in col_names:
            db.execute(text("ALTER TABLE daily_entries_module ADD COLUMN consumed_inventory_items JSON"))
            db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[CREATE ENTRY] Failed ensuring consumed_inventory_items column: {exc}")


def _ensure_daily_entry_schema(db: Session = Depends(get_db)) -> None:
    _ensure_daily_entry_age_column(db)
    _ensure_daily_entry_upi_id_column(db)
    _ensure_daily_entry_consumed_items_column(db)


def _get_doctor_white_label_for_branch(branch_id: int, db: Session) -> Dict[str, str]:
    assignment = (
        db.query(DoctorBranch)
        .filter(DoctorBranch.branch_id == branch_id, DoctorBranch.is_active.is_(True))
        .order_by(DoctorBranch.is_primary.desc(), DoctorBranch.assigned_date.desc())
        .first()
    )
    if not assignment:
        return {}

    doctor = db.query(Doctor).filter(Doctor.id == assignment.doctor_id, Doctor.is_active.is_(True)).first()
    if not doctor or not isinstance(doctor.report_preferences, dict):
        return {}

    white_label = doctor.report_preferences.get("white_label")
    if not isinstance(white_label, dict):
        return {}

    return {
        "clinic_name": (white_label.get("clinic_name") or "").strip(),
        "clinic_address": (white_label.get("clinic_address") or "").strip(),
        "logo_url": (white_label.get("logo_url") or "").strip(),
    }


def _resolve_branch_report_branding(branch_id: int, db: Session) -> Dict[str, str]:
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    branch_name = (branch.name or "").strip() if branch else ""
    branch_address = (branch.address or "").strip() if branch else ""
    branch_logo = (branch.director_photo_url or "").strip() if branch else ""

    doctor_branding = _get_doctor_white_label_for_branch(branch_id, db)

    clinic_name = doctor_branding.get("clinic_name") or branch_name or "Vaidya Vihar Diagnostic"
    clinic_address = doctor_branding.get("clinic_address") or branch_address
    logo_url = doctor_branding.get("logo_url") or branch_logo

    return {
        "clinic_name": clinic_name,
        "clinic_address": clinic_address,
        "logo_url": logo_url,
    }


def _test_requires_xray_consumption(test_name: Optional[str]) -> bool:
    if not test_name:
        return False
    normalized = test_name.lower()
    keywords = ["x-ray", "xray", "x ray", "radiograph"]
    return any(word in normalized for word in keywords)


def _append_consumed_item(entry: DailyEntryModule, payload: Dict[str, Any]) -> None:
    existing = entry.consumed_inventory_items or []
    if not isinstance(existing, list):
        existing = []
    existing.append(payload)
    entry.consumed_inventory_items = existing


def _consume_xray_inventory_if_needed(db: Session, entry: DailyEntryModule, current_user: User) -> None:
    if not _test_requires_xray_consumption(entry.test_name):
        return

    existing_consumption = (
        db.query(InventoryConsumptionHistory)
        .filter(
            InventoryConsumptionHistory.daily_entry_id == entry.id,
            InventoryConsumptionHistory.notes.ilike("%auto_xray%"),
        )
        .first()
    )
    if existing_consumption:
        return

    film_item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.branch_id == entry.branch_id,
            InventoryItem.department == "X-Ray",
            InventoryItem.is_active == True,
            InventoryItem.item_name.ilike("%film%"),
        )
        .order_by(InventoryItem.expiry_date.asc().nullsfirst(), InventoryItem.id.asc())
        .first()
    )

    if not film_item:
        return

    current_qty = float(film_item.current_qty)
    if current_qty < 1:
        return

    film_item.current_qty = current_qty - 1

    db.add(
        InventoryConsumptionHistory(
            branch_id=entry.branch_id,
            inventory_item_id=film_item.id,
            daily_entry_id=entry.id,
            patient_identifier=entry.auto_patient_id,
            test_name=entry.test_name,
            quantity=1,
            notes="auto_xray_consumption",
            created_by=current_user.id,
        )
    )

    _append_consumed_item(
        entry,
        {
            "inventory_item_id": film_item.id,
            "item_name": film_item.item_name,
            "quantity": 1,
            "source": "auto_xray_consumption",
            "at": datetime.now().isoformat(),
        },
    )


router = APIRouter(dependencies=[Depends(_ensure_daily_entry_schema)])


def generate_patient_id(db: Session, branch_id: int, attempt_offset: int = 0) -> str:
    """
    Generate auto_patient_id in format PAT-YYYYMMDD-XXX
    Uses MAX query to avoid race conditions and duplicate IDs
    """
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    prefix = f"PAT-{date_str}"
    
    # Query for the highest sequence number for today's date.
    # auto_patient_id has a global unique constraint, so sequence allocation
    # must also be global (not branch-scoped) to avoid collisions.
    result = db.query(DailyEntryModule.auto_patient_id).filter(
        DailyEntryModule.auto_patient_id.like(f"{prefix}-%")
    ).order_by(DailyEntryModule.auto_patient_id.desc()).first()
    
    if result and result[0]:
        # Extract the sequence number from the last ID (e.g., "PAT-20260706-005" -> 5)
        last_id = result[0]
        try:
            last_sequence = int(last_id.split('-')[-1])
            sequence = str(last_sequence + 1 + attempt_offset).zfill(3)
        except (ValueError, IndexError):
            # Fallback if parsing fails
            sequence = "001"
    else:
        # No entries for today yet
        sequence = str(1 + attempt_offset).zfill(3)
    
    return f"{prefix}-{sequence}"


def calculate_total_amount(fee_amount: Decimal, tax_percent: float) -> Decimal:
    """Calculate total amount including tax"""
    tax_amount = fee_amount * Decimal(tax_percent / 100)
    return fee_amount + tax_amount


def parse_entry_datetime(value: Optional[str]) -> datetime:
    """Parse frontend-provided datetime value with safe fallbacks."""
    if not value:
        return datetime.now()

    raw = value.strip()
    if not raw:
        return datetime.now()

    try:
        normalized = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    formats = [
        "%m/%d/%Y, %I:%M:%S %p",
        "%m/%d/%Y, %I:%M %p",
        "%d/%m/%Y, %I:%M:%S %p",
        "%d/%m/%Y, %I:%M %p",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    return datetime.now()


def get_user_branch_id(current_user: User) -> int:
    """Extract branch_id from current user, raise error if not available"""
    if current_user.role == 'super_admin':
        # Super admin can view all, but for creation they need to specify
        return None
    
    if not current_user.branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must be assigned to a branch"
        )
    return current_user.branch_id


def require_daily_ops_actor(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Authorize Daily Operations using role permissions and per-staff toggle."""
    if current_user.role in ['super_admin', 'branch_admin', 'branch_director']:
        return current_user

    if not _is_staff_role(current_user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff users can access this endpoint")

    if not current_user.branch_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch access required")

    ensure_staff_daily_ops_column(db)
    staff_profile = (
        db.query(StaffProfile)
        .filter(StaffProfile.user_id == current_user.id, StaffProfile.branch_id == current_user.branch_id)
        .first()
    )
    if not staff_profile or not staff_profile.can_access_daily_ops:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Daily Operations access disabled by director",
        )

    return current_user


# ==================== DAILY ENTRY ENDPOINTS ====================

# Specific routes MUST come before parameterized routes
@router.get("/api/daily-entries/grid", response_model=List[DailyEntryResponse])
async def get_daily_entries_grid(
    date: Optional[date] = Query(None, description="Filter by specific date (default: today)"),
    branch_id: Optional[int] = Query(None, description="Filter by branch ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """
    Get daily entries for grid display - filtered by date and branch.
    Used by the Daily Entry Module frontend grid component.
    """
    target_date = date or datetime.now().date()
    
    query = db.query(DailyEntryModule)
    
    # Branch scoping
    if current_user.role != 'super_admin':
        # Branch admin can only see their own branch
        user_branch_id = get_user_branch_id(current_user)
        query = query.filter(DailyEntryModule.branch_id == user_branch_id)
    elif branch_id:
        # Super admin can filter by specific branch
        query = query.filter(DailyEntryModule.branch_id == branch_id)
    
    # Filter by date
    query = query.filter(func.date(DailyEntryModule.auto_entry_datetime) == target_date)
    
    # Order by most recent first
    entries = query.order_by(DailyEntryModule.auto_entry_datetime.desc()).all()
    return _normalize_is_paid(entries)


@router.get("/api/daily-entries", response_model=List[DailyEntryResponse])
async def get_daily_entries(
    patient_name: Optional[str] = Query(None),
    referred_doctor: Optional[str] = Query(None),
    test_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """
    Get all daily entries for the authenticated user's branch with filters.
    Branch Admin sees only their branch data. Super Admin sees all.
    """
    query = db.query(DailyEntryModule)
    
    # Branch scoping
    if current_user.role != 'super_admin':
        branch_id = get_user_branch_id(current_user)
        query = query.filter(DailyEntryModule.branch_id == branch_id)
    
    # Apply filters
    if patient_name:
        query = query.filter(DailyEntryModule.patient_name.ilike(f"%{patient_name}%"))
    
    if referred_doctor:
        query = query.filter(DailyEntryModule.referred_doctor.ilike(f"%{referred_doctor}%"))
    
    if test_name:
        query = query.filter(DailyEntryModule.test_name.ilike(f"%{test_name}%"))
    
    if start_date:
        query = query.filter(func.date(DailyEntryModule.auto_entry_datetime) >= start_date)
    
    if end_date:
        query = query.filter(func.date(DailyEntryModule.auto_entry_datetime) <= end_date)
    
    entries = query.order_by(DailyEntryModule.auto_entry_datetime.desc()).all()
    return _normalize_is_paid(entries)


@router.post("/api/daily-entries", response_model=DailyEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_daily_entry(
    entry: DailyEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Create a new daily entry for the authenticated user's branch"""
    from sqlalchemy.exc import IntegrityError
    
    # Get branch_id - handle super_admin case
    if current_user.role == 'super_admin':
        # For super_admin, use branch_id from request or default to 1
        branch_id = getattr(entry, 'branch_id', None) or current_user.branch_id or 1
    else:
        branch_id = get_user_branch_id(current_user)
    
    print(f"[CREATE ENTRY] User: {current_user.username}, Role: {current_user.role}, Branch: {branch_id}")
    print(f"[CREATE ENTRY] Data: {entry.dict()}")
    
    # Retry logic for handling race conditions
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Generate auto_patient_id inside transaction
            auto_patient_id = generate_patient_id(db, branch_id, attempt)
            print(f"[CREATE ENTRY] Attempt {attempt + 1}: Generated Patient ID: {auto_patient_id}")
            
            # Calculate total amount
            total_amount = calculate_total_amount(entry.fee_amount, entry.tax_percent)
            print(f"[CREATE ENTRY] Calculated Total: {total_amount}")
            
            # Determine status based on report_pdf_url
            status_value = "Pending"
            entry_payload = entry.dict(exclude_unset=True)
            resolved_is_paid = bool(entry_payload.get('is_paid', False))

            branch_upi = (
                db.query(BranchBankDetails.upi_id)
                .filter(
                    BranchBankDetails.branch_id == branch_id,
                    BranchBankDetails.is_active == True,
                )
                .scalar()
            )
            
            db_entry = DailyEntryModule(
                branch_id=branch_id,
                auto_patient_id=auto_patient_id,
                auto_entry_datetime=parse_entry_datetime(entry.auto_entry_datetime),
                patient_name=entry.patient_name,
                age=entry.age,
                mobile=entry.mobile,
                address=entry.address,
                referred_doctor=entry.referred_doctor,
                test_name=entry.test_name,
                fee_amount=entry.fee_amount,
                tax_percent=entry.tax_percent,
                total_amount=total_amount,
                payment_method=entry.payment_method,
                upi_id=branch_upi,
                is_paid=resolved_is_paid,
                remarks=entry.remarks,
                status=status_value,
                created_by=current_user.id
            )
            
            db.add(db_entry)
            db.commit()
            db.refresh(db_entry)

            ensure_daily_entry_invoice(db, entry=db_entry, created_by=current_user.id)
            ensure_daily_entry_revenue(db, entry=db_entry, created_by=current_user.id)
            db.commit()
            
            print(f"[CREATE ENTRY] Success! Entry ID: {db_entry.id}, Patient ID: {db_entry.auto_patient_id}")
            return db_entry
            
        except IntegrityError as e:
            db.rollback()
            print(f"[CREATE ENTRY] IntegrityError on attempt {attempt + 1}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if attempt < max_retries - 1:
                # Retry with a new ID
                print(f"[CREATE ENTRY] Retrying with new ID...")
                continue
            else:
                # Final fallback path to avoid production 500 on repeated collisions.
                # Keep a deterministic prefix while adding a short uniqueness suffix.
                try:
                    fallback_auto_patient_id = f"PAT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                    print(f"[CREATE ENTRY] Using fallback patient ID: {fallback_auto_patient_id}")

                    total_amount = calculate_total_amount(entry.fee_amount, entry.tax_percent)
                    status_value = "Pending"
                    branch_upi = (
                        db.query(BranchBankDetails.upi_id)
                        .filter(
                            BranchBankDetails.branch_id == branch_id,
                            BranchBankDetails.is_active == True,
                        )
                        .scalar()
                    )

                    db_entry = DailyEntryModule(
                        branch_id=branch_id,
                        auto_patient_id=fallback_auto_patient_id,
                        auto_entry_datetime=parse_entry_datetime(entry.auto_entry_datetime),
                        patient_name=entry.patient_name,
                        age=entry.age,
                        mobile=entry.mobile,
                        address=entry.address,
                        referred_doctor=entry.referred_doctor,
                        test_name=entry.test_name,
                        fee_amount=entry.fee_amount,
                        tax_percent=entry.tax_percent,
                        total_amount=total_amount,
                        payment_method=entry.payment_method,
                        upi_id=branch_upi,
                        is_paid=resolved_is_paid,
                        remarks=entry.remarks,
                        status=status_value,
                        created_by=current_user.id,
                    )

                    db.add(db_entry)
                    db.commit()
                    db.refresh(db_entry)
                    print(f"[CREATE ENTRY] Fallback success! Entry ID: {db_entry.id}, Patient ID: {db_entry.auto_patient_id}")
                    return db_entry
                except Exception as fallback_error:
                    print(f"[CREATE ENTRY ERROR] Fallback failed: {fallback_error}")
                    traceback.print_exc()
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to generate unique patient ID after multiple attempts"
                    )
                
        except Exception as e:
            print(f"[CREATE ENTRY ERROR] {type(e).__name__}: {str(e)}")
            print(e)
            import traceback
            traceback.print_exc()
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create entry: {str(e)}"
            )
    
    # Should never reach here, but just in case
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected error in entry creation"
    )


@router.put("/api/daily-entries/{entry_id}", response_model=DailyEntryResponse)
async def update_daily_entry(
    entry_id: int,
    entry: DailyEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Update a daily entry (branch-scoped)"""
    db_entry = db.query(DailyEntryModule).filter(DailyEntryModule.id == entry_id).first()
    previous_status = db_entry.status if db_entry else None
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # Branch access check
    if current_user.role != 'super_admin' and db_entry.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")
    
    # Update fields
    update_data = entry.dict(exclude_unset=True)
    
    # Recalculate total if fee or tax changed
    if 'fee_amount' in update_data or 'tax_percent' in update_data:
        fee = update_data.get('fee_amount', db_entry.fee_amount)
        tax = update_data.get('tax_percent', db_entry.tax_percent)
        update_data['total_amount'] = calculate_total_amount(fee, tax)

    if 'auto_entry_datetime' in update_data:
        update_data['auto_entry_datetime'] = parse_entry_datetime(update_data.get('auto_entry_datetime'))

    if 'payment_method' in update_data:
        payment_method = update_data.get('payment_method')
        if payment_method in ('Cash', 'UPI'):
            update_data['is_paid'] = True
        elif payment_method == 'Hold':
            update_data['is_paid'] = False
    
    # Update status based on report_pdf_url
    if 'report_pdf_url' in update_data:
        update_data['status'] = "Completed" if update_data['report_pdf_url'] else "Pending"
    
    for key, value in update_data.items():
        setattr(db_entry, key, value)

    if bool(db_entry.is_paid):
        ensure_daily_entry_invoice(db, entry=db_entry, created_by=current_user.id)
        ensure_daily_entry_revenue(db, entry=db_entry, created_by=current_user.id)

    if previous_status != "Completed" and db_entry.status == "Completed":
        notify_on_daily_entry_completion(db, db_entry)
    
    db.commit()
    db.refresh(db_entry)
    
    return db_entry


@router.delete("/api/daily-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_daily_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Delete a daily entry (branch-scoped)"""
    db_entry = db.query(DailyEntryModule).filter(DailyEntryModule.id == entry_id).first()
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # Branch access check
    if current_user.role != 'super_admin' and db_entry.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")
    
    db.delete(db_entry)
    db.commit()
    
    return None


@router.post("/api/daily-entries/{entry_id}/upload-report")
async def upload_report_pdf(
    entry_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Upload PDF report for a daily entry"""
    db_entry = db.query(DailyEntryModule).filter(DailyEntryModule.id == entry_id).first()
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # Branch access check
    if current_user.role != 'super_admin' and db_entry.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{db_entry.auto_patient_id}_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Update entry with file URL
    previous_status = db_entry.status
    db_entry.report_pdf_url = f"/uploads/daily_entry_reports/{unique_filename}"
    db_entry.status = "Completed"
    _consume_xray_inventory_if_needed(db, db_entry, current_user)
    if previous_status != "Completed":
        notify_on_daily_entry_completion(db, db_entry)
    db.commit()
    
    return {
        "message": "Report uploaded successfully",
        "file_url": db_entry.report_pdf_url,
        "status": db_entry.status
    }


@router.post("/api/daily-entries/complete")
async def complete_daily_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor),
):
    """
    Mark a daily entry as completed and auto-consume X-Ray film when test name matches.
    """
    db_entry = db.query(DailyEntryModule).filter(DailyEntryModule.id == entry_id).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    if current_user.role != 'super_admin' and db_entry.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")

    previous_status = db_entry.status
    db_entry.status = "Completed"
    _consume_xray_inventory_if_needed(db, db_entry, current_user)
    if previous_status != "Completed":
        notify_on_daily_entry_completion(db, db_entry)
    db.commit()
    db.refresh(db_entry)

    return {
        "message": "Daily entry marked as completed",
        "entry_id": db_entry.id,
        "status": db_entry.status,
        "consumed_inventory_items": db_entry.consumed_inventory_items or [],
    }


@router.get("/api/daily-entries/{entry_id}/qr-code")
async def get_entry_qr_code(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Generate QR code for a daily entry's patient ID"""
    db_entry = db.query(DailyEntryModule).filter(DailyEntryModule.id == entry_id).first()
    
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # Branch access check
    if current_user.role != 'super_admin' and db_entry.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this entry")
    
    # Generate QR code
    qr_data = db_entry.auto_patient_id
    qr_image = generate_qr_code(qr_data)
    
    return {
        "patient_id": db_entry.auto_patient_id,
        "qr_code": qr_image
    }


# ==================== DAILY EXPENSE ENDPOINTS ====================

@router.get("/api/daily-expenses", response_model=List[DailyExpenseResponse])
async def get_daily_expenses(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Get all daily expenses for the authenticated user's branch"""
    query = db.query(DailyExpense)
    
    # Branch scoping
    if current_user.role != 'super_admin':
        branch_id = get_user_branch_id(current_user)
        query = query.filter(DailyExpense.branch_id == branch_id)
    
    # Apply filters
    if start_date:
        query = query.filter(func.date(DailyExpense.entry_date) >= start_date)
    
    if end_date:
        query = query.filter(func.date(DailyExpense.entry_date) <= end_date)
    
    expenses = query.order_by(DailyExpense.entry_date.desc()).all()
    return expenses


@router.post("/api/daily-expenses", response_model=DailyExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_daily_expense(
    expense: DailyExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Create a new daily expense for the authenticated user's branch"""
    if _is_staff_role(current_user.role):
        raise HTTPException(status_code=403, detail="Staff cannot create expenses")

    branch_id = get_user_branch_id(current_user)
    
    db_expense = DailyExpense(
        branch_id=branch_id,
        entry_date=expense.entry_date or datetime.now(),
        expense_item=expense.expense_item,
        cost=expense.cost,
        description=expense.description,
        created_by=current_user.id
    )
    
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    
    return db_expense


@router.put("/api/daily-expenses/{expense_id}", response_model=DailyExpenseResponse)
async def update_daily_expense(
    expense_id: int,
    expense: DailyExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Update a daily expense (branch-scoped)"""
    if _is_staff_role(current_user.role):
        raise HTTPException(status_code=403, detail="Staff cannot edit expenses")

    db_expense = db.query(DailyExpense).filter(DailyExpense.id == expense_id).first()
    
    if not db_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Branch access check
    if current_user.role != 'super_admin' and db_expense.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this expense")
    
    update_data = expense.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_expense, key, value)
    
    db.commit()
    db.refresh(db_expense)
    
    return db_expense


@router.delete("/api/daily-expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_daily_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Delete a daily expense (branch-scoped)"""
    if _is_staff_role(current_user.role):
        raise HTTPException(status_code=403, detail="Staff cannot delete expenses")

    db_expense = db.query(DailyExpense).filter(DailyExpense.id == expense_id).first()
    
    if not db_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Branch access check
    if current_user.role != 'super_admin' and db_expense.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this expense")
    
    db.delete(db_expense)
    db.commit()
    
    return None


# ==================== STATISTICS ENDPOINT ====================

@router.get("/api/daily-stats", response_model=DailyStatsResponse)
async def get_daily_stats(
    date_filter: Optional[date] = Query(None, description="Date for stats (default: today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Get daily statistics for the authenticated user's branch"""
    branch_id = get_user_branch_id(current_user)
    target_date = date_filter or datetime.now().date()
    
    # Get total revenue for the day
    revenue_query = db.query(func.sum(DailyEntryModule.total_amount)).filter(
        and_(
            DailyEntryModule.branch_id == branch_id,
            func.date(DailyEntryModule.auto_entry_datetime) == target_date
        )
    )
    total_revenue = revenue_query.scalar() or Decimal(0)
    
    # Get total expenses for the day
    expense_query = db.query(func.sum(DailyExpense.cost)).filter(
        and_(
            DailyExpense.branch_id == branch_id,
            func.date(DailyExpense.entry_date) == target_date
        )
    )
    total_expense = expense_query.scalar() or Decimal(0)
    
    # Calculate net profit
    net_profit = total_revenue - total_expense
    
    # Get patient count for the day
    patient_count = db.query(DailyEntryModule).filter(
        and_(
            DailyEntryModule.branch_id == branch_id,
            func.date(DailyEntryModule.auto_entry_datetime) == target_date
        )
    ).count()
    
    return DailyStatsResponse(
        total_revenue=total_revenue,
        total_expense=total_expense,
        net_profit=net_profit,
        patient_count=patient_count,
        date=target_date.isoformat()
    )


# ==================== DOCTOR SEARCH ENDPOINT ====================

@router.get("/api/doctors/search")
async def search_doctors(
    q: str = Query(..., min_length=2, description="Search query for doctor name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search for doctors by name (autocomplete endpoint).
    Returns distinct doctor names matching the search query.
    """
    # Get branch_id for scoping
    branch_id = None
    if current_user.role != 'super_admin':
        branch_id = get_user_branch_id(current_user)
    
    query = db.query(DailyEntryModule.referred_doctor).filter(
        and_(
            DailyEntryModule.referred_doctor.ilike(f"%{q}%"),
            DailyEntryModule.referred_doctor.isnot(None),
            DailyEntryModule.referred_doctor != ''
        )
    )
    
    # Apply branch scoping if not super admin
    if branch_id:
        query = query.filter(DailyEntryModule.branch_id == branch_id)
    
    doctors = query.distinct().limit(10).all()
    
    return [{"name": d[0]} for d in doctors if d[0]]


# ==================== EXPORT ENDPOINTS ====================

@router.get("/api/daily-entries/export")
async def export_daily_entries(
    type: str = Query(..., regex="^(csv|pdf)$"),
    period: str = Query(..., regex="^(daily|monthly|yearly)$"),
    date_filter: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_daily_ops_actor)
):
    """Export daily entries as CSV or PDF"""
    if _is_staff_role(current_user.role):
        raise HTTPException(status_code=403, detail="Staff cannot export daily operations reports")

    branch_id = get_user_branch_id(current_user)
    target_date = date_filter or datetime.now().date()
    
    # Build query based on period
    query = db.query(DailyEntryModule).filter(DailyEntryModule.branch_id == branch_id)
    
    if period == "daily":
        query = query.filter(func.date(DailyEntryModule.auto_entry_datetime) == target_date)
        filename_suffix = target_date.strftime("%Y%m%d")
    elif period == "monthly":
        query = query.filter(
            and_(
                extract('year', DailyEntryModule.auto_entry_datetime) == target_date.year,
                extract('month', DailyEntryModule.auto_entry_datetime) == target_date.month
            )
        )
        filename_suffix = target_date.strftime("%Y%m")
    else:  # yearly
        query = query.filter(extract('year', DailyEntryModule.auto_entry_datetime) == target_date.year)
        filename_suffix = target_date.strftime("%Y")
    
    entries = query.order_by(DailyEntryModule.auto_entry_datetime.desc()).all()
    
    if type == "csv":
        return export_to_csv(entries, filename_suffix)
    else:
        return export_to_pdf(entries, filename_suffix, period, branch_id, db)


def export_to_csv(entries: List[DailyEntryModule], filename_suffix: str):
    """Export entries to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Patient ID', 'Date', 'Patient Name', 'Mobile', 'Address',
        'Referred Doctor', 'Test Name', 'Fee Amount', 'Tax %', 
        'Total Amount', 'Payment Method', 'Status', 'Remarks'
    ])
    
    # Write data
    for entry in entries:
        writer.writerow([
            entry.auto_patient_id,
            entry.auto_entry_datetime.strftime("%Y-%m-%d %H:%M"),
            entry.patient_name,
            entry.mobile,
            entry.address,
            entry.referred_doctor or '',
            entry.test_name,
            float(entry.fee_amount),
            entry.tax_percent,
            float(entry.total_amount),
            entry.payment_method,
            entry.status,
            entry.remarks or ''
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=daily_entries_{filename_suffix}.csv"
        }
    )


def export_to_pdf(entries: List[DailyEntryModule], filename_suffix: str, period: str, branch_id: int, db: Session):
    """Export entries to PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    branding = _resolve_branch_report_branding(branch_id, db)
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    clinic_name_text = branding.get('clinic_name') or 'Vaidya Vihar Diagnostic'
    clinic_address_text = branding.get('clinic_address') or ''
    title_text = f"{clinic_name_text}<br/>Daily Entries Report - {period.capitalize()}"
    elements.append(Paragraph(title_text, title_style))

    if clinic_address_text:
        subtitle_style = ParagraphStyle(
            'ClinicSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4a5568'),
            alignment=TA_CENTER,
            spaceAfter=12,
        )
        elements.append(Paragraph(clinic_address_text, subtitle_style))

    elements.append(Spacer(1, 0.2 * inch))
    
    # Summary statistics
    total_revenue = sum(float(e.total_amount) for e in entries)
    patient_count = len(entries)
    
    summary_data = [
        ['Clinic:', clinic_name_text],
        ['Total Patients:', str(patient_count)],
        ['Total Revenue:', f'₹{total_revenue:,.2f}'],
        ['Period:', filename_suffix]
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Entries table
    table_data = [['Patient ID', 'Name', 'Test', 'Amount', 'Status']]
    
    for entry in entries[:50]:  # Limit to 50 entries per page
        table_data.append([
            entry.auto_patient_id,
            entry.patient_name[:20],
            entry.test_name[:25],
            f'₹{float(entry.total_amount):,.2f}',
            entry.status
        ])
    
    entries_table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 2*inch, 1*inch, 1*inch])
    entries_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(entries_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=daily_entries_{filename_suffix}.pdf"
        }
    )
