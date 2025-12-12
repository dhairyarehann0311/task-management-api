from __future__ import annotations

from datetime import datetime

from app.schemas.common import APIModel


class AuditEventOut(APIModel):
    id: int
    actor_user_id: int
    entity_type: str
    entity_id: int
    action: str
    details: str | None
    created_at: datetime
