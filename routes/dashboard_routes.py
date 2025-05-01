from datetime import datetime

from flask import Blueprint, render_template
from flask_login import current_user
from sqlalchemy import or_

from models import Category, Currency, Expense, Group, User
from services.helpers import (
    calculate_asset_debt_trends,
    calculate_balances,
    get_base_currency,
    get_budget_summary,
    get_category_spending,
)
from services.wrappers import login_required_dev
from session_timeout import demo_time_limited
from tables import group_users

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required_dev
@demo_time_limited
def dashboard():
    now = datetime.now()
    base_currency = get_base_currency()
    # Fetch all expenses where the user is either
    # the creator or a split participant
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
    groups = (
        Group.query.join(group_users)
        .filter(group_users.c.user_id == current_user.id)
        .all()
    )

    # Pre-calculate expense splits to avoid repeated calculations in template
    expense_splits = {}
    for expense in expenses:
        expense_splits[expense.id] = expense.calculate_splits()

    # Calculate monthly totals with contributors
    monthly_totals = {}
    if expenses:
        for expense in expenses:
            month_key = expense.date.strftime("%Y-%m")
            if month_key not in monthly_totals:
                monthly_totals[month_key] = {
                    "total": 0.0,
                    "by_card": {},
                    "contributors": {},
                    "by_account": {},  # New: track by account
                }

            # Add to total - MODIFIED: Only add expenses, not income or transfers
            if (
                not hasattr(expense, "transaction_type")
                or expense.transaction_type == "expense"
            ):
                monthly_totals[month_key]["total"] += expense.amount

                # Add to card totals
                if (
                    expense.card_used
                    not in monthly_totals[month_key]["by_card"]
                ):
                    monthly_totals[month_key]["by_card"][expense.card_used] = 0
                monthly_totals[month_key]["by_card"][expense.card_used] += (
                    expense.amount
                )

                # Add to account totals if available
                if hasattr(expense, "account") and expense.account:
                    account_name = expense.account.name
                    if (
                        account_name
                        not in monthly_totals[month_key]["by_account"]
                    ):
                        monthly_totals[month_key]["by_account"][
                            account_name
                        ] = 0
                    monthly_totals[month_key]["by_account"][account_name] += (
                        expense.amount
                    )

                # Calculate splits and add to contributors
                splits = expense_splits[expense.id]

                # Add payer's portion
                if splits["payer"]["amount"] > 0:
                    payer_email = splits["payer"]["email"]
                    if (
                        payer_email
                        not in monthly_totals[month_key]["contributors"]
                    ):
                        monthly_totals[month_key]["contributors"][
                            payer_email
                        ] = 0
                    monthly_totals[month_key]["contributors"][payer_email] += (
                        splits["payer"]["amount"]
                    )

                # Add other contributors' portions
                for split in splits["splits"]:
                    if (
                        split["email"]
                        not in monthly_totals[month_key]["contributors"]
                    ):
                        monthly_totals[month_key]["contributors"][
                            split["email"]
                        ] = 0
                    monthly_totals[month_key]["contributors"][
                        split["email"]
                    ] += split["amount"]

    # Calculate total expenses for current user
    # (only their portions for the current year)
    current_year = now.year
    total_expenses = 0
    total_expenses_only = 0  # NEW: For expenses only
    # Add these calculations for income and transfers
    total_income = 0
    total_transfers = 0
    monthly_labels = []
    monthly_amounts = []

    # Sort monthly totals to ensure chronological order
    sorted_monthly_totals = sorted(monthly_totals.items(), key=lambda x: x[0])

    for month, data in sorted_monthly_totals:
        monthly_labels.append(month)
        monthly_amounts.append(data["total"])
        # Calculate totals for each transaction type
    for expense in expenses:
        if hasattr(expense, "transaction_type"):
            if expense.transaction_type == "income":
                total_income += expense.amount
            elif expense.transaction_type == "transfer":
                total_transfers += expense.amount

    # Calculate derived metrics
    net_cash_flow = total_income - total_expenses_only

    # Calculate savings rate if income is not zero
    savings_rate = net_cash_flow / total_income * 100 if total_income > 0 else 0
    for expense in expenses:
        # Skip if not in current year
        if expense.date.year != current_year:
            continue

        # NEW: Check if it's an expense
        is_expense = (
            not hasattr(expense, "transaction_type")
            or expense.transaction_type == "expense"
        )

        splits = expense_splits[expense.id]

        if expense.paid_by == current_user.id:
            # If user paid, add their own portion
            total_expenses += splits["payer"]["amount"]
            if is_expense:
                total_expenses_only += splits["payer"]["amount"]

            # Also add what others owe them (the entire expense)
            for split in splits["splits"]:
                total_expenses += split["amount"]
                if is_expense:
                    total_expenses_only += split["amount"]
        else:
            # If someone else paid, add only this user's portion
            for split in splits["splits"]:
                if split["email"] == current_user.id:
                    total_expenses += split["amount"]
                    if is_expense:
                        total_expenses_only += split["amount"]
                    break

    # Calculate current month's total for the current user
    current_month_total = 0
    current_month_expenses_only = 0  # NEW: For expenses only
    current_month = now.strftime("%Y-%m")

    for expense in expenses:
        # Skip if not in current month
        if expense.date.strftime("%Y-%m") != current_month:
            continue

        # NEW: Check if it's an expense
        is_expense = (
            not hasattr(expense, "transaction_type")
            or expense.transaction_type == "expense"
        )

        splits = expense_splits[expense.id]

        if expense.paid_by == current_user.id:
            # If user paid, add their own portion
            current_month_total += splits["payer"]["amount"]
            if is_expense:
                current_month_expenses_only += splits["payer"]["amount"]

            # Also add what others owe them (the entire expense)
            for split in splits["splits"]:
                current_month_total += split["amount"]
                if is_expense:
                    current_month_expenses_only += split["amount"]
        else:
            # If someone else paid, add only this user's portion
            for split in splits["splits"]:
                if split["email"] == current_user.id:
                    current_month_total += split["amount"]
                    if is_expense:
                        current_month_expenses_only += split["amount"]
                    break

    # Get unique cards (only where current user paid)
    unique_cards = {
        expense.card_used
        for expense in expenses
        if expense.paid_by == current_user.id
    }

    # Calculate balances using the settlements method
    balances = calculate_balances(current_user.id)

    # Sort into "you owe" and "you are owed" categories
    you_owe = []
    you_are_owed = []
    net_balance = 0

    for balance in balances:
        if balance["amount"] < 0:
            # Current user owes money
            you_owe.append(
                {
                    "id": balance["user_id"],
                    "name": balance["name"],
                    "email": balance["email"],
                    "amount": abs(balance["amount"]),
                }
            )
            net_balance -= abs(balance["amount"])
        elif balance["amount"] > 0:
            # Current user is owed money
            you_are_owed.append(
                {
                    "id": balance["user_id"],
                    "name": balance["name"],
                    "email": balance["email"],
                    "amount": balance["amount"],
                }
            )
            net_balance += balance["amount"]

    # Create IOU data in the format the dashboard template expects
    iou_data = {
        "owes_me": {
            user["id"]: {"name": user["name"], "amount": user["amount"]}
            for user in you_are_owed
        },
        "i_owe": {
            user["id"]: {"name": user["name"], "amount": user["amount"]}
            for user in you_owe
        },
        "net_balance": net_balance,
    }

    budget_summary = get_budget_summary()

    categories = (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.name)
        .all()
    )
    currencies = Currency.query.all()

    # Calculate asset and debt trends
    asset_debt_trends = calculate_asset_debt_trends(current_user)

    base_currency = get_base_currency()

    return render_template(
        "dashboard.html",
        expenses=expenses,
        expense_splits=expense_splits,
        top_categories=get_category_spending(expenses, expense_splits),
        monthly_totals=monthly_totals,
        total_expenses=total_expenses,
        total_expenses_only=total_expenses_only,  # NEW: For expenses only
        current_month_total=current_month_total,
        current_month_expenses_only=current_month_expenses_only,  # NEW: For expenses only # noqa: E501
        unique_cards=unique_cards,
        users=users,
        groups=groups,
        iou_data=iou_data,
        base_currency=base_currency,
        budget_summary=budget_summary,
        currencies=currencies,
        categories=categories,
        monthly_labels=monthly_labels,
        monthly_amounts=monthly_amounts,
        total_income=total_income,
        total_transfers=total_transfers,
        net_cash_flow=net_cash_flow,
        savings_rate=savings_rate,
        asset_trends_months=asset_debt_trends["months"],
        asset_trends=asset_debt_trends["assets"],
        debt_trends=asset_debt_trends["debts"],
        total_assets=asset_debt_trends["total_assets"],
        total_debts=asset_debt_trends["total_debts"],
        net_worth=asset_debt_trends["net_worth"],
        now=now,
    )
