from datetime import datetime
from datetime import timezone as tz

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from extensions import db
from models import Budget, Category
from services.helpers import calculate_category_spending, get_base_currency
from services.wrappers import demo_time_limited, login_required_dev

budget_bp = Blueprint("budget", __name__)


@budget_bp.route("/budgets")
@login_required_dev
@demo_time_limited
def budgets():
    """View and manage budgets."""
    from datetime import datetime

    # Get all budgets for the current user
    user_budgets = (
        Budget.query.filter_by(user_id=current_user.id)
        .order_by(Budget.created_at.desc())
        .all()
    )

    # Get all categories for the form
    categories = (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.name)
        .all()
    )

    # Calculate budget progress for each budget
    budget_data = []
    total_month_budget = 0
    total_month_spent = 0

    for budget in user_budgets:
        spent = budget.calculate_spent_amount()
        remaining = budget.get_remaining_amount()
        percentage = budget.get_progress_percentage()
        status = budget.get_status()

        period_start, period_end = budget.get_current_period_dates()

        budget_data.append(
            {
                "budget": budget,
                "spent": spent,
                "remaining": remaining,
                "percentage": percentage,
                "status": status,
                "period_start": period_start,
                "period_end": period_end,
            }
        )

        # Add to monthly totals only for monthly budgets
        if budget.period == "monthly":
            total_month_budget += budget.amount
            total_month_spent += spent

    # Get base currency for display
    base_currency = get_base_currency()

    # Pass the current date to the template
    now = datetime.now()

    return render_template(
        "budgets.html",
        budget_data=budget_data,
        categories=categories,
        base_currency=base_currency,
        total_month_budget=total_month_budget,
        total_month_spent=total_month_spent,
        now=now,
    )


@budget_bp.route("/budgets/add", methods=["POST"])
@login_required_dev
def add_budget():
    """Add a new budget."""
    try:
        # Get form data
        category_id = request.form.get("category_id")
        amount = float(request.form.get("amount", 0))
        period = request.form.get("period", "monthly")
        include_subcategories = (
            request.form.get("include_subcategories") == "on"
        )
        name = request.form.get("name", "").strip() or None
        start_date_str = request.form.get("start_date")
        is_recurring = request.form.get("is_recurring") == "on"

        # Validate category exists
        category = Category.query.get(category_id)
        if not category or category.user_id != current_user.id:
            flash("Invalid category selected.")
            return redirect(url_for("budgets"))

        # Parse start date
        try:
            start_date = (
                datetime.strptime(start_date_str, "%Y-%m-%d")
                if start_date_str
                else datetime.now(tz.utc)
            )
        except ValueError:
            start_date = datetime.now(tz.utc)

        # Check if a budget already exists for this category
        existing_budget = Budget.query.filter_by(
            user_id=current_user.id,
            category_id=category_id,
            period=period,
            active=True,
        ).first()

        if existing_budget:
            flash(
                f"An active {period} budget already exists for this category. "
                f"Please edit or deactivate it first."
            )
            return redirect(url_for("budgets"))

        # Create new budget
        budget = Budget(
            user_id=current_user.id,
            category_id=category_id,
            name=name,
            amount=amount,
            period=period,
            include_subcategories=include_subcategories,
            start_date=start_date,
            is_recurring=is_recurring,
            active=True,
        )

        db.session.add(budget)
        db.session.commit()

        flash("Budget added successfully!")

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error adding budget: {e!s}")
        flash(f"Error adding budget: {e!s}")

    return redirect(url_for("budgets"))


@budget_bp.route("/budgets/edit/<int:budget_id>", methods=["POST"])
@login_required_dev
def edit_budget(budget_id):
    """Edit an existing budget."""
    try:
        # Find the budget
        budget = Budget.query.get_or_404(budget_id)

        # Security check
        if budget.user_id != current_user.id:
            flash("You do not have permission to edit this budget.")
            return redirect(url_for("budgets"))

        # Update fields
        budget.category_id = request.form.get("category_id", budget.category_id)
        budget.name = request.form.get("name", "").strip() or budget.name
        budget.amount = float(request.form.get("amount", budget.amount))
        budget.period = request.form.get("period", budget.period)
        budget.include_subcategories = (
            request.form.get("include_subcategories") == "on"
        )

        if request.form.get("start_date"):
            try:
                budget.start_date = datetime.strptime(
                    request.form.get("start_date"), "%Y-%m-%d"
                )
            except ValueError:
                pass  # Keep original if parsing fails

        budget.is_recurring = request.form.get("is_recurring") == "on"
        budget.updated_at = datetime.now(tz.utc)

        db.session.commit()
        flash("Budget updated successfully!")

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating budget")
        flash(f"Error updating budget: {e!s}")

    return redirect(url_for("budgets"))


@budget_bp.route("/budgets/toggle/<int:budget_id>", methods=["POST"])
@login_required_dev
def toggle_budget(budget_id):
    """Toggle budget active status."""
    try:
        # Find the budget
        budget = Budget.query.get_or_404(budget_id)

        # Security check
        if budget.user_id != current_user.id:
            flash("You do not have permission to modify this budget.")
            return redirect(url_for("budgets"))

        # Toggle active status
        budget.active = not budget.active
        db.session.commit()

        status = "activated" if budget.active else "deactivated"
        flash(f"Budget {status} successfully!")

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error toggling budget")
        flash(f"Error toggling budget: {e!s}")

    return redirect(url_for("budgets"))


@budget_bp.route("/budgets/delete/<int:budget_id>", methods=["POST"])
@login_required_dev
def delete_budget(budget_id):
    """Delete a budget."""
    try:
        # Find the budget
        budget = Budget.query.get_or_404(budget_id)

        # Security check
        if budget.user_id != current_user.id:
            flash("You do not have permission to delete this budget.")
            return redirect(url_for("budgets"))

        db.session.delete(budget)
        db.session.commit()

        flash("Budget deleted successfully!")

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting budget")
        flash(f"Error deleting budget: {e!s}")

    return redirect(url_for("budgets"))


@budget_bp.route("/budgets/get/<int:budget_id>", methods=["GET"])
@login_required_dev
def get_budget(budget_id):
    """Get budget details for editing via AJAX."""
    try:
        # Find the budget
        budget = Budget.query.get_or_404(budget_id)

        # Security check
        if budget.user_id != current_user.id:
            return jsonify(
                {
                    "success": False,
                    "message": "You do not have permission to view this budget",
                }
            ), 403

        # Get category details
        category = Category.query.get(budget.category_id)
        category_name = category.name if category else "Unknown"

        # Format dates
        start_date = budget.start_date.strftime("%Y-%m-%d")

        # Calculate spent amount
        spent = budget.calculate_spent_amount()
        remaining = budget.get_remaining_amount()
        percentage = budget.get_progress_percentage()
        status = budget.get_status()

        # Return the budget data
        return jsonify(
            {
                "success": True,
                "budget": {
                    "id": budget.id,
                    "name": budget.name or "",
                    "category_id": budget.category_id,
                    "category_name": category_name,
                    "amount": budget.amount,
                    "period": budget.period,
                    "include_subcategories": budget.include_subcategories,
                    "start_date": start_date,
                    "is_recurring": budget.is_recurring,
                    "active": budget.active,
                    "spent": spent,
                    "remaining": remaining,
                    "percentage": percentage,
                    "status": status,
                },
            }
        )

    except Exception as e:
        current_app.logger.exception(f"Error retrieving budget {budget_id}")
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500


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


@budget_bp.route("/budgets/subcategory-spending/<int:budget_id>")
@login_required_dev
def get_subcategory_spending(budget_id):
    """Get spending details for subcategories of a budget category."""
    try:
        # Find the budget
        budget = Budget.query.get_or_404(budget_id)

        # Security check
        if budget.user_id != current_user.id:
            return jsonify(
                {
                    "success": False,
                    "message": "You do not have permission to view this budget",
                }
            ), 403

        # Get the base currency symbol
        base_currency = get_base_currency()

        # Check if base_currency is a dictionary or an object
        currency_symbol = (
            base_currency["symbol"]
            if isinstance(base_currency, dict)
            else base_currency.symbol
        )

        # Get the category and its subcategories
        category = Category.query.get(budget.category_id)
        if not category:
            return jsonify(
                {"success": False, "message": "Category not found"}
            ), 404

        subcategories = []

        # Get period dates for this budget
        period_start, period_end = budget.get_current_period_dates()

        # If this budget includes the parent category directly
        if not budget.include_subcategories:
            # Only include the parent category itself
            spent = calculate_category_spending(
                category.id, period_start, period_end
            )

            subcategories.append(
                {
                    "id": category.id,
                    "name": category.name,
                    "icon": category.icon,
                    "color": category.color,
                    "spent": spent,
                }
            )
        else:
            # Include all subcategories
            for subcategory in category.subcategories:
                spent = calculate_category_spending(
                    subcategory.id, period_start, period_end
                )

                subcategories.append(
                    {
                        "id": subcategory.id,
                        "name": subcategory.name,
                        "icon": subcategory.icon,
                        "color": subcategory.color,
                        "spent": spent,
                    }
                )

            # If the parent category itself has direct expenses, add it too
            spent = calculate_category_spending(
                category.id,
                period_start,
                period_end,
                include_subcategories=False,
            )

            if spent > 0:
                subcategories.append(
                    {
                        "id": category.id,
                        "name": f"{category.name} (direct)",
                        "icon": category.icon,
                        "color": category.color,
                        "spent": spent,
                    }
                )

        # Sort subcategories by spent amount (highest first)
        subcategories = sorted(
            subcategories, key=lambda x: x["spent"], reverse=True
        )

        return jsonify(
            {
                "success": True,
                "budget_id": budget.id,
                "budget_amount": float(budget.amount),
                "currency_symbol": currency_symbol,
                "subcategories": subcategories,
            }
        )

    except Exception as e:
        current_app.logger.exception(
            f"Error retrieving subcategory spending for budget {budget_id}"
        )
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500
