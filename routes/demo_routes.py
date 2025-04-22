import os
from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)
from flask_login import login_user

from extensions import db
from models import (
    Account,
    Budget,
    Category,
    CategoryMapping,
    CategorySplit,
    Expense,
    IgnoredRecurringPattern,
    RecurringExpense,
    Settlement,
    Tag,
    User,
)
from routes.auth_routes import home
from simplefin_client import SimpleFin

demo_bp = Blueprint("demo", __name__)


@demo_bp.route("/demo")
@demo_bp.route("/")
def demo_login():
    """Auto-login as demo user with session timeout."""
    import logging

    logger = logging.getLogger(__name__)

    # Check if demo mode is enabled
    if os.getenv("DEMO_MODE", "False").lower() != "true":
        # If demo mode is not enabled, use default route
        return home()

    # Get demo timeout instance
    demo_timeout = current_app.extensions.get("demo_timeout")

    # Check concurrent session limit
    max_sessions = int(os.getenv("MAX_CONCURRENT_DEMO_SESSIONS", 5))
    current_sessions = (
        demo_timeout.get_active_demo_sessions()
    )  # Remove 'if demo_timeout else 0'

    if current_sessions >= max_sessions:
        flash(
            f"Maximum number of demo sessions ({max_sessions}) has been "
            f"reached. Please try again later."
        )
        return redirect(url_for("demo_max_users"))

    # Find or create demo user
    demo_user = User.query.filter_by(id="demo@example.com").first()
    if not demo_user:
        logger.info("Creating new demo user")
        demo_user = User(
            id="demo@example.com", name="Demo User", is_admin=False
        )
        demo_user.set_password("demo")
        db.session.add(demo_user)
        db.session.commit()
    else:
        logger.info("Using existing demo user")

    # Try to register the demo session
    if not demo_timeout.register_demo_session(demo_user.id):
        flash(
            f"Maximum number of demo sessions ({max_sessions}) has been "
            f"reached. Please try again later."
        )
        return redirect(url_for("login"))

    # Always reset demo data for each new session
    logger.info("Resetting demo data for new session")
    reset_demo_data(demo_user.id)

    # Create demo data
    result = create_demo_data(demo_user.id)
    logger.info("Demo data creation result: %s", result)

    # Login as demo user
    login_user(demo_user)

    # Set demo start time and expiry time
    demo_timeout_minutes = int(os.getenv("DEMO_TIMEOUT_MINUTES", 10))
    session["demo_start_time"] = datetime.now(timezone.utc).timestamp()
    session["demo_expiry_time"] = (
        datetime.now(timezone.utc) + timedelta(minutes=demo_timeout_minutes)
    ).timestamp()

    flash(
        f"Welcome to the demo! Your session will expire in "
        f"{demo_timeout_minutes} minutes."
    )

    return redirect(url_for("dashboard"))


@demo_bp.route("/demo_max_users")
def demo_max_users():
    return render_template("demo/demo_concurrent.html")


@demo_bp.route("/demo_expired")
def demo_expired():
    """Handle expired demo sessions."""
    return render_template("demo/demo_expired.html")


@demo_bp.route("/demo-thanks")
def demo_thanks():
    """Page to thank users after demo session."""
    return render_template("demo/demo_thanks.html")


# Demo data creation function
def create_demo_data(user_id):
    """Create comprehensive sample data for demo users with proper checking."""
    import logging
    from datetime import datetime, timedelta

    logger = logging.getLogger(__name__)
    logger.info("Starting demo data creation for user %s", {user_id})

    # First create default categories
    create_default_categories(user_id)
    db.session.flush()

    # Check if demo data already exists
    existing_accounts = Account.query.filter_by(user_id=user_id).all()
    if existing_accounts:
        logger.info(
            f"Found {len(existing_accounts)} existing accounts for user {user_id}"
        )
        # We'll still continue to create any missing data

    # Create sample accounts if they don't exist
    checking = Account.query.filter_by(
        name="Demo Checking", user_id=user_id
    ).first()
    if not checking:
        logger.info("Creating demo checking account")
        checking = Account(
            name="Demo Checking",
            type="checking",
            institution="Demo Bank",
            balance=2543.87,
            user_id=user_id,
            currency_code="USD",
        )
        db.session.add(checking)

    savings = Account.query.filter_by(
        name="Demo Savings", user_id=user_id
    ).first()
    if not savings:
        logger.info("Creating demo savings account")
        savings = Account(
            name="Demo Savings",
            type="savings",
            institution="Demo Bank",
            balance=8750.25,
            user_id=user_id,
            currency_code="USD",
        )
        db.session.add(savings)

    credit = Account.query.filter_by(
        name="Demo Credit Card", user_id=user_id
    ).first()
    if not credit:
        logger.info("Creating demo credit card account")
        credit = Account(
            name="Demo Credit Card",
            type="credit",
            institution="Demo Bank",
            balance=-1250.30,
            user_id=user_id,
            currency_code="USD",
        )
        db.session.add(credit)

    investment = Account.query.filter_by(
        name="Demo Investment", user_id=user_id
    ).first()
    if not investment:
        logger.info("Creating demo investment account")
        investment = Account(
            name="Demo Investment",
            type="investment",
            institution="Vanguard",
            balance=15000.00,
            user_id=user_id,
            currency_code="USD",
        )
        db.session.add(investment)

    db.session.flush()

    # Get categories
    food_category = Category.query.filter_by(
        name="Food", user_id=user_id
    ).first()
    housing_category = Category.query.filter_by(
        name="Housing", user_id=user_id
    ).first()
    transportation_category = Category.query.filter_by(
        name="Transportation", user_id=user_id
    ).first()
    entertainment_category = Category.query.filter_by(
        name="Entertainment", user_id=user_id
    ).first()

    # Create sample transactions if they don't exist
    # 1. Regular expenses
    if not Expense.query.filter_by(
        description="Grocery shopping", user_id=user_id
    ).first():
        logger.info("Creating demo grocery expense")
        expense1 = Expense(
            description="Grocery shopping",
            amount=125.75,
            date=datetime.now(timezone.utc),
            card_used="Demo Credit Card",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=food_category.id if food_category else None,
            split_with=None,
            group_id=None,
            account_id=credit.id,
            transaction_type="expense",
        )
        db.session.add(expense1)

    if not Expense.query.filter_by(
        description="Monthly rent", user_id=user_id
    ).first():
        logger.info("Creating demo rent expense")
        expense2 = Expense(
            description="Monthly rent",
            amount=1200.00,
            date=datetime.now(timezone.utc) - timedelta(days=7),
            card_used="Demo Checking",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=housing_category.id if housing_category else None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            transaction_type="expense",
        )
        db.session.add(expense2)

    # 2. Income transactions
    if not Expense.query.filter_by(
        description="Salary deposit", user_id=user_id
    ).first():
        logger.info("Creating demo salary income")
        income1 = Expense(
            description="Salary deposit",
            amount=3500.00,
            date=datetime.now(timezone.utc) - timedelta(days=15),
            card_used="Direct Deposit",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            transaction_type="income",
        )
        db.session.add(income1)

    if not Expense.query.filter_by(
        description="Side gig payment", user_id=user_id
    ).first():
        logger.info("Creating demo side income")
        income2 = Expense(
            description="Side gig payment",
            amount=250.00,
            date=datetime.now(timezone.utc) - timedelta(days=8),
            card_used="PayPal",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            transaction_type="income",
        )
        db.session.add(income2)

    # Add expenses with category splits
    if not Expense.query.filter_by(
        description="Shopping trip (mixed)", user_id=user_id
    ).first():
        logger.info("Creating demo category split expense - shopping")

        # Get additional categories
        shopping_category = Category.query.filter_by(
            name="Shopping", user_id=user_id
        ).first()
        personal_category = Category.query.filter_by(
            name="Personal", user_id=user_id
        ).first()

        # Create the main expense with has_category_splits=True
        split_expense1 = Expense(
            description="Shopping trip (mixed)",
            amount=183.50,
            date=datetime.now(timezone.utc) - timedelta(days=3),
            card_used="Demo Credit Card",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,  # No main category when using splits
            split_with=None,
            group_id=None,
            account_id=credit.id,
            transaction_type="expense",
            has_category_splits=True,  # This is the key flag
        )
        db.session.add(split_expense1)
        db.session.flush()  # Get the expense ID

        # Add category splits
        if shopping_category:
            cat_split1 = CategorySplit(
                expense_id=split_expense1.id,
                category_id=shopping_category.id,
                amount=120.00,
                description="Clothing items",
            )
            db.session.add(cat_split1)

        if food_category:
            cat_split2 = CategorySplit(
                expense_id=split_expense1.id,
                category_id=food_category.id,
                amount=38.50,
                description="Groceries",
            )
            db.session.add(cat_split2)

        if personal_category:
            cat_split3 = CategorySplit(
                expense_id=split_expense1.id,
                category_id=personal_category.id,
                amount=25.00,
                description="Personal care items",
            )
            db.session.add(cat_split3)

    # Add another split expense example - travel related
    if not Expense.query.filter_by(
        description="Weekend trip expenses", user_id=user_id
    ).first():
        logger.info("Creating demo category split expense - travel")

        # Create the main expense
        split_expense2 = Expense(
            description="Weekend trip expenses",
            amount=342.75,
            date=datetime.now(timezone.utc) - timedelta(days=14),
            card_used="Demo Credit Card",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=credit.id,
            transaction_type="expense",
            has_category_splits=True,
        )
        db.session.add(split_expense2)
        db.session.flush()

        # Add category splits - assuming we have transportation and
        # entertainment categories
        if transportation_category:
            cat_split4 = CategorySplit(
                expense_id=split_expense2.id,
                category_id=transportation_category.id,
                amount=95.50,
                description="Gas and tolls",
            )
            db.session.add(cat_split4)

        if food_category:
            cat_split5 = CategorySplit(
                expense_id=split_expense2.id,
                category_id=food_category.id,
                amount=127.25,
                description="Dining out",
            )
            db.session.add(cat_split5)

        if entertainment_category:
            cat_split6 = CategorySplit(
                expense_id=split_expense2.id,
                category_id=entertainment_category.id,
                amount=120.00,
                description="Activities and entertainment",
            )
            db.session.add(cat_split6)

    # 3. Transfers between accounts
    if not Expense.query.filter_by(
        description="Transfer to savings", user_id=user_id
    ).first():
        logger.info("Creating demo transfer to savings")
        transfer1 = Expense(
            description="Transfer to savings",
            amount=500.00,
            date=datetime.now(timezone.utc) - timedelta(days=10),
            card_used="Internal Transfer",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            destination_account_id=savings.id,
            transaction_type="transfer",
        )
        db.session.add(transfer1)

    if not Expense.query.filter_by(
        description="Credit card payment", user_id=user_id
    ).first():
        logger.info("Creating demo credit card payment")
        transfer2 = Expense(
            description="Credit card payment",
            amount=750.00,
            date=datetime.now(timezone.utc) - timedelta(days=12),
            card_used="Internal Transfer",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            destination_account_id=credit.id,
            transaction_type="transfer",
        )
        db.session.add(transfer2)

    if not Expense.query.filter_by(
        description="Investment contribution", user_id=user_id
    ).first():
        logger.info("Creating demo investment transfer")
        transfer3 = Expense(
            description="Investment contribution",
            amount=1000.00,
            date=datetime.now(timezone.utc) - timedelta(days=20),
            card_used="Internal Transfer",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=None,
            split_with=None,
            group_id=None,
            account_id=checking.id,
            destination_account_id=investment.id,
            transaction_type="transfer",
        )
        db.session.add(transfer3)

    # 4. Create recurring expenses
    netflix_recurring = RecurringExpense.query.filter_by(
        description="Netflix Subscription", user_id=user_id
    ).first()
    if not netflix_recurring:
        logger.info("Creating demo Netflix recurring expense")
        recurring1 = RecurringExpense(
            description="Netflix Subscription",
            amount=14.99,
            card_used="Demo Credit Card",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=entertainment_category.id
            if entertainment_category
            else None,
            frequency="monthly",
            start_date=datetime.now(timezone.utc) - timedelta(days=30),
            active=True,
            account_id=credit.id,
        )
        db.session.add(recurring1)

    rent_recurring = RecurringExpense.query.filter_by(
        description="Monthly Rent Payment", user_id=user_id
    ).first()
    if not rent_recurring:
        logger.info("Creating demo rent recurring expense")
        recurring2 = RecurringExpense(
            description="Monthly Rent Payment",
            amount=1200.00,
            card_used="Demo Checking",
            split_method="equal",
            paid_by=user_id,
            user_id=user_id,
            category_id=housing_category.id if housing_category else None,
            frequency="monthly",
            start_date=datetime.now(timezone.utc) - timedelta(days=15),
            active=True,
            account_id=checking.id,
        )
        db.session.add(recurring2)

    # 5. Create budgets
    food_budget = Budget.query.filter_by(
        name="Monthly Food", user_id=user_id
    ).first()
    if not food_budget:
        logger.info("Creating demo food budget")
        budget1 = Budget(
            user_id=user_id,
            category_id=food_category.id if food_category else None,
            name="Monthly Food",
            amount=600.00,
            period="monthly",
            include_subcategories=True,
            start_date=datetime.now(timezone.utc).replace(day=1),
            is_recurring=True,
            active=True,
        )
        db.session.add(budget1)

    transport_budget = Budget.query.filter_by(
        name="Transportation Budget", user_id=user_id
    ).first()
    if not transport_budget:
        logger.info("Creating demo transportation budget")
        budget2 = Budget(
            user_id=user_id,
            category_id=transportation_category.id
            if transportation_category
            else None,
            name="Transportation Budget",
            amount=300.00,
            period="monthly",
            include_subcategories=True,
            start_date=datetime.now(timezone.utc).replace(day=1),
            is_recurring=True,
            active=True,
        )
        db.session.add(budget2)

    entertainment_budget = Budget.query.filter_by(
        name="Entertainment Budget", user_id=user_id
    ).first()
    if not entertainment_budget:
        logger.info("Creating demo entertainment budget")
        budget3 = Budget(
            user_id=user_id,
            category_id=entertainment_category.id
            if entertainment_category
            else None,
            name="Entertainment Budget",
            amount=200.00,
            period="monthly",
            include_subcategories=True,
            start_date=datetime.now(timezone.utc).replace(day=1),
            is_recurring=True,
            active=True,
        )
        db.session.add(budget3)

    # Commit all changes
    try:
        db.session.commit()
        logger.info("Demo data created/updated successfully")
        return True
    except Exception:
        db.session.rollback()
        logger.exception("Error creating demo data")
        return False


def reset_demo_data(user_id):
    """Reset all demo data for a user with comprehensive relationship handling."""
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Resetting demo data for user %s", {user_id})

    try:
        # Start a transaction
        db.session.begin()

        # 1. Get all expenses for this user
        expenses = Expense.query.filter_by(user_id=user_id).all()
        expense_ids = [expense.id for expense in expenses]

        # 2. Delete category splits referencing these expenses
        if expense_ids:
            split_count = CategorySplit.query.filter(
                CategorySplit.expense_id.in_(expense_ids)
            ).delete(synchronize_session=False)
            logger.info("Deleted %s category splits", {split_count})

        # 3. Delete tags associations for these expenses
        if expense_ids:
            from sqlalchemy import text

            db.session.execute(
                text("""
                DELETE FROM expense_tags 
                WHERE expense_id IN :expense_ids
            """),
                {
                    "expense_ids": tuple(expense_ids)
                    if len(expense_ids) > 1
                    else f"({expense_ids[0]})"
                },
            )
            logger.info("Deleted expense tag associations")

        # 4. Now delete expenses
        expense_count = Expense.query.filter_by(user_id=user_id).delete()
        logger.info("Deleted %s expenses", {expense_count})

        # 5. Delete recurring expenses
        recurring_count = RecurringExpense.query.filter_by(
            user_id=user_id
        ).delete()
        logger.info("Deleted %s recurring expenses", {recurring_count})

        # 6. Delete budgets
        budget_count = Budget.query.filter_by(user_id=user_id).delete()
        logger.info("Deleted %s budgets", {budget_count})

        # 7. Delete category mappings
        mapping_count = CategoryMapping.query.filter_by(
            user_id=user_id
        ).delete()
        logger.info("Deleted %s category mappings", {mapping_count})

        # 8. Delete ignored patterns
        pattern_count = IgnoredRecurringPattern.query.filter_by(
            user_id=user_id
        ).delete()
        logger.info("Deleted %s ignored patterns", {pattern_count})

        # 9. Delete SimpleFin settings
        simplefin_count = SimpleFin.query.filter_by(user_id=user_id).delete()
        logger.info("Deleted %s SimpleFin settings", {simplefin_count})

        # 10. Delete settlements
        from sqlalchemy import or_

        settlement_count = Settlement.query.filter(
            or_(
                Settlement.payer_id == user_id,
                Settlement.receiver_id == user_id,
            )
        ).delete(synchronize_session=False)
        logger.info("Deleted %s settlements", {settlement_count})

        # 11. Delete all accounts
        account_count = Account.query.filter_by(user_id=user_id).delete()
        logger.info("Deleted %s accounts", {account_count})

        # 12. Delete all tags
        tag_count = Tag.query.filter_by(user_id=user_id).delete()
        logger.info("Deleted %s tags", {tag_count})

        # 13. Delete all categories
        category_count = Category.query.filter_by(user_id=user_id).delete()
        logger.info("Deleted %s categories", {category_count})

        # Commit the transaction
        db.session.commit()
        logger.info("Demo data reset successful")
        return True
    except Exception:
        db.session.rollback()
        logger.exception("Error resetting demo data")
        return False
