from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, event: AuditEvent) -> AuditEvent:
        self.db.add(event)
        await self.db.flush()
        return event

    async def timeline_for_user(self, *, user_id: int, days: int) -> list[AuditEvent]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        q = (
            select(AuditEvent)
            .where(and_(AuditEvent.actor_user_id == user_id, AuditEvent.created_at >= since))
            .order_by(AuditEvent.created_at.desc())
        )
        res = await self.db.execute(q)
        return list(res.scalars().all())
