from datetime import datetime
from datetime import timezone as tz
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from models import User


class SimpleFinSettings(Base):
    """Stores SimpleFin connection settings for a user."""

    __tablename__ = "SimpleFin"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("users.id"), nullable=False, unique=True
    )
    access_url: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Encoded/encrypted access URL
    last_sync: Mapped[datetime] = mapped_column(nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    sync_frequency: Mapped[str] = mapped_column(
        String(20), default="daily"
    )  # 'daily', 'weekly', etc.
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now(tz.utc), onupdate=datetime.now(tz.utc)
    )
    temp_accounts: Mapped[Optional[str]] = mapped_column(default=None)
    # Relationship with User
    user: Mapped[Optional["User"]] = relationship(
        "User",
        backref=backref("SimpleFin", uselist=False, lazy=True),
        default=None,
    )

    def __repr__(self) -> str:
        """Return string representation of SimpleFin settings."""
        return f"<SimpleFin settings for user {self.user_id}>"
