import uuid
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

# app
from app.enums import AiJobStatus, Intent
from app.models.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin



class AiJob(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "ai_jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    raw_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[AiJobStatus] = mapped_column(
        sa.Enum(AiJobStatus, native_enum=False, create_constraint=True, length=20),
        nullable=False,
        default=AiJobStatus.PENDING,
    )
    intent: Mapped[Intent | None] = mapped_column(
        sa.Enum(Intent, native_enum=False, create_constraint=True, length=20), nullable=True
    )
    result_ref_type: Mapped[str | None] = mapped_column(
        sa.String(50), nullable=True
    )
    result_ref_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, nullable=True
    )
    model_used: Mapped[str | None] = mapped_column(
        sa.String(100), nullable=True
    )
    error: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    __table_args__ = (
        sa.Index("ix_ai_jobs_user_id_created_at", "user_id", "created_at"),
        sa.Index("ix_ai_jobs_celery_task_id", "celery_task_id"),
    )