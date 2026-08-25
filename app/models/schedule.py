import uuid
from datetime import datetime

# SQLAlchemy
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

# app
from app.models.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin



class Schedule(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "schedules"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(
        sa.String(255), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    end_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        sa.Index("ix_schedules_user_id_start_at", "user_id", "start_at"),
        sa.Index("ix_schedules_user_id_created_at", "user_id", "created_at")
    )