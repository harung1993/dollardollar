"""
Currency conversion utilities
"""

from src.models.currency import Currency

def get_base_currency():
    """Get the base currency"""
    return Currency.query.filter_by(is_base=True).first()

def convert_currency(amount, from_code, to_code):
    """Convert an amount from one currency to another"""
    if from_code == to_code:
        return amount
    
    from_currency = Currency.query.filter_by(code=from_code).first()
    to_currency = Currency.query.filter_by(code=to_code).first()
    
    if not from_currency or not to_currency:
        return amount  # Return original if either currency not found
    
    # Get base currency for reference
    base_currency = Currency.query.filter_by(is_base=True).first()
    if not base_currency:
        return amount  # Cannot convert without a base currency
    
    # First convert amount to base currency
    if from_code == base_currency.code:
        # Amount is already in base currency
        amount_in_base = amount
    else:
        # Convert from source currency to base currency
        amount_in_base = amount * from_currency.rate_to_base
    
    # Then convert from base currency to target currency
    if to_code == base_currency.code:
        # Target is base currency, so we're done
        return amount_in_base
    else:
        # Convert from base currency to target currency
        return amount_in_base / to_currency.rate_to_base
