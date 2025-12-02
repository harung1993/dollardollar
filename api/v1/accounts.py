"""Accounts API endpoints"""
from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.account import Account
from src.extensions import db
from schemas import account_schema, accounts_schema

# Create namespace
ns = Namespace('accounts', description='Account operations')

# Define request/response models
account_model = ns.model('Account', {
    'name': fields.String(required=True, description='Account name'),
    'account_type': fields.String(required=True, description='Account type (checking, savings, credit, etc.)'),
    'balance': fields.Float(description='Initial balance'),
    'currency_code': fields.String(description='Currency code'),
    'institution': fields.String(description='Financial institution name'),
    'account_number': fields.String(description='Account number (last 4 digits)'),
    'is_active': fields.Boolean(description='Whether account is active'),
})


@ns.route('/')
class AccountList(Resource):
    @ns.doc('list_accounts', security='Bearer')
    @jwt_required()
    def get(self):
        """Get all accounts for current user"""
        current_user_id = get_jwt_identity()

        # Get all accounts for user
        accounts = Account.query.filter_by(user_id=current_user_id).all()

        # Serialize
        result = accounts_schema.dump(accounts)

        return {
            'success': True,
            'accounts': result
        }, 200

    @ns.doc('create_account', security='Bearer')
    @ns.expect(account_model)
    def post(self):
        """Create a new account"""
        current_user_id = get_jwt_identity()
        data = request.get_json()

        try:
            new_account = Account(
                name=data.get('name'),
                account_type=data.get('account_type'),
                balance=data.get('balance', 0),
                currency_code=data.get('currency_code', 'USD'),
                institution=data.get('institution', ''),
                account_number=data.get('account_number', ''),
                is_active=data.get('is_active', True),
                user_id=current_user_id
            )

            db.session.add(new_account)
            db.session.commit()

            result = account_schema.dump(new_account)

            return {
                'success': True,
                'account': result,
                'message': 'Account created successfully'
            }, 201

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400


@ns.route('/<int:id>')
@ns.param('id', 'Account ID')
class AccountDetail(Resource):
    @ns.doc('get_account', security='Bearer')
    @jwt_required()
    def get(self, id):
        """Get a specific account by ID"""
        current_user_id = get_jwt_identity()

        account = Account.query.filter_by(id=id, user_id=current_user_id).first()

        if not account:
            return {'success': False, 'error': 'Account not found'}, 404

        result = account_schema.dump(account)

        return {
            'success': True,
            'account': result
        }, 200

    @ns.doc('update_account', security='Bearer')
    @ns.expect(account_model)
    def put(self, id):
        """Update an account"""
        current_user_id = get_jwt_identity()

        account = Account.query.filter_by(id=id, user_id=current_user_id).first()

        if not account:
            return {'success': False, 'error': 'Account not found'}, 404

        data = request.get_json()

        try:
            if 'name' in data:
                account.name = data['name']
            if 'account_type' in data:
                account.account_type = data['account_type']
            if 'balance' in data:
                account.balance = data['balance']
            if 'currency_code' in data:
                account.currency_code = data['currency_code']
            if 'institution' in data:
                account.institution = data['institution']
            if 'account_number' in data:
                account.account_number = data['account_number']
            if 'is_active' in data:
                account.is_active = data['is_active']

            db.session.commit()

            result = account_schema.dump(account)

            return {
                'success': True,
                'account': result,
                'message': 'Account updated successfully'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400

    @ns.doc('delete_account', security='Bearer')
    def delete(self, id):
        """Delete an account"""
        current_user_id = get_jwt_identity()

        account = Account.query.filter_by(id=id, user_id=current_user_id).first()

        if not account:
            return {'success': False, 'error': 'Account not found'}, 404

        try:
            db.session.delete(account)
            db.session.commit()

            return {
                'success': True,
                'message': 'Account deleted successfully'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400


@ns.route('/<int:id>/balance')
@ns.param('id', 'Account ID')
class AccountBalance(Resource):
    @ns.doc('get_account_balance', security='Bearer')
    @jwt_required()
    def get(self, id):
        """Get calculated balance for an account"""
        current_user_id = get_jwt_identity()

        account = Account.query.filter_by(id=id, user_id=current_user_id).first()

        if not account:
            return {'success': False, 'error': 'Account not found'}, 404

        # Get calculated balance if method exists
        calculated_balance = account.get_balance() if hasattr(account, 'get_balance') else account.balance

        return {
            'success': True,
            'account_id': account.id,
            'account_name': account.name,
            'balance': calculated_balance,
            'currency_code': account.currency_code
        }, 200
