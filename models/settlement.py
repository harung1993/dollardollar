from datetime import datetime
from datetime import timezone as tz
from typing import TYPE_CHECKING, ClassVar, Optional

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


class Settlement(Base):
    """Stores settlement information."""

    __tablename__: ClassVar[str] = "settlements"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    payer_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("users.id"), nullable=False
    )
    receiver_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("users.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(nullable=False)

    # Relationships
    payer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[payer_id],
        backref=backref("settlements_paid", lazy=True),
        default=None,
    )
    receiver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[receiver_id],
        backref=backref("settlements_received", lazy=True),
        default=None,
    )

    date: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.now(tz.utc)
    )
    description: Mapped[str] = mapped_column(
        String(200), nullable=True, default="Settlement"
    )
