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
    from models import Expense, User


class Category(Base):
    """Stores category information."""

    __tablename__: ClassVar[str] = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    user_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", backref=backref("categories", lazy=True), default=None
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), default=None
    )
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side=[id],
        backref=backref("subcategories", lazy=True),
        default=None,
    )
    expenses: Mapped[Optional["Expense"]] = relationship(
        "Expense", backref=backref("category", lazy=True), default=None
    )

    icon: Mapped[str] = mapped_column(
        String(50), default="fa-tag"
    )  # FontAwesome icon name
    color: Mapped[str] = mapped_column(String(20), default="#6c757d")

    is_system: Mapped[bool] = mapped_column(
        default=False
    )  # System categories can't be deleted
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(tz.utc))

    def __repr__(self) -> str:
        """Return string representation of category information."""
        return f"<Category: {self.name}>"


class CategorySplit(Base):
    """Stores category split information."""

    __tablename__: ClassVar[str] = "category_splits"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(nullable=False)
    description: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, default=None
    )

    # Relationships
    expense: Mapped[Optional["Expense"]] = relationship(
        "Expense",
        backref=backref("category_splits", cascade="all, delete-orphan"),
        default=None,
    )
    category: Mapped[Optional["Category"]] = relationship(
        "Category", backref=backref("splits", lazy=True), default=None
    )


class CategoryMapping(Base):
    """Stores information about a category mapping."""

    __tablename__: ClassVar[str] = "category_mappings"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("users.id"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", backref=backref("category_mappings", lazy=True), default=None
    )
    category: Mapped[Optional["Category"]] = relationship(
        "Category", backref=backref("mappings", lazy=True), default=None
    )

    is_regex: Mapped[bool] = mapped_column(
        default=False
    )  # Whether the keyword is a regex pattern
    priority: Mapped[int] = mapped_column(
        default=0
    )  # Higher priority mappings take precedence
    match_count: Mapped[int] = mapped_column(
        default=0
    )  # How many times this mapping has been used
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(tz.utc))

    def __repr__(self) -> str:
        """Return string representation of category mapping information."""
        return (
            f"<CategoryMapping: '{self.keyword}' → "
            f"{self.category.name if self.category else self.category_id}>"
        )
