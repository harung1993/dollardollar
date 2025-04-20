from datetime import datetime
from datetime import timezone as tz
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import (
    Mapped,
    backref,
    mapped_column,
    relationship,
)

from models import Expense

from .base import Base

if TYPE_CHECKING:
    from models import Account, Category, Currency, Group, User


class RecurringExpense(Base):
    """Store recurring expense information."""

    __tablename__: ClassVar[str] = "recurring_expenses"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(nullable=False)
    card_used: Mapped[str] = mapped_column(String(150), nullable=False)
    split_method: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'equal', 'custom', 'percentage'

    paid_by: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("users.id"), nullable=False
    )

    # Recurring specific fields
    frequency: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'daily', 'weekly', 'monthly', 'yearly'
    start_date: Mapped[datetime] = mapped_column(nullable=False)

    group_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("groups.id"), default=None
    )
    split_with: Mapped[Optional[str]] = mapped_column(
        String(500), default=None
    )  # Comma-separated list of user IDs

    split_value: Mapped[Optional[float]] = mapped_column(default=None)
    split_details: Mapped[Optional[str]] = mapped_column(
        Text, default=None
    )  # JSON string

    end_date: Mapped[Optional[datetime]] = mapped_column(
        default=None
    )  # Optional end date
    last_created: Mapped[Optional[datetime]] = mapped_column(
        default=None
    )  # Track last created instance

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", backref=backref("recurring_expenses", lazy=True), default=None
    )
    group: Mapped[Optional["Group"]] = relationship(
        "Group", backref=backref("recurring_expenses", lazy=True), default=None
    )
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense",
        backref=backref("recurring_source", lazy=True),
        foreign_keys="Expense.recurring_id",
        default_factory=list,
    )
    currency_code: Mapped[Optional[str]] = mapped_column(
        String(3), ForeignKey("currencies.code"), default=None
    )
    original_amount: Mapped[Optional[float]] = mapped_column(
        default=None
    )  # Amount in original currency
    currency: Mapped[Optional["Currency"]] = relationship(
        "Currency",
        backref=backref("recurring_expenses", lazy=True),
        default=None,
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), default=None
    )
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        backref=backref("recurring_expenses", lazy=True),
        default=None,
    )
    account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("accounts.id", name="fk_recurring_account"),
        default=None,
    )
    account: Mapped[Optional["Account"]] = relationship(
        "Account",
        foreign_keys=[account_id],
        backref=backref("recurring_expenses", lazy=True),
        default=None,
    )

    # For transfers
    destination_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("accounts.id", name="fk_recurring_destination"), default=None
    )
    destination_account: Mapped[Optional["Account"]] = relationship(
        "Account",
        foreign_keys=[destination_account_id],
        backref=backref("recurring_incoming_transfers", lazy=True),
        default=None,
    )
    # Transaction type and account fields
    transaction_type: Mapped[str] = mapped_column(
        String(20), default="expense"
    )  # 'expense', 'income', 'transfer'
    active: Mapped[bool] = mapped_column(default=True)

    def create_expense_instance(self, for_date: datetime | None = None):
        """Create a single expense instance from this recurring template."""
        if for_date is None:
            for_date = datetime.now(tz.utc)
        # Copy data to create a new expense
        expense: Any = Expense(
            description=self.description,
            amount=self.amount,
            date=for_date,
            card_used=self.card_used,
            split_method=self.split_method,
            split_value=self.split_value,
            split_details=self.split_details,
            paid_by=self.paid_by,
            user_id=self.user_id,
            group_id=self.group_id,
            split_with=self.split_with,
            category_id=self.category_id,
            recurring_id=self.id,
            transaction_type=self.transaction_type,
            account_id=self.account_id,
            destination_account_id=self.destination_account_id
            if self.transaction_type == "transfer"
            else None,
            currency_code=self.currency_code,
            original_amount=self.original_amount,
        )

        # Update the last created date
        self.last_created = for_date

        return expense


class IgnoredRecurringPattern(Base):
    """Store patterns of recurring transactions, a user has chosen to ignore."""

    __tablename__: ClassVar[str] = "ignored_recurring_patterns"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("users.id"), nullable=False
    )
    pattern_key: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Unique pattern identifier
    description: Mapped[str] = mapped_column(
        String(200), nullable=False
    )  # For reference
    amount: Mapped[float] = mapped_column(nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    ignore_date: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.now(tz.utc)
    )

    # Relationship with User
    user: Mapped[Optional["User"]] = relationship(
        "User", backref=backref("ignored_patterns", lazy=True), default=None
    )

    # Ensure user can't ignore the same pattern twice
    __table_args__: tuple[UniqueConstraint] = (
        UniqueConstraint("user_id", "pattern_key"),
    )

    def __repr__(self) -> str:
        """Return string representation of ignored pattern information."""
        return (
            f"<IgnoredPattern: {self.description} ({self.amount}) - "
            f"{self.frequency}>"
        )
