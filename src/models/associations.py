"""
Association tables for many-to-many relationships
"""

from src.extensions import db

# Group-User Association Table
group_users = db.Table('group_users',
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id'), primary_key=True),
    db.Column('user_id', db.String(120), db.ForeignKey('users.id'), primary_key=True)
)

# Expense-Tag Association Table
expense_tags = db.Table('expense_tags',
    db.Column('expense_id', db.Integer, db.ForeignKey('expenses.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)
