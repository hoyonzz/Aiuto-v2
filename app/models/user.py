from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDPrimaryKeyMixin, TimeStampMixin




class User(UUIDPrimaryKeyMixin, TimeStampMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255)
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
