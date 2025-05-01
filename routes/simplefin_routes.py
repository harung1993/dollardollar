import base64
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
    session,
    url_for,
)
from flask_login import current_user

import simplefin_client
from extensions import db
from models import Account, Expense, User
from services.wrappers import login_required_dev
from simplefin_client import SimpleFin

simplefin_bp = Blueprint("simplefin", __name__)


@simplefin_bp.route("/connect_simplefin")
@login_required_dev
def connect_simplefin():
    """Redirect users to SimpleFin site to get their setup token."""
    if not current_app.config["SIMPLEFIN_ENABLED"]:
        flash(
            "SimpleFin integration is not enabled. "
            "Please contact the administrator."
        )
        return redirect(url_for("advanced"))

    # Get the URL for users to obtain their setup token
    setup_token_url = simplefin_client.get_setup_token_instructions()

    # Redirect to SimpleFin setup token page
    return redirect(setup_token_url)


@simplefin_bp.route("/simplefin/process_token", methods=["POST"])
@login_required_dev
def process_simplefin_token():  # noqa: PLR0911
    """Process the setup token provided by the user."""
    if not current_app.config["SIMPLEFIN_ENABLED"]:
        flash("SimpleFin integration is not enabled.")
        return redirect(url_for("advanced"))

    setup_token = request.form.get("setup_token")
    if not setup_token:
        flash("No setup token provided.")
        return redirect(url_for("advanced"))

    # Decode the setup token to get the claim URL
    claim_url = simplefin_client.decode_setup_token(setup_token)
    if not claim_url:
        flash("Invalid setup token. Please try again.")
        return redirect(url_for("advanced"))

    # Claim the access URL
    access_url = simplefin_client.claim_access_url(claim_url)
    if not access_url:
        flash(
            "Failed to claim access URL. "
            "Please try again with a new setup token."
        )
        return redirect(url_for("advanced"))

    if not simplefin_client.test_access_url(access_url):
        flash(
            "The access URL appears to be invalid. "
            "Please try again with a new setup token."
        )
        return redirect(url_for("advanced"))

    encoded_access_url = base64.b64encode(access_url.encode()).decode()

    # Create a SimpleFin settings record for this user
    try:
        # Check if a SimpleFin settings record already exists for this user
        simplefin_settings = SimpleFin.query.filter_by(
            user_id=current_user.id
        ).first()

        if simplefin_settings:
            # Update existing settings
            simplefin_settings.access_url = encoded_access_url
            simplefin_settings.last_sync = None  # Reset last sync time
            simplefin_settings.enabled = True
            simplefin_settings.sync_frequency = "daily"  # Default to daily
        else:
            # Create new settings
            simplefin_settings = SimpleFin(
                user_id=current_user.id,
                access_url=encoded_access_url,
                last_sync=None,
                enabled=True,
                sync_frequency="daily",
            )
            db.session.add(simplefin_settings)

        db.session.commit()

        # Redirect to fetch accounts page
        return redirect(url_for("simplefin_fetch_accounts"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error saving SimpleFin settings")
        flash(f"Error saving SimpleFin settings: {e!s}")
        return redirect(url_for("advanced"))


@simplefin_bp.route("/simplefin/fetch_accounts")
@login_required_dev
def simplefin_fetch_accounts():
    """Fetch accounts and transactions from SimpleFin."""
    if not current_app.config["SIMPLEFIN_ENABLED"]:
        flash("SimpleFin integration is not enabled.")
        return redirect(url_for("advanced"))

    try:
        # Get the user's SimpleFin settings
        simplefin_settings = SimpleFin.query.filter_by(
            user_id=current_user.id
        ).first()

        if not simplefin_settings or not simplefin_settings.access_url:
            flash(
                "No SimpleFin connection found. "
                "Please connect with SimpleFin first."
            )
            return redirect(url_for("advanced"))

        # Decode the access URL
        access_url = base64.b64decode(
            simplefin_settings.access_url.encode()
        ).decode()

        # Fetch accounts and transactions (last 30 days by default)
        raw_data = simplefin_client.get_accounts_with_transactions(
            access_url, days_back=30
        )

        if not raw_data:
            flash("Failed to fetch accounts and transactions from SimpleFin.")
            return redirect(url_for("advanced"))

        # Process the raw data
        accounts = simplefin_client.process_raw_accounts(raw_data)

        # Store account IDs in session instead of full data
        account_ids = [acc.get("id") for acc in accounts if acc.get("id")]
        session["simplefin_account_ids"] = account_ids

        # Render the account selection template
        return render_template("simplefin_accounts.html", accounts=accounts)

    except Exception as e:
        current_app.logger.exception("Error fetching SimpleFin accounts")
        flash(f"Error fetching accounts: {e!s}")
        return redirect(url_for("advanced"))


@simplefin_bp.route("/simplefin/add_accounts", methods=["POST"])
@login_required_dev
def simplefin_add_accounts():  # noqa: C901 PLR0912 PLR0915
    """Process selected accounts to add to the system."""
    # Get selected account IDs from form
    account_ids = request.form.getlist("account_ids")
    if not account_ids:
        flash("No accounts selected.")
        return redirect(url_for("advanced"))

    try:
        # Get the user's SimpleFin settings
        simplefin_settings = SimpleFin.query.filter_by(
            user_id=current_user.id
        ).first()

        if not simplefin_settings or not simplefin_settings.access_url:
            flash(
                "No SimpleFin connection found. Please reconnect with SimpleFin."
            )
            return redirect(url_for("advanced"))

        # Decode the access URL
        access_url = base64.b64decode(
            simplefin_settings.access_url.encode()
        ).decode()

        # Fetch accounts and transactions
        raw_data = simplefin_client.get_accounts_with_transactions(
            access_url, days_back=30
        )

        if not raw_data:
            flash("Failed to fetch accounts from SimpleFin. Please try again.")
            return redirect(url_for("advanced"))

        # Process the raw data
        accounts = simplefin_client.process_raw_accounts(raw_data)

        # Filter to only selected accounts
        selected_accounts = []
        for account in accounts:
            if account.get("id") in account_ids:
                # Apply customizations from form data
                account_id = account.get("id")

                # Get custom account name if provided
                custom_name = request.form.get(f"account_name_{account_id}")
                if custom_name and custom_name.strip():
                    account["name"] = custom_name.strip()

                # Get custom account type if provided
                custom_type = request.form.get(f"account_type_{account_id}")
                if custom_type:
                    account["type"] = custom_type

                selected_accounts.append(account)

        # Count for success message
        accounts_added = 0
        transactions_added = 0

        # Get the user's default currency
        default_currency = current_user.default_currency_code or "USD"

        # Process and add each selected account
        for sf_account in selected_accounts:
            # Check if account already exists
            existing_account = Account.query.filter_by(
                user_id=current_user.id,
                name=sf_account.get("name"),
                institution=sf_account.get("institution"),
            ).first()

            account_obj = None

            if existing_account:
                # Update existing account
                existing_account.balance = sf_account.get("balance", 0)
                existing_account.import_source = "simplefin"
                existing_account.last_sync = datetime.now(tz.utc)
                existing_account.external_id = sf_account.get("id")
                existing_account.status = "active"
                existing_account.type = sf_account.get(
                    "type"
                )  # Apply custom type
                db.session.commit()
                accounts_added += 1
                account_obj = existing_account
            else:
                # Create new account with custom values
                new_account = Account(
                    name=sf_account.get("name"),  # Custom name from form
                    type=sf_account.get("type"),  # Custom type from form
                    institution=sf_account.get("institution"),
                    balance=sf_account.get("balance", 0),
                    currency_code=sf_account.get(
                        "currency_code", default_currency
                    ),
                    user_id=current_user.id,
                    import_source="simplefin",
                    external_id=sf_account.get("id"),
                    last_sync=datetime.now(tz.utc),
                    status="active",
                )
                db.session.add(new_account)
                db.session.flush()  # Get ID without committing
                accounts_added += 1
                account_obj = new_account

            # Create transaction objects using the enhanced client method
            transaction_objects, import_count = (
                simplefin_client.create_transactions_from_account(
                    sf_account,
                    account_obj,
                    current_user.id,
                    detect_internal_transfer,  # Your transfer detection function
                    auto_categorize_transaction,  # Your auto-categorization function
                    get_category_id,  # Your function to find/create categories
                )
            )

            # Check for existing transactions to avoid duplicates
            transaction_objects_filtered = []
            for transaction in transaction_objects:
                existing = Expense.query.filter_by(
                    user_id=current_user.id,
                    external_id=transaction.external_id,
                    import_source="simplefin",
                ).first()

                if not existing:
                    transaction_objects_filtered.append(transaction)

            # Add filtered transactions to the session
            for transaction in transaction_objects_filtered:
                db.session.add(transaction)
                transactions_added += 1

                # Handle account balance updates for transfers
                if (
                    transaction.transaction_type == "transfer"
                    and transaction.destination_account_id
                ):
                    # Find the destination account
                    to_account = Account.query.get(
                        transaction.destination_account_id
                    )
                    if to_account and to_account.user_id == current_user.id:
                        # For transfers, add to destination account balance
                        to_account.balance += transaction.amount

        # Commit all changes
        db.session.commit()

        # Update the SimpleFin settings to record the sync time
        simplefin_settings.last_sync = datetime.now(tz.utc)
        db.session.commit()

        flash(
            f"Successfully added {accounts_added} accounts and "
            f"{transactions_added} transactions from SimpleFin."
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error adding SimpleFin accounts")
        flash(f"Error adding accounts: {e!s}")

    return redirect(url_for("accounts"))


@simplefin_bp.route("/sync_account/<int:account_id>", methods=["POST"])
@login_required_dev
def sync_account(account_id):
    """Sync transactions for a specific account."""
    try:
        account = Account.query.get_or_404(account_id)

        # Security check
        if account.user_id != current_user.id:
            return jsonify(
                {
                    "success": False,
                    "message": "You don't have permission to sync this account",
                }
            ), 403

        # Check if this is a SimpleFin account
        if account.import_source != "simplefin" or not account.external_id:
            return jsonify(
                {
                    "success": False,
                    "message": "This account is not connected to SimpleFin",
                }
            ), 400

        # Get the user's SimpleFin access URL
        simplefin_settings = SimpleFin.query.filter_by(
            user_id=current_user.id
        ).first()

        if not simplefin_settings or not simplefin_settings.access_url:
            return jsonify(
                {
                    "success": False,
                    "message": "No SimpleFin connection found. Please reconnect with SimpleFin.",
                    "action": "reconnect",
                    "redirect": url_for("connect_simplefin"),
                }
            )

        # Decode the access URL
        access_url = base64.b64decode(
            simplefin_settings.access_url.encode()
        ).decode()

        # Fetch accounts and transactions
        raw_data = simplefin_client.get_accounts_with_transactions(
            access_url, days_back=7
        )  # Last 7 days for manual sync

        if not raw_data:
            return jsonify(
                {
                    "success": False,
                    "message": "Failed to fetch data from SimpleFin.",
                }
            ), 500

        # Process the raw data
        accounts = simplefin_client.process_raw_accounts(raw_data)

        # Find the matching account
        sf_account = next(
            (acc for acc in accounts if acc.get("id") == account.external_id),
            None,
        )

        if not sf_account:
            return jsonify(
                {
                    "success": False,
                    "message": "Account not found in SimpleFin data.",
                }
            ), 404

        # Update account details
        account.balance = sf_account.get("balance", account.balance)
        account.last_sync = datetime.now(tz.utc)

        # Create transaction objects using the enhanced client method
        transaction_objects, _ = (
            simplefin_client.create_transactions_from_account(
                sf_account,
                account,
                current_user.id,
                detect_internal_transfer,
                auto_categorize_transaction,
                get_category_id,
            )
        )

        # Track new transactions
        new_transactions = 0

        # Filter out existing transactions and add new ones
        for transaction in transaction_objects:
            # Check if transaction already exists
            existing = Expense.query.filter_by(
                user_id=current_user.id,
                external_id=transaction.external_id,
                import_source="simplefin",
            ).first()

            if not existing:
                db.session.add(transaction)
                new_transactions += 1

                # Handle account balance updates for transfers
                if (
                    transaction.transaction_type == "transfer"
                    and transaction.destination_account_id
                ):
                    # Find the destination account
                    to_account = Account.query.get(
                        transaction.destination_account_id
                    )
                    if to_account and to_account.user_id == current_user.id:
                        # For transfers, add to destination account balance
                        to_account.balance += transaction.amount

        # Commit changes
        db.session.commit()

        # Update the SimpleFin settings last_sync time
        if simplefin_settings:
            simplefin_settings.last_sync = datetime.now(tz.utc)
            db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Account synced successfully. {new_transactions} new transactions imported.",
                "new_transactions": new_transactions,
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error syncing account %s", account_id)
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500


@simplefin_bp.route("/disconnect_account/<int:account_id>", methods=["POST"])
@login_required_dev
def disconnect_account(account_id):
    """Disconnect an account from SimpleFin."""
    try:
        account = Account.query.get_or_404(account_id)

        # Security check
        if account.user_id != current_user.id:
            return jsonify(
                {
                    "success": False,
                    "message": "You do not have permission to disconnect this account",
                }
            ), 403

        # Check if this is a SimpleFin account
        if account.import_source != "simplefin":
            return jsonify(
                {
                    "success": False,
                    "message": "This account is not connected to SimpleFin",
                }
            ), 400

        # Update account to remove SimpleFin connection
        account.import_source = None
        account.external_id = None
        account.status = "inactive"
        db.session.commit()

        return jsonify(
            {"success": True, "message": "Account disconnected successfully"}
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(
            "Error disconnecting account %s", account_id
        )
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500


@simplefin_bp.route("/simplefin/disconnect", methods=["POST"])
@login_required_dev
def simplefin_disconnect():
    """Disconnect SimpleFin integration for the current user."""
    if not current_app.config["SIMPLEFIN_ENABLED"]:
        return jsonify(
            {
                "success": False,
                "message": "SimpleFin integration is not enabled.",
            }
        )

    try:
        # Get the user's SimpleFin settings
        simplefin_settings = SimpleFin.query.filter_by(
            user_id=current_user.id
        ).first()

        if not simplefin_settings:
            return jsonify(
                {"success": False, "message": "No SimpleFin connection found."}
            )

        # Disable the SimpleFin integration
        simplefin_settings.enabled = False
        db.session.commit()

        # Also update all SimpleFin-connected accounts to show as disconnected
        accounts = Account.query.filter_by(
            user_id=current_user.id, import_source="simplefin"
        ).all()

        for account in accounts:
            account.import_source = None
            account.external_id = None
            account.status = "inactive"

        db.session.commit()

        return jsonify(
            {"success": True, "message": "SimpleFin disconnected successfully"}
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error disconnecting SimpleFin:")
        return jsonify({"success": False, "message": f"Error: {e!s}"})


@simplefin_bp.route("/simplefin/refresh", methods=["POST"])
@login_required_dev
def simplefin_refresh():
    """Refresh SimpleFin connection and trigger a sync."""
    if not current_app.config["SIMPLEFIN_ENABLED"]:
        return jsonify(
            {
                "success": False,
                "message": "SimpleFin integration is not enabled.",
            }
        )

    try:
        # Get the user's SimpleFin settings
        simplefin_settings = SimpleFin.query.filter_by(
            user_id=current_user.id
        ).first()

        if (
            not simplefin_settings
            or not simplefin_settings.access_url
            or not simplefin_settings.enabled
        ):
            # No valid connection, redirect to get a new setup token
            return jsonify(
                {
                    "success": False,
                    "message": "No valid SimpleFin connection found. Please reconnect.",
                    "redirect": url_for("connect_simplefin"),
                }
            )

        # Decode the access URL and test it
        access_url = base64.b64decode(
            simplefin_settings.access_url.encode()
        ).decode()

        if not simplefin_client.test_access_url(access_url):
            # Access URL no longer valid, redirect to get a new setup token
            return jsonify(
                {
                    "success": False,
                    "message": "Your SimpleFin connection has expired. Please reconnect.",
                    "redirect": url_for("connect_simplefin"),
                }
            )

        # Access URL still valid, redirect to fetch accounts
        return jsonify(
            {
                "success": True,
                "message": "SimpleFin connection is valid. Fetching accounts...",
                "redirect": url_for("simplefin_fetch_accounts"),
            }
        )

    except Exception as e:
        current_app.logger.exception("Error refreshing SimpleFin")
        return jsonify({"success": False, "message": f"Error: {e!s}"})


@simplefin_bp.route("/simplefin/run_scheduled_sync", methods=["POST"])
@login_required_dev
def run_scheduled_simplefin_sync():
    """Manually trigger the scheduled SimpleFin sync (admin only)."""
    if not current_user.is_admin:
        flash("Only administrators can manually trigger the scheduled sync.")
        return redirect(url_for("admin"))

    try:
        # Run the sync function
        sync_all_simplefin_accounts()
        flash("SimpleFin scheduled sync completed successfully!")
    except Exception as e:
        current_app.logger.exception("Error running scheduled SimpleFin sync")
        flash(f"Error running scheduled sync: {e!s}")

    return redirect(url_for("admin"))


# Function to sync all SimpleFin accounts for all users
def sync_all_simplefin_accounts():
    """Sync all SimpleFin accounts for all users - runs on a schedule"""
    with current_app.app_context():
        current_app.logger.info(
            "Starting scheduled SimpleFin sync for all users"
        )

        try:
            # Get all users with SimpleFin settings
            settings_list = SimpleFin.query.filter_by(enabled=True).all()

            for settings in settings_list:
                # Skip if last sync was less than 12 hours ago
                # (to prevent excessive syncing)
                if (
                    settings.last_sync
                    and (datetime(tz.utc) - settings.last_sync).total_seconds()
                    < 43200
                ):  # 12 hours
                    continue

                # Get the user
                user = User.query.filter_by(id=settings.user_id).first()
                if not user:
                    continue

                # Decode the access URL
                try:
                    access_url = base64.b64decode(
                        settings.access_url.encode()
                    ).decode()
                except:
                    current_app.logger.exception(
                        "Error decoding access URL for user %s",
                        settings.user_id,
                    )
                    continue

                # Fetch accounts and transactions (last 3 days for scheduled sync)
                raw_data = simplefin_client.get_accounts_with_transactions(
                    access_url, days_back=3
                )

                if not raw_data:
                    current_app.logger.exception(
                        "Failed to fetch SimpleFin data for user %s",
                        settings.user_id,
                    )
                    continue

                # Process the raw data
                accounts = simplefin_client.process_raw_accounts(raw_data)

                # Find all SimpleFin accounts for this user
                user_accounts = Account.query.filter_by(
                    user_id=settings.user_id, import_source="simplefin"
                ).all()

                # Create a mapping of external IDs to account objects
                account_map = {
                    acc.external_id: acc
                    for acc in user_accounts
                    if acc.external_id
                }

                # Track statistics
                accounts_updated = 0
                transactions_added = 0

                # Update each account
                for sf_account in accounts:
                    external_id = sf_account.get("id")
                    if not external_id:
                        continue

                    # Find the corresponding account
                    if external_id in account_map:
                        account = account_map[external_id]

                        # Update account details
                        account.balance = sf_account.get(
                            "balance", account.balance
                        )
                        account.last_sync = datetime.now(tz.utc)
                        accounts_updated += 1

                        # Create transaction objects using the enhanced client method
                        transaction_objects, _ = (
                            simplefin_client.create_transactions_from_account(
                                sf_account,
                                account,
                                settings.user_id,
                                detect_internal_transfer,
                                auto_categorize_transaction,
                                get_category_id,
                            )
                        )

                        # Filter out existing transactions and add new ones
                        for transaction in transaction_objects:
                            # Check if transaction already exists
                            existing = Expense.query.filter_by(
                                user_id=settings.user_id,
                                external_id=transaction.external_id,
                                import_source="simplefin",
                            ).first()

                            if not existing:
                                db.session.add(transaction)
                                transactions_added += 1

                                # Handle account balance updates for transfers
                                if (
                                    transaction.transaction_type == "transfer"
                                    and transaction.destination_account_id
                                ):
                                    # Find the destination account
                                    to_account = Account.query.get(
                                        transaction.destination_account_id
                                    )
                                    if (
                                        to_account
                                        and to_account.user_id
                                        == settings.user_id
                                    ):
                                        # For transfers,
                                        # add to destination account balance
                                        to_account.balance += transaction.amount

                # Commit changes for this user
                if accounts_updated > 0 or transactions_added > 0:
                    db.session.commit()

                    # Update the SimpleFin settings last_sync time
                    settings.last_sync = datetime.now(tz.utc)
                    db.session.commit()

                    current_app.logger.info(
                        f"SimpleFin sync for user {settings.user_id}: {accounts_updated} accounts updated, {transactions_added} transactions added"
                    )

        except Exception:
            db.session.rollback()
            current_app.logger.exception("Error in scheduled SimpleFin sync")


def sync_simplefin_for_user(user_id):
    """Sync SimpleFin accounts for a specific user - to be called on login."""
    with current_app.app_context():
        current_app.logger.info(
            "Starting SimpleFin sync for user %s on login", user_id
        )

        try:
            # Get the user's SimpleFin settings
            settings = SimpleFin.query.filter_by(
                user_id=user_id, enabled=True
            ).first()

            if not settings:
                current_app.logger.info(
                    "No SimpleFin settings found for user %s", user_id
                )
                return

            # Decode the access URL
            try:
                access_url = base64.b64decode(
                    settings.access_url.encode()
                ).decode()
            except:
                current_app.logger.exception(
                    "Error decoding access URL for user %s", user_id
                )
                return

            # Fetch accounts and transactions (last 3 days for a login sync)
            simplefin_instance = simplefin_client
            raw_data = simplefin_instance.get_accounts_with_transactions(
                access_url, days_back=3
            )

            if not raw_data:
                current_app.logger.error(
                    "Failed to fetch SimpleFin data for user %s", user_id
                )
                return

            # Process the raw data
            accounts = simplefin_instance.process_raw_accounts(raw_data)

            # Find all SimpleFin accounts for this user
            user_accounts = Account.query.filter_by(
                user_id=user_id, import_source="simplefin"
            ).all()

            # Create a mapping of external IDs to account objects
            account_map = {
                acc.external_id: acc for acc in user_accounts if acc.external_id
            }

            # Track statistics
            accounts_updated = 0
            transactions_added = 0

            # Update each account
            for sf_account in accounts:
                external_id = sf_account.get("id")
                if not external_id:
                    continue

                # Find the corresponding account
                if external_id in account_map:
                    account = account_map[external_id]

                    # Update account details
                    account.balance = sf_account.get("balance", account.balance)
                    account.last_sync = datetime.now(tz.utc)
                    accounts_updated += 1

                    # Create transaction objects
                    transaction_objects, _ = (
                        simplefin_instance.create_transactions_from_account(
                            sf_account,
                            account,
                            user_id,
                            detect_internal_transfer,
                            auto_categorize_transaction,
                            get_category_id,
                        )
                    )

                    # Filter out existing transactions and add new ones
                    for transaction in transaction_objects:
                        # Check if transaction already exists
                        existing = Expense.query.filter_by(
                            user_id=user_id,
                            external_id=transaction.external_id,
                            import_source="simplefin",
                        ).first()

                        if not existing:
                            db.session.add(transaction)
                            transactions_added += 1

                            # Handle account balance updates for transfers
                            if (
                                transaction.transaction_type == "transfer"
                                and transaction.destination_account_id
                            ):
                                # Find the destination account
                                to_account = Account.query.get(
                                    transaction.destination_account_id
                                )
                                if to_account and to_account.user_id == user_id:
                                    # For transfers, add to destination account balance
                                    to_account.balance += transaction.amount

            # Commit changes for this user
            if accounts_updated > 0 or transactions_added > 0:
                db.session.commit()

                # Update the SimpleFin settings last_sync time
                settings.last_sync = datetime.now(tz.utc)
                db.session.commit()

                current_app.logger.info(
                    f"SimpleFin sync on login for user {user_id}: {accounts_updated} accounts updated, {transactions_added} transactions added"
                )

        except Exception:
            db.session.rollback()
            current_app.logger.exception("Error in SimpleFin sync on login")
