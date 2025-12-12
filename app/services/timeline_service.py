from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repo import AuditRepository
from app.schemas.audit import AuditEventOut


class TimelineService:
    def __init__(self, db: AsyncSession):
        self.audit = AuditRepository(db)

    async def for_user(self, *, user_id: int, days: int) -> list[AuditEventOut]:
        events = await self.audit.timeline_for_user(user_id=user_id, days=days)
        return [AuditEventOut.model_validate(e) for e in events]
