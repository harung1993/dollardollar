import os
from dotenv import load_dotenv
from flask import Flask, render_template, send_file, request, jsonify, request, redirect, url_for, flash, session
import csv
import hashlib
import io
import re   
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import calendar
from functools import wraps
import logging
from sqlalchemy import func, or_, and_
import json
import secrets
from datetime import timedelta
from flask_mail import Mail, Message
from flask_migrate import Migrate
import ssl
import requests
import json
from sqlalchemy import inspect, text
from oidc_auth import setup_oidc_config, register_oidc_routes
from oidc_user import extend_user_model

os.environ['OPENSSL_LEGACY_PROVIDER'] = '1'

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass
#--------------------
# SETUP AND CONFIGURATION
#--------------------

# Load environment variables
load_dotenv()

# Development mode configuration
app = Flask(__name__)

# Configure from environment variables with sensible defaults
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret_key_change_in_production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///instance/expenses.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEVELOPMENT_MODE'] = os.getenv('DEVELOPMENT_MODE', 'True').lower() == 'true'
app.config['DISABLE_SIGNUPS'] = os.environ.get('DISABLE_SIGNUPS', 'False').lower() == 'true'  # Default to allowing signups
app.config['LOCAL_LOGIN_DISABLE'] = os.getenv('LOCAL_LOGIN_DISABLE', 'False').lower() == 'true' # Default to false to allow local logins



# Email configuration from environment variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))



mail = Mail(app)


# Logging configuration
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level))

# Development user credentials from environment
DEV_USER_EMAIL = os.getenv('DEV_USER_EMAIL', 'dev@example.com')
DEV_USER_PASSWORD = os.getenv('DEV_USER_PASSWORD', 'dev')

oidc_enabled = setup_oidc_config(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


migrate = Migrate(app, db)
#--------------------
# DATABASE MODELS
#--------------------

# Group-User Association Table
group_users = db.Table('group_users',
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id'), primary_key=True),
    db.Column('user_id', db.String(120), db.ForeignKey('users.id'), primary_key=True)
)

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    members = db.relationship('User', secondary=group_users, lazy='subquery',
        backref=db.backref('groups', lazy=True))
    expenses = db.relationship('Expense', backref='group', lazy=True)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(120), primary_key=True)  # Using email as ID
    password_hash = db.Column(db.String(256))
    name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    expenses = db.relationship('Expense', backref='user', lazy=True)
    default_currency_code = db.Column(db.String(3), db.ForeignKey('currencies.code'), nullable=True)
    default_currency = db.relationship('Currency', backref=db.backref('users', lazy=True))
    user_color = db.Column(db.String(7), default="#15803d")
    created_groups = db.relationship('Group', backref='creator', lazy=True,
        foreign_keys=[Group.created_by])

    # OIDC related fields
    oidc_id = db.Column(db.String(255), nullable=True, index=True, unique=True)
    oidc_provider = db.Column(db.String(50), nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)        

    def set_password(self, password):
        self.password_hash = generate_password_hash(password,method='pbkdf2:sha256')

    def check_password(self, password):
        try:
            return check_password_hash(self.password_hash, password)
        except ValueError:
            # Handle potential legacy or incompatible hash formats
            return False
        
    def generate_reset_token(self):
        """Generate a password reset token that expires in 1 hour"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        return self.reset_token
        
    def verify_reset_token(self, token):
        """Verify if the provided token is valid and not expired"""
        if not self.reset_token or self.reset_token != token:
            return False
        if not self.reset_token_expiry or self.reset_token_expiry < datetime.utcnow():
            return False
        return True
        
    def clear_reset_token(self):
        """Clear the reset token and expiry after use"""
        self.reset_token = None
        self.reset_token_expiry = None

# Extend User model with OIDC functionality if needed
if oidc_enabled:
    User = extend_user_model(db, User)       

class Settlement(db.Model):
    __tablename__ = 'settlements'
    id = db.Column(db.Integer, primary_key=True)
    payer_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(200), nullable=True, default="Settlement")
    
    # Relationships
    payer = db.relationship('User', foreign_keys=[payer_id], backref=db.backref('settlements_paid', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('settlements_received', lazy=True))
class Currency(db.Model):
    __tablename__ = 'currencies'
    code = db.Column(db.String(3), primary_key=True)  # ISO 4217 currency code (e.g., USD, EUR, GBP)
    name = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(5), nullable=False)
    rate_to_base = db.Column(db.Float, nullable=False, default=1.0)  # Exchange rate to base currency
    is_base = db.Column(db.Boolean, default=False)  # Whether this is the base currency
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"{self.code} ({self.symbol})"
    
expense_tags = db.Table('expense_tags',
    db.Column('expense_id', db.Integer, db.ForeignKey('expenses.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    card_used = db.Column(db.String(50), nullable=False)
    split_method = db.Column(db.String(20), nullable=False)  # 'equal', 'custom', 'percentage'
    split_value = db.Column(db.Float)  # deprecated - kept for backward compatibility
    paid_by = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    split_with = db.Column(db.String(500), nullable=True)  # Comma-separated list of user IDs
    split_details = db.Column(db.Text, nullable=True)  # JSON string storing custom split values for each user
    recurring_id = db.Column(db.Integer, db.ForeignKey('recurring_expenses.id'), nullable=True)
    tags = db.relationship('Tag', secondary=expense_tags, lazy='subquery', 
                   backref=db.backref('expenses', lazy=True))
    # Add these fields to your existing Expense class:
    currency_code = db.Column(db.String(3), db.ForeignKey('currencies.code'), nullable=True)
    original_amount = db.Column(db.Float, nullable=True)  # Amount in original currency
    currency = db.relationship('Currency', backref=db.backref('expenses', lazy=True))
    def calculate_splits(self):
    
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
                split_details = json.loads(self.split_details)
            except:
                split_details = {}
        
        if self.split_method == 'equal':
            # Count participants (include payer only if not already in splits)
            total_participants = len(split_users) + (1 if self.paid_by not in split_with_ids else 0)
            
            # Equal splits among all participants
            per_person = self.amount / total_participants if total_participants > 0 else 0
            per_person_original = original_amount / total_participants if total_participants > 0 else 0
            
            # Assign payer's portion (only if they're not already in the splits)
            if self.paid_by not in split_with_ids:
                result['payer']['amount'] = per_person
            else:
                result['payer']['amount'] = 0
            
            # Assign everyone else's portion
            for user in split_users:
                result['splits'].append({
                    'name': user['name'],
                    'email': user['email'],
                    'amount': per_person,
                    'original_amount': per_person_original,
                    'currency_code': self.currency_code
                })
                    
        elif self.split_method == 'percentage':
            # Use per-user percentages if available in split_details
            if split_details and split_details.get('type') == 'percentage':
                percentages = split_details.get('values', {})
                total_assigned = 0
                total_original_assigned = 0
                
                # Calculate payer's amount if specified
                payer_percent = float(percentages.get(self.paid_by, 0))
                payer_amount = (self.amount * payer_percent) / 100
                payer_original_amount = (original_amount * payer_percent) / 100
                
                result['payer']['amount'] = payer_amount if self.paid_by not in split_with_ids else 0
                total_assigned += payer_amount if self.paid_by not in split_with_ids else 0
                total_original_assigned += payer_original_amount if self.paid_by not in split_with_ids else 0
                
                # Calculate each user's portion based on their percentage
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
                
                # Validate total (handle rounding errors)
                if abs(total_assigned - self.amount) > 0.01:
                    difference = self.amount - total_assigned
                    if result['splits']:
                        result['splits'][-1]['amount'] += difference
                    elif result['payer']['amount'] > 0:
                        result['payer']['amount'] += difference
                
            else:
                # Backward compatibility mode
                payer_percentage = self.split_value if self.split_value is not None else 0
                payer_amount = (self.amount * payer_percentage) / 100
                payer_original_amount = (original_amount * payer_percentage) / 100
                
                result['payer']['amount'] = payer_amount if self.paid_by not in split_with_ids else 0
                
                # Split remainder equally
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
            # Use per-user custom amounts if available in split_details
            if split_details and split_details.get('type') == 'amount':
                amounts = split_details.get('values', {})
                total_assigned = 0
                total_original_assigned = 0
                
                # Set payer's amount if specified
                payer_amount = float(amounts.get(self.paid_by, 0))
                # For original amount, scale by the same proportion
                payer_ratio = payer_amount / self.amount if self.amount else 0
                payer_original_amount = original_amount * payer_ratio
                
                result['payer']['amount'] = payer_amount if self.paid_by not in split_with_ids else 0
                total_assigned += payer_amount if self.paid_by not in split_with_ids else 0
                
                # Set each user's amount
                for user in split_users:
                    user_amount = float(amounts.get(user['id'], 0))
                    # Scale original amount by same proportion
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
                
                # Validate total (handle rounding errors)
                if abs(total_assigned - self.amount) > 0.01:
                    difference = self.amount - total_assigned
                    if result['splits']:
                        result['splits'][-1]['amount'] += difference
                    elif result['payer']['amount'] > 0:
                        result['payer']['amount'] += difference
            else:
                # Backward compatibility mode
                payer_amount = self.split_value if self.split_value is not None else 0
                # Calculate the ratio of payer amount to total
                payer_ratio = payer_amount / self.amount if self.amount else 0
                payer_original_amount = original_amount * payer_ratio
                
                result['payer']['amount'] = payer_amount if self.paid_by not in split_with_ids else 0
                
                # Split remainder equally
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

class RecurringExpense(db.Model):
    __tablename__ = 'recurring_expenses'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    card_used = db.Column(db.String(50), nullable=False)
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
    
    # Relationships
    user = db.relationship('User', backref=db.backref('recurring_expenses', lazy=True))
    group = db.relationship('Group', backref=db.backref('recurring_expenses', lazy=True))
    expenses = db.relationship('Expense', backref=db.backref('recurring_source', lazy=True), 
                              foreign_keys='Expense.recurring_id')
    currency_code = db.Column(db.String(3), db.ForeignKey('currencies.code'), nullable=True)
    original_amount = db.Column(db.Float, nullable=True)  # Amount in original currency
    currency = db.relationship('Currency', backref=db.backref('recurring_expenses', lazy=True))
    
    def create_expense_instance(self, for_date=None):
        """Create a single expense instance from this recurring template"""
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
            recurring_id=self.id  # Link to this recurring expense
        )
        
        # Update the last created date
        self.last_created = for_date
        
        return expense
# Tag-Expense Association Table

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(20), default="#6c757d")  # Default color gray
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('tags', lazy=True))

class AppSettings(db.Model):
    __tablename__ = 'app_settings'
    id = db.Column(db.Integer, primary_key=True)
    app_title = db.Column(db.String(100), default="Dollar Dollar Bill Y'all")
    app_logo_url = db.Column(db.String(500), default="/static/images/dollar-logo.png")
    app_logo_emoji = db.Column(db.String(10), default="💵")
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.String(128))
    is_customized = db.Column(db.Boolean, default=False)
    
    @classmethod
    def get_settings(cls):
        """Get app settings or create default if not exists"""
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings
#--------------------
# AUTH AND UTILITIES
#--------------------

def login_required_dev(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.config['DEVELOPMENT_MODE']:
            if not current_user.is_authenticated:
                # Get or create dev user
                dev_user = User.query.filter_by(id=DEV_USER_EMAIL).first()
                if not dev_user:
                    dev_user = User(
                        id=DEV_USER_EMAIL,
                        name='Developer',
                        is_admin=True
                    )
                    dev_user.set_password(DEV_USER_PASSWORD)
                    db.session.add(dev_user)
                    db.session.commit()
                # Auto login dev user
                login_user(dev_user)
            return f(*args, **kwargs)
        # Normal authentication for non-dev mode - fixed implementation
        return login_required(f)(*args, **kwargs)
    return decorated_function

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
            print("Development user created:", DEV_USER_EMAIL)

def flash_message(message, category='success'):
    """
    Enhanced flash message with category support
    
    Args:
        message (str): The message to flash
        category (str): Message category ('success', 'error', 'warning', 'info')
    """
    from flask import flash
    flash(message, category)
#--------------------
# BUSINESS LOGIC FUNCTIONS
#--------------------
# Add this function to your app.py file
def update_currency_rates():
    """
    Update currency exchange rates using a public API
    Returns the number of currencies updated or -1 on error
    """
    try:
        # Get the base currency
        base_currency = Currency.query.filter_by(is_base=True).first()
        if not base_currency:
            app.logger.error("No base currency found. Cannot update rates.")
            return -1
            
        base_code = base_currency.code
        
        # Use ExchangeRate-API (free tier - https://www.exchangerate-api.com/)
        # Or you can use another free API like https://frankfurter.app/
        response = requests.get(f'https://api.frankfurter.app/latest?from={base_code}')
        
        if response.status_code != 200:
            app.logger.error(f"API request failed with status code {response.status_code}")
            return -1
        
        data = response.json()
        rates = data.get('rates', {})
        
        # Get all currencies except base
        currencies = Currency.query.filter(Currency.code != base_code).all()
        updated_count = 0
        
        # Update rates
        for currency in currencies:
            if currency.code in rates:
                currency.rate_to_base = 1 / rates[currency.code]  # Convert to base currency rate
                currency.last_updated = datetime.utcnow()
                updated_count += 1
            else:
                app.logger.warning(f"No rate found for {currency.code}")
        
        # Commit changes
        db.session.commit()
        app.logger.info(f"Updated {updated_count} currency rates")
        return updated_count
        
    except Exception as e:
        app.logger.error(f"Error updating currency rates: {str(e)}")
        return -1
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
    
    # Convert to base currency first, then to target currency
    amount_in_base = amount / from_currency.rate_to_base
    return amount_in_base * to_currency.rate_to_base
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

def send_welcome_email(user):
    """
    Send a welcome email to a newly registered user
    """
    try:
        subject = "Welcome to Dollar Dollar Bill Y'all!"
        
        # Create welcome email body
        body_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #15803d; color: white; padding: 10px 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
                .button {{ display: inline-block; background-color: #15803d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Dollar Dollar Bill Y'all!</h1>
                </div>
                <div class="content">
                    <h2>Hi {user.name},</h2>
                    <p>Thank you for joining our expense tracking app. We're excited to help you manage your finances effectively!</p>
                    
                    <h3>Getting Started:</h3>
                    <ol>
                        <li>Add your first expense from the dashboard</li>
                        <li>Create groups to share expenses with friends or family</li>
                        <li>Track your spending patterns in the stats section</li>
                    </ol>
                    
                    <p>If you have any questions or need assistance, please don't hesitate to contact us.</p>
                    
                    <a href="{request.host_url}" class="button">Go to Dashboard</a>
                </div>
                <div class="footer">
                    <p>This email was sent to {user.id}. If you didn't create this account, please ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Simple text version for clients that don't support HTML
        body_text = f"""
        Welcome to Dollar Dollar Bill Y'all!
        
        Hi {user.name},
        
        Thank you for joining our expense tracking app. We're excited to help you manage your finances effectively!
        
        Getting Started:
        1. Add your first expense from the dashboard
        2. Create groups to share expenses with friends or family
        3. Track your spending patterns in the stats section
        
        If you have any questions or need assistance, please don't hesitate to contact us.
        
        Visit: {request.host_url}
        
        This email was sent to {user.id}. If you didn't create this account, please ignore this email.
        """
        
        # Create and send the message
        msg = Message(
            subject=subject,
            recipients=[user.id],
            body=body_text,
            html=body_html
        )
        
        # Send the email
        mail.send(msg)
        
        app.logger.info(f"Welcome email sent to {user.id}")
        return True
        
    except Exception as e:
        app.logger.error(f"Error sending welcome email: {str(e)}")
        return False

def send_group_invitation_email(user, group, inviter):
    """
    Send an email notification when a user is added to a group
    """
    try:
        subject = f"You've been added to {group.name} on Dollar Dollar Bill Y'all"
        
        # Create invitation email body
        body_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #15803d; color: white; padding: 10px 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
                .button {{ display: inline-block; background-color: #15803d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Group Invitation</h1>
                </div>
                <div class="content">
                    <h2>Hi {user.name},</h2>
                    <p>You have been added to the group <strong>"{group.name}"</strong> by {inviter.name}.</p>
                    
                    <h3>Group Details:</h3>
                    <ul>
                        <li><strong>Group Name:</strong> {group.name}</li>
                        <li><strong>Description:</strong> {group.description or 'No description provided'}</li>
                        <li><strong>Created by:</strong> {group.creator.name}</li>
                        <li><strong>Members:</strong> {', '.join([member.name for member in group.members])}</li>
                    </ul>
                    
                    <p>You can now track and split expenses with other members of this group.</p>
                    
                    <a href="{request.host_url}groups/{group.id}" class="button">View Group</a>
                </div>
                <div class="footer">
                    <p>This email was sent to {user.id}. If you believe this was a mistake, please contact the group creator.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Simple text version for clients that don't support HTML
        body_text = f"""
        Group Invitation - Dollar Dollar Bill Y'all
        
        Hi {user.name},
        
        You have been added to the group "{group.name}" by {inviter.name}.
        
        Group Details:
        - Group Name: {group.name}
        - Description: {group.description or 'No description provided'}
        - Created by: {group.creator.name}
        - Members: {', '.join([member.name for member in group.members])}
        
        You can now track and split expenses with other members of this group.
        
        View Group: {request.host_url}groups/{group.id}
        
        This email was sent to {user.id}. If you believe this was a mistake, please contact the group creator.
        """
        
        # Create and send the message
        msg = Message(
            subject=subject,
            recipients=[user.id],
            body=body_text,
            html=body_html
        )
        
        # Send the email
        mail.send(msg)
        
        app.logger.info(f"Group invitation email sent to {user.id} for group {group.name}")
        return True
        
    except Exception as e:
        app.logger.error(f"Error sending group invitation email: {str(e)}")
        return False
    

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
            
        # Check AppSettings model for is_customized column
        if inspector.has_table('app_settings'):
            app_settings_columns = [col['name'] for col in inspector.get_columns('app_settings')]
            if 'is_customized' not in app_settings_columns:
                app.logger.warning("Missing is_customized column in app_settings table - adding it now")
                db.session.execute(text('ALTER TABLE app_settings ADD COLUMN is_customized BOOLEAN DEFAULT FALSE'))
                db.session.commit()
                app.logger.info("Added is_customized column to app_settings table")
            
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

    return {
        'get_user_color': get_user_color,
        'get_user_by_id': get_user_by_id
    }
    
# Add this near your other app context processors

@app.context_processor
def inject_settings():
    def get_app_settings():
        return AppSettings.get_settings()
    return dict(get_app_settings=get_app_settings)

@app.route('/get_transaction_details/<other_user_id>')
@login_required_dev
def get_transaction_details(other_user_id):
    """
    Fetch transaction details (expenses and settlements) between current user and another user
    """
    # Query expenses involving both users
    expenses = Expense.query.filter(
        or_(
            and_(
                Expense.user_id == current_user.id, 
                Expense.split_with.like(f'%{other_user_id}%')
            ),
            and_(
                Expense.user_id == other_user_id, 
                Expense.split_with.like(f'%{current_user.id}%')
            )
        )
    ).order_by(Expense.date.desc()).limit(20).all()

    # Query settlements between both users
    settlements = Settlement.query.filter(
        or_(
            and_(Settlement.payer_id == current_user.id, Settlement.receiver_id == other_user_id),
            and_(Settlement.payer_id == other_user_id, Settlement.receiver_id == current_user.id)
        )
    ).order_by(Settlement.date.desc()).limit(20).all()

    # Prepare transaction details
    transactions = []
    
    # Add expenses
    for expense in expenses:
        splits = expense.calculate_splits()
        transactions.append({
            'type': 'expense',
            'date': expense.date.strftime('%Y-%m-%d'),
            'description': expense.description,
            'amount': expense.amount,
            'payer': splits['payer']['name'],
            'split_method': expense.split_method
        })
    
    # Add settlements
    for settlement in settlements:
        transactions.append({
            'type': 'settlement',
            'date': settlement.date.strftime('%Y-%m-%d'),
            'description': settlement.description,
            'amount': settlement.amount,
            'payer': User.query.get(settlement.payer_id).name,
            'receiver': User.query.get(settlement.receiver_id).name
        })
    
    # Sort transactions by date, most recent first
    transactions.sort(key=lambda x: x['date'], reverse=True)

    return jsonify(transactions)


#--------------------
# ROUTES: AUTHENTICATION
#--------------------

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Check if local login is disabled
    local_login_disabled = app.config.get('LOCAL_LOGIN_DISABLE', False) and app.config.get('OIDC_ENABLED', False)
    
    # Check if signups are disabled
    if app.config.get('DISABLE_SIGNUPS', False) and not app.config.get('DEVELOPMENT_MODE', False):
        flash('New account registration is currently disabled.')
        return redirect(url_for('login'))
    
    # If local login is disabled, redirect to login with message
    if local_login_disabled:
        flash('Direct account creation is disabled. Please use SSO.')
        return redirect(url_for('login'))
    
    # Redirect to dashboard if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if User.query.filter_by(id=email).first():
            flash('Email already registered')
            return redirect(url_for('signup'))
        
        # Generate a consistent color for the user
        def generate_user_color(user_id):
            """
            Generate a consistent color for a user based on their ID
            """
            import hashlib
            
            # Use MD5 hash to generate a consistent color
            hash_object = hashlib.md5(user_id.encode())
            hash_hex = hash_object.hexdigest()
            
            # Use the first 6 characters of the hash to create a color
            r = int(hash_hex[:2], 16)
            g = int(hash_hex[2:4], 16)
            b = int(hash_hex[4:6], 16)
            
            # Ensure the color is not too light
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if brightness > 180:
                # If too bright, darken the color
                r = min(int(r * 0.7), 255)
                g = min(int(g * 0.7), 255)
                b = min(int(b * 0.7), 255)
            
            return f'#{r:02x}{g:02x}{b:02x}'
        
        user = User(
            id=email, 
            name=name, 
            user_color=generate_user_color(email)
        )
        user.set_password(password)
        
        # Make first user admin
        is_first_user = User.query.count() == 0
        if is_first_user:
            user.is_admin = True
        
        db.session.add(user)
        db.session.commit()
        
        # Send welcome email
        try:
            send_welcome_email(user)
        except Exception as e:
            app.logger.error(f"Failed to send welcome email: {str(e)}")
        
        login_user(user)
        flash('Account created successfully!')
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html', 
                          oidc_enabled=app.config.get('OIDC_ENABLED', False),
                          local_login_disabled=local_login_disabled)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if we should show a logout message
    if session.pop('show_logout_message', False):
        flash('You have been successfully logged out. You can log in again below.')
    
    # Check if local login is disabled
    oidc_enabled = app.config.get('OIDC_ENABLED', False)
    local_login_disable = app.config.get('LOCAL_LOGIN_DISABLE', False)
    local_login_disabled = local_login_disable and oidc_enabled
    
    # Use development mode auto-login if enabled
    if app.config['DEVELOPMENT_MODE'] and not current_user.is_authenticated:
        dev_user = User.query.filter_by(id=DEV_USER_EMAIL).first()
        if not dev_user:
            dev_user = User(
                id=DEV_USER_EMAIL,
                name='Developer',
                is_admin=True
            )
            dev_user.set_password(DEV_USER_PASSWORD)
            db.session.add(dev_user)
            db.session.commit()
        login_user(dev_user)
        return redirect(url_for('dashboard'))
    
    # Redirect to dashboard if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Handle login form submission
    if request.method == 'POST':
        # If local login is disabled and user tries to use the form
        if local_login_disabled:
            flash(f'Password login is disabled. Please use {app.config.get("OIDC_PROVIDER_NAME", "SSO")}.')
            return redirect(url_for('login'))
            
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(id=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password')
    
    # Render the login template with appropriate flags
    return render_template('login.html', 
                          signups_disabled=app.config.get('DISABLE_SIGNUPS', False),
                          oidc_enabled=oidc_enabled,
                          local_login_disabled=local_login_disabled)

@app.route('/logout')
@login_required_dev
def logout():
    # If user was logged in via OIDC, use the OIDC logout route
    if hasattr(current_user, 'oidc_id') and current_user.oidc_id and app.config.get('OIDC_ENABLED', False):
        return redirect(url_for('logout_oidc'))
    
    # Standard logout for local accounts
    logout_user()
    return redirect(url_for('login'))

#--------------------
# ROUTES: DASHBOARD
#--------------------
@app.route('/dashboard')
@login_required_dev
def dashboard():
    now = datetime.now()
    base_currency = get_base_currency()
    # Fetch all expenses where the user is either the creator or a split participant
    expenses = Expense.query.filter(
        or_(
            Expense.user_id == current_user.id,
            Expense.split_with.like(f'%{current_user.id}%')
        )
    ).order_by(Expense.date.desc()).all()
    
    users = User.query.all()
    groups = Group.query.join(group_users).filter(group_users.c.user_id == current_user.id).all()
    
    # Calculate monthly totals with contributors
    monthly_totals = {}
    if expenses:
        for expense in expenses:
            month_key = expense.date.strftime('%Y-%m')
            if month_key not in monthly_totals:
                monthly_totals[month_key] = {
                    'total': 0.0,
                    'by_card': {},
                    'contributors': {}
                }
            
            # Add to total
            monthly_totals[month_key]['total'] += expense.amount
            
            # Add to card totals
            if expense.card_used not in monthly_totals[month_key]['by_card']:
                monthly_totals[month_key]['by_card'][expense.card_used] = 0
            monthly_totals[month_key]['by_card'][expense.card_used] += expense.amount
            
            # Calculate splits and add to contributors
            splits = expense.calculate_splits()
            
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

    for expense in expenses:
        # Skip if not in current year
        if expense.date.year != current_year:
            continue
            
        splits = expense.calculate_splits()
        
        if expense.paid_by == current_user.id:
            # If user paid, add their own portion
            total_expenses += splits['payer']['amount']
            
            # Also add what others owe them (the entire expense)
            for split in splits['splits']:
                total_expenses += split['amount']
        else:
            # If someone else paid, add only this user's portion
            for split in splits['splits']:
                if split['email'] == current_user.id:
                    total_expenses += split['amount']
                    break
        
    # Calculate current month's total for the current user
    current_month_total = 0
    current_month = now.strftime('%Y-%m')

    for expense in expenses:
        # Skip if not in current month
        if expense.date.strftime('%Y-%m') != current_month:
            continue
            
        splits = expense.calculate_splits()
        
        if expense.paid_by == current_user.id:
            # If user paid, add their own portion
            current_month_total += splits['payer']['amount']
            
            # Also add what others owe them (the entire expense)
            for split in splits['splits']:
                current_month_total += split['amount']
        else:
            # If someone else paid, add only this user's portion
            for split in splits['splits']:
                if split['email'] == current_user.id:
                    current_month_total += split['amount']
                    break


    # Get unique cards (only where current user paid)
    unique_cards = set(expense.card_used for expense in expenses if expense.paid_by == current_user.id)
    
    # Calculate balances using the settlements method
    balances = calculate_balances(current_user.id)
    
    # Sort into "you owe" and "you are owed" categories
    you_owe = []
    you_are_owed = []
    net_balance = 0
    
    for balance in balances:
        if balance['amount'] < 0:
            # Current user owes money
            you_owe.append({
                'id': balance['user_id'],
                'name': balance['name'],
                'email': balance['email'],
                'amount': abs(balance['amount'])
            })
            net_balance -= abs(balance['amount'])
        elif balance['amount'] > 0:
            # Current user is owed money
            you_are_owed.append({
                'id': balance['user_id'],
                'name': balance['name'],
                'email': balance['email'],
                'amount': balance['amount']
            })
            net_balance += balance['amount']
    
    # Create IOU data in the format the dashboard template expects
    iou_data = {
        'owes_me': {user['id']: {'name': user['name'], 'amount': user['amount']} for user in you_are_owed},
        'i_owe': {user['id']: {'name': user['name'], 'amount': user['amount']} for user in you_owe},
        'net_balance': net_balance
    }
    
    currencies = Currency.query.all()
    print(f"Passing {len(currencies)} currencies to dashboard template")
    # Pre-calculate expense splits to avoid repeated calculations in template
    expense_splits = {}
    for expense in expenses:
        expense_splits[expense.id] = expense.calculate_splits()
    currencies = Currency.query.all()
    return render_template('dashboard.html', 
                         expenses=expenses,
                         expense_splits=expense_splits,
                         monthly_totals=monthly_totals,
                         total_expenses=total_expenses,
                         current_month_total=current_month_total,
                         unique_cards=unique_cards,
                         users=users,
                         groups=groups,
                         iou_data=iou_data,
                         base_currency=base_currency,
                         currencies=currencies,
                         now=now)



#--------------------
# ROUTES: EXPENSES MANAGEMENT
#--------------------


@app.route('/add_expense', methods=['GET', 'POST'])
@login_required_dev
def add_expense():
    """Add a new expense with support for AJAX requests"""
    if request.method == 'POST':
        try:
            # Check if this is a personal expense (no splits)
            is_personal_expense = request.form.get('personal_expense') == 'on'
            
            # Handle split_with based on whether it's a personal expense
            if is_personal_expense:
                # For personal expenses, we set split_with to empty
                split_with_str = None
            else:
                # Handle multi-select for split_with
                split_with_ids = request.form.getlist('split_with')
                if not split_with_ids:
                    error_msg = 'Please select at least one person to split with or mark as personal expense.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': error_msg}), 400
                    else:
                        flash_message(error_msg, 'error')
                        return redirect(url_for('dashboard'))
                
                split_with_str = ','.join(split_with_ids) if split_with_ids else None
            
            # Parse date with error handling
            try:
                expense_date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            except ValueError:
                error_msg = 'Invalid date format. Please use YYYY-MM-DD format.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                else:
                    flash_message(error_msg, 'error')
                    return redirect(url_for('dashboard'))
            
            # Process split details if provided
            split_details = None
            if request.form.get('split_details'):
                split_details = request.form.get('split_details')
            
            # Get currency information
            currency_code = request.form.get('currency_code', 'USD')
            if not currency_code:
                # Use user's default currency or system default (USD)
                currency_code = current_user.default_currency_code or 'USD'
            
            # Get original amount in the selected currency
            original_amount = float(request.form['amount'])
            
            # Find the currencies
            selected_currency = Currency.query.filter_by(code=currency_code).first()
            base_currency = Currency.query.filter_by(is_base=True).first()
            
            if not selected_currency or not base_currency:
                error_msg = 'Currency configuration error.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                else:
                    flash_message(error_msg, 'error')
                    return redirect(url_for('dashboard'))
            
            # Convert original amount to base currency
            amount = original_amount * selected_currency.rate_to_base
            
            # Create expense record
            expense = Expense(
                description=request.form['description'],
                amount=amount,  # Amount in base currency
                original_amount=original_amount,  # Original amount in selected currency
                currency_code=currency_code,  # Store the original currency code
                date=expense_date,
                card_used=request.form['card_used'],
                split_method=request.form['split_method'],
                split_value=float(request.form.get('split_value', 0)) if request.form.get('split_value') else 0,
                split_details=split_details,
                paid_by=request.form['paid_by'],
                user_id=current_user.id,
                group_id=request.form.get('group_id') if request.form.get('group_id') else None,
                split_with=split_with_str,
            )
            
            # Handle tags if present
            tag_ids = request.form.getlist('tags')
            if tag_ids:
                for tag_id in tag_ids:
                    tag = Tag.query.get(int(tag_id))
                    if tag and tag.user_id == current_user.id:
                        expense.tags.append(tag)
            
            db.session.add(expense)
            db.session.commit()
            
            # Success response
            success_msg = 'Expense added successfully!'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': success_msg,
                    'expense': {
                        'id': expense.id,
                        'description': expense.description,
                        'amount': expense.amount,
                        'date': expense.date.strftime('%Y-%m-%d')
                    }
                })
            else:
                flash_message(success_msg, 'success')
                return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding expense: {str(e)}")
            error_msg = f'Error: {str(e)}'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 500
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('dashboard'))
    
    # GET request just redirects to dashboard
    return redirect(url_for('dashboard'))


@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required_dev
def delete_expense(expense_id):
    """Delete an expense by ID with AJAX support"""
    try:
        # Find the expense
        expense = Expense.query.get_or_404(expense_id)
        
        # Security check: Only the creator can delete the expense
        if expense.user_id != current_user.id:
            error_msg = 'You do not have permission to delete this expense'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 403
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('transactions'))
        
        # Delete the expense
        db.session.delete(expense)
        db.session.commit()
        
        # Handle AJAX and regular requests
        success_msg = 'Expense deleted successfully'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': success_msg
            })
        else:
            flash_message(success_msg, 'success')
            return redirect(url_for('transactions'))
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting expense {expense_id}: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500
        else:
            flash_message(error_msg, 'error')
            return redirect(url_for('transactions'))

@app.route('/get_expense/<int:expense_id>', methods=['GET'])
@login_required_dev
def get_expense(expense_id):
    """Get expense details for editing"""
    try:
        # Find the expense
        expense = Expense.query.get_or_404(expense_id)
        
        # Security check: Only the creator or participants can view the expense details
        if expense.user_id != current_user.id and current_user.id not in (expense.split_with or ''):
            return jsonify({
                'success': False,
                'message': 'You do not have permission to view this expense'
            }), 403
        
        # Format the expense data
        split_with_ids = expense.split_with.split(',') if expense.split_with else []
        
        # Format the date in YYYY-MM-DD format
        formatted_date = expense.date.strftime('%Y-%m-%d')
        
        # Get tag IDs
        tag_ids = [tag.id for tag in expense.tags]
        
        # Return the expense data
        return jsonify({
            'success': True,
            'expense': {
                'id': expense.id,
                'description': expense.description,
                'amount': expense.amount,
                'date': formatted_date,
                'card_used': expense.card_used,
                'split_method': expense.split_method,
                'split_value': expense.split_value,
                'split_details': expense.split_details,
                'paid_by': expense.paid_by,
                'split_with': split_with_ids,
                'group_id': expense.group_id,
                'currency_code': expense.currency_code or current_user.default_currency_code or 'USD',
                'tag_ids': tag_ids
            }
        })
            
    except Exception as e:
        app.logger.error(f"Error retrieving expense {expense_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/update_expense/<int:expense_id>', methods=['POST'])
@login_required_dev
def update_expense(expense_id):
    """Update an existing expense with AJAX support"""
    try:
        # Find the expense
        expense = Expense.query.get_or_404(expense_id)
        
        # Security check: Only the creator can update the expense
        if expense.user_id != current_user.id:
            error_msg = 'You do not have permission to edit this expense'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 403
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('transactions'))
        
        # Check if this is a personal expense (no splits)
        is_personal_expense = request.form.get('personal_expense') == 'on'
        
        # Handle split_with based on whether it's a personal expense
        if is_personal_expense:
            # For personal expenses, we set split_with to empty
            split_with_str = None
        else:
            # Handle multi-select for split_with
            split_with_ids = request.form.getlist('split_with')
            if not split_with_ids:
                error_msg = 'Please select at least one person to split with or mark as personal expense.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                else:
                    flash_message(error_msg, 'error')
                    return redirect(url_for('transactions'))
            
            split_with_str = ','.join(split_with_ids) if split_with_ids else None
        
        # Parse date with error handling
        try:
            expense_date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        except ValueError:
            error_msg = 'Invalid date format. Please use YYYY-MM-DD format.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('transactions'))
        
        # Process split details if provided
        split_details = None
        if request.form.get('split_details'):
            split_details = request.form.get('split_details')
        
        # Get currency information
        currency_code = request.form.get('currency_code', 'USD')
        if not currency_code:
            # Use user's default currency or system default (USD)
            currency_code = current_user.default_currency_code or 'USD'
        
        # Get original amount in the selected currency
        original_amount = float(request.form['amount'])
        
        # Find the currencies
        selected_currency = Currency.query.filter_by(code=currency_code).first()
        base_currency = Currency.query.filter_by(is_base=True).first()
        
        if not selected_currency or not base_currency:
            error_msg = 'Currency configuration error.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('transactions'))
        
        # Convert original amount to base currency
        amount = original_amount * selected_currency.rate_to_base
        
        # Update expense fields
        expense.description = request.form['description']
        expense.amount = amount
        expense.original_amount = original_amount
        expense.currency_code = currency_code
        expense.date = expense_date
        expense.card_used = request.form['card_used']
        expense.split_method = request.form['split_method']
        expense.split_value = float(request.form.get('split_value', 0)) if request.form.get('split_value') else 0
        expense.split_details = split_details
        expense.paid_by = request.form['paid_by']
        expense.group_id = request.form.get('group_id') if request.form.get('group_id') and request.form.get('group_id') != '' else None
        expense.split_with = split_with_str
        
        # Handle tags - first remove all existing tags
        expense.tags = []
        
        # Add new tags
        tag_ids = request.form.getlist('tags')
        if tag_ids:
            for tag_id in tag_ids:
                tag = Tag.query.get(int(tag_id))
                if tag and tag.user_id == current_user.id:
                    expense.tags.append(tag)
        
        # Save changes
        db.session.commit()
        
        # Success response
        success_msg = 'Expense updated successfully!'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': success_msg,
                'expense': {
                    'id': expense.id,
                    'description': expense.description,
                    'amount': expense.amount,
                    'date': expense.date.strftime('%Y-%m-%d')
                }
            })
        else:
            flash_message(success_msg, 'success')
            return redirect(url_for('transactions'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating expense {expense_id}: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash_message(error_msg, 'error')
            return redirect(url_for('transactions'))


#--------------------
# ROUTES: tags
#--------------------


@app.route('/tags')
@login_required_dev
def manage_tags():
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    return render_template('tags.html', tags=tags)

@app.route('/tags/add', methods=['POST'])
@login_required_dev
def add_tag():
    """Add a new tag with AJAX support"""
    try:
        name = request.form.get('name')
        color = request.form.get('color', "#6c757d")
        
        # Check if tag already exists for this user
        existing_tag = Tag.query.filter_by(user_id=current_user.id, name=name).first()
        if existing_tag:
            error_msg = 'Tag with this name already exists'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('manage_tags'))
        
        tag = Tag(name=name, color=color, user_id=current_user.id)
        db.session.add(tag)
        db.session.commit()
        
        success_msg = 'Tag added successfully'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': success_msg,
                'tag': {
                    'id': tag.id,
                    'name': tag.name,
                    'color': tag.color
                }
            })
        else:
            flash_message(success_msg, 'success')
            return redirect(url_for('manage_tags'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding tag: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash_message(error_msg, 'error')
            return redirect(url_for('manage_tags'))
            
@app.route('/tags/delete/<int:tag_id>', methods=['POST'])
@login_required_dev
def delete_tag(tag_id):
    """Delete a tag with AJAX support"""
    try:
        tag = Tag.query.get_or_404(tag_id)
        
        # Check if tag belongs to current user
        if tag.user_id != current_user.id:
            error_msg = 'You don\'t have permission to delete this tag'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 403
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('manage_tags'))
        
        # Remove tag from all expenses
        for expense in tag.expenses:
            expense.tags.remove(tag)
        
        # Delete the tag
        db.session.delete(tag)
        db.session.commit()
        
        success_msg = 'Tag deleted successfully'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': success_msg})
        else:
            flash_message(success_msg, 'success')
            return redirect(url_for('manage_tags'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting tag {tag_id}: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash_message(error_msg, 'error')
            return redirect(url_for('manage_tags'))

@app.route('/recurring')
@login_required_dev
def recurring():
    base_currency = get_base_currency()
    recurring_expenses = RecurringExpense.query.filter(
        or_(
            RecurringExpense.user_id == current_user.id,
            RecurringExpense.split_with.like(f'%{current_user.id}%')
        )
    ).all()
    users = User.query.all()
    groups = Group.query.join(group_users).filter(group_users.c.user_id == current_user.id).all()
    currencies = Currency.query.all()
    return render_template('recurring.html', 
                          recurring_expenses=recurring_expenses, 
                          users=users,
                          currencies=currencies,
                          base_currency=base_currency,
                          groups=groups)

@app.route('/add_recurring', methods=['POST'])
@login_required_dev
def add_recurring():
    try:
        # Check if this is a personal expense (no splits)
        is_personal_expense = request.form.get('personal_expense') == 'on'
        
        # Handle split_with based on whether it's a personal expense
        if is_personal_expense:
            # For personal expenses, we set split_with to empty
            split_with_str = None
        else:
            # Handle multi-select for split_with
            split_with_ids = request.form.getlist('split_with')
            if not split_with_ids:
                error_msg = 'Please select at least one person to split with or mark as personal expense.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                else:
                    flash(error_msg)
                    return redirect(url_for('recurring'))
            
            split_with_str = ','.join(split_with_ids) if split_with_ids else None
        
        # Parse date with error handling
        try:
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = None
            if request.form.get('end_date'):
                end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        except ValueError:
            error_msg = 'Invalid date format. Please use YYYY-MM-DD format.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash(error_msg)
                return redirect(url_for('recurring'))
        
        # Process split details if provided
        split_details = None
        if request.form.get('split_details'):
            split_details = request.form.get('split_details')
        
        # Get currency information
        currency_code = request.form.get('currency_code', 'USD')
        if not currency_code:
            # Use user's default currency or system default (USD)
            currency_code = current_user.default_currency_code or 'USD'
        
        # Get original amount in the selected currency
        original_amount = float(request.form['amount'])
        
        # Find the currencies
        selected_currency = Currency.query.filter_by(code=currency_code).first()
        base_currency = Currency.query.filter_by(is_base=True).first()
        
        if not selected_currency or not base_currency:
            error_msg = 'Currency configuration error.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash(error_msg)
                return redirect(url_for('recurring'))
        
        # Convert original amount to base currency
        amount = original_amount * selected_currency.rate_to_base
        
        # Create new recurring expense
        recurring_expense = RecurringExpense(
            description=request.form['description'],
            amount=amount,
            original_amount=original_amount,
            currency_code=currency_code,
            card_used=request.form['card_used'],
            split_method=request.form['split_method'],
            split_value=float(request.form.get('split_value', 0)) if request.form.get('split_value') else 0,
            split_details=split_details,
            paid_by=request.form['paid_by'],
            user_id=current_user.id,
            group_id=request.form.get('group_id') if request.form.get('group_id') else None,
            split_with=split_with_str,
            frequency=request.form['frequency'],
            start_date=start_date,
            end_date=end_date,
            active=True
        )
        
        # Handle tags if present
        tag_ids = request.form.getlist('tags')
        
        db.session.add(recurring_expense)
        db.session.commit()
        
        # Create first expense instance if the start date is today or in the past
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date <= today:
            expense = recurring_expense.create_expense_instance(start_date)
            
            # Add the tags to the expense
            if tag_ids:
                for tag_id in tag_ids:
                    tag = Tag.query.get(int(tag_id))
                    if tag and tag.user_id == current_user.id:
                        expense.tags.append(tag)
            
            db.session.add(expense)
            db.session.commit()
        
        success_msg = 'Recurring expense added successfully!'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': success_msg,
                'recurring': {
                    'id': recurring_expense.id,
                    'description': recurring_expense.description,
                    'amount': recurring_expense.amount,
                    'frequency': recurring_expense.frequency
                }
            })
        else:
            flash(success_msg)
            return redirect(url_for('recurring'))
            
    except Exception as e:
        app.logger.error(f"Error adding recurring expense: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash(error_msg)
            return redirect(url_for('recurring'))

@app.route('/toggle_recurring/<int:recurring_id>', methods=['POST'])
@login_required_dev
def toggle_recurring(recurring_id):
    try:
        recurring_expense = RecurringExpense.query.get_or_404(recurring_id)
        
        # Security check
        if recurring_expense.user_id != current_user.id:
            error_msg = "You don't have permission to modify this recurring expense"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 403
            else:
                flash(error_msg)
                return redirect(url_for('recurring'))
        
        # Toggle the active status
        recurring_expense.active = not recurring_expense.active
        db.session.commit()
        
        status = "activated" if recurring_expense.active else "deactivated"
        success_msg = f'Recurring expense {status} successfully'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': success_msg,
                'status': recurring_expense.active
            })
        else:
            flash(success_msg)
            return redirect(url_for('recurring'))
            
    except Exception as e:
        app.logger.error(f"Error toggling recurring expense: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash(error_msg)
            return redirect(url_for('recurring'))

@app.route('/delete_recurring/<int:recurring_id>', methods=['POST'])
@login_required_dev
def delete_recurring(recurring_id):
    try:
        recurring_expense = RecurringExpense.query.get_or_404(recurring_id)
        
        # Security check
        if recurring_expense.user_id != current_user.id:
            error_msg = "You don't have permission to delete this recurring expense"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 403
            else:
                flash(error_msg)
                return redirect(url_for('recurring'))
        
        db.session.delete(recurring_expense)
        db.session.commit()
        
        success_msg = 'Recurring expense deleted successfully'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': success_msg
            })
        else:
            flash(success_msg)
            return redirect(url_for('recurring'))
            
    except Exception as e:
        app.logger.error(f"Error deleting recurring expense: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash(error_msg)
            return redirect(url_for('recurring'))
            
#--------------------
# ROUTES: GROUPS
#--------------------

@app.route('/groups')
@login_required_dev
def groups():
    groups = Group.query.join(group_users).filter(group_users.c.user_id == current_user.id).all()
    all_users = User.query.all()
    return render_template('groups.html', groups=groups, users=all_users)

@app.route('/groups/create', methods=['POST'])
@login_required_dev
def create_group():
    """Create a new group with AJAX support"""
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        member_ids = request.form.getlist('members')
        
        group = Group(
            name=name,
            description=description,
            created_by=current_user.id
        )
        
        # Add creator as a member
        group.members.append(current_user)
        
        # Add selected members
        for member_id in member_ids:
            user = User.query.filter_by(id=member_id).first()
            if user and user != current_user:
                group.members.append(user)
        
        db.session.add(group)
        db.session.commit()
        
        success_msg = 'Group created successfully!'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': success_msg,
                'group': {
                    'id': group.id,
                    'name': group.name,
                    'member_count': len(group.members)
                }
            })
        else:
            flash_message(success_msg, 'success')
            return redirect(url_for('groups'))
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating group: {str(e)}")
        error_msg = f'Error creating group: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash_message(error_msg, 'error')
            return redirect(url_for('groups'))

@app.route('/groups/<int:group_id>')
@login_required_dev
def group_details(group_id):
    base_currency = get_base_currency()
    group = Group.query.get_or_404(group_id)

    # Check if user is member of group
    if current_user not in group.members:
        flash_message('Access denied. You are not a member of this group.', 'error')
        return redirect(url_for('groups'))
    
    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.date.desc()).all()
    all_users = User.query.all()
    currencies = Currency.query.all()
    return render_template('group_details.html', group=group, expenses=expenses, currencies=currencies, base_currency=base_currency, users=all_users)

@app.route('/groups/<int:group_id>/add_member', methods=['POST'])
@login_required_dev
def add_group_member(group_id):
    """Add a member to a group with AJAX support"""
    try:
        group = Group.query.get_or_404(group_id)
        
        # Check permissions
        if current_user != group.creator:
            error_msg = 'Only group creator can add members'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 403
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('group_details', group_id=group_id))
        
        # Get user to add
        member_id = request.form.get('user_id')
        user = User.query.filter_by(id=member_id).first()
        
        if not user:
            error_msg = 'User not found'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 404
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('group_details', group_id=group_id))
        
        # Check if already a member
        if user in group.members:
            error_msg = f'{user.name} is already a member of this group'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash_message(error_msg, 'info')
                return redirect(url_for('group_details', group_id=group_id))
        
        # Add member
        group.members.append(user)
        db.session.commit()
        
        # Send invitation email
        try:
            send_group_invitation_email(user, group, current_user)
        except Exception as e:
            app.logger.error(f"Failed to send group invitation email: {str(e)}")
        
        success_msg = f'{user.name} added to group!'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': success_msg,
                'user': {
                    'id': user.id,
                    'name': user.name
                }
            })
        else:
            flash_message(success_msg, 'success')
            return redirect(url_for('group_details', group_id=group_id))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding group member: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash_message(error_msg, 'error')
            return redirect(url_for('group_details', group_id=group_id))

@app.route('/groups/<int:group_id>/remove_member/<member_id>', methods=['POST'])
@login_required_dev
def remove_group_member(group_id, member_id):
    """Remove a member from a group with AJAX support"""
    try:
        group = Group.query.get_or_404(group_id)
        
        # Check permissions
        if current_user != group.creator:
            error_msg = 'Only group creator can remove members'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 403
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('group_details', group_id=group_id))
        
        # Get user to remove
        user = User.query.filter_by(id=member_id).first()
        
        if not user:
            error_msg = 'User not found'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 404
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('group_details', group_id=group_id))
        
        # Check if user is a member and not the creator
        if user not in group.members:
            error_msg = f'{user.name} is not a member of this group'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('group_details', group_id=group_id))
        
        if user == group.creator:
            error_msg = 'Cannot remove group creator'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('group_details', group_id=group_id))
        
        # Remove member
        group.members.remove(user)
        db.session.commit()
        
        success_msg = f'{user.name} removed from group!'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': success_msg
            })
        else:
            flash_message(success_msg, 'success')
            return redirect(url_for('group_details', group_id=group_id))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error removing group member: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash_message(error_msg, 'error')
            return redirect(url_for('group_details', group_id=group_id))

#--------------------
# ROUTES: ADMIN
#--------------------

@app.route('/admin')
@login_required_dev
def admin():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    app_settings = AppSettings.get_settings()
    
    return render_template('admin.html', users=users, settings=app_settings)
    
@app.route('/admin/add_user', methods=['POST'])
@login_required_dev
def admin_add_user():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    email = request.form.get('email')
    password = request.form.get('password')
    name = request.form.get('name')
    is_admin = request.form.get('is_admin') == 'on'
    
    if User.query.filter_by(id=email).first():
        flash('Email already registered')
        return redirect(url_for('admin'))
    
    user = User(id=email, name=name, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    # Send welcome email
    try:
        send_welcome_email(user)
    except Exception as e:
        app.logger.error(f"Failed to send welcome email: {str(e)}")
    
    flash('User added successfully!')
    return redirect(url_for('admin'))

@app.route('/admin/delete_user/<user_id>', methods=['POST'])
@login_required_dev
def admin_delete_user(user_id):
    if not current_user.is_admin:
        flash_message('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if user_id == current_user.id:
        flash_message('Cannot delete your own admin account!', 'error')
        return redirect(url_for('admin'))
    
    user = User.query.filter_by(id=user_id).first()
    if user:
        # Delete associated expenses first
        Expense.query.filter_by(user_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()
        flash_message('User deleted successfully!', 'success')
    
    return redirect(url_for('admin'))

@app.route('/admin/reset_password', methods=['POST'])
@login_required_dev
def admin_reset_password():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    user_id = request.form.get('user_id')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate passwords match
    if new_password != confirm_password:
        flash('Passwords do not match!')
        return redirect(url_for('admin'))
    
    user = User.query.filter_by(id=user_id).first()
    if user:
        user.set_password(new_password)
        db.session.commit()
        flash(f'Password reset successful for {user.name}!')
    else:
        flash('User not found.')
        
    return redirect(url_for('admin'))

# Add this with your other admin routes

@app.route('/admin/update_app_branding', methods=['POST'])
@login_required_dev
def update_app_branding():
    """Update app branding settings (admin only)"""
    if not current_user.is_admin:
        flash_message('Only administrators can change app branding', 'danger')
        return redirect(url_for('admin'))
        
    settings = AppSettings.get_settings()
    settings.app_title = request.form.get('app_title')
    settings.app_logo_emoji = request.form.get('app_logo_emoji')
    settings.app_logo_url = request.form.get('app_logo_url')
    settings.last_updated = datetime.utcnow()
    settings.updated_by = current_user.id
    settings.is_customized = True  # Mark as customized
    
    db.session.commit()
    
    flash_message('App branding settings updated successfully', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/reset_app_branding', methods=['POST'])
@login_required_dev
def reset_app_branding():
    """Reset app branding to default values"""
    if not current_user.is_admin:
        flash_message('Only administrators can change app branding', 'danger')
        return redirect(url_for('admin'))
        
    settings = AppSettings.get_settings()
    settings.app_title = "Dollar Dollar Bill Y'all"
    settings.app_logo_emoji = "💵"
    settings.app_logo_url = "/static/images/dollar-logo.png"
#--------------------
# ROUTES: SETTLEMENTS
#--------------------

@app.route('/settlements')
@login_required_dev
def settlements():
    # Get all settlements involving the current user
    base_currency = get_base_currency()
    settlements = Settlement.query.filter(
        or_(
            Settlement.payer_id == current_user.id,
            Settlement.receiver_id == current_user.id
        )
    ).order_by(Settlement.date.desc()).all()
    
    # Get all users
    users = User.query.all()
    
    # Calculate balances between users
    balances = calculate_balances(current_user.id)
    
    # Split balances into "you owe" and "you are owed" categories
    you_owe = []
    you_are_owed = []
    
    for balance in balances:
        if balance['amount'] < 0:
            # Current user owes money
            you_owe.append({
                'id': balance['user_id'],
                'name': balance['name'],
                'email': balance['email'],
                'amount': abs(balance['amount'])
            })
        elif balance['amount'] > 0:
            # Current user is owed money
            you_are_owed.append({
                'id': balance['user_id'],
                'name': balance['name'],
                'email': balance['email'],
                'amount': balance['amount']
            })
    
    return render_template('settlements.html', 
                          settlements=settlements,
                          users=users,
                          you_owe=you_owe,
                          you_are_owed=you_are_owed,
                          base_currency=base_currency,
                          current_user_id=current_user.id)

@app.route('/add_settlement', methods=['POST'])
@login_required_dev
def add_settlement():
    """Add a settlement with AJAX support"""
    try:
        # Parse date with error handling
        try:
            settlement_date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        except ValueError:
            error_msg = 'Invalid date format. Please use YYYY-MM-DD format.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('settlements'))
        
        # Create settlement record
        settlement = Settlement(
            payer_id=request.form['payer_id'],
            receiver_id=request.form['receiver_id'],
            amount=float(request.form['amount']),
            date=settlement_date,
            description=request.form.get('description', 'Settlement')
        )
        
        db.session.add(settlement)
        db.session.commit()
        
        success_msg = 'Settlement recorded successfully!'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': success_msg,
                'settlement': {
                    'id': settlement.id,
                    'amount': settlement.amount,
                    'date': settlement.date.strftime('%Y-%m-%d'),
                    'payer': settlement.payer.name,
                    'receiver': settlement.receiver.name
                }
            })
        else:
            flash_message(success_msg, 'success')
            return redirect(url_for('settlements'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding settlement: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash_message(error_msg, 'error')
            return redirect(url_for('settlements'))


@app.route('/currencies')
@login_required_dev
def manage_currencies():
    currencies = Currency.query.all()
    return render_template('currencies.html', currencies=currencies)

@app.route('/currencies/add', methods=['POST'])
@login_required_dev
def add_currency():
    if not current_user.is_admin:
        flash_message('Only administrators can add currencies', 'error')
        return redirect(url_for('manage_currencies'))
    
    code = request.form.get('code', '').upper()
    name = request.form.get('name')
    symbol = request.form.get('symbol')
    rate_to_base = float(request.form.get('rate_to_base', 1.0))
    is_base = request.form.get('is_base') == 'on'
    
    # Validate currency code format
    if not code or len(code) != 3 or not code.isalpha():
        flash_message('Invalid currency code. Please use 3-letter ISO currency code (e.g., USD, EUR, GBP)', 'error')
        return redirect(url_for('manage_currencies'))
    
    # Check if currency already exists
    existing = Currency.query.filter_by(code=code).first()
    if existing:
        flash_message(f'Currency {code} already exists', 'error')
        return redirect(url_for('manage_currencies'))
    
    # If setting as base, update all existing base currencies
    if is_base:
        for currency in Currency.query.filter_by(is_base=True).all():
            currency.is_base = False
    
    # Create new currency
    currency = Currency(
        code=code,
        name=name,
        symbol=symbol,
        rate_to_base=rate_to_base,
        is_base=is_base
    )
    db.session.add(currency)
    
    try:
        db.session.commit()
        flash_message(f'Currency {code} added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash_message(f'Error adding currency: {str(e)}', 'error')
    
    return redirect(url_for('manage_currencies'))

@app.route('/currencies/update/<code>', methods=['POST'])
@login_required_dev
def update_currency(code):
    if not current_user.is_admin:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Only administrators can update currencies'}), 403
        flash('Only administrators can update currencies')
        return redirect(url_for('manage_currencies'))
    
    currency = Currency.query.filter_by(code=code).first_or_404()
    
    # Update fields
    currency.name = request.form.get('name', currency.name)
    currency.symbol = request.form.get('symbol', currency.symbol)
    currency.rate_to_base = float(request.form.get('rate_to_base', currency.rate_to_base))
    new_is_base = request.form.get('is_base') == 'on'
    
    # If setting as base, update all existing base currencies
    if new_is_base and not currency.is_base:
        for curr in Currency.query.filter_by(is_base=True).all():
            curr.is_base = False
    
    currency.is_base = new_is_base
    currency.last_updated = datetime.utcnow()
    
    try:
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'Currency {code} updated successfully'})
        flash(f'Currency {code} updated successfully')
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'Error updating currency: {str(e)}'}), 500
        flash(f'Error updating currency: {str(e)}')
    
    return redirect(url_for('manage_currencies'))

@app.route('/currencies/delete/<string:code>', methods=['DELETE'])
@login_required
def delete_currency(code):
    """
    Delete a currency from the system
    Only accessible to admin users
    """
    # Ensure user is an admin
    if not current_user.is_admin:
        return jsonify({
            'success': False, 
            'message': 'Unauthorized. Admin access required.'
        }), 403
    
    try:
        # Find the currency
        currency = Currency.query.filter_by(code=code).first()
        
        if not currency:
            return jsonify({
                'success': False, 
                'message': f'Currency {code} not found.'
            }), 404
        
        # Prevent deleting the base currency
        if currency.is_base:
            return jsonify({
                'success': False, 
                'message': 'Cannot delete the base currency. Set another currency as base first.'
            }), 400
        
        
        # Remove the currency
        db.session.delete(currency)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Currency {code} deleted successfully.'
        })
    
    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        
        # Log the error
        app.logger.error(f"Error deleting currency {code}: {str(e)}")
        
        return jsonify({
            'success': False, 
            'message': f'An error occurred while deleting currency {code}.'
        }), 500
@app.route('/currencies/set-base/<string:code>', methods=['POST'])
@login_required
def set_base_currency(code):
    """
    Change the base currency
    Only accessible to admin users
    """
    # Ensure user is an admin
    if not current_user.is_admin:
        flash('Unauthorized. Admin access required.', 'error')
        return redirect(url_for('manage_currencies'))  # Changed 'currencies' to 'manage_currencies'
    
    try:
        # Find the currency to be set as base
        new_base_currency = Currency.query.filter_by(code=code).first()
        
        if not new_base_currency:
            flash(f'Currency {code} not found.', 'error')
            return redirect(url_for('manage_currencies'))  # Changed 'currencies' to 'manage_currencies'
        
        # Find and unset the current base currency
        current_base_currency = Currency.query.filter_by(is_base=True).first()
        
        if current_base_currency:
            # Unset current base currency
            current_base_currency.is_base = False
        
        # Set new base currency
        new_base_currency.is_base = True
        
        # Update rate to base for this currency
        new_base_currency.rate_to_base = 1.0
        
        # Update rates for other currencies relative to the new base
        try:
            update_currency_rates()
        except Exception as rate_update_error:
            # Log the error but don't prevent the base currency change
            app.logger.error(f"Error updating rates after base currency change: {str(rate_update_error)}")
        
        # Commit changes
        db.session.commit()
        
        flash(f'Base currency successfully changed to {code}.', 'success')
    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        
        # Log the error
        app.logger.error(f"Error changing base currency to {code}: {str(e)}")
        
        flash('An error occurred while changing the base currency.', 'error')
    
    return redirect(url_for('manage_currencies'))  # Changed 'currencies' to 'manage_currencies'
@app.route('/update_currency_rates', methods=['POST'])
@login_required_dev
def update_rates_route():
    """API route to update currency rates"""
    if not current_user.is_admin:
        flash('Only administrators can update currency rates')
        return redirect(url_for('manage_currencies'))
    
    result = update_currency_rates()
    
    if result >= 0:
        flash(f'Successfully updated {result} currency rates')
    else:
        flash('Error updating currency rates. Check the logs for details.')
    
    return redirect(url_for('manage_currencies'))
@app.route('/set_default_currency', methods=['POST'])
@login_required_dev
def set_default_currency():
    currency_code = request.form.get('default_currency')
    
    # Verify currency exists
    currency = Currency.query.filter_by(code=currency_code).first()
    if not currency:
        flash('Invalid currency selected')
        return redirect(url_for('manage_currencies'))
    
    # Update user's default currency
    current_user.default_currency_code = currency_code
    db.session.commit()
    
    flash(f'Default currency set to {currency.code} ({currency.symbol})')
    return redirect(url_for('manage_currencies'))

@app.route('/transactions')
@login_required_dev
def transactions():
    """Display all transactions with filtering capabilities"""
    # Fetch all expenses where the user is either the creator or a split participant
    base_currency = get_base_currency()
    expenses = Expense.query.filter(
        or_(
            Expense.user_id == current_user.id,
            Expense.split_with.like(f'%{current_user.id}%')
        )
    ).order_by(Expense.date.desc()).all()
    
    users = User.query.all()
    
    # Pre-calculate all expense splits to avoid repeated calculations
    expense_splits = {}
    for expense in expenses:
        expense_splits[expense.id] = expense.calculate_splits()
    
    # Calculate total expenses for current user (similar to dashboard calculation)
    now = datetime.now()
    current_year = now.year
    total_expenses = 0

    for expense in expenses:
        # Skip if not in current year
        if expense.date.year != current_year:
            continue
            
        splits = expense_splits[expense.id]
        
        if expense.paid_by == current_user.id:
            # If user paid, add their own portion
            total_expenses += splits['payer']['amount']
            
            # Also add what others owe them (the entire expense)
            for split in splits['splits']:
                total_expenses += split['amount']
        else:
            # If someone else paid, add only this user's portion
            for split in splits['splits']:
                if split['email'] == current_user.id:
                    total_expenses += split['amount']
                    break
    
    # Calculate current month total (similar to dashboard calculation)
    current_month_total = 0
    current_month = now.strftime('%Y-%m')

    for expense in expenses:
        # Skip if not in current month
        if expense.date.strftime('%Y-%m') != current_month:
            continue
            
        splits = expense_splits[expense.id]
        
        if expense.paid_by == current_user.id:
            # If user paid, add their own portion
            current_month_total += splits['payer']['amount']
            
            # Also add what others owe them (the entire expense)
            for split in splits['splits']:
                current_month_total += split['amount']
        else:
            # If someone else paid, add only this user's portion
            for split in splits['splits']:
                if split['email'] == current_user.id:
                    current_month_total += split['amount']
                    break
    
    # Calculate monthly totals for statistics
    monthly_totals = {}
    unique_cards = set()
    
    currencies = Currency.query.all()
    for expense in expenses:
        month_key = expense.date.strftime('%Y-%m')
        if month_key not in monthly_totals:
            monthly_totals[month_key] = {
                'total': 0.0,
                'by_card': {},
                'contributors': {}
            }
            
        # Add to monthly totals
        monthly_totals[month_key]['total'] += expense.amount
        
        # Add card to total
        if expense.card_used not in monthly_totals[month_key]['by_card']:
            monthly_totals[month_key]['by_card'][expense.card_used] = 0
        monthly_totals[month_key]['by_card'][expense.card_used] += expense.amount
        
        # Track unique cards where current user paid
        if expense.paid_by == current_user.id:
            unique_cards.add(expense.card_used)
        
        # Add contributors' data
        splits = expense_splits[expense.id]
        
        # Add payer's portion
        if splits['payer']['amount'] > 0:
            user_id = splits['payer']['email']
            if user_id not in monthly_totals[month_key]['contributors']:
                monthly_totals[month_key]['contributors'][user_id] = 0
            monthly_totals[month_key]['contributors'][user_id] += splits['payer']['amount']
        
        # Add other contributors' portions
        for split in splits['splits']:
            user_id = split['email']
            if user_id not in monthly_totals[month_key]['contributors']:
                monthly_totals[month_key]['contributors'][user_id] = 0
            monthly_totals[month_key]['contributors'][user_id] += split['amount']
    
    return render_template('transactions.html', 
                        expenses=expenses,
                        expense_splits=expense_splits,
                        monthly_totals=monthly_totals,
                        total_expenses=total_expenses,
                        current_month_total=current_month_total,
                        unique_cards=unique_cards,
                        users=users,
                        base_currency=base_currency,
                        currencies=currencies)

#--------------------
# ROUTES: Housecleaning
#--------------------

@app.route('/export_transactions', methods=['POST'])
@login_required_dev
def export_transactions():
    """Export transactions as CSV file based on filter criteria"""
    try:
        # Get filter criteria from request
        filters = request.json if request.is_json else {}
        
        # Default to all transactions for the current user if no filters provided
        user_id = current_user.id
        
        # Extract filter parameters
        start_date = filters.get('startDate')
        end_date = filters.get('endDate')
        paid_by = filters.get('paidBy', 'all')
        card_used = filters.get('cardUsed', 'all')
        group_id = filters.get('groupId', 'all')
        min_amount = filters.get('minAmount')
        max_amount = filters.get('maxAmount')
        description = filters.get('description', '')
        
        # Import required libraries
        import csv
        import io
        from flask import send_file
        
        # Build query with SQLAlchemy
        query = Expense.query.filter(
            or_(
                Expense.user_id == user_id,
                Expense.split_with.like(f'%{user_id}%')
            )
        )
        
        # Apply filters
        if start_date:
            query = query.filter(Expense.date >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Expense.date <= datetime.strptime(end_date, '%Y-%m-%d'))
        if paid_by and paid_by != 'all':
            query = query.filter(Expense.paid_by == paid_by)
        if card_used and card_used != 'all':
            query = query.filter(Expense.card_used == card_used)
        if group_id:
            if group_id == 'none':
                query = query.filter(Expense.group_id == None)
            elif group_id != 'all':
                query = query.filter(Expense.group_id == group_id)
        if min_amount:
            query = query.filter(Expense.amount >= float(min_amount))
        if max_amount:
            query = query.filter(Expense.amount <= float(max_amount))
        if description:
            query = query.filter(Expense.description.ilike(f'%{description}%'))
        
        # Order by date, newest first
        expenses = query.order_by(Expense.date.desc()).all()
        
        # Create CSV data in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header row
        writer.writerow([
            'Date', 'Description', 'Amount', 'Card Used', 'Paid By', 
            'Split Method', 'Group', 'Your Role', 'Your Share', 'Total Expense'
        ])
        
        # Write data rows
        for expense in expenses:
            # Calculate split info
            splits = expense.calculate_splits()
            
            # Get group name if applicable
            group_name = expense.group.name if expense.group else "No Group"
            
            # Calculate user's role and share
            user_role = ''
            user_share = 0
            
            if expense.paid_by == user_id:
                user_role = 'Payer'
                user_share = splits['payer']['amount']
            else:
                user_role = 'Participant'
                for split in splits['splits']:
                    if split['email'] == user_id:
                        user_share = split['amount']
                        break
            
            # Find the name of who paid
            payer = User.query.filter_by(id=expense.paid_by).first()
            payer_name = payer.name if payer else expense.paid_by
            
            writer.writerow([
                expense.date.strftime('%Y-%m-%d'),
                expense.description,
                f"{expense.amount:.2f}",
                expense.card_used,
                payer_name,
                expense.split_method,
                group_name,
                user_role,
                f"{user_share:.2f}",
                f"{expense.amount:.2f}"
            ])
        
        # Rewind the string buffer
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"dollar_bill_transactions_{timestamp}.csv"
        
        # Send file for download
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
    )
        
    except Exception as e:
        app.logger.error(f"Error exporting transactions: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
#--------------------
# ROUTES: user 
#--------------------
@app.route('/profile')
@login_required_dev
def profile():
    """User profile page with settings to change password and personal color"""
    # Get user's account creation date (approximating from join date since we don't store it)
    account_created = "Account creation date not available"
    
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
    # Update to use flash_message instead of flash
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate inputs
    if not current_password or not new_password or not confirm_password:
        flash_message('All password fields are required', 'error')
        return redirect(url_for('profile'))
    
    if new_password != confirm_password:
        flash_message('New passwords do not match', 'error')
        return redirect(url_for('profile'))
    
    # Verify current password
    if not current_user.check_password(current_password):
        flash_message('Current password is incorrect', 'error')
        return redirect(url_for('profile'))
    
    # Set new password
    current_user.set_password(new_password)
    db.session.commit()
    
    flash_message('Password updated successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/update_color', methods=['POST'])
@login_required_dev
def update_color():
    """Update user's personal color with AJAX support"""
    try:
        # Retrieve color from form, defaulting to primary green
        user_color = request.form.get('user_color', '#15803d').strip()
        
        # Validate hex color format (supports 3 or 6 digit hex colors)
        hex_pattern = r'^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$'
        if not user_color or not re.match(hex_pattern, user_color):
            error_msg = 'Invalid color format. Please use a valid hex color code.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash_message(error_msg, 'error')
                return redirect(url_for('profile'))
        
        # Normalize to 6-digit hex if 3-digit shorthand is used
        if len(user_color) == 4:  # #RGB format
            user_color = '#' + ''.join(2 * c for c in user_color[1:])
        
        # Update user's color
        current_user.user_color = user_color
        db.session.commit()
        
        success_msg = 'Your personal color has been updated'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': success_msg,
                'color': user_color
            })
        else:
            flash_message(success_msg, 'success')
            return redirect(url_for('profile'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating user color: {str(e)}")
        error_msg = f'Error: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        else:
            flash_message(error_msg, 'error')
            return redirect(url_for('profile'))
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
    expenses = Expense.query.filter(and_(*query_filters)).order_by(Expense.date).all()
    
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
            current_user_expenses.append({
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
            })
            
            # Add to user's total
            total_user_expenses += user_portion
    
    # Calculate monthly spending for current user
    monthly_spending = {}
    monthly_labels = []
    monthly_amounts = []
    
    # Initialize all months in range
    current_date = start_date.replace(day=1)
    while current_date <= end_date:
        month_key = current_date.strftime('%Y-%m')
        month_label = current_date.strftime('%b %Y')
        monthly_labels.append(month_label)
        monthly_spending[month_key] = 0
        
        # Advance to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    # Fill in spending data
    for expense_data in current_user_expenses:
        month_key = expense_data['date'].strftime('%Y-%m')
        if month_key in monthly_spending:
            monthly_spending[month_key] += expense_data['user_portion']
    
    # Prepare chart data in correct order
    for month_key in sorted(monthly_spending.keys()):
        monthly_amounts.append(monthly_spending[month_key])
    
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
    
    previous_expenses = Expense.query.filter(and_(*previous_period_filters)).all()
    previous_total = 0
    
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
    
    for month_date in month_dates:
        # Add all items that occurred before this month
        while chronological_items and chronological_items[0]['date'] < month_date:
            item = chronological_items.pop(0)
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
    top_expenses = sorted(current_user_expenses, key=lambda x: x['user_portion'], reverse=True)[:10]  # Top 10

    return render_template('stats.html',
                        expenses=expenses,
                        total_expenses=total_user_expenses,  # User's spending only
                        spending_trend=spending_trend,
                        net_balance=net_balance,
                        balance_count=balance_count,
                        monthly_average=monthly_average,
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
                        top_expenses=top_expenses)


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
        init_default_currencies()
        print("Tables created successfully")
    except Exception as e:
        print(f"ERROR CREATING TABLES: {str(e)}")

# Register OIDC routes
if oidc_enabled:
    register_oidc_routes(app, User, db)        

if __name__ == '__main__':
    app.run(debug=True, port=5001)
