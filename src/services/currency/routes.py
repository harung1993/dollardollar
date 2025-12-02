"""
Currency Routes
Flask Blueprint for currency-related endpoints
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from src.utils.decorators import login_required_dev
from src.services.currency.service import CurrencyService

# Create Blueprint
bp = Blueprint('currency', __name__, url_prefix='/currencies')

# Initialize service
currency_service = CurrencyService()


@bp.route('/')
@login_required_dev
def manage_currencies():
    """Display all currencies"""
    currencies = currency_service.get_all_currencies()
    return render_template('currencies.html', currencies=currencies)


@bp.route('/add', methods=['POST'])
@login_required_dev
def add_currency():
    """Add a new currency"""
    if not current_user.is_admin:
        flash('Only administrators can add currencies')
        return redirect(url_for('currency.manage_currencies'))
    
    code = request.form.get('code', '').upper()
    name = request.form.get('name')
    symbol = request.form.get('symbol')
    rate_to_base = float(request.form.get('rate_to_base', 1.0))
    is_base = request.form.get('is_base') == 'on'
    
    success, message, currency = currency_service.add_currency(
        code, name, symbol, rate_to_base, is_base
    )
    
    flash(message)
    return redirect(url_for('currency.manage_currencies'))


@bp.route('/update/<code>', methods=['POST'])
@login_required_dev
def update_currency(code):
    """Update an existing currency"""
    if not current_user.is_admin:
        flash('Only administrators can update currencies')
        return redirect(url_for('currency.manage_currencies'))
    
    name = request.form.get('name')
    symbol = request.form.get('symbol')
    rate_to_base = float(request.form.get('rate_to_base'))
    is_base = request.form.get('is_base') == 'on'
    
    success, message, currency = currency_service.update_currency(
        code, name=name, symbol=symbol, rate_to_base=rate_to_base, is_base=is_base
    )
    
    flash(message)
    return redirect(url_for('currency.manage_currencies'))


@bp.route('/delete/<string:code>', methods=['DELETE'])
@login_required
def delete_currency(code):
    """Delete a currency (JSON API endpoint)"""
    if not current_user.is_admin:
        return jsonify({
            'success': False, 
            'message': 'Unauthorized. Admin access required.'
        }), 403
    
    success, message = currency_service.delete_currency(code)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        status_code = 404 if 'not found' in message.lower() else 400
        return jsonify({'success': False, 'message': message}), status_code


@bp.route('/set-base/<string:code>', methods=['POST'])
@login_required
def set_base_currency(code):
    """Change the base currency"""
    if not current_user.is_admin:
        flash('Unauthorized. Admin access required.', 'error')
        return redirect(url_for('currency.manage_currencies'))
    
    success, message = currency_service.set_base_currency(code)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('currency.manage_currencies'))


@bp.route('/update-rates', methods=['POST'])
@login_required_dev
def update_rates():
    """Update currency exchange rates"""
    if not current_user.is_admin:
        flash('Only administrators can update currency rates')
        return redirect(url_for('currency.manage_currencies'))
    
    result = currency_service.update_exchange_rates()
    
    if result >= 0:
        flash(f'Successfully updated {result} currency rates')
    else:
        flash('Error updating currency rates. Check the logs for details.')
    
    return redirect(url_for('currency.manage_currencies'))


@bp.route('/set-default', methods=['POST'])
@login_required_dev
def set_default_currency():
    """Set user's default currency"""
    currency_code = request.form.get('default_currency')
    
    # Verify currency exists
    currency = currency_service.get_currency(currency_code)
    if not currency:
        flash('Invalid currency selected')
        return redirect(url_for('currency.manage_currencies'))
    
    # Update user's default currency
    current_user.default_currency_code = currency_code
    from src.extensions import db
    db.session.commit()
    
    flash(f'Default currency set to {currency.code} ({currency.symbol})')
    return redirect(url_for('currency.manage_currencies'))
