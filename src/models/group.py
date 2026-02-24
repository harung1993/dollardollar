"""
Group and Settlement models
"""

from datetime import datetime
import json
from src.extensions import db
from src.models.associations import group_users

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    default_payer = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=True)
    default_split_method = db.Column(db.String(20), default='equal')  # 'equal', 'percentage', 'custom'
    default_split_values = db.Column(db.JSON, nullable=True)  # For PostgreSQL
    auto_include_all = db.Column(db.Boolean, default=True)
    
    # Relationships
    members = db.relationship('User', secondary=group_users, lazy='subquery',
        backref=db.backref('groups', lazy=True))
    
    # Helper method to handle different storage types (JSON vs TEXT)
    def get_split_values(self):
        """Get split values as a dictionary, handling different DB storage types"""
        if self.default_split_values is None:
            return {}
        
        if isinstance(self.default_split_values, dict):
            # Already a dict (PostgreSQL JSON type)
            return self.default_split_values
            
        # Otherwise, parse from text (SQLite)
        try:
            return json.loads(self.default_split_values)
        except:
            return {}


class Settlement(db.Model):
    __tablename__ = 'settlements'
    id = db.Column(db.Integer, primary_key=True)
    payer_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(200), nullable=True, default="Settlement")
    
    # Relationships
    payer = db.relationship('User', foreign_keys=[payer_id], backref=db.backref('settlements_paid', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('settlements_received', lazy=True))
