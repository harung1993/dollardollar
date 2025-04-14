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
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import calendar
from functools import wraps
import logging
from sqlalchemy import func, or_, and_
import secrets
from flask_mail import Message
from flask_migrate import Migrate
import ssl
import requests
from sqlalchemy import inspect, text
from oidc_auth import setup_oidc_config, register_oidc_routes
from oidc_user import extend_user_model
from datetime import datetime, timedelta
from simplefin_client import SimpleFin
from flask import session, request, jsonify, url_for, flash, redirect
from datetime import datetime, timedelta
import base64
import pytz
from config import get_config
from extensions import db, login_manager, mail, migrate, scheduler
import csv
import re
import io
import json
import uuid
import base64
import pytz
import secrets
import logging
import hashlib
import requests
import calendar
from functools import wraps
from datetime import datetime, date, timedelta

import ssl
import ssl

from dotenv import load_dotenv
from flask import Flask, render_template, send_file, request, jsonify, url_for, flash, redirect, session
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, or_, and_, inspect, text

from recurring_detection import detect_recurring_transactions, create_recurring_expense_from_detection
from oidc_auth import setup_oidc_config, register_oidc_routes
from oidc_user import extend_user_model
from simplefin_client import SimpleFin

from session_timeout import DemoTimeout, demo_time_limited


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
scheduler = APScheduler()
scheduler.timezone = pytz.timezone('EST') # Explicitly set scheduler to use EST
scheduler.init_app(app)

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
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


migrate = Migrate(app, db)


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
    monthly_report_enabled = db.Column(db.Boolean, default=True)     
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    timezone = db.Column(db.String(50), nullable=True, default='UTC')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password,method='pbkdf2:sha256')

    def check_password(self, password):
        try:
            return check_password_hash(self.password_hash, password)
        except ValueError:
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
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(50), default="fa-tag")  # FontAwesome icon name
    color = db.Column(db.String(20), default="#6c757d")
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    is_system = db.Column(db.Boolean, default=False)  # System categories can't be deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('categories', lazy=True))
    parent = db.relationship('Category', remote_side=[id], backref=db.backref('subcategories', lazy=True))
    expenses = db.relationship('Expense', backref=db.backref('category', lazy=True))

    def __repr__(self):
        return f"<Category: {self.name}>"

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

class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # checking, savings, credit, etc.
    institution = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id', name='fk_account_user'), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    currency_code = db.Column(db.String(3), db.ForeignKey('currencies.code', name='fk_account_currency'), nullable=True)
    last_sync = db.Column(db.DateTime, nullable=True)
    import_source = db.Column(db.String(50), nullable=True)
    # Relationships
    user = db.relationship('User', backref=db.backref('accounts', lazy=True))
    currency = db.relationship('Currency', backref=db.backref('accounts', lazy=True))
    external_id = db.Column(db.String(200), nullable=True)  # Add this line
    status = db.Column(db.String(20), nullable=True)  # Add this line too for 'active'/'inactive' status
    
    
    def __repr__(self):
        return f"<Account {self.name} ({self.type})>"



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
    tags = db.relationship('Tag', secondary=expense_tags, lazy='subquery', 
                   backref=db.backref('expenses', lazy=True))
    # Add these fields to your existing Expense class:
    currency_code = db.Column(db.String(3), db.ForeignKey('currencies.code'), nullable=True)
    original_amount = db.Column(db.Float, nullable=True) # Amount in original currency
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    currency = db.relationship('Currency', backref=db.backref('expenses', lazy=True))
    #imports
    transaction_type = db.Column(db.String(20), server_default='expense')  # 'expense', 'income', 'transfer'
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', name='fk_expense_account'), nullable=True)
    external_id = db.Column(db.String(200), nullable=True)  # For tracking external transaction IDs
    import_source = db.Column(db.String(50), nullable=True)  # 'csv', 'simplefin', 'manual'

    account = db.relationship('Account', foreign_keys=[account_id], backref=db.backref('expenses', lazy=True))

      # For transfers, we need a destination account
    destination_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', name='fk_destination_account'), nullable=True)
    destination_account = db.relationship('Account', foreign_keys=[destination_account_id], backref=db.backref('incoming_transfers', lazy=True))
    
    # Add to Expense class:
    has_category_splits = db.Column(db.Boolean, default=False)
    
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
                    import json
                    split_details = json.loads(self.split_details)
                elif isinstance(self.split_details, dict):
                    split_details = self.split_details
            except Exception as e:
                # Log the error or handle it as appropriate
                print(f"Error parsing split_details for expense {self.id}: {str(e)}")
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
            if split_details and isinstance(split_details, dict) and split_details.get('type') == 'percentage':
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
            if split_details and isinstance(split_details, dict) and split_details.get('type') in ['amount', 'custom']:
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
    
    # Relationships
    user = db.relationship('User', backref=db.backref('recurring_expenses', lazy=True))
    group = db.relationship('Group', backref=db.backref('recurring_expenses', lazy=True))
    expenses = db.relationship('Expense', backref=db.backref('recurring_source', lazy=True), 
                              foreign_keys='Expense.recurring_id')
    currency_code = db.Column(db.String(3), db.ForeignKey('currencies.code'), nullable=True)
    original_amount = db.Column(db.Float, nullable=True)  # Amount in original currency
    currency = db.relationship('Currency', backref=db.backref('recurring_expenses', lazy=True))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    category = db.relationship('Category', backref=db.backref('recurring_expenses', lazy=True))


    # Transaction type and account fields
    transaction_type = db.Column(db.String(20), default='expense')  # 'expense', 'income', 'transfer'
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', name='fk_recurring_account'), nullable=True)
    account = db.relationship('Account', foreign_keys=[account_id], backref=db.backref('recurring_expenses', lazy=True))
    
    # For transfers
    destination_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', name='fk_recurring_destination'), nullable=True)
    destination_account = db.relationship('Account', foreign_keys=[destination_account_id], 
                                         backref=db.backref('recurring_incoming_transfers', lazy=True))

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
    


class CategoryMapping(db.Model):
    __tablename__ = 'category_mappings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    keyword = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    is_regex = db.Column(db.Boolean, default=False)  # Whether the keyword is a regex pattern
    priority = db.Column(db.Integer, default=0)  # Higher priority mappings take precedence
    match_count = db.Column(db.Integer, default=0)  # How many times this mapping has been used
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('category_mappings', lazy=True))
    category = db.relationship('Category', backref=db.backref('mappings', lazy=True))
    
    def __repr__(self):
        return f"<CategoryMapping: '{self.keyword}' → {self.category.name}>"



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

        




class SimpleFin(db.Model):
    """
    Stores SimpleFin connection settings for a user
    """
    __tablename__ = 'SimpleFin'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False, unique=True)
    access_url = db.Column(db.Text, nullable=False)  # Encoded/encrypted access URL
    last_sync = db.Column(db.DateTime, nullable=True)
    enabled = db.Column(db.Boolean, default=True)
    sync_frequency = db.Column(db.String(20), default='daily')  # 'daily', 'weekly', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    temp_accounts = db.Column(db.Text, nullable=True)
    # Relationship with User
    user = db.relationship('User', backref=db.backref('SimpleFin', uselist=False, lazy=True))
    
    def __repr__(self):
        return f"<SimpleFin settings for user {self.user_id}>"


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

            
     
#--------------------
# Budget
#--------------------

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
    
    # Relationships
    user = db.relationship('User', backref=db.backref('budgets', lazy=True))
    category = db.relationship('Category', backref=db.backref('budgets', lazy=True))

    transaction_types = db.Column(db.String(100), default='expense')  # comma-separated list of types to include
    
    
    def get_current_period_dates(self):
        """Get start and end dates for the current budget period"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if self.period == 'weekly':
            # Start of the week (Monday)
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
            return start_of_week, end_of_week
            
        elif self.period == 'monthly':
            # Start of the month
            start_of_month = today.replace(day=1)
            # End of the month
            if today.month == 12:
                end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(seconds=1)
            else:
                end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(seconds=1)
            return start_of_month, end_of_month
            
        elif self.period == 'yearly':
            # Start of the year
            start_of_year = today.replace(month=1, day=1)
            # End of the year
            end_of_year = today.replace(year=today.year + 1, month=1, day=1) - timedelta(seconds=1)
            return start_of_year, end_of_year
            
        # Default to current day
        return today, today.replace(hour=23, minute=59, second=59)
    
    def calculate_spent_amount(self):
        """Calculate how much has been spent in this budget's category during the current period"""
        start_date, end_date = self.get_current_period_dates()
        
        # Base query: find all expenses in the relevant date range for this user
        from sqlalchemy import or_
        
        if self.include_subcategories:
            # If this is a parent category, include subcategories
            subcategories = Category.query.filter_by(parent_id=self.category_id).all()
            subcategory_ids = [subcat.id for subcat in subcategories]
            
            # Include the parent category itself and all subcategories
            category_filter = or_(
                Expense.category_id == self.category_id,
                Expense.category_id.in_(subcategory_ids) if subcategory_ids else False
            )
        else:
            # Only include this specific category
            category_filter = (Expense.category_id == self.category_id)
        
        # Get all expenses that match our criteria
        expenses = Expense.query.filter(
            Expense.user_id == self.user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            category_filter
        ).all()
        
        # Calculate the total spent for these expenses
        total_spent = 0.0
        
        # Process each expense to calculate the user's portion
        for expense in expenses:
            # If the expense has category splits, we need a different approach
            if expense.has_category_splits:
                # Handle category splits separately
                continue
                
            # Get the split information for this expense
            splits = expense.calculate_splits()
            
            # If the user is the payer and not in the splits, add their portion
            if expense.paid_by == self.user_id and (not expense.split_with or self.user_id not in expense.split_with.split(',')):
                total_spent += splits['payer']['amount']
            else:
                # Check if the current user is in the splits
                for split in splits['splits']:
                    if split['email'] == self.user_id:
                        total_spent += split['amount']
                        break
        
        # Handle expenses with category splits
        if self.include_subcategories:
            category_ids = [self.category_id] + [subcat.id for subcat in subcategories]
        else:
            category_ids = [self.category_id]
        
        # Find all category splits for relevant categories
        category_splits = CategorySplit.query.join(
            Expense, CategorySplit.expense_id == Expense.id
        ).filter(
            Expense.user_id == self.user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            CategorySplit.category_id.in_(category_ids)
        ).all()
        
        # Process each category split
        for cat_split in category_splits:
            expense = Expense.query.get(cat_split.expense_id)
            if not expense:
                continue
                
            # Get the split information for this expense
            splits = expense.calculate_splits()
            
            # Calculate the user's share of this category split
            if expense.paid_by == self.user_id and (not expense.split_with or self.user_id not in expense.split_with.split(',')):
                # User is the payer and not in splits - add their portion
                if expense.amount > 0:
                    user_ratio = splits['payer']['amount'] / expense.amount
                    total_spent += cat_split.amount * user_ratio
            else:
                # Check if the user is in the splits
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
                return 100  # Avoid division by zero
            percentage = (spent / self.amount) * 100
            return min(percentage, 100)  # Cap at 100%
        
    def get_status(self):
        """Return the budget status: 'under', 'approaching', 'over'"""
        percentage = self.get_progress_percentage()
        if percentage >= 100:
            return 'over'
        elif percentage >= 80:
            return 'approaching'
        else:
            return 'under'
            


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
            create_default_categories(dev_user.id)
            create_default_budgets(dev_user.id)
            print("Development user created:", DEV_USER_EMAIL)


def restrict_demo_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and demo_timeout.is_demo_user(current_user.id):
            flash('Demo users cannot access this page.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


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

def update_category_mappings(transaction_id, category_id, learn=False):
    """
    Update category mappings based on a manually categorized transaction
    If learn=True, create a new mapping based on this categorization
    """
    transaction = Expense.query.get(transaction_id)
    if not transaction or not category_id:
        return False
        
    if learn:
        # Extract a good keyword from the description
        keyword = extract_keywords(transaction.description)
        
        # Check if a similar mapping already exists
        existing = CategoryMapping.query.filter_by(
            user_id=transaction.user_id,
            keyword=keyword,
            active=True
        ).first()
        
        if existing:
            # Update the existing mapping
            existing.category_id = category_id
            existing.match_count += 1
            db.session.commit()
        else:
            # Create a new mapping
            new_mapping = CategoryMapping(
                user_id=transaction.user_id,
                keyword=keyword,
                category_id=category_id,
                match_count=1
            )
            db.session.add(new_mapping)
            db.session.commit()
        
        return True
        
    return False

def extract_keywords(description):
    """
    Extract meaningful keywords from a transaction description
    Returns the most significant word or phrase
    """
    if not description:
        return ""
        
    # Clean up description
    clean_desc = description.strip().lower()
    
    # Split into words
    words = clean_desc.split()
    
    # Remove common words that aren't useful for categorization
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'on', 'in', 'with', 'for', 'to', 'from', 'by', 'at', 'of'}
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    if not filtered_words:
        # If no good words remain, use the longest word from the original
        return max(words, key=len) if words else ""
    
    # Use the longest remaining word as the keyword
    # This is a simple approach - could be improved with more sophisticated NLP
    return max(filtered_words, key=len)



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


def create_default_category_mappings(user_id):
    """Create default category mappings for a new user"""
    # Check if user already has any mappings
    existing_mappings_count = CategoryMapping.query.filter_by(user_id=user_id).count()
    
    # Only create defaults if user has no mappings
    if existing_mappings_count > 0:
        return
    
    # Get user's categories to map to
    # We'll need to find the appropriate category IDs for the current user
    categories = {}
    
    # Find common top-level categories
    for category_name in ["Food", "Transportation", "Housing", "Shopping", "Entertainment", "Health", "Personal", "Other"]:
        category = Category.query.filter_by(
            user_id=user_id,
            name=category_name,
            parent_id=None
        ).first()
        
        if category:
            categories[category_name.lower()] = category.id
            
            # Also get subcategories
            for subcategory in category.subcategories:
                categories[subcategory.name.lower()] = subcategory.id
    
    # If we couldn't find any categories, we can't create mappings
    if not categories:
        app.logger.warning(f"Could not create default category mappings for user {user_id}: no categories found")
        return
    
    # Default mappings as (keyword, category_key, is_regex, priority)
    default_mappings = [
        # Food & Dining
        ("grocery", "groceries", False, 5),
        ("groceries", "groceries", False, 5),
        ("supermarket", "groceries", False, 5),
        ("walmart", "groceries", False, 3),
        ("target", "groceries", False, 3),
        ("costco", "groceries", False, 5),
        ("safeway", "groceries", False, 5),
        ("kroger", "groceries", False, 5),
        ("aldi", "groceries", False, 5),
        ("trader joe", "groceries", False, 5),
        ("whole foods", "groceries", False, 5),
        ("wegmans", "groceries", False, 5),
        ("publix", "groceries", False, 5),
        ("sprouts", "groceries", False, 5),
        ("sams club", "groceries", False, 5),

        # Restaurants
        ("restaurant", "restaurants", False, 5),
        ("dining", "restaurants", False, 5),
        ("takeout", "restaurants", False, 5),
        ("doordash", "restaurants", False, 5),
        ("ubereats", "restaurants", False, 5),
        ("grubhub", "restaurants", False, 5),
        ("mcdonald", "restaurants", False, 5),
        ("burger", "restaurants", False, 4),
        ("pizza", "restaurants", False, 4),
        ("chipotle", "restaurants", False, 5),
        ("panera", "restaurants", False, 5),
        ("kfc", "restaurants", False, 5),
        ("wendy's", "restaurants", False, 5),
        ("taco bell", "restaurants", False, 5),
        ("chick-fil-a", "restaurants", False, 5),
        ("five guys", "restaurants", False, 5),
        ("ihop", "restaurants", False, 5),
        ("denny's", "restaurants", False, 5),

        # Coffee shops
        ("starbucks", "coffee shops", False, 5),
        ("coffee", "coffee shops", False, 4),
        ("dunkin", "coffee shops", False, 5),
        ("peet", "coffee shops", False, 5),
        ("tim hortons", "coffee shops", False, 5),

        # Gas & Transportation
        ("gas station", "gas", False, 5),
        ("gasoline", "gas", False, 5),
        ("fuel", "gas", False, 5),
        ("chevron", "gas", False, 5),
        ("shell", "gas", False, 5),
        ("exxon", "gas", False, 5),
        ("tesla supercharger", "gas", False, 5),
        ("ev charging", "gas", False, 5),

        # Rideshare & Transit
        ("uber", "rideshare", False, 5),
        ("lyft", "rideshare", False, 5),
        ("taxi", "rideshare", False, 5),
        ("transit", "public transit", False, 5),
        ("subway", "public transit", False, 5),
        ("bus", "public transit", False, 5),
        ("train", "public transit", False, 5),
        ("amtrak", "public transit", False, 5),
        ("greyhound", "public transit", False, 5),
        ("parking", "transportation", False, 5),
        ("toll", "transportation", False, 5),
        ("bike share", "transportation", False, 5),
        ("scooter rental", "transportation", False, 5),

        # Housing & Utilities
        ("rent", "rent/mortgage", False, 5),
        ("mortgage", "rent/mortgage", False, 5),
        ("airbnb", "rent/mortgage", False, 5),
        ("vrbo", "rent/mortgage", False, 5),
        ("water bill", "utilities", False, 5),
        ("electric", "utilities", False, 5),
        ("utility", "utilities", False, 5),
        ("utilities", "utilities", False, 5),
        ("internet", "utilities", False, 5),
        ("Ngrid", "utilities", False, 5),
        ("maintenance", "home maintenance", False, 4),
        ("repair", "home maintenance", False, 4),
        ("hvac", "home maintenance", False, 5),
        ("pest control", "home maintenance", False, 5),
        ("home security", "home maintenance", False, 5),
        ("home depot", "home maintenance", False, 5),
        ("lowe's", "home maintenance", False, 5),

        # Shopping
        ("amazon", "shopping", False, 5),
        ("ebay", "shopping", False, 5),
        ("etsy", "shopping", False, 5),
        ("clothing", "clothing", False, 5),
        ("apparel", "clothing", False, 5),
        ("shoes", "clothing", False, 5),
        ("electronics", "electronics", False, 5),
        ("best buy", "electronics", False, 5),
        ("apple", "electronics", False, 5),
        ("microsoft", "electronics", False, 5),
        ("furniture", "shopping", False, 5),
        ("homegoods", "shopping", False, 5),
        ("ikea", "shopping", False, 5),
        ("tj maxx", "shopping", False, 5),
        ("marshalls", "shopping", False, 5),
        ("nordstrom", "shopping", False, 5),
        ("macys", "shopping", False, 5),
        ("zara", "shopping", False, 5),
        ("uniqlo", "shopping", False, 5),
        ("shein", "shopping", False, 5),

        # Entertainment & Subscriptions
        ("movie", "movies", False, 5),
        ("cinema", "movies", False, 5),
        ("theater", "movies", False, 5),
        ("amc", "movies", False, 5),
        ("regal", "movies", False, 5),
        ("netflix", "subscriptions", False, 5),
        ("hulu", "subscriptions", False, 5),
        ("spotify", "subscriptions", False, 5),
        ("apple music", "subscriptions", False, 5),
        ("disney+", "subscriptions", False, 5),
        ("hbo", "subscriptions", False, 5),
        ("prime video", "subscriptions", False, 5),
        ("paramount+", "subscriptions", False, 5),
        ("game", "entertainment", False, 4),
        ("playstation", "entertainment", False, 5),
        ("xbox", "entertainment", False, 5),
        ("nintendo", "entertainment", False, 5),
        ("concert", "entertainment", False, 5),
        ("festival", "entertainment", False, 5),
        ("sports ticket", "entertainment", False, 5),

        # Health & Wellness
        ("gym", "health", False, 5),
        ("fitness", "health", False, 5),
        ("doctor", "health", False, 5),
        ("dentist", "health", False, 5),
        ("hospital", "health", False, 5),
        ("pharmacy", "health", False, 5),
        ("walgreens", "health", False, 5),
        ("cvs", "health", False, 5),
        ("rite aid", "health", False, 5),
        ("vision", "health", False, 5),
        ("glasses", "health", False, 5),
        ("contacts", "health", False, 5),
        ("insurance", "health", False, 5),
    ]

    
    # Create the mappings
    for keyword, category_key, is_regex, priority in default_mappings:
        # Check if we have a matching category for this keyword
        if category_key in categories:
            category_id = categories[category_key]
            
            # Create the mapping
            mapping = CategoryMapping(
                user_id=user_id,
                keyword=keyword,
                category_id=category_id,
                is_regex=is_regex,
                priority=priority,
                match_count=0,
                active=True
            )
            
            db.session.add(mapping)
    
    # Commit all mappings at once
    try:
        db.session.commit()
        app.logger.info(f"Created default category mappings for user {user_id}")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating default category mappings: {str(e)}")

# Then modify the existing create_default_categories function to also create mappings:

def create_default_categories(user_id):
    """Create default expense categories for a new user"""
    default_categories = [
        # Housing
        {"name": "Housing", "icon": "fa-home", "color": "#3498db", "subcategories": [
            {"name": "Rent/Mortgage", "icon": "fa-building", "color": "#3498db"},
            {"name": "Utilities", "icon": "fa-bolt", "color": "#3498db"},
            {"name": "Home Maintenance", "icon": "fa-tools", "color": "#3498db"}
        ]},
        # Food
        {"name": "Food", "icon": "fa-utensils", "color": "#e74c3c", "subcategories": [
            {"name": "Groceries", "icon": "fa-shopping-basket", "color": "#e74c3c"},
            {"name": "Restaurants", "icon": "fa-hamburger", "color": "#e74c3c"},
            {"name": "Coffee Shops", "icon": "fa-coffee", "color": "#e74c3c"}
        ]},
        # Transportation
        {"name": "Transportation", "icon": "fa-car", "color": "#2ecc71", "subcategories": [
            {"name": "Gas", "icon": "fa-gas-pump", "color": "#2ecc71"},
            {"name": "Public Transit", "icon": "fa-bus", "color": "#2ecc71"},
            {"name": "Rideshare", "icon": "fa-taxi", "color": "#2ecc71"}
        ]},
        # Shopping
        {"name": "Shopping", "icon": "fa-shopping-cart", "color": "#9b59b6", "subcategories": [
            {"name": "Clothing", "icon": "fa-tshirt", "color": "#9b59b6"},
            {"name": "Electronics", "icon": "fa-laptop", "color": "#9b59b6"},
            {"name": "Gifts", "icon": "fa-gift", "color": "#9b59b6"}
        ]},
        # Entertainment
        {"name": "Entertainment", "icon": "fa-film", "color": "#f39c12", "subcategories": [
            {"name": "Movies", "icon": "fa-ticket-alt", "color": "#f39c12"},
            {"name": "Music", "icon": "fa-music", "color": "#f39c12"},
            {"name": "Subscriptions", "icon": "fa-play-circle", "color": "#f39c12"}
        ]},
        # Health
        {"name": "Health", "icon": "fa-heartbeat", "color": "#1abc9c", "subcategories": [
            {"name": "Medical", "icon": "fa-stethoscope", "color": "#1abc9c"},
            {"name": "Pharmacy", "icon": "fa-prescription-bottle", "color": "#1abc9c"},
            {"name": "Fitness", "icon": "fa-dumbbell", "color": "#1abc9c"}
        ]},
        # Personal
        {"name": "Personal", "icon": "fa-user", "color": "#34495e", "subcategories": [
            {"name": "Self-care", "icon": "fa-spa", "color": "#34495e"},
            {"name": "Education", "icon": "fa-graduation-cap", "color": "#34495e"}
        ]},
        # Other
        {"name": "Other", "icon": "fa-question-circle", "color": "#95a5a6", "is_system": True}
    ]

    for cat_data in default_categories:
        subcategories = cat_data.pop('subcategories', [])
        category = Category(user_id=user_id, **cat_data)
        db.session.add(category)
        db.session.flush()  # Get the ID without committing

        for subcat_data in subcategories:
            subcat = Category(user_id=user_id, parent_id=category.id, **subcat_data)
            db.session.add(subcat)

    db.session.commit()
    
    # Create default category mappings after creating categories
    create_default_category_mappings(user_id)

def create_default_budgets(user_id):
    """Create default budget templates for a new user, all deactivated by default"""
    from app import db, Budget, Category
    
    # Get the user's categories first
    categories = Category.query.filter_by(user_id=user_id).all()
    category_map = {}
    
    # Create a map of category types to their IDs
    for category in categories:
        if category.name == "Housing":
            category_map['housing'] = category.id
        elif category.name == "Food":
            category_map['food'] = category.id
        elif category.name == "Transportation":
            category_map['transportation'] = category.id
        elif category.name == "Entertainment":
            category_map['entertainment'] = category.id
        elif category.name == "Shopping":
            category_map['shopping'] = category.id
        elif category.name == "Health":
            category_map['health'] = category.id
        elif category.name == "Personal":
            category_map['personal'] = category.id
        elif category.name == "Other":
            category_map['other'] = category.id
    
    # Default budget templates with realistic amounts
    default_budgets = [
        {
            'name': 'Monthly Housing Budget',
            'category_type': 'housing',
            'amount': 1200,
            'period': 'monthly',
            'include_subcategories': True
        },
        {
            'name': 'Monthly Food Budget',
            'category_type': 'food',
            'amount': 600,
            'period': 'monthly',
            'include_subcategories': True
        },
        {
            'name': 'Monthly Transportation',
            'category_type': 'transportation',
            'amount': 400,
            'period': 'monthly',
            'include_subcategories': True
        },
        {
            'name': 'Monthly Entertainment',
            'category_type': 'entertainment',
            'amount': 200,
            'period': 'monthly',
            'include_subcategories': True
        },
        {
            'name': 'Monthly Shopping',
            'category_type': 'shopping',
            'amount': 300,
            'period': 'monthly',
            'include_subcategories': True
        },
        {
            'name': 'Monthly Healthcare',
            'category_type': 'health',
            'amount': 150,
            'period': 'monthly',
            'include_subcategories': True
        },
        {
            'name': 'Monthly Personal',
            'category_type': 'personal',
            'amount': 200,
            'period': 'monthly',
            'include_subcategories': True
        },
        {
            'name': 'Weekly Grocery Budget',
            'category_type': 'food',  # Will use subcategory if available
            'amount': 150,
            'period': 'weekly',
            'include_subcategories': False,
            'subcategory_name': 'Groceries'  # Try to find this subcategory
        },
        {
            'name': 'Weekly Dining Out',
            'category_type': 'food',  # Will use subcategory if available
            'amount': 75,
            'period': 'weekly',
            'include_subcategories': False,
            'subcategory_name': 'Restaurants'  # Try to find this subcategory
        },
        {
            'name': 'Monthly Subscriptions',
            'category_type': 'entertainment',  # Will use subcategory if available
            'amount': 50,
            'period': 'monthly',
            'include_subcategories': False,
            'subcategory_name': 'Subscriptions'  # Try to find this subcategory
        },
        {
            'name': 'Annual Vacation',
            'category_type': 'personal',
            'amount': 1500,
            'period': 'yearly',
            'include_subcategories': False
        }
    ]
    
    # Add budgets to database
    budgets_added = 0
    
    for budget_template in default_budgets:
        # Determine the category ID to use
        category_id = None
        cat_type = budget_template['category_type']
        
        if cat_type in category_map:
            category_id = category_map[cat_type]
            
            # Check for subcategory if specified
            if 'subcategory_name' in budget_template:
                # Find the category
                main_category = Category.query.get(category_id)
                if main_category and hasattr(main_category, 'subcategories'):
                    # Look for matching subcategory
                    for subcat in main_category.subcategories:
                        if budget_template['subcategory_name'].lower() in subcat.name.lower():
                            category_id = subcat.id
                            break
        
        # If we have a valid category, create the budget
        if category_id:
            new_budget = Budget(
                user_id=user_id,
                category_id=category_id,
                name=budget_template['name'],
                amount=budget_template['amount'],
                period=budget_template['period'],
                include_subcategories=budget_template.get('include_subcategories', True),
                start_date=datetime.utcnow(),
                is_recurring=True,
                active=False,  # Deactivated by default
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(new_budget)
            budgets_added += 1
    
    if budgets_added > 0:
        db.session.commit()
        
    return budgets_added

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
# ROUTES: DEMO
#--------------------
@app.route('/demo')
@app.route('/')
def demo_login():
    """Auto-login as demo user with session timeout"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if demo mode is enabled
    if not os.getenv('DEMO_MODE', 'False').lower() == 'true':
        # If demo mode is not enabled, use default route
        return home()
    
    # Get demo timeout instance
    demo_timeout = app.extensions.get('demo_timeout')
    
    # Check concurrent session limit
    max_sessions = int(os.getenv('MAX_CONCURRENT_DEMO_SESSIONS', 5))
    current_sessions = demo_timeout.get_active_demo_sessions()  # Remove 'if demo_timeout else 0'
    
    if current_sessions >= max_sessions:
        flash(f'Maximum number of demo sessions ({max_sessions}) has been reached. Please try again later.')
        return redirect(url_for('demo_max_users'))
    
    # Find or create demo user
    demo_user = User.query.filter_by(id='demo@example.com').first()
    if not demo_user:
        logger.info("Creating new demo user")
        demo_user = User(
            id='demo@example.com',
            name='Demo User',
            is_admin=False
        )
        demo_user.set_password('demo')
        db.session.add(demo_user)
        db.session.commit()
    else:
        logger.info("Using existing demo user")
    
    # Try to register the demo session
    if not demo_timeout.register_demo_session(demo_user.id):
        flash(f'Maximum number of demo sessions ({max_sessions}) has been reached. Please try again later.')
        return redirect(url_for('login'))
    
    # Always reset demo data for each new session
    logger.info("Resetting demo data for new session")
    reset_demo_data(demo_user.id)
    
    # Create demo data
    result = create_demo_data(demo_user.id)
    logger.info(f"Demo data creation result: {result}")
    
    # Login as demo user
    login_user(demo_user)
    
    # Set demo start time and expiry time
    demo_timeout_minutes = int(os.getenv('DEMO_TIMEOUT_MINUTES', 10))
    session['demo_start_time'] = datetime.utcnow().timestamp()
    session['demo_expiry_time'] = (datetime.utcnow() + timedelta(minutes=demo_timeout_minutes)).timestamp()
    
    flash(f'Welcome to the demo! Your session will expire in {demo_timeout_minutes} minutes.')
    
    return redirect(url_for('dashboard'))

@app.route('/demo_max_users')
def demo_max_users():
    return render_template('demo/demo_concurrent.html')

@app.route('/demo_expired')
def demo_expired():
    """Handle expired demo sessions"""
    return render_template('demo/demo_expired.html')

@app.route('/demo-thanks')
def demo_thanks():
    """Page to thank users after demo session"""
    return render_template('demo/demo_thanks.html')

# Demo data creation function
def create_demo_data(user_id):
    """Create comprehensive sample data for demo users with proper checking"""
    from datetime import datetime, timedelta
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting demo data creation for user {user_id}")
    
    # First create default categories
    create_default_categories(user_id)
    db.session.flush()
    
    # Check if demo data already exists
    existing_accounts = Account.query.filter_by(user_id=user_id).all()
    if existing_accounts:
        logger.info(f"Found {len(existing_accounts)} existing accounts for user {user_id}")
        # We'll still continue to create any missing data
    
    # Create sample accounts if they don't exist
    checking = Account.query.filter_by(name="Demo Checking", user_id=user_id).first()
    if not checking:
        logger.info("Creating demo checking account")
        checking = Account(
            name="Demo Checking",
            type="checking",
            institution="Demo Bank",
            balance=2543.87,
            user_id=user_id,
            currency_code="USD"
        )
        db.session.add(checking)
    
    savings = Account.query.filter_by(name="Demo Savings", user_id=user_id).first()
    if not savings:
        logger.info("Creating demo savings account")
        savings = Account(
            name="Demo Savings",
            type="savings",
            institution="Demo Bank",
            balance=8750.25,
            user_id=user_id,
            currency_code="USD"
        )
        db.session.add(savings)
    
    credit = Account.query.filter_by(name="Demo Credit Card", user_id=user_id).first()
    if not credit:
        logger.info("Creating demo credit card account")
        credit = Account(
            name="Demo Credit Card",
            type="credit",
            institution="Demo Bank",
            balance=-1250.30,
            user_id=user_id,
            currency_code="USD"
        )
        db.session.add(credit)
    
    investment = Account.query.filter_by(name="Demo Investment", user_id=user_id).first()
    if not investment:
        logger.info("Creating demo investment account")
        investment = Account(
            name="Demo Investment",
            type="investment",
            institution="Vanguard",
            balance=15000.00,
            user_id=user_id,
            currency_code="USD"
        )
        db.session.add(investment)
    
    db.session.flush()
    
    # Get categories
    food_category = Category.query.filter_by(name="Food", user_id=user_id).first()
    housing_category = Category.query.filter_by(name="Housing", user_id=user_id).first()
    transportation_category = Category.query.filter_by(name="Transportation", user_id=user_id).first()
    entertainment_category = Category.query.filter_by(name="Entertainment", user_id=user_id).first()
    
    # Create sample transactions if they don't exist
    # 1. Regular expenses
    if not Expense.query.filter_by(description="Grocery shopping", user_id=user_id).first():
        logger.info("Creating demo grocery expense")
        expense1 = Expense(
            description="Grocery shopping",
            amount=125.75,
            date=datetime.utcnow(),
            card_used="Demo Credit Card",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=food_category.id if food_category else None,
            split_with=None,
            group_id=None,
            account_id=credit.id,
            transaction_type="expense"
        )
        db.session.add(expense1)
    
    if not Expense.query.filter_by(description="Monthly rent", user_id=user_id).first():
        logger.info("Creating demo rent expense")
        expense2 = Expense(
            description="Monthly rent",
            amount=1200.00,
            date=datetime.utcnow() - timedelta(days=7),
            card_used="Demo Checking",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=housing_category.id if housing_category else None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            transaction_type="expense"
        )
        db.session.add(expense2)
    
    # 2. Income transactions
    if not Expense.query.filter_by(description="Salary deposit", user_id=user_id).first():
        logger.info("Creating demo salary income")
        income1 = Expense(
            description="Salary deposit",
            amount=3500.00,
            date=datetime.utcnow() - timedelta(days=15),
            card_used="Direct Deposit",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            transaction_type="income"
        )
        db.session.add(income1)
    
    if not Expense.query.filter_by(description="Side gig payment", user_id=user_id).first():
        logger.info("Creating demo side income")
        income2 = Expense(
            description="Side gig payment",
            amount=250.00,
            date=datetime.utcnow() - timedelta(days=8),
            card_used="PayPal",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            transaction_type="income"
        )
        db.session.add(income2)
    

    # Add expenses with category splits
    if not Expense.query.filter_by(description="Shopping trip (mixed)", user_id=user_id).first():
        logger.info("Creating demo category split expense - shopping")
        
        # Get additional categories
        shopping_category = Category.query.filter_by(name="Shopping", user_id=user_id).first()
        personal_category = Category.query.filter_by(name="Personal", user_id=user_id).first()
        
        # Create the main expense with has_category_splits=True
        split_expense1 = Expense(
            description="Shopping trip (mixed)",
            amount=183.50,
            date=datetime.utcnow() - timedelta(days=3),
            card_used="Demo Credit Card",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,  # No main category when using splits
            split_with=None,
            group_id=None,
            account_id=credit.id,
            transaction_type="expense",
            has_category_splits=True  # This is the key flag
        )
        db.session.add(split_expense1)
        db.session.flush()  # Get the expense ID
        
        # Add category splits
        if shopping_category:
            cat_split1 = CategorySplit(
                expense_id=split_expense1.id,
                category_id=shopping_category.id,
                amount=120.00,
                description="Clothing items"
            )
            db.session.add(cat_split1)
        
        if food_category:
            cat_split2 = CategorySplit(
                expense_id=split_expense1.id,
                category_id=food_category.id,
                amount=38.50,
                description="Groceries"
            )
            db.session.add(cat_split2)
        
        if personal_category:
            cat_split3 = CategorySplit(
                expense_id=split_expense1.id,
                category_id=personal_category.id,
                amount=25.00,
                description="Personal care items"
            )
            db.session.add(cat_split3)

# Add another split expense example - travel related
    if not Expense.query.filter_by(description="Weekend trip expenses", user_id=user_id).first():
        logger.info("Creating demo category split expense - travel")
        
        # Create the main expense
        split_expense2 = Expense(
            description="Weekend trip expenses",
            amount=342.75,
            date=datetime.utcnow() - timedelta(days=14),
            card_used="Demo Credit Card",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=credit.id,
            transaction_type="expense",
            has_category_splits=True
        )
        db.session.add(split_expense2)
        db.session.flush()
        
        # Add category splits - assuming we have transportation and entertainment categories
        if transportation_category:
            cat_split4 = CategorySplit(
                expense_id=split_expense2.id,
                category_id=transportation_category.id,
                amount=95.50,
                description="Gas and tolls"
            )
            db.session.add(cat_split4)
        
        if food_category:
            cat_split5 = CategorySplit(
                expense_id=split_expense2.id,
                category_id=food_category.id,
                amount=127.25,
                description="Dining out"
            )
            db.session.add(cat_split5)
        
        if entertainment_category:
            cat_split6 = CategorySplit(
                expense_id=split_expense2.id,
                category_id=entertainment_category.id,
                amount=120.00,
                description="Activities and entertainment"
            )
            db.session.add(cat_split6)
    
    # 3. Transfers between accounts
    if not Expense.query.filter_by(description="Transfer to savings", user_id=user_id).first():
        logger.info("Creating demo transfer to savings")
        transfer1 = Expense(
            description="Transfer to savings",
            amount=500.00,
            date=datetime.utcnow() - timedelta(days=10),
            card_used="Internal Transfer",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            destination_account_id=savings.id,
            transaction_type="transfer"
        )
        db.session.add(transfer1)
    
    if not Expense.query.filter_by(description="Credit card payment", user_id=user_id).first():
        logger.info("Creating demo credit card payment")
        transfer2 = Expense(
            description="Credit card payment",
            amount=750.00,
            date=datetime.utcnow() - timedelta(days=12),
            card_used="Internal Transfer",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            destination_account_id=credit.id,
            transaction_type="transfer"
        )
        db.session.add(transfer2)
    
    if not Expense.query.filter_by(description="Investment contribution", user_id=user_id).first():
        logger.info("Creating demo investment transfer")
        transfer3 = Expense(
            description="Investment contribution",
            amount=1000.00,
            date=datetime.utcnow() - timedelta(days=20),
            card_used="Internal Transfer",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            destination_account_id=investment.id,
            transaction_type="transfer"
        )
        db.session.add(transfer3)
    
    # 4. Create recurring expenses
    netflix_recurring = RecurringExpense.query.filter_by(
        description="Netflix Subscription", user_id=user_id).first()
    if not netflix_recurring:
        logger.info("Creating demo Netflix recurring expense")
        recurring1 = RecurringExpense(
            description="Netflix Subscription",
            amount=14.99,
            card_used="Demo Credit Card",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=entertainment_category.id if entertainment_category else None,
            frequency="monthly",
            start_date=datetime.utcnow() - timedelta(days=30),
            active=True,
            account_id=credit.id
        )
        db.session.add(recurring1)
    
    rent_recurring = RecurringExpense.query.filter_by(
        description="Monthly Rent Payment", user_id=user_id).first()
    if not rent_recurring:
        logger.info("Creating demo rent recurring expense")
        recurring2 = RecurringExpense(
            description="Monthly Rent Payment",
            amount=1200.00,
            card_used="Demo Checking",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=housing_category.id if housing_category else None,
            frequency="monthly",
            start_date=datetime.utcnow() - timedelta(days=15),
            active=True,
            account_id=checking.id
        )
        db.session.add(recurring2)
    
    # 5. Create budgets
    food_budget = Budget.query.filter_by(
        name="Monthly Food", user_id=user_id).first()
    if not food_budget:
        logger.info("Creating demo food budget")
        budget1 = Budget(
            user_id=user_id,
            category_id=food_category.id if food_category else None,
            name="Monthly Food",
            amount=600.00,
            period="monthly",
            include_subcategories=True,
            start_date=datetime.utcnow().replace(day=1),
            is_recurring=True,
            active=True
        )
        db.session.add(budget1)
    
    transport_budget = Budget.query.filter_by(
        name="Transportation Budget", user_id=user_id).first()
    if not transport_budget:
        logger.info("Creating demo transportation budget")
        budget2 = Budget(
            user_id=user_id,
            category_id=transportation_category.id if transportation_category else None,
            name="Transportation Budget",
            amount=300.00,
            period="monthly",
            include_subcategories=True,
            start_date=datetime.utcnow().replace(day=1),
            is_recurring=True,
            active=True
        )
        db.session.add(budget2)
    
    entertainment_budget = Budget.query.filter_by(
        name="Entertainment Budget", user_id=user_id).first()
    if not entertainment_budget:
        logger.info("Creating demo entertainment budget")
        budget3 = Budget(
            user_id=user_id,
            category_id=entertainment_category.id if entertainment_category else None,
            name="Entertainment Budget",
            amount=200.00,
            period="monthly",
            include_subcategories=True,
            start_date=datetime.utcnow().replace(day=1),
            is_recurring=True,
            active=True
        )
        db.session.add(budget3)
    
    # Commit all changes
    try:
        db.session.commit()
        logger.info("Demo data created/updated successfully")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating demo data: {str(e)}")
        return False
    
def reset_demo_data(user_id):
    """Reset all demo data for a user with comprehensive relationship handling"""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Resetting demo data for user {user_id}")
    
    try:
        # Start a transaction
        db.session.begin()
        
        # 1. Get all expenses for this user
        expenses = Expense.query.filter_by(user_id=user_id).all()
        expense_ids = [expense.id for expense in expenses]
        
        # 2. Delete category splits referencing these expenses
        if expense_ids:
            split_count = CategorySplit.query.filter(CategorySplit.expense_id.in_(expense_ids)).delete(synchronize_session=False)
            logger.info(f"Deleted {split_count} category splits")
            
        # 3. Delete tags associations for these expenses
        if expense_ids:
            from sqlalchemy import text
            db.session.execute(text("""
                DELETE FROM expense_tags 
                WHERE expense_id IN :expense_ids
            """), {'expense_ids': tuple(expense_ids) if len(expense_ids) > 1 else f"({expense_ids[0]})"})
            logger.info(f"Deleted expense tag associations")
        
        # 4. Now delete expenses
        expense_count = Expense.query.filter_by(user_id=user_id).delete()
        logger.info(f"Deleted {expense_count} expenses")
        
        # 5. Delete recurring expenses
        recurring_count = RecurringExpense.query.filter_by(user_id=user_id).delete()
        logger.info(f"Deleted {recurring_count} recurring expenses")
        
        # 6. Delete budgets
        budget_count = Budget.query.filter_by(user_id=user_id).delete()
        logger.info(f"Deleted {budget_count} budgets")
        
        # 7. Delete category mappings
        mapping_count = CategoryMapping.query.filter_by(user_id=user_id).delete()
        logger.info(f"Deleted {mapping_count} category mappings")
        
        # 8. Delete ignored patterns
        pattern_count = IgnoredRecurringPattern.query.filter_by(user_id=user_id).delete()
        logger.info(f"Deleted {pattern_count} ignored patterns")
        
        # 9. Delete SimpleFin settings
        simplefin_count = SimpleFin.query.filter_by(user_id=user_id).delete()
        logger.info(f"Deleted {simplefin_count} SimpleFin settings")
        
        # 10. Delete settlements
        from sqlalchemy import or_
        settlement_count = Settlement.query.filter(
            or_(Settlement.payer_id == user_id, Settlement.receiver_id == user_id)
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {settlement_count} settlements")
        
        # 11. Delete all accounts
        account_count = Account.query.filter_by(user_id=user_id).delete()
        logger.info(f"Deleted {account_count} accounts")
        
        # 12. Delete all tags
        tag_count = Tag.query.filter_by(user_id=user_id).delete()
        logger.info(f"Deleted {tag_count} tags")
        
        # 13. Delete all categories
        category_count = Category.query.filter_by(user_id=user_id).delete()
        logger.info(f"Deleted {category_count} categories")
        
        # Commit the transaction
        db.session.commit()
        logger.info("Demo data reset successful")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting demo data: {str(e)}")
        return False



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
        create_default_categories(user.id)
        create_default_budgets(user.id)
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
@restrict_demo_access
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

            if app.config.get('SIMPLEFIN_ENABLED', False):
                try:
                    # Check if user has SimpleFin connection
                    simplefin_settings = SimpleFin.query.filter_by(
                        user_id=user.id, 
                        enabled=True
                    ).first()
                    
                    if simplefin_settings:
                        # Check if last sync was more than 6 hours ago (or never)
                        if not simplefin_settings.last_sync or (datetime.utcnow() - simplefin_settings.last_sync).total_seconds() > 6 * 3600:
                            # Start sync in background thread to avoid slowing down login
                            import threading
                            sync_thread = threading.Thread(
                                target=sync_simplefin_for_user,
                                args=(user.id,)
                            )
                            sync_thread.daemon = True
                            sync_thread.start()
                            
                            # Let user know syncing is happening
                            flash('Your financial accounts are being synchronized in the background.')
                except Exception as e:
                    app.logger.error(f"Error checking SimpleFin sync status: {str(e)}")
                    # Don't show error to user to keep login smooth

            import threading
            detection_thread = threading.Thread(
                target=detect_recurring_transactions,
                args=(user.id,)
            )
            detection_thread.daemon = True
            detection_thread.start()

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
    # If this is a demo user, handle demo-specific logout
    demo_timeout = app.extensions.get('demo_timeout')
    is_demo_user = False
    
    if (demo_timeout and 
        current_user.is_authenticated and 
        demo_timeout.is_demo_user(current_user.id)):
        # Unregister the demo session
        demo_timeout.unregister_demo_session(current_user.id)
        
        # Reset demo data
        reset_demo_data(current_user.id)
        
        # Mark as demo user for redirection
        is_demo_user = True
    
    # If user was logged in via OIDC, use the OIDC logout route
    if hasattr(current_user, 'oidc_id') and current_user.oidc_id and app.config.get('OIDC_ENABLED', False):
        return redirect(url_for('logout_oidc'))
    
    # Standard logout for local accounts
    logout_user()
    
    # Set a flag to show logout message on next login
    session['show_logout_message'] = True
    
    # Redirect demo users to thank you page
    if is_demo_user:
        return redirect(url_for('demo_thanks'))
    
    return redirect(url_for('login'))








#--------------------
# ROUTES: DASHBOARD
#--------------------
@app.route('/dashboard')
@login_required_dev
@demo_time_limited
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
                    'by_account': {}  # New: track by account
                }
            
            # Add to total - MODIFIED: Only add expenses, not income or transfers
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
    total_expenses_only = 0  # NEW: For expenses only
    # Add these calculations for income and transfers
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
    
    # Calculate derived metrics
    net_cash_flow = total_income - total_expenses_only
    
    # Calculate savings rate if income is not zero
    if total_income > 0:
        savings_rate = (net_cash_flow / total_income) * 100
    else:
        savings_rate = 0
    for expense in expenses:
        # Skip if not in current year
        if expense.date.year != current_year:
            continue
        
        # NEW: Check if it's an expense
        is_expense = not hasattr(expense, 'transaction_type') or expense.transaction_type == 'expense'
            
        splits = expense_splits[expense.id]
        
        if expense.paid_by == current_user.id:
            # If user paid, add their own portion
            total_expenses += splits['payer']['amount']
            if is_expense:
                total_expenses_only += splits['payer']['amount']
            
            # Also add what others owe them (the entire expense)
            for split in splits['splits']:
                total_expenses += split['amount']
                if is_expense:
                    total_expenses_only += split['amount']
        else:
            # If someone else paid, add only this user's portion
            for split in splits['splits']:
                if split['email'] == current_user.id:
                    total_expenses += split['amount']
                    if is_expense:
                        total_expenses_only += split['amount']
                    break
        
    # Calculate current month's total for the current user
    current_month_total = 0
    current_month_expenses_only = 0  # NEW: For expenses only
    current_month = now.strftime('%Y-%m')
    
    for expense in expenses:
        # Skip if not in current month
        if expense.date.strftime('%Y-%m') != current_month:
            continue
            
        # NEW: Check if it's an expense
        is_expense = not hasattr(expense, 'transaction_type') or expense.transaction_type == 'expense'
            
        splits = expense_splits[expense.id]
        
        if expense.paid_by == current_user.id:
            # If user paid, add their own portion
            current_month_total += splits['payer']['amount']
            if is_expense:
                current_month_expenses_only += splits['payer']['amount']
            
            # Also add what others owe them (the entire expense)
            for split in splits['splits']:
                current_month_total += split['amount']
                if is_expense:
                    current_month_expenses_only += split['amount']
        else:
            # If someone else paid, add only this user's portion
            for split in splits['splits']:
                if split['email'] == current_user.id:
                    current_month_total += split['amount']
                    if is_expense:
                        current_month_expenses_only += split['amount']
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

    budget_summary = get_budget_summary()

    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    currencies = Currency.query.all()
    

    # Calculate asset and debt trends
    asset_debt_trends = calculate_asset_debt_trends(current_user)

    base_currency = get_base_currency()

    return render_template('dashboard.html', 
                         expenses=expenses,
                         expense_splits=expense_splits,
                         top_categories = get_category_spending(expenses, expense_splits),
                         monthly_totals=monthly_totals,
                         total_expenses=total_expenses,
                         total_expenses_only=total_expenses_only,  # NEW: For expenses only
                         current_month_total=current_month_total,
                         current_month_expenses_only=current_month_expenses_only,  # NEW: For expenses only
                         unique_cards=unique_cards,
                         users=users,
                         groups=groups,
                         iou_data=iou_data,
                         base_currency=base_currency,
                         budget_summary=budget_summary,
                         currencies=currencies,
                         categories=categories,
                         monthly_labels=monthly_labels,
                         monthly_amounts=monthly_amounts,
                         total_income=total_income,
                         total_transfers=total_transfers,
                         net_cash_flow=net_cash_flow,
                         savings_rate=savings_rate,
                         asset_trends_months=asset_debt_trends['months'],
                         asset_trends=asset_debt_trends['assets'],
                         debt_trends=asset_debt_trends['debts'],
                         total_assets=asset_debt_trends['total_assets'],
                         total_debts=asset_debt_trends['total_debts'],
                         net_worth=asset_debt_trends['net_worth'],
                         now=now)

from datetime import datetime

def get_category_spending(expenses, expense_splits):
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
        
        # Handle regular category if no splits
        elif expense.category:
            category_name = expense.category.name
            if category_name not in category_totals:
                category_totals[category_name] = {
                    'amount': 0,
                    'color': expense.category.color,
                    'icon': expense.category.icon
                }
            category_totals[category_name]['amount'] += expense.amount
    
    # Sort and return top categories
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
    )[:6]
    
    return sorted_categories

#--------------------
# ROUTES: timezone MANAGEMENT
#--------------------
@app.route('/update_timezone', methods=['POST'])
@login_required_dev
def update_timezone():
    """Update user's timezone preference"""
    timezone = request.form.get('timezone')
    
    # Validate timezone
    if timezone not in pytz.all_timezones:
        flash('Invalid timezone selected.')
        return redirect(url_for('profile'))
    
    # Update user's timezone
    current_user.timezone = timezone
    db.session.commit()
    
    flash('Timezone updated successfully.')
    return redirect(url_for('profile'))

# Utility functions for timezone handling
def get_user_timezone(user):
    """Get user's timezone, defaulting to UTC"""
    return pytz.timezone(user.timezone or 'UTC')

def localize_datetime(dt, user):
    """Convert datetime to user's local timezone"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    user_tz = get_user_timezone(user)
    return dt.astimezone(user_tz)

# Context processor for timezone-aware datetime formatting
@app.context_processor
def timezone_processor():
    def format_datetime(dt, format='medium'):
        """Format datetime in user's local timezone"""
        if not dt:
            return ''
        
        # Ensure dt is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        
        # Convert to user's timezone
        if current_user.is_authenticated:
            user_tz = pytz.timezone(current_user.timezone or 'UTC')
            local_dt = dt.astimezone(user_tz)
        else:
            local_dt = dt
        
        # Format based on preference
        if format == 'short':
            return local_dt.strftime('%Y-%m-%d')
        elif format == 'medium':
            return local_dt.strftime('%Y-%m-%d %H:%M')
        elif format == 'long':
            return local_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
        
        return local_dt
    
    return {
        'format_datetime': format_datetime
    }
#--------------------
# ROUTES: EXPENSES MANAGEMENT
#--------------------
# In app.py, modify the add_expense route to properly handle empty category_id:

@app.route('/add_expense', methods=['POST'])
@login_required_dev
def add_expense():
    """Add a new transaction (expense, income, or transfer)"""
    if request.method == 'POST':
        try:
            # Get transaction type
            transaction_type = request.form.get('transaction_type', 'expense')
            
            # Check if this is a personal expense (no splits)
            is_personal_expense = request.form.get('personal_expense') == 'on'
            
            # Handle split_with based on whether it's a personal expense or non-expense transaction
            if is_personal_expense or transaction_type in ['income', 'transfer']:
                # For personal expenses and non-expense transactions, we set split_with to empty
                split_with_str = None
            else:
                # Handle multi-select for split_with
                split_with_ids = request.form.getlist('split_with')
                if not split_with_ids and transaction_type == 'expense':
                    flash('Please select at least one person to split with or mark as personal expense.')
                    return redirect(url_for('transactions'))
                
                split_with_str = ','.join(split_with_ids) if split_with_ids else None
            
            # Parse date with error handling
            try:
                expense_date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD format.')
                return redirect(url_for('transactions'))
            
            # Carefully process split details
            split_details = None
            split_method = 'equal'  # Default
            
            # Check for custom split details
            raw_split_details = request.form.get('split_details')
            if raw_split_details:
                try:
                    # Parse the JSON split details
                    parsed_split_details = json.loads(raw_split_details)
                    
                    # Validate the split details structure
                    if isinstance(parsed_split_details, dict):
                        split_method = parsed_split_details.get('type', 'equal')
                        split_details = raw_split_details
                        
                        # Additional validation for custom splits
                        if split_method != 'equal':
                            # Ensure we have valid split values
                            split_values = parsed_split_details.get('values', {})
                            if split_values and len(split_values) > 0:
                                # Override default split method if custom values exist
                                split_method = parsed_split_details['type']
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, fall back to default
                    app.logger.warning(f"Failed to parse split details: {raw_split_details}")
            
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
                flash('Currency configuration error.')
                return redirect(url_for('transactions'))
            
            # Convert original amount to base currency
            amount = original_amount * selected_currency.rate_to_base
            
            # Process category - properly handle empty strings for category_id
            category_id = request.form.get('category_id')
            if not category_id or category_id.strip() == '':
                category_id = None  # Set to None instead of empty string
            else:
                # Make sure it's an integer if provided
                category_id = int(category_id)

            # Get account information - handle empty strings
            account_id = request.form.get('account_id')
            if not account_id or account_id.strip() == '':
                account_id = None
            else:
                # Make sure it's an integer if provided
                account_id = int(account_id)
                
            card_used = "No card"  # Default fallback
            
            # For transfers, get destination account - handle empty strings
            destination_account_id = None
            if transaction_type == 'transfer':
                destination_account_id = request.form.get('destination_account_id')
                if not destination_account_id or destination_account_id.strip() == '':
                    destination_account_id = None
                else:
                    # Make sure it's an integer if provided
                    destination_account_id = int(destination_account_id)
                
                # Validate different source and destination accounts
                if account_id == destination_account_id:
                    flash('Source and destination accounts must be different for transfers.')
                    return redirect(url_for('transactions'))
            
            # Determine paid_by (use from form or fallback to current user)
            paid_by = request.form.get('paid_by', current_user.id)
            
            # Create expense record
            expense = Expense(
                description=request.form['description'],
                amount=amount,  # Amount in base currency
                original_amount=original_amount,  # Original amount in selected currency
                currency_code=currency_code,  # Store the original currency code
                date=expense_date,
                card_used=card_used,  # Default or legacy value
                split_method=split_method,  # Use the carefully parsed split method
                split_value=0,  # We'll use split_details for more complex splits
                split_details=split_details,
                paid_by=paid_by,
                user_id=current_user.id,
                category_id=category_id,
                group_id=request.form.get('group_id') if request.form.get('group_id') else None,
                split_with=split_with_str,
                transaction_type=transaction_type,
                account_id=account_id,
                destination_account_id=destination_account_id
            )
            
            db.session.add(expense)
            db.session.commit()
            
            # Determine success message based on transaction type
            if transaction_type == 'expense':
                flash('Expense added successfully!')
            elif transaction_type == 'income':
                flash('Income recorded successfully!')
            elif transaction_type == 'transfer':
                flash('Transfer completed successfully!')
            else:
                flash('Transaction added successfully!')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}')
            app.logger.error(f"Error adding expense: {str(e)}")
            
    return redirect(url_for('transactions'))

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required_dev
def delete_expense(expense_id):
    """Delete an expense by ID"""
    try:
        # Find the expense
        expense = Expense.query.get_or_404(expense_id)
        
        # Security check: Only the creator can delete the expense
        if expense.user_id != current_user.id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'You do not have permission to delete this expense'
                }), 403
            else:
                flash('You do not have permission to delete this expense')
                return redirect(url_for('transactions'))
        
        # Delete the expense
        db.session.delete(expense)
        db.session.commit()
        
        # Handle AJAX and regular requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Expense deleted successfully'
            })
        else:
            flash('Expense deleted successfully')
            return redirect(url_for('transactions'))
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting expense {expense_id}: {str(e)}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': f'Error: {str(e)}'
            }), 500
        else:
            flash(f'Error: {str(e)}')
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
    """Update an existing expense with improved category split handling"""
    try:
        # Find the expense
        expense = Expense.query.get_or_404(expense_id)
        
        # Security check
        if expense.user_id != current_user.id:
            flash('You do not have permission to edit this expense')
            return redirect(url_for('transactions'))
        
        # Log incoming data for debugging
        app.logger.info(f"Update expense request data: {request.form}")
        
        # Get the transaction type with safer fallback
        transaction_type = request.form.get('transaction_type', 'expense')
        
        # Common fields for all transaction types (with safer handling)
        expense.description = request.form.get('description', expense.description)
        
        # Handle amount safely
        try:
            expense.amount = float(request.form.get('amount', expense.amount))
        except (ValueError, TypeError):
            # Keep existing amount if conversion fails
            pass
        
        # Handle date safely
        try:
            expense.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
        except (ValueError, TypeError):
            # Keep existing date if conversion fails
            pass
        
        # Handle category splits toggle - this determines which category approach to use
        enable_category_split = request.form.get('enable_category_split') == 'on'
        expense.has_category_splits = enable_category_split
        
        if enable_category_split:
            # When using splits, the main category becomes optional
            expense.category_id = None
            
            # Clear any existing splits
            CategorySplit.query.filter_by(expense_id=expense.id).delete()
            
            # Get split data from form
            split_data = request.form.get('category_splits_data', '[]')
            
            try:
                splits = json.loads(split_data)
                
                # Create new splits
                for split in splits:
                    category_id = split.get('category_id')
                    amount = float(split.get('amount', 0))
                    
                    if category_id and amount > 0:
                        category_split = CategorySplit(
                            expense_id=expense.id,
                            category_id=category_id,
                            amount=amount
                        )
                        db.session.add(category_split)
                
                # Validate that splits add up to the total
                total_splits = sum(float(split.get('amount', 0)) for split in splits)
                if abs(total_splits - expense.amount) > 0.01:
                    app.logger.warning(f"Split total {total_splits} doesn't match expense amount {expense.amount}")
                    
            except Exception as e:
                app.logger.error(f"Error processing category splits: {str(e)}")
                # If split processing fails, disable splits and fall back to main category
                expense.has_category_splits = False
                
                # Try to use the original category
                category_id = request.form.get('category_id')
                if category_id and category_id != 'null' and category_id.strip():
                    try:
                        expense.category_id = int(category_id)
                    except ValueError:
                        expense.category_id = None
                else:
                    expense.category_id = None
        else:
            # If not using splits, just update the main category
            # Handle category_id safely (allow null values)
            category_id = request.form.get('category_id')
            if category_id == 'null' or category_id == '':
                expense.category_id = None
            elif category_id is not None:
                try:
                    expense.category_id = int(category_id)
                except ValueError:
                    # Keep existing category if conversion fails
                    app.logger.warning(f"Invalid category_id value: {category_id}")
            
            # Clear any existing splits when not using splits
            CategorySplit.query.filter_by(expense_id=expense.id).delete()
        
        # Handle account_id safely
        account_id = request.form.get('account_id')
        if account_id and account_id != 'null' and account_id != '':
            try:
                expense.account_id = int(account_id)
            except ValueError:
                app.logger.warning(f"Invalid account_id value: {account_id}")
        
        # Set transaction type
        expense.transaction_type = transaction_type
        
        # Type-specific processing
        if transaction_type == 'expense':
            # Handle personal expense flag
            is_personal_expense = request.form.get('personal_expense') == 'on'
            
            # Split with handling
            if is_personal_expense:
                expense.split_with = None
                expense.split_details = None
            else:
                # Get split_with as a list, then join to string
                split_with_list = request.form.getlist('split_with')
                expense.split_with = ','.join(split_with_list) if split_with_list else None
                
                # Process split details
                expense.split_details = request.form.get('split_details')
            
            # Other expense-specific fields
            expense.split_method = request.form.get('split_method', 'equal')
            expense.paid_by = request.form.get('paid_by', current_user.id)
            
            # Group ID handling (allow empty string to be converted to None)
            group_id = request.form.get('group_id')
            if group_id and group_id.strip():
                try:
                    expense.group_id = int(group_id)
                except ValueError:
                    expense.group_id = None
            else:
                expense.group_id = None
            
            # Clear transfer-specific fields
            expense.destination_account_id = None
            
        elif transaction_type == 'income':
            # Income has no split details
            expense.split_with = None
            expense.split_details = None
            expense.split_method = 'equal'
            expense.paid_by = current_user.id
            expense.group_id = None
            
            # Clear transfer-specific fields
            expense.destination_account_id = None
            
        elif transaction_type == 'transfer':
            # Transfer has no split details
            expense.split_with = None
            expense.split_details = None
            expense.split_method = 'equal'
            expense.paid_by = current_user.id
            expense.group_id = None
            expense.has_category_splits = False
            
            # Set transfer-specific fields - with proper handling for empty values
            destination_id = request.form.get('destination_account_id')
            if destination_id and destination_id != 'null' and destination_id.strip():
                try:
                    expense.destination_account_id = int(destination_id)
                except ValueError:
                    # If not a valid integer, set to None
                    expense.destination_account_id = None
            else:
                # If empty, set to None
                expense.destination_account_id = None
        
        # Save changes
        db.session.commit()
        flash('Transaction updated successfully!')
        
        return redirect(url_for('transactions'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating expense {expense_id}: {str(e)}")
        flash(f'Error: {str(e)}')
        
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
    name = request.form.get('name')
    color = request.form.get('color', "#6c757d")
    
    # Check if tag already exists for this user
    existing_tag = Tag.query.filter_by(user_id=current_user.id, name=name).first()
    if existing_tag:
        flash('Tag with this name already exists')
        return redirect(url_for('manage_tags'))
    
    tag = Tag(name=name, color=color, user_id=current_user.id)
    db.session.add(tag)
    db.session.commit()
    
    flash('Tag added successfully')
    return redirect(url_for('manage_tags'))

@app.route('/tags/delete/<int:tag_id>', methods=['POST'])
@login_required_dev
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    
    # Check if tag belongs to current user
    if tag.user_id != current_user.id:
        flash('You don\'t have permission to delete this tag')
        return redirect(url_for('manage_tags'))
    
    db.session.delete(tag)
    db.session.commit()
    
    flash('Tag deleted successfully')
    return redirect(url_for('manage_tags'))




#--------------------
# ROUTES: recurring
#--------------------
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
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    return render_template('recurring.html', 
                          recurring_expenses=recurring_expenses, 
                          users=users,
                          currencies=currencies,
                          base_currency=base_currency,
                          categories=categories,
                          groups=groups)

@app.route('/get_recurring_form_html')
@login_required_dev
def get_recurring_form_html():
    """Return the HTML for the add recurring transaction form"""
    base_currency = get_base_currency()
    users = User.query.all()
    groups = Group.query.join(group_users).filter(group_users.c.user_id == current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    currencies = Currency.query.all()
    
    return render_template('partials/recurring_transaction_form.html',
                          users=users,
                          groups=groups,
                          categories=categories,
                          currencies=currencies,
                          base_currency=base_currency)



@app.route('/add_recurring', methods=['POST'])
@login_required_dev
def add_recurring():
    try:
        # Get transaction type
        transaction_type = request.form.get('transaction_type', 'expense')

        # Parse dates with error handling
        try:
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = None
            if request.form.get('end_date'):
                end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD format.')
            return redirect(url_for('recurring'))
        
        # Handle account_id vs card_used transition
        account_id = request.form.get('account_id')
        card_used = "Default Card"  # Default value
        
        if account_id:
            if account_id == 'default':
                # For backward compatibility use a default card name
                card_used = "Default Card"
            else:
                # Try to get the account name to use as card_used for backward compatibility
                try:
                    account = Account.query.get(int(account_id))
                    if account:
                        card_used = account.name
                except:
                    # If account lookup fails, use a default
                    card_used = "Default Card"
        
        # Create new recurring expense with common fields
        recurring_expense = RecurringExpense(
            description=request.form['description'],
            amount=float(request.form['amount']),
            card_used=card_used,  # For backward compatibility
            frequency=request.form['frequency'],
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id,
            transaction_type=transaction_type,
            active=True
        )
        
        # Handle account_id if provided
        if account_id and account_id != 'default':
            recurring_expense.account_id = int(account_id)
        
        # Handle currency if provided
        if request.form.get('currency_code'):
            recurring_expense.currency_code = request.form.get('currency_code')
        
        # Handle transaction type specific fields
        if transaction_type == 'expense':
            # Check if this is a personal expense (no splits)
            is_personal_expense = request.form.get('personal_expense') == 'on'
            
            # Setup expense fields
            recurring_expense.paid_by = request.form['paid_by']
            recurring_expense.split_method = request.form['split_method']
            recurring_expense.split_value = float(request.form.get('split_value', 0)) if request.form.get('split_value') else 0
            
            # Handle split with based on whether it's a personal expense
            if is_personal_expense:
                recurring_expense.split_with = None
                recurring_expense.split_details = None
            else:
                # Handle multi-select for split_with
                split_with_ids = request.form.getlist('split_with')
                if not split_with_ids:
                    flash('Please select at least one person to split with or mark as personal expense.')
                    return redirect(url_for('recurring'))
                
                recurring_expense.split_with = ','.join(split_with_ids) if split_with_ids else None
                
                # Process split details if provided
                if request.form.get('split_details'):
                    recurring_expense.split_details = request.form.get('split_details')
            
            # Set group if provided
            recurring_expense.group_id = request.form.get('group_id') if request.form.get('group_id') else None
            
            # Set category if provided
            category_id = request.form.get('category_id')
            if category_id and category_id.strip():
                recurring_expense.category_id = int(category_id)
                
        elif transaction_type == 'income':
            # Income has no split details or group
            recurring_expense.paid_by = current_user.id
            recurring_expense.split_with = None
            recurring_expense.split_method = 'equal'
            recurring_expense.split_details = None
            recurring_expense.group_id = None
            
            # Set category if provided
            category_id = request.form.get('category_id')
            if category_id and category_id.strip():
                recurring_expense.category_id = int(category_id)
                
        elif transaction_type == 'transfer':
            # Transfer has no split details, group, or category
            recurring_expense.paid_by = current_user.id
            recurring_expense.split_with = None
            recurring_expense.split_method = 'equal'
            recurring_expense.split_details = None
            recurring_expense.group_id = None
            recurring_expense.category_id = None
            
            # Set destination account if provided
            dest_account_id = request.form.get('destination_account_id')
            if dest_account_id and dest_account_id.strip():
                recurring_expense.destination_account_id = int(dest_account_id)
        
        db.session.add(recurring_expense)
        db.session.commit()
        
        # Create first expense instance if the start date is today or in the past
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date <= today:
            expense = recurring_expense.create_expense_instance(start_date)
            db.session.add(expense)
            db.session.commit()
        
        flash('Recurring transaction added successfully!')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding recurring transaction: {str(e)}")
        flash(f'Error: {str(e)}')
    
    return redirect(url_for('recurring'))

@app.route('/toggle_recurring/<int:recurring_id>', methods=['POST'])
@login_required_dev
def toggle_recurring(recurring_id):
    recurring_expense = RecurringExpense.query.get_or_404(recurring_id)
    
    # Security check
    if recurring_expense.user_id != current_user.id:
        flash('You don\'t have permission to modify this recurring expense')
        return redirect(url_for('recurring'))
    
    # Toggle the active status
    recurring_expense.active = not recurring_expense.active
    db.session.commit()
    
    status = "activated" if recurring_expense.active else "deactivated"
    flash(f'Recurring expense {status} successfully')
    
    return redirect(url_for('recurring'))

@app.route('/delete_recurring/<int:recurring_id>', methods=['POST'])
@login_required_dev
def delete_recurring(recurring_id):
    recurring_expense = RecurringExpense.query.get_or_404(recurring_id)
    
    # Security check
    if recurring_expense.user_id != current_user.id:
        flash('You don\'t have permission to delete this recurring expense')
        return redirect(url_for('recurring'))
    
    db.session.delete(recurring_expense)
    db.session.commit()
    
    flash('Recurring expense deleted successfully')
    
    return redirect(url_for('recurring'))

@app.route('/edit_recurring/<int:recurring_id>')
@login_required_dev
def edit_recurring_page(recurring_id):
    """Load the recurring expenses page with form pre-filled for editing"""
    # Find the recurring expense
    recurring = RecurringExpense.query.get_or_404(recurring_id)
    
    # Security check: Only the creator can edit
    if recurring.user_id != current_user.id:
        flash('You do not have permission to edit this recurring expense')
        return redirect(url_for('recurring'))
    
    # Prepare the same data needed for the recurring page
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
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    
    # Return the template with the recurring expense data and flags for edit mode
    return render_template('recurring.html', 
                          recurring_expenses=recurring_expenses, 
                          users=users,
                          currencies=currencies,
                          base_currency=base_currency,
                          groups=groups,
                          categories=categories,
                          edit_recurring=recurring,  # Pass the recurring expense to edit
                          auto_open_form=True)       # Flag to auto-open the form

@app.route('/update_recurring/<int:recurring_id>', methods=['POST'])
@login_required_dev
def update_recurring(recurring_id):
    """Update an existing recurring transaction"""
    try:
        # Find the recurring transaction
        recurring = RecurringExpense.query.get_or_404(recurring_id)
        
        # Security check: Only the creator can update
        if recurring.user_id != current_user.id:
            flash('You do not have permission to edit this recurring transaction')
            return redirect(url_for('recurring'))
        
        # Get transaction type
        transaction_type = request.form.get('transaction_type', 'expense')
        
        # Parse dates
        try:
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = None
            if request.form.get('end_date'):
                end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD format.')
            return redirect(url_for('recurring'))
        
        # Update basic fields for all transaction types
        recurring.description = request.form['description']
        recurring.amount = float(request.form['amount'])
        recurring.frequency = request.form['frequency']
        recurring.start_date = start_date
        recurring.end_date = end_date
        recurring.transaction_type = transaction_type
        
        # Handle account based on transaction type
        account_id = request.form.get('account_id')
        if account_id:
            if account_id == 'default':
                # Keep the existing card_used value
                pass
            else:
                # Try to get the account name for backward compatibility
                try:
                    account = Account.query.get(int(account_id))
                    if account:
                        recurring.card_used = account.name
                        recurring.account_id = int(account_id)
                except:
                    # Fallback - don't change card_used
                    pass
        
        # Handle currency if provided
        if request.form.get('currency_code'):
            recurring.currency_code = request.form.get('currency_code')
        
        # Handle fields based on transaction type
        if transaction_type == 'expense':
            # Handle expense-specific fields
            recurring.paid_by = request.form['paid_by']
            
            # Handle split with
            is_personal_expense = request.form.get('personal_expense') == 'on'
            if is_personal_expense:
                recurring.split_with = None
                recurring.split_details = None
            else:
                split_with_ids = request.form.getlist('split_with')
                recurring.split_with = ','.join(split_with_ids) if split_with_ids else None
                
                # Process split details
                recurring.split_method = request.form['split_method']
                if request.form.get('split_details'):
                    recurring.split_details = request.form.get('split_details')
            
            # Handle group 
            recurring.group_id = request.form.get('group_id') if request.form.get('group_id') and request.form.get('group_id') != '' else None
            
            # Handle category
            category_id = request.form.get('category_id')
            if category_id and category_id.strip():
                recurring.category_id = int(category_id)
            else:
                recurring.category_id = None
                
            # Clear transfer-specific fields
            recurring.destination_account_id = None
            
        elif transaction_type == 'income':
            # Income doesn't use split fields
            recurring.paid_by = current_user.id
            recurring.split_with = None
            recurring.split_details = None
            recurring.split_method = 'equal'
            recurring.group_id = None
            
            # Handle category
            category_id = request.form.get('category_id')
            if category_id and category_id.strip():
                recurring.category_id = int(category_id)
            else:
                recurring.category_id = None
                
            # Clear transfer-specific fields
            recurring.destination_account_id = None
            
        elif transaction_type == 'transfer':
            # Transfer doesn't use split or category fields
            recurring.paid_by = current_user.id
            recurring.split_with = None
            recurring.split_details = None
            recurring.split_method = 'equal'
            recurring.group_id = None
            recurring.category_id = None
            
            # Handle destination account
            dest_account_id = request.form.get('destination_account_id')
            if dest_account_id and dest_account_id.strip():
                recurring.destination_account_id = int(dest_account_id)
            else:
                recurring.destination_account_id = None
        
        # Save changes
        db.session.commit()
        flash('Recurring transaction updated successfully!')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating recurring transaction {recurring_id}: {str(e)}")
        flash(f'Error: {str(e)}')
        
    return redirect(url_for('recurring'))



@app.route('/detect_recurring_transactions')
@login_required_dev
def get_recurring_transactions():
    """API endpoint to detect recurring transactions for the current user"""
    try:
        # Default to 60 days lookback and 2 min occurrences
        lookback_days = int(request.args.get('lookback_days', 60))
        min_occurrences = int(request.args.get('min_occurrences', 2))
        
        # Detect recurring transactions
        candidates = detect_recurring_transactions(
            current_user.id, 
            lookback_days=lookback_days,
            min_occurrences=min_occurrences
        )
        
        # Get base currency symbol for formatting
        base_currency = get_base_currency()
        currency_symbol = base_currency['symbol'] if isinstance(base_currency, dict) else base_currency.symbol
        
        # Get all ignored patterns for this user
        ignored_patterns = IgnoredRecurringPattern.query.filter_by(user_id=current_user.id).all()
        ignored_keys = [pattern.pattern_key for pattern in ignored_patterns]
        
        # Prepare response data
        candidate_data = []
        for candidate in candidates:
            # Create a unique pattern key for this candidate
            pattern_key = f"{candidate['description']}_{candidate['amount']}_{candidate['frequency']}"
            
            # Skip if this pattern is in the ignored list
            if pattern_key in ignored_keys:
                continue
                
            # Create a candidate ID that's stable across requests
            candidate_id = f"candidate_{hash(pattern_key) & 0xffffffff}"
                
            # Create a serializable version of the candidate
            candidate_dict = {
                'id': candidate_id,  # Use a stable ID based on pattern
                'description': candidate['description'],
                'amount': candidate['amount'],
                'currency_code': candidate['currency_code'],
                'frequency': candidate['frequency'],
                'confidence': candidate['confidence'],
                'occurrences': candidate['occurrences'],
                'next_date': candidate['next_date'].isoformat(),
                'avg_interval': candidate['avg_interval'],
                'transaction_type': candidate['transaction_type'],
                # Include account and category info if available
                'account_id': candidate['account_id'],
                'category_id': candidate['category_id'],
                'account_name': None,
                'category_name': None
            }
            
            # Add account name if available
            if candidate['account_id']:
                account = Account.query.get(candidate['account_id'])
                if account:
                    candidate_dict['account_name'] = account.name
            
            # Add category name if available
            if candidate['category_id']:
                category = Category.query.get(candidate['category_id'])
                if category:
                    candidate_dict['category_name'] = category.name
                    candidate_dict['category_icon'] = category.icon
                    candidate_dict['category_color'] = category.color
            
            candidate_data.append(candidate_dict)
            
            # Store candidate in session for later reference
            # Use the stable candidate ID as the session key
            session_key = f'recurring_candidate_{candidate_id}'
            session[session_key] = {
                'description': candidate['description'],
                'amount': candidate['amount'],
                'currency_code': candidate['currency_code'],
                'frequency': candidate['frequency'],
                'account_id': candidate['account_id'],
                'category_id': candidate['category_id'],
                'transaction_type': candidate['transaction_type'],
                'transaction_ids': candidate['transaction_ids']
            }
        
        return jsonify({
            'success': True,
            'candidates': candidate_data,
            'currency_symbol': currency_symbol
        })
        
    except Exception as e:
        app.logger.error(f"Error detecting recurring transactions: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error detecting recurring transactions: {str(e)}'
        }), 500
@app.route('/recurring_candidate_history/<candidate_id>')
@login_required_dev
def recurring_candidate_history(candidate_id):
    """Get transaction history for a recurring candidate"""
    try:
        # Get stored candidate data from session
        session_key = f'recurring_candidate_{candidate_id}'
        candidate_data = session.get(session_key)
        
        if not candidate_data:
            return jsonify({
                'success': False,
                'message': 'Candidate details not found. Please refresh the page and try again.'
            }), 404
        
        # Get transaction IDs from the stored data
        transaction_ids = candidate_data.get('transaction_ids', [])
        
        # Get user's base currency
        base_currency = get_base_currency()
        currency_symbol = base_currency['symbol'] if isinstance(base_currency, dict) else base_currency.symbol
        
        # Fetch the actual transactions
        transactions = []
        for tx_id in transaction_ids:
            expense = Expense.query.get(tx_id)
            if expense and expense.user_id == current_user.id:
                tx_data = {
                    'id': expense.id,
                    'description': expense.description,
                    'amount': expense.amount,
                    'date': expense.date.isoformat(),
                    'account_name': expense.account.name if expense.account else None
                }
                
                # Add category information if available
                if hasattr(expense, 'category') and expense.category:
                    tx_data['category_name'] = expense.category.name
                    tx_data['category_icon'] = expense.category.icon
                    tx_data['category_color'] = expense.category.color
                
                transactions.append(tx_data)
        
        # Sort transactions by date (newest first)
        transactions.sort(key=lambda x: x['date'], reverse=True)
        
        return jsonify({
            'success': True,
            'candidate_id': candidate_id,
            'description': candidate_data['description'],
            'currency_symbol': currency_symbol,
            'transactions': transactions
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching transaction history: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching transaction history: {str(e)}'
        }), 500
@app.route('/convert_to_recurring/<candidate_id>', methods=['POST'])
@login_required_dev
def convert_to_recurring(candidate_id):
    """Convert a detected recurring transaction to a RecurringExpense"""
    from recurring_detection import create_recurring_expense_from_detection
    
    try:
        # Check if this is an edit request
        is_edit = request.args.get('edit', 'false').lower() == 'true'
        
        if is_edit:
            # If this is an edit, we're using the form data
            # Process the form data just like in add_recurring route
            
            # Extract form data
            description = request.form.get('description')
            amount = float(request.form.get('amount', 0))
            frequency = request.form.get('frequency')
            account_id = request.form.get('account_id')
            category_id = request.form.get('category_id')
            
            # Create a custom candidate data structure
            custom_candidate = {
                'description': description,
                'amount': amount,
                'frequency': frequency,
                'account_id': account_id,
                'category_id': category_id,
                'transaction_type': request.form.get('transaction_type', 'expense')  # Default
            }
            
            # Create recurring expense from custom data
            recurring = create_recurring_expense_from_detection(current_user.id, custom_candidate)
            
            # Additional fields from form
            recurring.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            if request.form.get('end_date'):
                recurring.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
            
            # Process split settings
            is_personal = request.form.get('personal_expense') == 'on'
            
            if is_personal:
                recurring.split_with = None
            else:
                split_with_ids = request.form.getlist('split_with')
                recurring.split_with = ','.join(split_with_ids) if split_with_ids else None
            
            recurring.split_method = request.form.get('split_method', 'equal')
            recurring.split_details = request.form.get('split_details')
            recurring.paid_by = request.form.get('paid_by', current_user.id)
            recurring.group_id = request.form.get('group_id') if request.form.get('group_id') else None
            
            # Save to database
            db.session.add(recurring)
            db.session.commit()
            
            # Check if this is a regular form submission or AJAX request
            if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                flash('Recurring expense created successfully!')
                return redirect(url_for('recurring'))
            
            return jsonify({
                'success': True,
                'message': 'Recurring expense created successfully!'
            })
            
        else:
            # Standard conversion (not edit)
            
            # Get candidate data from session
            session_key = f'recurring_candidate_{candidate_id}'
            candidate_data = session.get(session_key)
            
            if not candidate_data:
                return jsonify({
                    'success': False,
                    'message': 'Candidate details not found. Please refresh the page and try again.'
                }), 404
            
            # Create recurring expense from the candidate data
            recurring = create_recurring_expense_from_detection(current_user.id, candidate_data)
            
            # Set to active
            recurring.active = True
            
            # Save to database
            db.session.add(recurring)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Recurring expense created successfully!'
            })
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error converting to recurring: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/ignore_recurring_candidate/<candidate_id>', methods=['POST'])
@login_required_dev
def ignore_recurring_candidate(candidate_id):
    """Mark a recurring transaction pattern as ignored"""
    try:
        # Get candidate data from session
        session_key = f'recurring_candidate_{candidate_id}'
        candidate_data = session.get(session_key)
        
        if not candidate_data:
            return jsonify({
                'success': False,
                'message': 'Candidate details not found. Please refresh the page and try again.'
            }), 404
        
        # Create pattern key for this candidate
        pattern_key = f"{candidate_data['description']}_{candidate_data['amount']}_{candidate_data['frequency']}"
        
        # Check if already ignored
        existing = IgnoredRecurringPattern.query.filter_by(
            user_id=current_user.id,
            pattern_key=pattern_key
        ).first()
        
        if existing:
            return jsonify({
                'success': True,
                'message': 'Pattern was already ignored'
            })
        
        # Create ignored pattern record
        ignored = IgnoredRecurringPattern(
            user_id=current_user.id,
            pattern_key=pattern_key,
            description=candidate_data['description'],
            amount=candidate_data['amount'],
            frequency=candidate_data['frequency']
        )
        
        db.session.add(ignored)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pattern will no longer be detected as recurring'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error ignoring recurring candidate: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
@app.route('/restore_ignored_pattern/<int:pattern_id>', methods=['POST'])
@login_required_dev
def restore_ignored_pattern(pattern_id):
    """Restore a previously ignored recurring pattern"""
    try:
        # Find the pattern
        pattern = IgnoredRecurringPattern.query.get_or_404(pattern_id)
        
        # Security check
        if pattern.user_id != current_user.id:
            flash('You do not have permission to modify this pattern.')
            return redirect(url_for('manage_ignored_patterns'))
        
        # Delete the pattern (which effectively restores it for detection)
        db.session.delete(pattern)
        db.session.commit()
        
        flash('Pattern restored successfully. It may appear in future recurring detection results.')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error restoring pattern {pattern_id}: {str(e)}")
        flash(f'Error: {str(e)}')
    
    return redirect(url_for('manage_ignored_patterns'))
@app.route('/manage_ignored_patterns')
@login_required_dev
def manage_ignored_patterns():
    """View and manage ignored recurring transaction patterns"""
    # Get all ignored patterns for the current user
    ignored_patterns = IgnoredRecurringPattern.query.filter_by(user_id=current_user.id).order_by(
        IgnoredRecurringPattern.ignore_date.desc()
    ).all()
    
    # Get base currency for display
    base_currency = get_base_currency()
    
    return render_template('manage_ignored_patterns.html',
                          ignored_patterns=ignored_patterns,
                          base_currency=base_currency)


@app.route('/get_recurring/<int:recurring_id>')
@login_required_dev
def get_recurring(recurring_id):
    """Get recurring transaction details for editing"""
    try:
        # Find the recurring transaction
        recurring = RecurringExpense.query.get_or_404(recurring_id)
        
        # Security check: Only the creator can edit
        if recurring.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to edit this recurring transaction'
            }), 403
        
        # Process split_with into array
        split_with_ids = []
        if recurring.split_with:
            split_with_ids = recurring.split_with.split(',')
        
        # Format dates
        start_date = recurring.start_date.strftime('%Y-%m-%d') if recurring.start_date else None
        end_date = recurring.end_date.strftime('%Y-%m-%d') if recurring.end_date else None
        
        # Prepare split details if available
        split_details = None
        if recurring.split_details:
            try:
                split_details = json.loads(recurring.split_details)
            except:
                split_details = None
        
        # Return the recurring transaction data
        return jsonify({
            'success': True,
            'recurring': {
                'id': recurring.id,
                'description': recurring.description,
                'amount': recurring.amount,
                'transaction_type': recurring.transaction_type or 'expense',
                'frequency': recurring.frequency,
                'start_date': start_date,
                'end_date': end_date,
                'currency_code': recurring.currency_code,
                'account_id': recurring.account_id,
                'destination_account_id': recurring.destination_account_id,
                'paid_by': recurring.paid_by,
                'split_with': split_with_ids,
                'split_method': recurring.split_method,
                'split_details': split_details,
                'category_id': recurring.category_id,
                'group_id': recurring.group_id
            }
        })
            
    except Exception as e:
        app.logger.error(f"Error retrieving recurring transaction {recurring_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
    





@app.route('/get_category_splits/<int:expense_id>')
@login_required_dev
def get_category_splits(expense_id):
    """Get category splits for an expense"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        
        # Security check
        if expense.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to view this expense'
            }), 403
        
        if not expense.has_category_splits:
            return jsonify({
                'success': True,
                'splits': []
            })
        
        # Get all category splits for this expense
        splits = CategorySplit.query.filter_by(expense_id=expense_id).all()
        
        # Format the response
        splits_data = []
        for split in splits:
            category = Category.query.get(split.category_id)
            
            # Include category details if available
            category_data = {
                'id': category.id,
                'name': category.name,
                'icon': category.icon,
                'color': category.color
            } if category else {
                'id': None,
                'name': 'Unknown',
                'icon': 'fa-question',
                'color': '#6c757d'
            }
            
            splits_data.append({
                'id': split.id,
                'category_id': split.category_id,
                'amount': split.amount,
                'description': split.description,
                'category': category_data
            })
        
        return jsonify({
            'success': True,
            'splits': splits_data
        })
        
    except Exception as e:
        app.logger.error(f"Error getting category splits: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
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
        flash('Group created successfully!')
    except Exception as e:
        flash(f'Error creating group: {str(e)}')
    
    return redirect(url_for('groups'))

@app.route('/groups/<int:group_id>')
@login_required_dev
def group_details(group_id):
    base_currency = get_base_currency()
    group = Group.query.get_or_404(group_id)

    # Check if user is member of group
    if current_user not in group.members:
        flash('Access denied. You are not a member of this group.')
        return redirect(url_for('groups'))
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    
    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.date.desc()).all()
    all_users = User.query.all()
    currencies = Currency.query.all()
    return render_template('group_details.html', 
                           group=group, 
                           expenses=expenses,
                           currencies=currencies, 
                           base_currency=base_currency,
                           categories=categories,
                           users=all_users)

@app.route('/groups/<int:group_id>/add_member', methods=['POST'])
@login_required_dev
def add_group_member(group_id):
    group = Group.query.get_or_404(group_id)
    if current_user != group.creator:
        flash('Only group creator can add members')
        return redirect(url_for('group_details', group_id=group_id))
    
    member_id = request.form.get('user_id')
    user = User.query.filter_by(id=member_id).first()
    
    if user and user not in group.members:
        group.members.append(user)
        db.session.commit()
        flash(f'{user.name} added to group!')
        create_default_categories(user.id)
        # Send group invitation email
        try:
            send_group_invitation_email(user, group, current_user)
        except Exception as e:
            app.logger.error(f"Failed to send group invitation email: {str(e)}")
    
    return redirect(url_for('group_details', group_id=group_id))

@app.route('/groups/<int:group_id>/remove_member/<member_id>', methods=['POST'])
@login_required_dev
def remove_group_member(group_id, member_id):
    group = Group.query.get_or_404(group_id)
    if current_user != group.creator:
        flash('Only group creator can remove members')
        return redirect(url_for('group_details', group_id=group_id))
    
    user = User.query.filter_by(id=member_id).first()
    if user and user in group.members and user != group.creator:
        group.members.remove(user)
        db.session.commit()
        flash(f'{user.name} removed from group!')
    
    return redirect(url_for('group_details', group_id=group_id))

@app.route('/groups/<int:group_id>/delete', methods=['GET', 'POST'])
@login_required_dev
def delete_group(group_id):
    """Delete a group and its associated expenses"""
    # Find the group
    group = Group.query.get_or_404(group_id)
    
    # Security check: Only the creator can delete the group
    if current_user.id != group.created_by:
        flash('Only the group creator can delete the group', 'error')
        return redirect(url_for('group_details', group_id=group_id))
    
    # GET request shows confirmation prompt, POST actually deletes
    if request.method == 'GET':
        # Count associated expenses
        expense_count = Expense.query.filter_by(group_id=group_id).count()
        # Set up session data for confirmation
        session['delete_group_id'] = group_id
        session['delete_group_name'] = group.name
        session['delete_group_expense_count'] = expense_count
        # Show confirmation toast
        flash(f'Warning: Deleting this group will also delete {expense_count} associated transactions. This action cannot be undone.', 'warning')
        return redirect(url_for('group_details', group_id=group_id))
    
    # POST request (actual deletion)
    try:
        # Get stored values from session
        group_name = session.get('delete_group_name', group.name)
        expense_count = session.get('delete_group_expense_count', 0)
        
        # Delete associated expenses first
        Expense.query.filter_by(group_id=group_id).delete()
        
        # Delete the group
        db.session.delete(group)
        db.session.commit()
        
        # Clear session data
        session.pop('delete_group_id', None)
        session.pop('delete_group_name', None)
        session.pop('delete_group_expense_count', None)
        
        # Success message
        if expense_count > 0:
            flash(f'Group "{group_name}" and {expense_count} associated transactions have been deleted', 'success')
        else:
            flash(f'Group "{group_name}" has been deleted', 'success')
            
        return redirect(url_for('groups'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting group {group_id}: {str(e)}")
        flash(f'Error deleting group: {str(e)}', 'error')
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
    return render_template('admin.html', users=users)
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

    
    create_default_categories(user.id)
    db.session.commit() 


    create_default_budgets(user.id)
    db.session.commit() 

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
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    if user_id == current_user.id:
        flash('Cannot delete your own admin account!')
        return redirect(url_for('admin'))
    
    app.logger.info(f"Starting deletion process for user: {user_id}")
    
    user = User.query.filter_by(id=user_id).first()
    if not user:
        flash('User not found.')
        return redirect(url_for('admin'))
    
    try:
        # Start a transaction
        app.logger.info("Starting transaction")
        
        # Delete all related data in the correct order
        # 1. First handle budgets (they reference categories)
        app.logger.info("Deleting budgets...")
        Budget.query.filter_by(user_id=user_id).delete()
        
        # 2. Delete recurring expenses
        app.logger.info("Deleting recurring expenses...")
        RecurringExpense.query.filter_by(user_id=user_id).delete()
        
        # 3. Delete expenses
        app.logger.info("Deleting expenses...")
        Expense.query.filter_by(user_id=user_id).delete()
        
        # 4. Delete settlements
        app.logger.info("Deleting settlements...")
        Settlement.query.filter(
            or_(Settlement.payer_id == user_id, Settlement.receiver_id == user_id)
        ).delete(synchronize_session=False)
        
        # 5. Delete category mappings
        app.logger.info("Deleting category mappings...")
        CategoryMapping.query.filter_by(user_id=user_id).delete()
        
        # 6. Delete SimpleFin settings
        app.logger.info("Deleting SimpleFin settings...")
        SimpleFin.query.filter_by(user_id=user_id).delete()
        
        # 7. Delete ignored recurring patterns
        app.logger.info("Deleting ignored patterns...")
        IgnoredRecurringPattern.query.filter_by(user_id=user_id).delete()
        
        # 8. Handle user's accounts
        app.logger.info("Deleting accounts...")
        Account.query.filter_by(user_id=user_id).delete()
        
        # 9. Handle tags - first remove from association table
        app.logger.info("Handling tags...")
        user_tags = Tag.query.filter_by(user_id=user_id).all()
        for tag in user_tags:
            # Clear association with expenses
            tag.expenses = []
        db.session.flush()
        
        # Now delete the tags
        Tag.query.filter_by(user_id=user_id).delete()
        
        # 10. Categories can now be deleted
        app.logger.info("Deleting categories...")
        Category.query.filter_by(user_id=user_id).delete()
        
        # 11. Handle group memberships
        app.logger.info("Handling group memberships...")
        # First, handle groups created by this user
        for group in Group.query.filter_by(created_by=user_id).all():
            # Remove the user from the group members if they're in it
            if user in group.members:
                group.members.remove(user)
                
            # Find a new owner or delete the group if empty
            if group.members:
                # Assign first remaining member as new owner
                new_owner = next(iter(group.members))
                group.created_by = new_owner.id
            else:
                # Delete group if no members left
                db.session.delete(group)
        
        # Remove user from all groups they're a member of
        for group in user.groups:
            group.members.remove(user)
        
        # 12. Finally delete the user
        app.logger.info("Deleting user...")
        db.session.delete(user)
        
        # Commit all changes
        db.session.commit()
        app.logger.info(f"User {user_id} deleted successfully")
        flash('User deleted successfully!')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        flash(f'Error deleting user: {str(e)}')
    
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

@app.route('/admin/toggle_admin_status/<user_id>', methods=['POST'])
@login_required_dev
def admin_toggle_admin_status(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    # Prevent changing your own admin status
    if user_id == current_user.id:
        flash('Cannot change your own admin status!')
        return redirect(url_for('admin'))
    
    user = User.query.filter_by(id=user_id).first()
    if not user:
        flash('User not found.')
        return redirect(url_for('admin'))
    
    # Toggle admin status
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = "admin" if user.is_admin else "regular user"
    flash(f'User {user.name} is now a {status}!')
    
    return redirect(url_for('admin'))

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
    try:
        # Parse date with error handling
        try:
            settlement_date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD format.')
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
        flash('Settlement recorded successfully!')
        
    except Exception as e:
        flash(f'Error: {str(e)}')
        
    return redirect(url_for('settlements'))


#--------------------
# ROUTES: currencies
#--------------------

@app.route('/currencies')
@login_required_dev
def manage_currencies():
    currencies = Currency.query.all()
    return render_template('currencies.html', currencies=currencies)

@app.route('/currencies/add', methods=['POST'])
@login_required_dev
def add_currency():
    if not current_user.is_admin:
        flash('Only administrators can add currencies')
        return redirect(url_for('manage_currencies'))
    
    code = request.form.get('code', '').upper()
    name = request.form.get('name')
    symbol = request.form.get('symbol')
    rate_to_base = float(request.form.get('rate_to_base', 1.0))
    is_base = request.form.get('is_base') == 'on'
    
    # Validate currency code format
    if not code or len(code) != 3 or not code.isalpha():
        flash('Invalid currency code. Please use 3-letter ISO currency code (e.g., USD, EUR, GBP)')
        return redirect(url_for('manage_currencies'))
    
    # Check if currency already exists
    existing = Currency.query.filter_by(code=code).first()
    if existing:
        flash(f'Currency {code} already exists')
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
        flash(f'Currency {code} added successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding currency: {str(e)}')
    
    return redirect(url_for('manage_currencies'))

@app.route('/currencies/update/<code>', methods=['POST'])
@login_required_dev
def update_currency(code):
    if not current_user.is_admin:
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
        flash(f'Currency {code} updated successfully')
    except Exception as e:
        db.session.rollback()
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


#--------------------
# ROUTES: Transactions
#--------------------

@app.route('/transactions')
@login_required_dev
@demo_time_limited
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



@app.route('/get_transaction_form_html')
@login_required_dev
def get_transaction_form_html():
    """Return the HTML for the add transaction form"""
    base_currency = get_base_currency()
    users = User.query.all()
    groups = Group.query.join(group_users).filter(group_users.c.user_id == current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    currencies = Currency.query.all()
    tags = Tag.query.filter_by(user_id=current_user.id).all()  # Add tags
    return render_template('partials/add_transaction_form.html',
                          users=users,
                          groups=groups,
                          categories=categories,
                          currencies=currencies,
                          tags=tags,  # Pass tags to the template
                          base_currency=base_currency)

@app.route('/get_expense_edit_form/<int:expense_id>')
@login_required_dev
def get_expense_edit_form(expense_id):
    """Return the HTML for editing an expense, including category splits data"""
    expense = Expense.query.get_or_404(expense_id)
    
    # Security check
    if expense.user_id != current_user.id and current_user.id not in (expense.split_with or ''):
        return 'Access denied', 403
    
    # Prepare category splits data if available
    category_splits_data = []
    if expense.has_category_splits:
        # Get all category splits for this expense
        splits = CategorySplit.query.filter_by(expense_id=expense.id).all()
        for split in splits:
            category_splits_data.append({
                'category_id': split.category_id,
                'amount': split.amount
            })
    
    # Add category splits data to the expense object for the template
    expense.category_splits_data = json.dumps(category_splits_data) if category_splits_data else ''
    
    base_currency = get_base_currency()
    users = User.query.all()
    groups = Group.query.join(group_users).filter(group_users.c.user_id == current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    currencies = Currency.query.all()
    
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template('partials/edit_transaction_form.html',
                          expense=expense,
                          users=users,
                          groups=groups,
                          categories=categories,
                          currencies=currencies,
                          accounts=accounts,
                          user=current_user,
                          base_currency=base_currency)


#--------------------
# ROUTES: Accounts and Imports 
#--------------------

# This function should be added to the route that handles the accounts page
# Update the accounts route in app.py

@app.route('/accounts')
@login_required_dev
def accounts():
    """View and manage financial accounts"""
    # Get all user accounts
    user_accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get user's preferred currency for conversion and display
    user_currency = None
    if current_user.default_currency_code:
        user_currency = Currency.query.filter_by(code=current_user.default_currency_code).first()
    
    # Fall back to base currency if user has no preference
    if not user_currency:
        user_currency = Currency.query.filter_by(is_base=True).first()
        
    # If somehow we still don't have a currency, use USD as ultimate fallback
    if not user_currency:
        user_currency = Currency.query.filter_by(code='USD').first() or Currency(code='USD', name='US Dollar', symbol='$', rate_to_base=1.0)
        
    user_currency_code = user_currency.code
    
    # Calculate financial summary with currency conversion
    total_assets = 0
    total_liabilities = 0
    
    for account in user_accounts:
        # Get account balance in account's currency
        balance = account.balance or 0
        
        # Skip near-zero balances
        if abs(balance) < 0.01:
            continue
            
        # Get account's currency code
        account_currency = account.currency_code or user_currency_code
        
        # Convert to user's preferred currency if different
        if account_currency != user_currency_code:
            converted_balance = convert_currency(balance, account_currency, user_currency_code)
        else:
            converted_balance = balance
            
        # Add to appropriate total
        if account.type in ['checking', 'savings', 'investment'] and converted_balance > 0:
            total_assets += converted_balance
        elif account.type in ['credit', 'loan'] or converted_balance < 0:
            total_liabilities += abs(converted_balance)  # Store as positive amount
    
    # Calculate net worth
    net_worth = total_assets - total_liabilities
    
    # Get all currencies for the form
    currencies = Currency.query.all()
    
    return render_template('accounts.html',
                          accounts=user_accounts,
                          total_assets=total_assets,
                          total_liabilities=total_liabilities,
                          net_worth=net_worth,
                          user_currency=user_currency,
                          currencies=currencies)



@app.route('/advanced')
@login_required_dev
def advanced():
    """Display advanced features like account management and imports"""
    # Get all user accounts
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get connected accounts (those with SimpleFin integration)
    connected_accounts = [account for account in accounts if account.import_source == 'simplefin']
    
    # Calculate financial summary
    total_assets = sum(account.balance for account in accounts 
                    if account.type in ['checking', 'savings', 'investment'] and account.balance > 0)
    
    total_liabilities = abs(sum(account.balance for account in accounts 
                          if account.type in ['credit', 'loan'] or account.balance < 0))
    
    net_worth = total_assets - total_liabilities
    
    # Get base currency for display
    base_currency = get_base_currency()
    
    # Get all currencies for the form
    currencies = Currency.query.all()
    
    return render_template('advanced.html',
                          accounts=accounts,
                          connected_accounts=connected_accounts,
                          total_assets=total_assets,
                          total_liabilities=total_liabilities,
                          net_worth=net_worth,
                          base_currency=base_currency,
                          currencies=currencies)


@app.route('/add_account', methods=['POST'])
@login_required_dev
def add_account():
    """Add a new account"""
    try:
        name = request.form.get('name')
        account_type = request.form.get('type')
        institution = request.form.get('institution')
        balance = float(request.form.get('balance', 0))
        currency_code = request.form.get('currency_code', current_user.default_currency_code)
        
        # Create new account
        account = Account(
            name=name,
            type=account_type,
            institution=institution,
            balance=balance,
            currency_code=currency_code,
            user_id=current_user.id
        )
        
        db.session.add(account)
        db.session.commit()
        
        flash('Account added successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding account: {str(e)}')
    
    return redirect(url_for('accounts'))


@app.route('/get_account/<int:account_id>')
@login_required_dev
def get_account(account_id):
    """Get account details via AJAX"""
    try:
        account = Account.query.get_or_404(account_id)
        
        # Security check
        if account.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to view this account'
            }), 403
        
        # Get transaction count for this account
        transaction_count = Expense.query.filter_by(account_id=account_id).count()
        
        return jsonify({
            'success': True,
            'account': {
                'id': account.id,
                'name': account.name,
                'type': account.type,
                'institution': account.institution,
                'balance': account.balance,
                'currency_code': account.currency_code or current_user.default_currency_code,
                'transaction_count': transaction_count
            }
        })
    except Exception as e:
        app.logger.error(f"Error retrieving account {account_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/update_account', methods=['POST'])
@login_required_dev
def update_account():
    """Update an existing account"""
    try:
        account_id = request.form.get('account_id')
        account = Account.query.get_or_404(account_id)
        
        # Security check
        if account.user_id != current_user.id:
            flash('You do not have permission to edit this account')
            return redirect(url_for('accounts'))
        
        # Update fields
        account.name = request.form.get('name')
        account.type = request.form.get('type')
        account.institution = request.form.get('institution')
        account.balance = float(request.form.get('balance', 0))
        account.currency_code = request.form.get('currency_code')
        
        db.session.commit()
        flash('Account updated successfully')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating account: {str(e)}')
    
    return redirect(url_for('accounts'))

@app.route('/delete_account/<int:account_id>', methods=['DELETE'])
@login_required_dev
def delete_account(account_id):
    """Delete an account"""
    try:
        account = Account.query.get_or_404(account_id)
        
        # Security check
        if account.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to delete this account'
            }), 403
        
        db.session.delete(account)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Account deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting account {account_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
    
@app.route('/import_csv', methods=['POST'])
@login_required_dev
def import_csv():
    """Import transactions from a CSV file"""
    if 'csv_file' not in request.files:
        flash('No file provided')
        return redirect(url_for('advanced'))
    
    csv_file = request.files['csv_file']
    
    if csv_file.filename == '':
        flash('No file selected')
        return redirect(url_for('advanced'))
    
    # Case-insensitive extension check
    if not csv_file.filename.lower().endswith('.csv'):
        flash('File must be a CSV')
        return redirect(url_for('advanced'))
    
    # Define base_currency for any functions that might need it
    base_currency = get_base_currency()
    
    imported_expenses = []
    
    try:
        # Get form parameters
        account_id = request.form.get('account_id')
        date_format = request.form.get('date_format', 'MM/DD/YYYY')
        date_column = request.form.get('date_column', 'Date')
        amount_column = request.form.get('amount_column', 'Amount')
        description_column = request.form.get('description_column', 'Description')
        category_column = request.form.get('category_column')
        type_column = request.form.get('type_column')
        id_column = request.form.get('id_column')
        
        detect_duplicates = 'detect_duplicates' in request.form
        auto_categorize = 'auto_categorize' in request.form
        negative_is_expense = 'negative_is_expense' in request.form
        # NEW: Get the delimiter selection
        delimiter_type = request.form.get('delimiter', 'comma')
        delimiter = ','  # Default to comma
        # Read file content
        
        if delimiter_type == 'tab':
            delimiter = '\t'
        elif delimiter_type == 'semicolon':
            delimiter = ';'
        elif delimiter_type == 'pipe':
            delimiter = '|'
        elif delimiter_type == 'custom':
            custom_delimiter = request.form.get('custom_delimiter', ',')
            if custom_delimiter:
                delimiter = custom_delimiter
        file_content = csv_file.read().decode('utf-8')
        # Parse CSV
        import csv
        import io
        from datetime import datetime
        
        csv_reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)
        
        # Get account if specified
        account = None
        if account_id:
            account = Account.query.get(account_id)
            if account and account.user_id != current_user.id:
                flash('Invalid account selected')
                return redirect(url_for('advanced'))
        
        # Use the enhanced determine_transaction_type function that accepts account_id
        def determine_transaction_type_for_import(row, current_account_id=None):
            """Determine transaction type based on row data from CSV import"""
            type_column = request.form.get('type_column')
            negative_is_expense = 'negative_is_expense' in request.form
            
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
            description = row.get(description_column, '').strip()
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
            amount_str = row[amount_column].strip().replace('$', '').replace(',', '')
            try:
                amount = float(amount_str)
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
                
        # Get existing cards used
        existing_cards = db.session.query(Expense.card_used).filter_by(
            user_id=current_user.id
        ).distinct().all()
        existing_cards = [card[0] for card in existing_cards if card[0]]
        
        # Use the most frequent card as default if available
        default_card = "Imported Card"
        if existing_cards:
            from collections import Counter
            card_counter = Counter()
            for card in existing_cards:
                card_counter[card] += 1
            default_card = card_counter.most_common(1)[0][0]
        
        # Define date parser based on selected format
        def parse_date(date_str):
            if date_format == 'MM/DD/YYYY':
                return datetime.strptime(date_str, '%m/%d/%Y')
            elif date_format == 'DD/MM/YYYY':
                return datetime.strptime(date_str, '%d/%m/%Y')
            elif date_format == 'YYYY-MM-DD':
                return datetime.strptime(date_str, '%Y-%m-%d')
            elif date_format == 'YYYY/MM/DD':
                return datetime.strptime(date_str, '%Y/%m/%d')
            else:
                return datetime.strptime(date_str, '%m/%d/%Y')  # Default
        
        # Process each row
        imported_count = 0
        duplicate_count = 0
        
        for row in csv_reader:
            try:
                # Skip if missing required fields
                if not all(key in row for key in [date_column, amount_column, description_column]):
                    continue
                
                # Extract data
                date_str = row[date_column].strip()
                amount_str = row[amount_column].strip().replace('$', '').replace(',', '')
                description = row[description_column].strip()
                
                # Skip if empty data
                if not date_str or not amount_str or not description:
                    continue
                
                # Parse date
                transaction_date = parse_date(date_str)
                
                # Parse amount (handle negative values)
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue  # Skip if amount can't be parsed
                
                # Try to detect if this is an internal transfer
                is_transfer, source_account_id, destination_account_id = False, None, None
                if account and account.id:
                    is_transfer, source_account_id, destination_account_id = detect_internal_transfer(
                        description, amount, account.id
                    )
                
                if is_transfer:
                    # This is an internal transfer
                    transaction_type = 'transfer'
                    # Use the detected accounts, falling back to the selected account
                    source_account_id = source_account_id or account.id
                    # If we couldn't determine the destination, it stays None
                else:
                    # Use the function defined within this scope
                    transaction_type = determine_transaction_type_for_import(row, account.id if account else None)
                
                # Get external ID if available
                external_id = row.get(id_column) if id_column and id_column in row else None
                
                # Check for duplicates if enabled
                if detect_duplicates and external_id:
                    existing = Expense.query.filter_by(
                        user_id=current_user.id,
                        external_id=external_id,
                        import_source='csv'
                    ).first()
                    
                    if existing:
                        duplicate_count += 1
                        continue
                
                # Get category from CSV or auto-categorize (but not for transfers)
                category_id = None
                if transaction_type != 'transfer':
                    category_name = None
                    if category_column and category_column in row:
                        category_name = row[category_column].strip()
                    
                    # Use enhanced get_category_id that supports auto-categorization
                    category_id = get_category_id(
                        category_name, 
                        description if auto_categorize else None, 
                        current_user.id
                    )
                
                # Create new transaction
                transaction = Expense(
                    description=description,
                    amount=abs(amount),  # Always store positive amount
                    date=transaction_date,
                    card_used=default_card,  # Use most common card or a default
                    transaction_type=transaction_type,
                    split_method='equal',
                    paid_by=current_user.id,
                    user_id=current_user.id,
                    category_id=category_id,
                    account_id=source_account_id or (account.id if account else None),
                    destination_account_id=destination_account_id,
                    external_id=external_id,
                    import_source='csv'
                )
                
                # Add to session
                db.session.add(transaction)
                imported_expenses.append(transaction)
                imported_count += 1
                
                # If this is a transfer and we've identified a destination account,
                # update the balances of both accounts
                if transaction_type == 'transfer' and transaction.account_id and transaction.destination_account_id:
                    from_account = Account.query.get(transaction.account_id)
                    to_account = Account.query.get(transaction.destination_account_id)
                    
                    if from_account and to_account and from_account.user_id == current_user.id and to_account.user_id == current_user.id:
                        from_account.balance -= amount
                        to_account.balance += amount
                
            except Exception as row_error:
                app.logger.error(f"Error processing CSV row: {str(row_error)}")
                continue
        
        # Commit all transactions
        db.session.commit()
        
        # Update account balance if specified
        if account and imported_count > 0:
            # Update the last sync time
            account.last_sync = datetime.utcnow()
            db.session.commit()
        
        # Flash success message
        flash(f'Successfully imported {imported_count} transactions. Skipped {duplicate_count} duplicates.')
        
        # Redirect to a page showing the imported transactions
        return render_template('import_results.html', 
                               expenses=imported_expenses,
                               count=imported_count,
                               duplicate_count=duplicate_count,
                               base_currency=base_currency)  # Pass base_currency here
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error importing CSV: {str(e)}")
        flash(f'Error importing transactions: {str(e)}')
    
    return redirect(url_for('advanced'))

#--------------------
# ROUTES: simplefun
#--------------------
@app.route('/connect_simplefin')
@login_required_dev
def connect_simplefin():
    """Redirect users to SimpleFin site to get their setup token"""
    if not app.config['SIMPLEFIN_ENABLED']:
        flash('SimpleFin integration is not enabled. Please contact the administrator.')
        return redirect(url_for('advanced'))
    
    # Get the URL for users to obtain their setup token
    setup_token_url = simplefin_client.get_setup_token_instructions()
    
    # Redirect to SimpleFin setup token page
    return redirect(setup_token_url)

@app.route('/simplefin/process_token', methods=['POST'])
@login_required_dev
def process_simplefin_token():
    """Process the setup token provided by the user"""
    if not app.config['SIMPLEFIN_ENABLED']:
        flash('SimpleFin integration is not enabled.')
        return redirect(url_for('advanced'))
    
    setup_token = request.form.get('setup_token')
    if not setup_token:
        flash('No setup token provided.')
        return redirect(url_for('advanced'))
    
    # Decode the setup token to get the claim URL
    claim_url = simplefin_client.decode_setup_token(setup_token)
    if not claim_url:
        flash('Invalid setup token. Please try again.')
        return redirect(url_for('advanced'))
    
    # Claim the access URL
    access_url = simplefin_client.claim_access_url(claim_url)
    if not access_url:
        flash('Failed to claim access URL. Please try again with a new setup token.')
        return redirect(url_for('advanced'))
    
    
    if not simplefin_client.test_access_url(access_url):
        flash('The access URL appears to be invalid. Please try again with a new setup token.')
        return redirect(url_for('advanced'))
    
    encoded_access_url = base64.b64encode(access_url.encode()).decode()
    
    # Create a SimpleFin settings record for this user
    try:
        # Check if a SimpleFin settings record already exists for this user
        simplefin_settings = SimpleFin.query.filter_by(user_id=current_user.id).first()
        
        if simplefin_settings:
            # Update existing settings
            simplefin_settings.access_url = encoded_access_url
            simplefin_settings.last_sync = None  # Reset last sync time
            simplefin_settings.enabled = True
            simplefin_settings.sync_frequency = 'daily'  # Default to daily
        else:
            # Create new settings
            simplefin_settings = SimpleFin(
                user_id=current_user.id,
                access_url=encoded_access_url,
                last_sync=None,
                enabled=True,
                sync_frequency='daily'
            )
            db.session.add(simplefin_settings)
            
        db.session.commit()
        
        # Redirect to fetch accounts page
        return redirect(url_for('simplefin_fetch_accounts'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving SimpleFin settings: {str(e)}")
        flash(f'Error saving SimpleFin settings: {str(e)}')
        return redirect(url_for('advanced'))

@app.route('/simplefin/fetch_accounts') 
@login_required_dev 
def simplefin_fetch_accounts():
    """Fetch accounts and transactions from SimpleFin"""
    if not app.config['SIMPLEFIN_ENABLED']:
        flash('SimpleFin integration is not enabled.')
        return redirect(url_for('advanced'))
    
    try:
        # Get the user's SimpleFin settings
        simplefin_settings = SimpleFin.query.filter_by(user_id=current_user.id).first()
        
        if not simplefin_settings or not simplefin_settings.access_url:
            flash('No SimpleFin connection found. Please connect with SimpleFin first.')
            return redirect(url_for('advanced'))
        
        # Decode the access URL
        access_url = base64.b64decode(simplefin_settings.access_url.encode()).decode()
        
        # Fetch accounts and transactions (last 30 days by default)
        raw_data = simplefin_client.get_accounts_with_transactions(access_url, days_back=30)
        
        if not raw_data:
            flash('Failed to fetch accounts and transactions from SimpleFin.')
            return redirect(url_for('advanced'))
        
        # Process the raw data
        accounts = simplefin_client.process_raw_accounts(raw_data)
        
        # Store account IDs in session instead of full data
        account_ids = [acc.get('id') for acc in accounts if acc.get('id')]
        session['simplefin_account_ids'] = account_ids
        
        # Render the account selection template
        return render_template('simplefin_accounts.html', accounts=accounts)
        
    except Exception as e:
        app.logger.error(f"Error fetching SimpleFin accounts: {str(e)}")
        flash(f'Error fetching accounts: {str(e)}')
        return redirect(url_for('advanced'))

@app.route('/simplefin/add_accounts', methods=['POST'])
@login_required_dev
def simplefin_add_accounts():
    """Process selected accounts to add to the system"""
    # Get selected account IDs from form
    account_ids = request.form.getlist('account_ids')
    if not account_ids:
        flash('No accounts selected.')
        return redirect(url_for('advanced'))
    
    try:
        # Get the user's SimpleFin settings
        simplefin_settings = SimpleFin.query.filter_by(user_id=current_user.id).first()
        
        if not simplefin_settings or not simplefin_settings.access_url:
            flash('No SimpleFin connection found. Please reconnect with SimpleFin.')
            return redirect(url_for('advanced'))
        
        # Decode the access URL
        access_url = base64.b64decode(simplefin_settings.access_url.encode()).decode()
        
        # Fetch accounts and transactions
        raw_data = simplefin_client.get_accounts_with_transactions(access_url, days_back=30)
        
        if not raw_data:
            flash('Failed to fetch accounts from SimpleFin. Please try again.')
            return redirect(url_for('advanced'))
        
        # Process the raw data
        accounts = simplefin_client.process_raw_accounts(raw_data)
        
        # Filter to only selected accounts
        selected_accounts = []
        for account in accounts:
            if account.get('id') in account_ids:
                # Apply customizations from form data
                account_id = account.get('id')
                
                # Get custom account name if provided
                custom_name = request.form.get(f'account_name_{account_id}')
                if custom_name and custom_name.strip():
                    account['name'] = custom_name.strip()
                
                # Get custom account type if provided
                custom_type = request.form.get(f'account_type_{account_id}')
                if custom_type:
                    account['type'] = custom_type
                
                selected_accounts.append(account)
        
        # Count for success message
        accounts_added = 0
        transactions_added = 0
        
        # Get the user's default currency
        default_currency = current_user.default_currency_code or 'USD'
        
        # Process and add each selected account
        for sf_account in selected_accounts:
            # Check if account already exists
            existing_account = Account.query.filter_by(
                user_id=current_user.id,
                name=sf_account.get('name'),
                institution=sf_account.get('institution')
            ).first()
            
            account_obj = None
            
            if existing_account:
                # Update existing account
                existing_account.balance = sf_account.get('balance', 0)
                existing_account.import_source = 'simplefin'
                existing_account.last_sync = datetime.utcnow()
                existing_account.external_id = sf_account.get('id')
                existing_account.status = 'active'
                existing_account.type = sf_account.get('type')  # Apply custom type
                db.session.commit()
                accounts_added += 1
                account_obj = existing_account
            else:
                # Create new account with custom values
                new_account = Account(
                    name=sf_account.get('name'),  # Custom name from form
                    type=sf_account.get('type'),  # Custom type from form
                    institution=sf_account.get('institution'),
                    balance=sf_account.get('balance', 0),
                    currency_code=sf_account.get('currency_code', default_currency),
                    user_id=current_user.id,
                    import_source='simplefin',
                    external_id=sf_account.get('id'),
                    last_sync=datetime.utcnow(),
                    status='active'
                )
                db.session.add(new_account)
                db.session.flush()  # Get ID without committing
                accounts_added += 1
                account_obj = new_account
            
            # Create transaction objects using the enhanced client method
            transaction_objects, import_count = simplefin_client.create_transactions_from_account(
                sf_account,
                account_obj,
                current_user.id,
                detect_internal_transfer,  # Your transfer detection function
                auto_categorize_transaction,  # Your auto-categorization function
                get_category_id  # Your function to find/create categories
            )
            
            # Check for existing transactions to avoid duplicates
            transaction_objects_filtered = []
            for transaction in transaction_objects:
                existing = Expense.query.filter_by(
                    user_id=current_user.id,
                    external_id=transaction.external_id,
                    import_source='simplefin'
                ).first()
                
                if not existing:
                    transaction_objects_filtered.append(transaction)
            
            # Add filtered transactions to the session
            for transaction in transaction_objects_filtered:
                db.session.add(transaction)
                transactions_added += 1
                
                # Handle account balance updates for transfers
                if transaction.transaction_type == 'transfer' and transaction.destination_account_id:
                    # Find the destination account
                    to_account = Account.query.get(transaction.destination_account_id)
                    if to_account and to_account.user_id == current_user.id:
                        # For transfers, add to destination account balance
                        to_account.balance += transaction.amount
        
        # Commit all changes
        db.session.commit()
        
        # Update the SimpleFin settings to record the sync time
        simplefin_settings.last_sync = datetime.utcnow()
        db.session.commit()
        
        flash(f'Successfully added {accounts_added} accounts and {transactions_added} transactions from SimpleFin.')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding SimpleFin accounts: {str(e)}")
        flash(f'Error adding accounts: {str(e)}')
    
    return redirect(url_for('accounts'))
        
@app.route('/sync_account/<int:account_id>', methods=['POST'])
@login_required_dev
def sync_account(account_id):
    """Sync transactions for a specific account"""
    try:
        account = Account.query.get_or_404(account_id)
        
        # Security check
        if account.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to sync this account'
            }), 403
        
        # Check if this is a SimpleFin account
        if account.import_source != 'simplefin' or not account.external_id:
            return jsonify({
                'success': False,
                'message': 'This account is not connected to SimpleFin'
            }), 400
        
        # Get the user's SimpleFin access URL
        simplefin_settings = SimpleFin.query.filter_by(user_id=current_user.id).first()
        
        if not simplefin_settings or not simplefin_settings.access_url:
            return jsonify({
                'success': False,
                'message': 'No SimpleFin connection found. Please reconnect with SimpleFin.',
                'action': 'reconnect',
                'redirect': url_for('connect_simplefin')
            })
        
        # Decode the access URL
        access_url = base64.b64decode(simplefin_settings.access_url.encode()).decode()
        
        # Fetch accounts and transactions
        raw_data = simplefin_client.get_accounts_with_transactions(access_url, days_back=7)  # Last 7 days for manual sync
        
        if not raw_data:
            return jsonify({
                'success': False,
                'message': 'Failed to fetch data from SimpleFin.'
            }), 500
        
        # Process the raw data
        accounts = simplefin_client.process_raw_accounts(raw_data)
        
        # Find the matching account
        sf_account = next((acc for acc in accounts if acc.get('id') == account.external_id), None)
        
        if not sf_account:
            return jsonify({
                'success': False,
                'message': 'Account not found in SimpleFin data.'
            }), 404
        
        # Update account details
        account.balance = sf_account.get('balance', account.balance)
        account.last_sync = datetime.utcnow()
        
        # Create transaction objects using the enhanced client method
        transaction_objects, _ = simplefin_client.create_transactions_from_account(
            sf_account,
            account,
            current_user.id,
            detect_internal_transfer,
            auto_categorize_transaction,
            get_category_id
        )
        
        # Track new transactions
        new_transactions = 0
        
        # Filter out existing transactions and add new ones
        for transaction in transaction_objects:
            # Check if transaction already exists
            existing = Expense.query.filter_by(
                user_id=current_user.id,
                external_id=transaction.external_id,
                import_source='simplefin'
            ).first()
            
            if not existing:
                db.session.add(transaction)
                new_transactions += 1
                
                # Handle account balance updates for transfers
                if transaction.transaction_type == 'transfer' and transaction.destination_account_id:
                    # Find the destination account
                    to_account = Account.query.get(transaction.destination_account_id)
                    if to_account and to_account.user_id == current_user.id:
                        # For transfers, add to destination account balance
                        to_account.balance += transaction.amount
        
        # Commit changes
        db.session.commit()
        
        # Update the SimpleFin settings last_sync time
        if simplefin_settings:
            simplefin_settings.last_sync = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Account synced successfully. {new_transactions} new transactions imported.',
            'new_transactions': new_transactions
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error syncing account {account_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/disconnect_account/<int:account_id>', methods=['POST'])
@login_required_dev
def disconnect_account(account_id):
    """Disconnect an account from SimpleFin"""
    try:
        account = Account.query.get_or_404(account_id)
        
        # Security check
        if account.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to disconnect this account'
            }), 403
        
        # Check if this is a SimpleFin account
        if account.import_source != 'simplefin':
            return jsonify({
                'success': False,
                'message': 'This account is not connected to SimpleFin'
            }), 400
        
        # Update account to remove SimpleFin connection
        account.import_source = None
        account.external_id = None
        account.status = 'inactive'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Account disconnected successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error disconnecting account {account_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/simplefin/disconnect', methods=['POST'])
@login_required_dev
def simplefin_disconnect():
    """Disconnect SimpleFin integration for the current user"""
    if not app.config['SIMPLEFIN_ENABLED']:
        return jsonify({
            'success': False,
            'message': 'SimpleFin integration is not enabled.'
        })
    
    try:
        # Get the user's SimpleFin settings
        simplefin_settings = SimpleFin.query.filter_by(user_id=current_user.id).first()
        
        if not simplefin_settings:
            return jsonify({
                'success': False,
                'message': 'No SimpleFin connection found.'
            })
        
        # Disable the SimpleFin integration
        simplefin_settings.enabled = False
        db.session.commit()
        
        # Also update all SimpleFin-connected accounts to show as disconnected
        accounts = Account.query.filter_by(
            user_id=current_user.id,
            import_source='simplefin'
        ).all()
        
        for account in accounts:
            account.import_source = None
            account.external_id = None
            account.status = 'inactive'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'SimpleFin disconnected successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error disconnecting SimpleFin: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/simplefin/refresh', methods=['POST'])
@login_required_dev
def simplefin_refresh():
    """Refresh SimpleFin connection and trigger a sync"""
    if not app.config['SIMPLEFIN_ENABLED']:
        return jsonify({
            'success': False,
            'message': 'SimpleFin integration is not enabled.'
        })
    
    try:
        # Get the user's SimpleFin settings
        simplefin_settings = SimpleFin.query.filter_by(user_id=current_user.id).first()
        
        if not simplefin_settings or not simplefin_settings.access_url or not simplefin_settings.enabled:
            # No valid connection, redirect to get a new setup token
            return jsonify({
                'success': False,
                'message': 'No valid SimpleFin connection found. Please reconnect.',
                'redirect': url_for('connect_simplefin')
            })
        
        # Decode the access URL and test it
        access_url = base64.b64decode(simplefin_settings.access_url.encode()).decode()
        
        if not simplefin_client.test_access_url(access_url):
            # Access URL no longer valid, redirect to get a new setup token
            return jsonify({
                'success': False,
                'message': 'Your SimpleFin connection has expired. Please reconnect.',
                'redirect': url_for('connect_simplefin')
            })
        
        # Access URL still valid, redirect to fetch accounts
        return jsonify({
            'success': True,
            'message': 'SimpleFin connection is valid. Fetching accounts...',
            'redirect': url_for('simplefin_fetch_accounts')
        })
        
    except Exception as e:
        app.logger.error(f"Error refreshing SimpleFin: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })


@app.route('/simplefin/run_scheduled_sync', methods=['POST'])
@login_required_dev
def run_scheduled_simplefin_sync():
    """Manually trigger the scheduled SimpleFin sync (admin only)"""
    if not current_user.is_admin:
        flash('Only administrators can manually trigger the scheduled sync.')
        return redirect(url_for('admin'))
    
    try:
        # Run the sync function
        sync_all_simplefin_accounts()
        flash('SimpleFin scheduled sync completed successfully!')
    except Exception as e:
        app.logger.error(f"Error running scheduled SimpleFin sync: {str(e)}")
        flash(f'Error running scheduled sync: {str(e)}')
    
    return redirect(url_for('admin'))

# Function to sync all SimpleFin accounts for all users
def sync_all_simplefin_accounts():
    """Sync all SimpleFin accounts for all users - runs on a schedule"""
    with app.app_context():
        app.logger.info("Starting scheduled SimpleFin sync for all users")
        
        try:
            # Get all users with SimpleFin settings
            settings_list = SimpleFin.query.filter_by(enabled=True).all()
            
            for settings in settings_list:
                # Skip if last sync was less than 12 hours ago (to prevent excessive syncing)
                if settings.last_sync and (datetime.utcnow() - settings.last_sync).total_seconds() < 43200:  # 12 hours
                    continue
                
                # Get the user
                user = User.query.filter_by(id=settings.user_id).first()
                if not user:
                    continue
                
                # Decode the access URL
                try:
                    access_url = base64.b64decode(settings.access_url.encode()).decode()
                except:
                    app.logger.error(f"Error decoding access URL for user {settings.user_id}")
                    continue
                
                # Fetch accounts and transactions (last 3 days for scheduled sync)
                raw_data = simplefin_client.get_accounts_with_transactions(access_url, days_back=3)
                
                if not raw_data:
                    app.logger.error(f"Failed to fetch SimpleFin data for user {settings.user_id}")
                    continue
                
                # Process the raw data
                accounts = simplefin_client.process_raw_accounts(raw_data)
                
                # Find all SimpleFin accounts for this user
                user_accounts = Account.query.filter_by(
                    user_id=settings.user_id,
                    import_source='simplefin'
                ).all()
                
                # Create a mapping of external IDs to account objects
                account_map = {acc.external_id: acc for acc in user_accounts if acc.external_id}
                
                # Track statistics
                accounts_updated = 0
                transactions_added = 0
                
                # Update each account
                for sf_account in accounts:
                    external_id = sf_account.get('id')
                    if not external_id:
                        continue
                    
                    # Find the corresponding account
                    if external_id in account_map:
                        account = account_map[external_id]
                        
                        # Update account details
                        account.balance = sf_account.get('balance', account.balance)
                        account.last_sync = datetime.utcnow()
                        accounts_updated += 1
                        
                        # Create transaction objects using the enhanced client method
                        transaction_objects, _ = simplefin_client.create_transactions_from_account(
                            sf_account,
                            account,
                            settings.user_id,
                            detect_internal_transfer,
                            auto_categorize_transaction,
                            get_category_id
                        )
                        
                        # Filter out existing transactions and add new ones
                        for transaction in transaction_objects:
                            # Check if transaction already exists
                            existing = Expense.query.filter_by(
                                user_id=settings.user_id,
                                external_id=transaction.external_id,
                                import_source='simplefin'
                            ).first()
                            
                            if not existing:
                                db.session.add(transaction)
                                transactions_added += 1
                                
                                # Handle account balance updates for transfers
                                if transaction.transaction_type == 'transfer' and transaction.destination_account_id:
                                    # Find the destination account
                                    to_account = Account.query.get(transaction.destination_account_id)
                                    if to_account and to_account.user_id == settings.user_id:
                                        # For transfers, add to destination account balance
                                        to_account.balance += transaction.amount
                
                # Commit changes for this user
                if accounts_updated > 0 or transactions_added > 0:
                    db.session.commit()
                    
                    # Update the SimpleFin settings last_sync time
                    settings.last_sync = datetime.utcnow()
                    db.session.commit()
                    
                    app.logger.info(f"SimpleFin sync for user {settings.user_id}: {accounts_updated} accounts updated, {transactions_added} transactions added")
                
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in scheduled SimpleFin sync: {str(e)}")


def sync_simplefin_for_user(user_id):
    """Sync SimpleFin accounts for a specific user - to be called on login"""
    with app.app_context():
        app.logger.info(f"Starting SimpleFin sync for user {user_id} on login")
        
        try:
            # Get the user's SimpleFin settings
            settings = SimpleFin.query.filter_by(user_id=user_id, enabled=True).first()
            
            if not settings:
                app.logger.info(f"No SimpleFin settings found for user {user_id}")
                return
            
            # Decode the access URL
            try:
                access_url = base64.b64decode(settings.access_url.encode()).decode()
            except:
                app.logger.error(f"Error decoding access URL for user {user_id}")
                return
            
            # Fetch accounts and transactions (last 3 days for a login sync)
            simplefin_instance = simplefin_client
            raw_data = simplefin_instance.get_accounts_with_transactions(access_url, days_back=3)
            
            if not raw_data:
                app.logger.error(f"Failed to fetch SimpleFin data for user {user_id}")
                return
            
            # Process the raw data
            accounts = simplefin_instance.process_raw_accounts(raw_data)
            
            # Find all SimpleFin accounts for this user
            user_accounts = Account.query.filter_by(
                user_id=user_id,
                import_source='simplefin'
            ).all()
            
            # Create a mapping of external IDs to account objects
            account_map = {acc.external_id: acc for acc in user_accounts if acc.external_id}
            
            # Track statistics
            accounts_updated = 0
            transactions_added = 0
            
            # Update each account
            for sf_account in accounts:
                external_id = sf_account.get('id')
                if not external_id:
                    continue
                
                # Find the corresponding account
                if external_id in account_map:
                    account = account_map[external_id]
                    
                    # Update account details
                    account.balance = sf_account.get('balance', account.balance)
                    account.last_sync = datetime.utcnow()
                    accounts_updated += 1
                    
                    # Create transaction objects
                    transaction_objects, _ = simplefin_instance.create_transactions_from_account(
                        sf_account,
                        account,
                        user_id,
                        detect_internal_transfer,
                        auto_categorize_transaction,
                        get_category_id
                    )
                    
                    # Filter out existing transactions and add new ones
                    for transaction in transaction_objects:
                        # Check if transaction already exists
                        existing = Expense.query.filter_by(
                            user_id=user_id,
                            external_id=transaction.external_id,
                            import_source='simplefin'
                        ).first()
                        
                        if not existing:
                            db.session.add(transaction)
                            transactions_added += 1
                            
                            # Handle account balance updates for transfers
                            if transaction.transaction_type == 'transfer' and transaction.destination_account_id:
                                # Find the destination account
                                to_account = Account.query.get(transaction.destination_account_id)
                                if to_account and to_account.user_id == user_id:
                                    # For transfers, add to destination account balance
                                    to_account.balance += transaction.amount
            
            # Commit changes for this user
            if accounts_updated > 0 or transactions_added > 0:
                db.session.commit()
                
                # Update the SimpleFin settings last_sync time
                settings.last_sync = datetime.utcnow()
                db.session.commit()
                
                app.logger.info(f"SimpleFin sync on login for user {user_id}: {accounts_updated} accounts updated, {transactions_added} transactions added")
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in SimpleFin sync on login: {str(e)}")

@app.route('/category_mappings')
@login_required_dev
@demo_time_limited
def manage_category_mappings():
    """View and manage category mappings for auto-categorization"""
    # Get all mappings for the current user
    mappings = CategoryMapping.query.filter_by(user_id=current_user.id).order_by(
        CategoryMapping.active.desc(),
        CategoryMapping.priority.desc(), 
        CategoryMapping.match_count.desc()
    ).all()
    
    # Get all categories for the dropdown
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    
    return render_template('category_mappings.html', 
                          mappings=mappings,
                          categories=categories)
@app.route('/category_mappings/create_defaults', methods=['POST'])
@login_required_dev
@demo_time_limited
def create_default_mappings_route():
    """Create default category mappings for the current user (on demand)"""
    try:
        # Get current count to check if any were created
        current_count = CategoryMapping.query.filter_by(user_id=current_user.id).count()
        
        # Call the function to create default mappings
        create_default_category_mappings(current_user.id)
        
        # Get new count to see how many were created
        new_count = CategoryMapping.query.filter_by(user_id=current_user.id).count()
        created_count = new_count - current_count
        
        # Return success response
        return jsonify({
            'success': True,
            'count': created_count,
            'message': f'Successfully created {created_count} default mapping rules.'
        })
        
    except Exception as e:
        app.logger.error(f"Error creating default mappings: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating default mappings: {str(e)}'
        }), 500
    
@app.route('/bulk_categorize_transactions', methods=['POST'])
@login_required_dev
def bulk_categorize_transactions():
    """Categorize all uncategorized transactions using category mapping rules"""
    try:
        # Get all uncategorized transactions for the current user
        uncategorized = Expense.query.filter_by(
            user_id=current_user.id,
            category_id=None
        ).all()
        
        # Track statistics
        total_count = len(uncategorized)
        categorized_count = 0
        
        # Process each transaction
        for expense in uncategorized:
            # Skip if no description
            if not expense.description:
                continue
                
            # Try to auto-categorize
            category_id = auto_categorize_transaction(expense.description, current_user.id)
            
            # If we found a category, update the transaction
            if category_id:
                expense.category_id = category_id
                categorized_count += 1
        
        # Save all changes
        db.session.commit()
        
        flash(f'Successfully categorized {categorized_count} out of {total_count} transactions!')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error bulk categorizing transactions: {str(e)}")
        flash(f'Error: {str(e)}')
        
    # Determine where to redirect based on the referrer
    referrer = request.referrer
    if 'transactions' in referrer:
        return redirect(url_for('transactions'))
    elif 'category_mappings' in referrer:
        return redirect(url_for('manage_category_mappings'))
    else:
        return redirect(url_for('dashboard'))


@app.route('/category_mappings/add', methods=['POST'])
@login_required_dev
@demo_time_limited
def add_category_mapping():
    """Add a new category mapping rule"""
    keyword = request.form.get('keyword', '').strip()
    category_id = request.form.get('category_id')
    is_regex = request.form.get('is_regex') == 'on'
    priority = int(request.form.get('priority', 0))
    
    # Validate inputs
    if not keyword or not category_id:
        flash('Keyword and category are required.')
        return redirect(url_for('manage_category_mappings'))
    
    # Check if mapping already exists
    existing = CategoryMapping.query.filter_by(
        user_id=current_user.id,
        keyword=keyword
    ).first()
    
    if existing:
        flash('A mapping with this keyword already exists. Please edit the existing one.')
        return redirect(url_for('manage_category_mappings'))
    
    # Create new mapping
    mapping = CategoryMapping(
        user_id=current_user.id,
        keyword=keyword,
        category_id=category_id,
        is_regex=is_regex,
        priority=priority,
        active=True
    )
    
    db.session.add(mapping)
    db.session.commit()
    
    flash('Category mapping rule added successfully.')
    return redirect(url_for('manage_category_mappings'))

@app.route('/category_mappings/edit/<int:mapping_id>', methods=['POST'])
@login_required_dev
@demo_time_limited
def edit_category_mapping(mapping_id):
    """Edit an existing category mapping rule"""
    mapping = CategoryMapping.query.get_or_404(mapping_id)
    
    # Check if mapping belongs to current user
    if mapping.user_id != current_user.id:
        flash('You don\'t have permission to edit this mapping.')
        return redirect(url_for('manage_category_mappings'))
    
    # Update fields
    mapping.keyword = request.form.get('keyword', '').strip()
    mapping.category_id = request.form.get('category_id')
    mapping.is_regex = request.form.get('is_regex') == 'on'
    mapping.priority = int(request.form.get('priority', 0))
    
    db.session.commit()
    
    flash('Category mapping updated successfully.')
    return redirect(url_for('manage_category_mappings'))

@app.route('/category_mappings/toggle/<int:mapping_id>', methods=['POST'])
@login_required_dev
def toggle_category_mapping(mapping_id):
    """Toggle the active status of a mapping"""
    mapping = CategoryMapping.query.get_or_404(mapping_id)
    
    # Check if mapping belongs to current user
    if mapping.user_id != current_user.id:
        flash('You don\'t have permission to modify this mapping.')
        return redirect(url_for('manage_category_mappings'))
    
    # Toggle active status
    mapping.active = not mapping.active
    db.session.commit()
    
    status = "activated" if mapping.active else "deactivated"
    flash(f'Category mapping {status} successfully.')
    
    return redirect(url_for('manage_category_mappings'))

@app.route('/category_mappings/delete/<int:mapping_id>', methods=['POST'])
@login_required_dev
def delete_category_mapping(mapping_id):
    """Delete a category mapping rule"""
    mapping = CategoryMapping.query.get_or_404(mapping_id)
    
    # Check if mapping belongs to current user
    if mapping.user_id != current_user.id:
        flash('You don\'t have permission to delete this mapping.')
        return redirect(url_for('manage_category_mappings'))
    
    db.session.delete(mapping)
    db.session.commit()
    
    flash('Category mapping deleted successfully.')
    return redirect(url_for('manage_category_mappings'))

@app.route('/category_mappings/learn_from_history', methods=['POST'])
@login_required_dev
def learn_from_transaction_history():
    """Analyze transaction history to create category mapping suggestions"""
    # Get number of days to analyze from the form
    days = int(request.form.get('days', 30))
    
    # Calculate start date
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get transactions from the specified period that have categories
    transactions = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.category_id.isnot(None)
    ).all()
    
    # Group transactions by category and description pattern
    patterns = {}
    for transaction in transactions:
        # Skip transactions without descriptions
        if not transaction.description:
            continue
            
        # Clean up description and extract a key word/phrase
        keyword = extract_keywords(transaction.description)
        if not keyword:
            continue
            
        # Create a unique key for this keyword + category combo
        key = f"{keyword}_{transaction.category_id}"
        
        if key not in patterns:
            patterns[key] = {
                'keyword': keyword,
                'category_id': transaction.category_id,
                'count': 0,
                'total_amount': 0,
                'transactions': []
            }
            
        # Update the pattern
        patterns[key]['count'] += 1
        patterns[key]['total_amount'] += transaction.amount
        patterns[key]['transactions'].append(transaction.id)
    
    # Find significant patterns (occurred at least 3 times)
    significant_patterns = [p for p in patterns.values() if p['count'] >= 3]
    
    # Sort by frequency
    significant_patterns.sort(key=lambda x: x['count'], reverse=True)
    
    # Create mappings for these patterns (only if they don't already exist)
    created_count = 0
    for pattern in significant_patterns[:15]:  # Limit to top 15
        # Check if this pattern already exists
        existing = CategoryMapping.query.filter_by(
            user_id=current_user.id,
            keyword=pattern['keyword'],
            category_id=pattern['category_id']
        ).first()
        
        if not existing:
            # Create a new mapping
            mapping = CategoryMapping(
                user_id=current_user.id,
                keyword=pattern['keyword'],
                category_id=pattern['category_id'],
                is_regex=False,
                priority=0,
                match_count=pattern['count'],
                active=True
            )
            
            db.session.add(mapping)
            created_count += 1
    
    if created_count > 0:
        db.session.commit()
        flash(f'Created {created_count} new category mapping rules from your transaction history.')
    else:
        flash('No new mapping patterns were found in your transaction history.')
    
    return redirect(url_for('manage_category_mappings'))


@app.route('/category_mappings/upload', methods=['POST'])
@login_required_dev
def upload_category_mappings():
    """Upload and import category mappings from a CSV file"""
    if 'mapping_file' not in request.files:
        flash('No file provided')
        return redirect(url_for('manage_category_mappings'))
    
    mapping_file = request.files['mapping_file']
    
    if mapping_file.filename == '':
        flash('No file selected')
        return redirect(url_for('manage_category_mappings'))
    
    # Case-insensitive extension check
    if not mapping_file.filename.lower().endswith('.csv'):
        flash('File must be a CSV')
        return redirect(url_for('manage_category_mappings'))
    
    try:
        # Read file content
        file_content = mapping_file.read().decode('utf-8')
        
        # Parse CSV
        import csv
        import io
        
        csv_reader = csv.DictReader(io.StringIO(file_content))
        required_fields = ['keyword', 'category']
        
        # Validate CSV structure
        if not all(field in csv_reader.fieldnames for field in required_fields):
            flash(f'CSV must contain at least these columns: {", ".join(required_fields)}')
            return redirect(url_for('manage_category_mappings'))
        
        # Process rows
        imported_count = 0
        skipped_count = 0
        
        for row in csv_reader:
            try:
                # Get required fields
                keyword = row['keyword'].strip()
                category_name = row['category'].strip()
                
                # Get optional fields with defaults
                is_regex = str(row.get('is_regex', 'false')).lower() in ['true', '1', 'yes', 'y']
                priority = int(row.get('priority', 0))
                
                # Skip empty keywords
                if not keyword or not category_name:
                    skipped_count += 1
                    continue
                
                # Check if mapping already exists
                existing = CategoryMapping.query.filter_by(
                    user_id=current_user.id,
                    keyword=keyword
                ).first()
                
                if existing:
                    # Skip duplicate mappings
                    skipped_count += 1
                    continue
                
                # Find the category by name (case-insensitive search)
                # First try to find exact match
                category = Category.query.filter(
                    Category.user_id == current_user.id,
                    func.lower(Category.name) == func.lower(category_name)
                ).first()
                
                # If not found, try subcategories
                if not category:
                    category = Category.query.filter(
                        Category.user_id == current_user.id,
                        Category.parent_id.isnot(None),
                        func.lower(Category.name) == func.lower(category_name)
                    ).first()
                
                # If still not found, try partial matches
                if not category:
                    category = Category.query.filter(
                        Category.user_id == current_user.id,
                        func.lower(Category.name).like(f"%{category_name.lower()}%")
                    ).first()
                
                # If no category found, use "Other"
                if not category:
                    category = Category.query.filter_by(
                        name='Other',
                        user_id=current_user.id,
                        is_system=True
                    ).first()
                
                # If we still can't find a category, skip this mapping
                if not category:
                    skipped_count += 1
                    continue
                
                # Create mapping
                new_mapping = CategoryMapping(
                    user_id=current_user.id,
                    keyword=keyword,
                    category_id=category.id,
                    is_regex=is_regex,
                    priority=priority,
                    match_count=0,
                    active=True
                )
                
                db.session.add(new_mapping)
                imported_count += 1
                
            except Exception as e:
                app.logger.error(f"Error importing mapping row: {str(e)}")
                skipped_count += 1
                continue
        
        # Commit all successfully parsed mappings
        if imported_count > 0:
            db.session.commit()
            
        flash(f'Successfully imported {imported_count} mappings. Skipped {skipped_count} rows.')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error importing category mappings: {str(e)}")
        flash(f'Error importing mappings: {str(e)}')
    
    return redirect(url_for('manage_category_mappings'))

@app.route('/category_mappings/export', methods=['GET'])
@login_required_dev
def export_category_mappings():
    """Export category mappings to a CSV file"""
    try:
        # Get all active mappings for the current user
        mappings = CategoryMapping.query.filter_by(
            user_id=current_user.id,
            active=True
        ).all()
        
        if not mappings:
            flash('No active mappings to export.')
            return redirect(url_for('manage_category_mappings'))
        
        # Create CSV in memory
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header row
        writer.writerow(['keyword', 'category', 'is_regex', 'priority'])
        
        # Write data rows
        for mapping in mappings:
            category_name = mapping.category.name if mapping.category else "Unknown"
            writer.writerow([
                mapping.keyword,
                category_name,
                'true' if mapping.is_regex else 'false',
                mapping.priority
            ])
        
        # Prepare for download
        output.seek(0)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"category_mappings_{timestamp}.csv"
        
        # Send file
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error exporting category mappings: {str(e)}")
        flash(f'Error exporting mappings: {str(e)}')
        return redirect(url_for('manage_category_mappings'))

#--------------------
# ROUTES: House maintanance
#--------------------

@app.route('/update_notification_preferences', methods=['POST'])
@login_required_dev
def update_notification_preferences():
    """Update user's notification preferences"""
    current_user.monthly_report_enabled = 'monthly_report_enabled' in request.form
    db.session.commit()
    flash('Notification preferences updated successfully')
    return redirect(url_for('profile'))




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
        init_default_currencies()
        print("Tables created successfully")
    except Exception as e:
        print(f"ERROR CREATING TABLES: {str(e)}")

# Register OIDC routes
if oidc_enabled:
    register_oidc_routes(app, User, db)        

if __name__ == '__main__':
    app.run(debug=True, port=5001)
