from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import delete

from app.models.enums import TaskUserRole
from app.models.task import Tag, Task, TaskDependency, TaskTagLink, TaskUserLink
from app.schemas.task import TaskFilter


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, task_id: int) -> Task | None:
        q = (
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.user_links),
                selectinload(Task.tags).selectinload(TaskTagLink.tag),
                selectinload(Task.dependencies),
            )
        )
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def create(self, task: Task) -> Task:
        self.db.add(task)
        await self.db.flush()
        return task

    async def delete(self, task: Task) -> None:
        await self.db.delete(task)

    async def upsert_tags(self, tag_names: Sequence[str]) -> list[Tag]:
        tags: list[Tag] = []
        for name in {t.strip().lower() for t in tag_names if t.strip()}:
            res = await self.db.execute(select(Tag).where(Tag.name == name))
            tag = res.scalar_one_or_none()
            if tag is None:
                tag = Tag(name=name)
                self.db.add(tag)
                await self.db.flush()
            tags.append(tag)
        return tags

    async def replace_task_users(
        self,
        task: Task,
        user_links: Sequence[tuple[int, TaskUserRole]],
    ) -> None:
        # Delete existing links explicitly
        await self.db.execute(
            delete(TaskUserLink).where(TaskUserLink.task_id == task.id)
        )

        # Insert new links
        for user_id, role in user_links:
            self.db.add(
                TaskUserLink(
                    task_id=task.id,
                    user_id=user_id,
                    role=role,
                )
            )


    async def replace_task_tags(self, task: Task, tags: Sequence[Tag]) -> None:
        await self.db.execute(
            delete(TaskTagLink).where(TaskTagLink.task_id == task.id)
        )

        for tag in tags:
            self.db.add(
                TaskTagLink(
                    task_id=task.id,
                    tag_id=tag.id,
                )
            )

    async def replace_dependencies(self, task: Task, depends_on_ids: Sequence[int]) -> None:
        task.dependencies.clear()
        await self.db.flush()
        for dep_id in set(depends_on_ids):
            if dep_id == task.id:
                continue
            task.dependencies.append(TaskDependency(depends_on_task_id=dep_id))

    async def filter_tasks(
        self,
        *,
        f: TaskFilter,
        accessible_task_ids_subq,
    ) -> tuple[list[Task], int]:
        conditions = []
        if not f.include_archived:
            conditions.append(Task.is_archived.is_(False))
        if f.status_in:
            conditions.append(Task.status.in_(f.status_in))
        if f.priority_in:
            conditions.append(Task.priority.in_(f.priority_in))
        if f.due_date_from:
            conditions.append(Task.due_date >= f.due_date_from)
        if f.due_date_to:
            conditions.append(Task.due_date <= f.due_date_to)
        if f.created_from:
            conditions.append(Task.created_at >= f.created_from)
        if f.created_to:
            conditions.append(Task.created_at <= f.created_to)

        # Assignee / collaborator filters via TaskUserLink
        if f.assignee_user_ids:
            conditions.append(
                Task.id.in_(
                    select(TaskUserLink.task_id).where(
                        and_(
                            TaskUserLink.role == TaskUserRole.ASSIGNEE,
                            TaskUserLink.user_id.in_(f.assignee_user_ids),
                        )
                    )
                )
            )
        if f.collaborator_user_ids:
            conditions.append(
                Task.id.in_(
                    select(TaskUserLink.task_id).where(
                        and_(
                            TaskUserLink.role == TaskUserRole.COLLABORATOR,
                            TaskUserLink.user_id.in_(f.collaborator_user_ids),
                        )
                    )
                )
            )
        if f.tag_names:
            tag_names = [t.strip().lower() for t in f.tag_names if t.strip()]
            if tag_names:
                conditions.append(
                    Task.id.in_(
                        select(TaskTagLink.task_id)
                        .join(Tag, Tag.id == TaskTagLink.tag_id)
                        .where(Tag.name.in_(tag_names))
                    )
                )

        combine = and_ if f.logic == "AND" else or_
        where_clause = combine(*conditions) if conditions else True

        base_q = (
            select(Task)
            .where(Task.id.in_(accessible_task_ids_subq))
            .where(where_clause)
            .options(
                selectinload(Task.user_links),
                selectinload(Task.tags).selectinload(TaskTagLink.tag),
                selectinload(Task.dependencies),
            )
            .order_by(Task.updated_at.desc())
        )

        count_q = select(func.count()).select_from(
            select(Task.id)
            .where(Task.id.in_(accessible_task_ids_subq))
            .where(where_clause)
            .subquery()
        )

        total = (await self.db.execute(count_q)).scalar_one()
        offset = (f.page - 1) * f.page_size
        res = await self.db.execute(base_q.offset(offset).limit(f.page_size))
        return list(res.scalars().all()), int(total)

    async def accessible_task_ids_for_user(self, user_id: int):
        # tasks created by user or where user is linked
        return (
            select(Task.id)
            .where(
                or_(
                    Task.created_by_user_id == user_id,
                    Task.id.in_(select(TaskUserLink.task_id).where(TaskUserLink.user_id == user_id)),
                )
            )
            .subquery()
        )

    async def overdue_open_counts_per_user(self, today: date):
        # open = not DONE + due_date < today + assignee grouping
        q = (
            select(
                TaskUserLink.user_id.label("user_id"),
                func.count().filter(Task.status != "DONE").label("open_tasks"),
                func.count()
                .filter(and_(Task.status != "DONE", Task.due_date.is_not(None), Task.due_date < today))
                .label("overdue_tasks"),
            )
            .join(Task, Task.id == TaskUserLink.task_id)
            .where(TaskUserLink.role == TaskUserRole.ASSIGNEE)
            .group_by(TaskUserLink.user_id)
        )
        res = await self.db.execute(q)
        return [dict(r._mapping) for r in res.all()]
