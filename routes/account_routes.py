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
from models import Account, Currency, Expense
from services.helpers import (
    convert_currency,
    detect_internal_transfer,
    get_base_currency,
    get_category_id,
)
from services.wrappers import login_required_dev

account_bp = Blueprint("account", __name__)


@account_bp.route("/accounts")
@login_required_dev
def accounts():
    """View and manage financial accounts."""
    # Get all user accounts
    user_accounts = Account.query.filter_by(user_id=current_user.id).all()

    # Get user's preferred currency for conversion and display
    user_currency = None
    if current_user.default_currency_code:
        user_currency = Currency.query.filter_by(
            code=current_user.default_currency_code
        ).first()

    # Fall back to base currency if user has no preference
    if not user_currency:
        user_currency = Currency.query.filter_by(is_base=True).first()

    # If somehow we still don't have a currency, use USD as ultimate fallback
    if not user_currency:
        user_currency = Currency.query.filter_by(
            code="USD"
        ).first() or Currency(
            code="USD", name="US Dollar", symbol="$", rate_to_base=1.0
        )

    user_currency_code = user_currency.code

    # Calculate financial summary with currency conversion
    total_assets = 0
    total_liabilities = 0

    for account in user_accounts:
        # Get account balance in account's currency
        balance = account.balance or 0

        # Skip near-zero balances
        if abs(balance) < 0.01:  # noqa: PLR2004
            continue

        # Get account's currency code
        account_currency = account.currency_code or user_currency_code

        # Convert to user's preferred currency if different
        if account_currency != user_currency_code:
            converted_balance = convert_currency(
                balance, account_currency, user_currency_code
            )
        else:
            converted_balance = balance

        # Add to appropriate total
        if (
            account.type in ["checking", "savings", "investment"]
            and converted_balance > 0
        ):
            total_assets += converted_balance
        elif account.type in ["credit", "loan"] or converted_balance < 0:
            total_liabilities += abs(
                converted_balance
            )  # Store as positive amount

    # Calculate net worth
    net_worth = total_assets - total_liabilities

    # Get all currencies for the form
    currencies = Currency.query.all()

    return render_template(
        "accounts.html",
        accounts=user_accounts,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        net_worth=net_worth,
        user_currency=user_currency,
        currencies=currencies,
    )


@account_bp.route("/advanced")
@login_required_dev
def advanced():
    """Display advanced features like account management and imports."""
    # Get all user accounts
    accounts = Account.query.filter_by(user_id=current_user.id).all()

    # Get connected accounts (those with SimpleFin integration)
    connected_accounts = [
        account for account in accounts if account.import_source == "simplefin"
    ]

    # Calculate financial summary
    total_assets = sum(
        account.balance
        for account in accounts
        if account.type in ["checking", "savings", "investment"]
        and account.balance > 0
    )

    total_liabilities = abs(
        sum(
            account.balance
            for account in accounts
            if account.type in ["credit", "loan"] or account.balance < 0
        )
    )

    net_worth = total_assets - total_liabilities

    # Get base currency for display
    base_currency = get_base_currency()

    # Get all currencies for the form
    currencies = Currency.query.all()

    return render_template(
        "advanced.html",
        accounts=accounts,
        connected_accounts=connected_accounts,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        net_worth=net_worth,
        base_currency=base_currency,
        currencies=currencies,
    )


@account_bp.route("/add_account", methods=["POST"])
@login_required_dev
def add_account():
    """Add a new account."""
    try:
        name = request.form.get("name")
        account_type = request.form.get("type")
        institution = request.form.get("institution")
        balance = float(request.form.get("balance", 0))
        currency_code = request.form.get(
            "currency_code", current_user.default_currency_code
        )

        # Create new account
        account = Account(
            name=name,
            type=account_type,
            institution=institution,
            balance=balance,
            currency_code=currency_code,
            user_id=current_user.id,
        )

        db.session.add(account)
        db.session.commit()

        flash("Account added successfully")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding account: {e!s}")

    return redirect(url_for("accounts"))


@account_bp.route("/get_account/<int:account_id>")
@login_required_dev
def get_account(account_id):
    """Get account details via AJAX."""
    try:
        account = Account.query.get_or_404(account_id)

        # Security check
        if account.user_id != current_user.id:
            return jsonify(
                {
                    "success": False,
                    "message": "You do not have permission to view this account",
                }
            ), 403

        # Get transaction count for this account
        transaction_count = Expense.query.filter_by(
            account_id=account_id
        ).count()

        return jsonify(
            {
                "success": True,
                "account": {
                    "id": account.id,
                    "name": account.name,
                    "type": account.type,
                    "institution": account.institution,
                    "balance": account.balance,
                    "currency_code": account.currency_code
                    or current_user.default_currency_code,
                    "transaction_count": transaction_count,
                },
            }
        )
    except Exception as e:
        current_app.logger.exception("Error retrieving account %s", account_id)
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500


@account_bp.route("/update_account", methods=["POST"])
@login_required_dev
def update_account():
    """Update an existing account."""
    try:
        account_id = request.form.get("account_id")
        account = Account.query.get_or_404(account_id)

        # Security check
        if account.user_id != current_user.id:
            flash("You do not have permission to edit this account")
            return redirect(url_for("accounts"))

        # Update fields
        account.name = request.form.get("name")
        account.type = request.form.get("type")
        account.institution = request.form.get("institution")
        account.balance = float(request.form.get("balance", 0))
        account.currency_code = request.form.get("currency_code")

        db.session.commit()
        flash("Account updated successfully")

    except Exception as e:
        db.session.rollback()
        flash(f"Error updating account: {e!s}")

    return redirect(url_for("accounts"))


@account_bp.route("/delete_account/<int:account_id>", methods=["DELETE"])
@login_required_dev
def delete_account(account_id):
    """Delete an account."""
    try:
        account = Account.query.get_or_404(account_id)

        # Security check
        if account.user_id != current_user.id:
            return jsonify(
                {
                    "success": False,
                    "message": "You do not have permission to delete this account",
                }
            ), 403

        db.session.delete(account)
        db.session.commit()

        return jsonify(
            {"success": True, "message": "Account deleted successfully"}
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting account %s", account_id)
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500


@account_bp.route("/import_csv", methods=["POST"])
@login_required_dev
def import_csv():  # noqa: C901 PLR0912 PLR0915
    """Import transactions from a CSV file."""
    if "csv_file" not in request.files:
        flash("No file provided")
        return redirect(url_for("advanced"))

    csv_file = request.files["csv_file"]

    if csv_file.filename == "":
        flash("No file selected")
        return redirect(url_for("advanced"))

    # Case-insensitive extension check
    if not csv_file.filename.lower().endswith(".csv"):
        flash("File must be a CSV")
        return redirect(url_for("advanced"))

    # Define base_currency for any functions that might need it
    base_currency = get_base_currency()

    imported_expenses = []

    try:
        # Get form parameters
        account_id = request.form.get("account_id")
        date_format = request.form.get("date_format", "MM/DD/YYYY")
        date_column = request.form.get("date_column", "Date")
        amount_column = request.form.get("amount_column", "Amount")
        description_column = request.form.get(
            "description_column", "Description"
        )
        category_column = request.form.get("category_column")
        type_column = request.form.get("type_column")
        id_column = request.form.get("id_column")

        detect_duplicates = "detect_duplicates" in request.form
        auto_categorize = "auto_categorize" in request.form
        negative_is_expense = "negative_is_expense" in request.form
        # NEW: Get the delimiter selection
        delimiter_type = request.form.get("delimiter", "comma")
        delimiter = ","  # Default to comma
        # Read file content

        if delimiter_type == "tab":
            delimiter = "\t"
        elif delimiter_type == "semicolon":
            delimiter = ";"
        elif delimiter_type == "pipe":
            delimiter = "|"
        elif delimiter_type == "custom":
            custom_delimiter = request.form.get("custom_delimiter", ",")
            if custom_delimiter:
                delimiter = custom_delimiter
        file_content = csv_file.read().decode("utf-8")
        # Parse CSV
        import csv
        import io

        csv_reader = csv.DictReader(
            io.StringIO(file_content), delimiter=delimiter
        )

        # Get account if specified
        account = None
        if account_id:
            account = Account.query.get(account_id)
            if account and account.user_id != current_user.id:
                flash("Invalid account selected")
                return redirect(url_for("advanced"))

        # Use the enhanced determine_transaction_type
        # function that accepts account_id
        def determine_transaction_type_for_import(row, current_account_id=None):  # noqa: PLR0911 C901
            """Determine transaction type based on row data from CSV import."""
            type_column = request.form.get("type_column")
            negative_is_expense = "negative_is_expense" in request.form

            # Check if there's a specific transaction type column
            if type_column and type_column in row:
                type_value = row[type_column].strip().lower()

                # Map common terms to transaction types
                if type_value in [
                    "expense",
                    "debit",
                    "purchase",
                    "payment",
                    "withdrawal",
                ]:
                    return "expense"
                if type_value in ["income", "credit", "deposit", "refund"]:
                    return "income"
                if type_value in ["transfer", "move", "xfer"]:
                    return "transfer"

            # If no type column or unknown value, try to determine from description
            description = row.get(description_column, "").strip()
            if description:
                # Common transfer keywords
                transfer_keywords = [
                    "transfer",
                    "xfer",
                    "move",
                    "moved to",
                    "sent to",
                    "to account",
                    "between accounts",
                ]
                # Common income keywords
                income_keywords = [
                    "salary",
                    "deposit",
                    "refund",
                    "interest",
                    "dividend",
                    "payment received",
                ]
                # Common expense keywords
                expense_keywords = [
                    "payment",
                    "purchase",
                    "fee",
                    "subscription",
                    "bill",
                ]

                desc_lower = description.lower()

                # Check for keywords in description
                if any(keyword in desc_lower for keyword in transfer_keywords):
                    return "transfer"
                if any(keyword in desc_lower for keyword in income_keywords):
                    return "income"
                if any(keyword in desc_lower for keyword in expense_keywords):
                    return "expense"

            # If still undetermined, use amount sign
            amount_str = (
                row[amount_column].strip().replace("$", "").replace(",", "")
            )
            try:
                amount = float(amount_str)
                # Determine type based on amount sign and settings
                if amount < 0 and negative_is_expense:
                    return "expense"
                if amount > 0 and negative_is_expense:
                    return "income"
                if amount < 0 and not negative_is_expense:
                    return "income"  # In some systems, negative means money coming in
                return "expense"  # Default to expense for positive amounts
            except ValueError:
                # If amount can't be parsed, default to expense
                return "expense"

        # Get existing cards used
        existing_cards = (
            db.session.query(Expense.card_used)
            .filter_by(user_id=current_user.id)
            .distinct()
            .all()
        )
        existing_cards = [card[0] for card in existing_cards if card[0]]

        # Use the most frequent card as default if available
        default_card = "Imported Card"
        if existing_cards:
            from collections import Counter

            card_counter = Counter()
            for card in existing_cards:
                card_counter[card] += 1
            default_card = card_counter.most_common(1)[0][0]

        # Define date parser based on selected format
        def parse_date(date_str):
            if date_format == "MM/DD/YYYY":
                return datetime.strptime(date_str, "%m/%d/%Y")
            if date_format == "DD/MM/YYYY":
                return datetime.strptime(date_str, "%d/%m/%Y")
            if date_format == "YYYY-MM-DD":
                return datetime.strptime(date_str, "%Y-%m-%d")
            if date_format == "YYYY/MM/DD":
                return datetime.strptime(date_str, "%Y/%m/%d")
            return datetime.strptime(date_str, "%m/%d/%Y")  # Default

        # Process each row
        imported_count = 0
        duplicate_count = 0

        for row in csv_reader:
            try:
                # Skip if missing required fields
                if not all(
                    key in row
                    for key in [date_column, amount_column, description_column]
                ):
                    continue

                # Extract data
                date_str = row[date_column].strip()
                amount_str = (
                    row[amount_column].strip().replace("$", "").replace(",", "")
                )
                description = row[description_column].strip()

                # Skip if empty data
                if not date_str or not amount_str or not description:
                    continue

                # Parse date
                transaction_date = parse_date(date_str)

                # Parse amount (handle negative values)
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue  # Skip if amount can't be parsed

                # Try to detect if this is an internal transfer
                is_transfer, source_account_id, destination_account_id = (
                    False,
                    None,
                    None,
                )
                if account and account.id:
                    is_transfer, source_account_id, destination_account_id = (
                        detect_internal_transfer(
                            description, amount, account.id
                        )
                    )

                if is_transfer:
                    # This is an internal transfer
                    transaction_type = "transfer"
                    # Use the detected accounts, falling back to the selected account
                    source_account_id = source_account_id or account.id
                    # If we couldn't determine the destination, it stays None
                else:
                    # Use the function defined within this scope
                    transaction_type = determine_transaction_type_for_import(
                        row, account.id if account else None
                    )

                # Get external ID if available
                external_id = (
                    row.get(id_column)
                    if id_column and id_column in row
                    else None
                )

                # Check for duplicates if enabled
                if detect_duplicates and external_id:
                    existing = Expense.query.filter_by(
                        user_id=current_user.id,
                        external_id=external_id,
                        import_source="csv",
                    ).first()

                    if existing:
                        duplicate_count += 1
                        continue

                # Get category from CSV or auto-categorize (but not for transfers)
                category_id = None
                if transaction_type != "transfer":
                    category_name = None
                    if category_column and category_column in row:
                        category_name = row[category_column].strip()

                    # Use enhanced get_category_id that
                    # supports auto-categorization
                    category_id = get_category_id(
                        category_name,
                        description if auto_categorize else None,
                        current_user.id,
                    )

                # Create new transaction
                transaction = Expense(
                    description=description,
                    amount=abs(amount),  # Always store positive amount
                    date=transaction_date,
                    card_used=default_card,  # Use most common card or a default
                    transaction_type=transaction_type,
                    split_method="equal",
                    paid_by=current_user.id,
                    user_id=current_user.id,
                    category_id=category_id,
                    account_id=source_account_id
                    or (account.id if account else None),
                    destination_account_id=destination_account_id,
                    external_id=external_id,
                    import_source="csv",
                )

                # Add to session
                db.session.add(transaction)
                imported_expenses.append(transaction)
                imported_count += 1

                # If this is a transfer and we've identified a destination
                # account, update the balances of both accounts
                if (
                    transaction_type == "transfer"
                    and transaction.account_id
                    and transaction.destination_account_id
                ):
                    from_account = Account.query.get(transaction.account_id)
                    to_account = Account.query.get(
                        transaction.destination_account_id
                    )

                    if (
                        from_account
                        and to_account
                        and from_account.user_id == current_user.id
                        and to_account.user_id == current_user.id
                    ):
                        from_account.balance -= amount
                        to_account.balance += amount

            except Exception:
                current_app.logger.exception("Error processing CSV row")
                continue

        # Commit all transactions
        db.session.commit()

        # Update account balance if specified
        if account and imported_count > 0:
            # Update the last sync time
            account.last_sync = datetime(tz.utc)
            db.session.commit()

        # Flash success message
        flash(
            f"Successfully imported {imported_count} transactions. "
            f"Skipped {duplicate_count} duplicates."
        )

        # Redirect to a page showing the imported transactions
        return render_template(
            "import_results.html",
            expenses=imported_expenses,
            count=imported_count,
            duplicate_count=duplicate_count,
            base_currency=base_currency,
        )  # Pass base_currency here

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error importing CSV")
        flash(f"Error importing transactions: {e!s}")

    return redirect(url_for("advanced"))
