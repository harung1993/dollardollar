"""
Category Service
Business logic for category and category mapping management
"""

from datetime import datetime, timedelta
from src.extensions import db
from src.models.category import Category, CategoryMapping
from src.models.transaction import Expense
from src.models.recurring import RecurringExpense
from src.models.budget import Budget
from src.utils.helpers import auto_categorize_transaction

class CategoryService:
    """Service class for category and mapping operations"""

    def __init__(self):
        pass

    # Category Management Methods

    def get_all_categories(self, user_id, parent_id=None):
        """Get all categories for a user"""
        return Category.query.filter_by(
            user_id=user_id,
            parent_id=parent_id
        ).order_by(Category.name).all()

    def get_category(self, category_id):
        """Get a specific category"""
        return Category.query.get(category_id)

    def has_default_categories(self, user_id):
        """Check if user already has default categories"""
        default_names = ["Housing", "Food", "Transportation", "Shopping", "Entertainment", "Health"]
        match_count = Category.query.filter(
            Category.user_id == user_id,
            Category.name.in_(default_names),
            Category.parent_id == None
        ).count()
        return match_count >= 4

    def add_category(self, user_id, name, icon='fa-tag', color='#6c757d', parent_id=None):
        """Add a new category - Returns (success, message, category)"""
        if not name:
            return False, 'Category name is required', None

        if parent_id:
            parent = self.get_category(parent_id)
            if not parent or parent.user_id != user_id:
                return False, 'Invalid parent category', None

        category = Category(
            name=name,
            icon=icon,
            color=color,
            parent_id=parent_id,
            user_id=user_id
        )

        try:
            db.session.add(category)
            db.session.commit()
            return True, 'Category added successfully', category
        except Exception as e:
            db.session.rollback()
            return False, f'Error adding category: {str(e)}', None

    def update_category(self, category_id, user_id, name=None, icon=None, color=None):
        """Update a category - Returns (success, message)"""
        category = self.get_category(category_id)
        if not category:
            return False, 'Category not found'

        if category.user_id != user_id:
            return False, 'You don\'t have permission to edit this category'

        if category.is_system:
            return False, 'System categories cannot be edited'

        if name:
            category.name = name
        if icon:
            category.icon = icon
        if color:
            category.color = color

        try:
            db.session.commit()
            return True, 'Category updated successfully'
        except Exception as e:
            db.session.rollback()
            return False, f'Error updating category: {str(e)}'

    def delete_category(self, category_id, user_id):
        """Delete a category - Returns (success, message)"""
        category = self.get_category(category_id)
        if not category:
            return False, 'Category not found'

        if category.user_id != user_id:
            return False, 'You don\'t have permission to delete this category'

        if category.is_system:
            return False, 'System categories cannot be deleted'

        try:
            other_category = Category.query.filter_by(
                name='Other',
                user_id=user_id,
                is_system=True
            ).first()

            if category.subcategories:
                for subcategory in category.subcategories:
                    Expense.query.filter_by(category_id=subcategory.id).update({
                        'category_id': other_category.id if other_category else None
                    })
                    RecurringExpense.query.filter_by(category_id=subcategory.id).update({
                        'category_id': other_category.id if other_category else None
                    })
                    CategoryMapping.query.filter_by(category_id=subcategory.id).delete()
                    db.session.delete(subcategory)

            Expense.query.filter_by(category_id=category_id).update({
                'category_id': other_category.id if other_category else None
            })
            RecurringExpense.query.filter_by(category_id=category_id).update({
                'category_id': other_category.id if other_category else None
            })
            Budget.query.filter_by(category_id=category_id).update({
                'category_id': other_category.id if other_category else None
            })
            CategoryMapping.query.filter_by(category_id=category_id).delete()

            db.session.delete(category)
            db.session.commit()

            return True, 'Category deleted successfully'
        except Exception as e:
            db.session.rollback()
            return False, f'Error deleting category: {str(e)}'

    # Category Mapping Methods

    def get_all_mappings(self, user_id):
        """Get all category mappings for a user"""
        return CategoryMapping.query.filter_by(user_id=user_id).order_by(
            CategoryMapping.active.desc(),
            CategoryMapping.priority.desc(),
            CategoryMapping.match_count.desc()
        ).all()

    def add_mapping(self, user_id, keyword, category_id, is_regex=False, priority=0):
        """Add a new category mapping - Returns (success, message)"""
        if not keyword or not category_id:
            return False, 'Keyword and category are required'

        keyword = keyword.strip()

        existing = CategoryMapping.query.filter_by(
            user_id=user_id,
            keyword=keyword
        ).first()

        if existing:
            return False, 'A mapping with this keyword already exists'

        mapping = CategoryMapping(
            user_id=user_id,
            keyword=keyword,
            category_id=category_id,
            is_regex=is_regex,
            priority=priority,
            active=True
        )

        try:
            db.session.add(mapping)
            db.session.commit()
            return True, 'Category mapping rule added successfully'
        except Exception as e:
            db.session.rollback()
            return False, f'Error adding mapping: {str(e)}'

    def update_mapping(self, mapping_id, user_id, keyword=None, category_id=None, is_regex=None, priority=None):
        """Update a category mapping - Returns (success, message)"""
        mapping = CategoryMapping.query.get(mapping_id)
        if not mapping:
            return False, 'Mapping not found'

        if mapping.user_id != user_id:
            return False, 'You don\'t have permission to edit this mapping'

        if keyword:
            mapping.keyword = keyword.strip()
        if category_id:
            mapping.category_id = category_id
        if is_regex is not None:
            mapping.is_regex = is_regex
        if priority is not None:
            mapping.priority = priority

        try:
            db.session.commit()
            return True, 'Category mapping updated successfully'
        except Exception as e:
            db.session.rollback()
            return False, f'Error updating mapping: {str(e)}'

    def toggle_mapping(self, mapping_id, user_id):
        """Toggle mapping active status - Returns (success, message, new_status)"""
        mapping = CategoryMapping.query.get(mapping_id)
        if not mapping:
            return False, 'Mapping not found', None

        if mapping.user_id != user_id:
            return False, 'You don\'t have permission to modify this mapping', None

        mapping.active = not mapping.active

        try:
            db.session.commit()
            status = "activated" if mapping.active else "deactivated"
            return True, f'Category mapping {status} successfully', mapping.active
        except Exception as e:
            db.session.rollback()
            return False, f'Error toggling mapping: {str(e)}', None

    def delete_mapping(self, mapping_id, user_id):
        """Delete a category mapping - Returns (success, message)"""
        mapping = CategoryMapping.query.get(mapping_id)
        if not mapping:
            return False, 'Mapping not found'

        if mapping.user_id != user_id:
            return False, 'You don\'t have permission to delete this mapping'

        try:
            db.session.delete(mapping)
            db.session.commit()
            return True, 'Category mapping deleted successfully'
        except Exception as e:
            db.session.rollback()
            return False, f'Error deleting mapping: {str(e)}'

    def bulk_categorize_transactions(self, user_id):
        """Categorize all uncategorized transactions - Returns (success, message, categorized_count, total_count)"""
        try:
            uncategorized = Expense.query.filter_by(
                user_id=user_id,
                category_id=None
            ).all()

            total_count = len(uncategorized)
            categorized_count = 0

            for expense in uncategorized:
                if not expense.description:
                    continue

                category_id = auto_categorize_transaction(expense.description, user_id)

                if category_id:
                    expense.category_id = category_id
                    categorized_count += 1

            db.session.commit()
            return True, f'Successfully categorized {categorized_count} out of {total_count} transactions', categorized_count, total_count

        except Exception as e:
            db.session.rollback()
            return False, f'Error: {str(e)}', 0, 0
