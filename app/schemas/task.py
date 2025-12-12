from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.models.enums import TaskPriority, TaskStatus, TaskUserRole
from app.schemas.common import APIModel


class TaskUserLinkIn(APIModel):
    user_id: int
    role: TaskUserRole


class TaskCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None
    parent_task_id: int | None = None

    users: list[TaskUserLinkIn] = Field(default_factory=list) 
    tags: list[str] = Field(default_factory=list)  


class TaskUpdate(APIModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    is_archived: bool | None = None


class TaskOut(APIModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    is_archived: bool
    parent_task_id: int | None
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime

    assignees: list[int] = Field(default_factory=list)
    collaborators: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    dependencies: list[int] = Field(default_factory=list) 


class BulkTaskUpdateItem(APIModel):
    id: int
    patch: TaskUpdate


class BulkTaskUpdateRequest(APIModel):
    updates: list[BulkTaskUpdateItem]


class BulkTaskUpdateResult(APIModel):
    updated_ids: list[int]


class FilterLogic(str):
    AND = "AND"
    OR = "OR"


class TaskFilter(APIModel):
    logic: Literal["AND", "OR"] = "AND"
    status_in: list[TaskStatus] | None = None
    priority_in: list[TaskPriority] | None = None
    assignee_user_ids: list[int] | None = None
    collaborator_user_ids: list[int] | None = None
    tag_names: list[str] | None = None
    due_date_from: date | None = None
    due_date_to: date | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    include_archived: bool = False

    page: int = 1
    page_size: int = Field(default=20, ge=1, le=100)


class TaskFilterResponse(APIModel):
    items: list[TaskOut]
    page: int
    page_size: int
    total: int


class DependencyUpsert(APIModel):
    depends_on_task_ids: list[int]


class AnalyticsDistributionItem(APIModel):
    user_id: int
    open_tasks: int
    overdue_tasks: int
