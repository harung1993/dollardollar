from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy import or_

from models import Expense, User
from services.wrappers import login_required_dev

maintenance_bp = Blueprint("maintenance", __name__)


@maintenance_bp.route("/update_notification_preferences", methods=["POST"])
@login_required_dev
def update_notification_preferences():
    """Update user's notification preferences."""
    current_user.monthly_report_enabled = (
        "monthly_report_enabled" in request.form
    )
    db.session.commit()
    flash("Notification preferences updated successfully")
    return redirect(url_for("profile"))


@maintenance_bp.route("/export_transactions", methods=["POST"])
@login_required_dev
def export_transactions():
    """Export transactions as CSV file based on filter criteria."""
    try:
        # Get filter criteria from request
        filters = request.json if request.is_json else {}

        # Default to all transactions for the current user if no filters provided
        user_id = current_user.id

        # Extract filter parameters
        start_date = filters.get("startDate")
        end_date = filters.get("endDate")
        paid_by = filters.get("paidBy", "all")
        card_used = filters.get("cardUsed", "all")
        group_id = filters.get("groupId", "all")
        min_amount = filters.get("minAmount")
        max_amount = filters.get("maxAmount")
        description = filters.get("description", "")

        # Import required libraries
        import csv
        import io

        from flask import send_file

        # Build query with SQLAlchemy
        query = Expense.query.filter(
            or_(
                Expense.user_id == user_id,
                Expense.split_with.like(f"%{user_id}%"),
            )
        )

        # Apply filters
        if start_date:
            query = query.filter(
                Expense.date >= datetime.strptime(start_date, "%Y-%m-%d")
            )
        if end_date:
            query = query.filter(
                Expense.date <= datetime.strptime(end_date, "%Y-%m-%d")
            )
        if paid_by and paid_by != "all":
            query = query.filter(Expense.paid_by == paid_by)
        if card_used and card_used != "all":
            query = query.filter(Expense.card_used == card_used)
        if group_id:
            if group_id == "none":
                query = query.filter(Expense.group_id is None)
            elif group_id != "all":
                query = query.filter(Expense.group_id == group_id)
        if min_amount:
            query = query.filter(Expense.amount >= float(min_amount))
        if max_amount:
            query = query.filter(Expense.amount <= float(max_amount))
        if description:
            query = query.filter(Expense.description.ilike(f"%{description}%"))

        # Order by date, newest first
        expenses = query.order_by(Expense.date.desc()).all()

        # Create CSV data in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header row
        writer.writerow(
            [
                "Date",
                "Description",
                "Amount",
                "Card Used",
                "Paid By",
                "Split Method",
                "Group",
                "Your Role",
                "Your Share",
                "Total Expense",
            ]
        )

        # Write data rows
        for expense in expenses:
            # Calculate split info
            splits = expense.calculate_splits()

            # Get group name if applicable
            group_name = expense.group.name if expense.group else "No Group"

            # Calculate user's role and share
            user_role = ""
            user_share = 0

            if expense.paid_by == user_id:
                user_role = "Payer"
                user_share = splits["payer"]["amount"]
            else:
                user_role = "Participant"
                for split in splits["splits"]:
                    if split["email"] == user_id:
                        user_share = split["amount"]
                        break

            # Find the name of who paid
            payer = User.query.filter_by(id=expense.paid_by).first()
            payer_name = payer.name if payer else expense.paid_by

            writer.writerow(
                [
                    expense.date.strftime("%Y-%m-%d"),
                    expense.description,
                    f"{expense.amount:.2f}",
                    expense.card_used,
                    payer_name,
                    expense.split_method,
                    group_name,
                    user_role,
                    f"{user_share:.2f}",
                    f"{expense.amount:.2f}",
                ]
            )

        # Rewind the string buffer
        output.seek(0)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dollar_bill_transactions_{timestamp}.csv"

        # Send file for download
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        current_app.logger.exception("Error exporting transactions")
        return jsonify({"error": str(e)}), 500
