r"""29a41de6a866d56c36aba5159f45257c"""

import os
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    session,
)
from flask_login import (

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

from routes import register_blueprints
from services.wrappers import login_required_dev
from session_timeout import DemoTimeout

from models import Account, Budget, Category, CategoryMapping, CategorySplit, Currency, Expense, Group, RecurringExpense, Settlement, User

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
