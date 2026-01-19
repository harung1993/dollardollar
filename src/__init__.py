"""
Application factory for DollarDollar
Creates and configures the Flask application
"""

import os
import logging
import pytz
from flask import Flask
from src.config import get_config
from src.extensions import db, login_manager, mail, migrate, scheduler, init_extensions

# Import models (needed for migrations and relationships)
from src import models

def create_app(config_name=None):
    """Create and configure the Flask application"""
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Load configuration
    config = get_config()
    app.config.from_object(config)
    
    # Ensure instance path exists for SQLite
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass
    
    # Set up SQLite database path if not using PostgreSQL
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, "expenses.db")}'
    
    # Set up logging
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    logging.basicConfig(level=log_level)
    
    # Initialize Flask extensions
    init_extensions(app)
    
    # Configure login manager
    @login_manager.user_loader
    def load_user(user_id):
        from src.models.user import User
        return User.query.filter_by(id=user_id).first()
    
    # Set up OIDC if enabled
    oidc_enabled = False
    try:
        from integrations.oidc.auth import setup_oidc_config, register_oidc_routes
        from integrations.oidc.user import extend_user_model
        
        oidc_enabled = setup_oidc_config(app)
        if oidc_enabled:
            # Extend User model with OIDC methods
            from src.models.user import User
            User = extend_user_model(db, User)
            # Register OIDC routes
            register_oidc_routes(app)
            app.logger.info("OIDC authentication enabled")
    except Exception as e:
        app.logger.warning(f"OIDC setup failed: {e}")
    
    # Set up SimpleFin client
    try:
        from integrations.simplefin.client import SimpleFin
        simplefin_client = SimpleFin(app)
        app.extensions['simplefin_client'] = simplefin_client
    except Exception as e:
        app.logger.warning(f"SimpleFin client setup failed: {e}")
    
    # Set up FMP cache for investments
    try:
        from integrations.investments.fmp_cache import FMPCache
        fmp_cache = FMPCache()
        app.extensions['fmp_cache'] = fmp_cache
    except Exception as e:
        app.logger.warning(f"FMP cache setup failed: {e}")
    
    # Set up demo timeout middleware
    try:
        from src.utils.session_timeout import DemoTimeout
        demo_timeout = DemoTimeout(
            timeout_minutes=app.config.get('DEMO_TIMEOUT_MINUTES', 10),
            demo_users=[
                'demo@example.com',
                'demo1@example.com',
                'demo2@example.com',
            ]
        )
        demo_timeout.init_app(app)
        app.extensions['demo_timeout'] = demo_timeout
    except Exception as e:
        app.logger.warning(f"Demo timeout setup failed: {e}")
    
    # Register blueprints (services)
    # Currency Service
    from src.services.currency import bp as currency_bp
    app.register_blueprint(currency_bp)

    # Category Service (has 2 blueprints: categories and mappings)
    from src.services.category import bp as category_bp, mapping_bp as category_mapping_bp
    app.register_blueprint(category_bp)
    app.register_blueprint(category_mapping_bp)

    # Auth Service (has 2 blueprints: auth and admin)
    from src.services.auth import bp as auth_bp, admin_bp as admin_auth_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_auth_bp)

    # Transaction Service (has 2 blueprints: transaction and tag)
    from src.services.transaction import bp as transaction_bp, tag_bp as tag_transaction_bp
    app.register_blueprint(transaction_bp)
    app.register_blueprint(tag_transaction_bp)

    # Account Service (has 2 blueprints: account and simplefin)
    from src.services.account import bp as account_bp, simplefin_bp as simplefin_account_bp
    app.register_blueprint(account_bp)
    app.register_blueprint(simplefin_account_bp)

    # Budget Service
    from src.services.budget import bp as budget_bp
    app.register_blueprint(budget_bp)

    # Group Service (has 2 blueprints: group and settlement)
    from src.services.group import bp as group_bp, settlement_bp as settlement_group_bp
    app.register_blueprint(group_bp)
    app.register_blueprint(settlement_group_bp)

    # Recurring Service
    from src.services.recurring import bp as recurring_bp
    app.register_blueprint(recurring_bp)

    # Investment Service
    from src.services.investment import bp as investment_bp
    app.register_blueprint(investment_bp)

    # Analytics Service
    from src.services.analytics import bp as analytics_bp
    app.register_blueprint(analytics_bp)

    # Notification Service (internal - no blueprint)
    # NotificationService is imported directly when needed

    # Register context processors
    from src.utils.context_processors import utility_processor
    app.context_processor(utility_processor)

    # For now, register a basic route from the old app.py
    # This will be replaced as we extract services
    register_legacy_routes(app)

    # Set up scheduled tasks
    setup_scheduled_tasks(app)
    
    app.logger.info(f"DollarDollar application created successfully")
    app.logger.info(f"OIDC enabled: {oidc_enabled}")
    app.logger.info(f"SimpleFin enabled: {app.config.get('SIMPLEFIN_ENABLED', False)}")
    app.logger.info(f"Investment tracking enabled: {app.config.get('INVESTMENT_TRACKING_ENABLED', False)}")
    
    return app


def register_legacy_routes(app):
    """
    Register routes from the legacy app.py temporarily
    These will be moved to service blueprints gradually
    """
    from flask import render_template, redirect, url_for, request, jsonify
    from flask_login import login_required, current_user
    from src.utils.decorators import login_required_dev

    @app.route('/')
    def index():
        # If user is logged in, redirect to dashboard
        if current_user.is_authenticated:
            return redirect(url_for('analytics.dashboard'))
        # Otherwise redirect to login
        return redirect(url_for('auth.login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Redirect to analytics dashboard
        return redirect(url_for('analytics.dashboard'))

    @app.route('/detect_recurring_transactions')
    @login_required_dev
    def detect_recurring_transactions_legacy():
        """API endpoint to detect recurring transactions - legacy route for JavaScript"""
        try:
            from integrations.recurring.detector import detect_recurring_transactions
            from src.models.recurring import IgnoredRecurringPattern
            from src.utils.helpers import get_base_currency

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
            base_currency = get_base_currency(current_user)
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
                    'id': candidate_id,
                    'description': candidate['description'],
                    'amount': float(candidate['amount']),
                    'frequency': candidate['frequency'],
                    'occurrences': len(candidate.get('dates', [])),
                    'pattern_key': pattern_key,
                    'currency_symbol': currency_symbol
                }
                candidate_data.append(candidate_dict)

            return jsonify({
                'success': True,
                'candidates': candidate_data,
                'count': len(candidate_data)
            })

        except Exception as e:
            app.logger.error(f"Error detecting recurring transactions: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'candidates': []
            }), 500


def setup_scheduled_tasks(app):
    """Set up APScheduler cron jobs"""
    
    @scheduler.task('cron', id='monthly_reports', day=1, hour=1, minute=0)
    def scheduled_monthly_reports():
        """Run on the 1st day of each month at 1:00 AM"""
        with app.app_context():
            try:
                # Import here to avoid circular imports
                # from src.services.notification.service import NotificationService
                # notification_service = NotificationService()
                # notification_service.send_automatic_monthly_reports()
                app.logger.info("Monthly reports task executed")
            except Exception as e:
                app.logger.error(f"Monthly reports failed: {e}")
    
    @scheduler.task('cron', id='simplefin_sync', hour=23, minute=0)
    def scheduled_simplefin_sync():
        """Run every day at 11:00 PM"""
        with app.app_context():
            try:
                # Import here to avoid circular imports
                # from src.services.account.service import AccountService
                # account_service = AccountService()
                # account_service.sync_all_simplefin_accounts()
                app.logger.info("SimpleFin sync task executed")
            except Exception as e:
                app.logger.error(f"SimpleFin sync failed: {e}")
