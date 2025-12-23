"""
Transaction models (Expense and CategorySplit)
"""

from datetime import datetime
import json
from src.extensions import db
from src.models.associations import expense_tags

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    card_used = db.Column(db.String(150), nullable=False)
    split_method = db.Column(db.String(20), nullable=False)  # 'equal', 'custom', 'percentage'
    split_value = db.Column(db.Float)  # deprecated - kept for backward compatibility
    paid_by = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    split_with = db.Column(db.String(500), nullable=True)  # Comma-separated list of user IDs
    split_details = db.Column(db.Text, nullable=True)  # JSON string storing custom split values for each user
    recurring_id = db.Column(db.Integer, db.ForeignKey('recurring_expenses.id'), nullable=True)
    currency_code = db.Column(db.String(3), db.ForeignKey('currencies.code'), nullable=True)
    original_amount = db.Column(db.Float, nullable=True) # Amount in original currency
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    transaction_type = db.Column(db.String(20), server_default='expense')  # 'expense', 'income', 'transfer'
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', name='fk_expense_account'), nullable=True)
    external_id = db.Column(db.String(200), nullable=True)  # For tracking external transaction IDs
    import_source = db.Column(db.String(50), nullable=True)  # 'csv', 'simplefin', 'manual'
    destination_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', name='fk_destination_account'), nullable=True)
    has_category_splits = db.Column(db.Boolean, default=False)
    
    # Relationships
    tags = db.relationship('Tag', secondary=expense_tags, lazy='subquery', 
                   backref=db.backref('expenses', lazy=True))
    currency = db.relationship('Currency', backref=db.backref('expenses', lazy=True))
    user = db.relationship('User', backref=db.backref('expenses', lazy=True))
    account = db.relationship('Account', foreign_keys=[account_id], backref=db.backref('expenses', lazy=True))
    destination_account = db.relationship('Account', foreign_keys=[destination_account_id], backref=db.backref('incoming_transfers', lazy=True))
    category = db.relationship('Category', backref=db.backref('expenses', lazy=True))
    
    @property
    def is_income(self):
        return self.transaction_type == 'income'
    
    @property
    def is_transfer(self):
        return self.transaction_type == 'transfer'
    
    @property
    def is_expense(self):
        return self.transaction_type == 'expense' or self.transaction_type is None

    def calculate_splits(self):
        from src.models.user import User
        
        # Get the user who paid
        payer = User.query.filter_by(id=self.paid_by).first()
        payer_name = payer.name if payer else "Unknown"
        payer_email = payer.id
        
        # Get all people this expense is split with
        split_with_ids = self.split_with.split(',') if self.split_with else []
        split_users = []
        
        for user_id in split_with_ids:
            user = User.query.filter_by(id=user_id.strip()).first()
            if user:
                split_users.append({
                    'id': user.id,
                    'name': user.name,
                    'email': user.id
                })
        
        # Handle case where original_amount is None by using amount
        original_amount = self.original_amount if self.original_amount is not None else self.amount
        
        # Set up result structure with both base and original currency
        result = {
            'payer': {
                'name': payer_name, 
                'email': payer_email,
                'amount': 0,  # Base currency amount
                'original_amount': original_amount,  # Original amount
                'currency_code': self.currency_code  # Original currency code
            },
            'splits': []
        }
        
        # Parse split details if available
        split_details = {}
        if self.split_details:
            try:
                if isinstance(self.split_details, str):
                    split_details = json.loads(self.split_details)
                elif isinstance(self.split_details, dict):
                    split_details = self.split_details
            except Exception as e:
                print(f"Error parsing split_details for expense {self.id}: {str(e)}")
                split_details = {}
        
        if self.split_method == 'equal':
            total_participants = len(split_users) + (1 if self.paid_by not in split_with_ids else 0)
            per_person = self.amount / total_participants if total_participants > 0 else 0
            per_person_original = original_amount / total_participants if total_participants > 0 else 0
            
            if self.paid_by not in split_with_ids:
                result['payer']['amount'] = per_person
            else:
                result['payer']['amount'] = 0
            
            for user in split_users:
                result['splits'].append({
                    'name': user['name'],
                    'email': user['email'],
                    'amount': per_person,
                    'original_amount': per_person_original,
                    'currency_code': self.currency_code
                })
                    
        elif self.split_method == 'percentage':
            if split_details and isinstance(split_details, dict) and split_details.get('type') == 'percentage':
                percentages = split_details.get('values', {})
                total_assigned = 0
                total_original_assigned = 0
                
                payer_percent = float(percentages.get(self.paid_by, 0))
                payer_amount = (self.amount * payer_percent) / 100
                payer_original_amount = (original_amount * payer_percent) / 100
                
                result['payer']['amount'] = payer_amount if self.paid_by not in split_with_ids else 0
                total_assigned += payer_amount if self.paid_by not in split_with_ids else 0
                total_original_assigned += payer_original_amount if self.paid_by not in split_with_ids else 0
                
                for user in split_users:
                    user_percent = float(percentages.get(user['id'], 0))
                    user_amount = (self.amount * user_percent) / 100
                    user_original_amount = (original_amount * user_percent) / 100
                    
                    result['splits'].append({
                        'name': user['name'],
                        'email': user['email'],
                        'amount': user_amount,
                        'original_amount': user_original_amount,
                        'currency_code': self.currency_code
                    })
                    total_assigned += user_amount
                    total_original_assigned += user_original_amount
                
                if abs(total_assigned - self.amount) > 0.01:
                    difference = self.amount - total_assigned
                    if result['splits']:
                        result['splits'][-1]['amount'] += difference
                    elif result['payer']['amount'] > 0:
                        result['payer']['amount'] += difference
            else:
                payer_percentage = self.split_value if self.split_value is not None else 0
                payer_amount = (self.amount * payer_percentage) / 100
                payer_original_amount = (original_amount * payer_percentage) / 100
                
                result['payer']['amount'] = payer_amount if self.paid_by not in split_with_ids else 0
                
                remaining = self.amount - result['payer']['amount']
                remaining_original = original_amount - payer_original_amount
                per_person = remaining / len(split_users) if split_users else 0
                per_person_original = remaining_original / len(split_users) if split_users else 0
                
                for user in split_users:
                    result['splits'].append({
                        'name': user['name'],
                        'email': user['email'],
                        'amount': per_person,
                        'original_amount': per_person_original,
                        'currency_code': self.currency_code
                    })
        
        elif self.split_method == 'custom':
            if split_details and isinstance(split_details, dict) and split_details.get('type') in ['amount', 'custom']:
                amounts = split_details.get('values', {})
                total_assigned = 0
                
                payer_amount = float(amounts.get(self.paid_by, 0))
                payer_ratio = payer_amount / self.amount if self.amount else 0
                payer_original_amount = original_amount * payer_ratio
                
                result['payer']['amount'] = payer_amount if self.paid_by not in split_with_ids else 0
                total_assigned += payer_amount if self.paid_by not in split_with_ids else 0
                
                for user in split_users:
                    user_amount = float(amounts.get(user['id'], 0))
                    user_ratio = user_amount / self.amount if self.amount else 0
                    user_original_amount = original_amount * user_ratio
                    
                    result['splits'].append({
                        'name': user['name'],
                        'email': user['email'],
                        'amount': user_amount,
                        'original_amount': user_original_amount,
                        'currency_code': self.currency_code
                    })
                    total_assigned += user_amount
                
                if abs(total_assigned - self.amount) > 0.01:
                    difference = self.amount - total_assigned
                    if result['splits']:
                        result['splits'][-1]['amount'] += difference
                    elif result['payer']['amount'] > 0:
                        result['payer']['amount'] += difference
            else:
                payer_amount = self.split_value if self.split_value is not None else 0
                payer_ratio = payer_amount / self.amount if self.amount else 0
                payer_original_amount = original_amount * payer_ratio
                
                result['payer']['amount'] = payer_amount if self.paid_by not in split_with_ids else 0
                
                remaining = self.amount - result['payer']['amount']
                remaining_original = original_amount - payer_original_amount
                per_person = remaining / len(split_users) if split_users else 0
                per_person_original = remaining_original / len(split_users) if split_users else 0
                
                for user in split_users:
                    result['splits'].append({
                        'name': user['name'],
                        'email': user['email'],
                        'amount': per_person,
                        'original_amount': per_person_original,
                        'currency_code': self.currency_code
                    })

        return result


class CategorySplit(db.Model):
    __tablename__ = 'category_splits'
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    
    # Relationships
    expense = db.relationship('Expense', backref=db.backref('category_splits', cascade='all, delete-orphan'))
    category = db.relationship('Category', backref=db.backref('splits', lazy=True))
