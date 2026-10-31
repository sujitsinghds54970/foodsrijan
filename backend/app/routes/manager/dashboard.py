from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, Customer, User
from app.models.branch_lis import OrderQueue
from app.models.ceo import CeoAuditLog
from app.models.daily_entry_module import DailyEntryModule
from app.models.hr import DirectorStaffStatus, StaffAttendanceLog, StaffProfile, StaffTask
from app.models.inventory import InventoryItemV2
from app.models.patient_portal import CustomerFeedback
from app.services.executive_metrics import ResolvedScope, envelope
from app.utils.guards import OutletManagerContext, outlet_manager_context


router = APIRouter(prefix="/manager/dashboard", tags=["Outlet Manager"])

_ATTENDANCE_PROFILE_ID = getattr(StaffAttendanceLog, "staff_profile_id", StaffAttendanceLog.StaffEmployee_profile_id)
_OPEN_TASK_STATUSES = {"pending", "in progress", "in_progress", "overdue", "open"}
_LIVE_ORDER_STATUSES = {"registered", "ordered", "in processing", "in_progress", "in progress", "preparing", "dispatched"}


def _scope(context: OutletManagerContext) -> ResolvedScope:
    return ResolvedScope(
        level="branch",
        company_ids=(context.company_id,),
        company_id=context.company_id,
        branch_id=context.outlet_id,
    )


def _envelope(
    data: Any,
    context: OutletManagerContext,
    *,
    source_status: str = "complete",
    sources: list[str] | None = None,
    missing_sources: list[str] | None = None,
) -> dict[str, Any]:
    return envelope(
        data,
        _scope(context),
        source_status=source_status,
        sources=sources or [],
        missing_sources=missing_sources or [],
        ttl_seconds=60,
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _today_bounds() -> tuple[datetime, datetime]:
    start = datetime.combine(date.today(), datetime.min.time())
    return start, start + timedelta(days=1)


def _dashboard_sources(*extra: str) -> list[str]:
    return ["branches", *extra]


@router.get("/kpis")
def get_dashboard_kpis(
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    start, end = _today_bounds()
    window_start = datetime.utcnow() - timedelta(days=30)

    sales_total, order_count = (
        db.query(
            func.coalesce(func.sum(DailyEntryModule.total_amount), 0),
            func.count(DailyEntryModule.id),
        )
        .join(Branch, Branch.id == DailyEntryModule.branch_id)
        .filter(
            Branch.id == context.outlet_id,
            Branch.company_id == context.company_id,
            DailyEntryModule.auto_entry_datetime >= start,
            DailyEntryModule.auto_entry_datetime < end,
        )
        .first()
    )

    active_staff_count = (
        db.query(func.count(func.distinct(StaffProfile.id)))
        .select_from(StaffAttendanceLog)
        .join(StaffProfile, _ATTENDANCE_PROFILE_ID == StaffProfile.id)
        .join(Branch, Branch.id == StaffAttendanceLog.branch_id)
        .filter(
            Branch.id == context.outlet_id,
            Branch.company_id == context.company_id,
            StaffProfile.branch_id == context.outlet_id,
            StaffProfile.is_active.is_(True),
            StaffProfile.status == DirectorStaffStatus.ACTIVE,
            StaffAttendanceLog.attendance_date >= start,
            StaffAttendanceLog.attendance_date < end,
            StaffAttendanceLog.clock_in_time.isnot(None),
            StaffAttendanceLog.clock_out_time.is_(None),
        )
        .scalar()
        or 0
    )

    feedback_count, average_rating = (
        db.query(
            func.count(CustomerFeedback.id),
            func.avg(CustomerFeedback.rating),
        )
        .join(Customer, Customer.id == CustomerFeedback.patient_id)
        .join(Branch, Branch.id == Customer.branch_id)
        .filter(
            Branch.id == context.outlet_id,
            Branch.company_id == context.company_id,
            Customer.company_id == context.company_id,
            CustomerFeedback.rating.isnot(None),
            CustomerFeedback.created_at >= window_start,
        )
        .first()
    )

    low_stock_count = (
        db.query(func.count(InventoryItemV2.id))
        .join(Branch, Branch.id == InventoryItemV2.branch_id)
        .filter(
            Branch.id == context.outlet_id,
            Branch.company_id == context.company_id,
            InventoryItemV2.is_active.is_(True),
            InventoryItemV2.current_qty <= InventoryItemV2.min_threshold,
        )
        .scalar()
        or 0
    )

    open_task_count = (
        db.query(func.count(StaffTask.id))
        .join(Branch, Branch.id == StaffTask.branch_id)
        .filter(
            Branch.id == context.outlet_id,
            Branch.company_id == context.company_id,
            func.lower(StaffTask.status).in_(_OPEN_TASK_STATUSES),
        )
        .scalar()
        or 0
    )

    missing_sources: list[str] = []
    avg_customer_rating = round(float(average_rating), 2) if feedback_count and average_rating is not None else None
    if not feedback_count:
        missing_sources.append("patient_feedbacks")

    return _envelope(
        {
            "kpis": {
                "today_sales_total": float(sales_total or 0),
                "today_order_count": int(order_count or 0),
                "active_staff_count": int(active_staff_count),
                "average_customer_rating_30d": avg_customer_rating,
                "low_stock_items_count": int(low_stock_count),
                "pending_tasks_count": int(open_task_count),
            }
        },
        context,
        source_status="partial" if missing_sources else "complete",
        sources=_dashboard_sources(
            "daily_entries_module",
            "staff_attendance_logs",
            "staff_profiles",
            "inventory_items_v2",
            "staff_tasks",
            "patient_feedbacks",
        ),
        missing_sources=missing_sources,
    )


@router.get("/live-orders")
def get_live_orders(
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(OrderQueue)
        .join(Branch, Branch.id == OrderQueue.branch_id)
        .filter(
            Branch.id == context.outlet_id,
            Branch.company_id == context.company_id,
            func.lower(OrderQueue.status).in_(_LIVE_ORDER_STATUSES),
        )
        .order_by(OrderQueue.updated_at.desc(), OrderQueue.id.desc())
        .all()
    )
    return _envelope(
        {
            "live_orders": [
                {
                    "id": row.id,
                    "order_number": row.order_number,
                    "daily_entry_id": row.daily_entry_id,
                    "patient_name": row.patient_name,
                    "patient_code": row.patient_code,
                    "doctor_name": row.doctor_name,
                    "priority": row.priority,
                    "status": row.status,
                    "expected_tat_minutes": row.expected_tat_minutes,
                    "due_at": _json_value(row.due_at),
                    "menu_item_count": len(row.menu_items_json or []),
                    "created_at": _json_value(row.created_at),
                    "updated_at": _json_value(row.updated_at),
                }
                for row in rows
            ],
            "source_status": "complete",
        },
        context,
        source_status="empty" if not rows else "complete",
        sources=_dashboard_sources("branch_lis_order_queue"),
    )


@router.get("/staff-on-shift")
def get_staff_on_shift(
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    start, end = _today_bounds()
    rows = (
        db.query(StaffAttendanceLog, StaffProfile, User)
        .join(StaffProfile, _ATTENDANCE_PROFILE_ID == StaffProfile.id)
        .join(User, User.id == StaffProfile.user_id)
        .join(Branch, Branch.id == StaffAttendanceLog.branch_id)
        .filter(
            Branch.id == context.outlet_id,
            Branch.company_id == context.company_id,
            StaffProfile.branch_id == context.outlet_id,
            StaffProfile.is_active.is_(True),
            StaffProfile.status == DirectorStaffStatus.ACTIVE,
            User.company_id == context.company_id,
            StaffAttendanceLog.attendance_date >= start,
            StaffAttendanceLog.attendance_date < end,
            StaffAttendanceLog.clock_in_time.isnot(None),
            StaffAttendanceLog.clock_out_time.is_(None),
        )
        .order_by(StaffAttendanceLog.clock_in_time.asc(), StaffAttendanceLog.id.asc())
        .all()
    )
    return _envelope(
        {
            "staff": [
                {
                    "staff_profile_id": profile.id,
                    "user_id": user.id,
                    "name": user.display_name or " ".join(part for part in [user.first_name, user.last_name] if part).strip() or user.username,
                    "department": profile.department,
                    "specialization": profile.specialization,
                    "shift_timings": profile.shift_timings,
                    "attendance_status": _json_value(log.status),
                    "clock_in_time": _json_value(log.clock_in_time),
                    "work_mode": log.work_mode,
                    "task": log.task,
                }
                for log, profile, user in rows
            ]
        },
        context,
        source_status="empty" if not rows else "complete",
        sources=_dashboard_sources("staff_attendance_logs", "staff_profiles", "users"),
    )


@router.get("/activity")
def get_dashboard_activity(
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(CeoAuditLog, User)
        .join(User, User.id == CeoAuditLog.user_id)
        .filter(
            CeoAuditLog.request_meta["company_id"].as_integer() == context.company_id,
            CeoAuditLog.request_meta["outlet_id"].as_integer() == context.outlet_id,
        )
        .order_by(CeoAuditLog.created_at.desc(), CeoAuditLog.id.desc())
        .limit(10)
        .all()
    )
    return _envelope(
        {
            "events": [
                {
                    "id": row.id,
                    "action": row.action,
                    "http_method": row.http_method,
                    "endpoint": row.endpoint,
                    "response_status": row.response_status,
                    "actor": {
                        "id": user.id,
                        "username": user.username,
                        "name": user.display_name or " ".join(part for part in [user.first_name, user.last_name] if part).strip() or user.username,
                        "role": user.role,
                    },
                    "resource_type": row.request_meta.get("resource_type"),
                    "resource_id": row.request_meta.get("resource_id"),
                    "changes": row.request_meta.get("changes", {}),
                    "metadata": row.request_meta.get("metadata", {}),
                    "created_at": _json_value(row.created_at),
                }
                for row, user in rows
            ]
        },
        context,
        source_status="empty" if not rows else "complete",
        sources=_dashboard_sources("ceo_audit_logs", "users"),
    )


@router.get("/health")
def get_dashboard_health(
    context: OutletManagerContext = Depends(outlet_manager_context),
    db: Session = Depends(get_db),
):
    today = date.today()
    expiry_cutoff = today + timedelta(days=30)
    inventory_rows = (
        db.query(InventoryItemV2)
        .join(Branch, Branch.id == InventoryItemV2.branch_id)
        .filter(
            Branch.id == context.outlet_id,
            Branch.company_id == context.company_id,
            InventoryItemV2.is_active.is_(True),
        )
        .order_by(InventoryItemV2.id.asc())
        .all()
    )

    total_items = len(inventory_rows)
    in_stock_count = sum(1 for row in inventory_rows if float(row.current_qty or 0) > 0)
    low_stock_count = sum(1 for row in inventory_rows if float(row.current_qty or 0) <= float(row.min_threshold or 0))
    expiring_soon_count = sum(1 for row in inventory_rows if row.expiry_date is not None and row.expiry_date <= expiry_cutoff)

    feedback_rows = (
        db.query(CustomerFeedback)
        .join(Customer, Customer.id == CustomerFeedback.patient_id)
        .join(Branch, Branch.id == Customer.branch_id)
        .filter(
            Branch.id == context.outlet_id,
            Branch.company_id == context.company_id,
            Customer.company_id == context.company_id,
        )
        .order_by(CustomerFeedback.created_at.desc(), CustomerFeedback.id.desc())
        .all()
    )

    feedback_summary = None
    if feedback_rows:
        rated_rows = [row.rating for row in feedback_rows if row.rating is not None]
        feedback_summary = {
            "feedback_count": len(feedback_rows),
            "rated_feedback_count": len(rated_rows),
            "average_rating": round(sum(rated_rows) / len(rated_rows), 2) if rated_rows else None,
            "pending_resolution_count": sum(1 for row in feedback_rows if not row.is_resolved),
            "latest_feedback_at": _json_value(feedback_rows[0].created_at),
        }

    missing_sources = ["quality_food_safety"]
    if not feedback_rows:
        missing_sources.append("patient_feedbacks")

    def _percent(count: int) -> float | None:
        if not total_items:
            return None
        return round((count / total_items) * 100, 2)

    return _envelope(
        {
            "inventory_health": {
                "total_items": total_items,
                "in_stock_count": in_stock_count,
                "low_stock_count": low_stock_count,
                "expiring_soon_count": expiring_soon_count,
                "in_stock_percent": _percent(in_stock_count),
                "low_stock_percent": _percent(low_stock_count),
                "expiring_soon_percent": _percent(expiring_soon_count),
            },
            "quality_food_safety_score": None,
            "feedback_summary": feedback_summary,
        },
        context,
        source_status="partial",
        sources=_dashboard_sources("inventory_items_v2", "patient_feedbacks"),
        missing_sources=missing_sources,
    )
