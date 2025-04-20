from datetime import datetime
from datetime import timezone as tz
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import (
    Mapped,
    backref,
    mapped_column,
    relationship,
)

from .base import Base

if TYPE_CHECKING:
    from models import User


class Tag(Base):
    """Store tag information."""

    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("users.id"), nullable=False
    )

    # Relationship
    user: Mapped["User"] = relationship(
        "User", backref=backref("tags", lazy=True)
    )

    color: Mapped[str] = mapped_column(
        String(20), default="#6c757d"
    )  # Default color gray

    created_at: Mapped[datetime] = mapped_column(default=datetime.now(tz.utc))
