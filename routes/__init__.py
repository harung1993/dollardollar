from flask import Flask

from routes.auth_routes import auth_bp
from routes.demo_routes import demo_bp
from routes.transaction_routes import transaction_bp


def register_blueprints(app: Flask):
    """Register all route blueprints with the app."""
    # Import blueprints
    # from account_routes import account_bp
    # from admin_routes import admin_bp

    # from currency_routes import currency_bp
    # from dashboard_routes import dashboard_bp
    # from expense_routes import expense_bp
    # from group_routes import group_bp
    # from settlement_routes import settlement_bp
    # Register blueprints with URL prefixes (optional)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    # app.register_blueprint(dashboard_bp)
    # app.register_blueprint(expense_bp, url_prefix="/expenses")
    # app.register_blueprint(group_bp, url_prefix="/groups")
    # app.register_blueprint(admin_bp, url_prefix="/admin")
    # app.register_blueprint(settlement_bp, url_prefix="/settlements")
    # app.register_blueprint(currency_bp, url_prefix="/currencies")
    app.register_blueprint(transaction_bp, url_prefix="/transactions")
    # app.register_blueprint(account_bp, url_prefix="/accounts")
    app.register_blueprint(demo_bp, url_prefix="/demo")
