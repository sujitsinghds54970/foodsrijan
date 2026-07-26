"""
Branch LIS routes scoped to the authenticated user's branch.
"""

from __future__ import annotations

import base64
import io
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, Patient, User
from app.models.branch_lis import (
    InstrumentCalibration,
    LISReportArchive,
    OrderQueue,
    ProficiencyTestRun,
    QCResult,
    Sample,
    TestCatalog,
    TestPanel,
    Worklist,
)
from app.models.daily_entry_module import DailyEntryModule
from app.models.inventory import InventoryConsumptionHistory, InventoryItemV2
from app.models.patient import PatientProfile
from app.services.email_service import get_email_service
from app.services.sms_service import get_sms_service
from app.services.whatsapp_service import get_whatsapp_service
from app.utils.auth_system import get_current_user

router = APIRouter(prefix="/api/lis", tags=["Branch LIS"])


ORDER_PRIORITIES = {"Routine", "STAT", "Emergency"}
SAMPLE_STATUSES = {"Registered", "In Processing", "QC Passed", "Reported", "Delayed", "Rejected"}


class TestCatalogInput(BaseModel):
    test_code: str
    test_name: str
    department: str = "General"
    sample_type: str = "Blood"
    turnaround_minutes: int = Field(default=1440, ge=1, le=10080)


class PanelTestItem(BaseModel):
    test_code: str
    test_name: str
    department: str = "General"
    sample_type: str = "Blood"
    turnaround_minutes: int = Field(default=1440, ge=1, le=10080)


class TestPanelCreateRequest(BaseModel):
    panel_name: str
    description: Optional[str] = None
    tests: List[PanelTestItem]


class OrderCreateRequest(BaseModel):
    daily_entry_id: Optional[int] = None
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    patient_code: Optional[str] = None
    doctor_name: Optional[str] = None
    priority: str = "Routine"
    panel_id: Optional[int] = None
    tests: List[PanelTestItem] = Field(default_factory=list)
    notes: Optional[str] = None


class BarcodeResponse(BaseModel):
    sample_id: int
    sample_code: str
    barcode_value: str
    barcode_image_base64: str


class LISOrderSummary(BaseModel):
    id: int
    order_number: str
    source: str
    patient_name: str
    patient_code: Optional[str] = None
    doctor_name: Optional[str] = None
    priority: str
    status: str
    expected_tat_minutes: int
    due_at: Optional[str] = None
    tests: List[Dict[str, object]]
    created_at: str


class LISHealthScoreResponse(BaseModel):
    score: int
    status: str
    average_tat_minutes: float
    qc_failure_rate: float
    sample_rejection_rate: float
    pending_tests: int
    branch_name: Optional[str] = None
    last_updated: str


class LISStatsResponse(BaseModel):
    todays_test_volume: int
    average_tat_minutes: float
    tat_breakdown: Dict[str, float]
    pending_tests_count: int
    pending_by_department: Dict[str, int]
    sample_rejection_rate: float
    qc_status: str
    delayed_samples: int
    last_updated: str


class UpdateSampleStatusRequest(BaseModel):
    status: str
    rejection_reason: Optional[str] = None


class UpdateSampleRouteRequest(BaseModel):
    department: str
    analyzer_name: Optional[str] = None
    storage_location: Optional[str] = None


class CreateWorklistRequest(BaseModel):
    department: str
    analyzer_name: Optional[str] = None
    sample_ids: List[int]


class QCResultUpsertRequest(BaseModel):
    sample_id: Optional[int] = None
    analyzer_name: str
    test_code: str
    qc_status: str = "Passed"
    failure_reason: Optional[str] = None
    hil_flag: bool = False
    delta_check_flag: bool = False
    critical_value_flag: bool = False


class CalibrationUpsertRequest(BaseModel):
    analyzer_name: str
    calibration_status: str = "Due"
    next_due_at: Optional[str] = None
    maintenance_notes: Optional[str] = None


class ProficiencyRunRequest(BaseModel):
    program_name: str
    cycle_name: str
    department: str
    participation_status: str = "Planned"
    score: Optional[int] = None
    notes: Optional[str] = None


class ReportGenerateRequest(BaseModel):
    order_id: int
    sample_id: Optional[int] = None
    template_name: str = "Default LIS Template"
    signed_by: Optional[str] = None
    channels: List[str] = Field(default_factory=lambda: ["patient_portal"])
    legal_note: Optional[str] = None
    summary: Optional[str] = None


class BulkReportGenerateRequest(BaseModel):
    order_ids: List[int]
    template_name: str = "Default LIS Template"
    signed_by: Optional[str] = None
    channels: List[str] = Field(default_factory=lambda: ["patient_portal"])

def _require_branch_id(current_user: User) -> int:
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="User must be assigned to a branch")
    return int(current_user.branch_id)


def _normalize_priority(priority: str) -> str:
    value = (priority or "Routine").strip().upper()
    if value in {"STAT", "URGENT"}:
        return "STAT"
    if value in {"EMERGENCY", "CRITICAL"}:
        return "Emergency"
    return "Routine"


def _split_tests_from_daily_entry(test_name: str) -> List[dict]:
    tests = [part.strip() for part in (test_name or "").split(",") if part.strip()]
    if not tests:
        return [{"test_code": "GEN-TEST", "test_name": "General Test", "department": "General", "sample_type": "Blood", "turnaround_minutes": 1440}]
    return [
        {
            "test_code": f"AUTO-{idx + 1}",
            "test_name": name,
            "department": "General",
            "sample_type": "Blood",
            "turnaround_minutes": 1440,
        }
        for idx, name in enumerate(tests)
    ]


def _new_order_number(branch_id: int) -> str:
    return f"LIS-{branch_id}-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def _new_sample_code(branch_id: int) -> str:
    return f"SMP-{branch_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"


def _status_from_score(score: int) -> str:
    if score > 80:
        return "Green"
    if score >= 50:
        return "Yellow"
    return "Red"


def _sample_is_pending(sample: Sample) -> bool:
    return sample.status not in {"Reported", "Rejected"}


def _order_summary(order: OrderQueue) -> LISOrderSummary:
    return LISOrderSummary(
        id=order.id,
        order_number=order.order_number,
        source=order.source,
        patient_name=order.patient_name,
        patient_code=order.patient_code,
        doctor_name=order.doctor_name,
        priority=order.priority,
        status=order.status,
        expected_tat_minutes=order.expected_tat_minutes,
        due_at=order.due_at.isoformat() if order.due_at else None,
        tests=order.tests_json or [],
        created_at=order.created_at.isoformat(),
    )


def _calculate_tat_minutes(samples: List[Sample]) -> Dict[str, float]:
    durations: List[float] = []
    for sample in samples:
        if sample.started_at and sample.completed_at:
            durations.append((sample.completed_at - sample.started_at).total_seconds() / 60.0)
        elif sample.registered_at and sample.reported_at:
            durations.append((sample.reported_at - sample.registered_at).total_seconds() / 60.0)
    average = sum(durations) / len(durations) if durations else 0.0
    return {"average": round(average, 2)}


def _qc_status_label(failure_rate: float) -> str:
    if failure_rate <= 2:
        return "Good"
    if failure_rate <= 7:
        return "Watch"
    return "Critical"


def _westgard_flags(rows: List[QCResult]) -> List[dict]:
    by_test: Dict[str, List[QCResult]] = {}
    for row in rows:
        by_test.setdefault(row.test_code or "UNKNOWN", []).append(row)

    findings: List[dict] = []
    for test_code, test_rows in by_test.items():
        ordered = sorted(test_rows, key=lambda item: item.created_at or datetime.utcnow())
        if len(ordered) >= 2 and all(item.qc_status.lower() == "failed" for item in ordered[-2:]):
            findings.append(
                {
                    "test_code": test_code,
                    "rule": "2-2s",
                    "level": "Out of Control",
                    "message": "Two consecutive failed controls detected",
                    "at": ordered[-1].created_at.isoformat() if ordered[-1].created_at else datetime.utcnow().isoformat(),
                }
            )
        if len(ordered) >= 4:
            recent = ordered[-4:]
            fail_count = sum(1 for row in recent if row.qc_status.lower() == "failed")
            if fail_count >= 3:
                findings.append(
                    {
                        "test_code": test_code,
                        "rule": "4-1s",
                        "level": "Warning",
                        "message": "Frequent QC drift in last four runs",
                        "at": recent[-1].created_at.isoformat() if recent[-1].created_at else datetime.utcnow().isoformat(),
                    }
                )
    return findings


def _report_number(branch_id: int) -> str:
    return f"LISR-{branch_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"


def _safe_json_text(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


async def _deliver_report_channels(
    *,
    patient_name: str,
    mobile: Optional[str],
    email: Optional[str],
    report_number: str,
    channels: List[str],
) -> List[dict]:
    sent_channels: List[dict] = []
    sms_service = get_sms_service()
    email_service = get_email_service()
    whatsapp_service = get_whatsapp_service()
    for channel in channels:
        normalized = channel.strip().lower()
        if normalized == "sms":
            if not mobile:
                sent_channels.append({"channel": "sms", "status": "skipped", "reason": "No mobile"})
                continue
            response = await sms_service.send_report_ready_sms(
                mobile,
                patient_name,
                "LIS",
                report_number,
                datetime.utcnow().strftime("%Y-%m-%d"),
            )
            sent_channels.append({"channel": "sms", "status": "sent" if response.success else "failed"})
        elif normalized == "whatsapp":
            if not mobile:
                sent_channels.append({"channel": "whatsapp", "status": "skipped", "reason": "No mobile"})
                continue
            response = await whatsapp_service.send_report_ready_message(
                mobile,
                patient_name,
                "LIS Report",
                report_number,
                f"/api/lis/reports/archive?report_number={report_number}",
            )
            sent_channels.append({"channel": "whatsapp", "status": "sent" if response.success else "failed"})
        elif normalized == "email":
            if not email:
                sent_channels.append({"channel": "email", "status": "skipped", "reason": "No email"})
                continue
            sent = email_service.send_report_ready(email, patient_name, report_number)
            sent_channels.append({"channel": "email", "status": "sent" if sent else "failed"})
        elif normalized == "patient_portal":
            sent_channels.append({"channel": "patient_portal", "status": "sent"})
    return sent_channels


def _ensure_patient_in_branch(db: Session, branch_id: int, patient_id: Optional[int]) -> Optional[Patient]:
    if not patient_id:
        return None
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.branch_id == branch_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found in branch")
    return patient


def _resolve_tests_for_order(db: Session, branch_id: int, payload: OrderCreateRequest) -> List[dict]:
    if payload.panel_id:
        panel = (
            db.query(TestPanel)
            .filter(TestPanel.id == payload.panel_id, TestPanel.branch_id == branch_id, TestPanel.is_active.is_(True))
            .first()
        )
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found for branch")
        return list(panel.tests_json or [])
    if payload.tests:
        return [item.dict() for item in payload.tests]
    if payload.daily_entry_id:
        entry = (
            db.query(DailyEntryModule)
            .filter(DailyEntryModule.id == payload.daily_entry_id, DailyEntryModule.branch_id == branch_id)
            .first()
        )
        if not entry:
            raise HTTPException(status_code=404, detail="Daily entry not found for branch")
        return _split_tests_from_daily_entry(entry.test_name)
    raise HTTPException(status_code=400, detail="Provide tests, panel_id, or daily_entry_id")


@router.post("/catalog")
def create_test_catalog_item(
    payload: TestCatalogInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    existing = (
        db.query(TestCatalog)
        .filter(TestCatalog.branch_id == branch_id, TestCatalog.test_code == payload.test_code.strip())
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Test code already exists in branch catalog")
    item = TestCatalog(branch_id=branch_id, **payload.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "test_code": item.test_code, "test_name": item.test_name}


@router.get("/catalog")
def list_test_catalog(
    q: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    query = db.query(TestCatalog).filter(TestCatalog.branch_id == branch_id, TestCatalog.is_active.is_(True))
    if q:
        token = f"%{q.strip()}%"
        query = query.filter(
            (TestCatalog.test_code.ilike(token))
            | (TestCatalog.test_name.ilike(token))
            | (TestCatalog.department.ilike(token))
        )
    rows = query.order_by(TestCatalog.test_name.asc()).limit(200).all()
    return [
        {
            "id": row.id,
            "test_code": row.test_code,
            "test_name": row.test_name,
            "department": row.department,
            "sample_type": row.sample_type,
            "turnaround_minutes": row.turnaround_minutes,
        }
        for row in rows
    ]


@router.post("/panels")
def create_test_panel(
    payload: TestPanelCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    panel = TestPanel(
        branch_id=branch_id,
        panel_name=payload.panel_name.strip(),
        description=payload.description,
        tests_json=[test.dict() for test in payload.tests],
        created_by=current_user.id,
    )
    db.add(panel)
    db.commit()
    db.refresh(panel)
    return {"id": panel.id, "panel_name": panel.panel_name, "tests": panel.tests_json}


@router.get("/panels")
def list_test_panels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    rows = (
        db.query(TestPanel)
        .filter(TestPanel.branch_id == branch_id, TestPanel.is_active.is_(True))
        .order_by(TestPanel.updated_at.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "panel_name": row.panel_name,
            "description": row.description,
            "tests": row.tests_json or [],
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


@router.post("/orders", response_model=LISOrderSummary)
def create_lis_order(
    payload: OrderCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    priority = _normalize_priority(payload.priority)
    tests = _resolve_tests_for_order(db, branch_id, payload)
    patient = _ensure_patient_in_branch(db, branch_id, payload.patient_id)

    daily_entry: Optional[DailyEntryModule] = None
    if payload.daily_entry_id:
        daily_entry = (
            db.query(DailyEntryModule)
            .filter(DailyEntryModule.id == payload.daily_entry_id, DailyEntryModule.branch_id == branch_id)
            .first()
        )
        if not daily_entry:
            raise HTTPException(status_code=404, detail="Daily entry not found for branch")
        duplicate = (
            db.query(OrderQueue.id)
            .filter(OrderQueue.branch_id == branch_id, OrderQueue.daily_entry_id == payload.daily_entry_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Daily entry is already queued in LIS")

    expected_tat = max(int(test.get("turnaround_minutes", 1440)) for test in tests)
    if priority == "STAT":
        expected_tat = max(30, int(expected_tat * 0.7))
    elif priority == "Emergency":
        expected_tat = max(15, int(expected_tat * 0.5))

    profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient.id).first() if patient else None
    patient_name = (
        payload.patient_name
        or (f"{patient.first_name} {patient.last_name}".strip() if patient else "")
        or (daily_entry.patient_name if daily_entry else "")
    ).strip()
    if not patient_name:
        raise HTTPException(status_code=400, detail="patient_name is required when patient_id is not provided")

    patient_code = payload.patient_code or (profile.patient_code if profile else None) or (patient.patient_id if patient else None)
    doctor_name = payload.doctor_name or (daily_entry.referred_doctor if daily_entry else None)

    order = OrderQueue(
        branch_id=branch_id,
        daily_entry_id=payload.daily_entry_id,
        source="daily_ops" if payload.daily_entry_id else "manual",
        order_number=_new_order_number(branch_id),
        patient_id=patient.id if patient else None,
        patient_name=patient_name,
        patient_code=patient_code,
        doctor_name=doctor_name,
        priority=priority,
        status="Registered",
        expected_tat_minutes=expected_tat,
        due_at=datetime.utcnow() + timedelta(minutes=expected_tat),
        tests_json=tests,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(order)
    db.flush()

    first_test = tests[0]
    sample = Sample(
        branch_id=branch_id,
        order_id=order.id,
        sample_code=_new_sample_code(branch_id),
        barcode_value=_new_sample_code(branch_id),
        sample_type=str(first_test.get("sample_type") or "Blood"),
        department=str(first_test.get("department") or "General"),
        status="Registered",
        expected_completion_at=order.due_at,
    )
    db.add(sample)
    db.commit()
    db.refresh(order)
    return _order_summary(order)


@router.get("/orders", response_model=List[LISOrderSummary])
def list_lis_orders(
    priority: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    query = db.query(OrderQueue).filter(OrderQueue.branch_id == branch_id)
    if priority:
        query = query.filter(OrderQueue.priority == _normalize_priority(priority))
    if status:
        query = query.filter(OrderQueue.status == status.strip())
    orders = query.order_by(OrderQueue.created_at.desc()).limit(limit).all()
    return [_order_summary(order) for order in orders]


@router.post("/orders/{order_id}/barcode", response_model=BarcodeResponse)
def generate_sample_barcode(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    sample = (
        db.query(Sample)
        .join(OrderQueue, OrderQueue.id == Sample.order_id)
        .filter(OrderQueue.branch_id == branch_id, OrderQueue.id == order_id)
        .order_by(Sample.id.asc())
        .first()
    )
    if not sample:
        raise HTTPException(status_code=404, detail="No sample found for this order")

    barcode_value = f"{sample.sample_code}-{uuid.uuid4().hex[:6].upper()}"
    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data(barcode_value)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    data_uri = f"data:image/png;base64,{image_base64}"

    sample.barcode_value = barcode_value
    sample.barcode_image_base64 = data_uri
    db.commit()
    db.refresh(sample)
    return BarcodeResponse(
        sample_id=sample.id,
        sample_code=sample.sample_code,
        barcode_value=sample.barcode_value,
        barcode_image_base64=sample.barcode_image_base64 or "",
    )


@router.get("/health-score", response_model=LISHealthScoreResponse)
def get_lis_health_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    now = datetime.utcnow()
    samples = (
        db.query(Sample)
        .filter(Sample.branch_id == branch_id, Sample.registered_at >= now - timedelta(days=30))
        .all()
    )
    pending_tests = sum(1 for sample in samples if _sample_is_pending(sample))
    rejected = sum(1 for sample in samples if sample.status == "Rejected")
    sample_rejection_rate = round((rejected / len(samples) * 100.0), 2) if samples else 0.0

    qc_rows = (
        db.query(QCResult)
        .filter(QCResult.branch_id == branch_id, QCResult.created_at >= now - timedelta(days=14))
        .all()
    )
    qc_failures = sum(1 for row in qc_rows if row.qc_status.lower() == "failed")
    qc_failure_rate = round((qc_failures / len(qc_rows) * 100.0), 2) if qc_rows else 0.0

    tat = _calculate_tat_minutes(samples)["average"]
    score = 100
    score -= min(35, int(qc_failure_rate * 2))
    score -= min(25, int(sample_rejection_rate * 2))
    score -= min(20, int(pending_tests * 0.8))
    score -= min(20, int(max(tat - 180, 0) / 30))
    score = max(0, min(100, score))

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    return LISHealthScoreResponse(
        score=score,
        status=_status_from_score(score),
        average_tat_minutes=tat,
        qc_failure_rate=qc_failure_rate,
        sample_rejection_rate=sample_rejection_rate,
        pending_tests=pending_tests,
        branch_name=branch.name if branch else None,
        last_updated=now.isoformat(),
    )


@router.get("/stats", response_model=LISStatsResponse)
def get_lis_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    todays_orders = db.query(OrderQueue).filter(OrderQueue.branch_id == branch_id, OrderQueue.created_at >= today_start).all()
    all_samples = db.query(Sample).filter(Sample.branch_id == branch_id).all()
    todays_samples = [sample for sample in all_samples if sample.registered_at and sample.registered_at >= today_start]

    tat_average = _calculate_tat_minutes(all_samples)["average"]
    pending_samples = [sample for sample in all_samples if _sample_is_pending(sample)]
    pending_by_department: Dict[str, int] = {}
    for sample in pending_samples:
        pending_by_department[sample.department] = pending_by_department.get(sample.department, 0) + 1

    rejected_count = sum(1 for sample in all_samples if sample.status == "Rejected")
    sample_rejection_rate = round((rejected_count / len(all_samples) * 100.0), 2) if all_samples else 0.0

    qc_rows = db.query(QCResult).filter(QCResult.branch_id == branch_id, QCResult.created_at >= now - timedelta(days=14)).all()
    qc_failures = sum(1 for row in qc_rows if row.qc_status.lower() == "failed")
    qc_failure_rate = (qc_failures / len(qc_rows) * 100.0) if qc_rows else 0.0

    delayed_samples = sum(
        1
        for sample in pending_samples
        if sample.expected_completion_at is not None and sample.expected_completion_at < now
    )

    priority_to_samples: Dict[str, List[Sample]] = {"Routine": [], "STAT": [], "Emergency": []}
    order_lookup = {order.id: order for order in db.query(OrderQueue).filter(OrderQueue.branch_id == branch_id).all()}
    for sample in all_samples:
        order = order_lookup.get(sample.order_id)
        if order and order.priority in priority_to_samples:
            priority_to_samples[order.priority].append(sample)

    tat_breakdown = {
        "Routine": _calculate_tat_minutes(priority_to_samples["Routine"])["average"],
        "STAT": _calculate_tat_minutes(priority_to_samples["STAT"])["average"],
        "Emergency": _calculate_tat_minutes(priority_to_samples["Emergency"])["average"],
    }

    return LISStatsResponse(
        todays_test_volume=len(todays_orders),
        average_tat_minutes=tat_average,
        tat_breakdown=tat_breakdown,
        pending_tests_count=len(pending_samples),
        pending_by_department=pending_by_department,
        sample_rejection_rate=sample_rejection_rate,
        qc_status=_qc_status_label(qc_failure_rate),
        delayed_samples=delayed_samples,
        last_updated=now.isoformat(),
    )


@router.put("/samples/{sample_id}/status")
def update_sample_status(
    sample_id: int,
    payload: UpdateSampleStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    sample = db.query(Sample).filter(Sample.id == sample_id, Sample.branch_id == branch_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found for this branch")

    if payload.status not in SAMPLE_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {sorted(SAMPLE_STATUSES)}")

    sample.status = payload.status
    if payload.status == "Rejected":
        sample.rejection_reason = (payload.rejection_reason or "").strip() or "Rejected by lab"
        sample.completed_at = datetime.utcnow()
    elif payload.status == "In Processing":
        sample.started_at = datetime.utcnow()
    elif payload.status == "Reported":
        sample.reported_at = datetime.utcnow()
        sample.completed_at = sample.completed_at or datetime.utcnow()
    elif payload.status == "QC Passed":
        sample.completed_at = datetime.utcnow()

    order = db.query(OrderQueue).filter(OrderQueue.id == sample.order_id, OrderQueue.branch_id == branch_id).first()
    if order:
        open_samples = (
            db.query(func.count(Sample.id))
            .filter(and_(Sample.order_id == order.id, Sample.status.notin_(["Reported", "Rejected"])))
            .scalar()
        )
        if open_samples == 0:
            order.status = "Reported"
        elif payload.status in {"In Processing", "QC Passed"}:
            order.status = "In Processing"

    db.commit()
    return {"sample_id": sample.id, "status": sample.status, "rejection_reason": sample.rejection_reason}


@router.put("/samples/{sample_id}/route")
def route_sample(
    sample_id: int,
    payload: UpdateSampleRouteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    sample = db.query(Sample).filter(Sample.id == sample_id, Sample.branch_id == branch_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found for this branch")
    sample.department = payload.department.strip()
    sample.analyzer_name = payload.analyzer_name.strip() if payload.analyzer_name else None
    sample.storage_location = payload.storage_location.strip() if payload.storage_location else None
    if sample.status == "Registered":
        sample.status = "In Processing"
        sample.started_at = datetime.utcnow()
    db.commit()
    return {"sample_id": sample.id, "department": sample.department, "analyzer_name": sample.analyzer_name, "status": sample.status}


@router.post("/worklists")
def create_worklist(
    payload: CreateWorklistRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    sample_rows = db.query(Sample).filter(Sample.branch_id == branch_id, Sample.id.in_(payload.sample_ids)).all()
    if len(sample_rows) != len(set(payload.sample_ids)):
        raise HTTPException(status_code=404, detail="One or more samples are not found in this branch")

    worklist = Worklist(
        branch_id=branch_id,
        worklist_code=f"WL-{branch_id}-{datetime.utcnow().strftime('%Y%m%d%H%M')}-{uuid.uuid4().hex[:4].upper()}",
        department=payload.department.strip(),
        analyzer_name=payload.analyzer_name.strip() if payload.analyzer_name else None,
        status="Open",
        sample_ids_json=payload.sample_ids,
        created_by=current_user.id,
    )
    db.add(worklist)
    for sample in sample_rows:
        sample.department = payload.department.strip()
        if payload.analyzer_name:
            sample.analyzer_name = payload.analyzer_name.strip()
        if sample.status == "Registered":
            sample.status = "In Processing"
            sample.started_at = datetime.utcnow()
    db.commit()
    db.refresh(worklist)
    return {"id": worklist.id, "worklist_code": worklist.worklist_code, "sample_count": len(payload.sample_ids)}


@router.get("/analyzers")
def get_analyzer_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    samples = db.query(Sample).filter(Sample.branch_id == branch_id).all()
    calibrations = (
        db.query(InstrumentCalibration)
        .filter(InstrumentCalibration.branch_id == branch_id)
        .order_by(InstrumentCalibration.updated_at.desc())
        .all()
    )

    by_analyzer: Dict[str, dict] = {}
    for sample in samples:
        analyzer = sample.analyzer_name or "Unassigned Analyzer"
        bucket = by_analyzer.setdefault(
            analyzer,
            {"analyzer_name": analyzer, "sample_count": 0, "in_processing": 0, "reported": 0, "status": "Operational"},
        )
        bucket["sample_count"] += 1
        if sample.status == "In Processing":
            bucket["in_processing"] += 1
        if sample.status == "Reported":
            bucket["reported"] += 1

    calibration_payload = [
        {
            "id": calibration.id,
            "analyzer_name": calibration.analyzer_name,
            "calibration_status": calibration.calibration_status,
            "calibrated_at": calibration.calibrated_at.isoformat() if calibration.calibrated_at else None,
            "next_due_at": calibration.next_due_at.isoformat() if calibration.next_due_at else None,
            "maintenance_notes": calibration.maintenance_notes,
            "maintenance_history": calibration.maintenance_history_json or [],
        }
        for calibration in calibrations
    ]

    return {
        "analyzers": list(by_analyzer.values()),
        "calibration_logs": calibration_payload,
        "maintenance_history": [
            {
                "analyzer_name": row["analyzer_name"],
                "last_maintenance_note": row.get("maintenance_notes"),
                "history": row.get("maintenance_history", []),
            }
            for row in calibration_payload
        ],
    }


@router.get("/samples")
def list_samples(
    status: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    query = db.query(Sample).filter(Sample.branch_id == branch_id)
    if status:
        query = query.filter(Sample.status == status)
    samples = query.order_by(Sample.registered_at.desc()).limit(500).all()
    return [
        {
            "id": sample.id,
            "order_id": sample.order_id,
            "sample_code": sample.sample_code,
            "barcode_value": sample.barcode_value,
            "barcode_image_base64": sample.barcode_image_base64,
            "sample_type": sample.sample_type,
            "department": sample.department,
            "analyzer_name": sample.analyzer_name,
            "storage_location": sample.storage_location,
            "status": sample.status,
            "rejection_reason": sample.rejection_reason,
            "registered_at": sample.registered_at.isoformat() if sample.registered_at else None,
            "expected_completion_at": sample.expected_completion_at.isoformat() if sample.expected_completion_at else None,
        }
        for sample in samples
    ]


@router.post("/qc/results")
def upsert_qc_result(
    payload: QCResultUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    if payload.sample_id is not None:
        sample = db.query(Sample).filter(Sample.id == payload.sample_id, Sample.branch_id == branch_id).first()
        if not sample:
            raise HTTPException(status_code=404, detail="Sample not found for this branch")
    result = QCResult(
        branch_id=branch_id,
        sample_id=payload.sample_id,
        analyzer_name=payload.analyzer_name.strip(),
        test_code=payload.test_code.strip(),
        qc_status=payload.qc_status.strip(),
        failure_reason=(payload.failure_reason or "").strip() or None,
        hil_flag=payload.hil_flag,
        delta_check_flag=payload.delta_check_flag,
        critical_value_flag=payload.critical_value_flag,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return {"id": result.id, "qc_status": result.qc_status, "created_at": result.created_at.isoformat()}


@router.get("/qc/dashboard")
def get_qc_dashboard(
    days: int = Query(default=30, ge=1, le=180),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    start_at = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(QCResult)
        .filter(QCResult.branch_id == branch_id, QCResult.created_at >= start_at)
        .order_by(QCResult.created_at.asc())
        .all()
    )
    pass_count = sum(1 for row in rows if row.qc_status.lower() == "passed")
    fail_count = sum(1 for row in rows if row.qc_status.lower() == "failed")
    warning_count = sum(1 for row in rows if row.qc_status.lower() not in {"passed", "failed"})
    trend = [
        {
            "time": row.created_at.isoformat() if row.created_at else datetime.utcnow().isoformat(),
            "test_code": row.test_code,
            "status": row.qc_status,
            "hil_flag": row.hil_flag,
            "delta_check_flag": row.delta_check_flag,
            "critical_value_flag": row.critical_value_flag,
            "score": 100 if row.qc_status.lower() == "passed" else 40 if row.qc_status.lower() == "failed" else 70,
        }
        for row in rows
    ]
    return {
        "summary": {"pass": pass_count, "warning": warning_count, "out_of_control": fail_count},
        "westgard_findings": _westgard_flags(rows),
        "trend": trend,
    }


@router.post("/calibrations")
def upsert_calibration(
    payload: CalibrationUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    existing = (
        db.query(InstrumentCalibration)
        .filter(InstrumentCalibration.branch_id == branch_id, InstrumentCalibration.analyzer_name == payload.analyzer_name.strip())
        .first()
    )
    next_due = datetime.fromisoformat(payload.next_due_at) if payload.next_due_at else None
    if existing:
        existing.calibration_status = payload.calibration_status.strip()
        existing.calibrated_at = datetime.utcnow() if payload.calibration_status.lower() == "calibrated" else existing.calibrated_at
        existing.next_due_at = next_due
        existing.maintenance_notes = (payload.maintenance_notes or "").strip() or existing.maintenance_notes
    else:
        existing = InstrumentCalibration(
            branch_id=branch_id,
            analyzer_name=payload.analyzer_name.strip(),
            calibration_status=payload.calibration_status.strip(),
            calibrated_at=datetime.utcnow() if payload.calibration_status.lower() == "calibrated" else None,
            next_due_at=next_due,
            maintenance_notes=(payload.maintenance_notes or "").strip() or None,
            maintenance_history_json=[],
        )
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return {
        "id": existing.id,
        "analyzer_name": existing.analyzer_name,
        "calibration_status": existing.calibration_status,
        "next_due_at": existing.next_due_at.isoformat() if existing.next_due_at else None,
    }


@router.post("/proficiency-tests")
def create_proficiency_test_run(
    payload: ProficiencyRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    run = ProficiencyTestRun(
        branch_id=branch_id,
        program_name=payload.program_name.strip(),
        cycle_name=payload.cycle_name.strip(),
        department=payload.department.strip(),
        participation_status=payload.participation_status.strip(),
        score=payload.score,
        notes=(payload.notes or "").strip() or None,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"id": run.id, "program_name": run.program_name, "status": run.participation_status, "score": run.score}


@router.get("/proficiency-tests")
def list_proficiency_test_runs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    rows = (
        db.query(ProficiencyTestRun)
        .filter(ProficiencyTestRun.branch_id == branch_id)
        .order_by(ProficiencyTestRun.created_at.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "program_name": row.program_name,
            "cycle_name": row.cycle_name,
            "department": row.department,
            "participation_status": row.participation_status,
            "score": row.score,
            "notes": row.notes,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/inventory/overview")
def get_reagent_inventory_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    items = db.query(InventoryItemV2).filter(InventoryItemV2.branch_id == branch_id, InventoryItemV2.is_active.is_(True)).all()
    today = datetime.utcnow().date()
    low_stock = [item for item in items if float(item.current_qty or 0) <= float(item.min_threshold or 0)]
    near_expiry = [
        item
        for item in items
        if item.expiry_date is not None and 0 <= (item.expiry_date - today).days <= 60
    ]
    return {
        "total_items": len(items),
        "low_stock_alerts": [
            {
                "item_id": item.id,
                "item_name": item.item_name,
                "department": item.department,
                "current_qty": float(item.current_qty or 0),
                "min_threshold": float(item.min_threshold or 0),
            }
            for item in low_stock
        ],
        "lot_expiry_tracking": [
            {
                "item_id": item.id,
                "item_name": item.item_name,
                "lot_number": item.barcode_number,
                "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
                "days_to_expiry": (item.expiry_date - today).days if item.expiry_date else None,
            }
            for item in near_expiry
        ],
    }


@router.get("/inventory/consumption-analytics")
def get_reagent_consumption_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    rows = (
        db.query(InventoryConsumptionHistory)
        .filter(InventoryConsumptionHistory.branch_id == branch_id)
        .order_by(InventoryConsumptionHistory.consumed_on.desc())
        .limit(2000)
        .all()
    )
    item_map = {item.id: item for item in db.query(InventoryItemV2).filter(InventoryItemV2.branch_id == branch_id).all()}
    by_test: Dict[str, float] = {}
    by_department: Dict[str, float] = {}
    by_analyzer: Dict[str, float] = {}
    cost_per_test: Dict[str, float] = {}

    for row in rows:
        item = item_map.get(row.inventory_item_id)
        if not item:
            continue
        qty = float(row.quantity or 0)
        unit_cost = float(item.unit_cost or 0)
        test_name = (row.test_name or "Unknown Test").strip()
        department = (item.department or "General").strip()
        analyzer = "Unassigned Analyzer"
        if row.notes and "analyzer=" in row.notes:
            analyzer = row.notes.split("analyzer=", 1)[1].split("|", 1)[0].strip() or analyzer

        by_test[test_name] = by_test.get(test_name, 0.0) + qty
        by_department[department] = by_department.get(department, 0.0) + qty
        by_analyzer[analyzer] = by_analyzer.get(analyzer, 0.0) + qty
        cost_per_test[test_name] = cost_per_test.get(test_name, 0.0) + qty * unit_cost

    return {
        "usage_by_test": [{"name": key, "quantity": round(value, 2)} for key, value in sorted(by_test.items())],
        "usage_by_department": [{"name": key, "quantity": round(value, 2)} for key, value in sorted(by_department.items())],
        "usage_by_analyzer": [{"name": key, "quantity": round(value, 2)} for key, value in sorted(by_analyzer.items())],
        "cost_per_test": [{"name": key, "cost": round(value, 2)} for key, value in sorted(cost_per_test.items())],
    }


@router.post("/reports/generate")
async def generate_lis_report(
    payload: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    order = db.query(OrderQueue).filter(OrderQueue.id == payload.order_id, OrderQueue.branch_id == branch_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this branch")
    sample = None
    if payload.sample_id is not None:
        sample = db.query(Sample).filter(Sample.id == payload.sample_id, Sample.branch_id == branch_id).first()
        if not sample:
            raise HTTPException(status_code=404, detail="Sample not found for this branch")
    else:
        sample = db.query(Sample).filter(Sample.order_id == order.id, Sample.branch_id == branch_id).order_by(Sample.id.asc()).first()

    previous = (
        db.query(LISReportArchive)
        .filter(LISReportArchive.branch_id == branch_id, LISReportArchive.order_id == order.id)
        .order_by(LISReportArchive.version.desc())
        .first()
    )
    next_version = 1 if not previous else int(previous.version) + 1
    report_number = _report_number(branch_id)
    patient = db.query(Patient).filter(Patient.id == order.patient_id, Patient.branch_id == branch_id).first() if order.patient_id else None
    profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient.id).first() if patient else None

    report_payload = {
        "report_number": report_number,
        "order_number": order.order_number,
        "patient_name": order.patient_name,
        "patient_code": order.patient_code,
        "doctor_name": order.doctor_name,
        "priority": order.priority,
        "tests": order.tests_json or [],
        "summary": payload.summary or "Results validated and approved for release.",
        "legal_note": payload.legal_note or "Digitally signed LIS report for compliance use.",
    }
    fake_pdf = base64.b64encode(_safe_json_text(report_payload).encode("utf-8")).decode("utf-8")
    channel_results = await _deliver_report_channels(
        patient_name=order.patient_name,
        mobile=profile.mobile if profile else None,
        email=profile.email if profile else None,
        report_number=report_number,
        channels=payload.channels,
    )
    archive = LISReportArchive(
        branch_id=branch_id,
        order_id=order.id,
        sample_id=sample.id if sample else None,
        report_number=report_number,
        version=next_version,
        template_name=payload.template_name.strip(),
        signed_by=(payload.signed_by or "").strip() or None,
        signed_at=datetime.utcnow() if payload.signed_by else None,
        channels_json=channel_results,
        report_payload_json=report_payload,
        report_pdf_base64=fake_pdf,
        status="Delivered" if any(item.get("status") == "sent" for item in channel_results) else "Generated",
    )
    db.add(archive)
    if sample:
        sample.status = "Reported"
        sample.reported_at = datetime.utcnow()
        sample.completed_at = sample.completed_at or datetime.utcnow()
    order.status = "Reported"
    db.commit()
    db.refresh(archive)
    return {
        "report_id": archive.id,
        "report_number": archive.report_number,
        "version": archive.version,
        "status": archive.status,
        "channels": archive.channels_json or [],
        "pdf_base64": archive.report_pdf_base64,
    }


@router.post("/reports/bulk-generate")
async def bulk_generate_lis_reports(
    payload: BulkReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    if not payload.order_ids:
        raise HTTPException(status_code=400, detail="order_ids cannot be empty")
    results: List[dict] = []
    for order_id in payload.order_ids:
        order = db.query(OrderQueue).filter(OrderQueue.id == order_id, OrderQueue.branch_id == branch_id).first()
        if not order:
            continue
        report = await generate_lis_report(
            ReportGenerateRequest(
                order_id=order.id,
                template_name=payload.template_name,
                signed_by=payload.signed_by,
                channels=payload.channels,
            ),
            current_user=current_user,
            db=db,
        )
        results.append({"order_id": order.id, **report})
    return {"total_requested": len(payload.order_ids), "generated": len(results), "reports": results}


@router.get("/reports/archive")
def get_lis_report_archive(
    search: Optional[str] = Query(default=None),
    report_number: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    query = db.query(LISReportArchive).filter(LISReportArchive.branch_id == branch_id)
    if report_number:
        query = query.filter(LISReportArchive.report_number == report_number.strip())
    if search:
        token = f"%{search.strip()}%"
        query = query.join(OrderQueue, OrderQueue.id == LISReportArchive.order_id).filter(
            (LISReportArchive.report_number.ilike(token))
            | (OrderQueue.patient_name.ilike(token))
            | (OrderQueue.patient_code.ilike(token))
        )
    rows = query.order_by(LISReportArchive.created_at.desc(), LISReportArchive.version.desc()).limit(500).all()
    return [
        {
            "id": row.id,
            "report_number": row.report_number,
            "version": row.version,
            "template_name": row.template_name,
            "status": row.status,
            "signed_by": row.signed_by,
            "signed_at": row.signed_at.isoformat() if row.signed_at else None,
            "channels": row.channels_json or [],
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/analytics/performance")
def lis_analytics_performance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    samples = db.query(Sample).filter(Sample.branch_id == branch_id).all()
    qc_rows = db.query(QCResult).filter(QCResult.branch_id == branch_id).all()
    qc_by_dept: Dict[str, List[QCResult]] = {}
    for row in qc_rows:
        analyzer = (row.analyzer_name or "General").split("-", 1)[0].strip()
        qc_by_dept.setdefault(analyzer, []).append(row)

    by_department: Dict[str, dict] = {}
    for sample in samples:
        department = sample.department or "General"
        entry = by_department.setdefault(department, {"department": department, "volume": 0, "reported": 0, "tat_total": 0.0, "tat_count": 0})
        entry["volume"] += 1
        if sample.status == "Reported":
            entry["reported"] += 1
        if sample.started_at and sample.completed_at:
            entry["tat_total"] += (sample.completed_at - sample.started_at).total_seconds() / 60.0
            entry["tat_count"] += 1

    output = []
    for department, row in by_department.items():
        tat = round(row["tat_total"] / row["tat_count"], 2) if row["tat_count"] else 0.0
        qc_dept = qc_by_dept.get(department, [])
        qc_fail = sum(1 for item in qc_dept if item.qc_status.lower() == "failed")
        qc_status = _qc_status_label((qc_fail / len(qc_dept) * 100.0) if qc_dept else 0.0)
        output.append(
            {
                "department": department,
                "volume": row["volume"],
                "reported": row["reported"],
                "avg_tat_minutes": tat,
                "productivity_percent": round((row["reported"] / row["volume"] * 100.0), 2) if row["volume"] else 0.0,
                "qc_status": qc_status,
            }
        )
    return {"departments": sorted(output, key=lambda item: item["department"])}


@router.get("/analytics/tat")
def lis_analytics_tat(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    samples = db.query(Sample).filter(Sample.branch_id == branch_id).all()
    order_lookup = {row.id: row for row in db.query(OrderQueue).filter(OrderQueue.branch_id == branch_id).all()}
    by_day: Dict[str, List[float]] = {}
    by_priority: Dict[str, List[float]] = {"Routine": [], "STAT": [], "Emergency": []}
    by_department: Dict[str, List[float]] = {}
    predictions: List[dict] = []
    for sample in samples:
        if not sample.started_at:
            continue
        end_time = sample.completed_at or sample.reported_at
        if end_time:
            minutes = (end_time - sample.started_at).total_seconds() / 60.0
            day_key = sample.started_at.strftime("%A")
            by_day.setdefault(day_key, []).append(minutes)
            by_department.setdefault(sample.department or "General", []).append(minutes)
            order = order_lookup.get(sample.order_id)
            if order and order.priority in by_priority:
                by_priority[order.priority].append(minutes)
        else:
            expected = sample.expected_completion_at
            if expected and expected < datetime.utcnow():
                predictions.append(
                    {
                        "sample_id": sample.id,
                        "sample_code": sample.sample_code,
                        "department": sample.department,
                        "predicted_delay_minutes": round((datetime.utcnow() - expected).total_seconds() / 60.0, 2),
                    }
                )
    return {
        "tat_by_day_of_week": [{"day": day, "avg_tat_minutes": round(sum(values) / len(values), 2)} for day, values in sorted(by_day.items()) if values],
        "tat_by_priority": [{"priority": key, "avg_tat_minutes": round(sum(values) / len(values), 2) if values else 0.0} for key, values in by_priority.items()],
        "tat_by_department": [{"department": key, "avg_tat_minutes": round(sum(values) / len(values), 2)} for key, values in sorted(by_department.items()) if values],
        "predicted_breaches": predictions,
    }


@router.get("/analytics/financial")
def lis_analytics_financial(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    orders = db.query(OrderQueue).filter(OrderQueue.branch_id == branch_id).all()
    consumption = db.query(InventoryConsumptionHistory).filter(InventoryConsumptionHistory.branch_id == branch_id).all()
    item_lookup = {item.id: item for item in db.query(InventoryItemV2).filter(InventoryItemV2.branch_id == branch_id).all()}

    revenue = float(len(orders) * 850.0)
    reagent_cost = 0.0
    for row in consumption:
        item = item_lookup.get(row.inventory_item_id)
        if not item:
            continue
        reagent_cost += float(row.quantity or 0) * float(item.unit_cost or 0)
    profitability = revenue - reagent_cost
    margin = round((profitability / revenue * 100.0), 2) if revenue > 0 else 0.0
    return {
        "revenue": round(revenue, 2),
        "reagent_cost": round(reagent_cost, 2),
        "profitability": round(profitability, 2),
        "margin_percent": margin,
        "cost_per_test": round((reagent_cost / len(orders)), 2) if orders else 0.0,
    }


@router.get("/analytics/ai-insights")
def lis_ai_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    now = datetime.utcnow()
    samples = db.query(Sample).filter(Sample.branch_id == branch_id).all()
    qc_rows = db.query(QCResult).filter(QCResult.branch_id == branch_id, QCResult.created_at >= now - timedelta(days=30)).all()
    calibrations = db.query(InstrumentCalibration).filter(InstrumentCalibration.branch_id == branch_id).all()

    pending = [sample for sample in samples if _sample_is_pending(sample)]
    tat_prediction = [
        {
            "sample_code": sample.sample_code,
            "department": sample.department,
            "predicted_breach": bool(sample.expected_completion_at and sample.expected_completion_at < now),
        }
        for sample in pending[:30]
    ]

    weekday_volume: Dict[str, int] = {}
    for sample in samples:
        key = (sample.registered_at or now).strftime("%A")
        weekday_volume[key] = weekday_volume.get(key, 0) + 1
    demand_forecast = [
        {"day": day, "forecasted_volume": int(count * 1.08)}
        for day, count in sorted(weekday_volume.items())
    ]

    instrument_risk = []
    for calibration in calibrations:
        recent_qc = [row for row in qc_rows if (row.analyzer_name or "") == calibration.analyzer_name]
        fail_rate = (sum(1 for row in recent_qc if row.qc_status.lower() == "failed") / len(recent_qc) * 100.0) if recent_qc else 0.0
        risk = "High" if fail_rate > 20 or (calibration.next_due_at and calibration.next_due_at < now) else "Medium" if fail_rate > 8 else "Low"
        instrument_risk.append({"analyzer_name": calibration.analyzer_name, "failure_risk": risk, "qc_fail_rate": round(fail_rate, 2)})

    anomaly_detection = []
    rejection_rate = (sum(1 for sample in samples if sample.status == "Rejected") / len(samples) * 100.0) if samples else 0.0
    if rejection_rate > 12:
        anomaly_detection.append({"type": "rejection_spike", "message": f"Sample rejection rate is elevated at {round(rejection_rate, 2)}%"})
    if sum(1 for row in qc_rows if row.qc_status.lower() == "failed") >= 5:
        anomaly_detection.append({"type": "qc_failure_cluster", "message": "Multiple QC failures detected in the recent cycle"})
    if len(samples) > 0 and sum(1 for sample in samples if _sample_is_pending(sample)) / len(samples) > 0.45:
        anomaly_detection.append({"type": "backlog_growth", "message": "Pending sample queue exceeds expected operating threshold"})

    return {
        "tat_prediction": tat_prediction,
        "demand_forecast": demand_forecast,
        "instrument_failure_prediction": instrument_risk,
        "anomaly_detection": anomaly_detection,
    }


@router.get("/compliance")
def lis_compliance_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch_id = _require_branch_id(current_user)
    qc_recent = db.query(QCResult).filter(QCResult.branch_id == branch_id, QCResult.created_at >= datetime.utcnow() - timedelta(days=30)).all()
    proficiency = db.query(ProficiencyTestRun).filter(ProficiencyTestRun.branch_id == branch_id).order_by(ProficiencyTestRun.created_at.desc()).limit(12).all()
    calibration_due = db.query(InstrumentCalibration).filter(InstrumentCalibration.branch_id == branch_id).all()
    overdue_calibration = [
        row for row in calibration_due if row.next_due_at is not None and row.next_due_at < datetime.utcnow()
    ]
    return {
        "nabl": {"qc_runs_30d": len(qc_recent), "westgard_violations": len(_westgard_flags(qc_recent)), "status": "Compliant" if len(overdue_calibration) == 0 else "Action Needed"},
        "iso": {"proficiency_participation": len(proficiency), "latest_scores": [{"program_name": row.program_name, "score": row.score} for row in proficiency[:5]]},
        "calibration": {"total_analyzers": len(calibration_due), "overdue": len(overdue_calibration)},
    }


def enqueue_daily_ops_entry_to_lis(
    db: Session,
    *,
    daily_entry_id: int,
    branch_id: int,
    created_by: int,
) -> OrderQueue:
    existing = db.query(OrderQueue).filter(OrderQueue.branch_id == branch_id, OrderQueue.daily_entry_id == daily_entry_id).first()
    if existing:
        return existing

    entry = db.query(DailyEntryModule).filter(DailyEntryModule.id == daily_entry_id, DailyEntryModule.branch_id == branch_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Daily entry not found for LIS queueing")

    tests = _split_tests_from_daily_entry(entry.test_name)
    expected_tat = max(int(test.get("turnaround_minutes", 1440)) for test in tests)
    order = OrderQueue(
        branch_id=branch_id,
        daily_entry_id=entry.id,
        source="daily_ops",
        order_number=_new_order_number(branch_id),
        patient_id=None,
        patient_name=entry.patient_name,
        patient_code=entry.auto_patient_id,
        doctor_name=entry.referred_doctor,
        priority="Routine",
        status="Registered",
        expected_tat_minutes=expected_tat,
        due_at=datetime.utcnow() + timedelta(minutes=expected_tat),
        tests_json=tests,
        notes=entry.remarks,
        created_by=created_by,
    )
    db.add(order)
    db.flush()
    sample = Sample(
        branch_id=branch_id,
        order_id=order.id,
        sample_code=_new_sample_code(branch_id),
        barcode_value=_new_sample_code(branch_id),
        sample_type=str(tests[0].get("sample_type") or "Blood"),
        department=str(tests[0].get("department") or "General"),
        status="Registered",
        expected_completion_at=order.due_at,
    )
    db.add(sample)
    return order
