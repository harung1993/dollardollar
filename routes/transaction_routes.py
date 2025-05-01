import json
from datetime import datetime

from flask import Blueprint, jsonify, render_template
from flask_login import current_user
from sqlalchemy import and_, or_

from models import (
    Account,
    Category,
    CategorySplit,
    Currency,
    Expense,
    Group,
    Settlement,
    Tag,
    User,
)
from services.helpers import get_base_currency
from services.wrappers import login_required_dev
from session_timeout import demo_time_limited
from tables import group_users

transaction_bp = Blueprint("transaction", __name__)


@transaction_bp.route("/get_transaction_details/<other_user_id>")
@login_required_dev
def get_transaction_details(other_user_id):
    """Fetch transaction details between current user and another user."""
    # Query expenses involving both users
    expenses = (
        Expense.query.filter(
            or_(
                and_(
                    Expense.user_id == current_user.id,
                    Expense.split_with.like(f"%{other_user_id}%"),
                ),
                and_(
                    Expense.user_id == other_user_id,
                    Expense.split_with.like(f"%{current_user.id}%"),
                ),
            )
        )
        .order_by(Expense.date.desc())
        .limit(20)
        .all()
    )

    # Query settlements between both users
    settlements = (
        Settlement.query.filter(
            or_(
                and_(
                    Settlement.payer_id == current_user.id,
                    Settlement.receiver_id == other_user_id,
                ),
                and_(
                    Settlement.payer_id == other_user_id,
                    Settlement.receiver_id == current_user.id,
                ),
            )
        )
        .order_by(Settlement.date.desc())
        .limit(20)
        .all()
    )

    # Prepare transaction details
    transactions = []

    # Add expenses
    for expense in expenses:
        splits = expense.calculate_splits()
        transactions.append(
            {
                "type": "expense",
                "date": expense.date.strftime("%Y-%m-%d"),
                "description": expense.description,
                "amount": expense.amount,
                "payer": splits["payer"]["name"],
                "split_method": expense.split_method,
            }
        )

    # Add settlements
    for settlement in settlements:
        transactions.extend(
            [
                {
                    "type": "settlement",
                    "date": settlement.date.strftime("%Y-%m-%d"),
                    "description": settlement.description,
                    "amount": settlement.amount,
                    "payer": User.query.get(settlement.payer_id).name,
                    "receiver": User.query.get(settlement.receiver_id).name,
                }
            ]
        )

    # Sort transactions by date, most recent first
    transactions.sort(key=lambda x: x["date"], reverse=True)

    return jsonify(transactions)


@transaction_bp.route("/transactions")
@login_required_dev
@demo_time_limited
def transactions():  # noqa: C901 PLR0912 PLR0915
    """Display all transactions with filtering capabilities."""
    # Fetch all expenses where the user is either the creator
    # or a split participant
    base_currency = get_base_currency()
    expenses = (
        Expense.query.filter(
            or_(
                Expense.user_id == current_user.id,
                Expense.split_with.like(f"%{current_user.id}%"),
            )
        )
        .order_by(Expense.date.desc())
        .all()
    )

    users = User.query.all()

    # Pre-calculate all expense splits to avoid repeated calculations
    expense_splits = {}
    for expense in expenses:
        expense_splits[expense.id] = expense.calculate_splits()

    # Calculate total expenses for current user (similar to dashboard calculation)
    now = datetime.now()
    current_year = now.year
    total_expenses = 0

    for expense in expenses:
        # Skip if not in current year
        if expense.date.year != current_year:
            continue

        splits = expense_splits[expense.id]

        if expense.paid_by == current_user.id:
            # If user paid, add their own portion
            total_expenses += splits["payer"]["amount"]

            # Also add what others owe them (the entire expense)
            for split in splits["splits"]:
                total_expenses += split["amount"]
        else:
            # If someone else paid, add only this user's portion
            for split in splits["splits"]:
                if split["email"] == current_user.id:
                    total_expenses += split["amount"]
                    break

    # Calculate current month total (similar to dashboard calculation)
    current_month_total = 0
    current_month = now.strftime("%Y-%m")

    for expense in expenses:
        # Skip if not in current month
        if expense.date.strftime("%Y-%m") != current_month:
            continue

        splits = expense_splits[expense.id]

        if expense.paid_by == current_user.id:
            # If user paid, add their own portion
            current_month_total += splits["payer"]["amount"]

            # Also add what others owe them (the entire expense)
            for split in splits["splits"]:
                current_month_total += split["amount"]
        else:
            # If someone else paid, add only this user's portion
            for split in splits["splits"]:
                if split["email"] == current_user.id:
                    current_month_total += split["amount"]
                    break

    # Calculate monthly totals for statistics
    monthly_totals = {}
    unique_cards = set()

    currencies = Currency.query.all()
    for expense in expenses:
        month_key = expense.date.strftime("%Y-%m")
        if month_key not in monthly_totals:
            monthly_totals[month_key] = {
                "total": 0.0,
                "by_card": {},
                "contributors": {},
            }

        # Add to monthly totals
        monthly_totals[month_key]["total"] += expense.amount

        # Add card to total
        if expense.card_used not in monthly_totals[month_key]["by_card"]:
            monthly_totals[month_key]["by_card"][expense.card_used] = 0
        monthly_totals[month_key]["by_card"][expense.card_used] += (
            expense.amount
        )

        # Track unique cards where current user paid
        if expense.paid_by == current_user.id:
            unique_cards.add(expense.card_used)

        # Add contributors' data
        splits = expense_splits[expense.id]

        # Add payer's portion
        if splits["payer"]["amount"] > 0:
            user_id = splits["payer"]["email"]
            if user_id not in monthly_totals[month_key]["contributors"]:
                monthly_totals[month_key]["contributors"][user_id] = 0
            monthly_totals[month_key]["contributors"][user_id] += splits[
                "payer"
            ]["amount"]

        # Add other contributors' portions
        for split in splits["splits"]:
            user_id = split["email"]
            if user_id not in monthly_totals[month_key]["contributors"]:
                monthly_totals[month_key]["contributors"][user_id] = 0
            monthly_totals[month_key]["contributors"][user_id] += split[
                "amount"
            ]

    return render_template(
        "transactions.html",
        expenses=expenses,
        expense_splits=expense_splits,
        monthly_totals=monthly_totals,
        total_expenses=total_expenses,
        current_month_total=current_month_total,
        unique_cards=unique_cards,
        users=users,
        base_currency=base_currency,
        currencies=currencies,
    )


@transaction_bp.route("/get_transaction_form_html")
@login_required_dev
def get_transaction_form_html():
    """Return the HTML for the add transaction form."""
    base_currency = get_base_currency()
    users = User.query.all()
    groups = (
        Group.query.join(group_users)
        .filter(group_users.c.user_id == current_user.id)
        .all()
    )
    categories = (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.name)
        .all()
    )
    currencies = Currency.query.all()
    tags = Tag.query.filter_by(user_id=current_user.id).all()  # Add tags
    return render_template(
        "partials/add_transaction_form.html",
        users=users,
        groups=groups,
        categories=categories,
        currencies=currencies,
        tags=tags,  # Pass tags to the template
        base_currency=base_currency,
    )


@transaction_bp.route("/get_expense_edit_form/<int:expense_id>")
@login_required_dev
def get_expense_edit_form(expense_id):
    """Return the HTML for editing an expense, including category splits data."""
    expense = Expense.query.get_or_404(expense_id)

    # Security check
    if expense.user_id != current_user.id and current_user.id not in (
        expense.split_with or ""
    ):
        return "Access denied", 403

    # Prepare category splits data if available
    category_splits_data = []
    if expense.has_category_splits:
        # Get all category splits for this expense
        splits = CategorySplit.query.filter_by(expense_id=expense.id).all()
        for split in splits:
            category_splits_data.extend(
                {"category_id": split.category_id, "amount": split.amount}
            )

    # Add category splits data to the expense object for the template
    expense.category_splits_data = (
        json.dumps(category_splits_data) if category_splits_data else ""
    )

    base_currency = get_base_currency()
    users = User.query.all()
    groups = (
        Group.query.join(group_users)
        .filter(group_users.c.user_id == current_user.id)
        .all()
    )
    categories = (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.name)
        .all()
    )
    currencies = Currency.query.all()

    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "partials/edit_transaction_form.html",
        expense=expense,
        users=users,
        groups=groups,
        categories=categories,
        currencies=currencies,
        accounts=accounts,
        user=current_user,
        base_currency=base_currency,
    )
