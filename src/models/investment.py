"""
Investment models
"""

from datetime import datetime
from src.extensions import db

class Portfolio(db.Model):
    __tablename__ = 'portfolios'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('portfolios', lazy=True))
    account = db.relationship('Account', backref=db.backref('portfolios', lazy=True))
    
    def calculate_total_value(self):
        return sum(investment.current_value for investment in self.investments)
    
    def calculate_total_cost(self):
        """Calculate the total cost basis of all investments in this portfolio"""
        return sum(investment.cost_basis for investment in self.investments)
    
    def calculate_gain_loss(self):
        """Calculate the total gain/loss in this portfolio"""
        return self.calculate_total_value() - self.calculate_total_cost()
    
    def calculate_gain_loss_percentage(self):
        """Calculate the percentage gain/loss of this portfolio"""
        cost = self.calculate_total_cost()
        if cost == 0:
            return 0
        return (self.calculate_gain_loss() / cost) * 100


class Investment(db.Model):
    __tablename__ = 'investments'
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100))
    shares = db.Column(db.Float, nullable=False, default=0)
    purchase_price = db.Column(db.Float, nullable=False, default=0)
    current_price = db.Column(db.Float, default=0)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_update = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    sector = db.Column(db.String(50))
    industry = db.Column(db.String(50))
    
    # Relationships
    portfolio = db.relationship('Portfolio', backref=db.backref('investments', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f"<Investment {self.symbol} ({self.shares} shares)>"
    
    @property
    def cost_basis(self):
        """Calculate the total cost of this investment"""
        return self.shares * self.purchase_price
    
    @property
    def current_value(self):
        """Calculate the current value of this investment"""
        return self.shares * self.current_price
    
    @property
    def gain_loss(self):
        """Calculate the gain or loss for this investment"""
        return self.current_value - self.cost_basis
    
    @property
    def gain_loss_percentage(self):
        """Calculate the percentage gain or loss"""
        if self.cost_basis == 0:
            return 0
        return (self.gain_loss / self.cost_basis) * 100


class InvestmentTransaction(db.Model):
    __tablename__ = 'investment_transactions'
    id = db.Column(db.Integer, primary_key=True)
    investment_id = db.Column(db.Integer, db.ForeignKey('investments.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # buy, sell, dividend, split
    shares = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    fees = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    
    # Relationship
    investment = db.relationship('Investment', backref=db.backref('transactions', lazy=True, cascade='all, delete-orphan'))
    
    @property
    def transaction_value(self):
        """Calculate the total value of this transaction"""
        return self.shares * self.price + self.fees
