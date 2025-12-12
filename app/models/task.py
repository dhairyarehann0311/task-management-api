from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TaskPriority, TaskStatus, TaskUserRole


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), index=True, nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority), index=True, nullable=False
    )

    due_date: Mapped[date | None] = mapped_column(Date)

    # ---- Soft delete fields ----
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    archived_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )

    # ---- Ownership ----
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    parent_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )

    # ---- Relationships ----
    creator = relationship("User", foreign_keys=[created_by_user_id], lazy="joined")

    parent_task = relationship(
        "Task", remote_side=[id], back_populates="subtasks"
    )
    subtasks = relationship(
        "Task", back_populates="parent_task", cascade="all, delete-orphan"
    )

    user_links = relationship(
        "TaskUserLink", back_populates="task", cascade="all, delete-orphan"
    )
    tags = relationship(
        "TaskTagLink", back_populates="task", cascade="all, delete-orphan"
    )

    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    blocked_by = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        back_populates="depends_on_task",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_tasks_status_priority", "status", "priority"),
    )


class TaskUserLink(Base):
    __tablename__ = "task_user_links"
    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_task_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[TaskUserRole] = mapped_column(Enum(TaskUserRole), index=True)

    task = relationship("Task", back_populates="user_links")
    user = relationship("User", back_populates="task_links")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)


class TaskTagLink(Base):
    __tablename__ = "task_tag_links"
    __table_args__ = (UniqueConstraint("task_id", "tag_id", name="uq_task_tag"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), index=True)

    task = relationship("Task", back_populates="tags")
    tag = relationship("Tag")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_task_id", name="uq_dependency"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    depends_on_task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )

    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on_task = relationship("Task", foreign_keys=[depends_on_task_id], back_populates="blocked_by")
