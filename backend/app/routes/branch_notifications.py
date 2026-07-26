from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.hr import (
    BranchNotification,
    BranchNotificationType,
    LeaveStatus,
    StaffLeaveRequest,
    StaffNotification,
    StaffProfile,
)
from app.utils.auth_system import get_current_user

router = APIRouter(prefix="/branch", tags=["Branch Notifications"])


class LeaveActionRequest(BaseModel):
    action: Literal["approve", "reject"]
    reason: Optional[str] = Field(default=None, max_length=1000)


def _require_branch_director_or_admin(current_user: User) -> None:
    role = (current_user.role or "").strip().lower()
    if role not in {"branch_director", "branch_admin"}:
        raise HTTPException(status_code=403, detail="Only branch director/admin can access this endpoint")
    if not current_user.branch_id:
        raise HTTPException(status_code=400, detail="Branch assignment missing")


def _ensure_branch_notification_schema(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS branch_notifications (
                id INTEGER PRIMARY KEY,
                branch_id INTEGER NOT NULL,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                related_entity_id INTEGER,
                is_read BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_branch_notifications_branch_id ON branch_notifications(branch_id)"))

    columns = db.execute(text("PRAGMA table_info(staff_leave_requests)")).fetchall()
    if not any(column[1] == "rejection_reason" for column in columns):
        db.execute(text("ALTER TABLE staff_leave_requests ADD COLUMN rejection_reason TEXT"))

    db.commit()


@router.get("/notifications")
def get_branch_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_branch_director_or_admin(current_user)
    _ensure_branch_notification_schema(db)

    rows = (
        db.query(BranchNotification)
        .filter(BranchNotification.branch_id == current_user.branch_id)
        .order_by(BranchNotification.created_at.desc(), BranchNotification.id.desc())
        .all()
    )

    leave_ids = [
        row.related_entity_id
        for row in rows
        if row.related_entity_id and str(getattr(row.type, "value", row.type)) == BranchNotificationType.LEAVE_REQUEST.value
    ]

    leave_map = {}
    if leave_ids:
        leave_rows = (
            db.query(StaffLeaveRequest, StaffProfile)
            .join(StaffProfile, StaffProfile.id == StaffLeaveRequest.staff_profile_id)
            .filter(
                StaffLeaveRequest.branch_id == current_user.branch_id,
                StaffLeaveRequest.id.in_(leave_ids),
            )
            .all()
        )
        for leave, staff in leave_rows:
            staff_name = None
            if staff and staff.user:
                staff_name = f"{(staff.user.first_name or '').strip()} {(staff.user.last_name or '').strip()}".strip() or None
            if not staff_name and staff:
                staff_name = staff.staff_id
            leave_map[leave.id] = {
                "id": leave.id,
                "staff_profile_id": leave.staff_profile_id,
                "staff_name": staff_name,
                "staff_id": staff.staff_id if staff else None,
                "leave_type": leave.leave_type,
                "start_date": leave.start_date,
                "end_date": leave.end_date,
                "reason": leave.reason,
                "status": leave.status.value if leave.status else LeaveStatus.PENDING.value,
                "rejection_reason": leave.rejection_reason,
                "created_at": leave.created_at,
            }

    return [
        {
            "id": row.id,
            "branch_id": row.branch_id,
            "type": row.type.value if hasattr(row.type, "value") else str(row.type),
            "title": row.title,
            "message": row.message,
            "related_entity_id": row.related_entity_id,
            "is_read": bool(row.is_read),
            "created_at": row.created_at,
            "status": (
                (leave_map[row.related_entity_id]["status"].capitalize() if row.related_entity_id in leave_map else "Pending")
                if (row.type.value if hasattr(row.type, "value") else str(row.type)) == BranchNotificationType.LEAVE_REQUEST.value
                else ("Unread" if not row.is_read else "Read")
            ),
            "leave_request": leave_map.get(row.related_entity_id) if row.related_entity_id else None,
        }
        for row in rows
    ]


@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_branch_director_or_admin(current_user)
    _ensure_branch_notification_schema(db)

    notification = (
        db.query(BranchNotification)
        .filter(
            BranchNotification.id == notification_id,
            BranchNotification.branch_id == current_user.branch_id,
        )
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}


@router.post("/leaves/{leave_id}/action")
def action_leave_request(
    leave_id: int,
    payload: LeaveActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_branch_director_or_admin(current_user)
    _ensure_branch_notification_schema(db)

    leave = (
        db.query(StaffLeaveRequest)
        .filter(
            StaffLeaveRequest.id == leave_id,
            StaffLeaveRequest.branch_id == current_user.branch_id,
        )
        .first()
    )
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    reason = (payload.reason or "").strip()
    if payload.action == "reject" and not reason:
        raise HTTPException(status_code=400, detail="reason is required when rejecting a leave request")

    if payload.action == "approve":
        leave.status = LeaveStatus.APPROVED
        leave.rejection_reason = None
        leave.review_comment = reason or "Approved by branch director"
        notification_message = (
            f"Your leave request #{leave.id} has been approved."
            if not reason
            else f"Your leave request #{leave.id} has been approved. Note: {reason}"
        )
    else:
        leave.status = LeaveStatus.REJECTED
        leave.rejection_reason = reason
        leave.review_comment = reason
        notification_message = f"Your leave request #{leave.id} has been rejected. Reason: {reason}"

    leave.reviewed_by = current_user.id
    leave.reviewed_at = datetime.utcnow()
    leave.approved_by = current_user.id if payload.action == "approve" else None
    leave.approval_date = datetime.utcnow() if payload.action == "approve" else None

    db.add(
        StaffNotification(
            staff_profile_id=leave.staff_profile_id,
            branch_id=leave.branch_id,
            message=notification_message,
            link="/staff/attendance",
        )
    )

    branch_notification = (
        db.query(BranchNotification)
        .filter(
            BranchNotification.branch_id == current_user.branch_id,
            BranchNotification.related_entity_id == leave.id,
            BranchNotification.type == BranchNotificationType.LEAVE_REQUEST,
        )
        .order_by(BranchNotification.id.desc())
        .first()
    )
    if branch_notification:
        branch_notification.is_read = True

    db.commit()
    return {
        "message": "Leave action applied successfully",
        "leave_id": leave.id,
        "status": leave.status.value,
        "rejection_reason": leave.rejection_reason,
    }
