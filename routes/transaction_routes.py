from flask import Blueprint, jsonify
from flask_login import current_user
from sqlalchemy import and_, or_

from models import Expense, Settlement, User
from services.wrappers import login_required_dev

transaction_bp = Blueprint("auth", __name__)


@transaction_bp.route("/get_transaction_details/<other_user_id>")
@login_required_dev
def get_transaction_details(other_user_id):
    """Fetch transaction details between current user and another user."""
    # Query expenses involving both users
    expenses = (
        Expense.query.filter(
            or_(
                and_(
                    Expense.user_id == current_user.id,
                    Expense.split_with.like(f"%{other_user_id}%"),
                ),
                and_(
                    Expense.user_id == other_user_id,
                    Expense.split_with.like(f"%{current_user.id}%"),
                ),
            )
        )
        .order_by(Expense.date.desc())
        .limit(20)
        .all()
    )

    # Query settlements between both users
    settlements = (
        Settlement.query.filter(
            or_(
                and_(
                    Settlement.payer_id == current_user.id,
                    Settlement.receiver_id == other_user_id,
                ),
                and_(
                    Settlement.payer_id == other_user_id,
                    Settlement.receiver_id == current_user.id,
                ),
            )
        )
        .order_by(Settlement.date.desc())
        .limit(20)
        .all()
    )

    # Prepare transaction details
    transactions = []

    # Add expenses
    for expense in expenses:
        splits = expense.calculate_splits()
        transactions.append(
            {
                "type": "expense",
                "date": expense.date.strftime("%Y-%m-%d"),
                "description": expense.description,
                "amount": expense.amount,
                "payer": splits["payer"]["name"],
                "split_method": expense.split_method,
            }
        )

    # Add settlements
    for settlement in settlements:
        transactions.extend(
            [
                {
                    "type": "settlement",
                    "date": settlement.date.strftime("%Y-%m-%d"),
                    "description": settlement.description,
                    "amount": settlement.amount,
                    "payer": User.query.get(settlement.payer_id).name,
                    "receiver": User.query.get(settlement.receiver_id).name,
                }
            ]
        )

    # Sort transactions by date, most recent first
    transactions.sort(key=lambda x: x["date"], reverse=True)

    return jsonify(transactions)
