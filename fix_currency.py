r"""29a41de6a866d56c36aba5159f45257c"""
from app import app, db, Currency

with app.app_context():
    # Find the base currency
    base_currency = Currency.query.filter_by(is_base=True).first()
    
    if base_currency:
        print(f"Current base currency: {base_currency.code}")
        
        # Check if code needs correction
        if base_currency.code != 'USD':
            old_code = base_currency.code
            base_currency.code = 'USD'
            db.session.commit()
            print(f"Updated base currency code from {old_code} to USD")
        else:
            print("Base currency code is already USD, no change needed")
    else:
        print("No base currency found. Creating USD as base currency.")
        usd = Currency(
            code='USD',
            name='US Dollar',
            symbol='$',
            rate_to_base=1.0,
            is_base=True
        )
        db.session.add(usd)
        db.session.commit()
        print("Created USD as base currency")