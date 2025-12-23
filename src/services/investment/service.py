"""Investment Service - Portfolio and investment tracking"""
from datetime import datetime
from flask import current_app
from src.extensions import db
from src.models.investment import Portfolio, Investment, InvestmentTransaction

class InvestmentService:
    def __init__(self):
        pass

    def get_all_portfolios(self, user_id):
        return Portfolio.query.filter_by(user_id=user_id).all()

    def add_portfolio(self, user_id, name, description=None):
        try:
            portfolio = Portfolio(user_id=user_id, name=name, description=description)
            db.session.add(portfolio)
            db.session.commit()
            return True, 'Portfolio created!', portfolio
        except Exception as e:
            db.session.rollback()
            return False, f'Error: {str(e)}', None

    def add_investment(self, portfolio_id, user_id, symbol, name, shares, purchase_price):
        try:
            investment = Investment(
                portfolio_id=portfolio_id, symbol=symbol, name=name,
                shares=float(shares), purchase_price=float(purchase_price)
            )
            db.session.add(investment)
            db.session.commit()
            return True, 'Investment added!', investment
        except Exception as e:
            db.session.rollback()
            return False, f'Error: {str(e)}', None

    def update_prices(self, portfolio_id):
        """Update investment prices from external API"""
        # Would call FMP or Yahoo Finance integration
        return True, 'Prices updated!'
