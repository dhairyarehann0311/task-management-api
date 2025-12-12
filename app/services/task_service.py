from __future__ import annotations

from datetime import date
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.enums import TaskUserRole, UserRole
from app.models.task import Task
from app.repositories.audit_repo import AuditRepository
from app.repositories.task_repo import TaskRepository
from app.repositories.user_repo import UserRepository
from app.schemas.task import TaskCreate, TaskFilter, TaskUpdate


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tasks = TaskRepository(db)
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)

    async def _require_task(self, task_id: int) -> Task:
        task = await self.tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @staticmethod
    def _is_admin(role: UserRole) -> bool:
        return role == UserRole.ADMIN

    @staticmethod
    def _is_manager(role: UserRole) -> bool:
        return role in (UserRole.ADMIN, UserRole.MANAGER)

    async def _can_view(self, *, task: Task, user_id: int, role: UserRole) -> bool:
        if self._is_admin(role):
            return True
        if task.created_by_user_id == user_id:
            return True
        return any(link.user_id == user_id for link in task.user_links)

    async def _can_modify(self, *, task: Task, user_id: int, role: UserRole) -> bool:
        if self._is_admin(role):
            return True
        if self._is_manager(role):
            return True
        return task.created_by_user_id == user_id

    async def get_task(self, *, task_id: int, user_id: int, role: UserRole) -> Task:
        task = await self._require_task(task_id)
        if not await self._can_view(task=task, user_id=user_id, role=role):
            raise HTTPException(status_code=403, detail="Not allowed")
        return task

    async def create_task(self, *, data: TaskCreate, user_id: int) -> Task:
        # validate parent task if any
        if data.parent_task_id is not None:
            _ = await self._require_task(data.parent_task_id)

        task = Task(
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            due_date=data.due_date,
            parent_task_id=data.parent_task_id,
            created_by_user_id=user_id,
        )
        await self.tasks.create(task)

        # user links
        links: list[tuple[int, TaskUserRole]] = [(u.user_id, u.role) for u in data.users]
        # validate user ids exist
        for uid, _r in links:
            if not await self.users.get_by_id(uid):
                raise HTTPException(status_code=400, detail=f"User not found: {uid}")
        await self.tasks.replace_task_users(task, links)

        # tags
        tags = await self.tasks.upsert_tags(data.tags)
        await self.tasks.replace_task_tags(task, tags)

        await self.audit.add(
            AuditEvent(
                actor_user_id=user_id,
                entity_type="TASK",
                entity_id=task.id,
                action="CREATED",
                details=f"title={task.title}",
            )
        )
        return await self.tasks.get(task.id)  # reload with relations

    async def update_task(self, *, task_id: int, patch: TaskUpdate, user_id: int, role: UserRole) -> Task:
        task = await self._require_task(task_id)
        if not await self._can_modify(task=task, user_id=user_id, role=role):
            raise HTTPException(status_code=403, detail="Not allowed")

        changed = False
        for field, value in patch.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
            changed = True

        if not changed:
            return task

        await self.audit.add(
            AuditEvent(actor_user_id=user_id, entity_type="TASK", entity_id=task.id, action="UPDATED")
        )
        await self.db.flush()
        return await self.tasks.get(task.id)

    async def delete_task(self, *, task_id: int, user_id: int, role: UserRole) -> None:
        task = await self._require_task(task_id)
        if role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only ADMIN can delete tasks")

        await self.tasks.delete(task)
        await self.audit.add(
            AuditEvent(actor_user_id=user_id, entity_type="TASK", entity_id=task_id, action="DELETED")
        )

    async def bulk_update(self, *, updates: Iterable[tuple[int, TaskUpdate]], user_id: int, role: UserRole) -> list[int]:
        updated_ids: list[int] = []
        for task_id, patch in updates:
            task = await self._require_task(task_id)
            if not await self._can_modify(task=task, user_id=user_id, role=role):
                raise HTTPException(status_code=403, detail=f"Not allowed to update task {task_id}")
            for field, value in patch.model_dump(exclude_unset=True).items():
                setattr(task, field, value)
            updated_ids.append(task_id)

        await self.audit.add(
            AuditEvent(actor_user_id=user_id, entity_type="TASK", entity_id=0, action="BULK_UPDATED",
                      details=f"count={len(updated_ids)}")
        )
        return updated_ids

    async def filter_tasks(self, *, f: TaskFilter, user_id: int, role: UserRole):
        # Admin can access all tasks, others only accessible ones
        if self._is_admin(role):
            accessible = (await self.db.execute(
                # subquery of all task ids
                __import__("sqlalchemy").select(__import__("app.models.task", fromlist=["Task"]).Task.id).subquery()
            )).scalar_one_or_none()
        accessible_subq = (
            (await self.tasks.accessible_task_ids_for_user(user_id))
            if not self._is_admin(role)
            else __import__("sqlalchemy").select(__import__("app.models.task", fromlist=["Task"]).Task.id).subquery()
        )
        return await self.tasks.filter_tasks(f=f, accessible_task_ids_subq=accessible_subq)

    async def set_dependencies(self, *, task_id: int, depends_on_ids: list[int], user_id: int, role: UserRole) -> Task:
        task = await self._require_task(task_id)
        if not await self._can_modify(task=task, user_id=user_id, role=role):
            raise HTTPException(status_code=403, detail="Not allowed")

        # validate dependency tasks exist
        for dep_id in depends_on_ids:
            _ = await self._require_task(dep_id)

        for dep_id in depends_on_ids:
            dep_task = await self._require_task(dep_id)
            if any(d.depends_on_task_id == task_id for d in dep_task.dependencies):
                raise HTTPException(status_code=400, detail="Dependency cycle detected (1-hop)")

        await self.tasks.replace_dependencies(task, depends_on_ids)
        await self.audit.add(
            AuditEvent(
                actor_user_id=user_id,
                entity_type="TASK",
                entity_id=task.id,
                action="DEPENDENCIES_UPDATED",
                details=f"depends_on={depends_on_ids}",
            )
        )
        await self.db.flush()
        return await self.tasks.get(task.id)

    async def analytics_distribution(self, *, today: date):
        return await self.tasks.overdue_open_counts_per_user(today=today)
    
    from datetime import datetime, timezone

async def archive_task(self, *, task_id: int, user_id: int, role: UserRole) -> Task:
    task = await self._require_task(task_id)

    if not await self._can_modify(task=task, user_id=user_id, role=role):
        raise HTTPException(status_code=403, detail="Not allowed")

    # Enforce dependency rule
    if task.blocked_by:
        raise HTTPException(
            status_code=400,
            detail="Cannot archive task while other tasks depend on it",
        )

    task.is_archived = True
    task.archived_at = datetime.now(timezone.utc)
    task.archived_by_user_id = user_id

    await self.audit.add(
        AuditEvent(
            actor_user_id=user_id,
            entity_type="TASK",
            entity_id=task.id,
            action="ARCHIVED",
        )
    )

    await self.db.flush()
    return task

