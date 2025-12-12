from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import UserRole
from app.schemas.task import (
    BulkTaskUpdateRequest,
    BulkTaskUpdateResult,
    DependencyUpsert,
    TaskCreate,
    TaskFilter,
    TaskFilterResponse,
    TaskOut,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def to_task_out(task) -> TaskOut:
    assignees = [l.user_id for l in task.user_links if l.role.value == "ASSIGNEE"]
    collabs = [l.user_id for l in task.user_links if l.role.value == "COLLABORATOR"]
    tags = [tl.tag.name for tl in task.tags]
    deps = [d.depends_on_task_id for d in task.dependencies]
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        is_archived=task.is_archived,
        parent_task_id=task.parent_task_id,
        created_by_user_id=task.created_by_user_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        assignees=assignees,
        collaborators=collabs,
        tags=tags,
        dependencies=deps,
    )

@router.patch("/bulk", response_model=BulkTaskUpdateResult)
async def bulk_update(
    payload: BulkTaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
    me=Depends(get_current_user),
):
    service = TaskService(db)
    updated_ids = await service.bulk_update(
        updates=[(u.id, u.patch) for u in payload.updates],
        user_id=me.id,
        role=me.role,
    )
    await db.commit()
    return BulkTaskUpdateResult(updated_ids=updated_ids)


@router.post("/filter", response_model=TaskFilterResponse)
async def filter_tasks(
    f: TaskFilter,
    db: AsyncSession = Depends(get_db),
    me=Depends(get_current_user),
):
    service = TaskService(db)
    tasks, total = await service.tasks.filter_tasks(
        f=f,
        accessible_task_ids_subq=(
            await service.tasks.accessible_task_ids_for_user(me.id)
            if me.role != UserRole.ADMIN
            else __import__("sqlalchemy")
            .select(__import__("app.models.task", fromlist=["Task"]).Task.id)
            .subquery()
        ),
    )
    return TaskFilterResponse(
        items=[to_task_out(t) for t in tasks],
        page=f.page,
        page_size=f.page_size,
        total=total,
    )


@router.post("", response_model=TaskOut)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    me=Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.create_task(data=payload, user_id=me.id)
    await db.commit()
    return to_task_out(task)

@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    me=Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.get_task(task_id=task_id, user_id=me.id, role=me.role)
    return to_task_out(task)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    patch: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    me=Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.update_task(task_id=task_id, patch=patch, user_id=me.id, role=me.role)
    await db.commit()
    return to_task_out(task)


@router.patch("/{task_id}/archive", response_model=TaskOut)
async def archive_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    me=Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.archive_task(
        task_id=task_id,
        user_id=me.id,
        role=me.role,
    )
    await db.commit()
    return to_task_out(task)


@router.post("/{task_id}/dependencies", response_model=TaskOut)
async def set_dependencies(
    task_id: int,
    payload: DependencyUpsert,
    db: AsyncSession = Depends(get_db),
    me=Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.set_dependencies(
        task_id=task_id,
        depends_on_ids=payload.depends_on_task_ids,
        user_id=me.id,
        role=me.role,
    )
    await db.commit()
    return to_task_out(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    me=Depends(get_current_user),
):
    service = TaskService(db)
    await service.delete_task(task_id=task_id, user_id=me.id, role=me.role)
    await db.commit()
    return {"deleted": True}
