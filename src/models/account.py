"""
Account and SimpleFin models
"""

from datetime import datetime
from src.extensions import db

class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # checking, savings, credit, etc.
    institution = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id', name='fk_account_user'), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    currency_code = db.Column(db.String(3), db.ForeignKey('currencies.code', name='fk_account_currency'), nullable=True)
    last_sync = db.Column(db.DateTime, nullable=True)
    import_source = db.Column(db.String(50), nullable=True)
    external_id = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('accounts', lazy=True))
    currency = db.relationship('Currency', backref=db.backref('accounts', lazy=True))
    
    def __repr__(self):
        return f"<Account {self.name} ({self.type})>"


class SimpleFin(db.Model):
    """
    Stores SimpleFin connection settings for a user
    """
    __tablename__ = 'SimpleFin'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False, unique=True)
    access_url = db.Column(db.Text, nullable=False)  # Encoded/encrypted access URL
    last_sync = db.Column(db.DateTime, nullable=True)
    enabled = db.Column(db.Boolean, default=True)
    sync_frequency = db.Column(db.String(20), default='daily')  # 'daily', 'weekly', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    temp_accounts = db.Column(db.Text, nullable=True)
    
    # Relationship with User
    user = db.relationship('User', backref=db.backref('SimpleFin', uselist=False, lazy=True))
    
    def __repr__(self):
        return f"<SimpleFin settings for user {self.user_id}>"
