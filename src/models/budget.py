"""
Budget model
"""

from datetime import datetime, timedelta
from src.extensions import db
from sqlalchemy import or_

class Budget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    name = db.Column(db.String(100), nullable=True)  # Optional custom name for the budget
    amount = db.Column(db.Float, nullable=False)
    period = db.Column(db.String(20), nullable=False)  # 'weekly', 'monthly', 'yearly'
    include_subcategories = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_recurring = db.Column(db.Boolean, default=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    transaction_types = db.Column(db.String(100), default='expense')  # comma-separated list of types to include
    
    # Relationships
    user = db.relationship('User', backref=db.backref('budgets', lazy=True))
    category = db.relationship('Category', backref=db.backref('budgets', lazy=True))
    
    def get_current_period_dates(self):
        """Get start and end dates for the current budget period"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if self.period == 'weekly':
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
            return start_of_week, end_of_week
            
        elif self.period == 'monthly':
            start_of_month = today.replace(day=1)
            if today.month == 12:
                end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(seconds=1)
            else:
                end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(seconds=1)
            return start_of_month, end_of_month
            
        elif self.period == 'yearly':
            start_of_year = today.replace(month=1, day=1)
            end_of_year = today.replace(year=today.year + 1, month=1, day=1) - timedelta(seconds=1)
            return start_of_year, end_of_year
            
        return today, today.replace(hour=23, minute=59, second=59)
    
    def calculate_spent_amount(self):
        """Calculate how much has been spent in this budget's category during the current period"""
        from src.models.transaction import Expense, CategorySplit
        from src.models.category import Category
        
        start_date, end_date = self.get_current_period_dates()
        
        if self.include_subcategories:
            subcategories = Category.query.filter_by(parent_id=self.category_id).all()
            subcategory_ids = [subcat.id for subcat in subcategories]
            
            category_filter = or_(
                Expense.category_id == self.category_id,
                Expense.category_id.in_(subcategory_ids) if subcategory_ids else False
            )
        else:
            category_filter = (Expense.category_id == self.category_id)
        
        expenses = Expense.query.filter(
            Expense.user_id == self.user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            category_filter
        ).all()
        
        total_spent = 0.0
        
        for expense in expenses:
            if expense.has_category_splits:
                continue
                
            splits = expense.calculate_splits()
            
            if expense.paid_by == self.user_id and (not expense.split_with or self.user_id not in expense.split_with.split(',')):
                total_spent += splits['payer']['amount']
            else:
                for split in splits['splits']:
                    if split['email'] == self.user_id:
                        total_spent += split['amount']
                        break
        
        if self.include_subcategories:
            category_ids = [self.category_id] + subcategory_ids
        else:
            category_ids = [self.category_id]
        
        category_splits = CategorySplit.query.join(
            Expense, CategorySplit.expense_id == Expense.id
        ).filter(
            Expense.user_id == self.user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            CategorySplit.category_id.in_(category_ids)
        ).all()
        
        for cat_split in category_splits:
            expense = Expense.query.get(cat_split.expense_id)
            if not expense:
                continue
                
            splits = expense.calculate_splits()
            
            if expense.paid_by == self.user_id and (not expense.split_with or self.user_id not in expense.split_with.split(',')):
                if expense.amount > 0:
                    user_ratio = splits['payer']['amount'] / expense.amount
                    total_spent += cat_split.amount * user_ratio
            else:
                for split in splits['splits']:
                    if split['email'] == self.user_id:
                        if expense.amount > 0:
                            user_ratio = split['amount'] / expense.amount
                            total_spent += cat_split.amount * user_ratio
                        break
        
        return total_spent
    
    def get_remaining_amount(self):
        """Calculate remaining budget amount"""
        return self.amount - self.calculate_spent_amount()
    
    def get_progress_percentage(self):
        spent = self.calculate_spent_amount()
        if self.amount <= 0:
            return 100
        percentage = (spent / self.amount) * 100
        return min(percentage, 100)
        
    def get_status(self):
        """Return the budget status: 'under', 'approaching', 'over'"""
        percentage = self.get_progress_percentage()
        if percentage >= 100:
            return 'over'
        elif percentage >= 80:
            return 'approaching'
        else:
            return 'under'
