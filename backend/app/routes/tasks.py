from datetime import datetime, date
from pathlib import Path
from typing import Optional
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.hr import (
    BranchNotification,
    BranchNotificationType,
    DirectorNotification,
    StaffNotification,
    StaffProfile,
    StaffTask,
    TaskAttachment,
    TaskComment,
)
from app.utils.auth_system import get_current_user, is_super_ceo_user


router = APIRouter(prefix="/tasks", tags=["Task Management"])

BASE_DIR = Path(__file__).resolve().parents[2]
TASK_ATTACHMENTS_DIR = BASE_DIR / "uploads" / "staff" / "task_attachments"


class TaskCreateRequest(BaseModel):
    assigned_to: int
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = Field(default="Medium")


class TaskUpdateRequest(BaseModel):
    assigned_to: Optional[int] = None
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None


class TaskStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="In Progress or Completed")


class TaskCommentRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


def _normalize_role(role: Optional[str]) -> str:
    return (role or "").strip().lower()


def _is_global_executive_role(role: Optional[str]) -> bool:
    normalized = _normalize_role(role)
    return normalized in {"super_ceo", "super_admin"}


def _normalize_priority(value: Optional[str]) -> str:
    normalized = (value or "Medium").strip().lower()
    mapping = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "urgent": "Urgent",
    }
    if normalized not in mapping:
        raise HTTPException(status_code=400, detail="priority must be Low, Medium, High, or Urgent")
    return mapping[normalized]


def _normalize_status(value: Optional[str]) -> str:
    normalized = (value or "Pending").strip().lower()
    mapping = {
        "pending": "Pending",
        "in progress": "In Progress",
        "in_progress": "In Progress",
        "completed": "Completed",
        "overdue": "Overdue",
        "cancelled": "Cancelled",
    }
    if normalized not in mapping:
        raise HTTPException(status_code=400, detail="status must be Pending, In Progress, Completed, Overdue, or Cancelled")
    return mapping[normalized]


def _serialize_task(task: StaffTask) -> dict:
    return {
        "id": task.id,
        "branch_id": task.branch_id,
        "assigned_by": task.assigned_by,
        "assigned_to": task.assigned_to,
        "title": task.title or task.task_name,
        "task_name": task.task_name,
        "description": task.description,
        "due_date": task.due_date or task.deadline,
        "deadline": task.deadline,
        "priority": task.priority,
        "status": task.status,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
    }


def _is_director_like(user: User) -> bool:
    return _normalize_role(user.role) in {"branch_director", "branch_admin", "super_admin", "super_ceo"}


def _is_staff_role(role: Optional[str]) -> bool:
    """Check if role is a staff-type role (not admin/director/doctor)"""
    role_normalized = _normalize_role(role)
    non_staff_roles = {'super_admin', 'super_ceo', 'branch_admin', 'branch_director', 'admin', 'doctor'}
    return role_normalized not in non_staff_roles


def _ensure_task_access(task: StaffTask, current_user: User) -> None:
    role = _normalize_role(current_user.role)
    if _is_global_executive_role(role):
        return
    if role in {"branch_director", "branch_admin"}:
        if current_user.branch_id != task.branch_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return
    if _is_staff_role(current_user.role):
        if task.assigned_to != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        return
    raise HTTPException(status_code=403, detail="Access denied")


def _resolve_staff_profile(db: Session, user_id: int, branch_id: Optional[int]) -> Optional[StaffProfile]:
    query = db.query(StaffProfile).filter(StaffProfile.user_id == user_id)
    if branch_id is not None:
        query = query.filter(StaffProfile.branch_id == branch_id)
    return query.first()


def _ensure_branch_notifications_table(db: Session) -> None:
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


def _apply_overdue_flags(db: Session, branch_id: Optional[int] = None) -> None:
    now = datetime.utcnow()
    query = db.query(StaffTask).filter(
        StaffTask.status.in_(["Pending", "In Progress"]),
        StaffTask.due_date.isnot(None),
        StaffTask.due_date < now,
    )
    if branch_id is not None:
        query = query.filter(StaffTask.branch_id == branch_id)

    updated = False
    for row in query.all():
        row.status = "Overdue"
        updated = True

    if updated:
        db.commit()


@router.get("")
def list_tasks(
    status: Optional[str] = Query(default=None),
    due_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = _normalize_role(current_user.role)
    # Allow staff roles, directors, and admins
    if not _is_staff_role(current_user.role) and role not in {"branch_director", "branch_admin", "super_admin", "super_ceo"}:
        raise HTTPException(status_code=403, detail="Access denied")

    _apply_overdue_flags(db, None if _is_global_executive_role(role) else current_user.branch_id)

    query = db.query(StaffTask)
    if _is_staff_role(current_user.role):
        query = query.filter(StaffTask.assigned_to == current_user.id)
    elif role in {"branch_director", "branch_admin"}:
        query = query.filter(StaffTask.branch_id == current_user.branch_id)

    if status:
        query = query.filter(StaffTask.status == _normalize_status(status))

    if due_date:
        try:
            target = datetime.strptime(due_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="due_date must be YYYY-MM-DD")
        query = query.filter(StaffTask.due_date.isnot(None))
        query = query.filter(StaffTask.due_date >= datetime.combine(target, datetime.min.time()))
        query = query.filter(StaffTask.due_date < datetime.combine(target, datetime.max.time()))

    rows = query.order_by(StaffTask.updated_at.desc(), StaffTask.id.desc()).all()
    return {"items": [_serialize_task(row) for row in rows]}


@router.post("")
def create_task(
    payload: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_director_like(current_user):
        raise HTTPException(status_code=403, detail="Only branch director/admin can create tasks")

    assigned_user = db.query(User).filter(User.id == payload.assigned_to, User.is_active == True).first()
    if not assigned_user:
        raise HTTPException(status_code=404, detail="Assigned staff user not found")

    if not _is_global_executive_role(current_user.role):
        if current_user.branch_id is None:
            raise HTTPException(status_code=400, detail="Your account has no branch association")
        if assigned_user.branch_id != current_user.branch_id:
            raise HTTPException(status_code=400, detail="Can only assign tasks to users in your branch")

    profile = _resolve_staff_profile(db, assigned_user.id, assigned_user.branch_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Staff profile not found for assigned user")

    branch_id = assigned_user.branch_id or current_user.branch_id
    if branch_id is None:
        raise HTTPException(status_code=400, detail="Unable to resolve branch for task")

    normalized_priority = _normalize_priority(payload.priority)

    task = StaffTask(
        branch_id=branch_id,
        staff_profile_id=profile.id,
        assigned_by=current_user.id,
        assigned_to=assigned_user.id,
        title=payload.title.strip(),
        task_name=payload.title.strip(),
        description=(payload.description or "").strip() or None,
        due_date=payload.due_date,
        deadline=payload.due_date,
        priority=normalized_priority,
        status="Pending",
    )
    db.add(task)
    db.flush()

    db.add(
        StaffNotification(
            staff_profile_id=profile.id,
            branch_id=branch_id,
            message=f"New task assigned: {task.title or task.task_name}",
            link="/staff/tasks",
        )
    )

    _ensure_branch_notifications_table(db)
    db.add(
        BranchNotification(
            branch_id=branch_id,
            type=BranchNotificationType.TASK_ASSIGNED,
            title="Task assignment confirmed",
            message=f"Task '{task.title or task.task_name}' assigned to {assigned_user.first_name} {assigned_user.last_name}.",
            related_entity_id=task.id,
            is_read=False,
        )
    )

    db.commit()
    db.refresh(task)
    return {"message": "Task created", "task": _serialize_task(task)}


@router.put("/{task_id}")
def update_task(
    task_id: int,
    payload: TaskUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_director_like(current_user):
        raise HTTPException(status_code=403, detail="Only branch director/admin can update tasks")

    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    _ensure_task_access(task, current_user)

    if payload.assigned_to is not None:
        assigned_user = db.query(User).filter(User.id == payload.assigned_to, User.is_active == True).first()
        if not assigned_user:
            raise HTTPException(status_code=404, detail="Assigned staff user not found")
        if not _is_global_executive_role(current_user.role) and assigned_user.branch_id != current_user.branch_id:
            raise HTTPException(status_code=400, detail="Can only reassign inside your branch")
        profile = _resolve_staff_profile(db, assigned_user.id, assigned_user.branch_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Staff profile not found for assigned user")
        task.assigned_to = assigned_user.id
        task.staff_profile_id = profile.id

    if payload.title is not None:
        task.title = payload.title.strip()
        task.task_name = payload.title.strip()

    if payload.description is not None:
        task.description = payload.description.strip() or None

    if payload.due_date is not None:
        task.due_date = payload.due_date
        task.deadline = payload.due_date

    if payload.priority is not None:
        task.priority = _normalize_priority(payload.priority)

    db.commit()
    db.refresh(task)
    return {"message": "Task updated", "task": _serialize_task(task)}


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_director_like(current_user):
        raise HTTPException(status_code=403, detail="Only branch director/admin can delete tasks")

    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    _ensure_task_access(task, current_user)

    if (task.status or "").strip().lower() == "completed":
        raise HTTPException(status_code=409, detail="Completed tasks cannot be deleted")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}


@router.put("/{task_id}/status")
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = _normalize_role(current_user.role)
    if not _is_staff_role(current_user.role) and role not in {"branch_director", "branch_admin", "super_admin", "super_ceo"}:
        raise HTTPException(status_code=403, detail="Access denied")

    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    _ensure_task_access(task, current_user)

    normalized = _normalize_status(payload.status)
    if _is_staff_role(current_user.role) and normalized not in {"In Progress", "Completed"}:
        raise HTTPException(status_code=400, detail="Staff can set only In Progress or Completed")

    task.status = normalized
    task.completed_at = datetime.utcnow() if normalized == "Completed" else None

    if normalized == "Completed" and task.assigned_by:
        director = db.query(User).filter(User.id == task.assigned_by).first()
        if director:
            db.add(
                DirectorNotification(
                    director_user_id=director.id,
                    branch_id=task.branch_id,
                    title="Task Completed",
                    message=f"Task '{task.title or task.task_name}' was marked completed.",
                    is_read=False,
                )
            )

    db.commit()
    db.refresh(task)
    return {"message": "Task status updated", "task": _serialize_task(task)}


@router.get("/{task_id}/comments")
def list_task_comments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    _ensure_task_access(task, current_user)

    rows = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.asc()).all()
    return {
        "items": [
            {
                "id": row.id,
                "task_id": row.task_id,
                "user_id": row.user_id,
                "message": row.message,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@router.post("/{task_id}/comments")
def create_task_comment(
    task_id: int,
    payload: TaskCommentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    _ensure_task_access(task, current_user)

    row = TaskComment(task_id=task.id, user_id=current_user.id, message=payload.message.strip())
    db.add(row)

    if task.assigned_by and task.assigned_by != current_user.id:
        db.add(
            DirectorNotification(
                director_user_id=task.assigned_by,
                branch_id=task.branch_id,
                title="Task Comment",
                message=f"New comment on task '{task.title or task.task_name}'.",
                is_read=False,
            )
        )

    if task.staff_profile_id:
        db.add(
            StaffNotification(
                staff_profile_id=task.staff_profile_id,
                branch_id=task.branch_id,
                message=f"New comment on task: {task.title or task.task_name}",
                link="/staff/tasks",
            )
        )

    db.commit()
    db.refresh(row)
    return {
        "message": "Comment added",
        "comment": {
            "id": row.id,
            "task_id": row.task_id,
            "user_id": row.user_id,
            "message": row.message,
            "created_at": row.created_at,
        },
    }


@router.get("/{task_id}/attachments")
def list_task_attachments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    _ensure_task_access(task, current_user)

    rows = db.query(TaskAttachment).filter(TaskAttachment.task_id == task_id).order_by(TaskAttachment.created_at.desc()).all()
    return {
        "items": [
            {
                "id": row.id,
                "task_id": row.task_id,
                "file_url": row.file_url,
                "uploaded_by": row.uploaded_by,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@router.post("/{task_id}/attachments")
def upload_task_attachment(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    _ensure_task_access(task, current_user)

    suffix = Path(file.filename or "attachment").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".pdf", ".webp"}:
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp, pdf are allowed")

    TASK_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"task_{task_id}_{secrets.token_hex(8)}{suffix}"
    destination = TASK_ATTACHMENTS_DIR / filename

    with destination.open("wb") as output:
        output.write(file.file.read())

    file_url = f"/api/files/staff/task_attachments/{filename}"
    row = TaskAttachment(task_id=task.id, file_url=file_url, uploaded_by=current_user.id)
    db.add(row)

    db.commit()
    db.refresh(row)
    return {
        "message": "Attachment uploaded",
        "attachment": {
            "id": row.id,
            "task_id": row.task_id,
            "file_url": row.file_url,
            "uploaded_by": row.uploaded_by,
            "created_at": row.created_at,
        },
    }
