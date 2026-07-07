from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.utils.auth_system import get_current_user

router = APIRouter()


class ActivityLogResponse(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    branch_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int]
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


@router.get("/activity-logs/", response_model=List[ActivityLogResponse])
def list_logs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type, e.g. branch or asset"),
    entity_id: Optional[int] = Query(None, description="Filter by entity id"),
    branch_id: Optional[int] = Query(None, description="Filter by branch id"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admin can view activity logs")

    query = db.query(ActivityLog)
    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(ActivityLog.entity_id == entity_id)
    if branch_id:
        query = query.filter(ActivityLog.branch_id == branch_id)

    logs = query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()
    return [
        ActivityLogResponse(
            id=log.id,
            user_id=log.user_id,
            username=log.user.username if log.user else None,
            branch_id=log.branch_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            description=log.description,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            timestamp=log.timestamp,
        )
        for log in logs
    ]
