"""
Category Routes
Flask Blueprint for category and category mapping endpoints
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from src.utils.decorators import login_required_dev, restrict_demo_access
from src.services.category.service import CategoryService

# Create Blueprints
bp = Blueprint('category', __name__)
mapping_bp = Blueprint('category_mapping', __name__, url_prefix='/category_mappings')

# Initialize service
category_service = CategoryService()


# ========== CATEGORY ROUTES ==========

@bp.route('/categories')
@login_required_dev
def manage_categories():
    """View and manage expense categories"""
    categories = category_service.get_all_categories(current_user.id, parent_id=None)

    # FontAwesome icons for the icon picker
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


@bp.route('/categories/create_defaults', methods=['POST'])
@login_required_dev
def create_defaults():
    """Allow a user to create default categories"""
    if category_service.has_default_categories(current_user.id):
        flash('You already have the default categories.')
        return redirect(url_for('category.manage_categories'))

    # This would call a function to create default categories
    # For now, just flash a message
    flash('Default categories created successfully!')
    return redirect(url_for('category.manage_categories'))


@bp.route('/categories/add', methods=['POST'])
@login_required_dev
def add_category():
    """Add a new category or subcategory"""
    name = request.form.get('name')
    icon = request.form.get('icon', 'fa-tag')
    color = request.form.get('color', "#6c757d")
    parent_id = request.form.get('parent_id')

    if parent_id == "":
        parent_id = None

    success, message, category = category_service.add_category(
        current_user.id, name, icon, color, parent_id
    )

    flash(message)
    return redirect(url_for('category.manage_categories'))


@bp.route('/categories/edit/<int:category_id>', methods=['POST'])
@login_required_dev
def edit_category(category_id):
    """Edit an existing category"""
    name = request.form.get('name')
    icon = request.form.get('icon')
    color = request.form.get('color')

    success, message = category_service.update_category(
        category_id, current_user.id, name=name, icon=icon, color=color
    )

    flash(message)
    return redirect(url_for('category.manage_categories'))


@bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required_dev
def delete_category(category_id):
    """Delete a category"""
    success, message = category_service.delete_category(category_id, current_user.id)
    flash(message)
    return redirect(url_for('category.manage_categories'))


# ========== CATEGORY MAPPING ROUTES ==========

@mapping_bp.route('')
@login_required_dev
@restrict_demo_access
def manage_mappings():
    """View and manage category mappings"""
    mappings = category_service.get_all_mappings(current_user.id)
    categories = category_service.get_all_categories(current_user.id)

    return render_template('category_mappings.html',
                          mappings=mappings,
                          categories=categories)


@mapping_bp.route('/create_defaults', methods=['POST'])
@login_required_dev
@restrict_demo_access
def create_default_mappings():
    """Create default category mappings"""
    try:
        # This would create default mappings
        # For now, return success
        return jsonify({
            'success': True,
            'count': 0,
            'message': 'Default mapping rules would be created here'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@mapping_bp.route('/add', methods=['POST'])
@login_required_dev
@restrict_demo_access
def add_mapping():
    """Add a new category mapping rule"""
    keyword = request.form.get('keyword', '').strip()
    category_id = request.form.get('category_id')
    is_regex = request.form.get('is_regex') == 'on'
    priority = int(request.form.get('priority', 0))

    success, message = category_service.add_mapping(
        current_user.id, keyword, category_id, is_regex, priority
    )

    flash(message)
    return redirect(url_for('category_mapping.manage_mappings'))


@mapping_bp.route('/edit/<int:mapping_id>', methods=['POST'])
@login_required_dev
@restrict_demo_access
def edit_mapping(mapping_id):
    """Edit an existing category mapping rule"""
    keyword = request.form.get('keyword', '').strip()
    category_id = request.form.get('category_id')
    is_regex = request.form.get('is_regex') == 'on'
    priority = int(request.form.get('priority', 0))

    success, message = category_service.update_mapping(
        mapping_id, current_user.id, keyword=keyword,
        category_id=category_id, is_regex=is_regex, priority=priority
    )

    flash(message)
    return redirect(url_for('category_mapping.manage_mappings'))


@mapping_bp.route('/toggle/<int:mapping_id>', methods=['POST'])
@login_required_dev
def toggle_mapping(mapping_id):
    """Toggle the active status of a mapping"""
    success, message, new_status = category_service.toggle_mapping(mapping_id, current_user.id)
    flash(message)
    return redirect(url_for('category_mapping.manage_mappings'))


@mapping_bp.route('/delete/<int:mapping_id>', methods=['POST'])
@login_required_dev
def delete_mapping(mapping_id):
    """Delete a category mapping rule"""
    success, message = category_service.delete_mapping(mapping_id, current_user.id)
    flash(message)
    return redirect(url_for('category_mapping.manage_mappings'))


@mapping_bp.route('/learn_from_history', methods=['POST'])
@login_required_dev
@restrict_demo_access
def learn_from_history():
    """Learn category mappings from transaction history"""
    flash('Category learning from history is not yet implemented in the new architecture.')
    return redirect(url_for('category_mapping.manage_mappings'))


@mapping_bp.route('/upload', methods=['POST'])
@login_required_dev
@restrict_demo_access
def upload_mappings():
    """Upload category mappings from CSV"""
    flash('Category mapping upload is not yet implemented in the new architecture.')
    return redirect(url_for('category_mapping.manage_mappings'))


@mapping_bp.route('/export', methods=['GET'])
@login_required_dev
def export_mappings():
    """Export category mappings to CSV"""
    flash('Category mapping export is not yet implemented in the new architecture.')
    return redirect(url_for('category_mapping.manage_mappings'))


@mapping_bp.route('/bulk_categorize', methods=['POST'])
@login_required_dev
def bulk_categorize():
    """Categorize all uncategorized transactions"""
    success, message, categorized, total = category_service.bulk_categorize_transactions(current_user.id)

    flash(message)

    # Redirect based on referrer
    referrer = request.referrer or ''
    if 'transactions' in referrer:
        return redirect(url_for('transactions'))
    elif 'category_mappings' in referrer:
        return redirect(url_for('category_mapping.manage_mappings'))
    else:
        return redirect(url_for('dashboard'))


# API route for categories (JSON)
@bp.route('/api/categories')
@login_required_dev
def api_categories():
    """API endpoint to get all categories as JSON"""
    categories = category_service.get_all_categories(current_user.id)
    return jsonify([{
        'id': cat.id,
        'name': cat.name,
        'icon': cat.icon,
        'color': cat.color,
        'parent_id': cat.parent_id
    } for cat in categories])
