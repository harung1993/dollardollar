from flask import Flask  # noqa: D104

from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
from routes.currency_routes import currency_bp
from routes.dashboard_routes import dashboard_bp
from routes.demo_routes import demo_bp
from routes.expense_routes import expense_bp
from routes.group_routes import group_bp
from routes.recurring_routes import recurring_bp
from routes.settlement_routes import settlement_bp
from routes.tag_routes import tag_bp
from routes.timezone_routes import timezone_bp
from routes.transaction_routes import transaction_bp


def register_blueprints(app: Flask):
    """Register all route blueprints with the app."""
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(expense_bp, url_prefix="/expenses")
    app.register_blueprint(tag_bp, url_prefix="/tags")
    app.register_blueprint(recurring_bp, url_prefix="/recurring")
    app.register_blueprint(group_bp, url_prefix="/groups")
    app.register_blueprint(settlement_bp, url_prefix="/settlements")
    app.register_blueprint(currency_bp, url_prefix="/currencies")
    app.register_blueprint(transaction_bp, url_prefix="/transactions")
    # app.register_blueprint(account_bp, url_prefix="/accounts")
    app.register_blueprint(demo_bp, url_prefix="/demo")
    app.register_blueprint(timezone_bp, url_prefix="/timezone")
