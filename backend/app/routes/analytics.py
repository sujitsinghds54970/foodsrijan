from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import User
from app.models.analytics import DailyAnalyticsSnapshot
from app.models.daily_entry_module import DailyEntryModule, DailyExpense
from app.utils.auth_system import get_current_user, is_super_ceo_user

router = APIRouter()


def _to_float(value: object) -> float:
    return float(Decimal(str(value or 0)))


def _classify_modality(test_name: Optional[str]) -> str:
    text = (test_name or "").lower()
    if "xray" in text or "x-ray" in text:
        return "xray"
    if "sono" in text or "ultra" in text:
        return "sonography"
    if "path" in text or "cbc" in text or "blood" in text or "urine" in text:
        return "pathology"
    if "ct" in text or "mri" in text:
        return "ct_mri"
    return "other"


def _extract_test_tokens(test_name: Optional[str]) -> List[str]:
    if not test_name:
        return []
    normalized = test_name.replace("|", ",").replace(";", ",")
    return [token.strip() for token in normalized.split(",") if token.strip()]


def _check_analytics_access(current_user: User, branch_id: Optional[int] = None) -> None:
    if current_user.role not in ["branch_admin", "branch_director"] and not is_super_ceo_user(current_user):
        raise HTTPException(status_code=403, detail="Analytics access denied")
    if not is_super_ceo_user(current_user) and branch_id and current_user.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied for branch")


def build_daily_snapshot(db: Session, snapshot_date: date, branch_id: int) -> DailyAnalyticsSnapshot:
    start_dt = datetime.combine(snapshot_date, datetime.min.time())
    end_dt = datetime.combine(snapshot_date, datetime.max.time())

    entries = (
        db.query(DailyEntryModule)
        .filter(
            DailyEntryModule.branch_id == branch_id,
            DailyEntryModule.auto_entry_datetime >= start_dt,
            DailyEntryModule.auto_entry_datetime <= end_dt,
        )
        .all()
    )

    expenses_total = (
        db.query(func.coalesce(func.sum(DailyExpense.cost), 0))
        .filter(
            DailyExpense.branch_id == branch_id,
            DailyExpense.entry_date >= start_dt,
            DailyExpense.entry_date <= end_dt,
        )
        .scalar()
        or 0
    )

    total_revenue = 0.0
    patient_count = 0
    xray_count = 0
    sonography_count = 0
    pathology_count = 0
    ct_mri_count = 0
    other_count = 0
    total_menu_items = 0

    for entry in entries:
        total_revenue += _to_float(entry.total_amount)
        patient_count += 1

        tokens = _extract_test_tokens(entry.test_name)
        total_menu_items += len(tokens) if tokens else 1

        modality = _classify_modality(entry.test_name)
        if modality == "xray":
            xray_count += 1
        elif modality == "sonography":
            sonography_count += 1
        elif modality == "pathology":
            pathology_count += 1
        elif modality == "ct_mri":
            ct_mri_count += 1
        else:
            other_count += 1

    total_expenses = _to_float(expenses_total)
    net_profit = total_revenue - total_expenses
    avg_bill_value = (total_revenue / patient_count) if patient_count else 0.0

    snapshot = (
        db.query(DailyAnalyticsSnapshot)
        .filter(
            DailyAnalyticsSnapshot.date == snapshot_date,
            DailyAnalyticsSnapshot.branch_id == branch_id,
        )
        .first()
    )

    if not snapshot:
        snapshot = DailyAnalyticsSnapshot(date=snapshot_date, branch_id=branch_id)
        db.add(snapshot)

    snapshot.total_revenue = total_revenue
    snapshot.total_expenses = total_expenses
    snapshot.net_profit = net_profit
    snapshot.patient_count = patient_count
    snapshot.xray_count = xray_count
    snapshot.sonography_count = sonography_count
    snapshot.pathology_count = pathology_count
    snapshot.ct_mri_count = ct_mri_count
    snapshot.other_count = other_count
    snapshot.total_menu_items = total_menu_items
    snapshot.avg_bill_value = avg_bill_value

    db.flush()
    return snapshot


def backfill_snapshots(db: Session, start_date: date, end_date: date, branch_id: Optional[int] = None) -> int:
    branches_query = db.query(DailyEntryModule.branch_id).distinct()
    if branch_id:
        branches_query = branches_query.filter(DailyEntryModule.branch_id == branch_id)
    branch_ids = [row[0] for row in branches_query.all() if row[0] is not None]

    if not branch_ids and branch_id:
        branch_ids = [branch_id]

    total = 0
    current = start_date
    while current <= end_date:
        for b_id in branch_ids:
            build_daily_snapshot(db, current, b_id)
            total += 1
        current += timedelta(days=1)
    db.commit()
    return total


def run_daily_snapshot_job(for_date: Optional[date] = None) -> int:
    target_date = for_date or (date.today() - timedelta(days=1))
    db = SessionLocal()
    try:
        return backfill_snapshots(db, target_date, target_date)
    finally:
        db.close()


def _department_tat(db: Session, branch_id: int, start_dt: datetime, end_dt: datetime) -> List[Dict[str, float]]:
    rows = (
        db.query(DailyEntryModule)
        .filter(
            DailyEntryModule.branch_id == branch_id,
            DailyEntryModule.status == "Completed",
            DailyEntryModule.auto_entry_datetime >= start_dt,
            DailyEntryModule.auto_entry_datetime <= end_dt,
        )
        .all()
    )

    buckets: Dict[str, List[float]] = {
        "xray": [],
        "sonography": [],
        "pathology": [],
        "ct_mri": [],
        "other": [],
    }
    for row in rows:
        if not row.auto_entry_datetime or not row.updated_at:
            continue
        diff_minutes = max((row.updated_at - row.auto_entry_datetime).total_seconds() / 60.0, 0)
        buckets[_classify_modality(row.test_name)].append(diff_minutes)

    result = []
    for department, values in buckets.items():
        avg_mins = sum(values) / len(values) if values else 0.0
        result.append(
            {
                "department": department,
                "avg_minutes": round(avg_mins, 2),
                "avg_hours": round(avg_mins / 60.0, 2),
                "sample_size": len(values),
            }
        )
    return result


@router.get("/api/analytics/dashboard/branch/{branch_id}")
def analytics_dashboard_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_analytics_access(current_user, branch_id)

    today = date.today()
    start_of_month = today.replace(day=1)

    rows = (
        db.query(DailyAnalyticsSnapshot)
        .filter(
            DailyAnalyticsSnapshot.branch_id == branch_id,
            DailyAnalyticsSnapshot.date >= start_of_month,
            DailyAnalyticsSnapshot.date <= today,
        )
        .all()
    )

    if not rows:
        backfill_snapshots(db, start_of_month, today, branch_id)
        rows = (
            db.query(DailyAnalyticsSnapshot)
            .filter(
                DailyAnalyticsSnapshot.branch_id == branch_id,
                DailyAnalyticsSnapshot.date >= start_of_month,
                DailyAnalyticsSnapshot.date <= today,
            )
            .all()
        )

    total_revenue = sum(_to_float(r.total_revenue) for r in rows)
    total_expenses = sum(_to_float(r.total_expenses) for r in rows)
    net_profit = sum(_to_float(r.net_profit) for r in rows)
    patient_count = sum(int(r.patient_count or 0) for r in rows)
    total_menu_items = sum(int(r.total_menu_items or 0) for r in rows)

    modality_split = {
        "xray": sum(int(r.xray_count or 0) for r in rows),
        "sonography": sum(int(r.sonography_count or 0) for r in rows),
        "pathology": sum(int(r.pathology_count or 0) for r in rows),
        "ct_mri": sum(int(r.ct_mri_count or 0) for r in rows),
        "other": sum(int(r.other_count or 0) for r in rows),
    }

    start_dt = datetime.combine(start_of_month, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())
    tat = _department_tat(db, branch_id, start_dt, end_dt)

    return {
        "branch_id": branch_id,
        "period_start": start_of_month.isoformat(),
        "period_end": today.isoformat(),
        "kpis": {
            "total_revenue": round(total_revenue, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2),
            "patient_count": patient_count,
            "total_menu_items": total_menu_items,
            "avg_bill_value": round((total_revenue / patient_count) if patient_count else 0.0, 2),
        },
        "modality_split": modality_split,
        "department_tat": tat,
    }


@router.get("/api/analytics/trends")
def analytics_trends(
    branch_id: int = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_analytics_access(current_user, branch_id)

    end = end_date or date.today()
    start = start_date or (end - timedelta(days=29))
    if start > end:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    rows = (
        db.query(DailyAnalyticsSnapshot)
        .filter(
            DailyAnalyticsSnapshot.branch_id == branch_id,
            DailyAnalyticsSnapshot.date >= start,
            DailyAnalyticsSnapshot.date <= end,
        )
        .order_by(DailyAnalyticsSnapshot.date.asc())
        .all()
    )
    if not rows:
        backfill_snapshots(db, start, end, branch_id)
        rows = (
            db.query(DailyAnalyticsSnapshot)
            .filter(
                DailyAnalyticsSnapshot.branch_id == branch_id,
                DailyAnalyticsSnapshot.date >= start,
                DailyAnalyticsSnapshot.date <= end,
            )
            .order_by(DailyAnalyticsSnapshot.date.asc())
            .all()
        )

    daily = [
        {
            "date": row.date.isoformat(),
            "revenue": round(_to_float(row.total_revenue), 2),
            "expenses": round(_to_float(row.total_expenses), 2),
            "customers": int(row.patient_count or 0),
        }
        for row in rows
    ]

    monthly_map: Dict[str, Dict[str, float]] = {}
    for row in rows:
        key = row.date.strftime("%Y-%m")
        if key not in monthly_map:
            monthly_map[key] = {"revenue": 0.0, "expenses": 0.0, "customers": 0.0}
        monthly_map[key]["revenue"] += _to_float(row.total_revenue)
        monthly_map[key]["expenses"] += _to_float(row.total_expenses)
        monthly_map[key]["customers"] += int(row.patient_count or 0)

    monthly = [
        {
            "month": key,
            "revenue": round(values["revenue"], 2),
            "expenses": round(values["expenses"], 2),
            "customers": int(values["customers"]),
        }
        for key, values in sorted(monthly_map.items())
    ]

    return {
        "branch_id": branch_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": daily,
        "monthly": monthly,
    }


@router.get("/api/analytics/staff/top-referrers")
def analytics_top_referrers(
    branch_id: int = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_analytics_access(current_user, branch_id)

    end = end_date or date.today()
    start = start_date or end.replace(day=1)
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    rows = (
        db.query(
            DailyEntryModule.referred_doctor.label("doctor_name"),
            func.count(DailyEntryModule.id).label("patient_count"),
            func.coalesce(func.sum(DailyEntryModule.total_amount), 0).label("total_revenue"),
        )
        .filter(
            DailyEntryModule.branch_id == branch_id,
            DailyEntryModule.auto_entry_datetime >= start_dt,
            DailyEntryModule.auto_entry_datetime <= end_dt,
            DailyEntryModule.referred_doctor.isnot(None),
            DailyEntryModule.referred_doctor != "",
        )
        .group_by(DailyEntryModule.referred_doctor)
        .order_by(func.coalesce(func.sum(DailyEntryModule.total_amount), 0).desc())
        .limit(limit)
        .all()
    )

    result = [
        {
            "doctor_name": row.doctor_name,
            "patient_count": int(row.patient_count or 0),
            "total_revenue": round(_to_float(row.total_revenue), 2),
        }
        for row in rows
    ]
    return {"branch_id": branch_id, "start_date": start.isoformat(), "end_date": end.isoformat(), "items": result}


@router.get("/api/analytics/forecast/next-month")
def analytics_forecast_next_month(
    branch_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_analytics_access(current_user, branch_id)

    today = date.today()
    start = (today.replace(day=1) - timedelta(days=180)).replace(day=1)
    rows = (
        db.query(DailyAnalyticsSnapshot)
        .filter(
            DailyAnalyticsSnapshot.branch_id == branch_id,
            DailyAnalyticsSnapshot.date >= start,
            DailyAnalyticsSnapshot.date <= today,
        )
        .order_by(DailyAnalyticsSnapshot.date.asc())
        .all()
    )
    if not rows:
        backfill_snapshots(db, start, today, branch_id)
        rows = (
            db.query(DailyAnalyticsSnapshot)
            .filter(
                DailyAnalyticsSnapshot.branch_id == branch_id,
                DailyAnalyticsSnapshot.date >= start,
                DailyAnalyticsSnapshot.date <= today,
            )
            .order_by(DailyAnalyticsSnapshot.date.asc())
            .all()
        )

    month_map: Dict[str, int] = {}
    for row in rows:
        key = row.date.strftime("%Y-%m")
        month_map[key] = month_map.get(key, 0) + int(row.patient_count or 0)

    points = sorted(month_map.items())[-6:]
    if len(points) < 2:
        predicted = points[-1][1] if points else 0
    else:
        y_vals = [float(value) for _, value in points]
        n = len(y_vals)
        x_vals = list(range(n))
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)
        denominator = (n * sum_x2) - (sum_x * sum_x)
        if denominator == 0:
            predicted = y_vals[-1]
        else:
            slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator
            intercept = (sum_y - slope * sum_x) / n
            predicted = intercept + slope * n

    predicted = max(int(round(predicted)), 0)
    margin = int(round(predicted * 0.05))
    return {
        "branch_id": branch_id,
        "predicted_customers": predicted,
        "confidence_margin_percent": 5,
        "lower_bound": max(predicted - margin, 0),
        "upper_bound": predicted + margin,
        "series_used": [{"month": month, "customers": value} for month, value in points],
    }
