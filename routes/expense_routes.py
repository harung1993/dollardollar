import json
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

from extensions import db
from models import CategorySplit, Currency, Expense
from services.wrappers import login_required_dev

expense_bp = Blueprint("expense", __name__)


@expense_bp.route("/add_expense", methods=["POST"])
@login_required_dev
def add_expense():  # noqa: C901, PLR0912, PLR0915
    """Add a new transaction (expense, income, or transfer)."""
    if request.method == "POST":
        try:
            # Get transaction type
            transaction_type = request.form.get("transaction_type", "expense")

            # Check if this is a personal expense (no splits)
            is_personal_expense = request.form.get("personal_expense") == "on"

            # Handle split_with based on whether it's a personal
            # expense or non-expense transaction
            if is_personal_expense or transaction_type in [
                "income",
                "transfer",
            ]:
                # For personal expenses and non-expense transactions,
                # we set split_with to empty
                split_with_str = None
            else:
                # Handle multi-select for split_with
                split_with_ids = request.form.getlist("split_with")
                if not split_with_ids and transaction_type == "expense":
                    flash(
                        "Please select at least one person to split with "
                        "or mark as personal expense."
                    )
                    return redirect(url_for("transactions"))

                split_with_str = (
                    ",".join(split_with_ids) if split_with_ids else None
                )

            # Parse date with error handling
            try:
                expense_date = datetime.strptime(
                    request.form["date"], "%Y-%m-%d"
                )
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD format.")
                return redirect(url_for("transactions"))

            # Carefully process split details
            split_details = None
            split_method = "equal"  # Default

            # Check for custom split details
            raw_split_details = request.form.get("split_details")
            if raw_split_details:
                try:
                    # Parse the JSON split details
                    parsed_split_details = json.loads(raw_split_details)

                    # Validate the split details structure
                    if isinstance(parsed_split_details, dict):
                        split_method = parsed_split_details.get("type", "equal")
                        split_details = raw_split_details

                        # Additional validation for custom splits
                        if split_method != "equal":
                            # Ensure we have valid split values
                            split_values = parsed_split_details.get(
                                "values", {}
                            )
                            if split_values and len(split_values) > 0:
                                # Override default split method
                                # if custom values exist
                                split_method = parsed_split_details["type"]
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, fall back to default
                    current_app.logger.warning(
                        "Failed to parse split details: %s", raw_split_details
                    )

            # Get currency information
            currency_code = request.form.get("currency_code", "USD")
            if not currency_code:
                # Use user's default currency or system default (USD)
                currency_code = current_user.default_currency_code or "USD"

            # Get original amount in the selected currency
            original_amount = float(request.form["amount"])

            # Find the currencies
            selected_currency = Currency.query.filter_by(
                code=currency_code
            ).first()
            base_currency = Currency.query.filter_by(is_base=True).first()

            if not selected_currency or not base_currency:
                flash("Currency configuration error.")
                return redirect(url_for("transactions"))

            # Convert original amount to base currency
            amount = original_amount * selected_currency.rate_to_base

            # Process category - properly handle empty strings for category_id
            category_id = request.form.get("category_id")
            if not category_id or category_id.strip() == "":
                category_id = None  # Set to None instead of empty string
            else:
                # Make sure it's an integer if provided
                category_id = int(category_id)

            # Get account information - handle empty strings
            account_id = request.form.get("account_id")
            if not account_id or account_id.strip() == "":
                account_id = None
            else:
                # Make sure it's an integer if provided
                account_id = int(account_id)

            card_used = "No card"  # Default fallback

            # For transfers, get destination account - handle empty strings
            destination_account_id = None
            if transaction_type == "transfer":
                destination_account_id = request.form.get(
                    "destination_account_id"
                )
                if (
                    not destination_account_id
                    or destination_account_id.strip() == ""
                ):
                    destination_account_id = None
                else:
                    # Make sure it's an integer if provided
                    destination_account_id = int(destination_account_id)

                # Validate different source and destination accounts
                if account_id == destination_account_id:
                    flash(
                        "Source and destination accounts must be "
                        "different for transfers."
                    )
                    return redirect(url_for("transactions"))

            # Determine paid_by (use from form or fallback to current user)
            paid_by = request.form.get("paid_by", current_user.id)

            # Create expense record
            expense = Expense(
                description=request.form["description"],
                amount=amount,  # Amount in base currency
                original_amount=original_amount,  # Original amount in selected currency # noqa: E501
                currency_code=currency_code,  # Store the original currency code
                date=expense_date,
                card_used=card_used,  # Default or legacy value
                split_method=split_method,  # Use the carefully parsed split method # noqa: E501
                split_value=0,  # We'll use split_details for more complex splits # noqa: E501
                split_details=split_details,
                paid_by=paid_by,
                user_id=current_user.id,
                category_id=category_id,
                group_id=request.form.get("group_id")
                if request.form.get("group_id")
                else None,
                split_with=split_with_str,
                transaction_type=transaction_type,
                account_id=account_id,
                destination_account_id=destination_account_id,
            )

            db.session.add(expense)
            db.session.commit()

            # Determine success message based on transaction type
            if transaction_type == "expense":
                flash("Expense added successfully!")
            elif transaction_type == "income":
                flash("Income recorded successfully!")
            elif transaction_type == "transfer":
                flash("Transfer completed successfully!")
            else:
                flash("Transaction added successfully!")

        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e!s}")
            current_app.logger.exception("Error adding expense:")

    return redirect(url_for("transactions"))


@expense_bp.route("/delete_expense/<int:expense_id>", methods=["POST"])
@login_required_dev
def delete_expense(expense_id):
    """Delete an expense by ID."""
    try:
        # Find the expense
        expense = Expense.query.get_or_404(expense_id)

        # Security check: Only the creator can delete the expense
        if expense.user_id != current_user.id:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(
                    {
                        "success": False,
                        "message": "You do not have permission to "
                        "delete this expense",
                    }
                ), 403
            flash("You do not have permission to delete this expense")
            return redirect(url_for("transactions"))

        # Delete the expense
        db.session.delete(expense)
        db.session.commit()

        # Handle AJAX and regular requests
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                {"success": True, "message": "Expense deleted successfully"}
            )
        flash("Expense deleted successfully")
        return redirect(url_for("transactions"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting expense %s:", expense_id)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": f"Error: {e!s}"}), 500
        flash(f"Error: {e!s}")
        return redirect(url_for("transactions"))


@expense_bp.route("/get_expense/<int:expense_id>", methods=["GET"])
@login_required_dev
def get_expense(expense_id):
    """Get expense details for editing."""
    try:
        # Find the expense
        expense = Expense.query.get_or_404(expense_id)

        # Security check: Only the creator or participants
        # can view the expense details
        if expense.user_id != current_user.id and current_user.id not in (
            expense.split_with or ""
        ):
            return jsonify(
                {
                    "success": False,
                    "message": "You do not have permission "
                    "to view this expense",
                }
            ), 403

        # Format the expense data
        split_with_ids = (
            expense.split_with.split(",") if expense.split_with else []
        )

        # Format the date in YYYY-MM-DD format
        formatted_date = expense.date.strftime("%Y-%m-%d")

        # Get tag IDs
        tag_ids = [tag.id for tag in expense.tags]

        # Return the expense data
        return jsonify(
            {
                "success": True,
                "expense": {
                    "id": expense.id,
                    "description": expense.description,
                    "amount": expense.amount,
                    "date": formatted_date,
                    "card_used": expense.card_used,
                    "split_method": expense.split_method,
                    "split_value": expense.split_value,
                    "split_details": expense.split_details,
                    "paid_by": expense.paid_by,
                    "split_with": split_with_ids,
                    "group_id": expense.group_id,
                    "currency_code": expense.currency_code
                    or current_user.default_currency_code
                    or "USD",
                    "tag_ids": tag_ids,
                },
            }
        )

    except Exception as e:
        current_app.logger.exception("Error retrieving expense %s:", expense_id)
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500


@expense_bp.route("/update_expense/<int:expense_id>", methods=["POST"])
@login_required_dev
def update_expense(expense_id):  # noqa: C901, PLR0912, PLR0915
    """Update an existing expense with improved category split handling."""
    try:
        # Find the expense
        expense = Expense.query.get_or_404(expense_id)

        # Security check
        if expense.user_id != current_user.id:
            flash("You do not have permission to edit this expense")
            return redirect(url_for("transactions"))

        # Log incoming data for debugging
        current_app.logger.info("Update expense request data: %s", request.form)

        # Get the transaction type with safer fallback
        transaction_type = request.form.get("transaction_type", "expense")

        # Common fields for all transaction types (with safer handling)
        expense.description = request.form.get(
            "description", expense.description
        )

        # Handle amount safely
        try:  # noqa: SIM105
            expense.amount = float(request.form.get("amount", expense.amount))
        except (ValueError, TypeError):
            # Keep existing amount if conversion fails
            pass

        # Handle date safely
        try:  # noqa: SIM105
            expense.date = datetime.strptime(
                request.form.get("date"), "%Y-%m-%d"
            )
        except (ValueError, TypeError):
            # Keep existing date if conversion fails
            pass

        # Handle category splits toggle - this determines which
        # category approach to use
        enable_category_split = (
            request.form.get("enable_category_split") == "on"
        )
        expense.has_category_splits = enable_category_split

        if enable_category_split:
            # When using splits, the main category becomes optional
            expense.category_id = None

            # Clear any existing splits
            CategorySplit.query.filter_by(expense_id=expense.id).delete()

            # Get split data from form
            split_data = request.form.get("category_splits_data", "[]")

            try:
                splits = json.loads(split_data)

                # Create new splits
                for split in splits:
                    category_id = split.get("category_id")
                    amount = float(split.get("amount", 0))

                    if category_id and amount > 0:
                        category_split = CategorySplit(
                            expense_id=expense.id,
                            category_id=category_id,
                            amount=amount,
                        )
                        db.session.add(category_split)

                # Validate that splits add up to the total
                total_splits = sum(
                    float(split.get("amount", 0)) for split in splits
                )
                if abs(total_splits - expense.amount) > 0.01:  # noqa: PLR2004
                    current_app.logger.warning(
                        "Split total %s doesn't match expense amount %s",
                        total_splits,
                        expense.amount,
                    )

            except Exception:
                current_app.logger.exception(
                    "Error processing category splits:"
                )
                # If split processing fails, disable splits
                # and fall back to main category
                expense.has_category_splits = False

                # Try to use the original category
                category_id = request.form.get("category_id")
                if (
                    category_id
                    and category_id != "null"
                    and category_id.strip()
                ):
                    try:
                        expense.category_id = int(category_id)
                    except ValueError:
                        expense.category_id = None
                else:
                    expense.category_id = None
        else:
            # If not using splits, just update the main category
            # Handle category_id safely (allow null values)
            category_id = request.form.get("category_id")
            if category_id in {"null", ""}:
                expense.category_id = None
            elif category_id is not None:
                try:
                    expense.category_id = int(category_id)
                except ValueError:
                    # Keep existing category if conversion fails
                    current_app.logger.warning(
                        "Invalid category_id value: %s", category_id
                    )

            # Clear any existing splits when not using splits
            CategorySplit.query.filter_by(expense_id=expense.id).delete()

        # Handle account_id safely
        account_id = request.form.get("account_id")
        if account_id and account_id not in {"null", ""}:
            try:
                expense.account_id = int(account_id)
            except ValueError:
                current_app.logger.warning(
                    "Invalid account_id value: %s", {account_id}
                )

        # Set transaction type
        expense.transaction_type = transaction_type

        # Type-specific processing
        if transaction_type == "expense":
            # Handle personal expense flag
            is_personal_expense = request.form.get("personal_expense") == "on"

            # Split with handling
            if is_personal_expense:
                expense.split_with = None
                expense.split_details = None
            else:
                # Get split_with as a list, then join to string
                split_with_list = request.form.getlist("split_with")
                expense.split_with = (
                    ",".join(split_with_list) if split_with_list else None
                )

                # Process split details
                expense.split_details = request.form.get("split_details")

            # Other expense-specific fields
            expense.split_method = request.form.get("split_method", "equal")
            expense.paid_by = request.form.get("paid_by", current_user.id)

            # Group ID handling (allow empty string to be converted to None)
            group_id = request.form.get("group_id")
            if group_id and group_id.strip():
                try:
                    expense.group_id = int(group_id)
                except ValueError:
                    expense.group_id = None
            else:
                expense.group_id = None

            # Clear transfer-specific fields
            expense.destination_account_id = None

        elif transaction_type == "income":
            # Income has no split details
            expense.split_with = None
            expense.split_details = None
            expense.split_method = "equal"
            expense.paid_by = current_user.id
            expense.group_id = None

            # Clear transfer-specific fields
            expense.destination_account_id = None

        elif transaction_type == "transfer":
            # Transfer has no split details
            expense.split_with = None
            expense.split_details = None
            expense.split_method = "equal"
            expense.paid_by = current_user.id
            expense.group_id = None
            expense.has_category_splits = False

            # Set transfer-specific fields - with
            # proper handling for empty values
            destination_id = request.form.get("destination_account_id")
            if (
                destination_id
                and destination_id != "null"
                and destination_id.strip()
            ):
                try:
                    expense.destination_account_id = int(destination_id)
                except ValueError:
                    # If not a valid integer, set to None
                    expense.destination_account_id = None
            else:
                # If empty, set to None
                expense.destination_account_id = None

        # Save changes
        db.session.commit()
        flash("Transaction updated successfully!")

        return redirect(url_for("transactions"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating expense %s:", expense_id)
        flash(f"Error: {e!s}")

        return redirect(url_for("transactions"))
