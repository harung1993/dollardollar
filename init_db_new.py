#!/usr/bin/env python3
"""
Initialize database for DollarDollar application
Creates all tables and optionally adds demo data
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from src import create_app
from src.extensions import db
from src.models import (
    User, Account, Category, Currency,
    Expense, Budget, Group, RecurringExpense,
    Portfolio, Investment, CategoryMapping,
    Settlement, Tag
)

def init_database(add_demo_data=False):
    """Initialize the database"""
    print("="*60)
    print("DollarDollar Database Initialization")
    print("="*60)

    # Create app
    print("\n1. Creating Flask application...")
    app = create_app()

    with app.app_context():
        print("2. Dropping existing tables (if any)...")
        db.drop_all()

        print("3. Creating all tables...")
        db.create_all()

        print("\n✓ Tables created:")
        for table in db.metadata.sorted_tables:
            print(f"  - {table.name}")

        print("\n4. Creating base currency (USD)...")
        usd = Currency(
            code='USD',
            name='US Dollar',
            symbol='$',
            is_base=True,
            rate_to_base=1.0
        )
        db.session.add(usd)
        db.session.commit()
        print("✓ Base currency created")

        if add_demo_data:
            print("\n5. Adding demo data...")
            add_demo_user(app, db)

        print("\n" + "="*60)
        print("✅ Database initialized successfully!")
        print("="*60)
        print(f"\nDatabase location: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print("\nNext steps:")
        print("1. Run: /opt/miniconda3/bin/python3 app.py")
        print("2. Access: http://localhost:5001")
        print("3. Create an account or use demo@example.com (if demo data added)")
        print("="*60)

def add_demo_user(app, db):
    """Add a demo user with sample data"""
    from werkzeug.security import generate_password_hash
    from datetime import datetime, timedelta

    # Create demo user
    demo_user = User(
        id='demo@example.com',  # id is the email field
        password_hash=generate_password_hash('demo123'),
        is_admin=False,
        user_color='#4CAF50'
    )
    db.session.add(demo_user)
    db.session.commit()
    print("✓ Demo user created: demo@example.com / demo123")

    # Create default categories
    categories = [
        Category(name='Food & Dining', type='expense', user_id=demo_user.id, icon='🍔'),
        Category(name='Transportation', type='expense', user_id=demo_user.id, icon='🚗'),
        Category(name='Shopping', type='expense', user_id=demo_user.id, icon='🛍️'),
        Category(name='Entertainment', type='expense', user_id=demo_user.id, icon='🎬'),
        Category(name='Bills & Utilities', type='expense', user_id=demo_user.id, icon='💡'),
        Category(name='Salary', type='income', user_id=demo_user.id, icon='💰'),
    ]
    db.session.add_all(categories)
    db.session.commit()
    print(f"✓ Created {len(categories)} default categories")

    # Create a demo account
    demo_account = Account(
        name='Checking Account',
        type='checking',
        balance=5000.00,
        user_id=demo_user.id,
        currency_code='USD'
    )
    db.session.add(demo_account)
    db.session.commit()
    print(f"✓ Created demo account: {demo_account.name} (${demo_account.balance})")

    # Create some demo transactions
    transactions = []
    base_date = datetime.now()

    demo_transactions = [
        ('Coffee', -4.50, categories[0].id, -1),
        ('Grocery Shopping', -85.20, categories[0].id, -2),
        ('Gas', -45.00, categories[1].id, -3),
        ('Monthly Salary', 3500.00, categories[5].id, -5),
        ('Netflix Subscription', -15.99, categories[3].id, -7),
        ('Electric Bill', -120.00, categories[4].id, -10),
        ('Lunch', -12.50, categories[0].id, -1),
        ('Uber', -18.00, categories[1].id, -2),
    ]

    for desc, amount, cat_id, days_ago in demo_transactions:
        transaction = Expense(
            amount=abs(amount),
            description=desc,
            date=base_date + timedelta(days=days_ago),
            category_id=cat_id,
            account_id=demo_account.id,
            user_id=demo_user.id,
            type='income' if amount > 0 else 'expense'
        )
        transactions.append(transaction)

    db.session.add_all(transactions)
    db.session.commit()
    print(f"✓ Created {len(transactions)} demo transactions")

    # Create a demo budget
    budget = Budget(
        category_id=categories[0].id,  # Food & Dining
        amount=400.00,
        period='monthly',
        user_id=demo_user.id
    )
    db.session.add(budget)
    db.session.commit()
    print(f"✓ Created demo budget: ${budget.amount}/month for Food & Dining")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Initialize DollarDollar database')
    parser.add_argument('--demo', action='store_true', help='Add demo data')
    args = parser.parse_args()

    try:
        init_database(add_demo_data=args.demo)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
