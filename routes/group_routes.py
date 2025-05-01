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
from flask_login import current_user
from flask_mail import Message

from extensions import db, mail
from models import Category, Currency, Expense, Group, User
from services.defaults import create_default_categories
from services.helpers import get_base_currency
from services.wrappers import login_required_dev
from tables import group_users

group_bp = Blueprint("group", __name__)


@group_bp.route("/groups")
@login_required_dev
def groups():
    groups = (
        Group.query.join(group_users)
        .filter(group_users.c.user_id == current_user.id)
        .all()
    )
    all_users = User.query.all()
    return render_template("groups.html", groups=groups, users=all_users)


@group_bp.route("/groups/create", methods=["POST"])
@login_required_dev
def create_group():
    try:
        name = request.form.get("name")
        description = request.form.get("description")
        member_ids = request.form.getlist("members")

        group = Group(
            name=name, description=description, created_by=current_user.id
        )

        # Add creator as a member
        group.members.append(current_user)

        # Add selected members
        for member_id in member_ids:
            user = User.query.filter_by(id=member_id).first()
            if user and user != current_user:
                group.members.append(user)

        db.session.add(group)
        db.session.commit()
        flash("Group created successfully!")
    except Exception as e:  # noqa: BLE001
        flash(f"Error creating group: {e!s}")

    return redirect(url_for("groups"))


@group_bp.route("/groups/<int:group_id>")
@login_required_dev
def group_details(group_id):
    base_currency = get_base_currency()
    group = Group.query.get_or_404(group_id)

    # Check if user is member of group
    if current_user not in group.members:
        flash("Access denied. You are not a member of this group.")
        return redirect(url_for("groups"))
    categories = (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.name)
        .all()
    )

    expenses = (
        Expense.query.filter_by(group_id=group_id)
        .order_by(Expense.date.desc())
        .all()
    )
    all_users = User.query.all()
    currencies = Currency.query.all()
    return render_template(
        "group_details.html",
        group=group,
        expenses=expenses,
        currencies=currencies,
        base_currency=base_currency,
        categories=categories,
        users=all_users,
    )


@group_bp.route("/groups/<int:group_id>/add_member", methods=["POST"])
@login_required_dev
def add_group_member(group_id):
    group = Group.query.get_or_404(group_id)
    if current_user != group.creator:
        flash("Only group creator can add members")
        return redirect(url_for("group_details", group_id=group_id))

    member_id = request.form.get("user_id")
    user = User.query.filter_by(id=member_id).first()

    if user and user not in group.members:
        group.members.append(user)
        db.session.commit()
        flash(f"{user.name} added to group!")
        create_default_categories(user.id)
        # Send group invitation email
        try:
            send_group_invitation_email(user, group, current_user)
        except Exception:
            current_app.logger.exception(
                "Failed to send group invitation email"
            )

    return redirect(url_for("group_details", group_id=group_id))


@group_bp.route(
    "/groups/<int:group_id>/remove_member/<member_id>", methods=["POST"]
)
@login_required_dev
def remove_group_member(group_id, member_id):
    group = Group.query.get_or_404(group_id)
    if current_user != group.creator:
        flash("Only group creator can remove members")
        return redirect(url_for("group_details", group_id=group_id))

    user = User.query.filter_by(id=member_id).first()
    if user and user in group.members and user != group.creator:
        group.members.remove(user)
        db.session.commit()
        flash(f"{user.name} removed from group!")

    return redirect(url_for("group_details", group_id=group_id))


@group_bp.route("/groups/<int:group_id>/delete", methods=["GET", "POST"])
@login_required_dev
def delete_group(group_id):
    """Delete a group and its associated expenses."""
    # Find the group
    group = Group.query.get_or_404(group_id)

    # Security check: Only the creator can delete the group
    if current_user.id != group.created_by:
        flash("Only the group creator can delete the group", "error")
        return redirect(url_for("group_details", group_id=group_id))

    # GET request shows confirmation prompt, POST actually deletes
    if request.method == "GET":
        # Count associated expenses
        expense_count = Expense.query.filter_by(group_id=group_id).count()
        # Set up session data for confirmation
        session["delete_group_id"] = group_id
        session["delete_group_name"] = group.name
        session["delete_group_expense_count"] = expense_count
        # Show confirmation toast
        flash(
            f"Warning: Deleting this group will also delete {expense_count} "
            f"associated transactions. This action cannot be undone.",
            "warning",
        )
        return redirect(url_for("group_details", group_id=group_id))

    # POST request (actual deletion)
    try:
        # Get stored values from session
        group_name = session.get("delete_group_name", group.name)
        expense_count = session.get("delete_group_expense_count", 0)

        # Delete associated expenses first
        Expense.query.filter_by(group_id=group_id).delete()

        # Delete the group
        db.session.delete(group)
        db.session.commit()

        # Clear session data
        session.pop("delete_group_id", None)
        session.pop("delete_group_name", None)
        session.pop("delete_group_expense_count", None)

        # Success message
        if expense_count > 0:
            flash(
                f'Group "{group_name}" and {expense_count} '
                "associated transactions have been deleted",
                "success",
            )
        else:
            flash(f'Group "{group_name}" has been deleted', "success")

        return redirect(url_for("groups"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting group %s", group_id)
        flash(f"Error deleting group: {e!s}", "error")
        return redirect(url_for("group_details", group_id=group_id))


def send_group_invitation_email(user, group, inviter):
    """Send an email notification when a user is added to a group."""
    try:
        subject = (
            f"You've been added to {group.name} on Dollar Dollar Bill Y'all"
        )

        # Create invitation email body
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
                    <h1>Group Invitation</h1>
                </div>
                <div class="content">
                    <h2>Hi {user.name},</h2>
                    <p>You have been added to the group <strong>"{group.name}"</strong> by {inviter.name}.</p>

                    <h3>Group Details:</h3>
                    <ul>
                        <li><strong>Group Name:</strong> {group.name}</li>
                        <li><strong>Description:</strong> {group.description or "No description provided"}</li>
                        <li><strong>Created by:</strong> {group.creator.name}</li>
                        <li><strong>Members:</strong> {", ".join([member.name for member in group.members])}</li>
                    </ul>

                    <p>You can now track and split expenses with other members of this group.</p>

                    <a href="{request.host_url}groups/{group.id}" class="button">View Group</a>
                </div>
                <div class="footer">
                    <p>This email was sent to {user.id}. If you believe this was a mistake, please contact the group creator.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Simple text version for clients that don't support HTML
        body_text = f"""
        Group Invitation - Dollar Dollar Bill Y'all

        Hi {user.name},

        You have been added to the group "{group.name}" by {inviter.name}.

        Group Details:
        - Group Name: {group.name}
        - Description: {group.description or "No description provided"}
        - Created by: {group.creator.name}
        - Members: {", ".join([member.name for member in group.members])}

        You can now track and split expenses with other members of this group.

        View Group: {request.host_url}groups/{group.id}

        This email was sent to {user.id}. If you believe this was a mistake, please contact the group creator.
        """

        # Create and send the message
        msg = Message(
            subject=subject,
            recipients=[user.id],
            body=body_text,
            html=body_html,
        )

        # Send the email
        mail.send(msg)

        current_app.logger.info(
            f"Group invitation email sent to {user.id} for group {group.name}"
        )
        return True

    except Exception:
        current_app.logger.exception("Error sending group invitation email")
        return False
