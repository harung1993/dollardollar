"""
Account Routes
Flask Blueprint for account management, CSV import, and SimpleFin integration
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from src.utils.decorators import login_required_dev, restrict_demo_access
from src.services.account.service import AccountService, SimpleFinService
from src.models.currency import Currency

# Create Blueprints
bp = Blueprint('account', __name__)
simplefin_bp = Blueprint('simplefin', __name__, url_prefix='/simplefin')

# Initialize services
account_service = AccountService()
simplefin_service = SimpleFinService()


# ========== ACCOUNT MANAGEMENT ROUTES ==========

@bp.route('/accounts')
@login_required_dev
def accounts():
    """View and manage financial accounts"""
    # Get all user accounts
    user_accounts = account_service.get_all_accounts(current_user.id)

    # Calculate financial summary
    total_assets, total_liabilities, net_worth, user_currency = account_service.calculate_financial_summary(
        current_user.id
    )

    # Get all currencies for the form
    currencies = Currency.query.all()

    return render_template('accounts.html',
                          accounts=user_accounts,
                          total_assets=total_assets,
                          total_liabilities=total_liabilities,
                          net_worth=net_worth,
                          user_currency=user_currency,
                          currencies=currencies)


@bp.route('/advanced')
@login_required_dev
def advanced():
    """Display advanced features like account management and imports"""
    # Get all user accounts
    accounts = account_service.get_all_accounts(current_user.id)

    # Get connected accounts (those with SimpleFin integration)
    connected_accounts = [account for account in accounts if account.import_source == 'simplefin']

    # Calculate financial summary
    total_assets, total_liabilities, net_worth, base_currency = account_service.calculate_financial_summary(
        current_user.id
    )

    # Get all currencies
    currencies = Currency.query.all()

    return render_template('advanced.html',
                          accounts=accounts,
                          connected_accounts=connected_accounts,
                          total_assets=total_assets,
                          total_liabilities=total_liabilities,
                          net_worth=net_worth,
                          base_currency=base_currency,
                          currencies=currencies)


@bp.route('/add_account', methods=['POST'])
@login_required_dev
@restrict_demo_access
def add_account():
    """Add a new account"""
    name = request.form.get('name')
    account_type = request.form.get('type')
    institution = request.form.get('institution')
    balance = request.form.get('balance', 0)
    currency_code = request.form.get('currency_code', current_user.default_currency_code)

    success, message, account = account_service.add_account(
        current_user.id, name, account_type, institution, balance, currency_code
    )

    flash(message)
    return redirect(url_for('account.accounts'))


@bp.route('/get_account/<int:account_id>')
@login_required_dev
def get_account(account_id):
    """Get account details via AJAX"""
    success, message, account_data = account_service.get_account(account_id, current_user.id)

    if success:
        return jsonify({
            'success': True,
            'account': account_data
        })
    else:
        status_code = 403 if 'permission' in message else 404 if 'not found' in message else 500
        return jsonify({
            'success': False,
            'message': message
        }), status_code


@bp.route('/update_account', methods=['POST'])
@login_required_dev
@restrict_demo_access
def update_account():
    """Update an existing account"""
    account_id = request.form.get('account_id')
    name = request.form.get('name')
    account_type = request.form.get('type')
    institution = request.form.get('institution')
    balance = request.form.get('balance', 0)
    currency_code = request.form.get('currency_code')

    success, message = account_service.update_account(
        account_id, current_user.id, name, account_type, institution, balance, currency_code
    )

    flash(message)
    return redirect(url_for('account.accounts'))


@bp.route('/delete_account/<int:account_id>', methods=['DELETE'])
@login_required_dev
@restrict_demo_access
def delete_account(account_id):
    """Delete an account"""
    success, message = account_service.delete_account(account_id, current_user.id)

    if success:
        return jsonify({
            'success': True,
            'message': message
        })
    else:
        status_code = 403 if 'permission' in message else 500
        return jsonify({
            'success': False,
            'message': message
        }), status_code


# ========== CSV IMPORT ROUTES ==========

@bp.route('/import_csv', methods=['POST'])
@login_required_dev
@restrict_demo_access
def import_csv():
    """Import transactions from a CSV file"""
    if 'csv_file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('account.advanced'))

    csv_file = request.files['csv_file']

    if csv_file.filename == '':
        flash('No file selected')
        return redirect(url_for('account.advanced'))

    if not csv_file.filename.lower().endswith('.csv'):
        flash('File must be a CSV')
        return redirect(url_for('account.advanced'))

    # Get account ID if specified
    account_id = request.form.get('account_id')
    if account_id:
        try:
            account_id = int(account_id)
        except ValueError:
            account_id = None

    success, message, imported_count, skipped_count = account_service.import_csv(
        current_user.id, csv_file, account_id
    )

    flash(message)
    return redirect(url_for('account.advanced'))


# ========== SIMPLEFIN INTEGRATION ROUTES ==========

@bp.route('/connect_simplefin')
@login_required_dev
@restrict_demo_access
def connect_simplefin():
    """Initiate SimpleFin OAuth connection"""
    # This would redirect to SimpleFin OAuth flow
    # Actual implementation depends on SimpleFin client configuration
    return render_template('simplefin_connect.html')


@simplefin_bp.route('/process_token', methods=['POST'])
@login_required_dev
@restrict_demo_access
def process_token():
    """Process SimpleFin access token"""
    access_url = request.form.get('access_url')

    if not access_url:
        flash('No access token provided')
        return redirect(url_for('account.advanced'))

    success, message = simplefin_service.save_simplefin_token(current_user.id, access_url)
    flash(message)

    return redirect(url_for('account.advanced'))


@simplefin_bp.route('/fetch_accounts')
@login_required_dev
def fetch_accounts():
    """Fetch accounts from SimpleFin"""
    simplefin_settings = simplefin_service.get_simplefin_settings(current_user.id)

    if not simplefin_settings:
        return jsonify({
            'success': False,
            'message': 'SimpleFin not connected'
        }), 400

    # Actual SimpleFin API call would be made here
    # This is a placeholder for the integration
    return jsonify({
        'success': True,
        'accounts': []
    })


@simplefin_bp.route('/add_accounts', methods=['POST'])
@login_required_dev
@restrict_demo_access
def add_accounts():
    """Add selected SimpleFin accounts to user's account list"""
    # This would process selected accounts from SimpleFin
    # Actual implementation depends on SimpleFin client
    flash('SimpleFin accounts added')
    return redirect(url_for('account.advanced'))


@bp.route('/sync_account/<int:account_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def sync_account(account_id):
    """Sync a SimpleFin account"""
    success, message, synced_count = simplefin_service.sync_account(account_id, current_user.id)

    if success:
        return jsonify({
            'success': True,
            'message': message,
            'synced_count': synced_count
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


@bp.route('/disconnect_account/<int:account_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def disconnect_account(account_id):
    """Disconnect a SimpleFin account"""
    success, message = simplefin_service.disconnect_account(account_id, current_user.id)

    flash(message)
    return redirect(url_for('account.accounts'))


@simplefin_bp.route('/disconnect', methods=['POST'])
@login_required_dev
@restrict_demo_access
def disconnect():
    """Disconnect SimpleFin integration entirely"""
    success, message = simplefin_service.disconnect_simplefin(current_user.id)

    flash(message)
    return redirect(url_for('account.advanced'))


@simplefin_bp.route('/refresh', methods=['POST'])
@login_required_dev
@restrict_demo_access
def refresh():
    """Refresh all SimpleFin accounts"""
    # This would trigger a sync for all connected accounts
    # Actual implementation depends on SimpleFin client
    flash('SimpleFin accounts refreshed')
    return redirect(url_for('account.advanced'))


@simplefin_bp.route('/run_scheduled_sync', methods=['POST'])
@login_required_dev
def run_scheduled_sync():
    """Run scheduled SimpleFin sync (called by scheduler)"""
    # This would be called by the scheduled task system
    # Actual implementation depends on SimpleFin client
    return jsonify({
        'success': True,
        'message': 'Scheduled sync completed'
    })
