from datetime import datetime, timedelta

from flask_login import current_user
from sqlalchemy import or_

from models import Account, Budget, Currency, Expense, Settlement, User


def get_category_spending(expenses, expense_splits):
    current_month = datetime.now().month
    current_year = datetime.now().year

    category_totals = {}

    for expense in expenses:
        # Skip non-expenses
        if (
            hasattr(expense, "transaction_type")
            and expense.transaction_type != "expense"
        ):
            continue

        # Filter expenses for the current month and year
        if (
            expense.date.month != current_month
            or expense.date.year != current_year
        ):
            continue

        # Handle category splits first
        if expense.category_splits:
            for split in expense.category_splits:
                if split.category:
                    category_name = split.category.name
                    if category_name not in category_totals:
                        category_totals[category_name] = {
                            "amount": 0,
                            "color": split.category.color,
                            "icon": split.category.icon,
                        }
                    category_totals[category_name]["amount"] += split.amount

        # Handle regular category if no splits
        elif expense.category:
            category_name = expense.category.name
            if category_name not in category_totals:
                category_totals[category_name] = {
                    "amount": 0,
                    "color": expense.category.color,
                    "icon": expense.category.icon,
                }
            category_totals[category_name]["amount"] += expense.amount

    # Sort and return top categories
    return sorted(
        [
            {
                "name": name,
                "amount": data["amount"],
                "color": data["color"],
                "icon": data["icon"],
            }
            for name, data in category_totals.items()
        ],
        key=lambda x: x["amount"],
        reverse=True,
    )[:6]


def convert_currency(amount, from_code, to_code):
    """Convert an amount from one currency to another."""
    if from_code == to_code:
        return amount

    from_currency = Currency.query.filter_by(code=from_code).first()
    to_currency = Currency.query.filter_by(code=to_code).first()

    if not from_currency or not to_currency:
        return amount  # Return original if either currency not found

    # Get base currency for reference
    base_currency = Currency.query.filter_by(is_base=True).first()
    if not base_currency:
        return amount  # Cannot convert without a base currency

    # First convert amount to base currency
    if from_code == base_currency.code:
        # Amount is already in base currency
        amount_in_base = amount
    else:
        # Convert from source currency to base currency
        # The rate_to_base represents how much of the base currency
        # equals 1 unit of this currency
        amount_in_base = amount * from_currency.rate_to_base

    # Then convert from base currency to target currency
    if to_code == base_currency.code:
        # Target is base currency, so we're done
        return amount_in_base
    # Convert from base currency to target currency
    # We divide by the target currency's rate_to_base to get
    # the equivalent amount in the target currency
    return amount_in_base / to_currency.rate_to_base


def get_base_currency():
    """Get the current user's default currency or fall back to base currency."""
    if (
        current_user.is_authenticated
        and current_user.default_currency_code
        and current_user.default_currency
    ):
        # User has set a default currency, use that
        return {
            "code": current_user.default_currency.code,
            "symbol": current_user.default_currency.symbol,
            "name": current_user.default_currency.name,
        }
    # Fall back to system base currency if user has no preference
    base_currency = Currency.query.filter_by(is_base=True).first()
    if not base_currency:
        # Default to USD if no base currency is set
        return {"code": "USD", "symbol": "$", "name": "US Dollar"}
    return {
        "code": base_currency.code,
        "symbol": base_currency.symbol,
        "name": base_currency.name,
    }


def calculate_balances(user_id): # noqa: C901 PLR0912
    """Calculate balances between the current user and all other users."""
    balances = {}

    # Step 1: Calculate balances from expenses
    expenses = Expense.query.filter(
        or_(Expense.paid_by == user_id, Expense.split_with.like(f"%{user_id}%"))
    ).all()

    for expense in expenses:
        splits = expense.calculate_splits()

        # If current user paid for the expense
        if expense.paid_by == user_id:
            # Add what others owe to current user
            for split in splits["splits"]:
                other_user_id = split["email"]
                if other_user_id != user_id:
                    if other_user_id not in balances:
                        other_user = User.query.filter_by(
                            id=other_user_id
                        ).first()
                        balances[other_user_id] = {
                            "user_id": other_user_id,
                            "name": other_user.name
                            if other_user
                            else "Unknown",
                            "email": other_user_id,
                            "amount": 0,
                        }
                    balances[other_user_id]["amount"] += split["amount"]
        else:
            # If someone else paid and current user owes them
            payer_id = expense.paid_by

            # Find current user's portion
            current_user_portion = 0

            # Check if current user is in the splits
            for split in splits["splits"]:
                if split["email"] == user_id:
                    current_user_portion = split["amount"]
                    break

            if current_user_portion > 0:
                if payer_id not in balances:
                    payer = User.query.filter_by(id=payer_id).first()
                    balances[payer_id] = {
                        "user_id": payer_id,
                        "name": payer.name if payer else "Unknown",
                        "email": payer_id,
                        "amount": 0,
                    }
                balances[payer_id]["amount"] -= current_user_portion

    # Step 2: Adjust balances based on settlements
    settlements = Settlement.query.filter(
        or_(Settlement.payer_id == user_id, Settlement.receiver_id == user_id)
    ).all()

    for settlement in settlements:
        if settlement.payer_id == user_id:
            # Current user paid money to someone else
            other_user_id = settlement.receiver_id
            if other_user_id not in balances:
                other_user = User.query.filter_by(id=other_user_id).first()
                balances[other_user_id] = {
                    "user_id": other_user_id,
                    "name": other_user.name if other_user else "Unknown",
                    "email": other_user_id,
                    "amount": 0,
                }
            # FIX: When current user pays someone,
            # it INCREASES how much they owe the current user
            # Change from -= to +=
            balances[other_user_id]["amount"] += settlement.amount

        elif settlement.receiver_id == user_id:
            # Current user received money from someone else
            other_user_id = settlement.payer_id
            if other_user_id not in balances:
                other_user = User.query.filter_by(id=other_user_id).first()
                balances[other_user_id] = {
                    "user_id": other_user_id,
                    "name": other_user.name if other_user else "Unknown",
                    "email": other_user_id,
                    "amount": 0,
                }
            # FIX: When current user receives money,
            # it DECREASES how much they're owed
            # Change from += to -=
            balances[other_user_id]["amount"] -= settlement.amount

    # Return only non-zero balances
    return [
        balance
        for balance in balances.values()
        if abs(balance["amount"]) > 0.01  # noqa: PLR2004
    ]


def get_budget_summary():
    """Get budget summary for current user."""
    # Get all active budgets
    active_budgets = Budget.query.filter_by(
        user_id=current_user.id, active=True
    ).all()

    # Process budget data
    budget_summary = {
        "total_budgets": len(active_budgets),
        "over_budget": 0,
        "approaching_limit": 0,
        "under_budget": 0,
        "alert_budgets": [],  # For budgets that are over or approaching limit
    }

    for budget in active_budgets:
        status = budget.get_status()
        if status == "over":
            budget_summary["over_budget"] += 1
            budget_summary["alert_budgets"].append(
                {
                    "id": budget.id,
                    "name": budget.name or budget.category.name,
                    "percentage": budget.get_progress_percentage(),
                    "status": status,
                    "amount": budget.amount,
                    "spent": budget.calculate_spent_amount(),
                }
            )
        elif status == "approaching":
            budget_summary["approaching_limit"] += 1
            budget_summary["alert_budgets"].append(
                {
                    "id": budget.id,
                    "name": budget.name or budget.category.name,
                    "percentage": budget.get_progress_percentage(),
                    "status": status,
                    "amount": budget.amount,
                    "spent": budget.calculate_spent_amount(),
                }
            )
        else:
            budget_summary["under_budget"] += 1

    # Sort alert budgets by percentage (highest first)
    budget_summary["alert_budgets"] = sorted(
        budget_summary["alert_budgets"],
        key=lambda x: x["percentage"],
        reverse=True,
    )

    return budget_summary


def calculate_asset_debt_trends(current_user): # noqa: C901 PLR0912
    """Calculate asset and debt trends for a user's accounts."""
    # Initialize tracking
    monthly_assets = {}
    monthly_debts = {}

    # Get today's date and calculate a reasonable historical range
    # (last 12 months)
    today = datetime.now()
    twelve_months_ago = today - timedelta(days=365)

    # Get all accounts for the user
    accounts = Account.query.filter_by(user_id=current_user.id).all()

    # Get user's preferred currency code
    user_currency_code = current_user.default_currency_code or "USD"

    # Calculate true total assets and debts directly from accounts
    # (for accurate current total)
    direct_total_assets = 0
    direct_total_debts = 0

    for account in accounts:
        # Get account's currency code, default to user's preferred currency
        account_currency_code = account.currency_code or user_currency_code

        # Convert account balance to user's currency if needed
        if account_currency_code != user_currency_code:
            converted_balance = convert_currency(
                account.balance, account_currency_code, user_currency_code
            )
        else:
            converted_balance = account.balance

        if (
            account.type in ["checking", "savings", "investment"]
            and converted_balance > 0
        ):
            direct_total_assets += converted_balance
        elif account.type in ["credit"] or converted_balance < 0:
            # For credit cards with negative balances (standard convention)
            direct_total_debts += abs(converted_balance)

    # Process each account for historical trends
    for account in accounts:
        # Get account's currency code, default to user's preferred currency
        account_currency_code = account.currency_code or user_currency_code

        # Categorize account types
        is_asset = (
            account.type in ["checking", "savings", "investment"]
            and account.balance > 0
        )
        is_debt = account.type in ["credit"] or account.balance < 0

        # Skip accounts with zero or near-zero balance
        if abs(account.balance or 0) < 0.01: # noqa: PLR2004
            continue

        # Get monthly transactions for this account
        transactions = (
            Expense.query.filter(
                Expense.account_id == account.id,
                Expense.user_id == current_user.id,
                Expense.date >= twelve_months_ago,
            )
            .order_by(Expense.date)
            .all()
        )

        # Track balance over time
        balance_history = {}
        current_balance = account.balance or 0

        # Start with the most recent balance
        balance_history[today.strftime("%Y-%m")] = current_balance

        # Process transactions to track historical balances
        for transaction in transactions:
            month_key = transaction.date.strftime("%Y-%m")

            # Consider currency conversion for each transaction if needed
            transaction_amount = transaction.amount
            if (
                transaction.currency_code
                and transaction.currency_code != account_currency_code
            ):
                transaction_amount = convert_currency(
                    transaction_amount,
                    transaction.currency_code,
                    account_currency_code,
                )

            # Adjust balance based on transaction
            if transaction.transaction_type == "income":
                current_balance += transaction_amount
            elif transaction.transaction_type in {"expense", "transfer"}:
                current_balance -= transaction_amount

            # Update monthly balance
            balance_history[month_key] = current_balance

        # Convert balance history to user currency if needed
        if account_currency_code != user_currency_code:
            for month, balance in balance_history.items():
                balance_history[month] = convert_currency(
                    balance, account_currency_code, user_currency_code
                )

        # Categorize and store balances
        for month, balance in balance_history.items():
            if is_asset:
                # For asset accounts, add positive balances to the monthly total
                monthly_assets[month] = monthly_assets.get(month, 0) + balance
            elif is_debt:
                # For debt accounts or negative balances,
                # add the absolute value to the debt total
                monthly_debts[month] = monthly_debts.get(month, 0) + abs(
                    balance
                )

    # Ensure consistent months across both series
    all_months = sorted(
        set(list(monthly_assets.keys()) + list(monthly_debts.keys()))
    )

    # Fill in missing months with previous values or zero
    assets_trend = []
    debts_trend = []

    for month in all_months:
        assets_trend.append(
            monthly_assets.get(month, assets_trend[-1] if assets_trend else 0)
        )
        debts_trend.append(
            monthly_debts.get(month, debts_trend[-1] if debts_trend else 0)
        )

    # Use the directly calculated totals rather
    # than the trend values for accuracy
    total_assets = direct_total_assets
    total_debts = direct_total_debts
    net_worth = total_assets - total_debts

    return {
        "months": all_months,
        "assets": assets_trend,
        "debts": debts_trend,
        "total_assets": total_assets,
        "total_debts": total_debts,
        "net_worth": net_worth,
    }
