import secrets
from datetime import datetime, timedelta
from datetime import timezone as tz
from typing import TYPE_CHECKING, ClassVar, Optional

from flask_login import UserMixin
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import (
    Mapped,
    backref,
    mapped_column,
    relationship,
)
from werkzeug.security import check_password_hash, generate_password_hash

from models import Group

from .base import Base

if TYPE_CHECKING:
    from models import Currency, Expense, Group


class User(UserMixin, Base):
    """Stores user information and settings."""

    __tablename__: ClassVar[str] = "users"

    id: Mapped[str] = mapped_column(
        String(120), primary_key=True
    )  # Using email as ID

    name: Mapped[str] = mapped_column(String(100))

    password_hash: Mapped[Optional[str]] = mapped_column(
        String(256), default=None
    )
    reset_token: Mapped[Optional[str]] = mapped_column(
        String(100), default=None
    )
    reset_token_expiry: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, default=None
    )
    expenses: Mapped[Optional["Expense"]] = relationship(
        "Expense", backref="user", lazy=True, default=None
    )
    default_currency_code: Mapped[Optional[str]] = mapped_column(
        String(3), ForeignKey("currencies.code"), default=None
    )
    default_currency: Mapped[Optional["Currency"]] = relationship(
        "Currency", backref=backref("users", lazy=True), default=None
    )
    created_groups: Mapped[Optional["Group"]] = relationship(
        "Group",
        backref="creator",
        lazy=True,
        foreign_keys=[Group.created_by],
        default=None,
    )
    # OIDC related fields
    oidc_id: Mapped[Optional[str]] = mapped_column(
        String(255), index=True, unique=True, default=None
    )
    oidc_provider: Mapped[Optional[str]] = mapped_column(
        String(50), default=None
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(default=None)

    user_color: Mapped[str] = mapped_column(String(7), default="#15803d")

    is_admin: Mapped[bool] = mapped_column(default=False)
    monthly_report_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(tz.utc))
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=True, default="UTC"
    )

    def set_password(self, password):
        """Hash password and store it."""
        self.password_hash = generate_password_hash(
            password, method="pbkdf2:sha256"
        )

    def check_password(self, password):
        """Check password against stored password hash."""
        # No password set
        if not self.password_hash:
            return False
        try:
            return check_password_hash(self.password_hash, password)
        except ValueError:
            return False

    def generate_reset_token(self):
        """Generate a password reset token that expires in 1 hour."""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.now(tz.utc) + timedelta(hours=1)
        return self.reset_token

    def verify_reset_token(self, token):
        """Verify if the provided token is valid and not expired."""
        if not self.reset_token or self.reset_token != token:
            return False
        return not (
            not self.reset_token_expiry
            or self.reset_token_expiry < datetime.now(tz.utc)
        )

    def clear_reset_token(self):
        """Clear the reset token and expiry after use."""
        self.reset_token = "None"
        self.reset_token_expiry = datetime.now(tz.utc)
