from datetime import datetime, timedelta
from datetime import timezone as tz

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user
from sqlalchemy import func

from extensions import db
from models import Category, CategoryMapping, CategorySplit, Expense
from services.defaults import create_default_category_mappings
from services.helpers import auto_categorize_transaction
from services.wrappers import demo_time_limited, login_required_dev

category_bp = Blueprint("category", __name__)


@category_bp.route("/get_category_splits/<int:expense_id>")
@login_required_dev
def get_category_splits(expense_id):
    """Get category splits for an expense."""
    try:
        expense = Expense.query.get_or_404(expense_id)

        # Security check
        if expense.user_id != current_user.id:
            return jsonify(
                {
                    "success": False,
                    "message": "You do not have permission to view this expense",
                }
            ), 403

        if not expense.has_category_splits:
            return jsonify({"success": True, "splits": []})

        # Get all category splits for this expense
        splits = CategorySplit.query.filter_by(expense_id=expense_id).all()

        # Format the response
        splits_data = []
        for split in splits:
            category = Category.query.get(split.category_id)

            # Include category details if available
            category_data = (
                {
                    "id": category.id,
                    "name": category.name,
                    "icon": category.icon,
                    "color": category.color,
                }
                if category
                else {
                    "id": None,
                    "name": "Unknown",
                    "icon": "fa-question",
                    "color": "#6c757d",
                }
            )

            splits_data.append(
                {
                    "id": split.id,
                    "category_id": split.category_id,
                    "amount": split.amount,
                    "description": split.description,
                    "category": category_data,
                }
            )

        return jsonify({"success": True, "splits": splits_data})

    except Exception as e:
        current_app.logger.exception("Error getting category splits")
        return jsonify({"success": False, "message": f"Error: {e!s}"}), 500


@category_bp.route("/category_mappings")
@login_required_dev
@demo_time_limited
def manage_category_mappings():
    """View and manage category mappings for auto-categorization."""
    # Get all mappings for the current user
    mappings = (
        CategoryMapping.query.filter_by(user_id=current_user.id)
        .order_by(
            CategoryMapping.active.desc(),
            CategoryMapping.priority.desc(),
            CategoryMapping.match_count.desc(),
        )
        .all()
    )

    # Get all categories for the dropdown
    categories = (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.name)
        .all()
    )

    return render_template(
        "category_mappings.html", mappings=mappings, categories=categories
    )


@category_bp.route("/category_mappings/create_defaults", methods=["POST"])
@login_required_dev
@demo_time_limited
def create_default_mappings_route():
    """Create default category mappings for the current user (on demand)."""
    try:
        # Get current count to check if any were created
        current_count = CategoryMapping.query.filter_by(
            user_id=current_user.id
        ).count()

        # Call the function to create default mappings
        create_default_category_mappings(current_user.id)

        # Get new count to see how many were created
        new_count = CategoryMapping.query.filter_by(
            user_id=current_user.id
        ).count()
        created_count = new_count - current_count

        # Return success response
        return jsonify(
            {
                "success": True,
                "count": created_count,
                "message": f"Successfully created {created_count} default mapping rules.",
            }
        )

    except Exception as e:
        current_app.logger.exception("Error creating default mappings")
        return jsonify(
            {
                "success": False,
                "message": f"Error creating default mappings: {e!s}",
            }
        ), 500


@category_bp.route("/bulk_categorize_transactions", methods=["POST"])
@login_required_dev
def bulk_categorize_transactions():
    """Categorize all uncategorized transactions using category mapping rules."""
    try:
        # Get all uncategorized transactions for the current user
        uncategorized = Expense.query.filter_by(
            user_id=current_user.id, category_id=None
        ).all()

        # Track statistics
        total_count = len(uncategorized)
        categorized_count = 0

        # Process each transaction
        for expense in uncategorized:
            # Skip if no description
            if not expense.description:
                continue

            # Try to auto-categorize
            category_id = auto_categorize_transaction(
                expense.description, current_user.id
            )

            # If we found a category, update the transaction
            if category_id:
                expense.category_id = category_id
                categorized_count += 1

        # Save all changes
        db.session.commit()

        flash(
            f"Successfully categorized {categorized_count} out of {total_count} transactions!"
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error bulk categorizing transactions")
        flash(f"Error: {e!s}")

    # Determine where to redirect based on the referrer
    referrer = request.referrer
    if "transactions" in referrer:
        return redirect(url_for("transactions"))
    if "category_mappings" in referrer:
        return redirect(url_for("manage_category_mappings"))
    return redirect(url_for("dashboard"))


@category_bp.route("/category_mappings/add", methods=["POST"])
@login_required_dev
@demo_time_limited
def add_category_mapping():
    """Add a new category mapping rule."""
    keyword = request.form.get("keyword", "").strip()
    category_id = request.form.get("category_id")
    is_regex = request.form.get("is_regex") == "on"
    priority = int(request.form.get("priority", 0))

    # Validate inputs
    if not keyword or not category_id:
        flash("Keyword and category are required.")
        return redirect(url_for("manage_category_mappings"))

    # Check if mapping already exists
    existing = CategoryMapping.query.filter_by(
        user_id=current_user.id, keyword=keyword
    ).first()

    if existing:
        flash(
            "A mapping with this keyword already exists. Please edit the existing one."
        )
        return redirect(url_for("manage_category_mappings"))

    # Create new mapping
    mapping = CategoryMapping(
        user_id=current_user.id,
        keyword=keyword,
        category_id=category_id,
        is_regex=is_regex,
        priority=priority,
        active=True,
    )

    db.session.add(mapping)
    db.session.commit()

    flash("Category mapping rule added successfully.")
    return redirect(url_for("manage_category_mappings"))


@category_bp.route("/category_mappings/edit/<int:mapping_id>", methods=["POST"])
@login_required_dev
@demo_time_limited
def edit_category_mapping(mapping_id):
    """Edit an existing category mapping rule."""
    mapping = CategoryMapping.query.get_or_404(mapping_id)

    # Check if mapping belongs to current user
    if mapping.user_id != current_user.id:
        flash("You don't have permission to edit this mapping.")
        return redirect(url_for("manage_category_mappings"))

    # Update fields
    mapping.keyword = request.form.get("keyword", "").strip()
    mapping.category_id = request.form.get("category_id")
    mapping.is_regex = request.form.get("is_regex") == "on"
    mapping.priority = int(request.form.get("priority", 0))

    db.session.commit()

    flash("Category mapping updated successfully.")
    return redirect(url_for("manage_category_mappings"))


@category_bp.route(
    "/category_mappings/toggle/<int:mapping_id>", methods=["POST"]
)
@login_required_dev
def toggle_category_mapping(mapping_id):
    """Toggle the active status of a mapping."""
    mapping = CategoryMapping.query.get_or_404(mapping_id)

    # Check if mapping belongs to current user
    if mapping.user_id != current_user.id:
        flash("You don't have permission to modify this mapping.")
        return redirect(url_for("manage_category_mappings"))

    # Toggle active status
    mapping.active = not mapping.active
    db.session.commit()

    status = "activated" if mapping.active else "deactivated"
    flash(f"Category mapping {status} successfully.")

    return redirect(url_for("manage_category_mappings"))


@category_bp.route(
    "/category_mappings/delete/<int:mapping_id>", methods=["POST"]
)
@login_required_dev
def delete_category_mapping(mapping_id):
    """Delete a category mapping rule."""
    mapping = CategoryMapping.query.get_or_404(mapping_id)

    # Check if mapping belongs to current user
    if mapping.user_id != current_user.id:
        flash("You don't have permission to delete this mapping.")
        return redirect(url_for("manage_category_mappings"))

    db.session.delete(mapping)
    db.session.commit()

    flash("Category mapping deleted successfully.")
    return redirect(url_for("manage_category_mappings"))


@category_bp.route("/category_mappings/learn_from_history", methods=["POST"])
@login_required_dev
def learn_from_transaction_history():
    """Analyze transaction history to create category mapping suggestions."""
    # Get number of days to analyze from the form
    days = int(request.form.get("days", 30))

    # Calculate start date
    start_date = datetime.now(tz.utc) - timedelta(days=days)

    # Get transactions from the specified period that have categories
    transactions = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.category_id.isnot(None),
    ).all()

    # Group transactions by category and description pattern
    patterns = {}
    for transaction in transactions:
        # Skip transactions without descriptions
        if not transaction.description:
            continue

        # Clean up description and extract a key word/phrase
        keyword = extract_keywords(transaction.description)
        if not keyword:
            continue

        # Create a unique key for this keyword + category combo
        key = f"{keyword}_{transaction.category_id}"

        if key not in patterns:
            patterns[key] = {
                "keyword": keyword,
                "category_id": transaction.category_id,
                "count": 0,
                "total_amount": 0,
                "transactions": [],
            }

        # Update the pattern
        patterns[key]["count"] += 1
        patterns[key]["total_amount"] += transaction.amount
        patterns[key]["transactions"].append(transaction.id)

    # Find significant patterns (occurred at least 3 times)
    significant_patterns = [p for p in patterns.values() if p["count"] >= 3]

    # Sort by frequency
    significant_patterns.sort(key=lambda x: x["count"], reverse=True)

    # Create mappings for these patterns (only if they don't already exist)
    created_count = 0
    for pattern in significant_patterns[:15]:  # Limit to top 15
        # Check if this pattern already exists
        existing = CategoryMapping.query.filter_by(
            user_id=current_user.id,
            keyword=pattern["keyword"],
            category_id=pattern["category_id"],
        ).first()

        if not existing:
            # Create a new mapping
            mapping = CategoryMapping(
                user_id=current_user.id,
                keyword=pattern["keyword"],
                category_id=pattern["category_id"],
                is_regex=False,
                priority=0,
                match_count=pattern["count"],
                active=True,
            )

            db.session.add(mapping)
            created_count += 1

    if created_count > 0:
        db.session.commit()
        flash(
            f"Created {created_count} new category mapping rules from your transaction history."
        )
    else:
        flash("No new mapping patterns were found in your transaction history.")

    return redirect(url_for("manage_category_mappings"))


@category_bp.route("/category_mappings/upload", methods=["POST"])
@login_required_dev
def upload_category_mappings():
    """Upload and import category mappings from a CSV file."""
    if "mapping_file" not in request.files:
        flash("No file provided")
        return redirect(url_for("manage_category_mappings"))

    mapping_file = request.files["mapping_file"]

    if mapping_file.filename == "":
        flash("No file selected")
        return redirect(url_for("manage_category_mappings"))

    # Case-insensitive extension check
    if not mapping_file.filename.lower().endswith(".csv"):
        flash("File must be a CSV")
        return redirect(url_for("manage_category_mappings"))

    try:
        # Read file content
        file_content = mapping_file.read().decode("utf-8")

        # Parse CSV
        import csv
        import io

        csv_reader = csv.DictReader(io.StringIO(file_content))
        required_fields = ["keyword", "category"]

        # Validate CSV structure
        if not all(field in csv_reader.fieldnames for field in required_fields):
            flash(
                f"CSV must contain at least these columns: {', '.join(required_fields)}"
            )
            return redirect(url_for("manage_category_mappings"))

        # Process rows
        imported_count = 0
        skipped_count = 0

        for row in csv_reader:
            try:
                # Get required fields
                keyword = row["keyword"].strip()
                category_name = row["category"].strip()

                # Get optional fields with defaults
                is_regex = str(row.get("is_regex", "false")).lower() in [
                    "true",
                    "1",
                    "yes",
                    "y",
                ]
                priority = int(row.get("priority", 0))

                # Skip empty keywords
                if not keyword or not category_name:
                    skipped_count += 1
                    continue

                # Check if mapping already exists
                existing = CategoryMapping.query.filter_by(
                    user_id=current_user.id, keyword=keyword
                ).first()

                if existing:
                    # Skip duplicate mappings
                    skipped_count += 1
                    continue

                # Find the category by name (case-insensitive search)
                # First try to find exact match
                category = Category.query.filter(
                    Category.user_id == current_user.id,
                    func.lower(Category.name) == func.lower(category_name),
                ).first()

                # If not found, try subcategories
                if not category:
                    category = Category.query.filter(
                        Category.user_id == current_user.id,
                        Category.parent_id.isnot(None),
                        func.lower(Category.name) == func.lower(category_name),
                    ).first()

                # If still not found, try partial matches
                if not category:
                    category = Category.query.filter(
                        Category.user_id == current_user.id,
                        func.lower(Category.name).like(
                            f"%{category_name.lower()}%"
                        ),
                    ).first()

                # If no category found, use "Other"
                if not category:
                    category = Category.query.filter_by(
                        name="Other", user_id=current_user.id, is_system=True
                    ).first()

                # If we still can't find a category, skip this mapping
                if not category:
                    skipped_count += 1
                    continue

                # Create mapping
                new_mapping = CategoryMapping(
                    user_id=current_user.id,
                    keyword=keyword,
                    category_id=category.id,
                    is_regex=is_regex,
                    priority=priority,
                    match_count=0,
                    active=True,
                )

                db.session.add(new_mapping)
                imported_count += 1

            except Exception:
                current_app.logger.exception("Error importing mapping row")
                skipped_count += 1
                continue

        # Commit all successfully parsed mappings
        if imported_count > 0:
            db.session.commit()

        flash(
            f"Successfully imported {imported_count} mappings. Skipped {skipped_count} rows."
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error importing category mappings")
        flash(f"Error importing mappings: {e!s}")

    return redirect(url_for("manage_category_mappings"))


@category_bp.route("/category_mappings/export", methods=["GET"])
@login_required_dev
def export_category_mappings():
    """Export category mappings to a CSV file."""
    try:
        # Get all active mappings for the current user
        mappings = CategoryMapping.query.filter_by(
            user_id=current_user.id, active=True
        ).all()

        if not mappings:
            flash("No active mappings to export.")
            return redirect(url_for("manage_category_mappings"))

        # Create CSV in memory
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header row
        writer.writerow(["keyword", "category", "is_regex", "priority"])

        # Write data rows
        for mapping in mappings:
            category_name = (
                mapping.category.name if mapping.category else "Unknown"
            )
            writer.writerow(
                [
                    mapping.keyword,
                    category_name,
                    "true" if mapping.is_regex else "false",
                    mapping.priority,
                ]
            )

        # Prepare for download
        output.seek(0)

        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"category_mappings_{timestamp}.csv"

        # Send file
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        current_app.logger.exception("Error exporting category mappings")
        flash(f"Error exporting mappings: {e!s}")
        return redirect(url_for("manage_category_mappings"))


def update_category_mappings(transaction_id, category_id, learn=False):
    """Update category mappings based on a manually categorized transaction.

    If learn=True, create a new mapping based on this categorization
    """
    transaction = Expense.query.get(transaction_id)
    if not transaction or not category_id:
        return False

    if learn:
        # Extract a good keyword from the description
        keyword = extract_keywords(transaction.description)

        # Check if a similar mapping already exists
        existing = CategoryMapping.query.filter_by(
            user_id=transaction.user_id, keyword=keyword, active=True
        ).first()

        if existing:
            # Update the existing mapping
            existing.category_id = category_id
            existing.match_count += 1
            db.session.commit()
        else:
            # Create a new mapping
            new_mapping = CategoryMapping(
                user_id=transaction.user_id,
                keyword=keyword,
                category_id=category_id,
                match_count=1,
            )
            db.session.add(new_mapping)
            db.session.commit()

        return True

    return False


def extract_keywords(description):
    """Extract meaningful keywords from a transaction description.

    :return: the most significant word or phrase
    """
    if not description:
        return ""

    # Clean up description
    clean_desc = description.strip().lower()

    # Split into words
    words = clean_desc.split()

    # Remove common words that aren't useful for categorization
    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "on",
        "in",
        "with",
        "for",
        "to",
        "from",
        "by",
        "at",
        "of",
    }
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]

    if not filtered_words:
        # If no good words remain, use the longest word from the original
        return max(words, key=len) if words else ""

    # Use the longest remaining word as the keyword
    # This is a simple approach - could be improved with more sophisticated NLP
    return max(filtered_words, key=len)
