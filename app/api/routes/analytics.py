from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.task import AnalyticsDistributionItem
from app.services.task_service import TaskService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/task-distribution", response_model=list[AnalyticsDistributionItem])
async def task_distribution(db: AsyncSession = Depends(get_db), me=Depends(get_current_user)):
    service = TaskService(db)
    rows = await service.analytics_distribution(today=date.today())
    return [AnalyticsDistributionItem(**r) for r in rows]


@router.get("/overdue", response_model=list[AnalyticsDistributionItem])
async def overdue(db: AsyncSession = Depends(get_db), me=Depends(get_current_user)):
    service = TaskService(db)
    rows = await service.analytics_distribution(today=date.today())
    return [AnalyticsDistributionItem(**r) for r in rows]
