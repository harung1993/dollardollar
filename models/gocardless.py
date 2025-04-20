from datetime import datetime as dt
from datetime import timezone as tz
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    backref,
    mapped_column,
    relationship,
)

from .base import Base

if TYPE_CHECKING:
    from models import User


class GoCardlessSettings(Base):
    """Stores GoCardless connection settings for a user."""

    __tablename__ = "GoCardless"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("users.id"), nullable=False, unique=True
    )
    access_token: Mapped[Text] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)

    last_sync: Mapped[dt] = mapped_column(nullable=True)

    temp_accounts: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationship with User
    user: Mapped["User"] = relationship(
        "User", backref=backref("GoCardless", uselist=False, lazy=True)
    )

    access_token_expiration: Mapped[dt] = mapped_column(default=dt.now(tz.utc))
    refresh_token_expiration: Mapped[dt] = mapped_column(default=dt.now(tz.utc))
    enabled: Mapped[bool] = mapped_column(default=True)
    sync_frequency: Mapped[str] = mapped_column(
        String(20), default="daily"
    )  # 'daily', 'weekly', etc.
    created_at: Mapped[dt] = mapped_column(default=dt.now(tz.utc))
    updated_at: Mapped[dt] = mapped_column(
        default=dt.now(tz.utc),
        onupdate=dt.now(tz.utc),
    )

    def __repr__(self):
        """Return string representation of the GoCardless settings."""
        return f"<GoCardless settings for user {self.user_id}>"
