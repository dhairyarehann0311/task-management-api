from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.audit import AuditEventOut
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("", response_model=list[AuditEventOut])
async def my_timeline(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    me=Depends(get_current_user),
):
    svc = TimelineService(db)
    events = await svc.for_user(user_id=me.id, days=days)
    return events
