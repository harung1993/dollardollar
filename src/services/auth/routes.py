"""
Auth Routes
Flask Blueprint for authentication and user management endpoints
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from src.utils.decorators import login_required_dev
from src.services.auth.service import AuthService

# Create Blueprints
bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Initialize service
auth_service = AuthService()


# ========== PUBLIC AUTH ROUTES ==========

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')

        success, message, user = auth_service.signup_user(email, password, name)
        flash(message)

        if success:
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('auth.signup'))

    return render_template('signup.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'

        from src.models.user import User

        user = User.query.filter_by(id=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash('Login successful!')

            # Redirect to next page if specified, otherwise dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('analytics.dashboard'))
        else:
            flash('Invalid email or password')
            return redirect(url_for('auth.login'))

    return render_template('login.html')


@bp.route('/logout')
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))


# ========== PASSWORD RESET ROUTES ==========

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Request password reset"""
    if current_user.is_authenticated:
        return redirect(url_for('analytics.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        success, message = auth_service.request_password_reset(email)
        flash(message)
        return redirect(url_for('auth.login'))

    return render_template('reset_password_request.html')


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    if current_user.is_authenticated:
        return redirect(url_for('analytics.dashboard'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!')
            return redirect(url_for('auth.reset_password', token=token))

        success, message, user = auth_service.reset_password_with_token(token, password)
        flash(message)

        if success:
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('auth.reset_password', token=token))

    return render_template('reset_password.html', token=token)


# ========== ADMIN USER MANAGEMENT ROUTES ==========

@admin_bp.route('/add_user', methods=['POST'])
@login_required_dev
def add_user():
    """Admin: Add a new user"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('analytics.dashboard'))

    email = request.form.get('email')
    password = request.form.get('password')
    name = request.form.get('name')
    is_admin = request.form.get('is_admin') == 'on'

    success, message, user = auth_service.admin_add_user(email, password, name, is_admin)
    flash(message)

    return redirect(url_for('auth.admin'))


@admin_bp.route('/delete_user/<user_id>', methods=['POST'])
@login_required_dev
def delete_user(user_id):
    """Admin: Delete a user and all their data"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('analytics.dashboard'))

    success, message = auth_service.admin_delete_user(user_id, current_user.id)
    flash(message)

    return redirect(url_for('auth.admin'))


@admin_bp.route('/reset_password', methods=['POST'])
@login_required_dev
def reset_password_admin():
    """Admin: Reset a user's password"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('analytics.dashboard'))

    user_id = request.form.get('user_id')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    success, message, user = auth_service.admin_reset_password(user_id, new_password, confirm_password)
    flash(message)

    return redirect(url_for('auth.admin'))


@admin_bp.route('/toggle_admin_status/<user_id>', methods=['POST'])
@login_required_dev
def toggle_admin_status(user_id):
    """Admin: Toggle a user's admin status"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('analytics.dashboard'))

    success, message, new_status = auth_service.admin_toggle_admin_status(user_id, current_user.id)
    flash(message)

    return redirect(url_for('auth.admin'))


# ========== USER PROFILE ROUTES ==========

@bp.route('/profile', methods=['GET', 'POST'])
@login_required_dev
def profile():
    """User profile page"""
    if request.method == 'POST':
        # Handle profile updates here
        flash('Profile update functionality coming soon!')
        return redirect(url_for('auth.profile'))

    return render_template('profile.html', user=current_user)


@bp.route('/change_password', methods=['POST'])
@login_required_dev
def change_password():
    """Change user password"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash('New passwords do not match!')
        return redirect(url_for('auth.profile'))

    if not current_user.check_password(current_password):
        flash('Current password is incorrect!')
        return redirect(url_for('auth.profile'))

    current_user.set_password(new_password)
    from src.extensions import db
    db.session.commit()
    flash('Password changed successfully!')

    return redirect(url_for('auth.profile'))


@bp.route('/update_color', methods=['POST'])
@login_required_dev
def update_color():
    """Update user color preference"""
    color = request.form.get('user_color')
    if color:
        current_user.user_color = color
        from src.extensions import db
        db.session.commit()
        flash('Color preference updated!')

    return redirect(url_for('auth.profile'))


@bp.route('/update_timezone', methods=['POST'])
@login_required_dev
def update_timezone():
    """Update user timezone"""
    timezone = request.form.get('timezone')
    if timezone:
        current_user.timezone = timezone
        from src.extensions import db
        db.session.commit()
        flash('Timezone updated!')

    return redirect(url_for('auth.profile'))


@bp.route('/update_notification_preferences', methods=['POST'])
@login_required_dev
def update_notification_preferences():
    """Update notification preferences"""
    # This would update notification preferences when that feature is added
    flash('Notification preferences updated!')
    return redirect(url_for('auth.profile'))


# ========== ADMIN DASHBOARD ==========

@bp.route('/admin')
@login_required_dev
def admin():
    """Admin dashboard"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('analytics.dashboard'))

    from src.models.user import User
    users = User.query.all()
    return render_template('admin.html', users=users)
