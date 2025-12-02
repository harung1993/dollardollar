"""
Transaction Routes
Flask Blueprint for transaction and tag management endpoints
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from src.utils.decorators import login_required_dev, restrict_demo_access
from src.services.transaction.service import TransactionService, TagService
from src.models.user import User
from src.models.currency import Currency
from src.models.account import Account
from src.models.group import Group
from src.models.category import Category

# Create Blueprints
bp = Blueprint('transaction', __name__)
tag_bp = Blueprint('tag', __name__, url_prefix='/tags')

# Initialize services
transaction_service = TransactionService()
tag_service = TagService()


# ========== TRANSACTION CRUD ROUTES ==========

@bp.route('/add_expense', methods=['POST'])
@login_required_dev
@restrict_demo_access
def add_expense():
    """Add a new transaction with improved handling and AJAX support"""
    success, message, transaction_id = transaction_service.add_transaction(
        current_user.id,
        request.form
    )

    if success:
        return jsonify({
            'success': True,
            'message': message,
            'transaction_id': transaction_id
        })
    else:
        status_code = 400 if 'Amount' in message or 'Invalid' in message or 'same' in message else 500
        return jsonify({
            'success': False,
            'message': message
        }), status_code


@bp.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def delete_expense(expense_id):
    """Delete an expense by ID and update account balances"""
    success, message = transaction_service.delete_transaction(expense_id, current_user.id)

    if success:
        return jsonify({
            'success': True,
            'message': message
        })
    else:
        status_code = 403 if 'Permission' in message else 500
        return jsonify({
            'success': False,
            'message': message
        }), status_code


@bp.route('/get_expense/<int:expense_id>', methods=['GET'])
@login_required_dev
def get_expense(expense_id):
    """Get expense details for editing"""
    success, message, expense_data = transaction_service.get_transaction(expense_id, current_user.id)

    if success:
        return jsonify({
            'success': True,
            'expense': expense_data
        })
    else:
        status_code = 403 if 'permission' in message else 404 if 'not found' in message else 500
        return jsonify({
            'success': False,
            'message': message
        }), status_code


@bp.route('/update_expense/<int:expense_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def update_expense(expense_id):
    """Update an expense with improved error handling and AJAX support"""
    success, message = transaction_service.update_transaction(
        expense_id,
        current_user.id,
        request.form
    )

    if success:
        return jsonify({
            'success': True,
            'message': message
        })
    else:
        status_code = 400 if 'Invalid' in message or 'permission' in message else 500
        return jsonify({
            'success': False,
            'message': message
        }), status_code


# ========== TRANSACTION LISTING ROUTES ==========

@bp.route('/transactions')
@login_required_dev
def transactions():
    """Display all transactions with filtering capabilities"""
    # Get all transactions and splits
    expenses, expense_splits = transaction_service.get_all_transactions(current_user.id)

    # Calculate totals
    year_total, month_total = transaction_service.calculate_user_totals(
        current_user.id,
        expenses,
        expense_splits
    )

    # Calculate monthly totals for statistics
    from datetime import datetime
    monthly_totals = {}
    unique_cards = set()

    for expense in expenses:
        month_key = expense.date.strftime('%Y-%m')
        if month_key not in monthly_totals:
            monthly_totals[month_key] = {
                'total': 0.0,
                'by_card': {},
                'contributors': {}
            }

        # Add to monthly totals
        monthly_totals[month_key]['total'] += expense.amount

        # Add card to total
        if expense.card_used not in monthly_totals[month_key]['by_card']:
            monthly_totals[month_key]['by_card'][expense.card_used] = 0
        monthly_totals[month_key]['by_card'][expense.card_used] += expense.amount

        # Track unique cards where current user paid
        if expense.paid_by == current_user.id:
            unique_cards.add(expense.card_used)

        # Add contributors' data
        splits = expense_splits[expense.id]

        # Add payer's portion
        if splits['payer']['amount'] > 0:
            user_id = splits['payer']['email']
            if user_id not in monthly_totals[month_key]['contributors']:
                monthly_totals[month_key]['contributors'][user_id] = 0
            monthly_totals[month_key]['contributors'][user_id] += splits['payer']['amount']

        # Add other contributors' portions
        for split in splits['splits']:
            user_id = split['email']
            if user_id not in monthly_totals[month_key]['contributors']:
                monthly_totals[month_key]['contributors'][user_id] = 0
            monthly_totals[month_key]['contributors'][user_id] += split['amount']

    # Get supporting data
    users = User.query.all()
    from src.models.currency import Currency
    from src.utils.currency_converter import get_base_currency
    base_currency = get_base_currency()
    currencies = Currency.query.all()

    return render_template('transactions.html',
                          expenses=expenses,
                          expense_splits=expense_splits,
                          monthly_totals=monthly_totals,
                          total_expenses=year_total,
                          current_month_total=month_total,
                          unique_cards=unique_cards,
                          users=users,
                          base_currency=base_currency,
                          currencies=currencies)


@bp.route('/get_transaction_form_html')
@login_required_dev
def get_transaction_form_html():
    """Return transaction form HTML for AJAX loading"""
    # Get data for form dropdowns
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    groups = Group.query.filter(
        Group.members.any(id=current_user.id)
    ).all()
    categories = Category.query.filter_by(user_id=current_user.id, parent_id=None).all()
    currencies = Currency.query.all()

    return render_template('partials/transaction_form.html',
                          accounts=accounts,
                          groups=groups,
                          categories=categories,
                          currencies=currencies,
                          current_user=current_user)


@bp.route('/get_expense_edit_form/<int:expense_id>')
@login_required_dev
def get_expense_edit_form(expense_id):
    """Return expense edit form HTML for AJAX loading"""
    success, message, expense_data = transaction_service.get_transaction(expense_id, current_user.id)

    if not success:
        return jsonify({
            'success': False,
            'message': message
        }), 404

    # Get data for form dropdowns
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    groups = Group.query.filter(
        Group.members.any(id=current_user.id)
    ).all()
    categories = Category.query.filter_by(user_id=current_user.id, parent_id=None).all()
    currencies = Currency.query.all()

    return render_template('partials/expense_edit_form.html',
                          expense=expense_data,
                          accounts=accounts,
                          groups=groups,
                          categories=categories,
                          currencies=currencies,
                          current_user=current_user)


@bp.route('/get_category_splits/<int:expense_id>')
@login_required_dev
def get_category_splits(expense_id):
    """Get category splits for an expense"""
    from src.models.transaction import Expense, CategorySplit

    expense = Expense.query.get_or_404(expense_id)

    # Security check
    if expense.user_id != current_user.id:
        return jsonify({
            'success': False,
            'message': 'Permission denied'
        }), 403

    # Get category splits
    category_splits = CategorySplit.query.filter_by(expense_id=expense_id).all()

    splits_data = []
    for split in category_splits:
        category = Category.query.get(split.category_id)
        splits_data.append({
            'category_id': split.category_id,
            'category_name': category.name if category else 'Unknown',
            'amount': split.amount
        })

    return jsonify({
        'success': True,
        'splits': splits_data
    })


@bp.route('/export_transactions', methods=['POST'])
@login_required_dev
def export_transactions():
    """Export transactions to CSV"""
    import csv
    import io
    from flask import make_response

    # Get all transactions
    expenses, expense_splits = transaction_service.get_all_transactions(current_user.id)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Date', 'Description', 'Amount', 'Currency', 'Type',
        'Category', 'Account', 'Paid By', 'Group', 'Split Method'
    ])

    # Write transaction rows
    for expense in expenses:
        category_name = ''
        if expense.category:
            category_name = expense.category.name

        account_name = ''
        if expense.account:
            account_name = expense.account.name

        paid_by_name = ''
        if expense.paid_by:
            payer = User.query.get(expense.paid_by)
            if payer:
                paid_by_name = payer.name

        group_name = ''
        if expense.group:
            group_name = expense.group.name

        writer.writerow([
            expense.date.strftime('%Y-%m-%d'),
            expense.description,
            expense.amount,
            expense.currency_code or 'USD',
            expense.transaction_type or 'expense',
            category_name,
            account_name,
            paid_by_name,
            group_name,
            expense.split_method
        ])

    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=transactions.csv'

    return response


# ========== TAG MANAGEMENT ROUTES ==========

@tag_bp.route('/')
@login_required_dev
def manage_tags():
    """View and manage tags"""
    tags = tag_service.get_all_tags(current_user.id)
    return render_template('tags.html', tags=tags)


@tag_bp.route('/add', methods=['POST'])
@login_required_dev
@restrict_demo_access
def add_tag():
    """Add a new tag"""
    name = request.form.get('name')
    success, message, tag = tag_service.add_tag(current_user.id, name)

    flash(message)
    return redirect(url_for('tag.manage_tags'))


@tag_bp.route('/delete/<int:tag_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def delete_tag(tag_id):
    """Delete a tag"""
    success, message = tag_service.delete_tag(tag_id, current_user.id)

    flash(message)
    return redirect(url_for('tag.manage_tags'))
