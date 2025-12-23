"""Analytics Routes - Dashboard and reports"""
from flask import Blueprint, render_template, jsonify
from flask_login import current_user
from src.utils.decorators import login_required_dev
from src.services.analytics.service import AnalyticsService

bp = Blueprint('analytics', __name__)
analytics_service = AnalyticsService()

@bp.route('/dashboard')
@login_required_dev
def dashboard():
    """Main dashboard"""
    data = analytics_service.get_dashboard_data(current_user.id)
    return render_template('dashboard.html', **data)

@bp.route('/stats')
@login_required_dev
def stats():
    """Statistics page"""
    data = analytics_service.get_stats_data(current_user.id)
    return render_template('stats.html', **data)

@bp.route('/api/trends')
@login_required_dev
def trends():
    """Get spending trends data"""
    trends = analytics_service.get_spending_trends(current_user.id)
    return jsonify({'success': True, 'trends': trends})
