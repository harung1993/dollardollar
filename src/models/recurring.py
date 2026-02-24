"""
Recurring expense models
"""

from datetime import datetime
from src.extensions import db

class RecurringExpense(db.Model):
    __tablename__ = 'recurring_expenses'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    card_used = db.Column(db.String(150), nullable=False)
    split_method = db.Column(db.String(20), nullable=False)  # 'equal', 'custom', 'percentage'
    split_value = db.Column(db.Float, nullable=True)
    split_details = db.Column(db.Text, nullable=True)  # JSON string
    paid_by = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    split_with = db.Column(db.String(500), nullable=True)  # Comma-separated list of user IDs
    
    # Recurring specific fields
    frequency = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly', 'monthly', 'yearly'
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)  # Optional end date
    last_created = db.Column(db.DateTime, nullable=True)  # Track last created instance
    active = db.Column(db.Boolean, default=True)
    
    currency_code = db.Column(db.String(3), db.ForeignKey('currencies.code'), nullable=True)
    original_amount = db.Column(db.Float, nullable=True)  # Amount in original currency
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    # Transaction type and account fields
    transaction_type = db.Column(db.String(20), default='expense')  # 'expense', 'income', 'transfer'
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', name='fk_recurring_account'), nullable=True)
    destination_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', name='fk_recurring_destination'), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('recurring_expenses', lazy=True))
    group = db.relationship('Group', backref=db.backref('recurring_expenses', lazy=True))
    currency = db.relationship('Currency', backref=db.backref('recurring_expenses', lazy=True))
    category = db.relationship('Category', backref=db.backref('recurring_expenses', lazy=True))
    account = db.relationship('Account', foreign_keys=[account_id], backref=db.backref('recurring_expenses', lazy=True))
    destination_account = db.relationship('Account', foreign_keys=[destination_account_id], 
                                         backref=db.backref('recurring_incoming_transfers', lazy=True))

    def create_expense_instance(self, for_date=None):
        """Create a single expense instance from this recurring template"""
        from src.models.transaction import Expense
        
        if for_date is None:
            for_date = datetime.utcnow()
            
        # Copy data to create a new expense
        expense = Expense(
            description=self.description,
            amount=self.amount,
            date=for_date,
            card_used=self.card_used,
            split_method=self.split_method,
            split_value=self.split_value,
            split_details=self.split_details,
            paid_by=self.paid_by,
            user_id=self.user_id,
            group_id=self.group_id,
            split_with=self.split_with,
            category_id=self.category_id,
            recurring_id=self.id,  # Link to this recurring expense
            transaction_type=self.transaction_type,
            account_id=self.account_id,
            destination_account_id=self.destination_account_id if self.transaction_type == 'transfer' else None,
            currency_code=self.currency_code,
            original_amount=self.original_amount
        )
        
        # Update the last created date
        self.last_created = for_date
        
        return expense


class IgnoredRecurringPattern(db.Model):
    """
    Stores patterns of recurring transactions that a user has chosen to ignore
    """
    __tablename__ = 'ignored_recurring_patterns'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    pattern_key = db.Column(db.String(255), nullable=False)  # Unique pattern identifier
    description = db.Column(db.String(200), nullable=False)  # For reference
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(20), nullable=False)
    ignore_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship with User
    user = db.relationship('User', backref=db.backref('ignored_patterns', lazy=True))
    
    # Ensure user can't ignore the same pattern twice
    __table_args__ = (db.UniqueConstraint('user_id', 'pattern_key'),)
    
    def __repr__(self):
        return f"<IgnoredPattern: {self.description} ({self.amount}) - {self.frequency}>"
