"""Marshmallow schemas for serialization"""
from marshmallow import Schema, fields, validate, post_load


class UserSchema(Schema):
    """User serialization schema"""
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    default_currency_code = fields.Str()
    created_at = fields.DateTime(dump_only=True)


class TransactionSchema(Schema):
    """Transaction serialization schema"""
    id = fields.Int(dump_only=True)
    description = fields.Str(required=True)
    amount = fields.Float(required=True)
    date = fields.DateTime(required=True)
    currency_code = fields.Str()
    card_used = fields.Str()
    split_method = fields.Str()
    split_with = fields.Str()
    paid_by = fields.Int()
    user_id = fields.Int(dump_only=True)
    category_id = fields.Int(allow_none=True)
    account_id = fields.Int(allow_none=True)
    recurring_id = fields.Int(allow_none=True)
    transaction_type = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)

    # Nested relationships
    category = fields.Nested('CategorySchema', dump_only=True)
    account = fields.Nested('AccountSchema', dump_only=True)
    splits = fields.Method('get_splits', dump_only=True)

    def get_splits(self, obj):
        """Calculate and return split information"""
        return obj.calculate_splits() if hasattr(obj, 'calculate_splits') else None


class CategorySchema(Schema):
    """Category serialization schema"""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    icon = fields.Str()
    parent_id = fields.Int(allow_none=True)
    user_id = fields.Int(dump_only=True)

    # Nested subcategories
    subcategories = fields.Nested('self', many=True, dump_only=True)


class AccountSchema(Schema):
    """Account serialization schema"""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    account_type = fields.Str(required=True)
    balance = fields.Float()
    currency_code = fields.Str()
    institution = fields.Str()
    account_number = fields.Str()
    is_active = fields.Bool()
    user_id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

    # Calculated balance
    current_balance = fields.Method('get_current_balance', dump_only=True)

    def get_current_balance(self, obj):
        """Get calculated balance from transactions"""
        return obj.get_balance() if hasattr(obj, 'get_balance') else obj.balance


class BudgetSchema(Schema):
    """Budget serialization schema"""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    amount = fields.Float(required=True)
    period = fields.Str(required=True, validate=validate.OneOf(['monthly', 'weekly', 'yearly']))
    category_id = fields.Int(allow_none=True)
    user_id = fields.Int(dump_only=True)
    start_date = fields.Date()
    end_date = fields.Date(allow_none=True)
    is_active = fields.Bool()
    created_at = fields.DateTime(dump_only=True)

    # Nested category
    category = fields.Nested(CategorySchema, dump_only=True)

    # Progress calculation
    spent = fields.Method('get_spent', dump_only=True)
    remaining = fields.Method('get_remaining', dump_only=True)
    percentage = fields.Method('get_percentage', dump_only=True)

    def get_spent(self, obj):
        """Calculate spent amount"""
        return obj.get_spent() if hasattr(obj, 'get_spent') else 0

    def get_remaining(self, obj):
        """Calculate remaining amount"""
        return obj.get_remaining() if hasattr(obj, 'get_remaining') else obj.amount

    def get_percentage(self, obj):
        """Calculate percentage used"""
        return obj.get_percentage() if hasattr(obj, 'get_percentage') else 0


class GroupSchema(Schema):
    """Group serialization schema"""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    description = fields.Str()
    created_by = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

    # Members list
    members = fields.Nested(UserSchema, many=True, dump_only=True)
    member_count = fields.Method('get_member_count', dump_only=True)

    def get_member_count(self, obj):
        """Get number of members"""
        return len(obj.members) if hasattr(obj, 'members') else 0


class RecurringTransactionSchema(Schema):
    """Recurring transaction serialization schema"""
    id = fields.Int(dump_only=True)
    description = fields.Str(required=True)
    amount = fields.Float(required=True)
    frequency = fields.Str(required=True, validate=validate.OneOf(['daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly']))
    start_date = fields.Date(required=True)
    end_date = fields.Date(allow_none=True)
    next_date = fields.Date()
    active = fields.Bool()
    category_id = fields.Int(allow_none=True)
    account_id = fields.Int(allow_none=True)
    user_id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

    # Nested relationships
    category = fields.Nested(CategorySchema, dump_only=True)
    account = fields.Nested(AccountSchema, dump_only=True)


class CurrencySchema(Schema):
    """Currency serialization schema"""
    id = fields.Int(dump_only=True)
    code = fields.Str(required=True)
    name = fields.Str(required=True)
    symbol = fields.Str(required=True)
    exchange_rate = fields.Float()
    is_base = fields.Bool()
    last_updated = fields.DateTime()


class TagSchema(Schema):
    """Tag serialization schema"""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    color = fields.Str()
    user_id = fields.Int(dump_only=True)


# Initialize schema instances for use in API endpoints
user_schema = UserSchema()
users_schema = UserSchema(many=True)

transaction_schema = TransactionSchema()
transactions_schema = TransactionSchema(many=True)

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)

account_schema = AccountSchema()
accounts_schema = AccountSchema(many=True)

budget_schema = BudgetSchema()
budgets_schema = BudgetSchema(many=True)

group_schema = GroupSchema()
groups_schema = GroupSchema(many=True)

recurring_schema = RecurringTransactionSchema()
recurrings_schema = RecurringTransactionSchema(many=True)

currency_schema = CurrencySchema()
currencies_schema = CurrencySchema(many=True)

tag_schema = TagSchema()
tags_schema = TagSchema(many=True)
