"""
Recurring Routes
Flask Blueprint for recurring transaction management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from src.utils.decorators import login_required_dev, restrict_demo_access
from src.services.recurring.service import RecurringService
from src.models.category import Category
from src.models.account import Account

bp = Blueprint('recurring', __name__, url_prefix='/recurring')
recurring_service = RecurringService()

@bp.route('')
@login_required_dev
def recurring():
    """View all recurring expenses"""
    from src.models.user import User
    from src.models.group import Group
    from src.models.currency import Currency
    from src.models.associations import group_users
    from src.utils.currency_converter import get_base_currency

    base_currency = get_base_currency()
    recurring_expenses = recurring_service.get_all_recurring(current_user.id)
    users = User.query.all()
    groups = Group.query.join(group_users).filter(group_users.c.user_id == current_user.id).all()
    currencies = Currency.query.all()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    accounts = Account.query.filter_by(user_id=current_user.id).all()

    return render_template('recurring.html',
                         recurring_expenses=recurring_expenses,
                         users=users,
                         currencies=currencies,
                         categories=categories,
                         groups=groups,
                         base_currency=base_currency,
                         accounts=accounts)

@bp.route('/add', methods=['POST'])
@login_required_dev
@restrict_demo_access
def add_recurring():
    """Add new recurring expense"""
    success, message, _ = recurring_service.add_recurring(
        current_user.id,
        request.form.get('description'),
        request.form.get('amount'),
        request.form.get('frequency'),
        request.form.get('category_id'),
        request.form.get('start_date'),
        request.form.get('account_id'),
        request.form.get('currency_code')
    )
    flash(message)
    return redirect(url_for('recurring.recurring'))

@bp.route('/toggle/<int:recurring_id>', methods=['POST'])
@login_required_dev
def toggle_recurring(recurring_id):
    """Toggle recurring expense active status"""
    success, message, _ = recurring_service.toggle_recurring(recurring_id, current_user.id)
    flash(message)
    return redirect(url_for('recurring.recurring'))

@bp.route('/delete/<int:recurring_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def delete_recurring(recurring_id):
    """Delete recurring expense"""
    success, message = recurring_service.delete_recurring(recurring_id, current_user.id)
    flash(message)
    return redirect(url_for('recurring.recurring'))

@bp.route('/detect')
@login_required_dev
def detect_recurring_transactions():
    """Detect recurring patterns"""
    candidates = recurring_service.detect_recurring_patterns(current_user.id)
    return render_template('recurring_detection.html', candidates=candidates)

@bp.route('/manage_ignored_patterns')
@login_required_dev
def manage_ignored_patterns():
    """Manage ignored recurring patterns"""
    from src.models.recurring import IgnoredRecurringPattern
    ignored_patterns = IgnoredRecurringPattern.query.filter_by(user_id=current_user.id).all()
    return render_template('manage_ignored_patterns.html',
                         ignored_patterns=ignored_patterns)
