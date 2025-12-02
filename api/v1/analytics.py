"""Analytics API endpoints - Dashboard and Statistics"""
from flask import jsonify
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.services.analytics.service import AnalyticsService

# Create namespace
ns = Namespace('analytics', description='Analytics and dashboard operations')

# Initialize service
analytics_service = AnalyticsService()


@ns.route('/dashboard')
class Dashboard(Resource):
    @ns.doc('get_dashboard_data', security='Bearer')
    @jwt_required()
    def get(self):
        """Get dashboard overview data with metrics, charts, and categories"""
        current_user_id = get_jwt_identity()

        try:
            # Get dashboard data from service
            dashboard_data = analytics_service.get_dashboard_data(current_user_id)

            # Convert any SimpleNamespace objects to dicts for JSON serialization
            def convert_to_dict(obj):
                if hasattr(obj, '__dict__'):
                    return {key: convert_to_dict(value) for key, value in obj.__dict__.items()}
                elif isinstance(obj, list):
                    return [convert_to_dict(item) for item in obj]
                elif isinstance(obj, dict):
                    return {key: convert_to_dict(value) for key, value in obj.items()}
                else:
                    return obj

            serializable_data = convert_to_dict(dashboard_data)

            return {
                'success': True,
                'data': serializable_data
            }, 200

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }, 500


@ns.route('/stats')
class Statistics(Resource):
    @ns.doc('get_statistics', security='Bearer')
    @jwt_required()
    def get(self):
        """Get detailed statistics and charts data"""
        current_user_id = get_jwt_identity()

        try:
            # Get stats data from service
            stats_data = analytics_service.get_stats_data(current_user_id)

            # Convert to serializable format
            def convert_to_dict(obj):
                if hasattr(obj, '__dict__'):
                    return {key: convert_to_dict(value) for key, value in obj.__dict__.items()}
                elif isinstance(obj, list):
                    return [convert_to_dict(item) for item in obj]
                elif isinstance(obj, dict):
                    return {key: convert_to_dict(value) for key, value in obj.items()}
                else:
                    return obj

            serializable_data = convert_to_dict(stats_data)

            return {
                'success': True,
                'data': serializable_data
            }, 200

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }, 500


@ns.route('/trends')
class Trends(Resource):
    @ns.doc('get_spending_trends', security='Bearer')
    @jwt_required()
    def get(self):
        """Get spending trends over time"""
        current_user_id = get_jwt_identity()

        try:
            # Get trends from service (if method exists)
            if hasattr(analytics_service, 'get_spending_trends'):
                trends = analytics_service.get_spending_trends(current_user_id)
            else:
                # Fallback: use dashboard data for trends
                dashboard_data = analytics_service.get_dashboard_data(current_user_id)
                trends = {
                    'monthly_labels': dashboard_data.get('monthly_labels', []),
                    'monthly_expenses': dashboard_data.get('monthly_expenses', []),
                    'monthly_income': dashboard_data.get('monthly_income', []),
                }

            return {
                'success': True,
                'trends': trends
            }, 200

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }, 500


@ns.route('/categories/top')
class TopCategories(Resource):
    @ns.doc('get_top_spending_categories', security='Bearer')
    @jwt_required()
    def get(self):
        """Get top spending categories"""
        current_user_id = get_jwt_identity()

        try:
            # Get dashboard data which includes top categories
            dashboard_data = analytics_service.get_dashboard_data(current_user_id)
            top_categories = dashboard_data.get('top_categories', [])

            # Convert to list of dicts
            categories_list = []
            for cat_name, cat_data in top_categories:
                categories_list.append({
                    'name': cat_name,
                    'amount': cat_data['total'],
                    'percentage': cat_data['percentage'],
                    'count': cat_data['count']
                })

            return {
                'success': True,
                'categories': categories_list
            }, 200

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }, 500


@ns.route('/summary')
class Summary(Resource):
    @ns.doc('get_financial_summary', security='Bearer')
    @jwt_required()
    def get(self):
        """Get high-level financial summary (for dashboard metrics cards)"""
        current_user_id = get_jwt_identity()

        try:
            dashboard_data = analytics_service.get_dashboard_data(current_user_id)

            # Extract key metrics for dashboard cards
            summary = {
                'monthly_spending': dashboard_data.get('total_expenses_only', 0),
                'net_balance': getattr(dashboard_data.get('iou_data'), 'net_balance', 0) if dashboard_data.get('iou_data') else 0,
                'total_assets': dashboard_data.get('total_assets', 0),
                'budget_remaining': self._calculate_budget_remaining(dashboard_data),
                'currency_symbol': dashboard_data.get('base_currency', {}).get('symbol', '$'),
                'currency_code': dashboard_data.get('base_currency', {}).get('code', 'USD'),
            }

            return {
                'success': True,
                'summary': summary
            }, 200

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }, 500

    def _calculate_budget_remaining(self, dashboard_data):
        """Calculate total budget remaining across all budgets"""
        budget_summary = dashboard_data.get('budget_summary')
        if budget_summary and hasattr(budget_summary, '__dict__'):
            return getattr(budget_summary, 'total_remaining', 0)
        return 0
