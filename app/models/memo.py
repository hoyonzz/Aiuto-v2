import uuid

# SQLAlchemy
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

# app
from app.models.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin



class Memo(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "memos"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(
        sa.Text, nullable=False
    )

    __table_args__ = (
        sa.Index("ix_memos_user_id_created_at", "user_id", "created_at"),
    )