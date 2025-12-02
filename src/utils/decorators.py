"""
Custom decorators for authentication and access control
"""

from functools import wraps
from flask import flash, redirect, url_for, current_app
from flask_login import current_user, login_user, login_required
from src.models.user import User
from src.extensions import db

def login_required_dev(f):
    """
    Decorator for development mode - auto-logs in dev user
    In production, requires normal authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.config['DEVELOPMENT_MODE']:
            if not current_user.is_authenticated:
                # Get dev credentials from config
                dev_email = current_app.config.get('DEV_USER_EMAIL', 'dev@example.com')
                dev_password = current_app.config.get('DEV_USER_PASSWORD', 'dev')
                
                # Get or create dev user
                dev_user = User.query.filter_by(id=dev_email).first()
                if not dev_user:
                    dev_user = User(
                        id=dev_email,
                        name='Developer',
                        is_admin=True
                    )
                    dev_user.set_password(dev_password)
                    db.session.add(dev_user)
                    db.session.commit()
                # Auto login dev user
                login_user(dev_user)
            return f(*args, **kwargs)
        # Normal authentication for non-dev mode
        return login_required(f)(*args, **kwargs)
    return decorated_function


def restrict_demo_access(f):
    """
    Decorator to restrict demo users from accessing certain pages
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            demo_timeout = current_app.extensions.get('demo_timeout')
            if demo_timeout and demo_timeout.is_demo_user(current_user.id):
                flash('Demo users cannot access this page.')
                return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function
