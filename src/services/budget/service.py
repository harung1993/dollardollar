"""
Budget Service
Business logic for budget management and tracking
"""

from datetime import datetime
from flask import current_app
from src.extensions import db
from src.models.budget import Budget
from src.models.category import Category
from src.utils.currency_converter import get_base_currency


class BudgetService:
    """Service class for budget operations"""

    def __init__(self):
        pass

    # Budget CRUD Methods

    def get_all_budgets(self, user_id):
        """Get all budgets for a user with calculated data"""
        budgets = Budget.query.filter_by(user_id=user_id).order_by(Budget.created_at.desc()).all()

        budget_data = []
        total_month_budget = 0
        total_month_spent = 0

        for budget in budgets:
            spent = budget.calculate_spent_amount()
            remaining = budget.get_remaining_amount()
            percentage = budget.get_progress_percentage()
            status = budget.get_status()
            period_start, period_end = budget.get_current_period_dates()

            budget_data.append({
                'budget': budget,
                'spent': spent,
                'remaining': remaining,
                'percentage': percentage,
                'status': status,
                'period_start': period_start,
                'period_end': period_end
            })

            # Add to monthly totals only for monthly budgets
            if budget.period == 'monthly':
                total_month_budget += budget.amount
                total_month_spent += spent

        return budget_data, total_month_budget, total_month_spent

    def get_budget(self, budget_id, user_id):
        """
        Get a specific budget
        Returns (success, message, budget)
        """
        budget = Budget.query.get(budget_id)
        if not budget:
            return False, 'Budget not found', None

        if budget.user_id != user_id:
            return False, 'You do not have permission to view this budget', None

        return True, 'Success', budget

    def add_budget(self, user_id, category_id, amount, period, include_subcategories=False,
                   name=None, start_date=None, is_recurring=False):
        """
        Add a new budget
        Returns (success, message, budget)
        """
        # Validate category exists
        category = Category.query.get(category_id)
        if not category or category.user_id != user_id:
            return False, 'Invalid category selected', None

        # Parse start date
        if start_date:
            if isinstance(start_date, str):
                try:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d')
                except ValueError:
                    start_date = datetime.utcnow()
        else:
            start_date = datetime.utcnow()

        # Check if a budget already exists for this category
        existing_budget = Budget.query.filter_by(
            user_id=user_id,
            category_id=category_id,
            period=period,
            active=True
        ).first()

        if existing_budget:
            return False, f'An active {period} budget already exists for this category. Please edit or deactivate it first.', None

        try:
            # Create new budget
            budget = Budget(
                user_id=user_id,
                category_id=category_id,
                name=name,
                amount=float(amount),
                period=period,
                include_subcategories=include_subcategories,
                start_date=start_date,
                is_recurring=is_recurring,
                active=True
            )

            db.session.add(budget)
            db.session.commit()

            return True, 'Budget added successfully!', budget

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding budget: {str(e)}")
            return False, f'Error adding budget: {str(e)}', None

    def update_budget(self, budget_id, user_id, category_id=None, name=None, amount=None,
                      period=None, include_subcategories=None, start_date=None, is_recurring=None):
        """
        Update an existing budget
        Returns (success, message)
        """
        budget = Budget.query.get(budget_id)
        if not budget:
            return False, 'Budget not found'

        if budget.user_id != user_id:
            return False, 'You do not have permission to edit this budget'

        try:
            # Update fields
            if category_id is not None:
                budget.category_id = category_id
            if name is not None:
                budget.name = name.strip() if name.strip() else budget.name
            if amount is not None:
                budget.amount = float(amount)
            if period is not None:
                budget.period = period
            if include_subcategories is not None:
                budget.include_subcategories = include_subcategories
            if start_date is not None:
                if isinstance(start_date, str):
                    try:
                        budget.start_date = datetime.strptime(start_date, '%Y-%m-%d')
                    except ValueError:
                        pass
                else:
                    budget.start_date = start_date
            if is_recurring is not None:
                budget.is_recurring = is_recurring

            budget.updated_at = datetime.utcnow()

            db.session.commit()
            return True, 'Budget updated successfully!'

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating budget: {str(e)}")
            return False, f'Error updating budget: {str(e)}'

    def toggle_budget(self, budget_id, user_id):
        """
        Toggle budget active status
        Returns (success, message, new_status)
        """
        budget = Budget.query.get(budget_id)
        if not budget:
            return False, 'Budget not found', None

        if budget.user_id != user_id:
            return False, 'You do not have permission to modify this budget', None

        try:
            budget.active = not budget.active
            db.session.commit()

            status = "activated" if budget.active else "deactivated"
            return True, f'Budget {status} successfully!', budget.active

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error toggling budget: {str(e)}")
            return False, f'Error toggling budget: {str(e)}', None

    def delete_budget(self, budget_id, user_id):
        """
        Delete a budget
        Returns (success, message)
        """
        budget = Budget.query.get(budget_id)
        if not budget:
            return False, 'Budget not found'

        if budget.user_id != user_id:
            return False, 'You do not have permission to delete this budget'

        try:
            db.session.delete(budget)
            db.session.commit()
            return True, 'Budget deleted successfully!'

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting budget: {str(e)}")
            return False, f'Error deleting budget: {str(e)}'

    # Budget Analysis Methods

    def get_subcategory_spending(self, budget_id, user_id):
        """
        Get spending breakdown by subcategory for a budget
        Returns (success, message, spending_data)
        """
        budget = Budget.query.get(budget_id)
        if not budget:
            return False, 'Budget not found', None

        if budget.user_id != user_id:
            return False, 'You do not have permission to view this budget', None

        if not budget.include_subcategories:
            return False, 'This budget does not include subcategories', None

        # Get category and its subcategories
        category = Category.query.get(budget.category_id)
        if not category:
            return False, 'Category not found', None

        period_start, period_end = budget.get_current_period_dates()

        # Calculate spending for each subcategory
        from src.models.transaction import Expense
        spending_data = []

        for subcategory in category.subcategories:
            # Get expenses for this subcategory in the budget period
            expenses = Expense.query.filter(
                Expense.user_id == user_id,
                Expense.category_id == subcategory.id,
                Expense.date >= period_start,
                Expense.date <= period_end
            ).all()

            total = sum(expense.amount for expense in expenses)

            if total > 0:
                spending_data.append({
                    'subcategory': subcategory,
                    'amount': total,
                    'count': len(expenses)
                })

        # Sort by amount descending
        spending_data.sort(key=lambda x: x['amount'], reverse=True)

        return True, 'Success', spending_data

    def get_budget_transactions(self, budget_id, user_id):
        """
        Get all transactions for a budget
        Returns (success, message, transactions)
        """
        budget = Budget.query.get(budget_id)
        if not budget:
            return False, 'Budget not found', None

        if budget.user_id != user_id:
            return False, 'You do not have permission to view this budget', None

        period_start, period_end = budget.get_current_period_dates()

        # Get transactions
        from src.models.transaction import Expense

        if budget.include_subcategories:
            # Get category and all its subcategories
            category = Category.query.get(budget.category_id)
            category_ids = [budget.category_id]
            if category and category.subcategories:
                category_ids.extend([sub.id for sub in category.subcategories])

            transactions = Expense.query.filter(
                Expense.user_id == user_id,
                Expense.category_id.in_(category_ids),
                Expense.date >= period_start,
                Expense.date <= period_end
            ).order_by(Expense.date.desc()).all()
        else:
            transactions = Expense.query.filter(
                Expense.user_id == user_id,
                Expense.category_id == budget.category_id,
                Expense.date >= period_start,
                Expense.date <= period_end
            ).order_by(Expense.date.desc()).all()

        return True, 'Success', transactions

    def get_trends_data(self, user_id):
        """
        Get budget trends data for charts
        Returns spending trends over time
        """
        budgets = Budget.query.filter_by(user_id=user_id, active=True).all()

        trends_data = []
        for budget in budgets:
            # Get last 6 periods of data
            historical_data = []
            for i in range(6):
                # Calculate period dates for i periods ago
                # This is simplified - actual implementation would need period-specific logic
                spent = budget.calculate_spent_amount()
                historical_data.append({
                    'period': i,
                    'spent': spent,
                    'budget': budget.amount
                })

            trends_data.append({
                'budget': budget,
                'historical_data': historical_data
            })

        return trends_data

    def get_summary_data(self, user_id):
        """
        Get budget summary data for overview
        Returns aggregate budget statistics
        """
        budgets = Budget.query.filter_by(user_id=user_id, active=True).all()

        total_budgeted = 0
        total_spent = 0
        on_track_count = 0
        over_budget_count = 0

        for budget in budgets:
            if budget.period == 'monthly':
                total_budgeted += budget.amount
                spent = budget.calculate_spent_amount()
                total_spent += spent

                status = budget.get_status()
                if status == 'on_track':
                    on_track_count += 1
                elif status == 'over_budget':
                    over_budget_count += 1

        return {
            'total_budgeted': total_budgeted,
            'total_spent': total_spent,
            'on_track_count': on_track_count,
            'over_budget_count': over_budget_count,
            'budget_count': len(budgets)
        }
