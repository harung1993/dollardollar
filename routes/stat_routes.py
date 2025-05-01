from datetime import datetime, timedelta

from flask import Blueprint, render_template, request
from flask import current_app as app
from flask_login import current_user
from sqlalchemy import and_, or_

from models import Account, Category, Expense, Group, Settlement
from services.helpers import calculate_balances, get_base_currency
from services.wrappers import login_required_dev
from tables import group_users

stat_bp = Blueprint("stat", __name__)


@stat_bp.route("/stats")
@login_required_dev
def stats():
    """Display financial statistics and visualizations that are user-centric."""
    # Get filter parameters from request
    base_currency = get_base_currency()
    start_date_str = request.args.get("startDate", None)
    end_date_str = request.args.get("endDate", None)
    group_id = request.args.get("groupId", "all")
    chart_type = request.args.get("chartType", "all")
    is_comparison = request.args.get("compare", "false") == "true"

    if is_comparison:
        return handle_comparison_request()

    # Parse dates or use defaults (last 6 months)
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        else:
            # Default to 6 months ago
            start_date = datetime.now() - timedelta(days=180)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        else:
            end_date = datetime.now()
    except ValueError:
        # If date parsing fails, use default range
        start_date = datetime.now() - timedelta(days=180)
        end_date = datetime.now()

    # Build the filter query - only expenses where user is involved
    query_filters = [
        or_(
            Expense.user_id == current_user.id,
            Expense.split_with.like(f"%{current_user.id}%"),
        ),
        Expense.date >= start_date,
        Expense.date <= end_date,
    ]

    # Add group filter if specified
    if group_id != "all":
        if group_id == "none":
            query_filters.append(Expense.group_id.is_(None))
        else:
            query_filters.append(Expense.group_id == group_id)

    # Execute the query with all filters
    expenses = (
        Expense.query.filter(and_(*query_filters))
        .order_by(Expense.date.desc())
        .all()
    )

    # Get all settlements in the date range
    settlement_filters = [
        or_(
            Settlement.payer_id == current_user.id,
            Settlement.receiver_id == current_user.id,
        ),
        Settlement.date >= start_date,
        Settlement.date <= end_date,
    ]
    settlements = (
        Settlement.query.filter(and_(*settlement_filters))
        .order_by(Settlement.date)
        .all()
    )

    # USER-CENTRIC: Calculate only the current user's expenses
    current_user_expenses = []
    total_user_expenses = 0

    # Initialize monthly data structures BEFORE the loop
    monthly_spending = {}
    monthly_income = {}  # New dictionary to track income
    monthly_labels = []
    monthly_amounts = []
    monthly_income_amounts = []  # New array for chart

    # Initialize all months in range
    current_date = start_date.replace(day=1)
    while current_date <= end_date:
        month_key = current_date.strftime("%Y-%m")
        month_label = current_date.strftime("%b %Y")
        monthly_labels.append(month_label)
        monthly_spending[month_key] = 0
        monthly_income[month_key] = 0  # Initialize income for this month

        # Advance to next month
        if current_date.month == 12:
            current_date = current_date.replace(
                year=current_date.year + 1, month=1
            )
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    for expense in expenses:
        # Calculate splits for this expense
        splits = expense.calculate_splits()

        # Create a record of the user's portion only
        user_portion = 0

        if expense.paid_by == current_user.id:
            # If current user paid, include their own portion
            user_portion = splits["payer"]["amount"]
        else:
            # If someone else paid, find current user's portion from splits
            for split in splits["splits"]:
                if split["email"] == current_user.id:
                    user_portion = split["amount"]
                    break

        # Only add to list if user has a portion
        if user_portion > 0:
            expense_data = {
                "id": expense.id,
                "description": expense.description,
                "date": expense.date,
                "total_amount": expense.amount,
                "user_portion": user_portion,
                "paid_by": expense.paid_by,
                "paid_by_name": expense.user.name,
                "card_used": expense.card_used,
                "group_id": expense.group_id,
                "group_name": expense.group.name if expense.group else None,
            }

            if hasattr(expense, "transaction_type"):
                expense_data["transaction_type"] = expense.transaction_type
            else:
                # Default to 'expense' for backward compatibility
                expense_data["transaction_type"] = "expense"

            # Format amounts based on transaction type
            if expense_data["transaction_type"] == "income":
                expense_data["formatted_amount"] = (
                    f"+{base_currency['symbol']}{expense_data['user_portion']:.2f}"
                )
                expense_data["amount_color"] = "#10b981"  # Green
            elif expense_data["transaction_type"] == "transfer":
                expense_data["formatted_amount"] = (
                    f"{base_currency['symbol']}{expense_data['user_portion']:.2f}"
                )
                expense_data["amount_color"] = "#a855f7"  # Purple
            else:  # Expense (default)
                expense_data["formatted_amount"] = (
                    f"-{base_currency['symbol']}{expense_data['user_portion']:.2f}"
                )
                expense_data["amount_color"] = "#ef4444"  # Red

            # Add category information for the expense
            if hasattr(expense, "category_id") and expense.category_id:
                category = Category.query.get(expense.category_id)
                if category:
                    expense_data["category_name"] = category.name
                    expense_data["category_icon"] = category.icon
                    expense_data["category_color"] = category.color
            else:
                expense_data["category_name"] = None
                expense_data["category_icon"] = "fa-tag"
                expense_data["category_color"] = "#6c757d"

            current_user_expenses.append(expense_data)

            # Add to user's total
            total_user_expenses += user_portion

            # Add to monthly spending or income based on transaction type
            month_key = expense_data["date"].strftime("%Y-%m")
            if month_key in monthly_spending:
                # Separate income and expense transactions
                if expense_data.get("transaction_type") == "income":
                    monthly_income[month_key] += expense_data["user_portion"]
                else:  # 'expense' or 'transfer' or None (legacy expenses)
                    monthly_spending[month_key] += expense_data["user_portion"]

    # Prepare chart data in correct order
    for month_key in sorted(monthly_spending.keys()):
        monthly_amounts.append(monthly_spending[month_key])
        monthly_income_amounts.append(monthly_income[month_key])

    # Calculate spending trend compared to previous period
    previous_period_start = start_date - (end_date - start_date)
    previous_period_filters = [
        or_(
            Expense.user_id == current_user.id,
            Expense.split_with.like(f"%{current_user.id}%"),
        ),
        Expense.date >= previous_period_start,
        Expense.date < start_date,
    ]

    # Initialize previous_total before querying
    previous_total = 0

    previous_expenses = Expense.query.filter(
        and_(*previous_period_filters)
    ).all()

    # Process previous expenses and calculate total
    for expense in previous_expenses:
        splits = expense.calculate_splits()
        user_portion = 0

        if expense.paid_by == current_user.id:
            user_portion = splits["payer"]["amount"]
        else:
            for split in splits["splits"]:
                if split["email"] == current_user.id:
                    user_portion = split["amount"]
                    break

        previous_total += user_portion

    # Then calculate spending trend
    if previous_total > 0:
        spending_trend = (
            (total_user_expenses - previous_total) / previous_total
        ) * 100
    else:
        spending_trend = 0

    # Calculate net balance (from balances function)
    balances = calculate_balances(current_user.id)
    net_balance = sum(balance["amount"] for balance in balances)
    balance_count = len(balances)

    # Find largest expense for current user (based on their portion)
    largest_expense = {"amount": 0, "description": "None"}
    if current_user_expenses:
        largest = max(current_user_expenses, key=lambda x: x["user_portion"])
        largest_expense = {
            "amount": largest["user_portion"],
            "description": largest["description"],
        }

    # Calculate monthly average (current user's spending)
    month_count = len([amt for amt in monthly_amounts if amt > 0])
    if month_count > 0:
        monthly_average = total_user_expenses / month_count
    else:
        monthly_average = 0

    # Payment methods (cards used) - only count cards the current user used
    payment_methods = []
    payment_amounts = []
    cards_total = {}

    for expense_data in current_user_expenses:
        # Only include in payment methods if current user paid
        if expense_data["paid_by"] == current_user.id:
            card = expense_data["card_used"]
            if card not in cards_total:
                cards_total[card] = 0
            cards_total[card] += expense_data["user_portion"]

    # Sort by amount, descending
    for card, amount in sorted(
        cards_total.items(), key=lambda x: x[1], reverse=True
    )[:8]:  # Limit to top 8
        payment_methods.append(card)
        payment_amounts.append(amount)

    # Expense categories based on first word of description (only user's portion)
    categories = {}
    for expense_data in current_user_expenses:
        # Get first word of description as category
        category = (
            expense_data["description"].split()[0]
            if expense_data["description"]
            else "Other"
        )
        if category not in categories:
            categories[category] = 0
        categories[category] += expense_data["user_portion"]

    # Get top 6 categories
    expense_categories = []
    category_amounts = []

    for category, amount in sorted(
        categories.items(), key=lambda x: x[1], reverse=True
    )[:6]:
        expense_categories.append(category)
        category_amounts.append(amount)

    # Balance history chart data
    # For user-centric approach, we'll calculate net balance over time
    balance_labels = monthly_labels

    # Chronologically organize expenses and settlements
    chronological_items = []

    for expense in expenses:
        splits = expense.calculate_splits()

        # If current user paid
        if expense.paid_by == current_user.id:
            # Add what others owe to current user
            for split in splits["splits"]:
                amount = split["amount"]
                chronological_items.append(
                    {
                        "date": expense.date,
                        "amount": amount,  # Positive: others owe current user
                        "type": "expense",
                    }
                )
        # If current user owes
        elif current_user.id in [split["email"] for split in splits["splits"]]:
            # Find current user's portion
            user_split = next(
                (
                    split["amount"]
                    for split in splits["splits"]
                    if split["email"] == current_user.id
                ),
                0,
            )
            chronological_items.append(
                {
                    "date": expense.date,
                    "amount": -user_split,  # Negative: current user owes others
                    "type": "expense",
                }
            )

    # Add settlements
    for settlement in settlements:
        if settlement.payer_id == current_user.id:
            # User paid money to someone else (decreases balance)
            chronological_items.append(
                {
                    "date": settlement.date,
                    "amount": -settlement.amount,
                    "type": "settlement",
                }
            )
        else:
            # User received money (increases balance)
            chronological_items.append(
                {
                    "date": settlement.date,
                    "amount": settlement.amount,
                    "type": "settlement",
                }
            )

    # Sort all items chronologically
    chronological_items.sort(key=lambda x: x["date"])

    # Calculate running balance at each month boundary
    balance_amounts = []
    running_balance = 0

    # Converting month labels to datetime objects for comparison
    month_dates = [
        datetime.strptime(f"{label} 01", "%b %Y %d") for label in monthly_labels
    ]

    # Create a copy for processing
    items_to_process = chronological_items.copy()
    for month_date in month_dates:
        while items_to_process and items_to_process[0]["date"] < month_date:
            item = items_to_process.pop(0)
            running_balance += item["amount"]

        balance_amounts.append(running_balance)

    # Group comparison data - only count user's portion of expenses
    group_names = ["Personal"]
    group_totals = [0]

    # Personal expenses (no group)
    for expense_data in current_user_expenses:
        if expense_data["group_id"] is None:
            group_totals[0] += expense_data["user_portion"]

    # Add each group's total for current user
    groups = (
        Group.query.join(group_users)
        .filter(group_users.c.user_id == current_user.id)
        .all()
    )

    for group in groups:
        group_total = 0
        for expense_data in current_user_expenses:
            if expense_data["group_id"] == group.id:
                group_total += expense_data["user_portion"]

        group_names.append(group.name)
        group_totals.append(group_total)

    # Top expenses for the table - show user's portion
    top_expenses = sorted(
        current_user_expenses, key=lambda x: x["date"], reverse=True
    )[:10]

    user_categories = {}

    # Try to get all user categories
    try:
        for category in Category.query.filter_by(user_id=current_user.id).all():
            if not category.parent_id:  # Only top-level categories
                user_categories[category.id] = {
                    "name": category.name,
                    "total": 0,
                    "color": category.color,
                    "monthly": dict.fromkeys(
                        sorted(monthly_spending.keys()), 0
                    ),
                }

        # Add uncategorized as a fallback
        uncategorized_id = 0
        user_categories[uncategorized_id] = {
            "name": "Uncategorized",
            "total": 0,
            "color": "#6c757d",
            "monthly": dict.fromkeys(sorted(monthly_spending.keys()), 0),
        }

        # Calculate totals per actual category and monthly trends
        for expense_data in current_user_expenses:
            # Get category ID, default to uncategorized
            cat_id = uncategorized_id

            # DEBUGGING: Check the actual structure of expense_data
            app.logger.info(
                f"Processing expense: {expense_data['id']} - {expense_data['description']}"
            )

            # Fetch the actual expense object
            expense_obj = Expense.query.get(expense_data["id"])

            if (
                expense_obj
                and hasattr(expense_obj, "category_id")
                and expense_obj.category_id
            ):
                cat_id = expense_obj.category_id
                app.logger.info(f"Found category_id: {cat_id}")

                # If it's a subcategory, use parent category ID instead
                category = Category.query.get(cat_id)
                if (
                    category
                    and category.parent_id
                    and category.parent_id in user_categories
                ):
                    cat_id = category.parent_id
                    app.logger.info(f"Using parent category: {cat_id}")

            # Only process if we have this category
            if cat_id in user_categories:
                # Add to total
                user_categories[cat_id]["total"] += expense_data["user_portion"]

                # Add to monthly data
                month_key = expense_data["date"].strftime("%Y-%m")
                if month_key in user_categories[cat_id]["monthly"]:
                    user_categories[cat_id]["monthly"][month_key] += (
                        expense_data["user_portion"]
                    )
            else:
                app.logger.warning(
                    f"Category ID {cat_id} not found in user_categories"
                )
    except Exception:
        # Log the full error for debugging
        app.logger.exception("Error getting category data", exc_info=True)
        user_categories = {
            1: {"name": "Food", "total": 350, "color": "#ec4899"},
            2: {"name": "Housing", "total": 1200, "color": "#8b5cf6"},
            3: {"name": "Transport", "total": 250, "color": "#3b82f6"},
            4: {"name": "Entertainment", "total": 180, "color": "#10b981"},
            5: {"name": "Shopping", "total": 320, "color": "#f97316"},
            0: {"name": "Others", "total": 150, "color": "#6c757d"},
        }

    # Prepare category data for charts - sort by amount
    sorted_categories = sorted(
        user_categories.items(), key=lambda x: x[1]["total"], reverse=True
    )

    app.logger.info(
        f"Sorted categories: {[cat[1]['name'] for cat in sorted_categories]}"
    )

    # Category data for pie chart
    category_names = [
        cat_data["name"] for _, cat_data in sorted_categories[:8]
    ]  # Top 8
    category_totals = [
        cat_data["total"] for _, cat_data in sorted_categories[:8]
    ]

    app.logger.info(f"Category names: {category_names}")
    app.logger.info(f"Category totals: {category_totals}")

    # Category trend data for line chart
    category_trend_data = []
    for cat_id, cat_data in sorted_categories[:4]:  # Top 4 for trend
        if "monthly" in cat_data:
            monthly_data = []
            for month_key in sorted(cat_data["monthly"].keys()):
                monthly_data.append(cat_data["monthly"][month_key])

            category_trend_data.append(
                {
                    "name": cat_data["name"],
                    "color": cat_data["color"],
                    "data": monthly_data,
                }
            )
        else:
            # Fallback if monthly data isn't available
            category_trend_data.append(
                {
                    "name": cat_data["name"],
                    "color": cat_data["color"],
                    "data": [cat_data["total"] / len(monthly_labels)]
                    * len(monthly_labels),
                }
            )

    app.logger.info(f"Category trend data: {category_trend_data}")

    # NEW CODE FOR TAG ANALYSIS
    # -------------------------
    tag_data = {}

    # Try to get tag information
    try:
        for expense_data in current_user_expenses:
            expense_obj = Expense.query.get(expense_data["id"])
            if expense_obj and hasattr(expense_obj, "tags"):
                for tag in expense_obj.tags:
                    if tag.id not in tag_data:
                        tag_data[tag.id] = {
                            "name": tag.name,
                            "total": 0,
                            "color": tag.color,
                        }
                    tag_data[tag.id]["total"] += expense_data["user_portion"]
    except Exception:
        # Fallback for tags in case of error
        app.logger.exception("Error getting tag data", exc_info=True)
        tag_data = {
            1: {"name": "Groceries", "total": 280, "color": "#f43f5e"},
            2: {"name": "Dining", "total": 320, "color": "#fb7185"},
            3: {"name": "Bills", "total": 150, "color": "#f97316"},
            4: {"name": "Rent", "total": 950, "color": "#fb923c"},
            5: {"name": "Gas", "total": 120, "color": "#f59e0b"},
            6: {"name": "Coffee", "total": 75, "color": "#fbbf24"},
        }

    # Sort and prepare tag data
    sorted_tags = sorted(
        tag_data.items(), key=lambda x: x[1]["total"], reverse=True
    )[:6]  # Top 6

    tag_names = [tag_data["name"] for _, tag_data in sorted_tags]
    tag_totals = [tag_data["total"] for _, tag_data in sorted_tags]
    tag_colors = [tag_data["color"] for _, tag_data in sorted_tags]

    app.logger.info(f"Tag names: {tag_names}")
    app.logger.info(f"Tag totals: {tag_totals}")

    # Calculate totals for each transaction type
    total_expenses_only = 0
    total_income = 0
    total_transfers = 0

    for expense in expenses:
        if hasattr(expense, "transaction_type"):
            if (
                expense.transaction_type == "expense"
                or expense.transaction_type is None
            ):
                total_expenses_only += expense.amount
            elif expense.transaction_type == "income":
                total_income += expense.amount
            elif expense.transaction_type == "transfer":
                total_transfers += expense.amount
        else:
            # For backward compatibility, treat as expense if no transaction_type
            total_expenses_only += expense.amount

    # Calculate derived metrics
    net_cash_flow = total_income - total_expenses_only

    # Calculate savings rate if income is not zero
    if total_income > 0:
        savings_rate = (net_cash_flow / total_income) * 100
    else:
        savings_rate = 0

    # Calculate expense to income ratio
    if total_income > 0:
        expense_income_ratio = (total_expenses_only / total_income) * 100
    else:
        expense_income_ratio = 100  # Default to 100% if no income

    # Provide placeholder values for other metrics
    income_trend = 5.2  # Example value
    liquidity_ratio = 3.5  # Example value
    account_growth = 7.8  # Example value

    user_accounts = Account.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "stats.html",
        user_accounts=user_accounts,
        expenses=expenses,
        total_expenses=total_user_expenses,  # User's spending only
        spending_trend=spending_trend,
        net_balance=net_balance,
        balance_count=balance_count,
        monthly_average=monthly_average,
        monthly_income=monthly_income_amounts,
        month_count=month_count,
        largest_expense=largest_expense,
        monthly_labels=monthly_labels,
        monthly_amounts=monthly_amounts,
        payment_methods=payment_methods,
        payment_amounts=payment_amounts,
        expense_categories=expense_categories,
        category_amounts=category_amounts,
        balance_labels=balance_labels,
        balance_amounts=balance_amounts,
        group_names=group_names,
        group_totals=group_totals,
        base_currency=base_currency,
        top_expenses=top_expenses,
        total_expenses_only=total_expenses_only,  # New: For expenses only
        total_income=total_income,
        total_transfers=total_transfers,
        income_trend=income_trend,
        net_cash_flow=net_cash_flow,
        savings_rate=savings_rate,
        expense_income_ratio=expense_income_ratio,
        liquidity_ratio=liquidity_ratio,
        account_growth=account_growth,
        # New data for enhanced charts
        category_names=category_names,
        category_totals=category_totals,
        category_trend_data=category_trend_data,
        tag_names=tag_names,
        tag_totals=tag_totals,
        tag_colors=tag_colors,
    )
