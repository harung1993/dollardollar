from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_

from extensions import db
from models import Settlement, User
from services.helpers import calculate_balances, get_base_currency
from services.wrappers import login_required_dev

settlement_bp = Blueprint("settlement", __name__)


@settlement_bp.route("/settlements")
@login_required_dev
def settlements():
    # Get all settlements involving the current user
    base_currency = get_base_currency()
    settlements = (
        Settlement.query.filter(
            or_(
                Settlement.payer_id == current_user.id,
                Settlement.receiver_id == current_user.id,
            )
        )
        .order_by(Settlement.date.desc())
        .all()
    )

    # Get all users
    users = User.query.all()

    # Calculate balances between users
    balances = calculate_balances(current_user.id)

    # Split balances into "you owe" and "you are owed" categories
    you_owe = []
    you_are_owed = []

    for balance in balances:
        if balance["amount"] < 0:
            # Current user owes money
            you_owe.append(
                {
                    "id": balance["user_id"],
                    "name": balance["name"],
                    "email": balance["email"],
                    "amount": abs(balance["amount"]),
                }
            )
        elif balance["amount"] > 0:
            # Current user is owed money
            you_are_owed.append(
                {
                    "id": balance["user_id"],
                    "name": balance["name"],
                    "email": balance["email"],
                    "amount": balance["amount"],
                }
            )

    return render_template(
        "settlements.html",
        settlements=settlements,
        users=users,
        you_owe=you_owe,
        you_are_owed=you_are_owed,
        base_currency=base_currency,
        current_user_id=current_user.id,
    )


@settlement_bp.route("/add_settlement", methods=["POST"])
@login_required_dev
def add_settlement():
    try:
        # Parse date with error handling
        try:
            settlement_date = datetime.strptime(
                request.form["date"], "%Y-%m-%d"
            )
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD format.")
            return redirect(url_for("settlements"))

        # Create settlement record
        settlement = Settlement(
            payer_id=request.form["payer_id"],
            receiver_id=request.form["receiver_id"],
            amount=float(request.form["amount"]),
            date=settlement_date,
            description=request.form.get("description", "Settlement"),
        )

        db.session.add(settlement)
        db.session.commit()
        flash("Settlement recorded successfully!")

    except Exception as e:
        flash(f"Error: {e!s}")

    return redirect(url_for("settlements"))
