"""
Transaction Service
Business logic for transaction (expense/income/transfer) management
"""

import json
from datetime import datetime
from flask import current_app
from sqlalchemy import or_
from src.extensions import db
from src.models.transaction import Expense, CategorySplit
from src.models.account import Account
from src.models.user import User
from src.models.group import Group
from src.models.currency import Currency
from src.models.category import Tag


class TransactionService:
    """Service class for transaction operations"""

    def __init__(self):
        pass

    # Transaction CRUD Methods

    def add_transaction(self, user_id, form_data):
        """
        Add a new transaction (expense/income/transfer) with complex split logic
        Returns (success, message, transaction_id)
        """
        try:
            # Get transaction type
            transaction_type = form_data.get('transaction_type', 'expense')

            # Parse date with error handling
            try:
                expense_date = datetime.strptime(form_data.get('date', ''), '%Y-%m-%d')
            except ValueError:
                expense_date = datetime.utcnow()

            # Parse amount with validation
            try:
                amount = float(form_data.get('amount', 0))
                if amount <= 0:
                    return False, 'Amount must be greater than zero', None
            except ValueError:
                return False, 'Invalid amount format', None

            # Get currency information
            currency_code = form_data.get('currency_code')
            if not currency_code:
                # Get user's default currency
                user = User.query.get(user_id)
                currency_code = user.default_currency_code if user else 'USD'

            # Get account information
            account_id = form_data.get('account_id')
            card_used = "No card"  # Default name

            if account_id:
                try:
                    account_id = int(account_id)
                    account = Account.query.get(account_id)
                    if account:
                        card_used = account.name
                except ValueError:
                    account_id = None

            # Process group and split information
            group_id = form_data.get('group_id')
            paid_by = form_data.get('paid_by', user_id)
            split_method = form_data.get('split_method', 'equal')
            split_with_ids = form_data.getlist('split_with') if hasattr(form_data, 'getlist') else form_data.get('split_with', [])
            is_personal_expense = form_data.get('personal_expense') == 'on'

            # Initialize split details
            split_with_str = None
            split_details_str = None

            # Process split information for expenses
            if transaction_type == 'expense' and not is_personal_expense:
                # Convert split_with_ids list to comma-separated string
                split_with_str = ','.join(split_with_ids) if split_with_ids else None

                # Handle split details
                if split_method == 'group_default' and group_id:
                    split_method, split_details_str = self._handle_group_default_split(
                        group_id, split_with_ids, paid_by, amount
                    )
                elif split_method != 'equal' and split_with_ids:
                    split_details_str = self._handle_custom_split(
                        form_data, split_method, split_with_ids, paid_by, amount, group_id
                    )
                else:
                    split_details_str = None

            # Get destination account for transfers
            destination_account_id = None
            if transaction_type == 'transfer':
                dest_id = form_data.get('destination_account_id')
                if dest_id:
                    try:
                        destination_account_id = int(dest_id)
                        # Validate source and destination are different
                        if destination_account_id == account_id:
                            return False, 'Source and destination accounts cannot be the same', None
                    except ValueError:
                        destination_account_id = None

            # Process category
            category_id = form_data.get('category_id')
            if not category_id or category_id.strip() == '' or category_id == 'null':
                category_id = None
            else:
                try:
                    category_id = int(category_id)
                except ValueError:
                    category_id = None

            # Check for category splits
            has_category_splits, category_splits = self._parse_category_splits(
                form_data, amount
            )
            if has_category_splits:
                category_id = None  # Clear main category when using splits

            # Create the transaction record
            expense = Expense(
                description=form_data.get('description', ''),
                amount=amount,
                original_amount=amount,
                currency_code=currency_code,
                date=expense_date,
                card_used=card_used,
                split_method=split_method,
                split_value=0,
                split_details=split_details_str,
                paid_by=paid_by,
                user_id=user_id,
                category_id=category_id,
                group_id=group_id if group_id else None,
                split_with=split_with_str,
                transaction_type=transaction_type,
                account_id=account_id,
                destination_account_id=destination_account_id,
                has_category_splits=has_category_splits
            )

            db.session.add(expense)
            db.session.flush()  # Get ID without committing

            # Add category splits if provided
            if has_category_splits and category_splits:
                for split in category_splits:
                    if split.get('category_id') and float(split.get('amount', 0)) > 0:
                        category_split = CategorySplit(
                            expense_id=expense.id,
                            category_id=split['category_id'],
                            amount=float(split['amount'])
                        )
                        db.session.add(category_split)

            # Update account balances
            self._update_account_balances_on_add(
                account_id, destination_account_id, transaction_type, amount
            )

            # Commit all changes
            db.session.commit()

            return True, f'{transaction_type.capitalize()} added successfully', expense.id

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding transaction: {str(e)}", exc_info=True)
            return False, f'Error: {str(e)}', None

    def delete_transaction(self, transaction_id, user_id):
        """
        Delete a transaction and update account balances
        Returns (success, message)
        """
        try:
            # Find the transaction
            expense = Expense.query.get(transaction_id)
            if not expense:
                return False, 'Transaction not found'

            # Security check
            if expense.user_id != user_id:
                return False, 'Permission denied'

            # Get transaction data for account balance updates
            transaction_type = getattr(expense, 'transaction_type', 'expense')
            amount = expense.amount
            account_id = getattr(expense, 'account_id', None)
            destination_account_id = getattr(expense, 'destination_account_id', None)

            # Update account balances before deleting
            self._update_account_balances_on_delete(
                account_id, destination_account_id, transaction_type, amount
            )

            # Delete the transaction
            db.session.delete(expense)
            db.session.commit()

            return True, 'Transaction deleted successfully'

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting transaction {transaction_id}: {str(e)}")
            return False, f'Error: {str(e)}'

    def get_transaction(self, transaction_id, user_id):
        """
        Get transaction details for editing
        Returns (success, message, transaction_data)
        """
        try:
            # Find the transaction
            expense = Expense.query.get(transaction_id)
            if not expense:
                return False, 'Transaction not found', None

            # Security check: Only the creator or participants can view
            if expense.user_id != user_id and user_id not in (expense.split_with or ''):
                return False, 'You do not have permission to view this transaction', None

            # Format the transaction data
            split_with_ids = expense.split_with.split(',') if expense.split_with else []
            formatted_date = expense.date.strftime('%Y-%m-%d')
            tag_ids = [tag.id for tag in expense.tags]

            user = User.query.get(user_id)
            default_currency = user.default_currency_code if user else 'USD'

            transaction_data = {
                'id': expense.id,
                'description': expense.description,
                'amount': expense.amount,
                'date': formatted_date,
                'card_used': expense.card_used,
                'split_method': expense.split_method,
                'split_value': expense.split_value,
                'split_details': expense.split_details,
                'paid_by': expense.paid_by,
                'split_with': split_with_ids,
                'group_id': expense.group_id,
                'currency_code': expense.currency_code or default_currency,
                'tag_ids': tag_ids,
                'category_id': expense.category_id,
                'transaction_type': expense.transaction_type,
                'account_id': expense.account_id,
                'destination_account_id': expense.destination_account_id,
                'has_category_splits': expense.has_category_splits
            }

            return True, 'Success', transaction_data

        except Exception as e:
            current_app.logger.error(f"Error retrieving transaction {transaction_id}: {str(e)}")
            return False, f'Error: {str(e)}', None

    def update_transaction(self, transaction_id, user_id, form_data):
        """
        Update a transaction with complex split and account logic
        Returns (success, message)
        """
        try:
            # Verify transaction exists and belongs to current user
            expense = Expense.query.get(transaction_id)
            if not expense:
                return False, 'Transaction not found'

            if expense.user_id != user_id:
                return False, 'You do not have permission to edit this transaction'

            # Store original values for account balance adjustments
            original_amount = expense.amount
            original_transaction_type = expense.transaction_type or 'expense'
            original_account_id = expense.account_id
            original_destination_account_id = expense.destination_account_id

            # Update transaction type
            transaction_type = form_data.get('transaction_type', original_transaction_type)
            expense.transaction_type = transaction_type

            # Update basic fields
            expense.description = form_data.get('description', expense.description)

            try:
                expense.amount = float(form_data.get('amount', expense.amount))
            except (ValueError, TypeError):
                return False, 'Invalid amount provided'

            try:
                expense.date = datetime.strptime(form_data.get('date', ''), '%Y-%m-%d')
            except ValueError:
                pass  # Keep original date if new one is invalid

            # Handle category splits
            enable_category_split = form_data.get('enable_category_split') == 'on'
            expense.has_category_splits = enable_category_split

            if enable_category_split:
                expense.category_id = None
                CategorySplit.query.filter_by(expense_id=expense.id).delete()

                splits_data = form_data.get('category_splits_data', '[]')
                try:
                    splits = json.loads(splits_data)
                    for split in splits:
                        if not isinstance(split, dict):
                            continue

                        category_id = split.get('category_id')
                        amount = float(split.get('amount', 0))

                        if category_id and amount > 0:
                            cat_split = CategorySplit(
                                expense_id=expense.id,
                                category_id=category_id,
                                amount=amount
                            )
                            db.session.add(cat_split)
                except (json.JSONDecodeError, ValueError) as e:
                    return False, f'Invalid category split data: {str(e)}'
            else:
                CategorySplit.query.filter_by(expense_id=expense.id).delete()

                category_id = form_data.get('category_id')
                if category_id and category_id.strip() and category_id != 'null':
                    try:
                        expense.category_id = int(category_id)
                    except ValueError:
                        expense.category_id = None
                else:
                    expense.category_id = None

            # Update account
            account_id = form_data.get('account_id')
            if account_id and account_id != 'null':
                try:
                    expense.account_id = int(account_id)
                    account = Account.query.get(expense.account_id)
                    if account:
                        expense.card_used = account.name
                except ValueError:
                    pass

            # Handle destination account for transfers
            if transaction_type == 'transfer':
                destination_id = form_data.get('destination_account_id')
                if destination_id and destination_id != 'null':
                    try:
                        expense.destination_account_id = int(destination_id)
                    except ValueError:
                        pass
            else:
                expense.destination_account_id = None

            # Reverse original account effects
            self._update_account_balances_on_delete(
                original_account_id,
                original_destination_account_id,
                original_transaction_type,
                original_amount
            )

            # Apply new account effects
            self._update_account_balances_on_add(
                expense.account_id,
                expense.destination_account_id,
                expense.transaction_type,
                expense.amount
            )

            # Commit all changes
            db.session.commit()

            return True, 'Transaction updated successfully'

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating transaction: {str(e)}", exc_info=True)
            return False, f'Error: {str(e)}'

    # Transaction Listing Methods

    def get_all_transactions(self, user_id):
        """
        Get all transactions for a user (as creator or participant)
        Returns list of transactions with calculated splits
        """
        # Fetch all expenses where the user is either the creator or a split participant
        expenses = Expense.query.filter(
            or_(
                Expense.user_id == user_id,
                Expense.split_with.like(f'%{user_id}%')
            )
        ).order_by(Expense.date.desc()).all()

        # Pre-calculate all expense splits
        expense_splits = {}
        for expense in expenses:
            expense_splits[expense.id] = expense.calculate_splits()

        return expenses, expense_splits

    def calculate_user_totals(self, user_id, expenses, expense_splits):
        """
        Calculate totals for current year and month
        Returns (year_total, month_total)
        """
        now = datetime.now()
        current_year = now.year
        current_month = now.strftime('%Y-%m')

        year_total = 0
        month_total = 0

        for expense in expenses:
            splits = expense_splits[expense.id]

            # Calculate user's portion
            user_amount = 0
            if expense.paid_by == user_id:
                user_amount = splits['payer']['amount']
                for split in splits['splits']:
                    user_amount += split['amount']
            else:
                for split in splits['splits']:
                    if split['email'] == user_id:
                        user_amount = split['amount']
                        break

            # Add to year total
            if expense.date.year == current_year:
                year_total += user_amount

            # Add to month total
            if expense.date.strftime('%Y-%m') == current_month:
                month_total += user_amount

        return year_total, month_total

    # Helper Methods

    def _handle_group_default_split(self, group_id, split_with_ids, paid_by, amount):
        """Handle split method when using group defaults"""
        group = Group.query.get(group_id)
        if not group:
            return 'equal', None

        actual_split_method = group.default_split_method or 'equal'

        if actual_split_method != 'equal' and group.default_split_values:
            try:
                if isinstance(group.default_split_values, dict):
                    split_values = group.default_split_values
                else:
                    split_values = json.loads(group.default_split_values)

                split_details = {
                    "type": actual_split_method,
                    "values": split_values
                }
                return actual_split_method, json.dumps(split_details)
            except Exception as e:
                current_app.logger.warning(f"Error using group default splits: {str(e)}")
                return actual_split_method, None

        return actual_split_method, None

    def _handle_custom_split(self, form_data, split_method, split_with_ids, paid_by, amount, group_id):
        """Handle custom split details"""
        split_details_json = form_data.get('split_details')

        if split_details_json:
            try:
                split_details = json.loads(split_details_json)
                if not isinstance(split_details, dict) or 'type' not in split_details or 'values' not in split_details:
                    raise ValueError("Invalid split details structure")
                return json.dumps(split_details)
            except (json.JSONDecodeError, ValueError) as e:
                current_app.logger.warning(f"Invalid split details: {str(e)}")
                split_details = self._create_equal_split(split_with_ids, paid_by, amount, split_method)
                return json.dumps(split_details)

        # Try to use group default split values
        if group_id:
            group = Group.query.get(group_id)
            if group and group.default_split_method == split_method and group.default_split_values:
                if isinstance(group.default_split_values, dict):
                    split_values = group.default_split_values
                else:
                    split_values = json.loads(group.default_split_values)

                split_details = {
                    "type": split_method,
                    "values": split_values
                }
                return json.dumps(split_details)

        # Fallback to equal split
        split_details = self._create_equal_split(split_with_ids, paid_by, amount, split_method)
        return json.dumps(split_details)

    def _create_equal_split(self, split_with_ids, paid_by, amount, split_method):
        """Create a default equal split structure"""
        result = {
            "type": split_method,
            "values": {}
        }

        # Add all participants
        all_participants = list(split_with_ids)
        if paid_by not in all_participants:
            all_participants.append(paid_by)

        # Calculate equal shares
        if split_method == 'percentage':
            equal_share = 100.0 / len(all_participants) if all_participants else 100.0
            for participant_id in all_participants:
                result['values'][participant_id] = equal_share
        else:
            equal_share = amount / len(all_participants) if all_participants else amount
            for participant_id in all_participants:
                result['values'][participant_id] = equal_share

        return result

    def _parse_category_splits(self, form_data, total_amount):
        """Parse and validate category splits"""
        category_splits_data = form_data.get('category_splits_data')
        if not category_splits_data:
            return False, []

        try:
            category_splits = json.loads(category_splits_data)
            if isinstance(category_splits, list) and len(category_splits) > 0:
                # Validate total matches transaction amount
                total_split_amount = sum(float(split.get('amount', 0)) for split in category_splits)

                # Allow a small tolerance for rounding errors
                if abs(total_split_amount - total_amount) > 0.01:
                    current_app.logger.warning(
                        f"Category split total {total_split_amount} doesn't match amount {total_amount}"
                    )

                return True, category_splits
        except json.JSONDecodeError:
            current_app.logger.warning("Invalid category splits data")

        return False, []

    def _update_account_balances_on_add(self, account_id, destination_account_id, transaction_type, amount):
        """Update account balances when adding a transaction"""
        if not account_id:
            return

        account = Account.query.get(account_id)
        if not account:
            return

        if transaction_type == 'expense':
            account.balance -= amount
        elif transaction_type == 'income':
            account.balance += amount
        elif transaction_type == 'transfer' and destination_account_id:
            account.balance -= amount
            destination_account = Account.query.get(destination_account_id)
            if destination_account:
                destination_account.balance += amount

    def _update_account_balances_on_delete(self, account_id, destination_account_id, transaction_type, amount):
        """Reverse account balance changes when deleting a transaction"""
        if not account_id:
            return

        account = Account.query.get(account_id)
        if not account:
            return

        # Reverse the effect
        if transaction_type == 'expense':
            account.balance += amount
        elif transaction_type == 'income':
            account.balance -= amount
        elif transaction_type == 'transfer' and destination_account_id:
            account.balance += amount
            destination_account = Account.query.get(destination_account_id)
            if destination_account:
                destination_account.balance -= amount


# Tag Management (part of Transaction Service)

class TagService:
    """Service class for tag operations"""

    def __init__(self):
        pass

    def get_all_tags(self, user_id):
        """Get all tags for a user"""
        return Tag.query.filter_by(user_id=user_id).order_by(Tag.name).all()

    def add_tag(self, user_id, name):
        """
        Add a new tag
        Returns (success, message, tag)
        """
        if not name or not name.strip():
            return False, 'Tag name is required', None

        name = name.strip()

        # Check if tag already exists
        existing = Tag.query.filter_by(user_id=user_id, name=name).first()
        if existing:
            return False, 'A tag with this name already exists', None

        try:
            tag = Tag(user_id=user_id, name=name)
            db.session.add(tag)
            db.session.commit()
            return True, 'Tag added successfully', tag
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding tag: {str(e)}")
            return False, f'Error adding tag: {str(e)}', None

    def delete_tag(self, tag_id, user_id):
        """
        Delete a tag
        Returns (success, message)
        """
        tag = Tag.query.get(tag_id)
        if not tag:
            return False, 'Tag not found'

        if tag.user_id != user_id:
            return False, 'You don\'t have permission to delete this tag'

        try:
            db.session.delete(tag)
            db.session.commit()
            return True, 'Tag deleted successfully'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting tag: {str(e)}")
            return False, f'Error deleting tag: {str(e)}'
