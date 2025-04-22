from datetime import datetime, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_user, logout_user

from app import DEV_USER_EMAIL, DEV_USER_PASSWORD
from extensions import db
from recurring_detection import detect_recurring_transactions
from services.wrappers import login_required_dev, restrict_demo_access
from simplefin_client import SimpleFin

auth_bp = Blueprint("auth", __name__)

MAX_BRIGHTNESS = 180


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    # Check if local login is disabled
    local_login_disabled = current_app.config.get(
        "LOCAL_LOGIN_DISABLE", False
    ) and current_app.config.get("OIDC_ENABLED", False)

    # Check if signups are disabled
    if current_app.config.get(
        "DISABLE_SIGNUPS", False
    ) and not current_app.config.get("DEVELOPMENT_MODE", False):
        flash("New account registration is currently disabled.")
        return redirect(url_for("login"))

    # If local login is disabled, redirect to login with message
    if local_login_disabled:
        flash("Direct account creation is disabled. Please use SSO.")
        return redirect(url_for("login"))

    # Redirect to dashboard if already logged in
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name")

        if User.query.filter_by(id=email).first():
            flash("Email already registered")
            return redirect(url_for("signup"))

        # Generate a consistent color for the user
        def generate_user_color(user_id):
            """Generate a consistent color for a user based on their ID."""
            import hashlib

            # Use MD5 hash to generate a consistent color
            hash_object = hashlib.md5(user_id.encode())
            hash_hex = hash_object.hexdigest()

            # Use the first 6 characters of the hash to create a color
            r = int(hash_hex[:2], 16)
            g = int(hash_hex[2:4], 16)
            b = int(hash_hex[4:6], 16)

            # Ensure the color is not too light
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if brightness > MAX_BRIGHTNESS:
                # If too bright, darken the color
                r = min(int(r * 0.7), 255)
                g = min(int(g * 0.7), 255)
                b = min(int(b * 0.7), 255)

            return f"#{r:02x}{g:02x}{b:02x}"

        user = User(id=email, name=name, user_color=generate_user_color(email))
        user.set_password(password)

        # Make first user admin
        is_first_user = User.query.count() == 0
        if is_first_user:
            user.is_admin = True

        db.session.add(user)
        db.session.commit()
        from app import (
            create_default_budgets,
            create_default_categories,
            send_welcome_email,
        )

        create_default_categories(user.id)
        create_default_budgets(user.id)
        # Send welcome email
        try:
            send_welcome_email(user)
        except Exception:
            current_app.logger.exception("Failed to send welcome email")

        login_user(user)
        flash("Account created successfully!")
        return redirect(url_for("dashboard"))

    return render_template(
        "signup.html",
        oidc_enabled=current_app.config.get("OIDC_ENABLED", False),
        local_login_disabled=local_login_disabled,
    )


@auth_bp.route("/login", methods=["GET", "POST"])
@restrict_demo_access
def login():
    # Check if we should show a logout message
    if session.pop("show_logout_message", False):
        flash(
            "You have been successfully logged out. You can log in again below."
        )

    # Check if local login is disabled
    oidc_enabled = current_app.config.get("OIDC_ENABLED", False)
    local_login_disable = current_app.config.get("LOCAL_LOGIN_DISABLE", False)
    local_login_disabled = local_login_disable and oidc_enabled

    # Use development mode auto-login if enabled
    if (
        current_app.config["DEVELOPMENT_MODE"]
        and not current_user.is_authenticated
    ):
        dev_user = User.query.filter_by(id=DEV_USER_EMAIL).first()
        if not dev_user:
            dev_user = User(id=DEV_USER_EMAIL, name="Developer", is_admin=True)
            dev_user.set_password(DEV_USER_PASSWORD)
            db.session.add(dev_user)
            db.session.commit()
        login_user(dev_user)
        return redirect(url_for("dashboard"))

    # Redirect to dashboard if already logged in
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    # Handle login form submission
    if request.method == "POST":
        # If local login is disabled and user tries to use the form
        if local_login_disabled:
            flash(
                f"Password login is disabled. Please use"
                f"{current_app.config.get('OIDC_PROVIDER_NAME', 'SSO')}."
            )
            return redirect(url_for("login"))

        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(id=email).first()

        if user and user.check_password(password):
            login_user(user)
            # Update last login time
            user.last_login = datetime.now(timezone.utc)

            if current_app.config.get("SIMPLEFIN_ENABLED", False):
                try:
                    # Check if user has SimpleFin connection
                    simplefin_settings = SimpleFin.query.filter_by(
                        user_id=user.id, enabled=True
                    ).first()

                    # Check if last sync was more than 6 hours ago (or never)
                    if (
                        not simplefin_settings.last_sync
                        or (
                            datetime.now(timezone.utc)
                            - simplefin_settings.last_sync
                        ).total_seconds()
                        > 6 * 3600
                    ):
                        # Start sync in background thread to avoid
                        # slowing down login
                        import threading

                        from app import sync_simplefin_for_user

                        sync_thread = threading.Thread(
                            target=sync_simplefin_for_user, args=(user.id,)
                        )
                        sync_thread.daemon = True
                        sync_thread.start()

                        # Let user know syncing is happening
                        flash(
                            "Your financial accounts are being "
                            "synchronized in the background."
                        )
                except Exception:
                    current_app.logger.exception(
                        "Error checking SimpleFin sync status"
                    )
                    # Don't show error to user to keep login smooth

            import threading

            detection_thread = threading.Thread(
                target=detect_recurring_transactions, args=(user.id,)
            )
            detection_thread.daemon = True
            detection_thread.start()

            db.session.commit()
            return redirect(url_for("dashboard"))

        flash("Invalid email or password")

    # Render the login template with appropriate flags
    return render_template(
        "login.html",
        signups_disabled=current_app.config.get("DISABLE_SIGNUPS", False),
        oidc_enabled=oidc_enabled,
        local_login_disabled=local_login_disabled,
    )


@auth_bp.route("/logout")
@login_required_dev
def logout():
    from app import reset_demo_data

    # If this is a demo user, handle demo-specific logout
    demo_timeout = current_app.extensions.get("demo_timeout")
    is_demo_user = False

    if (
        demo_timeout
        and current_user.is_authenticated
        and demo_timeout.is_demo_user(current_user.id)
    ):
        # Unregister the demo session
        demo_timeout.unregister_demo_session(current_user.id)

        # Reset demo data
        reset_demo_data(current_user.id)

        # Mark as demo user for redirection
        is_demo_user = True

    # If user was logged in via OIDC, use the OIDC logout route
    if (
        hasattr(current_user, "oidc_id")
        and current_user.oidc_id
        and current_app.config.get("OIDC_ENABLED", False)
    ):
        return redirect(url_for("logout_oidc"))

    # Standard logout for local accounts
    logout_user()

    # Set a flag to show logout message on next login
    session["show_logout_message"] = True

    # Redirect demo users to thank you page
    if is_demo_user:
        return redirect(url_for("demo_thanks"))

    return redirect(url_for("login"))

def login_required_dev(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.config["DEVELOPMENT_MODE"]:
            if not current_user.is_authenticated:
                # Get or create dev user
                dev_user = User.query.filter_by(id=DEV_USER_EMAIL).first()
                if not dev_user:
                    dev_user = User(
                        id=DEV_USER_EMAIL, name="Developer", is_admin=True
                    )
                    dev_user.set_password(DEV_USER_PASSWORD)
                    db.session.add(dev_user)
                    db.session.commit()
                # Auto login dev user
                login_user(dev_user)
            return f(*args, **kwargs)
        # Normal authentication for non-dev mode - fixed implementation
        return login_required(f)(*args, **kwargs)

    return decorated_function


def restrict_demo_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and demo_timeout.is_demo_user(
            current_user.id
        ):
            flash("Demo users cannot access this page.")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return decorated_function