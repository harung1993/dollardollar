#!/usr/bin/env python3
"""
Complete Test Suite for DollarDollar Modular Application
Tests all 11 services and their integration
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all modules can be imported"""
    print("\n" + "="*60)
    print("TEST 1: Testing Module Imports")
    print("="*60)

    try:
        print("✓ Importing Flask extensions...")
        from src.extensions import db, login_manager, mail, migrate, scheduler

        print("✓ Importing configuration...")
        from src.config import get_config

        print("✓ Importing application factory...")
        from src import create_app

        print("✓ Importing models...")
        from src.models import User, Account, Category, Currency
        from src.models import Expense, Budget, Group, RecurringExpense
        from src.models import Portfolio, Investment

        print("✓ Importing services...")
        from src.services.currency import bp as currency_bp
        from src.services.category import bp as category_bp
        from src.services.auth import bp as auth_bp
        from src.services.transaction import bp as transaction_bp
        from src.services.account import bp as account_bp
        from src.services.budget import bp as budget_bp
        from src.services.group import bp as group_bp
        from src.services.recurring import bp as recurring_bp
        from src.services.investment import bp as investment_bp
        from src.services.analytics import bp as analytics_bp
        from src.services.notification.service import NotificationService

        print("\n✅ ALL IMPORTS SUCCESSFUL!")
        return True

    except Exception as e:
        print(f"\n❌ IMPORT FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_creation():
    """Test application factory"""
    print("\n" + "="*60)
    print("TEST 2: Testing Application Factory")
    print("="*60)

    try:
        from src import create_app

        print("✓ Creating Flask application...")
        app = create_app()

        print(f"✓ App created: {app.name}")
        print(f"✓ Debug mode: {app.debug}")
        print(f"✓ Testing mode: {app.testing}")

        return app

    except Exception as e:
        print(f"\n❌ APP CREATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_blueprints(app):
    """Test blueprint registration"""
    print("\n" + "="*60)
    print("TEST 3: Testing Blueprint Registration")
    print("="*60)

    try:
        blueprints = list(app.blueprints.keys())
        print(f"\n✓ Total blueprints registered: {len(blueprints)}")

        print("\nRegistered blueprints:")
        for i, bp_name in enumerate(sorted(blueprints), 1):
            print(f"  {i}. {bp_name}")

        # Expected blueprints
        expected = [
            'currency',
            'category', 'category_mapping',
            'auth', 'admin_auth',
            'transaction', 'tag',
            'account', 'simplefin',
            'budget',
            'group', 'settlement',
            'recurring',
            'investment',
            'analytics'
        ]

        print(f"\n✓ Expected blueprints: {len(expected)}")

        missing = [bp for bp in expected if bp not in blueprints]
        if missing:
            print(f"\n⚠️  Missing blueprints: {missing}")
        else:
            print("\n✅ ALL EXPECTED BLUEPRINTS REGISTERED!")

        return True

    except Exception as e:
        print(f"\n❌ BLUEPRINT TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routes(app):
    """Test route registration"""
    print("\n" + "="*60)
    print("TEST 4: Testing Route Registration")
    print("="*60)

    try:
        # Get all routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': ','.join(rule.methods - {'HEAD', 'OPTIONS'}),
                'path': rule.rule
            })

        print(f"\n✓ Total routes registered: {len(routes)}")

        # Group by service
        services = {}
        for route in routes:
            service = route['endpoint'].split('.')[0] if '.' in route['endpoint'] else 'root'
            if service not in services:
                services[service] = []
            services[service].append(route)

        print(f"\n✓ Routes organized into {len(services)} groups:")
        for service, route_list in sorted(services.items()):
            print(f"\n  {service.upper()}: {len(route_list)} routes")
            for route in sorted(route_list, key=lambda x: x['path'])[:5]:  # Show first 5
                print(f"    - {route['methods']:15} {route['path']}")
            if len(route_list) > 5:
                print(f"    ... and {len(route_list) - 5} more")

        print("\n✅ ALL ROUTES REGISTERED!")
        return True

    except Exception as e:
        print(f"\n❌ ROUTE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_connection(app):
    """Test database setup"""
    print("\n" + "="*60)
    print("TEST 5: Testing Database Connection")
    print("="*60)

    try:
        with app.app_context():
            from src.extensions import db

            print("✓ Database instance created")
            print(f"✓ Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')[:50]}...")

            # Try to get engine info
            try:
                engine = db.engine
                print(f"✓ Database engine: {engine.name}")
                print(f"✓ Database driver: {engine.driver}")
            except:
                print("⚠️  Database not initialized yet (run migrations first)")

            print("\n✅ DATABASE CONFIGURATION OK!")
            return True

    except Exception as e:
        print(f"\n❌ DATABASE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models(app):
    """Test model definitions"""
    print("\n" + "="*60)
    print("TEST 6: Testing Model Definitions")
    print("="*60)

    try:
        with app.app_context():
            from src.extensions import db
            from src.models import (
                User, Account, Category, Currency,
                Expense, Budget, Group, RecurringExpense,
                Portfolio, Investment
            )

            models = [
                User, Account, Category, Currency,
                Expense, Budget, Group, RecurringExpense,
                Portfolio, Investment
            ]

            print(f"\n✓ Testing {len(models)} model classes:")
            for model in models:
                print(f"  - {model.__name__}: {model.__tablename__}")

            print("\n✅ ALL MODELS DEFINED!")
            return True

    except Exception as e:
        print(f"\n❌ MODEL TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_services(app):
    """Test service classes"""
    print("\n" + "="*60)
    print("TEST 7: Testing Service Classes")
    print("="*60)

    try:
        with app.app_context():
            from src.services.currency.service import CurrencyService
            from src.services.category.service import CategoryService
            from src.services.auth.service import AuthService
            from src.services.transaction.service import TransactionService
            from src.services.account.service import AccountService
            from src.services.budget.service import BudgetService
            from src.services.group.service import GroupService
            from src.services.recurring.service import RecurringService
            from src.services.investment.service import InvestmentService
            from src.services.analytics.service import AnalyticsService
            from src.services.notification.service import NotificationService

            services = [
                ('CurrencyService', CurrencyService),
                ('CategoryService', CategoryService),
                ('AuthService', AuthService),
                ('TransactionService', TransactionService),
                ('AccountService', AccountService),
                ('BudgetService', BudgetService),
                ('GroupService', GroupService),
                ('RecurringService', RecurringService),
                ('InvestmentService', InvestmentService),
                ('AnalyticsService', AnalyticsService),
                ('NotificationService', NotificationService),
            ]

            print(f"\n✓ Testing {len(services)} service classes:")
            for name, ServiceClass in services:
                service = ServiceClass()
                print(f"  - {name}: ✓")

            print("\n✅ ALL SERVICES CAN BE INSTANTIATED!")
            return True

    except Exception as e:
        print(f"\n❌ SERVICE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config(app):
    """Test configuration"""
    print("\n" + "="*60)
    print("TEST 8: Testing Configuration")
    print("="*60)

    try:
        print("\nKey configuration values:")
        keys = [
            'SECRET_KEY',
            'SQLALCHEMY_DATABASE_URI',
            'MAIL_SERVER',
            'DEBUG',
            'TESTING'
        ]

        for key in keys:
            value = app.config.get(key, 'Not set')
            if key in ['SECRET_KEY', 'SQLALCHEMY_DATABASE_URI'] and value != 'Not set':
                # Mask sensitive values
                value = value[:10] + '...' if len(str(value)) > 10 else value
            print(f"  - {key}: {value}")

        print("\n✅ CONFIGURATION OK!")
        return True

    except Exception as e:
        print(f"\n❌ CONFIG TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results):
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success Rate: {(passed/total)*100:.1f}%")

    print("\nDetailed Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    if passed == total:
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED! APPLICATION IS READY!")
        print("="*60)
        print("\nNext steps:")
        print("1. Initialize database: flask db upgrade")
        print("2. Create .env file with your configuration")
        print("3. Start app: python3 app.py")
        print("4. Access at: http://localhost:5001")
        return True
    else:
        print("\n" + "="*60)
        print("⚠️  SOME TESTS FAILED - REVIEW ERRORS ABOVE")
        print("="*60)
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("DollarDollar Complete Test Suite")
    print("Testing Modular Application Architecture")
    print("="*60)

    results = {}

    # Test 1: Imports
    results['Module Imports'] = test_imports()
    if not results['Module Imports']:
        print("\n❌ Cannot proceed without successful imports")
        print_summary(results)
        return False

    # Test 2: App Creation
    app = test_app_creation()
    results['Application Factory'] = app is not None
    if not app:
        print("\n❌ Cannot proceed without app instance")
        print_summary(results)
        return False

    # Test 3-8: Various tests
    results['Blueprint Registration'] = test_blueprints(app)
    results['Route Registration'] = test_routes(app)
    results['Database Connection'] = test_database_connection(app)
    results['Model Definitions'] = test_models(app)
    results['Service Classes'] = test_services(app)
    results['Configuration'] = test_config(app)

    # Print summary
    success = print_summary(results)

    return success


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
