"""
Auth Service
Business logic for user authentication and management
"""

import hashlib
from flask import current_app
from flask_mail import Message
from src.extensions import db, mail
from src.models.user import User
from src.models.category import Category, CategoryMapping
from src.models.budget import Budget


class AuthService:
    """Service class for authentication and user management operations"""

    def __init__(self):
        pass

    # User Registration & Authentication Methods

    def signup_user(self, email, password, name):
        """
        Register a new user with default categories and budgets
        Returns (success, message, user)
        """
        # Check if OIDC is enabled
        if current_app.config.get('OIDC_ENABLED'):
            return False, 'Signups are disabled when OIDC authentication is enabled', None

        # Check if signups are allowed
        if not current_app.config.get('ALLOW_SIGNUPS', True):
            return False, 'Signups are currently disabled', None

        # Check if user already exists
        if User.query.filter_by(id=email).first():
            return False, 'Email already registered', None

        try:
            # Create user
            user = User(
                id=email,
                name=name,
                is_admin=False,
                user_color=self.generate_user_color(email)
            )
            user.set_password(password)
            db.session.add(user)

            # Flush to get the user ID without committing yet
            db.session.flush()

            # Create default categories and budgets in the same transaction
            self.create_default_categories(user.id)
            self.create_default_budgets(user.id)

            # Commit everything at once
            db.session.commit()

            # Send welcome email (outside transaction)
            try:
                self.send_welcome_email(user)
            except Exception as e:
                current_app.logger.error(f"Failed to send welcome email: {str(e)}")

            return True, 'Account created successfully! You can now log in.', user

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user: {str(e)}")
            return False, f'Error creating account: {str(e)}', None

    def generate_user_color(self, user_id):
        """
        Generate a consistent color for a user based on their ID
        """
        # Use MD5 hash to generate a consistent color
        hash_object = hashlib.md5(user_id.encode())
        hash_hex = hash_object.hexdigest()

        # Take the first 6 characters for RGB
        r = int(hash_hex[0:2], 16)
        g = int(hash_hex[2:4], 16)
        b = int(hash_hex[4:6], 16)

        # Return as hex color
        return f'#{r:02x}{g:02x}{b:02x}'

    # Password Reset Methods

    def request_password_reset(self, email):
        """
        Send password reset email to user
        Returns (success, message)
        """
        user = User.query.filter_by(id=email).first()
        if not user:
            # Don't reveal if email exists or not (security)
            return True, 'If that email is registered, you will receive a password reset link.'

        try:
            token = user.generate_reset_token()
            self.send_password_reset_email(user, token)
            return True, 'Password reset link sent to your email.'
        except Exception as e:
            current_app.logger.error(f"Error sending reset email: {str(e)}")
            return False, 'Error sending reset email. Please try again later.'

    def reset_password_with_token(self, token, new_password):
        """
        Reset user password using reset token
        Returns (success, message, user)
        """
        user = User.verify_reset_token(token)
        if not user:
            return False, 'Invalid or expired reset link', None

        try:
            user.set_password(new_password)
            db.session.commit()
            return True, 'Password reset successful! You can now log in.', user
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error resetting password: {str(e)}")
            return False, f'Error resetting password: {str(e)}', None

    # Admin User Management Methods

    def admin_add_user(self, email, password, name, is_admin=False):
        """
        Admin function to add a new user
        Returns (success, message, user)
        """
        if User.query.filter_by(id=email).first():
            return False, 'Email already registered', None

        try:
            # Create and add user
            user = User(id=email, name=name, is_admin=is_admin)
            user.set_password(password)
            db.session.add(user)

            # Flush to get the user ID without committing yet
            db.session.flush()

            # Create categories and budgets in the same transaction
            self.create_default_categories(user.id)
            self.create_default_budgets(user.id)

            # Now commit everything at once
            db.session.commit()

            # Send email outside the transaction
            try:
                self.send_welcome_email(user)
            except Exception as e:
                current_app.logger.error(f"Failed to send welcome email: {str(e)}")

            return True, 'User added successfully!', user

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user: {str(e)}")
            return False, f'Error creating user: {str(e)}', None

    def admin_delete_user(self, user_id, current_user_id):
        """
        Admin function to delete a user and all their data
        Returns (success, message)
        """
        # Prevent self-deletion
        if user_id == current_user_id:
            return False, 'Cannot delete your own admin account!'

        user = User.query.filter_by(id=user_id).first()
        if not user:
            return False, 'User not found.'

        current_app.logger.info(f"Starting deletion process for user: {user_id}")

        try:
            from src.models.budget import Budget
            from src.models.recurring import RecurringExpense, IgnoredRecurringPattern
            from src.models.transaction import Expense
            from src.models.group import Settlement, Group
            from src.models.category import CategoryMapping, Tag, Category
            from src.models.account import SimpleFin, Account
            from sqlalchemy import or_

            # Delete all related data in the correct order
            # 1. First handle budgets (they reference categories)
            current_app.logger.info("Deleting budgets...")
            Budget.query.filter_by(user_id=user_id).delete()

            # 2. Delete recurring expenses
            current_app.logger.info("Deleting recurring expenses...")
            RecurringExpense.query.filter_by(user_id=user_id).delete()

            # 3. Delete expenses
            current_app.logger.info("Deleting expenses...")
            Expense.query.filter_by(user_id=user_id).delete()

            # 4. Delete settlements
            current_app.logger.info("Deleting settlements...")
            Settlement.query.filter(
                or_(Settlement.payer_id == user_id, Settlement.receiver_id == user_id)
            ).delete(synchronize_session=False)

            # 5. Delete category mappings
            current_app.logger.info("Deleting category mappings...")
            CategoryMapping.query.filter_by(user_id=user_id).delete()

            # 6. Delete SimpleFin settings
            current_app.logger.info("Deleting SimpleFin settings...")
            SimpleFin.query.filter_by(user_id=user_id).delete()

            # 7. Delete ignored recurring patterns
            current_app.logger.info("Deleting ignored patterns...")
            IgnoredRecurringPattern.query.filter_by(user_id=user_id).delete()

            # 8. Handle user's accounts
            current_app.logger.info("Deleting accounts...")
            Account.query.filter_by(user_id=user_id).delete()

            # 9. Handle tags - first remove from association table
            current_app.logger.info("Handling tags...")
            user_tags = Tag.query.filter_by(user_id=user_id).all()
            for tag in user_tags:
                # Clear association with expenses
                tag.expenses = []
            db.session.flush()

            # Now delete the tags
            Tag.query.filter_by(user_id=user_id).delete()

            # 10. Categories can now be deleted
            current_app.logger.info("Deleting categories...")
            Category.query.filter_by(user_id=user_id).delete()

            # 11. Handle group memberships
            current_app.logger.info("Handling group memberships...")
            # First, handle groups created by this user
            for group in Group.query.filter_by(created_by=user_id).all():
                # Remove the user from the group members if they're in it
                if user in group.members:
                    group.members.remove(user)

                # Find a new owner or delete the group if empty
                if group.members:
                    # Assign first remaining member as new owner
                    new_owner = next(iter(group.members))
                    group.created_by = new_owner.id
                else:
                    # Delete group if no members left
                    db.session.delete(group)

            # Remove user from all groups they're a member of
            for group in user.groups:
                group.members.remove(user)

            # 12. Finally delete the user
            current_app.logger.info("Deleting user...")
            db.session.delete(user)

            # Commit all changes
            db.session.commit()
            current_app.logger.info(f"User {user_id} deleted successfully")
            return True, 'User deleted successfully!'

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting user: {str(e)}", exc_info=True)
            return False, f'Error deleting user: {str(e)}'

    def admin_reset_password(self, user_id, new_password, confirm_password):
        """
        Admin function to reset a user's password
        Returns (success, message, user)
        """
        # Validate passwords match
        if new_password != confirm_password:
            return False, 'Passwords do not match!', None

        user = User.query.filter_by(id=user_id).first()
        if not user:
            return False, 'User not found.', None

        try:
            user.set_password(new_password)
            db.session.commit()
            return True, f'Password reset successful for {user.name}!', user
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error resetting password: {str(e)}")
            return False, f'Error resetting password: {str(e)}', None

    def admin_toggle_admin_status(self, user_id, current_user_id):
        """
        Admin function to toggle a user's admin status
        Returns (success, message, new_status)
        """
        # Prevent changing your own admin status
        if user_id == current_user_id:
            return False, 'Cannot change your own admin status!', None

        user = User.query.filter_by(id=user_id).first()
        if not user:
            return False, 'User not found.', None

        try:
            # Toggle admin status
            user.is_admin = not user.is_admin
            db.session.commit()

            status = "admin" if user.is_admin else "regular user"
            return True, f'User {user.name} is now a {status}!', user.is_admin

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error toggling admin status: {str(e)}")
            return False, f'Error updating user: {str(e)}', None

    # Helper Methods for Default Data Creation

    def create_default_categories(self, user_id):
        """Create default expense categories for a new user"""
        default_categories = [
            # Housing
            {"name": "Housing", "icon": "fa-home", "color": "#3498db", "subcategories": [
                {"name": "Rent/Mortgage", "icon": "fa-building", "color": "#3498db"},
                {"name": "Utilities", "icon": "fa-bolt", "color": "#3498db"},
                {"name": "Home Maintenance", "icon": "fa-tools", "color": "#3498db"}
            ]},
            # Food
            {"name": "Food", "icon": "fa-utensils", "color": "#e74c3c", "subcategories": [
                {"name": "Groceries", "icon": "fa-shopping-basket", "color": "#e74c3c"},
                {"name": "Restaurants", "icon": "fa-hamburger", "color": "#e74c3c"},
                {"name": "Coffee Shops", "icon": "fa-coffee", "color": "#e74c3c"}
            ]},
            # Transportation
            {"name": "Transportation", "icon": "fa-car", "color": "#2ecc71", "subcategories": [
                {"name": "Gas", "icon": "fa-gas-pump", "color": "#2ecc71"},
                {"name": "Public Transit", "icon": "fa-bus", "color": "#2ecc71"},
                {"name": "Rideshare", "icon": "fa-taxi", "color": "#2ecc71"}
            ]},
            # Shopping
            {"name": "Shopping", "icon": "fa-shopping-cart", "color": "#9b59b6", "subcategories": [
                {"name": "Clothing", "icon": "fa-tshirt", "color": "#9b59b6"},
                {"name": "Electronics", "icon": "fa-laptop", "color": "#9b59b6"},
                {"name": "Gifts", "icon": "fa-gift", "color": "#9b59b6"}
            ]},
            # Entertainment
            {"name": "Entertainment", "icon": "fa-film", "color": "#f39c12", "subcategories": [
                {"name": "Movies", "icon": "fa-ticket-alt", "color": "#f39c12"},
                {"name": "Music", "icon": "fa-music", "color": "#f39c12"},
                {"name": "Subscriptions", "icon": "fa-play-circle", "color": "#f39c12"}
            ]},
            # Health
            {"name": "Health", "icon": "fa-heartbeat", "color": "#1abc9c", "subcategories": [
                {"name": "Medical", "icon": "fa-stethoscope", "color": "#1abc9c"},
                {"name": "Pharmacy", "icon": "fa-prescription-bottle", "color": "#1abc9c"},
                {"name": "Fitness", "icon": "fa-dumbbell", "color": "#1abc9c"}
            ]},
            # Personal
            {"name": "Personal", "icon": "fa-user", "color": "#34495e", "subcategories": [
                {"name": "Self-care", "icon": "fa-spa", "color": "#34495e"},
                {"name": "Education", "icon": "fa-graduation-cap", "color": "#34495e"}
            ]},
            # Other
            {"name": "Other", "icon": "fa-question-circle", "color": "#95a5a6", "is_system": True}
        ]

        for cat_data in default_categories:
            subcategories = cat_data.pop('subcategories', [])
            category = Category(user_id=user_id, **cat_data)
            db.session.add(category)
            db.session.flush()  # Get the ID without committing

            for subcat_data in subcategories:
                subcat = Category(user_id=user_id, parent_id=category.id, **subcat_data)
                db.session.add(subcat)

        # Create default category mappings after creating categories
        self.create_default_category_mappings(user_id)

    def create_default_category_mappings(self, user_id):
        """Create default category mapping rules for a new user"""
        # Get the user's categories
        categories = Category.query.filter_by(user_id=user_id).all()
        category_map = {cat.name: cat.id for cat in categories}

        # Define default mappings (keyword -> category name)
        default_mappings = [
            # Food
            ("grocery", "Groceries"),
            ("restaurant", "Restaurants"),
            ("coffee", "Coffee Shops"),
            ("uber eats", "Restaurants"),
            ("doordash", "Restaurants"),

            # Transportation
            ("gas", "Gas"),
            ("uber", "Rideshare"),
            ("lyft", "Rideshare"),
            ("transit", "Public Transit"),

            # Shopping
            ("amazon", "Shopping"),
            ("target", "Shopping"),
            ("walmart", "Shopping"),

            # Utilities
            ("electric", "Utilities"),
            ("water", "Utilities"),
            ("internet", "Utilities"),
        ]

        for keyword, category_name in default_mappings:
            if category_name in category_map:
                mapping = CategoryMapping(
                    user_id=user_id,
                    keyword=keyword,
                    category_id=category_map[category_name],
                    is_regex=False,
                    priority=0,
                    active=True
                )
                db.session.add(mapping)

    def create_default_budgets(self, user_id):
        """Create default budget templates for a new user, all deactivated by default"""
        # Get the user's categories first
        categories = Category.query.filter_by(user_id=user_id).all()
        category_map = {cat.name: cat.id for cat in categories}

        # Define default budgets (all inactive)
        default_budgets = [
            {"name": "Housing", "amount": 1500, "period": "monthly"},
            {"name": "Food", "amount": 600, "period": "monthly"},
            {"name": "Transportation", "amount": 300, "period": "monthly"},
            {"name": "Shopping", "amount": 200, "period": "monthly"},
            {"name": "Entertainment", "amount": 150, "period": "monthly"},
        ]

        for budget_data in default_budgets:
            category_name = budget_data["name"]
            if category_name in category_map:
                budget = Budget(
                    user_id=user_id,
                    name=budget_data["name"],
                    amount=budget_data["amount"],
                    period=budget_data["period"],
                    category_id=category_map[category_name],
                    active=False  # All budgets start inactive
                )
                db.session.add(budget)

    # Email Methods

    def send_welcome_email(self, user):
        """Send a welcome email to a newly registered user"""
        subject = "Welcome to Dollar Dollar Bill Y'all!"

        # Create welcome email body
        body_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #15803d; color: white; padding: 10px 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
                .button {{ display: inline-block; background-color: #15803d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Dollar Dollar Bill Y'all!</h1>
                </div>
                <div class="content">
                    <h2>Hi {user.name},</h2>
                    <p>Thank you for joining our expense tracking app. We're excited to help you manage your finances effectively!</p>

                    <h3>Getting Started:</h3>
                    <ol>
                        <li>Add your first expense from the dashboard</li>
                        <li>Create groups to share expenses with friends or family</li>
                        <li>Track your spending patterns in the stats section</li>
                        <li>Set up budgets to stay on top of your finances</li>
                    </ol>

                    <p>If you have any questions, feel free to reach out to our support team.</p>

                    <p>Happy tracking!</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 Dollar Dollar Bill Y'all. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg = Message(
            subject=subject,
            recipients=[user.id],
            html=body_html
        )

        mail.send(msg)

    def send_password_reset_email(self, user, token):
        """Send password reset email with token link"""
        from flask import url_for

        reset_url = url_for('auth.reset_password', token=token, _external=True)

        subject = "Password Reset Request - Dollar Dollar Bill Y'all"

        body_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #15803d; color: white; padding: 10px 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; background-color: #15803d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 15px; }}
                .warning {{ color: #e74c3c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <h2>Hi {user.name},</h2>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>

                    <a href="{reset_url}" class="button">Reset Password</a>

                    <p>This link will expire in 1 hour.</p>

                    <p class="warning">If you didn't request this, please ignore this email. Your password will remain unchanged.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg = Message(
            subject=subject,
            recipients=[user.id],
            html=body_html
        )

        mail.send(msg)
