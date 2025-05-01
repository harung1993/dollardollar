import calendar
from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, render_template, request
from flask_login import current_user
from flask_mail import Message
from sqlalchemy import and_, or_

from extensions import mail
from models import Budget, Expense, User
from services.helpers import calculate_balances, get_base_currency
from services.wrappers import login_required_dev

report_bp = Blueprint("report", __name__)


def generate_monthly_report_data(user_id, year, month):
    """Generate data for monthly expense report."""
    user = User.query.get(user_id)
    if not user:
        return None

    # Calculate date range for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    # Get base currency
    base_currency = get_base_currency()
    currency_symbol = (
        base_currency["symbol"]
        if isinstance(base_currency, dict)
        else base_currency.symbol
    )

    # Get user's expenses for the month
    query_filters = [
        or_(
            Expense.user_id == user_id, Expense.split_with.like(f"%{user_id}%")
        ),
        Expense.date >= start_date,
        Expense.date <= end_date,
    ]

    expenses_raw = (
        Expense.query.filter(and_(*query_filters)).order_by(Expense.date).all()
    )

    # Calculate user's portion of expenses
    expenses = []
    total_spent = 0

    for expense in expenses_raw:
        # Calculate splits
        splits = expense.calculate_splits()

        # Get user's portion
        user_portion = 0
        if expense.paid_by == user_id:
            user_portion = splits["payer"]["amount"]
        else:
            for split in splits["splits"]:
                if split["email"] == user_id:
                    user_portion = split["amount"]
                    break

        if user_portion > 0:
            expenses.append(
                {
                    "id": expense.id,
                    "description": expense.description,
                    "date": expense.date,
                    "amount": user_portion,
                    "category": expense.category.name
                    if hasattr(expense, "category") and expense.category
                    else "Uncategorized",
                }
            )
            total_spent += user_portion

    # Get budget status
    budgets = Budget.query.filter_by(user_id=user_id, active=True).all()
    budget_status = []

    for budget in budgets:
        # Calculate budget status for this specific month
        spent = 0
        for expense in expenses:
            if (
                hasattr(expense, "category_id")
                and expense.category_id == budget.category_id
            ):
                spent += expense["amount"]

        percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
        status = "under"
        if percentage >= 100:
            status = "over"
        elif percentage >= 85:
            status = "approaching"

        budget_status.append(
            {
                "name": budget.name
                or (budget.category.name if budget.category else "Budget"),
                "amount": budget.amount,
                "spent": spent,
                "remaining": budget.amount - spent,
                "percentage": percentage,
                "status": status,
            }
        )

    # Get category breakdown
    categories = {}
    for expense in expenses:
        category = expense.get("category", "Uncategorized")
        if category not in categories:
            categories[category] = 0
        categories[category] += expense["amount"]

    # Format category data
    category_data = []
    for category, amount in sorted(
        categories.items(), key=lambda x: x[1], reverse=True
    ):
        percentage = (amount / total_spent * 100) if total_spent > 0 else 0
        category_data.append(
            {"name": category, "amount": amount, "percentage": percentage}
        )

    # Get balance information
    balances = calculate_balances(user_id)
    you_owe = []
    you_are_owed = []
    net_balance = 0

    for balance in balances:
        if balance["amount"] < 0:
            you_owe.append(
                {
                    "name": balance["name"],
                    "email": balance["email"],
                    "amount": abs(balance["amount"]),
                }
            )
            net_balance -= abs(balance["amount"])
        elif balance["amount"] > 0:
            you_are_owed.append(
                {
                    "name": balance["name"],
                    "email": balance["email"],
                    "amount": balance["amount"],
                }
            )
            net_balance += balance["amount"]

    # Get comparison with previous month
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    prev_start_date = datetime(prev_year, prev_month, 1)
    if prev_month == 12:
        prev_end_date = datetime(prev_year + 1, 1, 1) - timedelta(days=1)
    else:
        prev_end_date = datetime(prev_year, prev_month + 1, 1) - timedelta(
            days=1
        )

    prev_query_filters = [
        or_(
            Expense.user_id == user_id, Expense.split_with.like(f"%{user_id}%")
        ),
        Expense.date >= prev_start_date,
        Expense.date <= prev_end_date,
    ]

    prev_expenses = Expense.query.filter(and_(*prev_query_filters)).all()
    prev_total = 0

    for expense in prev_expenses:
        splits = expense.calculate_splits()
        user_portion = 0

        if expense.paid_by == user_id:
            user_portion = splits["payer"]["amount"]
        else:
            for split in splits["splits"]:
                if split["email"] == user_id:
                    user_portion = split["amount"]
                    break

        prev_total += user_portion

    # Calculate spending trend
    if prev_total > 0:
        spending_trend = ((total_spent - prev_total) / prev_total) * 100
    else:
        spending_trend = 0

    return {
        "user": user,
        "month_name": calendar.month_name[month],
        "year": year,
        "currency_symbol": currency_symbol,
        "total_spent": total_spent,
        "spending_trend": spending_trend,
        "prev_total": prev_total,
        "expense_count": len(expenses),
        "budget_status": budget_status,
        "category_data": category_data,
        "you_owe": you_owe,
        "you_are_owed": you_are_owed,
        "net_balance": net_balance,
        "top_expenses": sorted(
            expenses, key=lambda x: x["amount"], reverse=True
        )[:5],
    }


def send_monthly_report(user_id, year, month):
    """Generate and send monthly expense report email."""
    try:
        # Generate report data
        report_data = generate_monthly_report_data(user_id, year, month)
        if not report_data:
            current_app.logger.error(
                f"Failed to generate report data for user {user_id}"
            )
            return False

        # Create the email
        subject = f"Your Monthly Expense Report for {report_data['month_name']} {report_data['year']}"

        # Render the email templates
        html_content = render_template(
            "email/monthly_report.html", **report_data
        )
        text_content = render_template(
            "email/monthly_report.txt", **report_data
        )

        # Send the email
        msg = Message(
            subject=subject,
            recipients=[report_data["user"].id],
            body=text_content,
            html=html_content,
        )

        mail.send(msg)
        current_app.logger.info(
            f"Monthly report sent to {report_data['user'].id} for {report_data['month_name']} {report_data['year']}"
        )
        return True

    except Exception:
        current_app.logger.exception(
            "Error sending monthly report", exc_info=True
        )
        return False


@report_bp.route("/generate_monthly_report", methods=["GET", "POST"])
@login_required_dev
def generate_monthly_report():
    """Generate and send a monthly expense report for the current user."""
    if request.method == "POST":
        try:
            report_date = datetime.strptime(
                request.form.get("report_month", ""), "%Y-%m"
            )
            report_year = report_date.year
            report_month = report_date.month
        except ValueError:
            # Default to previous month if invalid input
            today = datetime.now()
            if today.month == 1:
                report_month = 12
                report_year = today.year - 1
            else:
                report_month = today.month - 1
                report_year = today.year

        # Generate and send the report
        success = send_monthly_report(
            current_user.id, report_year, report_month
        )

        if success:
            flash("Monthly report has been sent to your email.")
        else:
            flash("Error generating monthly report. Please try again later.")

    # For GET request, show the form
    # Get the last 12 months for selection
    months = []
    today = datetime.now()
    for i in range(12):
        if today.month - i <= 0:
            month = today.month - i + 12
            year = today.year - 1
        else:
            month = today.month - i
            year = today.year

        month_name = calendar.month_name[month]
        months.append(
            {"value": f"{year}-{month:02d}", "label": f"{month_name} {year}"}
        )

    return render_template("generate_report.html", months=months)


def send_automatic_monthly_reports():
    """Send monthly reports to all users who have opted in."""
    with current_app.app_context():
        # Get the previous month
        today = datetime.now()
        if today.month == 1:
            report_month = 12
            report_year = today.year - 1
        else:
            report_month = today.month - 1
            report_year = today.year

        # Get users who have opted in
        # (you'd need to add this field to User model)
        # For now, we'll assume all users want reports
        users = User.query.all()

        current_app.logger.info(
            f"Starting to send monthly reports for {calendar.month_name[report_month]} {report_year}"
        )

        success_count = 0
        for user in users:
            if send_monthly_report(user.id, report_year, report_month):
                success_count += 1

        current_app.logger.info(
            f"Sent {success_count}/{len(users)} monthly reports"
        )
