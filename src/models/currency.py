"""
Currency model
"""

from datetime import datetime
from src.extensions import db

class Currency(db.Model):
    __tablename__ = 'currencies'
    code = db.Column(db.String(3), primary_key=True)  # ISO 4217 currency code (e.g., USD, EUR, GBP)
    name = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(5), nullable=False)
    rate_to_base = db.Column(db.Float, nullable=False, default=1.0)  # Exchange rate to base currency
    is_base = db.Column(db.Boolean, default=False)  # Whether this is the base currency
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"{self.code} ({self.symbol})"
