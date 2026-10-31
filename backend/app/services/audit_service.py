from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import User
from app.models.ceo import CeoAuditLog


def write_ceo_audit(
    db: Session,
    actor: User,
    request: Request,
    action: str,
    metadata: dict[str, Any],
    *,
    response_status: int = 200,
) -> CeoAuditLog:
    previous = db.query(CeoAuditLog).order_by(CeoAuditLog.id.desc()).first()
    previous_signature = previous.signature if previous else None
    signed_payload = {
        "action": action,
        "actor": actor.id,
        "endpoint": request.url.path,
        "metadata": metadata,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "previous": previous_signature,
    }
    row = CeoAuditLog(
        user_id=actor.id,
        action=action,
        http_method=request.method,
        endpoint=request.url.path,
        response_status=response_status,
        request_meta=metadata,
        previous_signature=previous_signature,
        signature=hashlib.sha256(
            json.dumps(signed_payload, sort_keys=True, default=str).encode()
        ).hexdigest(),
    )
    db.add(row)
    return row
