"""Template context processors for Jinja2 templates"""
import hashlib
from src.models.user import User


def utility_processor():
    """Provide utility functions to templates"""

    def get_user_color(user_id):
        """
        Generate a consistent color for a user based on their ID
        This ensures the same user always gets the same color
        """
        # Use MD5 hash to generate a consistent color
        hash_object = hashlib.md5(user_id.encode())
        hash_hex = hash_object.hexdigest()

        # Use the first 6 characters of the hash to create a color
        # This ensures a consistent but pseudo-random color
        r = int(hash_hex[:2], 16)
        g = int(hash_hex[2:4], 16)
        b = int(hash_hex[4:6], 16)

        # Ensure the color is not too light
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        if brightness > 180:
            # If too bright, darken the color
            r = min(r * 0.7, 255)
            g = min(g * 0.7, 255)
            b = min(b * 0.7, 255)

        return f'rgb({r},{g},{b})'

    def get_user_by_id(user_id):
        """
        Retrieve a user by their ID
        Returns None if user not found to prevent template errors
        """
        return User.query.filter_by(id=user_id).first()

    def get_category_icon_html(category):
        """
        Generate HTML for a category icon with proper styling
        """
        if not category:
            return '<i class="fas fa-tag"></i>'

        icon = category.icon or 'fa-tag'
        color = category.color or '#6c757d'

        return f'<i class="fas {icon}" style="color: {color};"></i>'

    return {
        'get_user_color': get_user_color,
        'get_user_by_id': get_user_by_id,
        'get_category_icon_html': get_category_icon_html
    }
