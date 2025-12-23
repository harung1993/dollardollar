"""
Group Routes
Flask Blueprint for group and settlement management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from src.utils.decorators import login_required_dev, restrict_demo_access
from src.services.group.service import GroupService, SettlementService
from src.models.user import User
from src.models.category import Category
from src.models.currency import Currency
from src.utils.currency_converter import get_base_currency

# Create Blueprints
bp = Blueprint('group', __name__, url_prefix='/groups')
settlement_bp = Blueprint('settlement', __name__, url_prefix='/settlements')

# Initialize services
group_service = GroupService()
settlement_service = SettlementService()


# ========== GROUP ROUTES ==========

@bp.route('/')
@login_required_dev
def groups():
    """View all groups"""
    groups = group_service.get_all_groups(current_user.id)
    all_users = User.query.all()
    base_currency = get_base_currency()
    return render_template('groups.html', groups=groups, users=all_users, base_currency=base_currency)


@bp.route('/create', methods=['POST'])
@login_required_dev
@restrict_demo_access
def create_group():
    """Create a new group"""
    name = request.form.get('name')
    description = request.form.get('description')
    member_ids = request.form.getlist('members')
    default_split_method = request.form.get('default_split_method', 'equal')
    default_payer = request.form.get('default_payer') or None
    auto_include_all = request.form.get('auto_include_all') == 'on'
    default_split_values = request.form.get('default_split_values')

    success, message, group = group_service.create_group(
        current_user.id, name, description, member_ids,
        default_split_method, default_payer, auto_include_all, default_split_values
    )

    flash(message)
    return redirect(url_for('group.groups'))


@bp.route('/<int:group_id>')
@login_required_dev
def group_details(group_id):
    """View group details"""
    success, message, group = group_service.get_group(group_id, current_user.id)

    if not success:
        flash(message)
        return redirect(url_for('group.groups'))

    base_currency = get_base_currency()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    expenses = group_service.get_group_expenses(group_id)
    all_users = User.query.all()
    currencies = Currency.query.all()

    return render_template('group_details.html',
                          group=group,
                          expenses=expenses,
                          currencies=currencies,
                          base_currency=base_currency,
                          categories=categories,
                          users=all_users)


@bp.route('/<int:group_id>/add_member', methods=['POST'])
@login_required_dev
@restrict_demo_access
def add_member(group_id):
    """Add a member to a group"""
    member_id = request.form.get('member_id')
    success, message = group_service.add_member(group_id, current_user.id, member_id)

    flash(message)
    return redirect(url_for('group.group_details', group_id=group_id))


@bp.route('/<int:group_id>/remove_member/<member_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def remove_member(group_id, member_id):
    """Remove a member from a group"""
    success, message = group_service.remove_member(group_id, current_user.id, member_id)

    flash(message)
    return redirect(url_for('group.group_details', group_id=group_id))


@bp.route('/<int:group_id>/delete', methods=['GET', 'POST'])
@login_required_dev
@restrict_demo_access
def delete_group(group_id):
    """Delete a group"""
    success, message = group_service.delete_group(group_id, current_user.id)

    flash(message)
    return redirect(url_for('group.groups'))


@bp.route('/update_settings/<int:group_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def update_settings(group_id):
    """Update group settings"""
    default_split_method = request.form.get('default_split_method')
    default_payer = request.form.get('default_payer')
    auto_include_all = request.form.get('auto_include_all') == 'on'
    default_split_values = request.form.get('default_split_values')

    success, message = group_service.update_settings(
        group_id, current_user.id, default_split_method,
        default_payer, auto_include_all, default_split_values
    )

    flash(message)
    return redirect(url_for('group.group_details', group_id=group_id))


@bp.route('/get_details/<int:group_id>', methods=['GET'])
@login_required_dev
def get_details(group_id):
    """Get group details via AJAX"""
    success, message, group = group_service.get_group(group_id, current_user.id)

    if success:
        balances = group_service.calculate_group_balances(group_id)
        return jsonify({
            'success': True,
            'group': {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'member_count': len(group.members),
                'balances': balances
            }
        })
    else:
        return jsonify({'success': False, 'message': message}), 403


# ========== SETTLEMENT ROUTES ==========

@settlement_bp.route('')
@login_required_dev
def settlements():
    """View all settlements"""
    settlements = settlement_service.get_all_settlements(current_user.id)
    base_currency = get_base_currency()
    users = User.query.all()

    # Calculate balances (you_owe and you_are_owed)
    from src.utils.helpers import calculate_balances
    balances = calculate_balances(current_user.id)

    you_owe = []
    you_are_owed = []

    for balance in balances:
        if balance['amount'] < 0:
            # Current user owes money
            you_owe.append({
                'id': balance['user_id'],
                'name': balance['name'],
                'email': balance['email'],
                'amount': abs(balance['amount'])
            })
        elif balance['amount'] > 0:
            # Current user is owed money
            you_are_owed.append({
                'id': balance['user_id'],
                'name': balance['name'],
                'email': balance['email'],
                'amount': balance['amount']
            })

    return render_template('settlements.html',
                          settlements=settlements,
                          users=users,
                          you_owe=you_owe,
                          you_are_owed=you_are_owed,
                          base_currency=base_currency,
                          current_user_id=current_user.id)


@settlement_bp.route('/add', methods=['POST'])
@login_required_dev
@restrict_demo_access
def add_settlement():
    """Add a settlement payment"""
    payer_id = request.form.get('payer_id')
    receiver_id = request.form.get('receiver_id')
    amount = request.form.get('amount')
    group_id = request.form.get('group_id')
    description = request.form.get('description')

    success, message, settlement = settlement_service.add_settlement(
        payer_id, receiver_id, amount, group_id, description
    )

    flash(message)
    return redirect(url_for('settlement.settlements'))
