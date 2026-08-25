import uuid
from datetime import date

# SQLAlchemy
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

# app
from app.enums import TaskStatus
from app.models.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin



class Task(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "tasks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    due_date: Mapped[date | None] = mapped_column(
        sa.Date, nullable=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        sa.Enum(TaskStatus, native_enum=False, length=20),
        nullable=False,
        default=TaskStatus.TODO,
    )
    
    __table_args__ = (
        sa.Index("ix_tasks_user_id_due_date", "user_id", "due_date"),
        sa.Index("ix_tasks_user_id_created_at", "user_id", "created_at")
    )
