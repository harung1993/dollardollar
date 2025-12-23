"""Investment Routes"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from src.utils.decorators import login_required_dev, restrict_demo_access
from src.services.investment.service import InvestmentService

bp = Blueprint('investment', __name__, url_prefix='/investments')
investment_service = InvestmentService()

@bp.route('/')
@login_required_dev
def investments():
    portfolios = investment_service.get_all_portfolios(current_user.id)
    return render_template('investments.html', portfolios=portfolios)

@bp.route('/portfolio/add', methods=['POST'])
@login_required_dev
@restrict_demo_access
def add_portfolio():
    success, message, _ = investment_service.add_portfolio(
        current_user.id, request.form.get('name'), request.form.get('description')
    )
    flash(message)
    return redirect(url_for('investment.investments'))
