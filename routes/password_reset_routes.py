from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask import current_app as app
from flask_login import current_user
from flask_mail import Message

from extensions import db, mail
from models import User

password_bp = Blueprint("password", __name__)


@password_bp.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form["email"]
        user = User.query.filter_by(id=email).first()

        if user:
            token = user.generate_reset_token()
            db.session.commit()

            # Generate the reset password URL
            reset_url = url_for(
                "reset_password", token=token, email=email, _external=True
            )

            # Prepare the email
            subject = "Password Reset Request"
            body_text = f"""
                    To reset your password, please visit the following link:
                    {reset_url}

                    If you did not make this request, please ignore this email.

                    This link will expire in 1 hour.
                    """
            body_html = f'''
                    <p>To reset your password, please click the link below:</p>
                    <p><a href="{reset_url}">Reset Your Password</a></p>
                    <p>If you did not make this request, please ignore this email.</p>
                    <p>This link will expire in 1 hour.</p>
                    '''

            try:
                msg = Message(
                    subject=subject,
                    recipients=[email],
                    body=body_text,
                    html=body_html,
                )
                mail.send(msg)
                app.logger.info(f"Password reset email sent to {email}")

                # Success message
                # (don't reveal if email exists or not for security)
                flash(
                    "If your email address exists in our database, "
                    "you will receive a password reset link shortly."
                )
            except Exception:
                app.logger.exception("Error sending password reset email")
                flash(
                    "An error occurred while sending the password reset email. "
                    "Please try again later."
                )
        else:
            # Still show success message even if email not found (security)
            flash(
                "If your email address exists in our database, "
                "you will receive a password reset link shortly."
            )
            app.logger.info(
                f"Password reset requested for non-existent email: {email}"
            )

        return redirect(url_for("login"))

    return render_template("reset_password.html")


@password_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    email = request.args.get("email")
    if not email:
        flash("Invalid reset link.")
        return redirect(url_for("login"))

    user = User.query.filter_by(id=email).first()

    # Verify the token is valid
    if not user or not user.verify_reset_token(token):
        flash("Invalid or expired reset link. Please request a new one.")
        return redirect(url_for("reset_password_request"))

    if request.method == "POST":
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template(
                "reset_password_confirm.html", token=token, email=email
            )

        # Update the user's password
        user.set_password(password)
        user.clear_reset_token()
        db.session.commit()

        app.logger.info(f"Password reset successful for user: {email}")
        flash(
            "Your password has been reset successfully. "
            "You can now log in with your new password."
        )
        return redirect(url_for("login"))

    return render_template(
        "reset_password_confirm.html", token=token, email=email
    )
