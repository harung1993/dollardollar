import json
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user
from sqlalchemy import or_

from extensions import db
from models import (
    Account,
    Category,
    Currency,
    Expense,
    Group,
    IgnoredRecurringPattern,
    RecurringExpense,
    User,
)
from recurring_detection import detect_recurring_transactions
from services.helpers import get_base_currency
from services.wrappers import login_required_dev
from tables import group_users

recurring_bp = Blueprint("recurring", __name__)


@recurring_bp.route("/recurring")
@login_required_dev
def recurring():
    base_currency = get_base_currency()
    recurring_expenses = RecurringExpense.query.filter(
        or_(
            RecurringExpense.user_id == current_user.id,
            RecurringExpense.split_with.like(f"%{current_user.id}%"),
        )
    ).all()
    users = User.query.all()
    groups = (
        Group.query.join(group_users)
        .filter(group_users.c.user_id == current_user.id)
        .all()
    )
    currencies = Currency.query.all()
    categories = (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.name)
        .all()
    )
    return render_template(
        "recurring.html",
        recurring_expenses=recurring_expenses,
        users=users,
        currencies=currencies,
        base_currency=base_currency,
        categories=categories,
        groups=groups,
    )


@recurring_bp.route("/get_recurring_form_html")
@login_required_dev
def get_recurring_form_html():
    """Return the HTML for the add recurring transaction form."""
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

    return render_template(
        "partials/recurring_transaction_form.html",
        users=users,
        groups=groups,
        categories=categories,
        currencies=currencies,
        base_currency=base_currency,
    )


@recurring_bp.route("/add_recurring", methods=["POST"])
@login_required_dev
def add_recurring():  # noqa: C901 PLR0912 PLR0915
    try:
        # Get transaction type
        transaction_type = request.form.get("transaction_type", "expense")

        # Parse dates with error handling
        try:
            start_date = datetime.strptime(
                request.form["start_date"], "%Y-%m-%d"
            )
            end_date = None
            if request.form.get("end_date"):
                end_date = datetime.strptime(
                    request.form["end_date"], "%Y-%m-%d"
                )
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD format.")
            return redirect(url_for("recurring"))

        # Handle account_id vs card_used transition
        account_id = request.form.get("account_id")
        card_used = "Default Card"  # Default value

        if account_id:
            if account_id == "default":
                # For backward compatibility use a default card name
                card_used = "Default Card"
            else:
                # Try to get the account name to use as
                # card_used for backward compatibility
                try:
                    account = Account.query.get(int(account_id))
                    if account:
                        card_used = account.name
                except:  # noqa: E722
                    # If account lookup fails, use a default
                    card_used = "Default Card"

        # Create new recurring expense with common fields
        recurring_expense = RecurringExpense(
            description=request.form["description"],
            amount=float(request.form["amount"]),
            card_used=card_used,  # For backward compatibility
            frequency=request.form["frequency"],
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id,
            transaction_type=transaction_type,
            active=True,
        )

        # Handle account_id if provided
        if account_id and account_id != "default":
            recurring_expense.account_id = int(account_id)

        # Handle currency if provided
        if request.form.get("currency_code"):
            recurring_expense.currency_code = request.form.get("currency_code")

        # Handle transaction type specific fields
        if transaction_type == "expense":
            # Check if this is a personal expense (no splits)
            is_personal_expense = request.form.get("personal_expense") == "on"

            # Setup expense fields
            recurring_expense.paid_by = request.form["paid_by"]
            recurring_expense.split_method = request.form["split_method"]
            recurring_expense.split_value = (
                float(request.form.get("split_value", 0))
                if request.form.get("split_value")
                else 0
            )

            # Handle split with based on whether it's a personal expense
            if is_personal_expense:
                recurring_expense.split_with = None
                recurring_expense.split_details = None
            else:
                # Handle multi-select for split_with
                split_with_ids = request.form.getlist("split_with")
                if not split_with_ids:
                    flash(
                        "Please select at least one person to "
                        "split with or mark as personal expense."
                    )
                    return redirect(url_for("recurring"))

                recurring_expense.split_with = (
                    ",".join(split_with_ids) if split_with_ids else None
                )

                # Process split details if provided
                if request.form.get("split_details"):
                    recurring_expense.split_details = request.form.get(
                        "split_details"
                    )

            # Set group if provided
            recurring_expense.group_id = (
                request.form.get("group_id")
                if request.form.get("group_id")
                else None
            )

            # Set category if provided
            category_id = request.form.get("category_id")
            if category_id and category_id.strip():
                recurring_expense.category_id = int(category_id)

        elif transaction_type == "income":
            # Income has no split details or group
            recurring_expense.paid_by = current_user.id
            recurring_expense.split_with = None
            recurring_expense.split_method = "equal"
            recurring_expense.split_details = None
            recurring_expense.group_id = None

            # Set category if provided
            category_id = request.form.get("category_id")
            if category_id and category_id.strip():
                recurring_expense.category_id = int(category_id)

        elif transaction_type == "transfer":
            # Transfer has no split details, group, or category
            recurring_expense.paid_by = current_user.id
            recurring_expense.split_with = None
            recurring_expense.split_method = "equal"
            recurring_expense.split_details = None
            recurring_expense.group_id = None
            category_id = request.form.get("category_id")
            if category_id and category_id.strip():
                recurring_expense.category_id = int(category_id)

            # Set destination account if provided
            dest_account_id = request.form.get("destination_account_id")
            if dest_account_id and dest_account_id.strip():
                recurring_expense.destination_account_id = int(dest_account_id)

        db.session.add(recurring_expense)
        db.session.commit()

        # Create first expense instance if the start date is today
        # or in the past
        today = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if start_date <= today:
            expense = recurring_expense.create_expense_instance(start_date)
            db.session.add(expense)
            db.session.commit()

        flash("Recurring transaction added successfully!")

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error adding recurring transaction:")
        flash(f"Error: {e!s}")

    return redirect(url_for("recurring"))


@recurring_bp.route("/toggle_recurring/<int:recurring_id>", methods=["POST"])
@login_required_dev
def toggle_recurring(recurring_id):
    recurring_expense = RecurringExpense.query.get_or_404(recurring_id)

    # Security check
    if recurring_expense.user_id != current_user.id:
        flash("You don't have permission to modify this recurring expense")
        return redirect(url_for("recurring"))

    # Toggle the active status
    recurring_expense.active = not recurring_expense.active
    db.session.commit()

    status = "activated" if recurring_expense.active else "deactivated"
    flash(f"Recurring expense {status} successfully")

    return redirect(url_for("recurring"))


@recurring_bp.route("/delete_recurring/<int:recurring_id>", methods=["POST"])
@login_required_dev
def delete_recurring(recurring_id):
    recurring_expense = RecurringExpense.query.get_or_404(recurring_id)

    # Security check
    if recurring_expense.user_id != current_user.id:
        flash("You don't have permission to delete this recurring expense")
        return redirect(url_for("recurring"))

    db.session.delete(recurring_expense)
    db.session.commit()

    flash("Recurring expense deleted successfully")

    return redirect(url_for("recurring"))


@recurring_bp.route("/edit_recurring/<int:recurring_id>")
@login_required_dev
def edit_recurring_page(recurring_id):
    """Load the recurring expenses page with form pre-filled for editing."""
    # Find the recurring expense
    recurring = RecurringExpense.query.get_or_404(recurring_id)

    # Security check: Only the creator can edit
    if recurring.user_id != current_user.id:
        flash("You do not have permission to edit this recurring expense")
        return redirect(url_for("recurring"))

    # Prepare the same data needed for the recurring page
    base_currency = get_base_currency()
    recurring_expenses = RecurringExpense.query.filter(
        or_(
            RecurringExpense.user_id == current_user.id,
            RecurringExpense.split_with.like(f"%{current_user.id}%"),
        )
    ).all()
    users = User.query.all()
    groups = (
        Group.query.join(group_users)
        .filter(group_users.c.user_id == current_user.id)
        .all()
    )
    currencies = Currency.query.all()
    categories = (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.name)
        .all()
    )

    # Return the template with the recurring expense data and flags for edit mode
    return render_template(
        "recurring.html",
        recurring_expenses=recurring_expenses,
        users=users,
        currencies=currencies,
        base_currency=base_currency,
        groups=groups,
        categories=categories,
        edit_recurring=recurring,  # Pass the recurring expense to edit
        auto_open_form=True,
    )  # Flag to auto-open the form


@recurring_bp.route("/update_recurring/<int:recurring_id>", methods=["POST"])
@login_required_dev
def update_recurring(recurring_id):  # noqa: C901 PLR0912 PLR0915
    """Update an existing recurring transaction."""
    try:
        # Find the recurring transaction
        recurring = RecurringExpense.query.get_or_404(recurring_id)

        # Security check: Only the creator can update
        if recurring.user_id != current_user.id:
            flash(
                "You do not have permission to edit this recurring transaction"
            )
            return redirect(url_for("recurring"))

        # Get transaction type
        transaction_type = request.form.get("transaction_type", "expense")

        # Parse dates
        try:
            start_date = datetime.strptime(
                request.form["start_date"], "%Y-%m-%d"
            )
            end_date = None
            if request.form.get("end_date"):
                end_date = datetime.strptime(
                    request.form.get("end_date"), "%Y-%m-%d"
                )
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD format.")
            return redirect(url_for("recurring"))

        # Update basic fields for all transaction types
        recurring.description = request.form["description"]
        recurring.amount = float(request.form["amount"])
        recurring.frequency = request.form["frequency"]
        recurring.start_date = start_date
        recurring.end_date = end_date
        recurring.transaction_type = transaction_type

        # Handle account based on transaction type
        account_id = request.form.get("account_id")
        if account_id:
            if account_id == "default":
                # Keep the existing card_used value
                pass
            else:
                # Try to get the account name for backward compatibility
                try:
                    account = Account.query.get(int(account_id))
                    if account:
                        recurring.card_used = account.name
                        recurring.account_id = int(account_id)
                except:  # noqa: E722
                    # Fallback - don't change card_used
                    pass

        # Handle currency if provided
        if request.form.get("currency_code"):
            recurring.currency_code = request.form.get("currency_code")

        # Handle fields based on transaction type
        if transaction_type == "expense":
            # Handle expense-specific fields
            recurring.paid_by = request.form["paid_by"]

            # Handle split with
            is_personal_expense = request.form.get("personal_expense") == "on"
            if is_personal_expense:
                recurring.split_with = None
                recurring.split_details = None
            else:
                split_with_ids = request.form.getlist("split_with")
                recurring.split_with = (
                    ",".join(split_with_ids) if split_with_ids else None
                )

                # Process split details
                recurring.split_method = request.form["split_method"]
                if request.form.get("split_details"):
                    recurring.split_details = request.form.get("split_details")

            # Handle group
            recurring.group_id = (
                request.form.get("group_id")
                if request.form.get("group_id")
                and request.form.get("group_id") != ""
                else None
            )

            # Handle category
            category_id = request.form.get("category_id")
            if category_id and category_id.strip():
                recurring.category_id = int(category_id)
            else:
                recurring.category_id = None

            # Clear transfer-specific fields
            recurring.destination_account_id = None

        elif transaction_type == "income":
            # Income doesn't use split fields
            recurring.paid_by = current_user.id
            recurring.split_with = None
            recurring.split_details = None
            recurring.split_method = "equal"
            recurring.group_id = None

            # Handle category
            category_id = request.form.get("category_id")
            if category_id and category_id.strip():
                recurring.category_id = int(category_id)
            else:
                recurring.category_id = None

            # Clear transfer-specific fields
            recurring.destination_account_id = None

        elif transaction_type == "transfer":
            # Transfer doesn't use split or category fields
            recurring.paid_by = current_user.id
            recurring.split_with = None
            recurring.split_details = None
            recurring.split_method = "equal"
            recurring.group_id = None
            category_id = request.form.get("category_id")
            if category_id and category_id.strip():
                recurring.category_id = int(category_id)
            else:
                recurring.category_id = None

            # Handle destination account
            dest_account_id = request.form.get("destination_account_id")
            if dest_account_id and dest_account_id.strip():
                recurring.destination_account_id = int(dest_account_id)
            else:
                recurring.destination_account_id = None

        # Save changes
        db.session.commit()
        flash("Recurring transaction updated successfully!")

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(
            "Error updating recurring transaction %s:", recurring_id
        )
        flash(f"Error: {e!s}")

    return redirect(url_for("recurring"))


@recurring_bp.route("/detect_recurring_transactions")
@login_required_dev
def get_recurring_transactions():
    """Detect recurring transactions for the current user."""
    try:
        # Default to 60 days lookback and 2 min occurrences
        lookback_days = int(request.args.get("lookback_days", 60))
        min_occurrences = int(request.args.get("min_occurrences", 2))

        # Detect recurring transactions
        candidates = detect_recurring_transactions(
            current_user.id,
            lookback_days=lookback_days,
            min_occurrences=min_occurrences,
        )

        # Get base currency symbol for formatting
        base_currency = get_base_currency()
        currency_symbol = (
            base_currency["symbol"]
            if isinstance(base_currency, dict)
            else base_currency.symbol
        )

        # Get all ignored patterns for this user
        ignored_patterns = IgnoredRecurringPattern.query.filter_by(
            user_id=current_user.id
        ).all()
        ignored_keys = [pattern.pattern_key for pattern in ignored_patterns]

        # Prepare response data
        candidate_data = []
        for candidate in candidates:
            # Create a unique pattern key for this candidate
            pattern_key = f"{candidate['description']}_{candidate['amount']}_{candidate['frequency']}"  # noqa: E501

            # Skip if this pattern is in the ignored list
            if pattern_key in ignored_keys:
                continue

            # Create a candidate ID that's stable across requests
            candidate_id = f"candidate_{hash(pattern_key) & 0xFFFFFFFF}"

            # Create a serializable version of the candidate
            candidate_dict = {
                "id": candidate_id,  # Use a stable ID based on pattern
                "description": candidate["description"],
                "amount": candidate["amount"],
                "currency_code": candidate["currency_code"],
                "frequency": candidate["frequency"],
                "confidence": candidate["confidence"],
                "occurrences": candidate["occurrences"],
                "next_date": candidate["next_date"].isoformat(),
                "avg_interval": candidate["avg_interval"],
                "transaction_type": candidate["transaction_type"],
                # Include account and category info if available
                "account_id": candidate["account_id"],
                "category_id": candidate["category_id"],
                "account_name": None,
                "category_name": None,
            }

            # Add account name if available
            if candidate["account_id"]:
                account = Account.query.get(candidate["account_id"])
                if account:
                    candidate_dict["account_name"] = account.name

            # Add category name if available
            if candidate["category_id"]:
                category = Category.query.get(candidate["category_id"])
                if category:
                    candidate_dict["category_name"] = category.name
                    candidate_dict["category_icon"] = category.icon
                    candidate_dict["category_color"] = category.color

            candidate_data.append(candidate_dict)

            # Store candidate in session for later reference
            # Use the stable candidate ID as the session key
            session_key = f"recurring_candidate_{candidate_id}"
            session[session_key] = {
                "description": candidate["description"],
                "amount": candidate["amount"],
                "currency_code": candidate["currency_code"],
                "frequency": candidate["frequency"],
                "account_id": candidate["account_id"],
                "category_id": candidate["category_id"],
                "transaction_type": candidate["transaction_type"],
                "transaction_ids": candidate["transaction_ids"],
            }

        return jsonify(
            {
                "success": True,
                "candidates": candidate_data,
                "currency_symbol": currency_symbol,
            }
        )

    except Exception as e:
        current_app.logger.exception("Error detecting recurring transactions:")
        return jsonify(
            {
                "success": False,
                "message": f"Error detecting recurring transactions: {e!s}",
            }
        ), 500


@recurring_bp.route("/recurring_candidate_history/<candidate_id>")
@login_required_dev
def recurring_candidate_history(candidate_id):
    """Get transaction history for a recurring candidate."""
    try:
        # Get stored candidate data from session
        session_key = f"recurring_candidate_{candidate_id}"
        candidate_data = session.get(session_key)

        if not candidate_data:
            return jsonify(
                {
                    "success": False,
                    "message": "Candidate details not found. "
                    "Please refresh the page and try again.",
                }
            ), 404

        # Get transaction IDs from the stored data
        transaction_ids = candidate_data.get("transaction_ids", [])

        # Get user's base currency
        base_currency = get_base_currency()
        currency_symbol = (
            base_currency["symbol"]
            if isinstance(base_currency, dict)
            else base_currency.symbol
        )

        # Fetch the actual transactions
        transactions = []
        for tx_id in transaction_ids:
            expense = Expense.query.get(tx_id)
            if expense and expense.user_id == current_user.id:
                tx_data = {
                    "id": expense.id,
                    "description": expense.description,
                    "amount": expense.amount,
                    "date": expense.date.isoformat(),
                    "account_name": expense.account.name
                    if expense.account
                    else None,
                }

                # Add category information if available
                if hasattr(expense, "category") and expense.category:
                    tx_data["category_name"] = expense.category.name
                    tx_data["category_icon"] = expense.category.icon
                    tx_data["category_color"] = expense.category.color

                transactions.append(tx_data)

        # Sort transactions by date (newest first)
        transactions.sort(key=lambda x: x["date"], reverse=True)

        return jsonify(
            {
                "success": True,
                "candidate_id": candidate_id,
                "description": candidate_data["description"],
                "currency_symbol": currency_symbol,
                "transactions": transactions,
            }
        )

    except Exception as e:
        current_app.logger.exception("Error fetching transaction history")
        return jsonify(
            {
                "success": False,
                "message": f"Error fetching transaction history: {e!s}",
            }
        ), 500


@recurring_bp.route("/convert_to_recurring/<candidate_id>", methods=["POST"])
@login_required_dev
def convert_to_recurring(candidate_id):
    """Convert a detected recurring transaction to a RecurringExpense."""
    from recurring_detection import create_recurring_expense_from_detection

    try:
        # Check if this is an edit request
        is_edit = request.args.get("edit", "false").lower() == "true"

        if is_edit:
            # If this is an edit, we're using the form data
            # Process the form data just like in add_recurring route

            # Extract form data
            description = request.form.get("description")
            amount = float(request.form.get("amount", 0))
            frequency = request.form.get("frequency")
            account_id = request.form.get("account_id")
            category_id = request.form.get("category_id")

            # Create a custom candidate data structure
            custom_candidate = {
                "description": description,
                "amount": amount,
                "frequency": frequency,
                "account_id": account_id,
                "category_id": category_id,
                "transaction_type": request.form.get(
                    "transaction_type", "expense"
                ),  # Default
            }

            # Create recurring expense from custom data
            recurring = create_recurring_expense_from_detection(
                current_user.id, custom_candidate
            )

            # Additional fields from form
            recurring.start_date = datetime.strptime(
                request.form.get("start_date"), "%Y-%m-%d"
            )
            if request.form.get("end_date"):
                recurring.end_date = datetime.strptime(
                    request.form.get("end_date"), "%Y-%m-%d"
                )

            # Process split settings
            is_personal = request.form.get("personal_expense") == "on"

            if is_personal:
                recurring.split_with = None
            else:
                split_with_ids = request.form.getlist("split_with")
                recurring.split_with = (
                    ",".join(split_with_ids) if split_with_ids else None
                )

            recurring.split_method = request.form.get("split_method", "equal")
            recurring.split_details = request.form.get("split_details")
            recurring.paid_by = request.form.get("paid_by", current_user.id)
            recurring.group_id = (
                request.form.get("group_id")
                if request.form.get("group_id")
                else None
            )

            # Save to database
            db.session.add(recurring)
            db.session.commit()

            # Check if this is a regular form submission or AJAX request
            if request.headers.get("X-Requested-With") != "XMLHttpRequest":
                flash("Recurring expense created successfully!")
                return redirect(url_for("recurring"))

            return jsonify(
                {
                    "success": True,
                    "message": "Recurring expense created successfully!",
                }
            )

        # Standard conversion (not edit)

        # Get candidate data from session
        session_key = f"recurring_candidate_{candidate_id}"
        candidate_data = session.get(session_key)

        if not candidate_data:
            return jsonify(
                {
                    "success": False,
                    "message": "Candidate details not found. "
                    "Please refresh the page and try again.",
                }
            ), 404

        # Create recurring expense from the candidate data
        recurring = create_recurring_expense_from_detection(
            current_user.id, candidate_data
        )

        # Set to active
        recurring.active = True

        # Save to database
        db.session.add(recurring)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Recurring expense created successfully!",
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error converting to recurring")
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500


@recurring_bp.route(
    "/ignore_recurring_candidate/<candidate_id>", methods=["POST"]
)
@login_required_dev
def ignore_recurring_candidate(candidate_id):
    """Mark a recurring transaction pattern as ignored."""
    try:
        # Get candidate data from session
        session_key = f"recurring_candidate_{candidate_id}"
        candidate_data = session.get(session_key)

        if not candidate_data:
            return jsonify(
                {
                    "success": False,
                    "message": "Candidate details not found. "
                    "Please refresh the page and try again.",
                }
            ), 404

        # Create pattern key for this candidate
        pattern_key = f"{candidate_data['description']}_{candidate_data['amount']}_{candidate_data['frequency']}"  # noqa: E501

        # Check if already ignored
        existing = IgnoredRecurringPattern.query.filter_by(
            user_id=current_user.id, pattern_key=pattern_key
        ).first()

        if existing:
            return jsonify(
                {"success": True, "message": "Pattern was already ignored"}
            )

        # Create ignored pattern record
        ignored = IgnoredRecurringPattern(
            user_id=current_user.id,
            pattern_key=pattern_key,
            description=candidate_data["description"],
            amount=candidate_data["amount"],
            frequency=candidate_data["frequency"],
        )

        db.session.add(ignored)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Pattern will no longer be detected as recurring",
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error ignoring recurring candidate")
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500


@recurring_bp.route(
    "/restore_ignored_pattern/<int:pattern_id>", methods=["POST"]
)
@login_required_dev
def restore_ignored_pattern(pattern_id):
    """Restore a previously ignored recurring pattern."""
    try:
        # Find the pattern
        pattern = IgnoredRecurringPattern.query.get_or_404(pattern_id)

        # Security check
        if pattern.user_id != current_user.id:
            flash("You do not have permission to modify this pattern.")
            return redirect(url_for("manage_ignored_patterns"))

        # Delete the pattern (which effectively restores it for detection)
        db.session.delete(pattern)
        db.session.commit()

        flash(
            "Pattern restored successfully. "
            "It may appear in future recurring detection results."
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error restoring pattern %s", {pattern_id})
        flash(f"Error: {e!s}")

    return redirect(url_for("manage_ignored_patterns"))


@recurring_bp.route("/manage_ignored_patterns")
@login_required_dev
def manage_ignored_patterns():
    """View and manage ignored recurring transaction patterns."""
    # Get all ignored patterns for the current user
    ignored_patterns = (
        IgnoredRecurringPattern.query.filter_by(user_id=current_user.id)
        .order_by(IgnoredRecurringPattern.ignore_date.desc())
        .all()
    )

    # Get base currency for display
    base_currency = get_base_currency()

    return render_template(
        "manage_ignored_patterns.html",
        ignored_patterns=ignored_patterns,
        base_currency=base_currency,
    )


@recurring_bp.route("/get_recurring/<int:recurring_id>")
@login_required_dev
def get_recurring(recurring_id):
    """Get recurring transaction details for editing."""
    try:
        # Find the recurring transaction
        recurring = RecurringExpense.query.get_or_404(recurring_id)

        # Security check: Only the creator can edit
        if recurring.user_id != current_user.id:
            return jsonify(
                {
                    "success": False,
                    "message": "You do not have permission to edit "
                    "this recurring transaction",
                }
            ), 403

        # Process split_with into array
        split_with_ids = []
        if recurring.split_with:
            split_with_ids = recurring.split_with.split(",")

        # Format dates
        start_date = (
            recurring.start_date.strftime("%Y-%m-%d")
            if recurring.start_date
            else None
        )
        end_date = (
            recurring.end_date.strftime("%Y-%m-%d")
            if recurring.end_date
            else None
        )

        # Prepare split details if available
        split_details = None
        if recurring.split_details:
            try:
                split_details = json.loads(recurring.split_details)
            except:  # noqa: E722
                split_details = None

        # Return the recurring transaction data
        return jsonify(
            {
                "success": True,
                "recurring": {
                    "id": recurring.id,
                    "description": recurring.description,
                    "amount": recurring.amount,
                    "transaction_type": recurring.transaction_type or "expense",
                    "frequency": recurring.frequency,
                    "start_date": start_date,
                    "end_date": end_date,
                    "currency_code": recurring.currency_code,
                    "account_id": recurring.account_id,
                    "destination_account_id": recurring.destination_account_id,
                    "paid_by": recurring.paid_by,
                    "split_with": split_with_ids,
                    "split_method": recurring.split_method,
                    "split_details": split_details,
                    "category_id": recurring.category_id,
                    "group_id": recurring.group_id,
                },
            }
        )

    except Exception as e:
        current_app.logger.exception(
            "Error retrieving recurring transaction %s", {recurring_id}
        )
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500
