r"""29a41de6a866d56c36aba5159f45257c"""

import os
from flask import (
    Flask,
    render_template,
    send_file,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    session,
)
import re
from flask_login import (
    login_user,
    login_required,
    logout_user,
    current_user,
)

import calendar
import logging
from flask_mail import Message
import ssl
import requests
from oidc_auth import setup_oidc_config, register_oidc_routes
from oidc_user import extend_user_model
from simplefin_client import SimpleFin
import base64
import pytz
from config import get_config
from extensions import db, login_manager, mail, migrate, scheduler
import extensions
import json
from datetime import datetime, timedelta


from sqlalchemy import func, or_, and_, inspect, text

from recurring_detection import (create_recurring_expense_from_detection,
                                 detect_recurring_transactions)
from routes import register_blueprints
from services.wrappers import login_required_dev, restrict_demo_access
from session_timeout import DemoTimeout, demo_time_limited

from models import Account, Budget, Category, CategoryMapping, CategorySplit, Currency, Expense, Group, IgnoredRecurringPattern, RecurringExpense, Settlement, User

# Development user credentials from environment
DEV_USER_EMAIL = os.getenv('DEV_USER_EMAIL', 'dev@example.com')
DEV_USER_PASSWORD = os.getenv('DEV_USER_PASSWORD', 'dev')
os.environ["OPENSSL_LEGACY_PROVIDER"] = "1"

APP_VERSION = "4.2"

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

def create_app(config_object=None):
    # App Factory
    app = Flask(__name__)

    if config_object is None:
        config_object = get_config()
    app.config.from_object(config_object)
    register_blueprints(app)        
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    scheduler.init_app(app)
    
    return app

app = create_app()
logging.basicConfig(level=getattr(logging, app.config['LOG_LEVEL']))
app.config['SIMPLEFIN_ENABLED'] = os.getenv('SIMPLEFIN_ENABLED', 'True').lower() == 'true'
app.config['SIMPLEFIN_SETUP_TOKEN_URL'] = os.getenv('SIMPLEFIN_SETUP_TOKEN_URL', 'https://beta-bridge.simplefin.org/setup-token')

app.config['GOCARDLESS_ENABLED'] = os.getenv('GOCARDLESS_ENABLED', 'True').lower() == 'true'

# Email configuration from environment variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))

app.config['TIMEZONE'] = 'EST'  # Default timezone

# Initialize scheduler
# scheduler = APScheduler()
scheduler.timezone = pytz.timezone('EST') # Explicitly set scheduler to use EST
scheduler.init_app(app)
logging.basicConfig(level=getattr(logging, app.config['LOG_LEVEL']))
@scheduler.task('cron', id='monthly_reports', day=1, hour=1, minute=0)
def scheduled_monthly_reports():
    """Run on the 1st day of each month at 1:00 AM"""
    send_automatic_monthly_reports()
@scheduler.task('cron', id='simplefin_sync', hour=23, minute=0)
def scheduled_simplefin_sync():
    """Run every day at 11:00 PM"""
    sync_all_simplefin_accounts()
scheduler.start()

simplefin_client = SimpleFin(app)

oidc_enabled = setup_oidc_config(app)
# db = SQLAlchemy(app)
# login_manager = LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = 'login'


# migrate = Migrate(app, db)


# Initialize demo timeout middleware
demo_timeout = DemoTimeout(
    timeout_minutes=int(os.getenv('DEMO_TIMEOUT_MINUTES', 10)),
    demo_users=[
        'demo@example.com',
        'demo1@example.com',
        'demo2@example.com',
        # Add any specific demo accounts here
    ]
)
demo_timeout.init_app(app)
app.extensions['demo_timeout'] = demo_timeout  # Store for access in decorator

if oidc_enabled:
    User = extend_user_model(db, User)

@login_manager.user_loader
def load_user(id):
    return User.query.filter_by(id=id).first()

def init_db():
    """Initialize the database"""
    with app.app_context():
        db.drop_all()  # This will drop all existing tables
        db.create_all()  # This will create new tables with current schema
        print("Database initialized successfully!")
        
        # Create dev user in development mode
        if app.config['DEVELOPMENT_MODE']:
            dev_user = User(
                id=DEV_USER_EMAIL,
                name='Developer',
                is_admin=True
            )
            dev_user.set_password(DEV_USER_PASSWORD)
            db.session.add(dev_user)
            db.session.commit()
            create_default_categories(dev_user.id)
            create_default_budgets(dev_user.id)
            print("Development user created:", DEV_USER_EMAIL)




#--------------------
# BUSINESS LOGIC FUNCTIONS
#--------------------

# enhance transfer detection
def calculate_asset_debt_trends(current_user):
    """
    Calculate asset and debt trends for a user's accounts
    """
    from datetime import datetime, timedelta
    
    # Initialize tracking
    monthly_assets = {}
    monthly_debts = {}
    
    # Get today's date and calculate a reasonable historical range (last 12 months)
    today = datetime.now()
    twelve_months_ago = today - timedelta(days=365)
    
    # Get all accounts for the user
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get user's preferred currency code
    user_currency_code = current_user.default_currency_code or 'USD'
    
    # Calculate true total assets and debts directly from accounts (for accurate current total)
    direct_total_assets = 0
    direct_total_debts = 0
    
    for account in accounts:
        # Get account's currency code, default to user's preferred currency
        account_currency_code = account.currency_code or user_currency_code
        
        # Convert account balance to user's currency if needed
        if account_currency_code != user_currency_code:
            converted_balance = convert_currency(account.balance, account_currency_code, user_currency_code)
        else:
            converted_balance = account.balance
        
        if account.type in ['checking', 'savings', 'investment'] and converted_balance > 0:
            direct_total_assets += converted_balance
        elif account.type in ['credit'] or converted_balance < 0:
            # For credit cards with negative balances (standard convention)
            direct_total_debts += abs(converted_balance)
    
    # Process each account for historical trends
    for account in accounts:
        # Get account's currency code, default to user's preferred currency
        account_currency_code = account.currency_code or user_currency_code
        
        # Categorize account types
        is_asset = account.type in ['checking', 'savings', 'investment'] and account.balance > 0
        is_debt = account.type in ['credit'] or account.balance < 0
        
        # Skip accounts with zero or near-zero balance
        if abs(account.balance or 0) < 0.01:
            continue
        
        # Get monthly transactions for this account
        transactions = Expense.query.filter(
            Expense.account_id == account.id,
            Expense.user_id == current_user.id,
            Expense.date >= twelve_months_ago
        ).order_by(Expense.date).all()
        
        # Track balance over time
        balance_history = {}
        current_balance = account.balance or 0
        
        # Start with the most recent balance
        balance_history[today.strftime('%Y-%m')] = current_balance
        
        # Process transactions to track historical balances
        for transaction in transactions:
            month_key = transaction.date.strftime('%Y-%m')
            
            # Consider currency conversion for each transaction if needed
            transaction_amount = transaction.amount
            if transaction.currency_code and transaction.currency_code != account_currency_code:
                transaction_amount = convert_currency(transaction_amount, transaction.currency_code, account_currency_code)
            
            # Adjust balance based on transaction
            if transaction.transaction_type == 'income':
                current_balance += transaction_amount
            elif transaction.transaction_type == 'expense' or transaction.transaction_type == 'transfer':
                current_balance -= transaction_amount
            
            # Update monthly balance
            balance_history[month_key] = current_balance
        
        # Convert balance history to user currency if needed
        if account_currency_code != user_currency_code:
            for month, balance in balance_history.items():
                balance_history[month] = convert_currency(balance, account_currency_code, user_currency_code)
        
        # Categorize and store balances
        for month, balance in balance_history.items():
            if is_asset:
                # For asset accounts, add positive balances to the monthly total
                monthly_assets[month] = monthly_assets.get(month, 0) + balance
            elif is_debt:
                # For debt accounts or negative balances, add the absolute value to the debt total
                monthly_debts[month] = monthly_debts.get(month, 0) + abs(balance)
    
    # Ensure consistent months across both series
    all_months = sorted(set(list(monthly_assets.keys()) + list(monthly_debts.keys())))
    
    # Fill in missing months with previous values or zero
    assets_trend = []
    debts_trend = []
    
    for month in all_months:
        assets_trend.append(monthly_assets.get(month, assets_trend[-1] if assets_trend else 0))
        debts_trend.append(monthly_debts.get(month, debts_trend[-1] if debts_trend else 0))
    
    # Use the directly calculated totals rather than the trend values for accuracy
    total_assets = direct_total_assets
    total_debts = direct_total_debts
    net_worth = total_assets - total_debts
    
    return {
        'months': all_months,
        'assets': assets_trend,
        'debts': debts_trend,
        'total_assets': total_assets,
        'total_debts': total_debts,
        'net_worth': net_worth
    }


def detect_internal_transfer(description, amount, account_id=None):
    """
    Detect if a transaction appears to be an internal transfer between accounts
    Returns a tuple of (is_transfer, source_account_id, destination_account_id)
    """
    # Default return values
    is_transfer = False
    source_account_id = account_id
    destination_account_id = None
    
    # Skip if no description or account
    if not description or not account_id:
        return is_transfer, source_account_id, destination_account_id
    
    # Normalize description for easier matching
    desc_lower = description.lower()
    
    # Common transfer-related keywords
    transfer_keywords = [
        'transfer', 'xfer', 'move', 'moved to', 'sent to', 'to account', 
        'from account', 'between accounts', 'internal', 'account to account',
        'trx to', 'trx from', 'trans to', 'trans from','ACH Withdrawal',
        'Robinhood', 'BK OF AMER VISA ONLINE PMT','Payment Thank You',


    ]
    
    # Check for transfer keywords in description
    if any(keyword in desc_lower for keyword in transfer_keywords):
        is_transfer = True
        
        # Try to identify the destination account
        # Get all user accounts
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        
        # Look for account names in the description
        for account in user_accounts:
            # Skip the source account
            if account.id == account_id:
                continue
                
            # Check if account name appears in the description
            if account.name.lower() in desc_lower:
                # This is likely the destination account
                destination_account_id = account.id
                break
    
    return is_transfer, source_account_id, destination_account_id

# Update the determine_transaction_type function to detect internal transfers
def determine_transaction_type(row, current_account_id=None):
    """
    Determine transaction type based on row data from CSV import
    Now with enhanced internal transfer detection
    """
    type_column = request.form.get('type_column')
    negative_is_expense = 'negative_is_expense' in request.form
    
    # Get description column name (default to 'Description')
    description_column = request.form.get('description_column', 'Description')
    description = row.get(description_column, '').strip()
    
    # Get amount column name (default to 'Amount')
    amount_column = request.form.get('amount_column', 'Amount')
    amount_str = row.get(amount_column, '0').strip().replace('$', '').replace(',', '')
    
    try:
        amount = float(amount_str)
    except ValueError:
        amount = 0
    
    # First check for internal transfer
    if current_account_id:
        is_transfer, _, _ = detect_internal_transfer(description, amount, current_account_id)
        if is_transfer:
            return 'transfer'
    
    # Check if there's a specific transaction type column
    if type_column and type_column in row:
        type_value = row[type_column].strip().lower()
        
        # Map common terms to transaction types
        if type_value in ['expense', 'debit', 'purchase', 'payment', 'withdrawal']:
            return 'expense'
        elif type_value in ['income', 'credit', 'deposit', 'refund']:
            return 'income'
        elif type_value in ['transfer', 'move', 'xfer']:
            return 'transfer'
    
    # If no type column or unknown value, try to determine from description
    if description:
        # Common transfer keywords
        transfer_keywords = ['transfer', 'xfer', 'move', 'moved to', 'sent to', 'to account', 'between accounts']
        # Common income keywords
        income_keywords = ['salary', 'deposit', 'refund', 'interest', 'dividend', 'payment received']
        # Common expense keywords
        expense_keywords = ['payment', 'purchase', 'fee', 'subscription', 'bill']
        
        desc_lower = description.lower()
        
        # Check for keywords in description
        if any(keyword in desc_lower for keyword in transfer_keywords):
            return 'transfer'
        elif any(keyword in desc_lower for keyword in income_keywords):
            return 'income'
        elif any(keyword in desc_lower for keyword in expense_keywords):
            return 'expense'
    
    # If still undetermined, use amount sign
    try:
        # Determine type based on amount sign and settings
        if amount < 0 and negative_is_expense:
            return 'expense'
        elif amount > 0 and negative_is_expense:
            return 'income'
        elif amount < 0 and not negative_is_expense:
            return 'income'  # In some systems, negative means money coming in
        else:
            return 'expense'  # Default to expense for positive amounts
    except ValueError:
        # If amount can't be parsed, default to expense
        return 'expense'

def auto_categorize_transaction(description, user_id):
    """
    Automatically categorize a transaction based on its description
    Returns the best matching category ID or None if no match found
    """
    if not description:
        return None
        
    # Standardize description - lowercase and remove extra spaces
    description = description.strip().lower()
    
    # Get all active category mappings for the user
    mappings = CategoryMapping.query.filter_by(
        user_id=user_id,
        active=True
    ).order_by(CategoryMapping.priority.desc(), CategoryMapping.match_count.desc()).all()
    
    # Keep track of matches and their scores
    matches = []
    
    # Check each mapping
    for mapping in mappings:
        matched = False
        if mapping.is_regex:
            # Use regex pattern matching
            try:
                import re
                pattern = re.compile(mapping.keyword, re.IGNORECASE)
                if pattern.search(description):
                    matched = True
            except:
                # If regex is invalid, fall back to simple substring search
                matched = mapping.keyword.lower() in description
        else:
            # Simple substring matching
            matched = mapping.keyword.lower() in description
            
        if matched:
            # Calculate match score based on:
            # 1. Priority (user-defined importance)
            # 2. Usage count (previous successful matches)
            # 3. Keyword length (longer keywords are more specific)
            # 4. Keyword position (earlier in the string is better)
            score = (mapping.priority * 100) + (mapping.match_count * 10) + len(mapping.keyword)
            
            # Adjust score based on position (if simple keyword)
            if not mapping.is_regex:
                position = description.find(mapping.keyword.lower())
                if position == 0:  # Matches at the start
                    score += 50
                elif position > 0:  # Adjust based on how early it appears
                    score += max(0, 30 - position)
                    
            matches.append((mapping, score))
    
    # Sort matches by score, descending
    matches.sort(key=lambda x: x[1], reverse=True)
    
    # If we have any matches, increment the match count for the winner and return its category ID
    if matches:
        best_mapping = matches[0][0]
        best_mapping.match_count += 1
        db.session.commit()
        return best_mapping.category_id
    
    return None


def get_category_id(category_name, description=None, user_id=None):
    """Find, create, or auto-suggest a category based on name and description"""
    # Clean the category name
    category_name = category_name.strip() if category_name else ""
    
    # If we have a user ID and no category name but have a description
    if user_id and not category_name and description:
        # Try to auto-categorize based on description
        auto_category_id = auto_categorize_transaction(description, user_id)
        if auto_category_id:
            return auto_category_id
    
    # If we have a category name, try to find it
    if category_name:
        # Try to find an exact match first
        category = Category.query.filter(
            Category.user_id == user_id if user_id else current_user.id,
            func.lower(Category.name) == func.lower(category_name)
        ).first()
        
        if category:
            return category.id
        
        # Try to find a partial match in subcategories
        subcategory = Category.query.filter(
            Category.user_id == user_id if user_id else current_user.id,
            Category.parent_id.isnot(None),
            func.lower(Category.name).like(f"%{category_name.lower()}%")
        ).first()
        
        if subcategory:
            return subcategory.id
        
        # Try to find a partial match in parent categories
        parent_category = Category.query.filter(
            Category.user_id == user_id if user_id else current_user.id,
            Category.parent_id.is_(None),
            func.lower(Category.name).like(f"%{category_name.lower()}%")
        ).first()
        
        if parent_category:
            return parent_category.id
        
        # If auto-categorize is enabled, create a new category
        if 'auto_categorize' in request.form:
            # Find "Other" category as parent
            other_category = Category.query.filter_by(
                name='Other',
                user_id=user_id if user_id else current_user.id,
                is_system=True
            ).first()
            
            new_category = Category(
                name=category_name[:50],  # Limit to 50 chars
                icon='fa-tag',
                color='#6c757d',
                parent_id=other_category.id if other_category else None,
                user_id=user_id if user_id else current_user.id
            )
            
            db.session.add(new_category)
            db.session.flush()  # Get ID without committing
            
            return new_category.id
    
    # If we still don't have a category, try auto-categorization again with the description
    if description and user_id:
        # Try to auto-categorize based on description
        auto_category_id = auto_categorize_transaction(description, user_id)
        if auto_category_id:
            return auto_category_id
    
    # Default to None if no match found and auto-categorize is off
    return None


def init_default_currencies():
    """Initialize the default currencies in the database"""
    with app.app_context():
        # Check if any currencies exist
        if Currency.query.count() == 0:
            # Add USD as base currency
            usd = Currency(
                code='USD',
                name='US Dollar',
                symbol='$',
                rate_to_base=1.0,
                is_base=True
            )
            
            # Add some common currencies
            eur = Currency(
                code='EUR',
                name='Euro',
                symbol='€',
                rate_to_base=1.1,  # Example rate
                is_base=False
            )
            
            gbp = Currency(
                code='GBP',
                name='British Pound',
                symbol='£',
                rate_to_base=1.3,  # Example rate
                is_base=False
            )
            
            jpy = Currency(
                code='JPY',
                name='Japanese Yen',
                symbol='¥',
                rate_to_base=0.0091,  # Example rate
                is_base=False
            )
            
            db.session.add(usd)
            db.session.add(eur)
            db.session.add(gbp)
            db.session.add(jpy)
            
            try:
                db.session.commit()
                print("Default currencies initialized")
            except Exception as e:
                db.session.rollback()
                print(f"Error initializing currencies: {str(e)}")


def convert_currency(amount, from_code, to_code):
    """Convert an amount from one currency to another"""
    if from_code == to_code:
        return amount
    
    from_currency = Currency.query.filter_by(code=from_code).first()
    to_currency = Currency.query.filter_by(code=to_code).first()
    
    if not from_currency or not to_currency:
        return amount  # Return original if either currency not found
    
    # Get base currency for reference
    base_currency = Currency.query.filter_by(is_base=True).first()
    if not base_currency:
        return amount  # Cannot convert without a base currency
    
    # First convert amount to base currency
    if from_code == base_currency.code:
        # Amount is already in base currency
        amount_in_base = amount
    else:
        # Convert from source currency to base currency
        # The rate_to_base represents how much of the base currency 
        # equals 1 unit of this currency
        amount_in_base = amount * from_currency.rate_to_base
    
    # Then convert from base currency to target currency
    if to_code == base_currency.code:
        # Target is base currency, so we're done
        return amount_in_base
    else:
        # Convert from base currency to target currency
        # We divide by the target currency's rate_to_base to get 
        # the equivalent amount in the target currency
        return amount_in_base / to_currency.rate_to_base

def create_scheduled_expenses():
    """Create expense instances for active recurring expenses"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Find active recurring expenses
    active_recurring = RecurringExpense.query.filter_by(active=True).all()
    
    for recurring in active_recurring:
        # Skip if end date is set and passed
        if recurring.end_date and recurring.end_date < today:
            continue
            
        # Determine if we need to create an expense based on frequency and last created date
        create_expense = False
        last_date = recurring.last_created or recurring.start_date
        
        if recurring.frequency == 'daily':
            # Create if last was created yesterday or earlier
            if (today - last_date).days >= 1:
                create_expense = True
                
        elif recurring.frequency == 'weekly':
            # Create if last was created 7 days ago or more
            if (today - last_date).days >= 7:
                create_expense = True
                
        elif recurring.frequency == 'monthly':
            # Create if we're in a new month from the last creation
            last_month = last_date.month
            last_year = last_date.year
            
            current_month = today.month
            current_year = today.year
            
            if current_year > last_year or (current_year == last_year and current_month > last_month):
                create_expense = True
                
        elif recurring.frequency == 'yearly':
            # Create if we're in a new year from the last creation
            if today.year > last_date.year:
                create_expense = True
        
        # Create the expense if needed
        if create_expense:
            expense = recurring.create_expense_instance(today)
            db.session.add(expense)
    
    # Commit all changes
    if active_recurring:
        db.session.commit()
def calculate_iou_data(expenses, users):
    """Calculate who owes whom money based on expenses"""
    # Initialize data structure
    iou_data = {
        'owes_me': {},  # People who owe current user
        'i_owe': {},    # People current user owes
        'net_balance': 0  # Overall balance (positive if owed money)
    }
    
    # Calculate balances
    for expense in expenses:
        splits = expense.calculate_splits()
        
        # If current user is the payer
        if expense.paid_by == current_user.id:
            # Track what others owe current user
            for split in splits['splits']:
                user_id = split['email']
                user_name = split['name']
                amount = split['amount']
                
                if user_id not in iou_data['owes_me']:
                    iou_data['owes_me'][user_id] = {'name': user_name, 'amount': 0}
                iou_data['owes_me'][user_id]['amount'] += amount
        
        # If current user is in the splits (but not the payer)
        elif current_user.id in [split['email'] for split in splits['splits']]:
            payer_id = expense.paid_by
            payer = User.query.filter_by(id=payer_id).first()
            
            # Find current user's split amount
            current_user_split = next((split['amount'] for split in splits['splits'] if split['email'] == current_user.id), 0)
            
            if payer_id not in iou_data['i_owe']:
                iou_data['i_owe'][payer_id] = {'name': payer.name, 'amount': 0}
            iou_data['i_owe'][payer_id]['amount'] += current_user_split
    
    # Calculate net balance
    total_owed = sum(data['amount'] for data in iou_data['owes_me'].values())
    total_owing = sum(data['amount'] for data in iou_data['i_owe'].values())
    iou_data['net_balance'] = total_owed - total_owing
    
    return iou_data

def calculate_balances(user_id):
    """Calculate balances between the current user and all other users"""
    balances = {}
    
    # Step 1: Calculate balances from expenses
    expenses = Expense.query.filter(
        or_(
            Expense.paid_by == user_id,
            Expense.split_with.like(f'%{user_id}%')
        )
    ).all()
    
    for expense in expenses:
        splits = expense.calculate_splits()
        
        # If current user paid for the expense
        if expense.paid_by == user_id:
            # Add what others owe to current user
            for split in splits['splits']:
                other_user_id = split['email']
                if other_user_id != user_id:
                    if other_user_id not in balances:
                        other_user = User.query.filter_by(id=other_user_id).first()
                        balances[other_user_id] = {
                            'user_id': other_user_id,
                            'name': other_user.name if other_user else 'Unknown',
                            'email': other_user_id,
                            'amount': 0
                        }
                    balances[other_user_id]['amount'] += split['amount']
        else:
            # If someone else paid and current user owes them
            payer_id = expense.paid_by
            
            # Find current user's portion
            current_user_portion = 0
            
            # Check if current user is in the splits
            for split in splits['splits']:
                if split['email'] == user_id:
                    current_user_portion = split['amount']
                    break
            
            if current_user_portion > 0:
                if payer_id not in balances:
                    payer = User.query.filter_by(id=payer_id).first()
                    balances[payer_id] = {
                        'user_id': payer_id,
                        'name': payer.name if payer else 'Unknown',
                        'email': payer_id,
                        'amount': 0
                    }
                balances[payer_id]['amount'] -= current_user_portion
    
    # Step 2: Adjust balances based on settlements
    settlements = Settlement.query.filter(
        or_(
            Settlement.payer_id == user_id,
            Settlement.receiver_id == user_id
        )
    ).all()
    
    for settlement in settlements:
        if settlement.payer_id == user_id:
            # Current user paid money to someone else
            other_user_id = settlement.receiver_id
            if other_user_id not in balances:
                other_user = User.query.filter_by(id=other_user_id).first()
                balances[other_user_id] = {
                    'user_id': other_user_id,
                    'name': other_user.name if other_user else 'Unknown',
                    'email': other_user_id,
                    'amount': 0
                }
            # FIX: When current user pays someone, it INCREASES how much they owe the current user
            # Change from -= to += 
            balances[other_user_id]['amount'] += settlement.amount
            
        elif settlement.receiver_id == user_id:
            # Current user received money from someone else
            other_user_id = settlement.payer_id
            if other_user_id not in balances:
                other_user = User.query.filter_by(id=other_user_id).first()
                balances[other_user_id] = {
                    'user_id': other_user_id,
                    'name': other_user.name if other_user else 'Unknown',
                    'email': other_user_id,
                    'amount': 0
                }
            # FIX: When current user receives money, it DECREASES how much they're owed
            # Change from += to -=
            balances[other_user_id]['amount'] -= settlement.amount
    
    # Return only non-zero balances
    return [balance for balance in balances.values() if abs(balance['amount']) > 0.01]

def get_base_currency():
    """Get the current user's default currency or fall back to base currency if not set"""
    if current_user.is_authenticated and current_user.default_currency_code and current_user.default_currency:
        # User has set a default currency, use that
        return {
            'code': current_user.default_currency.code,
            'symbol': current_user.default_currency.symbol,
            'name': current_user.default_currency.name
        }
    else:
        # Fall back to system base currency if user has no preference
        base_currency = Currency.query.filter_by(is_base=True).first()
        if not base_currency:
            # Default to USD if no base currency is set
            return {'code': 'USD', 'symbol': '$', 'name': 'US Dollar'}
        return {
            'code': base_currency.code,
            'symbol': base_currency.symbol,
            'name': base_currency.name
        }
    

@app.before_first_request
def check_db_structure():
    """
    Check database structure and add any missing columns.
    This function runs before the first request to ensure the database schema is up-to-date.
    """
    with app.app_context():
        app.logger.info("Checking database structure...")
        inspector = inspect(db.engine)
        
        # Check User model for user_color column
        users_columns = [col['name'] for col in inspector.get_columns('users')]
        if 'user_color' not in users_columns:
            app.logger.warning("Missing user_color column in users table - adding it now")
            db.session.execute(text('ALTER TABLE users ADD COLUMN user_color VARCHAR(7) DEFAULT "#15803d"'))
            db.session.commit()
            app.logger.info("Added user_color column to users table")
            
        # Check for OIDC columns
        if 'oidc_id' not in users_columns:
            app.logger.warning("Missing oidc_id column in users table - adding it now")
            db.session.execute(text('ALTER TABLE users ADD COLUMN oidc_id VARCHAR(255)'))
            db.session.commit()
            app.logger.info("Added oidc_id column to users table")
            
            # Create index on oidc_id column
            indexes = [idx['name'] for idx in inspector.get_indexes('users')]
            if 'ix_users_oidc_id' not in indexes:
                db.session.execute(text('CREATE UNIQUE INDEX ix_users_oidc_id ON users (oidc_id)'))
                db.session.commit()
                app.logger.info("Created index on oidc_id column")
                
        if 'oidc_provider' not in users_columns:
            app.logger.warning("Missing oidc_provider column in users table - adding it now")
            db.session.execute(text('ALTER TABLE users ADD COLUMN oidc_provider VARCHAR(50)'))
            db.session.commit()
            app.logger.info("Added oidc_provider column to users table")
            
        if 'last_login' not in users_columns:
            app.logger.warning("Missing last_login column in users table - adding it now")
            # Change DATETIME to TIMESTAMP for PostgreSQL compatibility
            db.session.execute(text('ALTER TABLE users ADD COLUMN last_login TIMESTAMP'))
            db.session.commit()
            app.logger.info("Added last_login column to users table")
            
        app.logger.info("Database structure check completed")

@app.context_processor
def utility_processor():
    def get_user_color(user_id):
        """
        Generate a consistent color for a user based on their ID
        This ensures the same user always gets the same color
        """
        import hashlib

        # Use MD5 hash to generate a consistent color
        hash_object = hashlib.md5(user_id.encode())
        hash_hex = hash_object.hexdigest()
        
        # Use the first 6 characters of the hash to create a color
        # This ensures a consistent but pseudo-random color
        r = int(hash_hex[:2], 16)
        g = int(hash_hex[2:4], 16)
        b = int(hash_hex[4:6], 16)
        
        # Ensure the color is not too light
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        if brightness > 180:
            # If too bright, darken the color
            r = min(r * 0.7, 255)
            g = min(g * 0.7, 255)
            b = min(b * 0.7, 255)
        
        return f'rgb({r},{g},{b})'

    def get_user_by_id(user_id):
        """
        Retrieve a user by their ID
        Returns None if user not found to prevent template errors
        """
        return User.query.filter_by(id=user_id).first()
    
    def get_category_icon_html(category):
        """
        Generate HTML for a category icon with proper styling
        """
        if not category:
            return '<i class="fas fa-tag"></i>'

        icon = category.icon or 'fa-tag'
        color = category.color or '#6c757d'

        return f'<i class="fas {icon}" style="color: {color};"></i>'

    def get_categories_as_tree():
        """
        Return categories in a hierarchical structure for dropdowns
        """
        # Get top-level categories
        top_categories = Category.query.filter_by(
            user_id=current_user.id,
            parent_id=None
        ).order_by(Category.name).all()

        result = []

        # Build tree structure
        for category in top_categories:
            cat_data = {
                'id': category.id,
                'name': category.name,
                'icon': category.icon,
                'color': category.color,
                'subcategories': []
            }

            # Add subcategories
            for subcat in category.subcategories:
                cat_data['subcategories'].append({
                    'id': subcat.id,
                    'name': subcat.name,
                    'icon': subcat.icon,
                    'color': subcat.color
                })

            result.append(cat_data)

        return result
    
    def get_budget_status_for_category(category_id):
        """Get budget status for a specific category"""
        if not current_user.is_authenticated:
            return None
            
        # Find active budget for this category
        budget = Budget.query.filter_by(
            user_id=current_user.id,
            category_id=category_id,
            active=True
        ).first()
        
        if not budget:
            return None
            
        return {
            'id': budget.id,
            'percentage': budget.get_progress_percentage(),
            'status': budget.get_status(),
            'amount': budget.amount,
            'spent': budget.calculate_spent_amount(),
            'remaining': budget.get_remaining_amount()
        }
    
    def get_account_by_id(account_id):
        """Retrieve an account by its ID"""
        return Account.query.get(account_id)

    # Return a single dictionary containing all functions
    return {
        'get_user_color': get_user_color,
        'get_user_by_id': get_user_by_id,
        'get_category_icon_html': get_category_icon_html,
        'get_categories_as_tree': get_categories_as_tree,
        'get_budget_status_for_category': get_budget_status_for_category,
        'get_account_by_id': get_account_by_id
    }
    


    

#--------------------
# ROUTES: Categories
#--------------------


def has_default_categories(user_id):
    """Check if a user already has the default category set"""
    # We'll check for a few specific default categories to determine if defaults were already created
    default_category_names = ["Housing", "Food", "Transportation", "Shopping", "Entertainment", "Health"]
    
    # Count how many of these default categories the user has
    match_count = Category.query.filter(
        Category.user_id == user_id,
        Category.name.in_(default_category_names),
        Category.parent_id == None  # Top-level categories only
    ).count()
    
    # If they have at least 4 of these categories, assume defaults were created
    return match_count >= 4

@app.route('/categories/create_defaults', methods=['POST'])
@login_required_dev
def user_create_default_categories():
    """Allow a user to create default categories for themselves"""
    # Check if user already has default categories
    if has_default_categories(current_user.id):
        flash('You already have the default categories.')
        return redirect(url_for('manage_categories'))
    
    # Create default categories
    create_default_categories(current_user.id)
    flash('Default categories created successfully!')
    
    return redirect(url_for('manage_categories'))


@app.route('/categories')
@login_required_dev
def manage_categories():
    """View and manage expense categories"""
    # Get all top-level categories
    categories = Category.query.filter_by(
        user_id=current_user.id,
        parent_id=None
    ).order_by(Category.name).all()

    # Get all FontAwesome icons for the icon picker
    icons = [
        "fa-home", "fa-building", "fa-bolt", "fa-tools", 
        "fa-utensils", "fa-shopping-basket", "fa-hamburger", "fa-coffee",
        "fa-car", "fa-gas-pump", "fa-bus", "fa-taxi",
        "fa-shopping-cart", "fa-tshirt", "fa-laptop", "fa-gift",
        "fa-film", "fa-ticket-alt", "fa-music", "fa-play-circle",
        "fa-heartbeat", "fa-stethoscope", "fa-prescription-bottle", "fa-dumbbell",
        "fa-user", "fa-spa", "fa-graduation-cap",
        "fa-question-circle", "fa-tag", "fa-money-bill", "fa-credit-card",
        "fa-plane", "fa-hotel", "fa-glass-cheers", "fa-book", "fa-gamepad", 
        "fa-baby", "fa-dog", "fa-cat", "fa-phone", "fa-wifi"
    ]

    return render_template('categories.html', categories=categories, icons=icons)

@app.route('/categories/add', methods=['POST'])
@login_required_dev
def add_category():
    """Add a new category or subcategory"""
    name = request.form.get('name')
    icon = request.form.get('icon', 'fa-tag')
    color = request.form.get('color', "#6c757d")
    parent_id = request.form.get('parent_id')
    if parent_id == "":
        parent_id = None
    if not name:
        flash('Category name is required')
        return redirect(url_for('manage_categories'))

    # Validate parent category belongs to user
    if parent_id:
        parent = Category.query.get(parent_id)
        if not parent or parent.user_id != current_user.id:
            flash('Invalid parent category')
            return redirect(url_for('manage_categories'))

    category = Category(
        name=name,
        icon=icon,
        color=color,
        parent_id=parent_id,
        user_id=current_user.id
    )

    db.session.add(category)
    db.session.commit()

    flash('Category added successfully')
    return redirect(url_for('manage_categories'))

@app.route('/categories/edit/<int:category_id>', methods=['POST'])
@login_required_dev
def edit_category(category_id):
    """Edit an existing category"""
    category = Category.query.get_or_404(category_id)

    # Check if category belongs to current user
    if category.user_id != current_user.id:
        flash('You don\'t have permission to edit this category')
        return redirect(url_for('manage_categories'))

    # Don't allow editing system categories
    if category.is_system:
        flash('System categories cannot be edited')
        return redirect(url_for('manage_categories'))

    category.name = request.form.get('name', category.name)
    category.icon = request.form.get('icon', category.icon)
    category.color = request.form.get('color', category.color)

    db.session.commit()

    flash('Category updated successfully')
    return redirect(url_for('manage_categories'))

@app.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required_dev
def delete_category(category_id):
    """Debug-enhanced category deletion route"""
    try:
        # Find the category
        category = Category.query.get_or_404(category_id)
        
        # Extensive logging
        app.logger.info(f"Attempting to delete category: {category.name} (ID: {category.id})")
        app.logger.info(f"Category details - User ID: {category.user_id}, Is System: {category.is_system}")
        
        # Security checks
        if category.user_id != current_user.id:
            app.logger.warning(f"Unauthorized delete attempt for category {category_id}")
            flash('You don\'t have permission to delete this category')
            return redirect(url_for('manage_categories'))

        # Don't allow deleting system categories
        if category.is_system:
            app.logger.warning(f"Attempted to delete system category {category_id}")
            flash('System categories cannot be deleted')
            return redirect(url_for('manage_categories'))

        # Check related records before deletion
        expense_count = Expense.query.filter_by(category_id=category_id).count()
        recurring_count = RecurringExpense.query.filter_by(category_id=category_id).count()
        budget_count = Budget.query.filter_by(category_id=category_id).count()
        mapping_count = CategoryMapping.query.filter_by(category_id=category_id).count()
        
        app.logger.info(f"Related records - Expenses: {expense_count}, Recurring: {recurring_count}, Budgets: {budget_count}, Mappings: {mapping_count}")
        
        # Find 'Other' category (fallback)
        other_category = Category.query.filter_by(
            name='Other', 
            user_id=current_user.id,
            is_system=True
        ).first()
        
        app.logger.info(f"Other category found: {bool(other_category)}")
        
        # Subcategories handling
        if category.subcategories:
            app.logger.info(f"Handling {len(category.subcategories)} subcategories")
            for subcategory in category.subcategories:
                # Update or delete related records for subcategory
                Expense.query.filter_by(category_id=subcategory.id).update({
                    'category_id': other_category.id if other_category else None
                })
                RecurringExpense.query.filter_by(category_id=subcategory.id).update({
                    'category_id': other_category.id if other_category else None
                })
                CategoryMapping.query.filter_by(category_id=subcategory.id).delete()
                
                # Log subcategory deletion
                app.logger.info(f"Deleting subcategory: {subcategory.name} (ID: {subcategory.id})")
                db.session.delete(subcategory)
        
        # Update or delete main category's related records
        Expense.query.filter_by(category_id=category_id).update({
            'category_id': other_category.id if other_category else None
        })
        RecurringExpense.query.filter_by(category_id=category_id).update({
            'category_id': other_category.id if other_category else None
        })
        Budget.query.filter_by(category_id=category_id).update({
            'category_id': other_category.id if other_category else None
        })
        CategoryMapping.query.filter_by(category_id=category_id).delete()
        
        # Actually delete the category
        db.session.delete(category)
        
        # Commit changes
        db.session.commit()
        
        app.logger.info(f"Category {category.name} (ID: {category_id}) deleted successfully")
        flash('Category deleted successfully')
        
    except Exception as e:
        # Rollback and log any errors
        db.session.rollback()
        app.logger.error(f"Error deleting category {category_id}: {str(e)}", exc_info=True)
        flash(f'Error deleting category: {str(e)}')
    
    return redirect(url_for('manage_categories'))

#--------------------
# ROUTES: Budget
#--------------------
@app.route('/budgets')
@login_required_dev
@demo_time_limited
def budgets():
    """View and manage budgets"""
    from datetime import datetime

    # Get all budgets for the current user
    user_budgets = Budget.query.filter_by(user_id=current_user.id).order_by(Budget.created_at.desc()).all()
    
    # Get all categories for the form
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    
    # Calculate budget progress for each budget
    budget_data = []
    total_month_budget = 0
    total_month_spent = 0
    
    for budget in user_budgets:
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
    
    # Get base currency for display
    base_currency = get_base_currency()
    
    # Pass the current date to the template
    now = datetime.now()
    
    return render_template('budgets.html',
                          budget_data=budget_data,
                          categories=categories,
                          base_currency=base_currency,
                          total_month_budget=total_month_budget,
                          total_month_spent=total_month_spent,
                          now=now)

@app.route('/budgets/add', methods=['POST'])
@login_required_dev
def add_budget():
    """Add a new budget"""
    try:
        # Get form data
        category_id = request.form.get('category_id')
        amount = float(request.form.get('amount', 0))
        period = request.form.get('period', 'monthly')
        include_subcategories = request.form.get('include_subcategories') == 'on'
        name = request.form.get('name', '').strip() or None
        start_date_str = request.form.get('start_date')
        is_recurring = request.form.get('is_recurring') == 'on'
        
        # Validate category exists
        category = Category.query.get(category_id)
        if not category or category.user_id != current_user.id:
            flash('Invalid category selected.')
            return redirect(url_for('budgets'))
        
        # Parse start date
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.utcnow()
        except ValueError:
            start_date = datetime.utcnow()
        
        # Check if a budget already exists for this category
        existing_budget = Budget.query.filter_by(
            user_id=current_user.id,
            category_id=category_id,
            period=period,
            active=True
        ).first()
        
        if existing_budget:
            flash(f'An active {period} budget already exists for this category. Please edit or deactivate it first.')
            return redirect(url_for('budgets'))
        
        # Create new budget
        budget = Budget(
            user_id=current_user.id,
            category_id=category_id,
            name=name,
            amount=amount,
            period=period,
            include_subcategories=include_subcategories,
            start_date=start_date,
            is_recurring=is_recurring,
            active=True
        )
        
        db.session.add(budget)
        db.session.commit()
        
        flash('Budget added successfully!')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding budget: {str(e)}")
        flash(f'Error adding budget: {str(e)}')
    
    return redirect(url_for('budgets'))

@app.route('/budgets/edit/<int:budget_id>', methods=['POST'])
@login_required_dev
def edit_budget(budget_id):
    """Edit an existing budget"""
    try:
        # Find the budget
        budget = Budget.query.get_or_404(budget_id)
        
        # Security check
        if budget.user_id != current_user.id:
            flash('You do not have permission to edit this budget.')
            return redirect(url_for('budgets'))
        
        # Update fields
        budget.category_id = request.form.get('category_id', budget.category_id)
        budget.name = request.form.get('name', '').strip() or budget.name
        budget.amount = float(request.form.get('amount', budget.amount))
        budget.period = request.form.get('period', budget.period)
        budget.include_subcategories = request.form.get('include_subcategories') == 'on'
        
        if request.form.get('start_date'):
            try:
                budget.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            except ValueError:
                pass  # Keep original if parsing fails
        
        budget.is_recurring = request.form.get('is_recurring') == 'on'
        budget.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Budget updated successfully!')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating budget: {str(e)}")
        flash(f'Error updating budget: {str(e)}')
    
    return redirect(url_for('budgets'))

@app.route('/budgets/toggle/<int:budget_id>', methods=['POST'])
@login_required_dev
def toggle_budget(budget_id):
    """Toggle budget active status"""
    try:
        # Find the budget
        budget = Budget.query.get_or_404(budget_id)
        
        # Security check
        if budget.user_id != current_user.id:
            flash('You do not have permission to modify this budget.')
            return redirect(url_for('budgets'))
        
        # Toggle active status
        budget.active = not budget.active
        db.session.commit()
        
        status = "activated" if budget.active else "deactivated"
        flash(f'Budget {status} successfully!')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error toggling budget: {str(e)}")
        flash(f'Error toggling budget: {str(e)}')
    
    return redirect(url_for('budgets'))

@app.route('/budgets/delete/<int:budget_id>', methods=['POST'])
@login_required_dev
def delete_budget(budget_id):
    """Delete a budget"""
    try:
        # Find the budget
        budget = Budget.query.get_or_404(budget_id)
        
        # Security check
        if budget.user_id != current_user.id:
            flash('You do not have permission to delete this budget.')
            return redirect(url_for('budgets'))
        
        db.session.delete(budget)
        db.session.commit()
        
        flash('Budget deleted successfully!')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting budget: {str(e)}")
        flash(f'Error deleting budget: {str(e)}')
    
    return redirect(url_for('budgets'))

@app.route('/budgets/get/<int:budget_id>', methods=['GET'])
@login_required_dev
def get_budget(budget_id):
    """Get budget details for editing via AJAX"""
    try:
        # Find the budget
        budget = Budget.query.get_or_404(budget_id)
        
        # Security check
        if budget.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to view this budget'
            }), 403
        
        # Get category details
        category = Category.query.get(budget.category_id)
        category_name = category.name if category else "Unknown"
        
        # Format dates
        start_date = budget.start_date.strftime('%Y-%m-%d')
        
        # Calculate spent amount
        spent = budget.calculate_spent_amount()
        remaining = budget.get_remaining_amount()
        percentage = budget.get_progress_percentage()
        status = budget.get_status()
        
        # Return the budget data
        return jsonify({
            'success': True,
            'budget': {
                'id': budget.id,
                'name': budget.name or '',
                'category_id': budget.category_id,
                'category_name': category_name,
                'amount': budget.amount,
                'period': budget.period,
                'include_subcategories': budget.include_subcategories,
                'start_date': start_date,
                'is_recurring': budget.is_recurring,
                'active': budget.active,
                'spent': spent,
                'remaining': remaining,
                'percentage': percentage,
                'status': status
            }
        })
            
    except Exception as e:
        app.logger.error(f"Error retrieving budget {budget_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


def get_budget_summary():
    """Get budget summary for current user"""
    # Get all active budgets
    active_budgets = Budget.query.filter_by(
        user_id=current_user.id,
        active=True
    ).all()
    
    # Process budget data
    budget_summary = {
        'total_budgets': len(active_budgets),
        'over_budget': 0,
        'approaching_limit': 0,
        'under_budget': 0,
        'alert_budgets': []  # For budgets that are over or approaching limit
    }
    
    for budget in active_budgets:
        status = budget.get_status()
        if status == 'over':
            budget_summary['over_budget'] += 1
            budget_summary['alert_budgets'].append({
                'id': budget.id,
                'name': budget.name or budget.category.name,
                'percentage': budget.get_progress_percentage(),
                'status': status,
                'amount': budget.amount,
                'spent': budget.calculate_spent_amount()
            })
        elif status == 'approaching':
            budget_summary['approaching_limit'] += 1
            budget_summary['alert_budgets'].append({
                'id': budget.id,
                'name': budget.name or budget.category.name,
                'percentage': budget.get_progress_percentage(),
                'status': status,
                'amount': budget.amount,
                'spent': budget.calculate_spent_amount()
            })
        else:
            budget_summary['under_budget'] += 1
    
    # Sort alert budgets by percentage (highest first)
    budget_summary['alert_budgets'] = sorted(
        budget_summary['alert_budgets'],
        key=lambda x: x['percentage'],
        reverse=True
    )
    
    return budget_summary
@app.route('/budgets/subcategory-spending/<int:budget_id>')
@login_required_dev
def get_subcategory_spending(budget_id):
    """Get spending details for subcategories of a budget category"""
    try:
        # Find the budget
        budget = Budget.query.get_or_404(budget_id)
        
        # Security check
        if budget.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to view this budget'
            }), 403
        
        # Get the base currency symbol
        base_currency = get_base_currency()
        
        # Check if base_currency is a dictionary or an object
        currency_symbol = base_currency['symbol'] if isinstance(base_currency, dict) else base_currency.symbol
        
        # Get the category and its subcategories
        category = Category.query.get(budget.category_id)
        if not category:
            return jsonify({
                'success': False,
                'message': 'Category not found'
            }), 404
        
        subcategories = []
        
        # Get period dates for this budget
        period_start, period_end = budget.get_current_period_dates()
        
        # If this budget includes the parent category directly
        if not budget.include_subcategories:
            # Only include the parent category itself
            spent = calculate_category_spending(category.id, period_start, period_end)
            
            subcategories.append({
                'id': category.id,
                'name': category.name,
                'icon': category.icon,
                'color': category.color,
                'spent': spent
            })
        else:
            # Include all subcategories
            for subcategory in category.subcategories:
                spent = calculate_category_spending(subcategory.id, period_start, period_end)
                
                subcategories.append({
                    'id': subcategory.id,
                    'name': subcategory.name,
                    'icon': subcategory.icon,
                    'color': subcategory.color,
                    'spent': spent
                })
                
            # If the parent category itself has direct expenses, add it too
            spent = calculate_category_spending(category.id, period_start, period_end, include_subcategories=False)
            
            if spent > 0:
                subcategories.append({
                    'id': category.id,
                    'name': f"{category.name} (direct)",
                    'icon': category.icon,
                    'color': category.color,
                    'spent': spent
                })
        
        # Sort subcategories by spent amount (highest first)
        subcategories = sorted(subcategories, key=lambda x: x['spent'], reverse=True)
        
        return jsonify({
            'success': True,
            'budget_id': budget.id,
            'budget_amount': float(budget.amount),
            'currency_symbol': currency_symbol,
            'subcategories': subcategories
        })
            
    except Exception as e:
        app.logger.error(f"Error retrieving subcategory spending for budget {budget_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

def calculate_category_spending(category_id, start_date, end_date, include_subcategories=True):
    """Calculate total spending for a category within a date range"""
    
    # Get the category
    category = Category.query.get(category_id)
    if not category:
        return 0
    
    total_spent = 0
    
    # 1. Get direct expenses (transactions directly assigned to this category without splits)
    direct_expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.category_id == category_id,
        Expense.date >= start_date,
        Expense.date <= end_date,
        Expense.has_category_splits == False  # Important: only include non-split expenses
    ).all()
    
    # Add up direct expenses
    for expense in direct_expenses:
        # Use amount_base if available (for currency conversion), otherwise use amount
        amount = getattr(expense, 'amount_base', expense.amount)
        total_spent += amount
    
    # 2. Get category splits assigned to this category
    category_splits = CategorySplit.query.join(Expense).filter(
        Expense.user_id == current_user.id,
        CategorySplit.category_id == category_id,
        Expense.date >= start_date,
        Expense.date <= end_date
    ).all()
    
    # Add up split amounts
    for split in category_splits:
        # Use split amount directly - these should already be in the correct currency
        total_spent += split.amount
    
    # 3. Include subcategories if requested and if this is a parent category
    if include_subcategories and not category.parent_id:
        subcategory_ids = [subcat.id for subcat in category.subcategories]
        
        for subcategory_id in subcategory_ids:
            # For each subcategory, repeat the process
            # Process direct expenses
            subcat_direct = Expense.query.filter(
                Expense.user_id == current_user.id,
                Expense.category_id == subcategory_id,
                Expense.date >= start_date,
                Expense.date <= end_date,
                Expense.has_category_splits == False
            ).all()
            
            for expense in subcat_direct:
                amount = getattr(expense, 'amount_base', expense.amount)
                total_spent += amount
            
            # Process split expenses
            subcat_splits = CategorySplit.query.join(Expense).filter(
                Expense.user_id == current_user.id,
                CategorySplit.category_id == subcategory_id,
                Expense.date >= start_date,
                Expense.date <= end_date
            ).all()
            
            for split in subcat_splits:
                total_spent += split.amount
    
    return total_spent

# Add to utility_processor to make budget info available in templates
@app.context_processor
def utility_processor():
    # Previous utility functions...
    
    def get_budget_status_for_category(category_id):
        """Get budget status for a specific category"""
        if not current_user.is_authenticated:
            return None
            
        # Find active budget for this category
        budget = Budget.query.filter_by(
            user_id=current_user.id,
            category_id=category_id,
            active=True
        ).first()
        
        if not budget:
            return None
            
        return {
            'id': budget.id,
            'percentage': budget.get_progress_percentage(),
            'status': budget.get_status(),
            'amount': budget.amount,
            'spent': budget.calculate_spent_amount(),
            'remaining': budget.get_remaining_amount()
        }
    def template_convert_currency(amount, from_code, to_code):
        """Make convert_currency available to templates"""
        return convert_currency(amount, from_code, to_code)
    return {
        # Previous functions...
        'get_budget_status_for_category': get_budget_status_for_category,
        'convert_currency': template_convert_currency 
    }
@app.context_processor
def inject_app_version():
    """Make app version available to all templates"""
    return {
        'app_version': APP_VERSION
    }

@app.route('/budgets/trends-data')
@login_required_dev
def budget_trends_data():
    """Get budget trends data for chart visualization with proper split handling"""
    budget_id = request.args.get('budget_id')
    
    # Default time period (last 6 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Prepare response data structure
    response = {
        'labels': [],
        'actual': [],
        'budget': [],
        'colors': []
    }
    
    # Generate monthly labels
    current_date = start_date
    while current_date <= end_date:
        month_label = current_date.strftime('%b %Y')
        response['labels'].append(month_label)
        current_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    
    # If no budget selected, return all budgets aggregated by month
    if not budget_id:
        # Get all active budgets
        budgets = Budget.query.filter_by(user_id=current_user.id, active=True).all()
        app.logger.debug(f"Found {len(budgets)} active budgets")
        
        # For each month, calculate total budget and spending
        for i, month in enumerate(response['labels']):
            month_date = datetime.strptime(month, '%b %Y')
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                month_end = month_date.replace(year=month_date.year+1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_date.replace(month=month_date.month+1, day=1) - timedelta(days=1)
            
            # Sum all budgets for this month
            monthly_budget = 0
            for budget in budgets:
                if budget.period == 'monthly':
                    monthly_budget += budget.amount
                elif budget.period == 'yearly':
                    monthly_budget += budget.amount / 12
                elif budget.period == 'weekly':
                    # Calculate weeks in this month
                    weeks_in_month = (month_end - month_start).days / 7
                    monthly_budget += budget.amount * weeks_in_month
            
            response['budget'].append(monthly_budget)
            app.logger.debug(f"Month {month}: Budget amount = {monthly_budget}")
            
            # Calculate actual spending for this month
            monthly_spent = 0
            
            # 1. Get regular expenses without splits (no category splits, no user splits)
            direct_expenses = Expense.query.filter(
                Expense.user_id == current_user.id,
                Expense.date >= month_start,
                Expense.date <= month_end,
                Expense.has_category_splits == False,
                Expense.split_with.is_(None) | (Expense.split_with == '')
            ).all()
            
            # Add up direct expenses (no splits)
            direct_total = 0
            for expense in direct_expenses:
                amount = getattr(expense, 'amount_base', expense.amount)
                direct_total += amount
            
            monthly_spent += direct_total
            app.logger.debug(f"Month {month}: Direct expenses (no splits) = {direct_total}")
            
            # 2. Get expenses that have user splits but no category splits
            user_split_expenses = Expense.query.filter(
                Expense.user_id == current_user.id,
                Expense.date >= month_start,
                Expense.date <= month_end,
                Expense.has_category_splits == False,
                Expense.split_with.isnot(None) & (Expense.split_with != '')
            ).all()
            
            # Calculate user's portion for each user split expense
            user_split_total = 0
            for expense in user_split_expenses:
                # Get split information with error handling
                try:
                    split_info = expense.calculate_splits()
                    if not split_info:
                        continue
                    
                    # Calculate user's portion
                    user_amount = 0
                    
                    # Check if user is payer and not in split list
                    if expense.paid_by == current_user.id and (
                        not expense.split_with or 
                        current_user.id not in expense.split_with.split(',')
                    ):
                        user_amount = split_info['payer']['amount']
                    else:
                        # Look for user in splits
                        for split in split_info['splits']:
                            if split['email'] == current_user.id:
                                user_amount = split['amount']
                                break
                    
                    user_split_total += user_amount
                    
                except Exception as e:
                    app.logger.error(f"Error calculating splits for expense {expense.id}: {str(e)}")
                    # Fallback: Just divide by number of participants (including payer)
                    participants = 1  # Start with payer
                    if expense.split_with:
                        participants += len(expense.split_with.split(','))
                    
                    if participants > 0:
                        user_split_total += expense.amount / participants
            
            monthly_spent += user_split_total
            app.logger.debug(f"Month {month}: User split expenses = {user_split_total}")
            
            # 3. Get expenses with category splits
            split_expenses = Expense.query.filter(
                Expense.user_id == current_user.id,
                Expense.date >= month_start,
                Expense.date <= month_end,
                Expense.has_category_splits == True
            ).all()
            
            # Process each split expense
            category_split_total = 0
            for split_expense in split_expenses:
                # Get category splits for this expense
                category_splits = CategorySplit.query.filter_by(expense_id=split_expense.id).all()
                
                # Calculate the base amount from category splits
                split_amount = sum(split.amount for split in category_splits)
                
                # If expense also has user splits, calculate user's portion
                if split_expense.split_with and split_expense.split_with.strip():
                    try:
                        split_info = split_expense.calculate_splits()
                        if not split_info:
                            # If no split info, treat as full amount
                            category_split_total += split_amount
                            continue
                        
                        # Calculate user's percentage of the total expense
                        user_percentage = 0
                        
                        # Check if user is payer and not in split list
                        if split_expense.paid_by == current_user.id and current_user.id not in split_expense.split_with.split(','):
                            user_percentage = split_info['payer']['amount'] / split_expense.amount if split_expense.amount > 0 else 0
                        else:
                            # Look for user in splits
                            for split in split_info['splits']:
                                if split['email'] == current_user.id:
                                    user_percentage = split['amount'] / split_expense.amount if split_expense.amount > 0 else 0
                                    break
                        
                        # Apply user's percentage to the category amount
                        category_split_total += split_amount * user_percentage
                        
                    except Exception as e:
                        app.logger.error(f"Error calculating splits for expense {split_expense.id}: {str(e)}")
                        # Fallback: Just divide by number of participants
                        participants = 1  # Start with payer
                        if split_expense.split_with:
                            participants += len(split_expense.split_with.split(','))
                        
                        if participants > 0:
                            category_split_total += split_amount / participants
                else:
                    # No user splits, use the full category split amount
                    category_split_total += split_amount
            
            monthly_spent += category_split_total
            app.logger.debug(f"Month {month}: Category split expenses = {category_split_total}")
            
            # Add the calculated amounts to the response
            response['actual'].append(monthly_spent)
            
            # Set color based on whether spending exceeds budget
            color = '#ef4444' if monthly_spent > monthly_budget else '#22c55e'
            response['colors'].append(color)
            
            app.logger.debug(f"Month {month}: Total monthly spent = {monthly_spent}")
    else:
        # Get specific budget
        budget = Budget.query.get_or_404(budget_id)
        
        # Security check
        if budget.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        app.logger.debug(f"Processing trends for single budget {budget_id}: {budget.name or 'Unnamed'}, amount={budget.amount}")
        
        # Process each month
        for i, month in enumerate(response['labels']):
            month_date = datetime.strptime(month, '%b %Y')
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                month_end = month_date.replace(year=month_date.year+1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_date.replace(month=month_date.month+1, day=1) - timedelta(days=1)
            
            # Get budget amount for this month
            monthly_budget = 0
            if budget.period == 'monthly':
                monthly_budget = budget.amount
            elif budget.period == 'yearly':
                monthly_budget = budget.amount / 12
            elif budget.period == 'weekly':
                # Calculate weeks in this month
                weeks_in_month = (month_end - month_start).days / 7
                monthly_budget = budget.amount * weeks_in_month
                
            response['budget'].append(monthly_budget)
            app.logger.debug(f"Month {month}: Budget amount = {monthly_budget}")
            
            # Create list of categories to include
            category_ids = [budget.category_id]
            if budget.include_subcategories and budget.category:
                category_ids.extend([subcat.id for subcat in budget.category.subcategories])
            
            # Calculate spending for this category
            monthly_spent = 0
            
            # 1. Get direct expenses (not split by category, not split by user)
            direct_expenses = Expense.query.filter(
                Expense.user_id == current_user.id,
                Expense.date >= month_start,
                Expense.date <= month_end,
                Expense.category_id.in_(category_ids),
                Expense.has_category_splits == False,
                Expense.split_with.is_(None) | (Expense.split_with == '')
            ).all()
            
            # Add up direct expenses
            direct_total = 0
            for expense in direct_expenses:
                amount = getattr(expense, 'amount_base', expense.amount)
                direct_total += amount
            
            monthly_spent += direct_total
            app.logger.debug(f"Month {month}: Direct expenses (no splits) = {direct_total}")
            
            # 2. Get expenses with user splits but not category splits
            user_split_expenses = Expense.query.filter(
                Expense.user_id == current_user.id,
                Expense.date >= month_start,
                Expense.date <= month_end,
                Expense.category_id.in_(category_ids),
                Expense.has_category_splits == False,
                Expense.split_with.isnot(None) & (Expense.split_with != '')
            ).all()
            
            # Process user split expenses
            user_split_total = 0
            for expense in user_split_expenses:
                try:
                    # Get split information
                    split_info = expense.calculate_splits()
                    if not split_info:
                        continue
                    
                    # Calculate user's portion
                    user_amount = 0
                    
                    # Check if user is payer and not in split list
                    if expense.paid_by == current_user.id and (
                        not expense.split_with or 
                        current_user.id not in expense.split_with.split(',')
                    ):
                        user_amount = split_info['payer']['amount']
                    else:
                        # Look for user in splits
                        for split in split_info['splits']:
                            if split['email'] == current_user.id:
                                user_amount = split['amount']
                                break
                    
                    user_split_total += user_amount
                    
                except Exception as e:
                    app.logger.error(f"Error calculating splits for expense {expense.id}: {str(e)}")
                    # Fallback: Just divide by number of participants (including payer)
                    participants = 1  # Start with payer
                    if expense.split_with:
                        participants += len(expense.split_with.split(','))
                    
                    if participants > 0:
                        user_split_total += expense.amount / participants
            
            monthly_spent += user_split_total
            app.logger.debug(f"Month {month}: User split expenses = {user_split_total}")
            
            # 3. Get category splits for these categories
            category_splits = CategorySplit.query.join(Expense).filter(
                Expense.user_id == current_user.id,
                Expense.date >= month_start,
                Expense.date <= month_end,
                CategorySplit.category_id.in_(category_ids)
            ).all()
            
            # Group by expense to avoid double counting
            expense_splits = {}
            for split in category_splits:
                if split.expense_id not in expense_splits:
                    expense_splits[split.expense_id] = []
                expense_splits[split.expense_id].append(split)
            
            # Process each expense with category splits
            category_split_total = 0
            for expense_id, splits in expense_splits.items():
                try:
                    # Get the expense
                    expense = Expense.query.get(expense_id)
                    if not expense:
                        continue
                    
                    # Calculate total relevant split amount
                    relevant_amount = sum(split.amount for split in splits)
                    
                    # If expense also has user splits, calculate user's portion
                    if expense.split_with and expense.split_with.strip():
                        split_info = expense.calculate_splits()
                        if not split_info:
                            # If no split info, treat as full amount
                            category_split_total += relevant_amount
                            continue
                        
                        # Calculate user's percentage of the total expense
                        user_percentage = 0
                        
                        # Check if user is payer and not in split list
                        if expense.paid_by == current_user.id and current_user.id not in expense.split_with.split(','):
                            user_percentage = split_info['payer']['amount'] / expense.amount if expense.amount > 0 else 0
                        else:
                            # Look for user in splits
                            for split in split_info['splits']:
                                if split['email'] == current_user.id:
                                    user_percentage = split['amount'] / expense.amount if expense.amount > 0 else 0
                                    break
                        
                        # Apply user's percentage to the category amount
                        user_portion = relevant_amount * user_percentage
                        category_split_total += user_portion
                        app.logger.debug(f"Expense {expense_id}: User percentage {user_percentage}, Amount {relevant_amount}, User portion {user_portion}")
                        
                    else:
                        # No user splits, use the full category split amount
                        category_split_total += relevant_amount
                        
                except Exception as e:
                    app.logger.error(f"Error processing expense {expense_id} with category splits: {str(e)}")
                    # Fallback: Just divide by number of participants
                    expense = Expense.query.get(expense_id)
                    if expense and expense.split_with:
                        participants = 1 + len(expense.split_with.split(','))
                        relevant_amount = sum(split.amount for split in splits)
                        category_split_total += relevant_amount / participants
                    else:
                        # If no split info or can't get expense, add full amount
                        category_split_total += sum(split.amount for split in splits)
            
            monthly_spent += category_split_total
            app.logger.debug(f"Month {month}: Category split expenses = {category_split_total}")
            
            # Add the calculated amounts to the response
            response['actual'].append(monthly_spent)
            
            # Set color based on whether spending exceeds budget
            color = '#ef4444' if monthly_spent > monthly_budget else '#22c55e'
            response['colors'].append(color)
            
            app.logger.debug(f"Month {month}: Total monthly spent = {monthly_spent}, Budget = {monthly_budget}")
            
    # Debug log the final response data
    app.logger.debug(f"Budget trends response: labels={response['labels']}")
    app.logger.debug(f"Budget trends response: budget={response['budget']}")
    app.logger.debug(f"Budget trends response: actual={response['actual']}")
    
    return jsonify(response)


@app.route('/budgets/transactions/<int:budget_id>')
@login_required_dev
@demo_time_limited
def budget_transactions(budget_id):
    """Get transactions related to a specific budget with proper split handling"""
    # Get the budget
    budget = Budget.query.get_or_404(budget_id)
    
    # Security check
    if budget.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Default time period (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    transactions = []
    
    # Create list of categories to include
    category_ids = [budget.category_id]
    if budget.include_subcategories and budget.category:
        category_ids.extend([subcat.id for subcat in budget.category.subcategories])
    
    # 1. Get expenses directly assigned to these categories (not split by category)
    direct_expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.category_id.in_(category_ids),
        Expense.has_category_splits == False
    ).order_by(Expense.date.desc()).all()
    
    # 2. Get expenses with category splits for these categories
    split_expenses_query = db.session.query(Expense).join(
        CategorySplit, Expense.id == CategorySplit.expense_id
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        CategorySplit.category_id.in_(category_ids)
    ).order_by(Expense.date.desc()).distinct()
    
    # Combine and sort expenses by date
    all_expenses = sorted(
        list(direct_expenses) + list(split_expenses_query.all()),
        key=lambda x: x.date,
        reverse=True
    )[:50]  # Limit to 50 transactions
    
    # Format transactions for the response
    for expense in all_expenses:
        # Initialize basic transaction info
        transaction = {
            'id': expense.id,
            'description': expense.description,
            'date': expense.date.strftime('%Y-%m-%d'),
            'card_used': expense.card_used,
            'transaction_type': expense.transaction_type,
            'has_category_splits': expense.has_category_splits,
            'has_user_splits': bool(expense.split_with and expense.split_with.strip())
        }
        
        # Get split information if needed
        split_info = expense.calculate_splits() if transaction['has_user_splits'] else None
        
        # Handle amount based on split type
        if expense.has_category_splits:
            # Get category splits relevant to this budget
            relevant_cat_splits = CategorySplit.query.filter(
                CategorySplit.expense_id == expense.id,
                CategorySplit.category_id.in_(category_ids)
            ).all()
            
            # Calculate relevant category amount
            relevant_cat_amount = sum(split.amount for split in relevant_cat_splits)
            
            # If expense also has user splits, calculate the user's portion
            if transaction['has_user_splits'] and split_info:
                # Calculate user's percentage of the total expense
                user_percentage = 0
                
                # Check if user is payer and not in split list
                if expense.paid_by == current_user.id and current_user.id not in expense.split_with.split(','):
                    user_percentage = split_info['payer']['amount'] / expense.amount if expense.amount > 0 else 0
                else:
                    # Look for user in splits
                    for split in split_info['splits']:
                        if split['email'] == current_user.id:
                            user_percentage = split['amount'] / expense.amount if expense.amount > 0 else 0
                            break
                
                # Apply user's percentage to the category amount
                transaction['amount'] = relevant_cat_amount * user_percentage
                
                # Add split details for display
                transaction['split_details'] = {
                    'total_users': len(split_info['splits']) + (1 if split_info['payer']['amount'] > 0 else 0),
                    'user_portion_percentage': user_percentage * 100,
                    'category_amount': relevant_cat_amount,
                    'user_amount': transaction['amount'],
                    'total_amount': expense.amount
                }
            else:
                # No user splits, use the full category amount
                transaction['amount'] = relevant_cat_amount
            
            # Add category information from the first relevant split
            if relevant_cat_splits:
                cat_id = relevant_cat_splits[0].category_id
                category = Category.query.get(cat_id)
                if category:
                    transaction['category_name'] = category.name
                    transaction['category_icon'] = category.icon
                    transaction['category_color'] = category.color
                else:
                    transaction['category_name'] = 'Split Category'
                    transaction['category_icon'] = 'fa-tags'
                    transaction['category_color'] = '#6c757d'
        else:
            # For non-category-split expenses
            if transaction['has_user_splits'] and split_info:
                # Calculate user's portion
                user_amount = 0
                
                # Check if user is payer and not in split list
                if expense.paid_by == current_user.id and current_user.id not in expense.split_with.split(','):
                    user_amount = split_info['payer']['amount']
                else:
                    # Look for user in splits
                    for split in split_info['splits']:
                        if split['email'] == current_user.id:
                            user_amount = split['amount']
                            break
                
                transaction['amount'] = user_amount
                
                # Add split details for display
                total_users = len(split_info['splits']) + (1 if split_info['payer']['amount'] > 0 else 0)
                transaction['split_details'] = {
                    'total_users': total_users,
                    'user_portion_percentage': (user_amount / expense.amount * 100) if expense.amount > 0 else 0,
                    'user_amount': user_amount,
                    'total_amount': expense.amount
                }
            else:
                # Regular non-split expense, use the full amount
                transaction['amount'] = expense.amount
            
            # Add category information
            if expense.category_id:
                category = Category.query.get(expense.category_id)
                if category:
                    transaction['category_name'] = category.name
                    transaction['category_icon'] = category.icon
                    transaction['category_color'] = category.color
                else:
                    transaction['category_name'] = 'Uncategorized'
                    transaction['category_icon'] = 'fa-tag'
                    transaction['category_color'] = '#6c757d'
            else:
                transaction['category_name'] = 'Uncategorized'
                transaction['category_icon'] = 'fa-tag'
                transaction['category_color'] = '#6c757d'
        
        # Add the original total amount for reference
        transaction['original_amount'] = expense.amount
        
        # Add tags if available
        if hasattr(expense, 'tags') and expense.tags:
            transaction['tags'] = [tag.name for tag in expense.tags]
        
        transactions.append(transaction)
    
    return jsonify({
        'transactions': transactions,
        'budget_id': budget_id,
        'budget_name': budget.name or (budget.category.name if budget.category else "Budget")
    })


@app.route('/budgets/summary-data')
@login_required_dev
def budget_summary_data():
    """Get budget summary data for charts and displays"""
    try:
        # Get all active monthly budgets
        monthly_budgets = Budget.query.filter_by(
            user_id=current_user.id,
            period='monthly',
            active=True
        ).all()
        
        # Calculate totals
        total_budget = sum(budget.amount for budget in monthly_budgets)
        total_spent = sum(budget.calculate_spent_amount() for budget in monthly_budgets)
        
        # Get budgets with their data
        budget_data = []
        for budget in monthly_budgets:
            spent = budget.calculate_spent_amount()
            percentage = budget.get_progress_percentage()
            status = budget.get_status()
            
            # Get category info
            category = Category.query.get(budget.category_id)
            category_name = category.name if category else "Unknown"
            category_color = category.color if category else "#6c757d"
            
            budget_data.append({
                'id': budget.id,
                'name': budget.name or category_name,
                'amount': budget.amount,
                'spent': spent,
                'percentage': percentage,
                'status': status,
                'color': category_color
            })
        
        return jsonify({
            'success': True,
            'total_budget': total_budget,
            'total_spent': total_spent,
            'budgets': budget_data
        })
            
    except Exception as e:
        app.logger.error(f"Error retrieving budget summary data: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
    
    
@app.route('/api/categories')
@login_required_dev
def get_categories_api():
    """API endpoint to fetch categories for the current user"""
    try:
        # Get all categories for the current user
        categories = Category.query.filter_by(user_id=current_user.id).all()
        
        # Convert to JSON-serializable format
        result = []
        for category in categories:
            result.append({
                'id': category.id,
                'name': category.name,
                'icon': category.icon,
                'color': category.color,
                'parent_id': category.parent_id,
                # Add this to help with displaying in the UI
                'is_parent': category.parent_id is None
            })
        
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error fetching categories: {str(e)}")
        return jsonify({'error': str(e)}), 500
#--------------------
# ROUTES: user 
#--------------------
@app.route('/profile')
@login_required_dev
def profile():
    """User profile page with settings to change password and personal color"""
    # Get user's account creation date (approximating from join date since we don't store it)
    account_created = current_user.created_at.strftime('%Y-%m-%d') if current_user.created_at else "Account creation date not available"
    
    # Get user color (default to app's primary green if not set)
    user_color = current_user.user_color if hasattr(current_user, 'user_color') and current_user.user_color else "#15803d"
    
    # Get available currencies for default currency selection
    currencies = Currency.query.all()
    
    # Check if OIDC is enabled
    oidc_enabled = app.config.get('OIDC_ENABLED', False)
    
    return render_template('profile.html', 
                          user_color=user_color,
                          account_created=account_created,
                          currencies=currencies,
                          oidc_enabled=oidc_enabled)

@app.route('/profile/change_password', methods=['POST'])
@login_required_dev
def change_password():
    """Handle password change request"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate inputs
    if not current_password or not new_password or not confirm_password:
        flash('All password fields are required')
        return redirect(url_for('profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match')
        return redirect(url_for('profile'))
    
    # Verify current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect')
        return redirect(url_for('profile'))
    
    # Set new password
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Password updated successfully')
    return redirect(url_for('profile'))

@app.route('/profile/update_color', methods=['POST'])
@login_required_dev
def update_color():
    """Update user's personal color"""
    # Retrieve color from form, defaulting to primary green
    user_color = request.form.get('user_color', '#15803d').strip()
    
    # Validate hex color format (supports 3 or 6 digit hex colors)
    hex_pattern = r'^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$'
    if not user_color or not re.match(hex_pattern, user_color):
        flash('Invalid color format. Please use a valid hex color code.')
        return redirect(url_for('profile'))
    
    # Normalize to 6-digit hex if 3-digit shorthand is used
    if len(user_color) == 4:  # #RGB format
        user_color = '#' + ''.join(2 * c for c in user_color[1:])
    
    # Update user's color
    current_user.user_color = user_color
    db.session.commit()
    
    flash('Your personal color has been updated')
    return redirect(url_for('profile'))


#--------------------
# ROUTES: stats and reports
#--------------------

# This helps verify what data is actually being passed to the template

def generate_monthly_report_data(user_id, year, month):
    """Generate data for monthly expense report"""
    user = User.query.get(user_id)
    if not user:
        return None
    
    # Calculate date range for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Get base currency
    base_currency = get_base_currency()
    currency_symbol = base_currency['symbol'] if isinstance(base_currency, dict) else base_currency.symbol
    
    # Get user's expenses for the month
    query_filters = [
        or_(
            Expense.user_id == user_id,
            Expense.split_with.like(f'%{user_id}%')
        ),
        Expense.date >= start_date,
        Expense.date <= end_date
    ]
    
    expenses_raw = Expense.query.filter(and_(*query_filters)).order_by(Expense.date).all()
    
    # Calculate user's portion of expenses
    expenses = []
    total_spent = 0
    
    for expense in expenses_raw:
        # Calculate splits
        splits = expense.calculate_splits()
        
        # Get user's portion
        user_portion = 0
        if expense.paid_by == user_id:
            user_portion = splits['payer']['amount']
        else:
            for split in splits['splits']:
                if split['email'] == user_id:
                    user_portion = split['amount']
                    break
        
        if user_portion > 0:
            expenses.append({
                'id': expense.id,
                'description': expense.description,
                'date': expense.date,
                'amount': user_portion,
                'category': expense.category.name if hasattr(expense, 'category') and expense.category else 'Uncategorized'
            })
            total_spent += user_portion
    
    # Get budget status
    budgets = Budget.query.filter_by(user_id=user_id, active=True).all()
    budget_status = []
    
    for budget in budgets:
        # Calculate budget status for this specific month
        spent = 0
        for expense in expenses:
            if hasattr(expense, 'category_id') and expense.category_id == budget.category_id:
                spent += expense['amount']
        
        percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
        status = 'under'
        if percentage >= 100:
            status = 'over'
        elif percentage >= 85:
            status = 'approaching'
        
        budget_status.append({
            'name': budget.name or (budget.category.name if budget.category else 'Budget'),
            'amount': budget.amount,
            'spent': spent,
            'remaining': budget.amount - spent,
            'percentage': percentage,
            'status': status
        })
    
    # Get category breakdown
    categories = {}
    for expense in expenses:
        category = expense.get('category', 'Uncategorized')
        if category not in categories:
            categories[category] = 0
        categories[category] += expense['amount']
    
    # Format category data
    category_data = []
    for category, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total_spent * 100) if total_spent > 0 else 0
        category_data.append({
            'name': category,
            'amount': amount,
            'percentage': percentage
        })
    
    # Get balance information
    balances = calculate_balances(user_id)
    you_owe = []
    you_are_owed = []
    net_balance = 0
    
    for balance in balances:
        if balance['amount'] < 0:
            you_owe.append({
                'name': balance['name'],
                'email': balance['email'],
                'amount': abs(balance['amount'])
            })
            net_balance -= abs(balance['amount'])
        elif balance['amount'] > 0:
            you_are_owed.append({
                'name': balance['name'],
                'email': balance['email'],
                'amount': balance['amount']
            })
            net_balance += balance['amount']
    
    # Get comparison with previous month
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    
    prev_start_date = datetime(prev_year, prev_month, 1)
    if prev_month == 12:
        prev_end_date = datetime(prev_year + 1, 1, 1) - timedelta(days=1)
    else:
        prev_end_date = datetime(prev_year, prev_month + 1, 1) - timedelta(days=1)
    
    prev_query_filters = [
        or_(
            Expense.user_id == user_id,
            Expense.split_with.like(f'%{user_id}%')
        ),
        Expense.date >= prev_start_date,
        Expense.date <= prev_end_date
    ]
    
    prev_expenses = Expense.query.filter(and_(*prev_query_filters)).all()
    prev_total = 0
    
    for expense in prev_expenses:
        splits = expense.calculate_splits()
        user_portion = 0
        
        if expense.paid_by == user_id:
            user_portion = splits['payer']['amount']
        else:
            for split in splits['splits']:
                if split['email'] == user_id:
                    user_portion = split['amount']
                    break
        
        prev_total += user_portion
    
    # Calculate spending trend
    if prev_total > 0:
        spending_trend = ((total_spent - prev_total) / prev_total) * 100
    else:
        spending_trend = 0
    
    return {
        'user': user,
        'month_name': calendar.month_name[month],
        'year': year,
        'currency_symbol': currency_symbol,
        'total_spent': total_spent,
        'spending_trend': spending_trend,
        'prev_total': prev_total,
        'expense_count': len(expenses),
        'budget_status': budget_status,
        'category_data': category_data,
        'you_owe': you_owe,
        'you_are_owed': you_are_owed,
        'net_balance': net_balance,
        'top_expenses': sorted(expenses, key=lambda x: x['amount'], reverse=True)[:5]
    }


def send_monthly_report(user_id, year, month):
    """Generate and send monthly expense report email"""
    try:
        # Generate report data
        report_data = generate_monthly_report_data(user_id, year, month)
        if not report_data:
            app.logger.error(f"Failed to generate report data for user {user_id}")
            return False
        
        # Create the email
        subject = f"Your Monthly Expense Report for {report_data['month_name']} {report_data['year']}"
        
        # Render the email templates
        html_content = render_template('email/monthly_report.html', **report_data)
        text_content = render_template('email/monthly_report.txt', **report_data)
        
        # Send the email
        msg = Message(
            subject=subject,
            recipients=[report_data['user'].id],
            body=text_content,
            html=html_content
        )
        
        mail.send(msg)
        app.logger.info(f"Monthly report sent to {report_data['user'].id} for {report_data['month_name']} {report_data['year']}")
        return True
        
    except Exception as e:
        app.logger.error(f"Error sending monthly report: {str(e)}", exc_info=True)
        return False

@app.route('/generate_monthly_report', methods=['GET', 'POST'])
@login_required_dev
def generate_monthly_report():
    """Generate and send a monthly expense report for the current user"""
    if request.method == 'POST':
 
        try:
            report_date = datetime.strptime(request.form.get('report_month', ''), '%Y-%m')
            report_year = report_date.year
            report_month = report_date.month
        except ValueError:
            # Default to previous month if invalid input
            today = datetime.now()
            if today.month == 1:
                report_month = 12
                report_year = today.year - 1
            else:
                report_month = today.month - 1
                report_year = today.year
        
        # Generate and send the report
        success = send_monthly_report(current_user.id, report_year, report_month)
        
        if success:
            flash('Monthly report has been sent to your email.')
        else:
            flash('Error generating monthly report. Please try again later.')
    
    # For GET request, show the form
    # Get the last 12 months for selection
    months = []
    today = datetime.now()
    for i in range(12):
        if today.month - i <= 0:
            month = today.month - i + 12
            year = today.year - 1
        else:
            month = today.month - i
            year = today.year
        
        month_name = calendar.month_name[month]
        months.append({
            'value': f"{year}-{month:02d}",
            'label': f"{month_name} {year}"
        })
    
    return render_template('generate_report.html', months=months)


def send_automatic_monthly_reports():
    """Send monthly reports to all users who have opted in"""
    with app.app_context():
        # Get the previous month
        today = datetime.now()
        if today.month == 1:
            report_month = 12
            report_year = today.year - 1
        else:
            report_month = today.month - 1
            report_year = today.year
        
        # Get users who have opted in (you'd need to add this field to User model)
        # For now, we'll assume all users want reports
        users = User.query.all()
        
        app.logger.info(f"Starting to send monthly reports for {calendar.month_name[report_month]} {report_year}")
        
        success_count = 0
        for user in users:
            if send_monthly_report(user.id, report_year, report_month):
                success_count += 1
        
        app.logger.info(f"Sent {success_count}/{len(users)} monthly reports")

#--------------------
# # statss
#--------------------
@app.route('/stats')
@login_required_dev
def stats():
    """Display financial statistics and visualizations that are user-centric"""
    # Get filter parameters from request
    base_currency = get_base_currency()
    start_date_str = request.args.get('startDate', None)
    end_date_str = request.args.get('endDate', None)
    group_id = request.args.get('groupId', 'all')
    chart_type = request.args.get('chartType', 'all')
    is_comparison = request.args.get('compare', 'false') == 'true'

    if is_comparison:
        return handle_comparison_request()
    
    # Parse dates or use defaults (last 6 months)
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            # Default to 6 months ago
            start_date = datetime.now() - timedelta(days=180)
            
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            end_date = datetime.now()
    except ValueError:
        # If date parsing fails, use default range
        start_date = datetime.now() - timedelta(days=180)
        end_date = datetime.now()
    
    # Build the filter query - only expenses where user is involved
    query_filters = [
        or_(
            Expense.user_id == current_user.id,
            Expense.split_with.like(f'%{current_user.id}%')
        ),
        Expense.date >= start_date,
        Expense.date <= end_date
    ]
    
    # Add group filter if specified
    if group_id != 'all':
        if group_id == 'none':
            query_filters.append(Expense.group_id.is_(None))
        else:
            query_filters.append(Expense.group_id == group_id)
    
    # Execute the query with all filters
    expenses = Expense.query.filter(and_(*query_filters)).order_by(Expense.date.desc()).all()
    
    # Get all settlements in the date range
    settlement_filters = [
        or_(
            Settlement.payer_id == current_user.id,
            Settlement.receiver_id == current_user.id
        ),
        Settlement.date >= start_date,
        Settlement.date <= end_date
    ]
    settlements = Settlement.query.filter(and_(*settlement_filters)).order_by(Settlement.date).all()
    
    # USER-CENTRIC: Calculate only the current user's expenses
    current_user_expenses = []
    total_user_expenses = 0
    
    # Initialize monthly data structures BEFORE the loop
    monthly_spending = {}
    monthly_income = {}  # New dictionary to track income
    monthly_labels = []
    monthly_amounts = []
    monthly_income_amounts = []  # New array for chart

    # Initialize all months in range
    current_date = start_date.replace(day=1)
    while current_date <= end_date:
        month_key = current_date.strftime('%Y-%m')
        month_label = current_date.strftime('%b %Y')
        monthly_labels.append(month_label)
        monthly_spending[month_key] = 0
        monthly_income[month_key] = 0  # Initialize income for this month
        
        # Advance to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    for expense in expenses:
        # Calculate splits for this expense
        splits = expense.calculate_splits()
        
        # Create a record of the user's portion only
        user_portion = 0
        
        if expense.paid_by == current_user.id:
            # If current user paid, include their own portion
            user_portion = splits['payer']['amount']
        else:
            # If someone else paid, find current user's portion from splits
            for split in splits['splits']:
                if split['email'] == current_user.id:
                    user_portion = split['amount']
                    break
        
        # Only add to list if user has a portion
        if user_portion > 0:
            expense_data = {
                'id': expense.id,
                'description': expense.description,
                'date': expense.date,
                'total_amount': expense.amount,
                'user_portion': user_portion,
                'paid_by': expense.paid_by,
                'paid_by_name': expense.user.name,
                'card_used': expense.card_used,
                'group_id': expense.group_id,
                'group_name': expense.group.name if expense.group else None
            }
            
            if hasattr(expense, 'transaction_type'):
                expense_data['transaction_type'] = expense.transaction_type
            else:
                # Default to 'expense' for backward compatibility
                expense_data['transaction_type'] = 'expense'
            
            # Format amounts based on transaction type
            if expense_data['transaction_type'] == 'income':
                expense_data['formatted_amount'] = f"+{base_currency['symbol']}{expense_data['user_portion']:.2f}"
                expense_data['amount_color'] = '#10b981'  # Green
            elif expense_data['transaction_type'] == 'transfer':
                expense_data['formatted_amount'] = f"{base_currency['symbol']}{expense_data['user_portion']:.2f}"
                expense_data['amount_color'] = '#a855f7'  # Purple
            else:  # Expense (default)
                expense_data['formatted_amount'] = f"-{base_currency['symbol']}{expense_data['user_portion']:.2f}"
                expense_data['amount_color'] = '#ef4444'  # Red

            # Add category information for the expense
            if hasattr(expense, 'category_id') and expense.category_id:
                category = Category.query.get(expense.category_id)
                if category:
                    expense_data['category_name'] = category.name
                    expense_data['category_icon'] = category.icon
                    expense_data['category_color'] = category.color
            else:
                expense_data['category_name'] = None
                expense_data['category_icon'] = 'fa-tag'
                expense_data['category_color'] = '#6c757d'
            
            current_user_expenses.append(expense_data)
            
            # Add to user's total
            total_user_expenses += user_portion

            # Add to monthly spending or income based on transaction type
            month_key = expense_data['date'].strftime('%Y-%m')
            if month_key in monthly_spending:
                # Separate income and expense transactions
                if expense_data.get('transaction_type') == 'income':
                    monthly_income[month_key] += expense_data['user_portion']
                else:  # 'expense' or 'transfer' or None (legacy expenses)
                    monthly_spending[month_key] += expense_data['user_portion']

    # Prepare chart data in correct order
    for month_key in sorted(monthly_spending.keys()):
        monthly_amounts.append(monthly_spending[month_key])
        monthly_income_amounts.append(monthly_income[month_key])
            
    # Calculate spending trend compared to previous period
    previous_period_start = start_date - (end_date - start_date)
    previous_period_filters = [
        or_(
            Expense.user_id == current_user.id,
            Expense.split_with.like(f'%{current_user.id}%')
        ),
        Expense.date >= previous_period_start,
        Expense.date < start_date
    ]
    
    # Initialize previous_total before querying
    previous_total = 0
    
    previous_expenses = Expense.query.filter(and_(*previous_period_filters)).all()
    
    # Process previous expenses and calculate total
    for expense in previous_expenses:
        splits = expense.calculate_splits()
        user_portion = 0
        
        if expense.paid_by == current_user.id:
            user_portion = splits['payer']['amount']
        else:
            for split in splits['splits']:
                if split['email'] == current_user.id:
                    user_portion = split['amount']
                    break
        
        previous_total += user_portion
    
    # Then calculate spending trend
    if previous_total > 0:
        spending_trend = ((total_user_expenses - previous_total) / previous_total) * 100
    else:
        spending_trend = 0
    
    # Calculate net balance (from balances function)
    balances = calculate_balances(current_user.id)
    net_balance = sum(balance['amount'] for balance in balances)
    balance_count = len(balances)
    
    # Find largest expense for current user (based on their portion)
    largest_expense = {"amount": 0, "description": "None"}
    if current_user_expenses:
        largest = max(current_user_expenses, key=lambda x: x['user_portion'])
        largest_expense = {"amount": largest['user_portion'], "description": largest['description']}
    
    # Calculate monthly average (current user's spending)
    month_count = len([amt for amt in monthly_amounts if amt > 0])
    if month_count > 0:
        monthly_average = total_user_expenses / month_count
    else:
        monthly_average = 0
    
    # Payment methods (cards used) - only count cards the current user used
    payment_methods = []
    payment_amounts = []
    cards_total = {}
    
    for expense_data in current_user_expenses:
        # Only include in payment methods if current user paid
        if expense_data['paid_by'] == current_user.id:
            card = expense_data['card_used']
            if card not in cards_total:
                cards_total[card] = 0
            cards_total[card] += expense_data['user_portion']
    
    # Sort by amount, descending
    for card, amount in sorted(cards_total.items(), key=lambda x: x[1], reverse=True)[:8]:  # Limit to top 8
        payment_methods.append(card)
        payment_amounts.append(amount)
    
    # Expense categories based on first word of description (only user's portion)
    categories = {}
    for expense_data in current_user_expenses:
        # Get first word of description as category
        category = expense_data['description'].split()[0] if expense_data['description'] else "Other"
        if category not in categories:
            categories[category] = 0
        categories[category] += expense_data['user_portion']
    
    # Get top 6 categories
    expense_categories = []
    category_amounts = []
    
    for category, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:6]:
        expense_categories.append(category)
        category_amounts.append(amount)
    
    # Balance history chart data
    # For user-centric approach, we'll calculate net balance over time
    balance_labels = monthly_labels
    
    # Chronologically organize expenses and settlements
    chronological_items = []
    
    for expense in expenses:
        splits = expense.calculate_splits()
        
        # If current user paid
        if expense.paid_by == current_user.id:
            # Add what others owe to current user
            for split in splits['splits']:
                amount = split['amount']
                chronological_items.append({
                    'date': expense.date,
                    'amount': amount,  # Positive: others owe current user
                    'type': 'expense'
                })
        # If current user owes
        elif current_user.id in [split['email'] for split in splits['splits']]:
            # Find current user's portion
            user_split = next((split['amount'] for split in splits['splits'] if split['email'] == current_user.id), 0)
            chronological_items.append({
                'date': expense.date,
                'amount': -user_split,  # Negative: current user owes others
                'type': 'expense'
            })
    
    # Add settlements
    for settlement in settlements:
        if settlement.payer_id == current_user.id:
            # User paid money to someone else (decreases balance)
            chronological_items.append({
                'date': settlement.date,
                'amount': -settlement.amount,
                'type': 'settlement'
            })
        else:
            # User received money (increases balance)
            chronological_items.append({
                'date': settlement.date,
                'amount': settlement.amount,
                'type': 'settlement'
            })
    
    # Sort all items chronologically
    chronological_items.sort(key=lambda x: x['date'])
    
    # Calculate running balance at each month boundary
    balance_amounts = []
    running_balance = 0
    
    # Converting month labels to datetime objects for comparison
    month_dates = [datetime.strptime(f"{label} 01", "%b %Y %d") for label in monthly_labels]
   
    # Create a copy for processing
    items_to_process = chronological_items.copy()
    for month_date in month_dates:
        while items_to_process and items_to_process[0]['date'] < month_date:
            item = items_to_process.pop(0)
            running_balance += item['amount']
        
        balance_amounts.append(running_balance)
    
    # Group comparison data - only count user's portion of expenses
    group_names = ["Personal"]
    group_totals = [0]
    
    # Personal expenses (no group)
    for expense_data in current_user_expenses:
        if expense_data['group_id'] is None:
            group_totals[0] += expense_data['user_portion']
    
    # Add each group's total for current user
    groups = Group.query.join(group_users).filter(group_users.c.user_id == current_user.id).all()
    
    for group in groups:
        group_total = 0
        for expense_data in current_user_expenses:
            if expense_data['group_id'] == group.id:
                group_total += expense_data['user_portion']
        
        group_names.append(group.name)
        group_totals.append(group_total)
    
    # Top expenses for the table - show user's portion
    top_expenses = sorted(current_user_expenses, key=lambda x: x['date'], reverse=True)[:10]

    user_categories = {}
    
    # Try to get all user categories
    try:
        for category in Category.query.filter_by(user_id=current_user.id).all():
            if not category.parent_id:  # Only top-level categories
                user_categories[category.id] = {
                    'name': category.name,
                    'total': 0,
                    'color': category.color,
                    'monthly': {month_key: 0 for month_key in sorted(monthly_spending.keys())}
                }
                
        # Add uncategorized as a fallback
        uncategorized_id = 0
        user_categories[uncategorized_id] = {
            'name': 'Uncategorized',
            'total': 0,
            'color': '#6c757d',
            'monthly': {month_key: 0 for month_key in sorted(monthly_spending.keys())}
        }
        
        # Calculate totals per actual category and monthly trends
        for expense_data in current_user_expenses:
            # Get category ID, default to uncategorized
            cat_id = uncategorized_id
            
            # DEBUGGING: Check the actual structure of expense_data
            app.logger.info(f"Processing expense: {expense_data['id']} - {expense_data['description']}")
            
            # Fetch the actual expense object
            expense_obj = Expense.query.get(expense_data['id'])
            
            if expense_obj and hasattr(expense_obj, 'category_id') and expense_obj.category_id:
                cat_id = expense_obj.category_id
                app.logger.info(f"Found category_id: {cat_id}")
                
                # If it's a subcategory, use parent category ID instead
                category = Category.query.get(cat_id)
                if category and category.parent_id and category.parent_id in user_categories:
                    cat_id = category.parent_id
                    app.logger.info(f"Using parent category: {cat_id}")
            
            # Only process if we have this category
            if cat_id in user_categories:
                # Add to total
                user_categories[cat_id]['total'] += expense_data['user_portion']
                
                # Add to monthly data
                month_key = expense_data['date'].strftime('%Y-%m')
                if month_key in user_categories[cat_id]['monthly']:
                    user_categories[cat_id]['monthly'][month_key] += expense_data['user_portion']
            else:
                app.logger.warning(f"Category ID {cat_id} not found in user_categories")
    except Exception as e:
        # Log the full error for debugging
        app.logger.error(f"Error getting category data: {str(e)}", exc_info=True)
        user_categories = {
            1: {'name': 'Food', 'total': 350, 'color': '#ec4899'},
            2: {'name': 'Housing', 'total': 1200, 'color': '#8b5cf6'},
            3: {'name': 'Transport', 'total': 250, 'color': '#3b82f6'},
            4: {'name': 'Entertainment', 'total': 180, 'color': '#10b981'},
            5: {'name': 'Shopping', 'total': 320, 'color': '#f97316'},
            0: {'name': 'Others', 'total': 150, 'color': '#6c757d'}
        }
    
    # Prepare category data for charts - sort by amount
    sorted_categories = sorted(user_categories.items(), key=lambda x: x[1]['total'], reverse=True)
    
    app.logger.info(f"Sorted categories: {[cat[1]['name'] for cat in sorted_categories]}")
    
    # Category data for pie chart
    category_names = [cat_data['name'] for _, cat_data in sorted_categories[:8]]  # Top 8
    category_totals = [cat_data['total'] for _, cat_data in sorted_categories[:8]]
    
    app.logger.info(f"Category names: {category_names}")
    app.logger.info(f"Category totals: {category_totals}")
    
    # Category trend data for line chart
    category_trend_data = []
    for cat_id, cat_data in sorted_categories[:4]:  # Top 4 for trend 
        if 'monthly' in cat_data:
            monthly_data = []
            for month_key in sorted(cat_data['monthly'].keys()):
                monthly_data.append(cat_data['monthly'][month_key])
                
            category_trend_data.append({
                'name': cat_data['name'],
                'color': cat_data['color'],
                'data': monthly_data
            })
        else:
            # Fallback if monthly data isn't available
            category_trend_data.append({
                'name': cat_data['name'],
                'color': cat_data['color'],
                'data': [cat_data['total'] / len(monthly_labels)] * len(monthly_labels)
            })
    
    app.logger.info(f"Category trend data: {category_trend_data}")
    
    # NEW CODE FOR TAG ANALYSIS
    # -------------------------
    tag_data = {}
    
    # Try to get tag information
    try:
        for expense_data in current_user_expenses:
            expense_obj = Expense.query.get(expense_data['id'])
            if expense_obj and hasattr(expense_obj, 'tags'):
                for tag in expense_obj.tags:
                    if tag.id not in tag_data:
                        tag_data[tag.id] = {
                            'name': tag.name,
                            'total': 0,
                            'color': tag.color
                        }
                    tag_data[tag.id]['total'] += expense_data['user_portion']
    except Exception as e:
        # Fallback for tags in case of error
        app.logger.error(f"Error getting tag data: {str(e)}", exc_info=True)
        tag_data = {
            1: {'name': 'Groceries', 'total': 280, 'color': '#f43f5e'},
            2: {'name': 'Dining', 'total': 320, 'color': '#fb7185'},
            3: {'name': 'Bills', 'total': 150, 'color': '#f97316'},
            4: {'name': 'Rent', 'total': 950, 'color': '#fb923c'},
            5: {'name': 'Gas', 'total': 120, 'color': '#f59e0b'},
            6: {'name': 'Coffee', 'total': 75, 'color': '#fbbf24'}
        }
    
    # Sort and prepare tag data
    sorted_tags = sorted(tag_data.items(), key=lambda x: x[1]['total'], reverse=True)[:6]  # Top 6
    
    tag_names = [tag_data['name'] for _, tag_data in sorted_tags]
    tag_totals = [tag_data['total'] for _, tag_data in sorted_tags]
    tag_colors = [tag_data['color'] for _, tag_data in sorted_tags]
    
    app.logger.info(f"Tag names: {tag_names}")
    app.logger.info(f"Tag totals: {tag_totals}")
    
    # Calculate totals for each transaction type
    total_expenses_only = 0
    total_income = 0
    total_transfers = 0
    
    for expense in expenses:
        if hasattr(expense, 'transaction_type'):
            if expense.transaction_type == 'expense' or expense.transaction_type is None:
                total_expenses_only += expense.amount
            elif expense.transaction_type == 'income':
                total_income += expense.amount
            elif expense.transaction_type == 'transfer':
                total_transfers += expense.amount
        else:
            # For backward compatibility, treat as expense if no transaction_type
            total_expenses_only += expense.amount
    
    # Calculate derived metrics
    net_cash_flow = total_income - total_expenses_only
    
    # Calculate savings rate if income is not zero
    if total_income > 0:
        savings_rate = (net_cash_flow / total_income) * 100
    else:
        savings_rate = 0
    
    # Calculate expense to income ratio
    if total_income > 0:
        expense_income_ratio = (total_expenses_only / total_income) * 100
    else:
        expense_income_ratio = 100  # Default to 100% if no income
    
    # Provide placeholder values for other metrics
    income_trend = 5.2  # Example value
    liquidity_ratio = 3.5  # Example value
    account_growth = 7.8  # Example value

    user_accounts = Account.query.filter_by(user_id=current_user.id).all()

    return render_template('stats.html',
                           user_accounts=user_accounts,
                          expenses=expenses,
                          total_expenses=total_user_expenses,  # User's spending only
                          spending_trend=spending_trend,
                          net_balance=net_balance,
                          balance_count=balance_count,
                          monthly_average=monthly_average,
                          monthly_income=monthly_income_amounts,
                          month_count=month_count,
                          largest_expense=largest_expense,
                          monthly_labels=monthly_labels,
                          monthly_amounts=monthly_amounts,
                          payment_methods=payment_methods,
                          payment_amounts=payment_amounts,
                          expense_categories=expense_categories,
                          category_amounts=category_amounts,
                          balance_labels=balance_labels,
                          balance_amounts=balance_amounts,
                          group_names=group_names,
                          group_totals=group_totals,
                          base_currency=base_currency,
                          top_expenses=top_expenses,
                          total_expenses_only=total_expenses_only,  # New: For expenses only
                          total_income=total_income,
                          total_transfers=total_transfers,
                          income_trend=income_trend,
                          net_cash_flow=net_cash_flow,
                          savings_rate=savings_rate,
                          expense_income_ratio=expense_income_ratio,
                          liquidity_ratio=liquidity_ratio,
                          account_growth=account_growth,
                          # New data for enhanced charts
                          category_names=category_names,
                          category_totals=category_totals,
                          category_trend_data=category_trend_data,
                          tag_names=tag_names,
                          tag_totals=tag_totals,
                          tag_colors=tag_colors)

def handle_comparison_request():
    """Handle time frame comparison requests within the stats route"""
    # Get parameters from request
    primary_start = request.args.get('primaryStart')
    primary_end = request.args.get('primaryEnd')
    comparison_start = request.args.get('comparisonStart')
    comparison_end = request.args.get('comparisonEnd')
    metric = request.args.get('metric', 'spending')
    
    # Convert string dates to datetime objects
    try:
        primary_start_date = datetime.strptime(primary_start, '%Y-%m-%d')
        primary_end_date = datetime.strptime(primary_end, '%Y-%m-%d')
        comparison_start_date = datetime.strptime(comparison_start, '%Y-%m-%d')
        comparison_end_date = datetime.strptime(comparison_end, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Initialize response data structure
    result = {
        'primary': {
            'totalSpending': 0,
            'transactionCount': 0,
            'topCategory': 'None',
            'dailyAmounts': []  # Make sure this is initialized
        },
        'comparison': {
            'totalSpending': 0,
            'transactionCount': 0,
            'topCategory': 'None',
            'dailyAmounts': []  # Make sure this is initialized
        },
        'dateLabels': []  # Initialize date labels
    }
    
    # Get expenses for both periods - reuse your existing query logic
    primary_query_filters = [
        or_(
            Expense.user_id == current_user.id,
            Expense.split_with.like(f'%{current_user.id}%')
        ),
        Expense.date >= primary_start_date,
        Expense.date <= primary_end_date
    ]
    primary_expenses_raw = Expense.query.filter(and_(*primary_query_filters)).order_by(Expense.date).all()
    
    comparison_query_filters = [
        or_(
            Expense.user_id == current_user.id,
            Expense.split_with.like(f'%{current_user.id}%')
        ),
        Expense.date >= comparison_start_date,
        Expense.date <= comparison_end_date
    ]
    comparison_expenses_raw = Expense.query.filter(and_(*comparison_query_filters)).order_by(Expense.date).all()
    
    # Process expenses to get user's portion
    primary_expenses = []
    comparison_expenses = []
    primary_total = 0
    comparison_total = 0
    
    # Process primary period expenses
    for expense in primary_expenses_raw:
        splits = expense.calculate_splits()
        user_portion = 0
        
        if expense.paid_by == current_user.id:
            user_portion = splits['payer']['amount']
        else:
            for split in splits['splits']:
                if split['email'] == current_user.id:
                    user_portion = split['amount']
                    break
        
        if user_portion > 0:
            expense_data = {
                'id': expense.id,
                'description': expense.description,
                'date': expense.date,
                'total_amount': expense.amount,
                'user_portion': user_portion,
                'paid_by': expense.paid_by,
                'category_name': get_category_name(expense)
            }
            primary_expenses.append(expense_data)
            primary_total += user_portion
    
    # Process comparison period expenses
    for expense in comparison_expenses_raw:
        splits = expense.calculate_splits()
        user_portion = 0
        
        if expense.paid_by == current_user.id:
            user_portion = splits['payer']['amount']
        else:
            for split in splits['splits']:
                if split['email'] == current_user.id:
                    user_portion = split['amount']
                    break
        
        if user_portion > 0:
            expense_data = {
                'id': expense.id,
                'description': expense.description,
                'date': expense.date,
                'total_amount': expense.amount,
                'user_portion': user_portion,
                'paid_by': expense.paid_by,
                'category_name': get_category_name(expense)
            }
            comparison_expenses.append(expense_data)
            comparison_total += user_portion
    
    # Update basic metrics
    result['primary']['totalSpending'] = primary_total
    result['primary']['transactionCount'] = len(primary_expenses)
    result['comparison']['totalSpending'] = comparison_total
    result['comparison']['transactionCount'] = len(comparison_expenses)
    
    # Process data based on the selected metric
    if metric == 'spending':
        # Calculate daily spending for each period
        primary_daily = process_daily_spending(primary_expenses, primary_start_date, primary_end_date)
        comparison_daily = process_daily_spending(comparison_expenses, comparison_start_date, comparison_end_date)
        
        # Normalize to 10 data points for consistent display
        result['primary']['dailyAmounts'] = normalize_time_series(primary_daily, 10)
        result['comparison']['dailyAmounts'] = normalize_time_series(comparison_daily, 10)
        result['dateLabels'] = [f'Day {i+1}' for i in range(10)]
        
        # Debugging - log the daily spending data
        app.logger.info(f"Primary daily amounts: {result['primary']['dailyAmounts']}")
        app.logger.info(f"Comparison daily amounts: {result['comparison']['dailyAmounts']}")
        
    elif metric == 'categories':
        # Get category spending for both periods
        primary_categories = {}
        comparison_categories = {}
        
        # Process primary period categories
        for expense in primary_expenses:
            category = expense['category_name'] or 'Uncategorized'
            if category not in primary_categories:
                primary_categories[category] = 0
            primary_categories[category] += expense['user_portion']
            
        # Process comparison period categories
        for expense in comparison_expenses:
            category = expense['category_name'] or 'Uncategorized'
            if category not in comparison_categories:
                comparison_categories[category] = 0
            comparison_categories[category] += expense['user_portion']
        
        # Get top categories across both periods
        all_categories = set(list(primary_categories.keys()) + list(comparison_categories.keys()))
        top_categories = sorted(
            all_categories,
            key=lambda c: (primary_categories.get(c, 0) + comparison_categories.get(c, 0)),
            reverse=True
        )[:5]
        
        result['categoryLabels'] = top_categories
        result['primary']['categoryAmounts'] = [primary_categories.get(cat, 0) for cat in top_categories]
        result['comparison']['categoryAmounts'] = [comparison_categories.get(cat, 0) for cat in top_categories]
        
        # Set top category
        result['primary']['topCategory'] = max(primary_categories.items(), key=lambda x: x[1])[0] if primary_categories else 'None'
        result['comparison']['topCategory'] = max(comparison_categories.items(), key=lambda x: x[1])[0] if comparison_categories else 'None'
        
    elif metric == 'tags':
        # Similar logic for tags - adapt based on your data model
        primary_tags = {}
        comparison_tags = {}
        
        # For primary period
        for expense in primary_expenses:
            # Get tags for this expense - adapt to your model
            expense_obj = Expense.query.get(expense['id'])
            if expense_obj and hasattr(expense_obj, 'tags'):
                for tag in expense_obj.tags:
                    if tag.name not in primary_tags:
                        primary_tags[tag.name] = 0
                    primary_tags[tag.name] += expense['user_portion']
        
        # For comparison period
        for expense in comparison_expenses:
            expense_obj = Expense.query.get(expense['id'])
            if expense_obj and hasattr(expense_obj, 'tags'):
                for tag in expense_obj.tags:
                    if tag.name not in comparison_tags:
                        comparison_tags[tag.name] = 0
                    comparison_tags[tag.name] += expense['user_portion']
        
        # Get top tags
        all_tags = set(list(primary_tags.keys()) + list(comparison_tags.keys()))
        top_tags = sorted(
            all_tags,
            key=lambda t: (primary_tags.get(t, 0) + comparison_tags.get(t, 0)),
            reverse=True
        )[:5]
        
        result['tagLabels'] = top_tags
        result['primary']['tagAmounts'] = [primary_tags.get(tag, 0) for tag in top_tags]
        result['comparison']['tagAmounts'] = [comparison_tags.get(tag, 0) for tag in top_tags]
        
    elif metric == 'payment':
        # Payment method comparison
        primary_payment = {}
        comparison_payment = {}
        
        # For primary period - only count what the user paid directly
        for expense in primary_expenses:
            if expense['paid_by'] == current_user.id:
                # Get the payment method (assuming it's stored as card_used)
                expense_obj = Expense.query.get(expense['id'])
                if expense_obj and hasattr(expense_obj, 'card_used'):
                    card = expense_obj.card_used
                    if card not in primary_payment:
                        primary_payment[card] = 0
                    primary_payment[card] += expense['user_portion']
        
        # For comparison period
        for expense in comparison_expenses:
            if expense['paid_by'] == current_user.id:
                expense_obj = Expense.query.get(expense['id'])
                if expense_obj and hasattr(expense_obj, 'card_used'):
                    card = expense_obj.card_used
                    if card not in comparison_payment:
                        comparison_payment[card] = 0
                    comparison_payment[card] += expense['user_portion']
        
        # Combine payment methods
        all_methods = set(list(primary_payment.keys()) + list(comparison_payment.keys()))
        
        result['paymentLabels'] = list(all_methods)
        result['primary']['paymentAmounts'] = [primary_payment.get(method, 0) for method in all_methods]
        result['comparison']['paymentAmounts'] = [comparison_payment.get(method, 0) for method in all_methods]
    
    return jsonify(result)

# Helper functions for the comparison feature

def process_daily_spending(expenses, start_date, end_date):
    """Process expenses into daily totals"""
    # Calculate number of days in period
    days = (end_date - start_date).days + 1
    daily_spending = [0] * days
    
    for expense in expenses:
        # Calculate day index
        day_index = (expense['date'] - start_date).days
        if 0 <= day_index < days:
            daily_spending[day_index] += expense['user_portion']
    
    return daily_spending

def normalize_time_series(data, target_length):
    """Normalize a time series to a target length for better comparison"""
    if len(data) == 0:
        return [0] * target_length
    
    if len(data) == target_length:
        return data
    
    # Use resampling to normalize the data
    result = []
    ratio = len(data) / target_length
    
    for i in range(target_length):
        start_idx = int(i * ratio)
        end_idx = int((i + 1) * ratio)
        if end_idx > len(data):
            end_idx = len(data)
        
        if start_idx == end_idx:
            segment_avg = data[start_idx] if start_idx < len(data) else 0
        else:
            segment_avg = sum(data[start_idx:end_idx]) / (end_idx - start_idx)
        
        result.append(segment_avg)
    
    return result


def get_category_name(expense):
    """Helper function to get the category name for an expense"""
    if hasattr(expense, 'category_id') and expense.category_id:
        category = Category.query.get(expense.category_id)
        if category:
            return category.name
    return None


def process_daily_spending(expenses, start_date, end_date):
    """Process expenses into daily totals"""
    days = (end_date - start_date).days + 1
    daily_spending = [0] * days
    
    for expense in expenses:
        day_index = (expense['date'] - start_date).days
        if 0 <= day_index < days:
            daily_spending[day_index] += expense['user_portion']
    
    return daily_spending


def normalize_time_series(data, target_length):
    """Normalize a time series to a target length for better comparison"""
    if len(data) == 0:
        return [0] * target_length
    
    if len(data) == target_length:
        return data
    
    # Use resampling to normalize the data
    result = []
    ratio = len(data) / target_length
    
    for i in range(target_length):
        start_idx = int(i * ratio)
        end_idx = int((i + 1) * ratio)
        if end_idx > len(data):
            end_idx = len(data)
        
        if start_idx == end_idx:
            segment_avg = data[start_idx] if start_idx < len(data) else 0
        else:
            segment_avg = sum(data[start_idx:end_idx]) / (end_idx - start_idx)
        
        result.append(segment_avg)
    
    return result


#--------------------
# # Password reset routes
#--------------------


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(id=email).first()
        
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            
            # Generate the reset password URL
            reset_url = url_for('reset_password', token=token, email=email, _external=True)
            
            # Prepare the email
            subject = "Password Reset Request"
            body_text = f'''
                    To reset your password, please visit the following link:
                    {reset_url}

                    If you did not make this request, please ignore this email.

                    This link will expire in 1 hour.
                    '''
            body_html = f'''
                    <p>To reset your password, please click the link below:</p>
                    <p><a href="{reset_url}">Reset Your Password</a></p>
                    <p>If you did not make this request, please ignore this email.</p>
                    <p>This link will expire in 1 hour.</p>
                    '''
            
            try:
                msg = Message(
                    subject=subject,
                    recipients=[email],
                    body=body_text,
                    html=body_html
                )
                mail.send(msg)
                app.logger.info(f"Password reset email sent to {email}")
                
                # Success message (don't reveal if email exists or not for security)
                flash("If your email address exists in our database, you will receive a password reset link shortly.")
            except Exception as e:
                app.logger.error(f"Error sending password reset email: {str(e)}")
                flash("An error occurred while sending the password reset email. Please try again later.")
        else:
            # Still show success message even if email not found (security)
            flash("If your email address exists in our database, you will receive a password reset link shortly.")
            app.logger.info(f"Password reset requested for non-existent email: {email}")
        
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    email = request.args.get('email')
    if not email:
        flash('Invalid reset link.')
        return redirect(url_for('login'))
    
    user = User.query.filter_by(id=email).first()
    
    # Verify the token is valid
    if not user or not user.verify_reset_token(token):
        flash('Invalid or expired reset link. Please request a new one.')
        return redirect(url_for('reset_password_request'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template('reset_password_confirm.html', token=token, email=email)
        
        # Update the user's password
        user.set_password(password)
        user.clear_reset_token()
        db.session.commit()
        
        app.logger.info(f"Password reset successful for user: {email}")
        flash('Your password has been reset successfully. You can now log in with your new password.')
        return redirect(url_for('login'))
    
    return render_template('reset_password_confirm.html', token=token, email=email)





#--------------------
# DATABASE INITIALIZATION
#--------------------

# Database initialization at application startup
with app.app_context():
    try:
        print("Creating database tables...")
        db.create_all()
        extensions.init_db()
        #init_default_currencies()
        print("Tables created successfully")
        print(inspect(db.engine).get_table_names())
        print(db.engine)
        print(extensions.engine)
    except Exception as e:
        print(f"ERROR CREATING TABLES: {str(e)}")

# Register OIDC routes
if oidc_enabled:
    register_oidc_routes(app, User, db)        

if __name__ == '__main__':
    app.run(debug=True, port=5001)
