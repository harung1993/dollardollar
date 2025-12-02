"""
CLI commands for database management and utilities
"""

import click
from flask.cli import with_appcontext
from src.extensions import db
from src.models.user import User
from src.models.currency import Currency

def register_commands(app):
    """Register all CLI commands with the app"""
    
    @app.cli.command('init-db')
    @with_appcontext
    def init_db_command():
        """Initialize the database"""
        db.drop_all()
        db.create_all()
        
        # Create default currencies
        create_default_currencies()
        
        # Create dev user in development mode
        if app.config.get('DEVELOPMENT_MODE'):
            dev_email = app.config.get('DEV_USER_EMAIL', 'dev@example.com')
            dev_password = app.config.get('DEV_USER_PASSWORD', 'dev')
            
            dev_user = User(
                id=dev_email,
                name='Developer',
                is_admin=True
            )
            dev_user.set_password(dev_password)
            db.session.add(dev_user)
            db.session.commit()
            
            click.echo(f'Development user created: {dev_email}')
        
        click.echo('Database initialized successfully!')
    
    @app.cli.command('reset-db')
    @with_appcontext
    def reset_db_command():
        """Reset the database (drop and recreate)"""
        if click.confirm('This will delete all data. Are you sure?'):
            db.drop_all()
            db.create_all()
            create_default_currencies()
            click.echo('Database reset successfully!')
        else:
            click.echo('Database reset cancelled.')
    
    @app.cli.command('create-admin')
    @click.argument('email')
    @click.argument('password')
    @with_appcontext
    def create_admin_command(email, password):
        """Create an admin user"""
        user = User.query.filter_by(id=email).first()
        if user:
            click.echo(f'User {email} already exists!')
            return
        
        user = User(
            id=email,
            name='Admin',
            is_admin=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f'Admin user created: {email}')


def create_default_currencies():
    """Create default currencies in the database"""
    default_currencies = [
        {'code': 'USD', 'name': 'US Dollar', 'symbol': '$', 'rate_to_base': 1.0, 'is_base': True},
        {'code': 'EUR', 'name': 'Euro', 'symbol': '€', 'rate_to_base': 1.1},
        {'code': 'GBP', 'name': 'British Pound', 'symbol': '£', 'rate_to_base': 1.25},
        {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': '¥', 'rate_to_base': 0.0091},
        {'code': 'CAD', 'name': 'Canadian Dollar', 'symbol': 'C$', 'rate_to_base': 0.74},
        {'code': 'AUD', 'name': 'Australian Dollar', 'symbol': 'A$', 'rate_to_base': 0.65},
        {'code': 'INR', 'name': 'Indian Rupee', 'symbol': '₹', 'rate_to_base': 0.012},
    ]
    
    for curr_data in default_currencies:
        existing = Currency.query.filter_by(code=curr_data['code']).first()
        if not existing:
            currency = Currency(**curr_data)
            db.session.add(currency)
    
    db.session.commit()
