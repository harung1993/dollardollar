from datetime import datetime
from datetime import timezone as tz

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from extensions import db
from models import Currency
from services.wrappers import login_required, login_required_dev
from update_currencies import update_currency_rates

currency_bp = Blueprint("currency", __name__)


@currency_bp.route("/currencies")
@login_required_dev
def manage_currencies():
    currencies = Currency.query.all()
    return render_template("currencies.html", currencies=currencies)


@currency_bp.route("/currencies/add", methods=["POST"])
@login_required_dev
def add_currency():
    if not current_user.is_admin:
        flash("Only administrators can add currencies")
        return redirect(url_for("manage_currencies"))

    code = request.form.get("code", "").upper()
    name = request.form.get("name")
    symbol = request.form.get("symbol")
    rate_to_base = float(request.form.get("rate_to_base", 1.0))
    is_base = request.form.get("is_base") == "on"

    # Validate currency code format
    if not code or len(code) != 3 or not code.isalpha():
        flash(
            "Invalid currency code. Please use 3-letter ISO currency code (e.g., USD, EUR, GBP)"
        )
        return redirect(url_for("manage_currencies"))

    # Check if currency already exists
    existing = Currency.query.filter_by(code=code).first()
    if existing:
        flash(f"Currency {code} already exists")
        return redirect(url_for("manage_currencies"))

    # If setting as base, update all existing base currencies
    if is_base:
        for currency in Currency.query.filter_by(is_base=True).all():
            currency.is_base = False

    # Create new currency
    currency = Currency(
        code=code,
        name=name,
        symbol=symbol,
        rate_to_base=rate_to_base,
        is_base=is_base,
    )
    db.session.add(currency)

    try:
        db.session.commit()
        flash(f"Currency {code} added successfully")
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        flash(f"Error adding currency: {e!s}")

    return redirect(url_for("manage_currencies"))


@currency_bp.route("/currencies/update/<code>", methods=["POST"])
@login_required_dev
def update_currency(code):
    if not current_user.is_admin:
        flash("Only administrators can update currencies")
        return redirect(url_for("manage_currencies"))

    currency = Currency.query.filter_by(code=code).first_or_404()

    # Update fields
    currency.name = request.form.get("name", currency.name)
    currency.symbol = request.form.get("symbol", currency.symbol)
    currency.rate_to_base = float(
        request.form.get("rate_to_base", currency.rate_to_base)
    )
    new_is_base = request.form.get("is_base") == "on"

    # If setting as base, update all existing base currencies
    if new_is_base and not currency.is_base:
        for curr in Currency.query.filter_by(is_base=True).all():
            curr.is_base = False

    currency.is_base = new_is_base
    currency.last_updated = datetime.now(tz.utc)

    try:
        db.session.commit()
        flash(f"Currency {code} updated successfully")
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        flash(f"Error updating currency: {e!s}")

    return redirect(url_for("manage_currencies"))


@currency_bp.route("/currencies/delete/<string:code>", methods=["DELETE"])
@login_required
def delete_currency(code):
    """Delete a currency from the system.

    Only accessible to admin users
    """
    # Ensure user is an admin
    if not current_user.is_admin:
        return jsonify(
            {
                "success": False,
                "message": "Unauthorized. Admin access required.",
            }
        ), 403

    try:
        # Find the currency
        currency = Currency.query.filter_by(code=code).first()

        if not currency:
            return jsonify(
                {"success": False, "message": f"Currency {code} not found."}
            ), 404

        # Prevent deleting the base currency
        if currency.is_base:
            return jsonify(
                {
                    "success": False,
                    "message": "Cannot delete the base currency. "
                    "Set another currency as base first.",
                }
            ), 400

        # Remove the currency
        db.session.delete(currency)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Currency {code} deleted successfully.",
            }
        )

    except Exception:
        # Rollback in case of error
        db.session.rollback()

        # Log the error
        current_app.logger.exception("Error deleting currency %s", code)

        return jsonify(
            {
                "success": False,
                "message": f"An error occurred while deleting currency {code}.",
            }
        ), 500


@currency_bp.route("/currencies/set-base/<string:code>", methods=["POST"])
@login_required
def set_base_currency(code):
    """Change the base currency.

    Only accessible to admin users
    """
    # Ensure user is an admin
    if not current_user.is_admin:
        flash("Unauthorized. Admin access required.", "error")
        return redirect(
            url_for("manage_currencies")
        )  # Changed 'currencies' to 'manage_currencies'

    try:
        # Find the currency to be set as base
        new_base_currency = Currency.query.filter_by(code=code).first()

        if not new_base_currency:
            flash(f"Currency {code} not found.", "error")
            return redirect(
                url_for("manage_currencies")
            )  # Changed 'currencies' to 'manage_currencies'

        # Find and unset the current base currency
        current_base_currency = Currency.query.filter_by(is_base=True).first()

        if current_base_currency:
            # Unset current base currency
            current_base_currency.is_base = False

        # Set new base currency
        new_base_currency.is_base = True

        # Update rate to base for this currency
        new_base_currency.rate_to_base = 1.0

        # Update rates for other currencies relative to the new base
        try:
            update_currency_rates()
        except Exception:
            # Log the error but don't prevent the base currency change
            current_app.logger.exception(
                "Error updating rates after base currency change"
            )

        # Commit changes
        db.session.commit()

        flash(f"Base currency successfully changed to {code}.", "success")
    except Exception:
        # Rollback in case of error
        db.session.rollback()

        # Log the error
        current_app.logger.exception("Error changing base currency to %s", code)

        flash("An error occurred while changing the base currency.", "error")

    return redirect(
        url_for("manage_currencies")
    )  # Changed 'currencies' to 'manage_currencies'


@currency_bp.route("/update_currency_rates", methods=["POST"])
@login_required_dev
def update_rates_route():
    """Update currency rates."""
    if not current_user.is_admin:
        flash("Only administrators can update currency rates")
        return redirect(url_for("manage_currencies"))

    result = update_currency_rates()

    if result >= 0:
        flash(f"Successfully updated {result} currency rates")
    else:
        flash("Error updating currency rates. Check the logs for details.")

    return redirect(url_for("manage_currencies"))


@currency_bp.route("/set_default_currency", methods=["POST"])
@login_required_dev
def set_default_currency():
    currency_code = request.form.get("default_currency")

    # Verify currency exists
    currency = Currency.query.filter_by(code=currency_code).first()
    if not currency:
        flash("Invalid currency selected")
        return redirect(url_for("manage_currencies"))

    # Update user's default currency
    current_user.default_currency_code = currency_code
    db.session.commit()

    flash(f"Default currency set to {currency.code} ({currency.symbol})")
    return redirect(url_for("manage_currencies"))
