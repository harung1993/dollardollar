"""
Currency Service
Business logic for currency management and exchange rates
"""

import requests
from datetime import datetime
from src.extensions import db
from src.models.currency import Currency

class CurrencyService:
    """Service class for currency operations"""
    
    def __init__(self):
        pass
    
    def get_all_currencies(self):
        """Get all currencies"""
        return Currency.query.all()
    
    def get_currency(self, code):
        """Get a specific currency by code"""
        return Currency.query.filter_by(code=code).first()
    
    def get_base_currency(self):
        """Get the base currency"""
        return Currency.query.filter_by(is_base=True).first()
    
    def add_currency(self, code, name, symbol, rate_to_base=1.0, is_base=False):
        """
        Add a new currency
        Returns (success, message, currency)
        """
        # Validate currency code format
        code = code.upper()
        if not code or len(code) != 3 or not code.isalpha():
            return False, 'Invalid currency code. Please use 3-letter ISO currency code (e.g., USD, EUR, GBP)', None
        
        # Check if currency already exists
        existing = self.get_currency(code)
        if existing:
            return False, f'Currency {code} already exists', None
        
        # If setting as base, update all existing base currencies
        if is_base:
            for currency in Currency.query.filter_by(is_base=True).all():
                currency.is_base = False
        
        # Create new currency
        currency = Currency(
            code=code,
            name=name,
            symbol=symbol,
            rate_to_base=rate_to_base,
            is_base=is_base
        )
        db.session.add(currency)
        
        try:
            db.session.commit()
            return True, f'Currency {code} added successfully', currency
        except Exception as e:
            db.session.rollback()
            return False, f'Error adding currency: {str(e)}', None
    
    def update_currency(self, code, name=None, symbol=None, rate_to_base=None, is_base=None):
        """
        Update an existing currency
        Returns (success, message, currency)
        """
        currency = self.get_currency(code)
        if not currency:
            return False, f'Currency {code} not found', None
        
        # Update fields if provided
        if name is not None:
            currency.name = name
        if symbol is not None:
            currency.symbol = symbol
        if rate_to_base is not None:
            currency.rate_to_base = rate_to_base
        
        # Handle base currency change
        if is_base is not None:
            if is_base and not currency.is_base:
                # Setting as base, unset all others
                for curr in Currency.query.filter_by(is_base=True).all():
                    curr.is_base = False
            currency.is_base = is_base
        
        currency.last_updated = datetime.utcnow()
        
        try:
            db.session.commit()
            return True, f'Currency {code} updated successfully', currency
        except Exception as e:
            db.session.rollback()
            return False, f'Error updating currency: {str(e)}', None
    
    def delete_currency(self, code):
        """
        Delete a currency
        Returns (success, message)
        """
        currency = self.get_currency(code)
        if not currency:
            return False, f'Currency {code} not found'
        
        # Prevent deleting the base currency
        if currency.is_base:
            return False, 'Cannot delete the base currency. Set another currency as base first.'
        
        try:
            db.session.delete(currency)
            db.session.commit()
            return True, f'Currency {code} deleted successfully'
        except Exception as e:
            db.session.rollback()
            return False, f'Error deleting currency: {str(e)}'
    
    def set_base_currency(self, code):
        """
        Set a currency as the base currency
        Returns (success, message)
        """
        new_base_currency = self.get_currency(code)
        if not new_base_currency:
            return False, f'Currency {code} not found'
        
        try:
            # Unset current base currency
            current_base_currency = self.get_base_currency()
            if current_base_currency:
                current_base_currency.is_base = False
            
            # Set new base currency
            new_base_currency.is_base = True
            new_base_currency.rate_to_base = 1.0
            
            # Update rates for other currencies
            self.update_exchange_rates()
            
            db.session.commit()
            return True, f'Base currency successfully changed to {code}'
        except Exception as e:
            db.session.rollback()
            return False, f'Error changing base currency: {str(e)}'
    
    def update_exchange_rates(self):
        """
        Update currency exchange rates using a public API
        Returns the number of currencies updated or -1 on error
        """
        try:
            # Get the base currency
            base_currency = self.get_base_currency()
            if not base_currency:
                return -1
            
            base_code = base_currency.code
            
            # Use Frankfurter API (free, no API key required)
            response = requests.get(f'https://api.frankfurter.app/latest?from={base_code}')
            
            if response.status_code != 200:
                return -1
            
            data = response.json()
            rates = data.get('rates', {})
            
            # Get all currencies except base
            currencies = Currency.query.filter(Currency.code != base_code).all()
            updated_count = 0
            
            # Update rates
            for currency in currencies:
                if currency.code in rates:
                    currency.rate_to_base = 1 / rates[currency.code]  # Convert to base currency rate
                    currency.last_updated = datetime.utcnow()
                    updated_count += 1
            
            # Commit changes
            db.session.commit()
            return updated_count
            
        except Exception as e:
            return -1
