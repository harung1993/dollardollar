r"""29a41de6a866d56c36aba5159f45257c"""
#!/usr/bin/env python
"""
This script updates currency exchange rates in the application database.
"""

import os
import sys
from datetime import datetime
import requests

# Add app directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import app with its context
from app import app, db, Currency

def update_currency_rates():
    """
    Update currency exchange rates using a public API
    More robust rate updating mechanism
    """
    try:
        # Find the base currency
        base_currency = Currency.query.filter_by(is_base=True).first()
        
        if not base_currency:
            logger.error("No base currency found. Cannot update rates.")
            return -1
        
        base_code = base_currency.code
        logger.info(f"Updating rates with base currency: {base_code}")
        
        # Use Frankfurter API
        api_url = f'https://api.frankfurter.app/latest?from={base_code}'
        
        try:
            response = requests.get(api_url, timeout=10)
        except requests.RequestException as req_err:
            logger.error(f"API request failed: {req_err}")
            return -1
        
        if response.status_code != 200:
            logger.error(f"API returned status code {response.status_code}")
            return -1
        
        try:
            data = response.json()
        except ValueError:
            logger.error("Failed to parse API response")
            return -1
        
        rates = data.get('rates', {})
        
        # Always set base currency rate to 1.0
        base_currency.rate_to_base = 1.0
        
        # Get all currencies except base
        currencies = Currency.query.filter(Currency.code != base_code).all()
        updated_count = 0
        
        # Update rates
        for currency in currencies:
            if currency.code in rates:
                try:
                    # Convert the rate to base currency rate
                    currency.rate_to_base = 1 / rates[currency.code]
                    currency.last_updated = datetime.utcnow()
                    updated_count += 1
                    
                    logger.info(f"Updated {currency.code}: rate = {currency.rate_to_base}")
                except (TypeError, ZeroDivisionError) as rate_err:
                    logger.error(f"Error calculating rate for {currency.code}: {rate_err}")
        
        # Commit changes
        db.session.commit()
        
        logger.info(f"Successfully updated {updated_count} currency rates")
        return updated_count
    
    except Exception as e:
        logger.error(f"Unexpected error in currency rate update: {str(e)}")
        return -1