from datetime import datetime
from datetime import timezone as tz
from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import (
    Mapped,
    backref,
    mapped_column,
    relationship,
)

from tables import expense_tags

from .base import Base

if TYPE_CHECKING:
    from models import Account, Currency, Tag, User


class Expense(Base):
    """Store expense information."""

    __tablename__: ClassVar[str] = "expenses"

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

    transaction_type: Mapped[str] = mapped_column(
        String(20), server_default="expense"
    )  # 'expense', 'income', 'transfer'

    split_value: Mapped[Optional[float]] = mapped_column(
        default=None
    )  # deprecated - kept for backward compatibility

    group_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("groups.id"), nullable=True, default=None
    )
    split_with: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )  # Comma-separated list of user IDs
    split_details: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None
    )  # JSON string storing custom split values for each user
    recurring_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recurring_expenses.id"), nullable=True, default=None
    )

    # Add these fields to your existing Expense class:
    currency_code: Mapped[Optional[str]] = mapped_column(
        String(3), ForeignKey("currencies.code"), nullable=True, default=None
    )
    original_amount: Mapped[Optional[float]] = mapped_column(
        nullable=True, default=None
    )  # Amount in original currency
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True, default=None
    )

    # imports
    account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("accounts.id", name="fk_expense_account"),
        nullable=True,
        default=None,
    )

    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary=expense_tags,
        lazy="subquery",
        backref=backref("expenses", lazy=True),
        default_factory=list,
    )

    currency: Mapped[Optional["Currency"]] = relationship(
        "Currency", backref=backref("expenses", lazy=True), default=None
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, default=None
    )  # For tracking external transaction IDs
    import_source: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default=None
    )  # 'csv', 'simplefin', 'manual'

    account: Mapped[Optional["Account"]] = relationship(
        "Account",
        foreign_keys=[account_id],
        backref=backref("expenses", lazy=True),
        default=None,
    )

    # For transfers, we need a destination account
    destination_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("accounts.id", name="fk_destination_account"),
        nullable=True,
        default=None,
    )
    destination_account: Mapped[Optional["Account"]] = relationship(
        "Account",
        foreign_keys=[destination_account_id],
        backref=backref("incoming_transfers", lazy=True),
        default=None,
    )

    # Add to Expense class:
    has_category_splits: Mapped[bool] = mapped_column(default=False)

    date: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.now(tz.utc)
    )

    @property
    def is_income(self) -> bool:
        """Return whether this is an income."""
        return self.transaction_type == "income"

    @property
    def is_transfer(self) -> bool:
        """Return whether this is a transfer."""
        return self.transaction_type == "transfer"

    @property
    def is_expense(self) -> bool:
        """Return whether this is an expense."""
        return (
            self.transaction_type == "expense" or self.transaction_type is None
        )

    def calculate_splits(self) -> dict[str, Any]:  # noqa: C901, PLR0912, PLR0915
        """Calculate the split for each person.

        :return: Dictionary containing payer and split information
        :rtype: dict
        """
        # Get the user who paid
        payer: User | None = User.query.filter_by(id=self.paid_by).first()
        if not payer:
            return {}
        payer = cast(User, payer)
        payer_name: str = payer.name if payer else "Unknown"
        payer_email: str = payer.id

        # Get all people this expense is split with
        split_with_ids = self.split_with.split(",") if self.split_with else []
        split_users = []

        for user_id in split_with_ids:
            user = User.query.filter_by(id=user_id.strip()).first()
            if user:
                split_users.append(
                    {"id": user.id, "name": user.name, "email": user.id}
                )

        # Handle case where original_amount is None by using amount
        original_amount = (
            self.original_amount
            if self.original_amount is not None
            else self.amount
        )

        # Set up result structure with both base and original currency
        result = {
            "payer": {
                "name": payer_name,
                "email": payer_email,
                "amount": 0,  # Base currency amount
                "original_amount": original_amount,  # Original amount
                "currency_code": self.currency_code,  # Original currency code
            },
            "splits": [],
        }

        # Parse split details if available
        split_details = {}
        if self.split_details:
            try:
                if isinstance(self.split_details, str):
                    import json

                    split_details = json.loads(self.split_details)
                elif isinstance(self.split_details, dict):
                    split_details = self.split_details
            except Exception as e:
                # Log the error or handle it as appropriate
                print(
                    f"Error parsing split_details for expense {self.id}: {str(e)}"
                )
                split_details = {}

        if self.split_method == "equal":
            # Count participants (include payer only if not already in splits)
            total_participants = len(split_users) + (
                1 if self.paid_by not in split_with_ids else 0
            )

            # Equal splits among all participants
            per_person = (
                self.amount / total_participants
                if total_participants > 0
                else 0
            )
            per_person_original = (
                original_amount / total_participants
                if total_participants > 0
                else 0
            )

            # Assign payer's portion (only if they're not already in the splits)
            if self.paid_by not in split_with_ids:
                result["payer"]["amount"] = per_person
            else:
                result["payer"]["amount"] = 0

            # Assign everyone else's portion
            for user in split_users:
                result["splits"].append(
                    {
                        "name": user["name"],
                        "email": user["email"],
                        "amount": per_person,
                        "original_amount": per_person_original,
                        "currency_code": self.currency_code,
                    }
                )

        elif self.split_method == "percentage":
            # Use per-user percentages if available in split_details
            if (
                split_details
                and isinstance(split_details, dict)
                and split_details.get("type") == "percentage"
            ):
                percentages = split_details.get("values", {})
                total_assigned = 0
                total_original_assigned = 0

                # Calculate payer's amount if specified
                payer_percent = float(percentages.get(self.paid_by, 0))
                payer_amount = (self.amount * payer_percent) / 100
                payer_original_amount = (original_amount * payer_percent) / 100

                result["payer"]["amount"] = (
                    payer_amount if self.paid_by not in split_with_ids else 0
                )
                total_assigned += (
                    payer_amount if self.paid_by not in split_with_ids else 0
                )
                total_original_assigned += (
                    payer_original_amount
                    if self.paid_by not in split_with_ids
                    else 0
                )

                # Calculate each user's portion based on their percentage
                for user in split_users:
                    user_percent = float(percentages.get(user["id"], 0))
                    user_amount = (self.amount * user_percent) / 100
                    user_original_amount = (
                        original_amount * user_percent
                    ) / 100

                    result["splits"].append(
                        {
                            "name": user["name"],
                            "email": user["email"],
                            "amount": user_amount,
                            "original_amount": user_original_amount,
                            "currency_code": self.currency_code,
                        }
                    )
                    total_assigned += user_amount
                    total_original_assigned += user_original_amount

                # Validate total (handle rounding errors)
                if abs(total_assigned - self.amount) > 0.01:
                    difference = self.amount - total_assigned
                    if result["splits"]:
                        result["splits"][-1]["amount"] += difference
                    elif result["payer"]["amount"] > 0:
                        result["payer"]["amount"] += difference

            else:
                # Backward compatibility mode
                payer_percentage = (
                    self.split_value if self.split_value is not None else 0
                )
                payer_amount = (self.amount * payer_percentage) / 100
                payer_original_amount = (
                    original_amount * payer_percentage
                ) / 100

                result["payer"]["amount"] = (
                    payer_amount if self.paid_by not in split_with_ids else 0
                )

                # Split remainder equally
                remaining = self.amount - result["payer"]["amount"]
                remaining_original = original_amount - payer_original_amount
                per_person = remaining / len(split_users) if split_users else 0
                per_person_original = (
                    remaining_original / len(split_users) if split_users else 0
                )

                for user in split_users:
                    result["splits"].append(
                        {
                            "name": user["name"],
                            "email": user["email"],
                            "amount": per_person,
                            "original_amount": per_person_original,
                            "currency_code": self.currency_code,
                        }
                    )

        elif self.split_method == "custom":
            # Use per-user custom amounts if available in split_details
            if (
                split_details
                and isinstance(split_details, dict)
                and split_details.get("type") in ["amount", "custom"]
            ):
                amounts = split_details.get("values", {})
                total_assigned = 0
                total_original_assigned = 0

                # Set payer's amount if specified
                payer_amount = float(amounts.get(self.paid_by, 0))
                # For original amount, scale by the same proportion
                payer_ratio = payer_amount / self.amount if self.amount else 0
                payer_original_amount = original_amount * payer_ratio

                result["payer"]["amount"] = (
                    payer_amount if self.paid_by not in split_with_ids else 0
                )
                total_assigned += (
                    payer_amount if self.paid_by not in split_with_ids else 0
                )

                # Set each user's amount
                for user in split_users:
                    user_amount = float(amounts.get(user["id"], 0))
                    # Scale original amount by same proportion
                    user_ratio = user_amount / self.amount if self.amount else 0
                    user_original_amount = original_amount * user_ratio

                    result["splits"].append(
                        {
                            "name": user["name"],
                            "email": user["email"],
                            "amount": user_amount,
                            "original_amount": user_original_amount,
                            "currency_code": self.currency_code,
                        }
                    )
                    total_assigned += user_amount

                # Validate total (handle rounding errors)
                if abs(total_assigned - self.amount) > 0.01:
                    difference = self.amount - total_assigned
                    if result["splits"]:
                        result["splits"][-1]["amount"] += difference
                    elif result["payer"]["amount"] > 0:
                        result["payer"]["amount"] += difference
            else:
                # Backward compatibility mode
                payer_amount = (
                    self.split_value if self.split_value is not None else 0
                )
                # Calculate the ratio of payer amount to total
                payer_ratio = payer_amount / self.amount if self.amount else 0
                payer_original_amount = original_amount * payer_ratio

                result["payer"]["amount"] = (
                    payer_amount if self.paid_by not in split_with_ids else 0
                )

                # Split remainder equally
                remaining = self.amount - result["payer"]["amount"]
                remaining_original = original_amount - payer_original_amount
                per_person = remaining / len(split_users) if split_users else 0
                per_person_original = (
                    remaining_original / len(split_users) if split_users else 0
                )

                for user in split_users:
                    result["splits"].append(
                        {
                            "name": user["name"],
                            "email": user["email"],
                            "amount": per_person,
                            "original_amount": per_person_original,
                            "currency_code": self.currency_code,
                        }
                    )

        return result
