import pytz
from flask import Blueprint, current_app, flash, redirect, request, url_for
from flask_login import current_user

from extensions import db
from services.wrappers import login_required_dev

timezone_bp = Blueprint("timezone", __name__)


@timezone_bp.route("/update_timezone", methods=["POST"])
@login_required_dev
def update_timezone():
    """Update user's timezone preference."""
    timezone = request.form.get("timezone")

    # Validate timezone
    if timezone not in pytz.all_timezones:
        flash("Invalid timezone selected.")
        return redirect(url_for("profile"))

    # Update user's timezone
    current_user.timezone = timezone
    db.session.commit()

    flash("Timezone updated successfully.")
    return redirect(url_for("profile"))


# Utility functions for timezone handling
def get_user_timezone(user):
    """Get user's timezone, defaulting to UTC."""
    return pytz.timezone(user.timezone or "UTC")


def localize_datetime(dt, user):
    """Convert datetime to user's local timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    user_tz = get_user_timezone(user)
    return dt.astimezone(user_tz)


# Context processor for timezone-aware datetime formatting
@current_app.context_processor
def timezone_processor():
    def format_datetime(dt, format="medium"):
        """Format datetime in user's local timezone."""
        if not dt:
            return ""

        # Ensure dt is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)

        # Convert to user's timezone
        if current_user.is_authenticated:
            user_tz = pytz.timezone(current_user.timezone or "UTC")
            local_dt = dt.astimezone(user_tz)
        else:
            local_dt = dt

        # Format based on preference
        if format == "short":
            return local_dt.strftime("%Y-%m-%d")
        if format == "medium":
            return local_dt.strftime("%Y-%m-%d %H:%M")
        if format == "long":
            return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")

        return local_dt

    return {"format_datetime": format_datetime}
