#!/usr/bin/env python3
"""
Comprehensive template URL fixer - maps all endpoints to their actual blueprint names
"""

import os
import re
from pathlib import Path

# Complete mapping based on actual routes in services
URL_MAPPINGS = {
    # Auth Service - auth/routes.py
    'login': 'auth.login',
    'logout': 'auth.logout',
    'signup': 'auth.signup',
    'reset_password_request': 'auth.reset_password_request',
    'reset_password': 'auth.reset_password',
    'admin_add_user': 'auth.add_user',
    'admin_delete_user': 'auth.delete_user',
    'admin_reset_password': 'auth.reset_password_admin',
    'admin_toggle_admin_status': 'auth.toggle_admin_status',

    # Transaction Service - transaction/routes.py
    'add_expense': 'transaction.add_expense',
    'update_expense': 'transaction.update_expense',
    'delete_expense': 'transaction.delete_expense',
    'get_expense': 'transaction.get_expense',
    'transactions': 'transaction.transactions',
    'get_transaction_form_html': 'transaction.get_transaction_form_html',
    'get_expense_edit_form': 'transaction.get_expense_edit_form',
    'get_category_splits': 'transaction.get_category_splits',
    'export_transactions': 'transaction.export_transactions',

    # Tag Management (in transaction service)
    'tags': 'transaction.manage_tags',
    'add_tag': 'transaction.add_tag',
    'delete_tag': 'transaction.delete_tag',

    # Account Service - account/routes.py
    'accounts': 'account.accounts',
    'add_account': 'account.add_account',
    'update_account': 'account.update_account',
    'delete_account': 'account.delete_account',
    'get_account': 'account.get_account',
    'advanced': 'account.advanced',
    'import_csv': 'account.import_csv',
    'connect_simplefin': 'account.connect_simplefin',
    'process_simplefin_token': 'account.process_token',
    'simplefin_add_accounts': 'account.add_accounts',
    'sync_account': 'account.sync_account',
    'disconnect_account': 'account.disconnect_account',
    'simplefin_disconnect': 'account.disconnect',
    'simplefin_refresh': 'account.refresh',
    'run_scheduled_sync': 'account.run_scheduled_sync',

    # Category Service - category/routes.py
    'categories': 'category.manage_categories',
    'manage_categories': 'category.manage_categories',
    'user_create_default_categories': 'category.create_defaults',
    'add_category': 'category.add_category',
    'edit_category': 'category.edit_category',
    'delete_category': 'category.delete_category',
    'api_categories': 'category.api_categories',

    # Category Mapping (in category service)
    'category_mappings': 'category.manage_mappings',
    'create_default_mappings': 'category.create_default_mappings',
    'add_category_mapping': 'category.add_mapping',
    'edit_category_mapping': 'category.edit_mapping',
    'delete_category_mapping': 'category.delete_mapping',
    'toggle_category_mapping': 'category.toggle_mapping',
    'bulk_categorize': 'category.bulk_categorize',
    'export_category_mappings': 'category.export_mappings',
    'upload_category_mappings': 'category.upload_mappings',
    'learn_from_transaction_history': 'category.learn_from_history',

    # Budget Service - budget/routes.py
    'budgets': 'budget.budgets',
    'add_budget': 'budget.add_budget',
    'edit_budget': 'budget.edit_budget',
    'toggle_budget': 'budget.toggle_budget',
    'delete_budget': 'budget.delete_budget',
    'get_budget': 'budget.get_budget',
    'budget_transactions': 'budget.budget_transactions',
    'subcategory_spending': 'budget.subcategory_spending',
    'trends_data': 'budget.trends_data',
    'summary_data': 'budget.summary_data',

    # Group Service - group/routes.py
    'groups': 'group.groups',
    'create_group': 'group.create_group',
    'group_details': 'group.group_details',
    'add_member': 'group.add_member',
    'remove_member': 'group.remove_member',
    'delete_group': 'group.delete_group',
    'update_settings': 'group.update_settings',
    'get_details': 'group.get_details',

    # Settlement (in group service)
    'settlements': 'group.settlements',
    'add_settlement': 'group.add_settlement',

    # Currency Service - currency/routes.py
    'currencies': 'currency.manage_currencies',
    'manage_currencies': 'currency.manage_currencies',
    'add_currency': 'currency.add_currency',
    'update_currency': 'currency.update_currency',
    'delete_currency': 'currency.delete_currency',
    'set_base_currency': 'currency.set_base_currency',
    'update_rates_route': 'currency.update_rates',
    'set_default_currency': 'currency.set_default_currency',

    # Recurring Service - recurring/routes.py
    'recurring': 'recurring.recurring',
    'add_recurring': 'recurring.add_recurring',
    'toggle_recurring': 'recurring.toggle_recurring',
    'delete_recurring': 'recurring.delete_recurring',
    'detect_recurring': 'recurring.detect_recurring_transactions',
    'manage_ignored_patterns': 'recurring.manage_ignored_patterns',

    # Investment Service - investment/routes.py
    'investments': 'investment.investments',
    'add_portfolio': 'investment.add_portfolio',
    'portfolios': 'investment.portfolios',
    'investment_transactions': 'investment.investment_transactions',
    'setup_investment_api': 'investment.setup_investment_api',
    'update_investment_api': 'investment.update_investment_api',

    # Analytics Service - analytics/routes.py
    'dashboard': 'analytics.dashboard',
    'stats': 'analytics.stats',
    'api_trends': 'analytics.trends',

    # Settings/Profile - need to determine where these should go
    # For now, assuming they'll be in auth service
    'profile': 'auth.profile',
    'change_password': 'auth.change_password',
    'update_color': 'auth.update_color',
    'update_timezone': 'auth.update_timezone',
    'update_notification_preferences': 'auth.update_notification_preferences',

    # Admin
    'admin': 'auth.admin',

    # Cache management - if exists
    'api_cache': 'admin.api_cache',
    'clear_all_cache': 'admin.clear_all_cache',
    'clear_expired_cache': 'admin.clear_expired_cache',

    # OIDC
    'login_oidc': 'auth.login_oidc',

    # Static files (keep as is)
    'static': 'static',
}

def update_template_file(filepath):
    """Update a single template file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes_made = 0
    unmapped = set()

    # Find all url_for patterns
    url_for_pattern = r"url_for\(['\"]([^'\"]+)['\"]"

    def replace_url(match):
        nonlocal changes_made
        old_endpoint = match.group(1)

        # Skip if already correctly prefixed
        if '.' in old_endpoint and old_endpoint in [
            'auth.login', 'auth.logout', 'auth.signup',
            'transaction.add_expense', 'transaction.transactions',
            'account.accounts', 'category.manage_categories',
            'budget.budgets', 'group.groups', 'currency.manage_currencies',
            'recurring.recurring', 'investment.investments',
            'analytics.dashboard', 'analytics.stats', 'static'
        ]:
            return match.group(0)

        # Get new endpoint name
        new_endpoint = URL_MAPPINGS.get(old_endpoint)

        if new_endpoint:
            if new_endpoint != old_endpoint:
                changes_made += 1
                return f"url_for('{new_endpoint}'"
        else:
            # Track unmapped endpoints
            if '.' not in old_endpoint and old_endpoint != 'static':
                unmapped.add(old_endpoint)

        return match.group(0)

    content = re.sub(url_for_pattern, replace_url, content)

    # Write back if changed
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    return changes_made, unmapped

def main():
    """Update all templates"""
    templates_dir = Path('templates')

    if not templates_dir.exists():
        print("❌ Templates directory not found!")
        return

    print("="*60)
    print("Comprehensive Template URL Fixer")
    print("="*60)

    total_files = 0
    total_changes = 0
    updated_files = []
    all_unmapped = set()

    for template_file in templates_dir.rglob('*.html'):
        changes, unmapped = update_template_file(template_file)
        total_files += 1

        if changes > 0:
            total_changes += changes
            updated_files.append((template_file.name, changes))
            print(f"✓ {template_file.name}: {changes} URLs updated")

        all_unmapped.update(unmapped)

    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"Total templates scanned: {total_files}")
    print(f"Templates updated: {len(updated_files)}")
    print(f"Total URL changes: {total_changes}")

    if updated_files:
        print("\nUpdated files:")
        for filename, changes in updated_files:
            print(f"  - {filename}: {changes} changes")

    if all_unmapped:
        print("\n⚠️  Unmapped endpoints found (may need routes created):")
        for endpoint in sorted(all_unmapped):
            print(f"  - {endpoint}")

    print("\n✅ Template update complete!")

if __name__ == '__main__':
    main()
