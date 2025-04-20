from datetime import datetime
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
    from models import Currency, User


class Account(Base):
    """Store account information."""

    __tablename__: ClassVar[str] = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # checking, savings, credit, etc.
    institution: Mapped[str] = mapped_column(String(100), nullable=True)
    user_id: Mapped[str] = mapped_column(
        String(120),
        ForeignKey("users.id", name="fk_account_user"),
        nullable=False,
    )

    currency_code: Mapped[Optional[str]] = mapped_column(
        String(3),
        ForeignKey("currencies.code", name="fk_account_currency"),
        default=None,
    )

    last_sync: Mapped[Optional[datetime]] = mapped_column(default=None)
    import_source: Mapped[Optional[str]] = mapped_column(
        String(50), default=None
    )
    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", backref=backref("accounts", lazy=True), default=None
    )

    currency: Mapped[Optional["Currency"]] = relationship(
        "Currency", backref=backref("accounts", lazy=True), default=None
    )

    external_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, default=None
    )
    status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, default=None
    )  # Add this line too for 'active'/'inactive' status

    balance: Mapped[float] = mapped_column(default=0.0)

    def __repr__(self) -> str:
        """Return string representation of account information."""
        return f"<Account {self.name} ({self.type})>"
