#!/usr/bin/env python3
"""
Update all template URLs to use blueprint-prefixed endpoint names
"""

import os
import re
from pathlib import Path

# Mapping of old endpoint names to new blueprint-prefixed names
URL_MAPPINGS = {
    # Auth Service
    'login': 'auth.login',
    'logout': 'auth.logout',
    'signup': 'auth.signup',
    'reset_password_request': 'auth.reset_password_request',
    'reset_password': 'auth.reset_password',

    # Admin Auth
    'admin.add_user': 'admin.add_user',  # Already correct
    'admin.delete_user': 'admin.delete_user',  # Already correct
    'admin.reset_password': 'admin.reset_password',  # Already correct
    'admin.toggle_admin_status': 'admin.toggle_admin_status',  # Already correct

    # Transaction Service
    'add_expense': 'transaction.add_expense',
    'update_expense': 'transaction.update_expense',
    'delete_expense': 'transaction.delete_expense',
    'get_expense': 'transaction.get_expense',
    'get_category_splits': 'transaction.get_category_splits',
    'transactions': 'transaction.transactions',
    'export_transactions': 'transaction.export_transactions',
    'import_transactions': 'transaction.import_transactions',
    'split_expense': 'transaction.split_expense',

    # Tag Service (part of transaction)
    'tags': 'tag.tags',
    'add_tag': 'tag.add_tag',
    'delete_tag': 'tag.delete_tag',

    # Account Service
    'accounts': 'account.accounts',
    'add_account': 'account.add_account',
    'update_account': 'account.update_account',
    'delete_account': 'account.delete_account',
    'advanced': 'account.advanced',
    'connect_simplefin': 'account.connect_simplefin',

    # SimpleFin Service
    'simplefin.fetch_accounts': 'simplefin.fetch_accounts',  # Already correct
    'simplefin.add_accounts': 'simplefin.add_accounts',  # Already correct
    'simplefin.process_token': 'simplefin.process_token',  # Already correct
    'simplefin.refresh': 'simplefin.refresh',  # Already correct
    'simplefin.disconnect': 'simplefin.disconnect',  # Already correct

    # Category Service
    'categories': 'category.categories',
    'add_category': 'category.add_category',
    'edit_category': 'category.edit_category',
    'delete_category': 'category.delete_category',
    'create_default_categories': 'category.create_default_categories',
    'api_categories': 'category.api_categories',

    # Category Mapping Service
    'category_mappings': 'category_mapping.category_mappings',
    'add_category_mapping': 'category_mapping.add_category_mapping',
    'edit_category_mapping': 'category_mapping.edit_category_mapping',
    'delete_category_mapping': 'category_mapping.delete_category_mapping',
    'toggle_category_mapping': 'category_mapping.toggle_category_mapping',
    'bulk_categorize': 'category_mapping.bulk_categorize',
    'create_default_mappings': 'category_mapping.create_default_mappings',

    # Budget Service
    'budgets': 'budget.budgets',
    'add_budget': 'budget.add_budget',
    'edit_budget': 'budget.edit_budget',
    'delete_budget': 'budget.delete_budget',
    'get_budget': 'budget.get_budget',
    'budget_transactions': 'budget.budget_transactions',

    # Group Service
    'groups': 'group.groups',
    'group_detail': 'group.group_detail',
    'add_group': 'group.add_group',
    'edit_group': 'group.edit_group',
    'delete_group': 'group.delete_group',
    'add_group_member': 'group.add_group_member',
    'remove_group_member': 'group.remove_group_member',
    'update_group_shares': 'group.update_group_shares',

    # Settlement Service
    'settlements': 'settlement.settlements',
    'add_settlement': 'settlement.add_settlement',

    # Recurring Service
    'recurring': 'recurring.recurring',
    'add_recurring': 'recurring.add_recurring',
    'delete_recurring': 'recurring.delete_recurring',
    'toggle_recurring': 'recurring.toggle_recurring',
    'detect_recurring': 'recurring.detect_recurring',

    # Investment Service
    'investments': 'investment.investments',
    'add_portfolio': 'investment.add_portfolio',

    # Currency Service
    'currencies': 'currency.currencies',
    'add_currency': 'currency.add_currency',
    'update_currency': 'currency.update_currency',
    'delete_currency': 'currency.delete_currency',
    'set_base_currency': 'currency.set_base_currency',
    'update_currency_rates': 'currency.update_currency_rates',
    'set_default_currency': 'currency.set_default_currency',

    # Analytics Service
    'dashboard': 'analytics.dashboard',
    'stats': 'analytics.stats',
    'api_trends': 'analytics.api_trends',

    # Static files (keep as is)
    'static': 'static',
}

def update_template_file(filepath):
    """Update a single template file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes_made = 0

    # Find all url_for patterns
    url_for_pattern = r"url_for\(['\"]([^'\"]+)['\"]"

    def replace_url(match):
        nonlocal changes_made
        old_endpoint = match.group(1)

        # Skip if already has a dot (blueprint prefix)
        if '.' in old_endpoint and not old_endpoint.startswith('static'):
            return match.group(0)

        # Get new endpoint name
        new_endpoint = URL_MAPPINGS.get(old_endpoint, old_endpoint)

        if new_endpoint != old_endpoint:
            changes_made += 1
            return f"url_for('{new_endpoint}'"

        return match.group(0)

    content = re.sub(url_for_pattern, replace_url, content)

    # Write back if changed
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return changes_made

    return 0

def main():
    """Update all templates"""
    templates_dir = Path('templates')

    if not templates_dir.exists():
        print("❌ Templates directory not found!")
        return

    print("="*60)
    print("Updating Template URLs")
    print("="*60)

    total_files = 0
    total_changes = 0
    updated_files = []

    for template_file in templates_dir.rglob('*.html'):
        changes = update_template_file(template_file)
        total_files += 1

        if changes > 0:
            total_changes += changes
            updated_files.append((template_file.name, changes))
            print(f"✓ {template_file.name}: {changes} URLs updated")

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

    print("\n✅ Template update complete!")

if __name__ == '__main__':
    main()
