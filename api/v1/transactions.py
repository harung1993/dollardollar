"""Transactions API endpoints"""
from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.transaction import Expense
from src.extensions import db
from schemas import transaction_schema, transactions_schema
from datetime import datetime
from sqlalchemy import or_, and_

# Create namespace
ns = Namespace('transactions', description='Transaction operations')

# Define request/response models
transaction_model = ns.model('Transaction', {
    'description': fields.String(required=True, description='Transaction description'),
    'amount': fields.Float(required=True, description='Transaction amount'),
    'date': fields.DateTime(required=True, description='Transaction date'),
    'currency_code': fields.String(description='Currency code (e.g., USD)'),
    'card_used': fields.String(description='Card or payment method'),
    'category_id': fields.Integer(description='Category ID'),
    'account_id': fields.Integer(description='Account ID'),
    'transaction_type': fields.String(description='Type: expense, income, or transfer'),
    'notes': fields.String(description='Additional notes'),
    'split_method': fields.String(description='Split method: equal, custom, percentage'),
    'split_with': fields.String(description='Comma-separated user IDs to split with'),
    'paid_by': fields.Integer(description='User ID who paid'),
})


@ns.route('/')
class TransactionList(Resource):
    @ns.doc('list_transactions', security='Bearer')
    @jwt_required()
    def get(self):
        """Get all transactions for current user with optional filters"""
        current_user_id = get_jwt_identity()

        # Get query parameters for filtering
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)
        category_id = request.args.get('category_id', type=int)
        account_id = request.args.get('account_id', type=int)
        transaction_type = request.args.get('type', type=str)
        search = request.args.get('search', type=str)

        # Build query
        query = Expense.query.filter(
            or_(
                Expense.user_id == current_user_id,
                Expense.split_with.like(f'%{current_user_id}%')
            )
        )

        # Apply filters
        if start_date:
            try:
                start = datetime.fromisoformat(start_date)
                query = query.filter(Expense.date >= start)
            except ValueError:
                pass

        if end_date:
            try:
                end = datetime.fromisoformat(end_date)
                query = query.filter(Expense.date <= end)
            except ValueError:
                pass

        if category_id:
            query = query.filter(Expense.category_id == category_id)

        if account_id:
            query = query.filter(Expense.account_id == account_id)

        if transaction_type:
            query = query.filter(Expense.transaction_type == transaction_type)

        if search:
            query = query.filter(Expense.description.ilike(f'%{search}%'))

        # Order by date descending
        query = query.order_by(Expense.date.desc())

        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        transactions = pagination.items

        # Serialize
        result = transactions_schema.dump(transactions)

        return {
            'success': True,
            'transactions': result,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }, 200

    @ns.doc('create_transaction', security='Bearer')
    @ns.expect(transaction_model)
    def post(self):
        """Create a new transaction"""
        current_user_id = get_jwt_identity()
        data = request.get_json()

        try:
            # Create new transaction
            new_transaction = Expense(
                description=data.get('description'),
                amount=data.get('amount'),
                date=datetime.fromisoformat(data.get('date')) if isinstance(data.get('date'), str) else data.get('date'),
                currency_code=data.get('currency_code', 'USD'),
                card_used=data.get('card_used', 'Cash'),
                category_id=data.get('category_id'),
                account_id=data.get('account_id'),
                transaction_type=data.get('transaction_type', 'expense'),
                notes=data.get('notes'),
                split_method=data.get('split_method', 'equal'),
                split_with=data.get('split_with', ''),
                paid_by=data.get('paid_by', current_user_id),
                user_id=current_user_id
            )

            db.session.add(new_transaction)
            db.session.commit()

            # Serialize and return
            result = transaction_schema.dump(new_transaction)

            return {
                'success': True,
                'transaction': result,
                'message': 'Transaction created successfully'
            }, 201

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400


@ns.route('/<int:id>')
@ns.param('id', 'Transaction ID')
class TransactionDetail(Resource):
    @ns.doc('get_transaction', security='Bearer')
    @jwt_required()
    def get(self, id):
        """Get a specific transaction by ID"""
        current_user_id = get_jwt_identity()

        transaction = Expense.query.filter(
            and_(
                Expense.id == id,
                or_(
                    Expense.user_id == current_user_id,
                    Expense.split_with.like(f'%{current_user_id}%')
                )
            )
        ).first()

        if not transaction:
            return {'success': False, 'error': 'Transaction not found'}, 404

        result = transaction_schema.dump(transaction)

        return {
            'success': True,
            'transaction': result
        }, 200

    @ns.doc('update_transaction', security='Bearer')
    @ns.expect(transaction_model)
    def put(self, id):
        """Update a transaction"""
        current_user_id = get_jwt_identity()

        transaction = Expense.query.filter_by(id=id, user_id=current_user_id).first()

        if not transaction:
            return {'success': False, 'error': 'Transaction not found'}, 404

        data = request.get_json()

        try:
            # Update fields
            if 'description' in data:
                transaction.description = data['description']
            if 'amount' in data:
                transaction.amount = data['amount']
            if 'date' in data:
                transaction.date = datetime.fromisoformat(data['date']) if isinstance(data['date'], str) else data['date']
            if 'currency_code' in data:
                transaction.currency_code = data['currency_code']
            if 'card_used' in data:
                transaction.card_used = data['card_used']
            if 'category_id' in data:
                transaction.category_id = data['category_id']
            if 'account_id' in data:
                transaction.account_id = data['account_id']
            if 'transaction_type' in data:
                transaction.transaction_type = data['transaction_type']
            if 'notes' in data:
                transaction.notes = data['notes']
            if 'split_method' in data:
                transaction.split_method = data['split_method']
            if 'split_with' in data:
                transaction.split_with = data['split_with']

            db.session.commit()

            result = transaction_schema.dump(transaction)

            return {
                'success': True,
                'transaction': result,
                'message': 'Transaction updated successfully'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400

    @ns.doc('delete_transaction', security='Bearer')
    def delete(self, id):
        """Delete a transaction"""
        current_user_id = get_jwt_identity()

        transaction = Expense.query.filter_by(id=id, user_id=current_user_id).first()

        if not transaction:
            return {'success': False, 'error': 'Transaction not found'}, 404

        try:
            db.session.delete(transaction)
            db.session.commit()

            return {
                'success': True,
                'message': 'Transaction deleted successfully'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400


@ns.route('/recent')
class RecentTransactions(Resource):
    @ns.doc('get_recent_transactions', security='Bearer')
    @jwt_required()
    def get(self):
        """Get recent transactions (last 10)"""
        current_user_id = get_jwt_identity()
        limit = request.args.get('limit', 10, type=int)

        transactions = Expense.query.filter(
            or_(
                Expense.user_id == current_user_id,
                Expense.split_with.like(f'%{current_user_id}%')
            )
        ).order_by(Expense.date.desc()).limit(limit).all()

        result = transactions_schema.dump(transactions)

        return {
            'success': True,
            'transactions': result
        }, 200
