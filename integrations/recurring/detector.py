from datetime import datetime, timedelta
from collections import defaultdict
import calendar
from flask import current_app
from sqlalchemy import and_, or_

def detect_recurring_transactions(user_id, lookback_days=60, min_occurrences=2):
    """
    Detect potential recurring transactions for a user based on transaction history.
    """
    # Import database and models
    from src.extensions import db
    from src.models.transaction import Expense

    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    # Query transactions using SQLAlchemy ORM
    transactions_query = Expense.query.filter(
        and_(
            Expense.user_id == user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            or_(Expense.recurring_id == None, Expense.recurring_id.is_(None))
        )
    ).order_by(Expense.date).all()

    # Convert to list of dictionaries
    result = transactions_query
    
    # Convert result to a list of dictionaries for easier processing
    transactions = []
    for expense in result:
        transactions.append({
            'id': expense.id,
            'description': expense.description,
            'amount': expense.amount,
            'date': expense.date,
            'currency_code': expense.currency_code,
            'account_id': expense.account_id,
            'category_id': expense.category_id,
            'transaction_type': getattr(expense, 'transaction_type', 'expense')
        })
    
    # Group transactions by name + amount (potential recurrence key)
    transaction_groups = defaultdict(list)
    
    for transaction in transactions:
        # Create a composite key of description and amount
        key = f"{transaction['description'].strip().lower()}_{round(transaction['amount'], 2)}"
        transaction_groups[key].append(transaction)
    
    # Find recurring patterns
    recurring_candidates = []
    
    for key, group in transaction_groups.items():
        # Only consider groups with multiple occurrences
        if len(group) < min_occurrences:
            continue
        
        # Sort transactions by date
        sorted_transactions = sorted(group, key=lambda x: x['date'])
        
        # Analyze time intervals between transactions
        intervals = []
        for i in range(1, len(sorted_transactions)):
            delta = (sorted_transactions[i]['date'] - sorted_transactions[i-1]['date']).days
            intervals.append(delta)
        
        # Skip if no intervals (only one transaction)
        if not intervals:
            continue
            
        # Calculate average interval
        avg_interval = sum(intervals) / len(intervals)
        
        # Determine frequency based on average interval
        frequency = determine_frequency(avg_interval)
        
        # Skip if frequency couldn't be determined
        if not frequency:
            continue
            
        # Check consistency of intervals for higher confidence
        interval_consistency = calculate_interval_consistency(intervals)
        
        # Last transaction date
        last_transaction = sorted_transactions[-1]
        
        # Calculate next expected date
        next_date = calculate_next_occurrence(last_transaction['date'], frequency)
        
        # Only include if consistency is reasonable
        if interval_consistency >= 0.7:  # 70% consistency threshold
            # Get sample transaction for details
            sample = sorted_transactions[0]
            
            recurring_candidates.append({
                'description': sample['description'],
                'amount': sample['amount'],
                'currency_code': sample['currency_code'],
                'frequency': frequency,
                'account_id': sample['account_id'],
                'category_id': sample['category_id'],
                'transaction_type': sample['transaction_type'],
                'confidence': min(interval_consistency * 100, 98),
                'occurrences': len(sorted_transactions),
                'last_date': last_transaction['date'],
                'next_date': next_date,
                'avg_interval': round(avg_interval, 1),
                'transaction_ids': [t['id'] for t in sorted_transactions]
            })
    
    # Sort by confidence (highest first)
    recurring_candidates.sort(key=lambda x: x['confidence'], reverse=True)
    
    return recurring_candidates


def determine_frequency(avg_interval):
    """Determine the likely frequency based on average interval in days"""
    if 25 <= avg_interval <= 35:
        return 'monthly'
    elif 6 <= avg_interval <= 8:
        return 'weekly'
    elif 13 <= avg_interval <= 16:
        return 'biweekly'
    elif 85 <= avg_interval <= 95:
        return 'quarterly'
    elif 350 <= avg_interval <= 380:
        return 'yearly'
    elif avg_interval <= 3:
        return 'daily'
    else:
        return None  # Can't determine frequency


def calculate_interval_consistency(intervals):
    """
    Calculate how consistent the intervals are.
    Returns a value between 0 and 1, where 1 is perfectly consistent.
    """
    if not intervals:
        return 0
    
    # If only one interval, it's consistent by definition
    if len(intervals) == 1:
        return 0.95  # High but not perfect confidence
    
    # Calculate mean and standard deviation
    mean_interval = sum(intervals) / len(intervals)
    variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
    std_deviation = variance ** 0.5
    
    # Calculate coefficient of variation (lower is more consistent)
    if mean_interval == 0:
        return 0
    
    cv = std_deviation / mean_interval
    
    # Convert to consistency score (1 - normalized CV)
    # If CV is greater than 0.5, consistency drops quickly
    if cv > 0.5:
        return max(0, 1 - (cv * 1.5))
    else:
        return max(0, 1 - cv)


def calculate_next_occurrence(last_date, frequency):
    """Calculate the next expected occurrence based on frequency"""
    if frequency == 'daily':
        return last_date + timedelta(days=1)
    elif frequency == 'weekly':
        return last_date + timedelta(weeks=1)
    elif frequency == 'biweekly':
        return last_date + timedelta(weeks=2)
    elif frequency == 'monthly':
        # Handle month rollover properly
        month = last_date.month + 1
        year = last_date.year
        
        if month > 12:
            month = 1
            year += 1
            
        # Handle different days in months
        day = min(last_date.day, calendar.monthrange(year, month)[1])
        
        return last_date.replace(year=year, month=month, day=day)
    elif frequency == 'quarterly':
        # Add three months
        month = last_date.month + 3
        year = last_date.year
        
        if month > 12:
            month -= 12
            year += 1
            
        # Handle different days in months
        day = min(last_date.day, calendar.monthrange(year, month)[1])
        
        return last_date.replace(year=year, month=month, day=day)
    elif frequency == 'yearly':
        # Add a year
        return last_date.replace(year=last_date.year + 1)
    else:
        # Default fallback
        return last_date + timedelta(days=30)


def create_recurring_expense_from_detection(user_id, candidate, start_date=None):
    """
    Create a RecurringExpense from a detected candidate
    """
    from flask import current_app
    from app import RecurringExpense
    
    if start_date is None:
        start_date = datetime.now()
    
    # Create the recurring expense
    recurring = RecurringExpense(
        description=candidate['description'],
        amount=candidate['amount'],
        card_used="Auto-detected",
        split_method='equal',
        paid_by=user_id,
        user_id=user_id,
        frequency=candidate['frequency'],
        start_date=start_date,
        active=False,
        currency_code=candidate.get('currency_code'),
        category_id=candidate.get('category_id'),
        account_id=candidate.get('account_id'),
        transaction_type=candidate['transaction_type'] 
    )
    
    return recurring