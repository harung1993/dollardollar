from datetime import datetime, timedelta
from datetime import timezone as tz
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from sqlalchemy import ForeignKey, String, literal, or_
from sqlalchemy.orm import (
    Mapped,
    backref,
    mapped_column,
    relationship,
)
from sqlalchemy.sql.elements import ColumnElement

from .base import Base

if TYPE_CHECKING:
    from models import Category, CategorySplit, Expense, User


class Budget(Base):
    """Store budget information."""

    __tablename__: ClassVar[str] = "budgets"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("users.id"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(100)
    )  # Optional custom name for the budget
    amount: Mapped[float] = mapped_column(nullable=False)
    period: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'weekly', 'monthly', 'yearly'
    include_subcategories: Mapped[bool] = mapped_column(default=True)
    start_date: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.now(tz.utc)
    )
    is_recurring: Mapped[bool] = mapped_column(default=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(tz.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now(tz.utc), onupdate=datetime.now(tz.utc)
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", backref=backref("budgets", lazy=True), default=None
    )
    category: Mapped[Optional["Category"]] = relationship(
        "Category", backref=backref("budgets", lazy=True), default=None
    )

    transaction_types: Mapped[str] = mapped_column(
        String(100), default="expense"
    )  # comma-separated list of types to include

    def get_current_period_dates(self):
        """Get start and end dates for the current budget period."""
        today: datetime = datetime.now(tz.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        if self.period == "weekly":
            # Start of the week (Monday)
            start_of_week: datetime = today - timedelta(days=today.weekday())
            end_of_week: datetime = start_of_week + timedelta(
                days=6, hours=23, minutes=59, seconds=59
            )
            return start_of_week, end_of_week

        if self.period == "monthly":
            # Start of the month
            start_of_month = today.replace(day=1)
            # End of the month
            if today.month == 12:
                end_of_month = today.replace(
                    year=today.year + 1, month=1, day=1
                ) - timedelta(seconds=1)
            else:
                end_of_month = today.replace(
                    month=today.month + 1, day=1
                ) - timedelta(seconds=1)
            return start_of_month, end_of_month

        if self.period == "yearly":
            # Start of the year
            start_of_year = today.replace(month=1, day=1)
            # End of the year
            end_of_year = today.replace(
                year=today.year + 1, month=1, day=1
            ) - timedelta(seconds=1)
            return start_of_year, end_of_year

        # Default to current day
        return today, today.replace(hour=23, minute=59, second=59)

    def calculate_spent_amount(self):
        """Calculate spent amount in this budget's category during the period."""
        start_date: datetime
        end_date: datetime
        start_date, end_date = self.get_current_period_dates()

        # Base query: find all expenses in the relevant date range for this user

        subcategories: list[Category] = []
        if self.include_subcategories:
            # If this is a parent category, include subcategories
            subcategories = Category.query.filter_by(
                parent_id=self.category_id
            ).all()
            subcategory_ids: list[int] = [subcat.id for subcat in subcategories]

            # Include the parent category itself and all subcategories
            category_filter: ColumnElement[bool] = or_(
                Expense.category_id == self.category_id,
                Expense.category_id.in_(subcategory_ids)
                if subcategory_ids
                else literal(False),
            )
        else:
            # Only include this specific category
            category_filter = Expense.category_id == self.category_id

        # Get all expenses that match our criteria
        expenses: list[Expense] = Expense.query.filter(
            Expense.user_id == self.user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            category_filter,
        ).all()

        # Calculate the total spent for these expenses
        total_spent = 0.0

        # Process each expense to calculate the user's portion
        for expense in expenses:
            # If the expense has category splits, we need a different approach
            if expense.has_category_splits:
                # Handle category splits separately
                continue

            # Get the split information for this expense
            splits: dict[str, Any] = expense.calculate_splits()

            # If the user is the payer and not in the splits, add their portion
            if expense.paid_by == self.user_id and (
                not expense.split_with
                or self.user_id not in expense.split_with.split(",")
            ):
                total_spent += splits["payer"]["amount"]
            else:
                # Check if the current user is in the splits
                for split in splits["splits"]:
                    if split["email"] == self.user_id:
                        total_spent += split["amount"]
                        break

        # Handle expenses with category splits
        if self.include_subcategories:
            category_ids: list[int] = [self.category_id] + [
                subcat.id for subcat in subcategories
            ]
        else:
            category_ids = [self.category_id]

        # Find all category splits for relevant categories
        category_splits = (
            CategorySplit.query.join(
                Expense, CategorySplit.expense_id == Expense.id
            )
            .filter(
                Expense.user_id == self.user_id,
                Expense.date >= start_date,
                Expense.date <= end_date,
                CategorySplit.category_id.in_(category_ids),
            )
            .all()
        )

        # Process each category split
        for cat_split in category_splits:
            expense = Expense.query.get(cat_split.expense_id)
            if not expense:
                continue

            # Get the split information for this expense
            splits = expense.calculate_splits()

            # Calculate the user's share of this category split
            if expense.paid_by == self.user_id and (
                not expense.split_with
                or self.user_id not in expense.split_with.split(",")
            ):
                # User is the payer and not in splits - add their portion
                if expense.amount > 0:
                    user_ratio = splits["payer"]["amount"] / expense.amount
                    total_spent += cat_split.amount * user_ratio
            else:
                # Check if the user is in the splits
                for split in splits["splits"]:
                    if split["email"] == self.user_id:
                        if expense.amount > 0:
                            user_ratio = split["amount"] / expense.amount
                            total_spent += cat_split.amount * user_ratio
                        break

        return total_spent

    def get_remaining_amount(self):
        """Calculate remaining budget amount."""
        return self.amount - self.calculate_spent_amount()

    def get_progress_percentage(self):
        """Return progress percentage."""
        spent = self.calculate_spent_amount()
        if self.amount <= 0:
            return 100  # Avoid division by zero
        percentage = (spent / self.amount) * 100
        return min(percentage, 100)  # Cap at 100%

    def get_status(self):
        """Return the budget status: 'under', 'approaching', 'over'."""
        percentage = self.get_progress_percentage()
        if percentage >= 100:
            return "over"
        if percentage >= 80:
            return "approaching"
        return "under"
