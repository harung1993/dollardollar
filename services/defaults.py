from datetime import datetime
from datetime import timezone as tz

from flask import current_app

from extensions import db
from models import Budget, Category, CategoryMapping


def create_default_categories(user_id):
    """Create default expense categories for a new user."""
    default_categories = [
        # Housing
        {
            "name": "Housing",
            "icon": "fa-home",
            "color": "#3498db",
            "subcategories": [
                {
                    "name": "Rent/Mortgage",
                    "icon": "fa-building",
                    "color": "#3498db",
                },
                {"name": "Utilities", "icon": "fa-bolt", "color": "#3498db"},
                {
                    "name": "Home Maintenance",
                    "icon": "fa-tools",
                    "color": "#3498db",
                },
            ],
        },
        # Food
        {
            "name": "Food",
            "icon": "fa-utensils",
            "color": "#e74c3c",
            "subcategories": [
                {
                    "name": "Groceries",
                    "icon": "fa-shopping-basket",
                    "color": "#e74c3c",
                },
                {
                    "name": "Restaurants",
                    "icon": "fa-hamburger",
                    "color": "#e74c3c",
                },
                {
                    "name": "Coffee Shops",
                    "icon": "fa-coffee",
                    "color": "#e74c3c",
                },
            ],
        },
        # Transportation
        {
            "name": "Transportation",
            "icon": "fa-car",
            "color": "#2ecc71",
            "subcategories": [
                {"name": "Gas", "icon": "fa-gas-pump", "color": "#2ecc71"},
                {
                    "name": "Public Transit",
                    "icon": "fa-bus",
                    "color": "#2ecc71",
                },
                {"name": "Rideshare", "icon": "fa-taxi", "color": "#2ecc71"},
            ],
        },
        # Shopping
        {
            "name": "Shopping",
            "icon": "fa-shopping-cart",
            "color": "#9b59b6",
            "subcategories": [
                {"name": "Clothing", "icon": "fa-tshirt", "color": "#9b59b6"},
                {
                    "name": "Electronics",
                    "icon": "fa-laptop",
                    "color": "#9b59b6",
                },
                {"name": "Gifts", "icon": "fa-gift", "color": "#9b59b6"},
            ],
        },
        # Entertainment
        {
            "name": "Entertainment",
            "icon": "fa-film",
            "color": "#f39c12",
            "subcategories": [
                {"name": "Movies", "icon": "fa-ticket-alt", "color": "#f39c12"},
                {"name": "Music", "icon": "fa-music", "color": "#f39c12"},
                {
                    "name": "Subscriptions",
                    "icon": "fa-play-circle",
                    "color": "#f39c12",
                },
            ],
        },
        # Health
        {
            "name": "Health",
            "icon": "fa-heartbeat",
            "color": "#1abc9c",
            "subcategories": [
                {
                    "name": "Medical",
                    "icon": "fa-stethoscope",
                    "color": "#1abc9c",
                },
                {
                    "name": "Pharmacy",
                    "icon": "fa-prescription-bottle",
                    "color": "#1abc9c",
                },
                {"name": "Fitness", "icon": "fa-dumbbell", "color": "#1abc9c"},
            ],
        },
        # Personal
        {
            "name": "Personal",
            "icon": "fa-user",
            "color": "#34495e",
            "subcategories": [
                {"name": "Self-care", "icon": "fa-spa", "color": "#34495e"},
                {
                    "name": "Education",
                    "icon": "fa-graduation-cap",
                    "color": "#34495e",
                },
            ],
        },
        # Other
        {
            "name": "Other",
            "icon": "fa-question-circle",
            "color": "#95a5a6",
            "is_system": True,
        },
    ]

    for cat_data in default_categories:
        subcategories = cat_data.pop("subcategories", [])
        category = Category(user_id=user_id, **cat_data)
        db.session.add(category)
        db.session.flush()  # Get the ID without committing

        for subcat_data in subcategories:
            subcat = Category(
                user_id=user_id, parent_id=category.id, **subcat_data
            )
            db.session.add(subcat)

    db.session.commit()

    # Create default category mappings after creating categories
    create_default_category_mappings(user_id)


def create_default_budgets(user_id):  # noqa: C901 PLR0912
    """Create default budget templates for a new user.

    All deactivated by default.
    """
    # Get the user's categories first
    categories = Category.query.filter_by(user_id=user_id).all()
    category_map = {}

    # Create a map of category types to their IDs
    for category in categories:
        if category.name == "Housing":
            category_map["housing"] = category.id
        elif category.name == "Food":
            category_map["food"] = category.id
        elif category.name == "Transportation":
            category_map["transportation"] = category.id
        elif category.name == "Entertainment":
            category_map["entertainment"] = category.id
        elif category.name == "Shopping":
            category_map["shopping"] = category.id
        elif category.name == "Health":
            category_map["health"] = category.id
        elif category.name == "Personal":
            category_map["personal"] = category.id
        elif category.name == "Other":
            category_map["other"] = category.id

    # Default budget templates with realistic amounts
    default_budgets = [
        {
            "name": "Monthly Housing Budget",
            "category_type": "housing",
            "amount": 1200,
            "period": "monthly",
            "include_subcategories": True,
        },
        {
            "name": "Monthly Food Budget",
            "category_type": "food",
            "amount": 600,
            "period": "monthly",
            "include_subcategories": True,
        },
        {
            "name": "Monthly Transportation",
            "category_type": "transportation",
            "amount": 400,
            "period": "monthly",
            "include_subcategories": True,
        },
        {
            "name": "Monthly Entertainment",
            "category_type": "entertainment",
            "amount": 200,
            "period": "monthly",
            "include_subcategories": True,
        },
        {
            "name": "Monthly Shopping",
            "category_type": "shopping",
            "amount": 300,
            "period": "monthly",
            "include_subcategories": True,
        },
        {
            "name": "Monthly Healthcare",
            "category_type": "health",
            "amount": 150,
            "period": "monthly",
            "include_subcategories": True,
        },
        {
            "name": "Monthly Personal",
            "category_type": "personal",
            "amount": 200,
            "period": "monthly",
            "include_subcategories": True,
        },
        {
            "name": "Weekly Grocery Budget",
            "category_type": "food",  # Will use subcategory if available
            "amount": 150,
            "period": "weekly",
            "include_subcategories": False,
            "subcategory_name": "Groceries",  # Try to find this subcategory
        },
        {
            "name": "Weekly Dining Out",
            "category_type": "food",  # Will use subcategory if available
            "amount": 75,
            "period": "weekly",
            "include_subcategories": False,
            "subcategory_name": "Restaurants",  # Try to find this subcategory
        },
        {
            "name": "Monthly Subscriptions",
            "category_type": "entertainment",  # Will use subcategory if available
            "amount": 50,
            "period": "monthly",
            "include_subcategories": False,
            "subcategory_name": "Subscriptions",  # Try to find this subcategory
        },
        {
            "name": "Annual Vacation",
            "category_type": "personal",
            "amount": 1500,
            "period": "yearly",
            "include_subcategories": False,
        },
    ]

    # Add budgets to database
    budgets_added = 0

    for budget_template in default_budgets:
        # Determine the category ID to use
        category_id = None
        cat_type = budget_template["category_type"]

        if cat_type in category_map:
            category_id = category_map[cat_type]

            # Check for subcategory if specified
            if "subcategory_name" in budget_template:
                # Find the category
                main_category = Category.query.get(category_id)
                if main_category and hasattr(main_category, "subcategories"):
                    # Look for matching subcategory
                    for subcat in main_category.subcategories:
                        if (
                            budget_template["subcategory_name"].lower()
                            in subcat.name.lower()
                        ):
                            category_id = subcat.id
                            break

        # If we have a valid category, create the budget
        if category_id:
            new_budget = Budget(
                user_id=user_id,
                category_id=category_id,
                name=budget_template["name"],
                amount=budget_template["amount"],
                period=budget_template["period"],
                include_subcategories=budget_template.get(
                    "include_subcategories", True
                ),
                start_date=datetime.now(tz.utc),
                is_recurring=True,
                active=False,  # Deactivated by default
                created_at=datetime.now(tz.utc),
                updated_at=datetime.now(tz.utc),
            )

            db.session.add(new_budget)
            budgets_added += 1

    if budgets_added > 0:
        db.session.commit()

    return budgets_added


def create_default_category_mappings(user_id):
    """Create default category mappings for a new user."""
    # Check if user already has any mappings
    existing_mappings_count = CategoryMapping.query.filter_by(
        user_id=user_id
    ).count()

    # Only create defaults if user has no mappings
    if existing_mappings_count > 0:
        return

    # Get user's categories to map to
    # We'll need to find the appropriate category IDs for the current user
    categories = {}

    # Find common top-level categories
    for category_name in [
        "Food",
        "Transportation",
        "Housing",
        "Shopping",
        "Entertainment",
        "Health",
        "Personal",
        "Other",
    ]:
        category = Category.query.filter_by(
            user_id=user_id, name=category_name, parent_id=None
        ).first()

        if category:
            categories[category_name.lower()] = category.id

            # Also get subcategories
            for subcategory in category.subcategories:
                categories[subcategory.name.lower()] = subcategory.id

    # If we couldn't find any categories, we can't create mappings
    if not categories:
        current_app.logger.warning(
            "Could not create default category mappings for user %s: "
            "no categories found",
            user_id,
        )
        return

    # Default mappings as (keyword, category_key, is_regex, priority)
    default_mappings = [
        # Food & Dining
        ("grocery", "groceries", False, 5),
        ("groceries", "groceries", False, 5),
        ("supermarket", "groceries", False, 5),
        ("walmart", "groceries", False, 3),
        ("target", "groceries", False, 3),
        ("costco", "groceries", False, 5),
        ("safeway", "groceries", False, 5),
        ("kroger", "groceries", False, 5),
        ("aldi", "groceries", False, 5),
        ("trader joe", "groceries", False, 5),
        ("whole foods", "groceries", False, 5),
        ("wegmans", "groceries", False, 5),
        ("publix", "groceries", False, 5),
        ("sprouts", "groceries", False, 5),
        ("sams club", "groceries", False, 5),
        # Restaurants
        ("restaurant", "restaurants", False, 5),
        ("dining", "restaurants", False, 5),
        ("takeout", "restaurants", False, 5),
        ("doordash", "restaurants", False, 5),
        ("ubereats", "restaurants", False, 5),
        ("grubhub", "restaurants", False, 5),
        ("mcdonald", "restaurants", False, 5),
        ("burger", "restaurants", False, 4),
        ("pizza", "restaurants", False, 4),
        ("chipotle", "restaurants", False, 5),
        ("panera", "restaurants", False, 5),
        ("kfc", "restaurants", False, 5),
        ("wendy's", "restaurants", False, 5),
        ("taco bell", "restaurants", False, 5),
        ("chick-fil-a", "restaurants", False, 5),
        ("five guys", "restaurants", False, 5),
        ("ihop", "restaurants", False, 5),
        ("denny's", "restaurants", False, 5),
        # Coffee shops
        ("starbucks", "coffee shops", False, 5),
        ("coffee", "coffee shops", False, 4),
        ("dunkin", "coffee shops", False, 5),
        ("peet", "coffee shops", False, 5),
        ("tim hortons", "coffee shops", False, 5),
        # Gas & Transportation
        ("gas station", "gas", False, 5),
        ("gasoline", "gas", False, 5),
        ("fuel", "gas", False, 5),
        ("chevron", "gas", False, 5),
        ("shell", "gas", False, 5),
        ("exxon", "gas", False, 5),
        ("tesla supercharger", "gas", False, 5),
        ("ev charging", "gas", False, 5),
        # Rideshare & Transit
        ("uber", "rideshare", False, 5),
        ("lyft", "rideshare", False, 5),
        ("taxi", "rideshare", False, 5),
        ("transit", "public transit", False, 5),
        ("subway", "public transit", False, 5),
        ("bus", "public transit", False, 5),
        ("train", "public transit", False, 5),
        ("amtrak", "public transit", False, 5),
        ("greyhound", "public transit", False, 5),
        ("parking", "transportation", False, 5),
        ("toll", "transportation", False, 5),
        ("bike share", "transportation", False, 5),
        ("scooter rental", "transportation", False, 5),
        # Housing & Utilities
        ("rent", "rent/mortgage", False, 5),
        ("mortgage", "rent/mortgage", False, 5),
        ("airbnb", "rent/mortgage", False, 5),
        ("vrbo", "rent/mortgage", False, 5),
        ("water bill", "utilities", False, 5),
        ("electric", "utilities", False, 5),
        ("utility", "utilities", False, 5),
        ("utilities", "utilities", False, 5),
        ("internet", "utilities", False, 5),
        ("Ngrid", "utilities", False, 5),
        ("maintenance", "home maintenance", False, 4),
        ("repair", "home maintenance", False, 4),
        ("hvac", "home maintenance", False, 5),
        ("pest control", "home maintenance", False, 5),
        ("home security", "home maintenance", False, 5),
        ("home depot", "home maintenance", False, 5),
        ("lowe's", "home maintenance", False, 5),
        # Shopping
        ("amazon", "shopping", False, 5),
        ("ebay", "shopping", False, 5),
        ("etsy", "shopping", False, 5),
        ("clothing", "clothing", False, 5),
        ("apparel", "clothing", False, 5),
        ("shoes", "clothing", False, 5),
        ("electronics", "electronics", False, 5),
        ("best buy", "electronics", False, 5),
        ("apple", "electronics", False, 5),
        ("microsoft", "electronics", False, 5),
        ("furniture", "shopping", False, 5),
        ("homegoods", "shopping", False, 5),
        ("ikea", "shopping", False, 5),
        ("tj maxx", "shopping", False, 5),
        ("marshalls", "shopping", False, 5),
        ("nordstrom", "shopping", False, 5),
        ("macys", "shopping", False, 5),
        ("zara", "shopping", False, 5),
        ("uniqlo", "shopping", False, 5),
        ("shein", "shopping", False, 5),
        # Entertainment & Subscriptions
        ("movie", "movies", False, 5),
        ("cinema", "movies", False, 5),
        ("theater", "movies", False, 5),
        ("amc", "movies", False, 5),
        ("regal", "movies", False, 5),
        ("netflix", "subscriptions", False, 5),
        ("hulu", "subscriptions", False, 5),
        ("spotify", "subscriptions", False, 5),
        ("apple music", "subscriptions", False, 5),
        ("disney+", "subscriptions", False, 5),
        ("hbo", "subscriptions", False, 5),
        ("prime video", "subscriptions", False, 5),
        ("paramount+", "subscriptions", False, 5),
        ("game", "entertainment", False, 4),
        ("playstation", "entertainment", False, 5),
        ("xbox", "entertainment", False, 5),
        ("nintendo", "entertainment", False, 5),
        ("concert", "entertainment", False, 5),
        ("festival", "entertainment", False, 5),
        ("sports ticket", "entertainment", False, 5),
        # Health & Wellness
        ("gym", "health", False, 5),
        ("fitness", "health", False, 5),
        ("doctor", "health", False, 5),
        ("dentist", "health", False, 5),
        ("hospital", "health", False, 5),
        ("pharmacy", "health", False, 5),
        ("walgreens", "health", False, 5),
        ("cvs", "health", False, 5),
        ("rite aid", "health", False, 5),
        ("vision", "health", False, 5),
        ("glasses", "health", False, 5),
        ("contacts", "health", False, 5),
        ("insurance", "health", False, 5),
    ]

    # Create the mappings
    for keyword, category_key, is_regex, priority in default_mappings:
        # Check if we have a matching category for this keyword
        if category_key in categories:
            category_id = categories[category_key]

            # Create the mapping
            mapping = CategoryMapping(
                user_id=user_id,
                keyword=keyword,
                category_id=category_id,
                is_regex=is_regex,
                priority=priority,
                match_count=0,
                active=True,
            )

            db.session.add(mapping)

    # Commit all mappings at once
    try:
        db.session.commit()
        current_app.logger.info(
            "Created default category mappings for user %s", user_id
        )
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error creating default category mappings")
