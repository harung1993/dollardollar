"""Budgets API endpoints"""
from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.budget import Budget
from src.extensions import db
from schemas import budget_schema, budgets_schema
from datetime import datetime

# Create namespace
ns = Namespace('budgets', description='Budget operations')

# Define request/response models
budget_model = ns.model('Budget', {
    'name': fields.String(required=True, description='Budget name'),
    'amount': fields.Float(required=True, description='Budget amount'),
    'period': fields.String(required=True, description='Budget period (monthly, weekly, yearly)'),
    'category_id': fields.Integer(description='Category ID'),
    'start_date': fields.Date(description='Start date'),
    'end_date': fields.Date(description='End date'),
    'is_active': fields.Boolean(description='Whether budget is active'),
})


@ns.route('/')
class BudgetList(Resource):
    @ns.doc('list_budgets', security='Bearer')
    @jwt_required()
    def get(self):
        """Get all budgets for current user"""
        current_user_id = get_jwt_identity()

        # Get all budgets for user
        budgets = Budget.query.filter_by(user_id=current_user_id).all()

        # Serialize
        result = budgets_schema.dump(budgets)

        return {
            'success': True,
            'budgets': result
        }, 200

    @ns.doc('create_budget', security='Bearer')
    @ns.expect(budget_model)
    def post(self):
        """Create a new budget"""
        current_user_id = get_jwt_identity()
        data = request.get_json()

        try:
            # Parse dates if provided
            start_date = None
            end_date = None

            if data.get('start_date'):
                if isinstance(data['start_date'], str):
                    start_date = datetime.fromisoformat(data['start_date']).date()
                else:
                    start_date = data['start_date']

            if data.get('end_date'):
                if isinstance(data['end_date'], str):
                    end_date = datetime.fromisoformat(data['end_date']).date()
                else:
                    end_date = data['end_date']

            new_budget = Budget(
                name=data.get('name'),
                amount=data.get('amount'),
                period=data.get('period', 'monthly'),
                category_id=data.get('category_id'),
                start_date=start_date or datetime.now().date(),
                end_date=end_date,
                is_active=data.get('is_active', True),
                user_id=current_user_id
            )

            db.session.add(new_budget)
            db.session.commit()

            result = budget_schema.dump(new_budget)

            return {
                'success': True,
                'budget': result,
                'message': 'Budget created successfully'
            }, 201

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400


@ns.route('/<int:id>')
@ns.param('id', 'Budget ID')
class BudgetDetail(Resource):
    @ns.doc('get_budget', security='Bearer')
    @jwt_required()
    def get(self, id):
        """Get a specific budget by ID"""
        current_user_id = get_jwt_identity()

        budget = Budget.query.filter_by(id=id, user_id=current_user_id).first()

        if not budget:
            return {'success': False, 'error': 'Budget not found'}, 404

        result = budget_schema.dump(budget)

        return {
            'success': True,
            'budget': result
        }, 200

    @ns.doc('update_budget', security='Bearer')
    @ns.expect(budget_model)
    def put(self, id):
        """Update a budget"""
        current_user_id = get_jwt_identity()

        budget = Budget.query.filter_by(id=id, user_id=current_user_id).first()

        if not budget:
            return {'success': False, 'error': 'Budget not found'}, 404

        data = request.get_json()

        try:
            if 'name' in data:
                budget.name = data['name']
            if 'amount' in data:
                budget.amount = data['amount']
            if 'period' in data:
                budget.period = data['period']
            if 'category_id' in data:
                budget.category_id = data['category_id']
            if 'is_active' in data:
                budget.is_active = data['is_active']
            if 'start_date' in data:
                if isinstance(data['start_date'], str):
                    budget.start_date = datetime.fromisoformat(data['start_date']).date()
                else:
                    budget.start_date = data['start_date']
            if 'end_date' in data:
                if isinstance(data['end_date'], str):
                    budget.end_date = datetime.fromisoformat(data['end_date']).date() if data['end_date'] else None
                else:
                    budget.end_date = data['end_date']

            db.session.commit()

            result = budget_schema.dump(budget)

            return {
                'success': True,
                'budget': result,
                'message': 'Budget updated successfully'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400

    @ns.doc('delete_budget', security='Bearer')
    def delete(self, id):
        """Delete a budget"""
        current_user_id = get_jwt_identity()

        budget = Budget.query.filter_by(id=id, user_id=current_user_id).first()

        if not budget:
            return {'success': False, 'error': 'Budget not found'}, 404

        try:
            db.session.delete(budget)
            db.session.commit()

            return {
                'success': True,
                'message': 'Budget deleted successfully'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400


@ns.route('/<int:id>/progress')
@ns.param('id', 'Budget ID')
class BudgetProgress(Resource):
    @ns.doc('get_budget_progress', security='Bearer')
    @jwt_required()
    def get(self, id):
        """Get budget progress and spending details"""
        current_user_id = get_jwt_identity()

        budget = Budget.query.filter_by(id=id, user_id=current_user_id).first()

        if not budget:
            return {'success': False, 'error': 'Budget not found'}, 404

        # Calculate spending if methods exist
        spent = budget.get_spent() if hasattr(budget, 'get_spent') else 0
        remaining = budget.get_remaining() if hasattr(budget, 'get_remaining') else budget.amount
        percentage = budget.get_percentage() if hasattr(budget, 'get_percentage') else 0

        return {
            'success': True,
            'budget_id': budget.id,
            'budget_name': budget.name,
            'budget_amount': budget.amount,
            'spent': spent,
            'remaining': remaining,
            'percentage': percentage,
            'status': 'over_budget' if spent > budget.amount else 'on_track' if percentage < 80 else 'warning'
        }, 200
