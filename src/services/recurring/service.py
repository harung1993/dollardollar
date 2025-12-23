"""
Recurring Service
Business logic for recurring transaction management and detection
"""

from datetime import datetime
from flask import current_app
from src.extensions import db
from src.models.recurring import RecurringExpense, IgnoredRecurringPattern
from src.models.transaction import Expense


class RecurringService:
    """Service class for recurring transaction operations"""

    def __init__(self):
        pass

    def get_all_recurring(self, user_id):
        """Get all recurring expenses for a user"""
        from sqlalchemy import or_
        return RecurringExpense.query.filter(
            or_(
                RecurringExpense.user_id == user_id,
                RecurringExpense.split_with.like(f'%{user_id}%')
            )
        ).all()

    def get_recurring(self, recurring_id, user_id):
        """Get a specific recurring expense"""
        recurring = RecurringExpense.query.get(recurring_id)
        if not recurring or recurring.user_id != user_id:
            return None
        return recurring

    def add_recurring(self, user_id, description, amount, frequency, category_id=None,
                     start_date=None, account_id=None, currency_code=None):
        """Add a new recurring expense"""
        try:
            recurring = RecurringExpense(
                user_id=user_id,
                description=description,
                amount=float(amount),
                frequency=frequency,
                category_id=category_id,
                next_date=start_date or datetime.utcnow(),
                account_id=account_id,
                currency_code=currency_code,
                active=True
            )

            db.session.add(recurring)
            db.session.commit()
            return True, 'Recurring expense added successfully!', recurring

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding recurring: {str(e)}")
            return False, f'Error: {str(e)}', None

    def update_recurring(self, recurring_id, user_id, **kwargs):
        """Update a recurring expense"""
        recurring = self.get_recurring(recurring_id, user_id)
        if not recurring:
            return False, 'Recurring expense not found'

        try:
            for key, value in kwargs.items():
                if hasattr(recurring, key) and value is not None:
                    setattr(recurring, key, value)

            db.session.commit()
            return True, 'Recurring expense updated successfully!'

        except Exception as e:
            db.session.rollback()
            return False, f'Error: {str(e)}'

    def toggle_recurring(self, recurring_id, user_id):
        """Toggle active status of recurring expense"""
        recurring = self.get_recurring(recurring_id, user_id)
        if not recurring:
            return False, 'Recurring expense not found', None

        try:
            recurring.active = not recurring.active
            db.session.commit()
            status = "activated" if recurring.active else "deactivated"
            return True, f'Recurring expense {status}!', recurring.active

        except Exception as e:
            db.session.rollback()
            return False, f'Error: {str(e)}', None

    def delete_recurring(self, recurring_id, user_id):
        """Delete a recurring expense"""
        recurring = self.get_recurring(recurring_id, user_id)
        if not recurring:
            return False, 'Recurring expense not found'

        try:
            db.session.delete(recurring)
            db.session.commit()
            return True, 'Recurring expense deleted successfully!'

        except Exception as e:
            db.session.rollback()
            return False, f'Error: {str(e)}'

    def detect_recurring_patterns(self, user_id):
        """Detect recurring transaction patterns"""
        # This would call the recurring detection integration
        from integrations.recurring.detector import detect_recurring_patterns
        return detect_recurring_patterns(user_id)

    def ignore_pattern(self, user_id, pattern_signature):
        """Add a pattern to the ignore list"""
        try:
            ignored = IgnoredRecurringPattern(
                user_id=user_id,
                pattern_signature=pattern_signature
            )
            db.session.add(ignored)
            db.session.commit()
            return True, 'Pattern ignored successfully!'

        except Exception as e:
            db.session.rollback()
            return False, f'Error: {str(e)}'
