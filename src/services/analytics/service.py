"""Analytics Service - Dashboard and statistics"""
from datetime import datetime, timedelta
from sqlalchemy import or_
from src.models.transaction import Expense
from src.models.budget import Budget
from src.models.group import Group
from src.models.user import User
from src.models.category import Category
from src.models.currency import Currency
from src.models.account import Account
from src.models.associations import group_users
from src.extensions import db

class AnalyticsService:
    def __init__(self):
        pass

    def get_dashboard_data(self, user_id):
        """Get dashboard overview data"""
        from src.utils.helpers import get_base_currency, sync_investments_with_accounts, calculate_asset_debt_trends
        from src.models.user import User

        now = datetime.now()
        current_user = User.query.get(user_id)
        base_currency = get_base_currency(current_user)

        # Fetch all expenses where the user is either the creator or a split participant
        expenses = Expense.query.filter(
            or_(
                Expense.user_id == user_id,
                Expense.split_with.like(f'%{user_id}%')
            )
        ).order_by(Expense.date.desc()).all()

        users = User.query.all()
        groups = Group.query.join(group_users).filter(group_users.c.user_id == user_id).all()

        # Synchronize investment portfolios with linked accounts
        try:
            sync_investments_with_accounts(user_id)
        except Exception as e:
            pass  # Silently fail if sync fails

        # Pre-calculate expense splits to avoid repeated calculations in template
        expense_splits = {}
        for expense in expenses:
            expense_splits[expense.id] = expense.calculate_splits()

        # Calculate monthly totals with contributors
        monthly_totals = {}
        if expenses:
            for expense in expenses:
                month_key = expense.date.strftime('%Y-%m')
                if month_key not in monthly_totals:
                    monthly_totals[month_key] = {
                        'total': 0.0,
                        'by_card': {},
                        'contributors': {},
                        'by_account': {}
                    }

                # Add to total - only add expenses, not income or transfers
                if not hasattr(expense, 'transaction_type') or expense.transaction_type == 'expense':
                    monthly_totals[month_key]['total'] += expense.amount

                    # Add to card totals
                    if expense.card_used not in monthly_totals[month_key]['by_card']:
                        monthly_totals[month_key]['by_card'][expense.card_used] = 0
                    monthly_totals[month_key]['by_card'][expense.card_used] += expense.amount

                    # Add to account totals if available
                    if hasattr(expense, 'account') and expense.account:
                        account_name = expense.account.name
                        if account_name not in monthly_totals[month_key]['by_account']:
                            monthly_totals[month_key]['by_account'][account_name] = 0
                        monthly_totals[month_key]['by_account'][account_name] += expense.amount

                    # Calculate splits and add to contributors
                    splits = expense_splits[expense.id]

                    # Add payer's portion
                    if splits['payer']['amount'] > 0:
                        payer_email = splits['payer']['email']
                        if payer_email not in monthly_totals[month_key]['contributors']:
                            monthly_totals[month_key]['contributors'][payer_email] = 0
                        monthly_totals[month_key]['contributors'][payer_email] += splits['payer']['amount']

                    # Add other contributors' portions
                    for split in splits['splits']:
                        if split['email'] not in monthly_totals[month_key]['contributors']:
                            monthly_totals[month_key]['contributors'][split['email']] = 0
                        monthly_totals[month_key]['contributors'][split['email']] += split['amount']

        # Calculate total expenses for current user (only their portions for the current year)
        current_year = now.year
        total_expenses = 0
        total_expenses_only = 0
        total_income = 0
        total_transfers = 0
        monthly_labels = []
        monthly_amounts = []

        # Sort monthly totals to ensure chronological order
        sorted_monthly_totals = sorted(monthly_totals.items(), key=lambda x: x[0])

        for month, data in sorted_monthly_totals:
            monthly_labels.append(month)
            monthly_amounts.append(data['total'])

        # Calculate totals for each transaction type
        for expense in expenses:
            if hasattr(expense, 'transaction_type'):
                if expense.transaction_type == 'income':
                    total_income += expense.amount
                elif expense.transaction_type == 'transfer':
                    total_transfers += expense.amount

        # Calculate user's share from expense splits
        current_month_total = 0
        current_month_expenses_only = 0
        unique_cards = set()

        for expense in expenses:
            if expense.date.year != current_year:
                continue

            splits = expense_splits[expense.id]
            user_share = 0

            # Find user's share
            if splits['payer']['id'] == user_id:
                user_share = splits['payer']['amount']
            else:
                for split in splits['splits']:
                    if split['id'] == user_id:
                        user_share = split['amount']
                        break

            # Add to totals
            if not hasattr(expense, 'transaction_type') or expense.transaction_type == 'expense':
                total_expenses += user_share
                total_expenses_only += user_share

                if expense.date.month == now.month and expense.date.year == now.year:
                    current_month_total += user_share
                    current_month_expenses_only += user_share

                if expense.card_used:
                    unique_cards.add(expense.card_used)

        # Calculate IOU data
        iou_data = self._calculate_iou_data(user_id, expenses, expense_splits)

        # Calculate budget summary
        budget_summary = self._calculate_budget_summary(user_id, now)

        # Calculate derived metrics
        net_cash_flow = total_income - total_expenses_only

        # Calculate savings rate if income is not zero
        if total_income > 0:
            savings_rate = (net_cash_flow / total_income) * 100
        else:
            savings_rate = 0

        # Get categories and currencies
        categories = Category.query.filter_by(user_id=user_id).order_by(Category.name).all()
        currencies = Currency.query.all()

        # Calculate asset and debt trends
        asset_debt_trends = calculate_asset_debt_trends(current_user)

        return {
            'expenses': expenses,
            'expense_splits': expense_splits,
            'top_categories': self._get_category_spending(expenses, expense_splits),
            'monthly_totals': monthly_totals,
            'total_expenses': total_expenses,
            'total_expenses_only': total_expenses_only,
            'current_month_total': current_month_total,
            'current_month_expenses_only': current_month_expenses_only,
            'unique_cards': list(unique_cards),
            'users': users,
            'groups': groups,
            'iou_data': iou_data,
            'base_currency': base_currency,
            'budget_summary': budget_summary,
            'currencies': currencies,
            'categories': categories,
            'monthly_labels': monthly_labels,
            'monthly_amounts': monthly_amounts,
            'total_income': total_income,
            'total_transfers': total_transfers,
            'net_cash_flow': net_cash_flow,
            'savings_rate': savings_rate,
            'asset_trends_months': asset_debt_trends['months'],
            'asset_trends': asset_debt_trends['assets'],
            'debt_trends': asset_debt_trends['debts'],
            'total_assets': asset_debt_trends['total_assets'],
            'total_debts': asset_debt_trends['total_debts'],
            'net_worth': asset_debt_trends['net_worth'],
            'investment_total': asset_debt_trends['investment_total'],
            'now': now
        }

    def _calculate_iou_data(self, user_id, expenses, expense_splits):
        """Calculate IOU balances between users"""
        from types import SimpleNamespace

        owes_me = {}  # People who owe current user
        i_owe = {}    # People current user owes

        for expense in expenses:
            splits = expense_splits[expense.id]
            payer_id = splits['payer']['id']

            # If current user is the payer
            if payer_id == user_id:
                # Track what others owe current user
                for split in splits['splits']:
                    split_user_id = split['id']
                    user_name = split['name']
                    amount = split['amount']

                    if split_user_id not in owes_me:
                        owes_me[split_user_id] = {'name': user_name, 'amount': 0}
                    owes_me[split_user_id]['amount'] += amount

            # If current user is in the splits (but not the payer)
            elif user_id in [split['id'] for split in splits['splits']]:
                payer = User.query.filter_by(id=payer_id).first()

                # Find current user's split amount
                current_user_split = next((split['amount'] for split in splits['splits'] if split['id'] == user_id), 0)

                if payer_id not in i_owe:
                    i_owe[payer_id] = {'name': payer.name if payer else 'Unknown', 'amount': 0}
                i_owe[payer_id]['amount'] += current_user_split

        # Calculate net balance
        total_owed = sum(data['amount'] for data in owes_me.values())
        total_owing = sum(data['amount'] for data in i_owe.values())
        net_balance = total_owed - total_owing

        return SimpleNamespace(
            owes_me=owes_me,
            i_owe=i_owe,
            net_balance=net_balance
        )

    def _calculate_budget_summary(self, user_id, now):
        """Calculate budget summary for the current month"""
        budgets = Budget.query.filter_by(user_id=user_id, active=True).all()

        # Use a namespace object so template can access with dot notation
        from types import SimpleNamespace

        budget_items = []
        total_budget = 0
        total_spent = 0
        over_budget_count = 0
        approaching_limit_count = 0

        for budget in budgets:
            # Calculate spending for this budget category
            month_start = datetime(now.year, now.month, 1)

            expenses = Expense.query.filter(
                Expense.user_id == user_id,
                Expense.category_id == budget.category_id,
                Expense.date >= month_start,
                Expense.date < datetime(now.year, now.month + 1, 1) if now.month < 12 else datetime(now.year + 1, 1, 1)
            ).all()

            spent = sum(e.amount for e in expenses if not hasattr(e, 'transaction_type') or e.transaction_type == 'expense')

            total_budget += budget.amount
            total_spent += spent

            percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0

            # Count budgets that are over or approaching limit
            if percentage >= 100:
                over_budget_count += 1
            elif percentage >= 80:  # Approaching limit if at 80% or more
                approaching_limit_count += 1

            budget_items.append(SimpleNamespace(
                category=budget.category.name if budget.category else 'Unknown',
                budget=budget.amount,
                spent=spent,
                percentage=percentage
            ))

        return SimpleNamespace(
            total_budgets=len(budgets),
            total_budget=total_budget,
            total_spent=total_spent,
            over_budget=over_budget_count,
            approaching_limit=approaching_limit_count,
            budgets=budget_items
        )

    def _get_category_spending(self, expenses, expense_splits):
        """Get top category spending for current month"""
        current_month = datetime.now().month
        current_year = datetime.now().year

        category_totals = {}

        for expense in expenses:
            # Skip non-expenses
            if hasattr(expense, 'transaction_type') and expense.transaction_type != 'expense':
                continue

            # Filter expenses for the current month and year
            if expense.date.month != current_month or expense.date.year != current_year:
                continue

            # Handle category splits first
            if expense.category_splits:
                for split in expense.category_splits:
                    if split.category:
                        category_name = split.category.name
                        if category_name not in category_totals:
                            category_totals[category_name] = {
                                'amount': 0,
                                'color': split.category.color,
                                'icon': split.category.icon
                            }
                        category_totals[category_name]['amount'] += split.amount
            else:
                # Use single category
                if expense.category:
                    category_name = expense.category.name
                    if category_name not in category_totals:
                        category_totals[category_name] = {
                            'amount': 0,
                            'color': expense.category.color,
                            'icon': expense.category.icon
                        }
                    category_totals[category_name]['amount'] += expense.amount

        # Sort and return top categories as list of dicts
        sorted_categories = sorted(
            [
                {
                    'name': name,
                    'amount': data['amount'],
                    'color': data['color'],
                    'icon': data['icon']
                }
                for name, data in category_totals.items()
            ],
            key=lambda x: x['amount'],
            reverse=True
        )[:6]  # Top 6 categories

        return sorted_categories

    def get_spending_trends(self, user_id, months=6):
        """Get spending trends over time"""
        trends = []
        for i in range(months):
            month_date = datetime.now() - timedelta(days=30*i)
            expenses = Expense.query.filter(
                Expense.user_id == user_id,
                Expense.date >= datetime(month_date.year, month_date.month, 1),
                Expense.date < datetime(month_date.year, month_date.month + 1, 1) if month_date.month < 12
                    else datetime(month_date.year + 1, 1, 1)
            ).all()
            total = sum(e.amount for e in expenses)
            trends.append({'month': month_date.strftime('%Y-%m'), 'total': total})
        return trends

    def get_stats_data(self, user_id):
        """Get detailed statistics data"""
        # Get base dashboard data
        data = self.get_dashboard_data(user_id)

        # Add monthly_income for stats page
        from src.models.transaction import Expense
        from sqlalchemy import or_

        # Get all expenses for the user
        expenses = Expense.query.filter(
            or_(
                Expense.user_id == user_id,
                Expense.split_with.like(f'%{user_id}%')
            )
        ).all()

        # Pre-calculate splits
        expense_splits = {}
        for expense in expenses:
            expense_splits[expense.id] = expense.calculate_splits()

        # Track monthly income
        monthly_income_dict = {}

        for expense in expenses:
            # Only process income transactions
            if hasattr(expense, 'transaction_type') and expense.transaction_type == 'income':
                month_key = expense.date.strftime('%Y-%m')

                if month_key not in monthly_income_dict:
                    monthly_income_dict[month_key] = 0

                # Calculate user's portion of the income
                splits = expense_splits[expense.id]
                user_portion = 0

                if splits['payer']['id'] == user_id:
                    user_portion = splits['payer']['amount']
                else:
                    for split in splits['splits']:
                        if split['id'] == user_id:
                            user_portion = split['amount']
                            break

                monthly_income_dict[month_key] += user_portion

        # Create monthly_income array in same order as monthly_labels
        monthly_income = []
        for label in data.get('monthly_labels', []):
            # Convert label back to month_key format (YYYY-MM)
            # If monthly_labels are already in YYYY-MM format, use directly
            # Otherwise parse the format from the dashboard
            month_key = label
            monthly_income.append(monthly_income_dict.get(month_key, 0))

        # Add to data dictionary
        data['monthly_income'] = monthly_income

        # Add category analysis data
        category_names = []
        category_totals = []

        # Get top categories from the existing category spending
        top_categories = data.get('top_categories', [])
        for cat in top_categories[:8]:  # Top 8 categories
            category_names.append(cat['name'])
            category_totals.append(cat['amount'])

        data['category_names'] = category_names
        data['category_totals'] = category_totals

        # Add tag data (empty for now, can be implemented later)
        data['tag_names'] = []
        data['tag_totals'] = []
        data['tag_colors'] = []

        # Add financial ratios (simple defaults for now)
        data['liquidity_ratio'] = 0
        data['account_growth'] = 0
        data['spending_trend'] = 0  # Could calculate actual trend if needed

        # Add net_balance from IOU data if available
        if 'iou_data' in data and hasattr(data['iou_data'], 'net_balance'):
            data['net_balance'] = data['iou_data'].net_balance
        else:
            data['net_balance'] = 0

        return data
