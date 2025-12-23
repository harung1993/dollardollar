"""
Budget Routes
Flask Blueprint for budget management endpoints
"""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from src.utils.decorators import login_required_dev, restrict_demo_access
from src.services.budget.service import BudgetService
from src.models.category import Category
from src.utils.currency_converter import get_base_currency

# Create Blueprint
bp = Blueprint('budget', __name__, url_prefix='/budgets')

# Initialize service
budget_service = BudgetService()


# ========== BUDGET MANAGEMENT ROUTES ==========

@bp.route('/')
@login_required_dev
def budgets():
    """View and manage budgets"""
    # Get all budgets with calculated data
    budget_data, total_month_budget, total_month_spent = budget_service.get_all_budgets(current_user.id)

    # Get all categories for the form
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()

    # Get base currency for display
    base_currency = get_base_currency()

    # Pass the current date to the template
    now = datetime.now()

    return render_template('budgets.html',
                          budget_data=budget_data,
                          categories=categories,
                          base_currency=base_currency,
                          total_month_budget=total_month_budget,
                          total_month_spent=total_month_spent,
                          now=now)


@bp.route('/add', methods=['POST'])
@login_required_dev
@restrict_demo_access
def add_budget():
    """Add a new budget"""
    category_id = request.form.get('category_id')
    amount = request.form.get('amount', 0)
    period = request.form.get('period', 'monthly')
    include_subcategories = request.form.get('include_subcategories') == 'on'
    name = request.form.get('name', '').strip() or None
    start_date = request.form.get('start_date')
    is_recurring = request.form.get('is_recurring') == 'on'

    success, message, budget = budget_service.add_budget(
        current_user.id, category_id, amount, period,
        include_subcategories, name, start_date, is_recurring
    )

    flash(message)
    return redirect(url_for('budget.budgets'))


@bp.route('/edit/<int:budget_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def edit_budget(budget_id):
    """Edit an existing budget"""
    category_id = request.form.get('category_id')
    name = request.form.get('name', '').strip()
    amount = request.form.get('amount')
    period = request.form.get('period')
    include_subcategories = request.form.get('include_subcategories') == 'on'
    start_date = request.form.get('start_date')
    is_recurring = request.form.get('is_recurring') == 'on'

    success, message = budget_service.update_budget(
        budget_id, current_user.id,
        category_id=category_id,
        name=name if name else None,
        amount=amount,
        period=period,
        include_subcategories=include_subcategories,
        start_date=start_date,
        is_recurring=is_recurring
    )

    flash(message)
    return redirect(url_for('budget.budgets'))


@bp.route('/toggle/<int:budget_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def toggle_budget(budget_id):
    """Toggle budget active status"""
    success, message, new_status = budget_service.toggle_budget(budget_id, current_user.id)

    flash(message)
    return redirect(url_for('budget.budgets'))


@bp.route('/delete/<int:budget_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def delete_budget(budget_id):
    """Delete a budget"""
    success, message = budget_service.delete_budget(budget_id, current_user.id)

    flash(message)
    return redirect(url_for('budget.budgets'))


@bp.route('/get/<int:budget_id>', methods=['GET'])
@login_required_dev
def get_budget(budget_id):
    """Get budget details via AJAX"""
    success, message, budget = budget_service.get_budget(budget_id, current_user.id)

    if success:
        return jsonify({
            'success': True,
            'budget': {
                'id': budget.id,
                'name': budget.name,
                'category_id': budget.category_id,
                'amount': budget.amount,
                'period': budget.period,
                'include_subcategories': budget.include_subcategories,
                'start_date': budget.start_date.strftime('%Y-%m-%d') if budget.start_date else None,
                'is_recurring': budget.is_recurring,
                'active': budget.active
            }
        })
    else:
        status_code = 403 if 'permission' in message else 404 if 'not found' in message else 500
        return jsonify({
            'success': False,
            'message': message
        }), status_code


# ========== BUDGET ANALYSIS ROUTES ==========

@bp.route('/subcategory-spending/<int:budget_id>')
@login_required_dev
def subcategory_spending(budget_id):
    """Get subcategory spending breakdown for a budget"""
    success, message, spending_data = budget_service.get_subcategory_spending(budget_id, current_user.id)

    if success:
        return jsonify({
            'success': True,
            'spending': [{
                'subcategory_name': item['subcategory'].name,
                'amount': item['amount'],
                'count': item['count']
            } for item in spending_data]
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


@bp.route('/transactions/<int:budget_id>')
@login_required_dev
def budget_transactions(budget_id):
    """Get all transactions for a budget"""
    success, message, transactions = budget_service.get_budget_transactions(budget_id, current_user.id)

    if not success:
        flash(message)
        return redirect(url_for('budget.budgets'))

    # Get budget info
    success_budget, _, budget = budget_service.get_budget(budget_id, current_user.id)

    return render_template('budget_transactions.html',
                          budget=budget,
                          transactions=transactions)


@bp.route('/trends-data')
@login_required_dev
def trends_data():
    """Get budget trends data for charts"""
    trends = budget_service.get_trends_data(current_user.id)

    return jsonify({
        'success': True,
        'trends': [{
            'budget_id': trend['budget'].id,
            'budget_name': trend['budget'].name,
            'data': trend['historical_data']
        } for trend in trends]
    })


@bp.route('/summary-data')
@login_required_dev
def summary_data():
    """Get budget summary data for overview"""
    summary = budget_service.get_summary_data(current_user.id)

    return jsonify({
        'success': True,
        'summary': summary
    })
