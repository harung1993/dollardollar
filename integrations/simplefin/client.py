# simplefin_client.py
import os
import requests
import json
import base64
import time
from datetime import datetime, timedelta
from flask import session, url_for, redirect, flash
from urllib.parse import urlencode

class SimpleFin:
    """
    A client for interacting with the SimpleFin API
    Handles setup token flow, account access, and transaction syncing
    """
    def __init__(self, app):
        self.app = app
        # No API URL needed for direct bridge URL approach
        self.setup_token_url = app.config.get('SIMPLEFIN_SETUP_TOKEN_URL', 'https://beta-bridge.simplefin.org/setup-token')
    
    def get_setup_token_instructions(self):
        """Return the URL where users can get their setup token"""
        return self.setup_token_url
    
    def decode_setup_token(self, setup_token):
        """Decode a base64 setup token to get the claim URL"""
        try:
            # Try to decode as base64
            decoded = base64.b64decode(setup_token).decode('utf-8')
            self.app.logger.info(f"Decoded claim URL: {decoded}")
            return decoded
        except Exception as e:
            self.app.logger.error(f"Error decoding token: {str(e)}")
            # If not base64, assume it's already a URL
            return setup_token

    def claim_access_url(self, claim_url):
        """Make a POST request to the claim URL to get an access URL"""
        self.app.logger.info(f"Claiming access URL from: {claim_url}")
        
        try:
            response = requests.post(claim_url)
            
            if response.status_code == 200:
                access_url = response.text.strip()
                self.app.logger.info(f"Access URL received")
                return access_url
            else:
                self.app.logger.error(f"Error claiming access URL: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.app.logger.error(f"Error claiming access URL: {str(e)}")
            return None

    def parse_access_url(self, access_url):
        """Parse the access URL to extract credentials and base URL"""
        try:
            scheme, rest = access_url.split('//', 1)
            auth, rest = rest.split('@', 1)
            username, password = auth.split(':', 1)
            base_url = scheme + '//' + rest
            
            return {
                'username': username,
                'password': password,
                'base_url': base_url,
                'full_url': access_url
            }
        except Exception as e:
            self.app.logger.error(f"Error parsing access URL: {str(e)}")
            return None

    def get_accounts_with_transactions(self, access_url, days_back=30):
        """Get accounts with transactions from the given days back"""
        # Calculate start date for X days ago
        start_date = datetime.now() - timedelta(days=days_back)
        start_timestamp = int(start_date.timestamp())
        
        try:
            # Parse the access URL to get auth credentials
            parsed = self.parse_access_url(access_url)
            if not parsed:
                return None
                
            # Build the URL with start-date parameter
            url = f"{parsed['base_url']}/accounts?start-date={start_timestamp}"
            
            self.app.logger.info(f"Fetching accounts and transactions from: {url}")
            
            response = requests.get(url, auth=(parsed['username'], parsed['password']))
            if response.status_code == 200:
                return response.json()
            else:
                self.app.logger.error(f"Error fetching accounts: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.app.logger.error(f"Error fetching accounts: {str(e)}")
            return None

    def process_raw_accounts(self, raw_data):
        """Process raw SimpleFin accounts data into a standardized format"""
        if not raw_data or 'accounts' not in raw_data:
            return []
            
        processed_accounts = []
        
        for account in raw_data['accounts']:
            # Convert balance date to datetime if available
            balance_date = None
            if 'balance-date' in account and account['balance-date']:
                try:
                    balance_date = datetime.fromtimestamp(account['balance-date'])
                except:
                    pass
            
            # Determine account type
            account_type = 'checking'  # Default
            if 'type' in account:
                account_type_lower = account['type'].lower() if account['type'] else ''
                if any(term in account_type_lower for term in ['credit', 'card', 'visa', 'mastercard']):
                    account_type = 'credit'
                elif any(term in account_type_lower for term in ['saving', 'savings']):
                    account_type = 'savings'
                elif any(term in account_type_lower for term in ['investment', 'brokerage', 'retire', '401k', 'ira']):
                    account_type = 'investment'
                elif any(term in account_type_lower for term in ['loan', 'mortgage', 'debt', 'lend']):
                    account_type = 'loan'
                        
            # Get organization/institution info
            institution = "Unknown Institution"
            if 'org' in account and account['org'] and 'name' in account['org']:
                institution = account['org']['name']
            
            # Create standardized account object
            processed_account = {
                'id': account.get('id'),
                'name': account.get('name', 'Unnamed Account'),
                'type': account_type,
                'institution': institution,
                'balance': float(account.get('balance', 0)),
                'currency_code': account.get('currency', 'USD'),
                'balance_date': balance_date,
                'transactions': self.process_raw_transactions(account.get('transactions', []))
            }
            
            processed_accounts.append(processed_account)
            
        return processed_accounts

    def process_raw_transactions(self, raw_transactions):
        """Process raw SimpleFin transactions into a standardized format"""
        processed_transactions = []
        
        for trans in raw_transactions:
            # Skip transactions without required fields
            if 'id' not in trans or 'posted' not in trans or 'amount' not in trans:
                continue
                
            # Convert posted date to datetime
            posted_date = None
            if trans['posted']:
                try:
                    posted_date = datetime.fromtimestamp(trans['posted'])
                except:
                    posted_date = datetime.now()  # Fallback
            
            # Determine transaction type based on amount sign
            amount = float(trans.get('amount', 0))
            raw_amount = amount  # Keep the original amount with sign for transfer detection
            if amount < 0:
                transaction_type = 'expense'
                amount = abs(amount)  # Store as positive
            elif amount > 0:
                transaction_type = 'income'
            else:
                continue  # Skip zero-amount transactions
            
            # Extract category if available
            category_name = None
            if 'category' in trans:
                category_name = trans['category']
            
            # Create standardized transaction object
            processed_transaction = {
                'external_id': trans.get('id'),
                'date': posted_date,
                'description': trans.get('description', 'Unknown Transaction'),
                'amount': amount,
                'raw_amount': raw_amount,  # Keep the original amount with sign
                'transaction_type': transaction_type,
                'category_name': category_name,
                'payee': trans.get('payee'),
                'memo': trans.get('memo'),
                'pending': trans.get('pending', False)
            }
            
            processed_transactions.append(processed_transaction)
            
        return processed_transactions

    def test_access_url(self, access_url):
        """Test if an access URL is valid by making a simple request"""
        try:
            # Parse the access URL to get auth credentials
            parsed = self.parse_access_url(access_url)
            if not parsed:
                return False
                
            # Make a simple request to fetch accounts (without transactions)
            url = f"{parsed['base_url']}/accounts"
            
            response = requests.get(url, auth=(parsed['username'], parsed['password']))
            return response.status_code == 200
            
        except Exception as e:
            self.app.logger.error(f"Error testing access URL: {str(e)}")
            return False

    def create_transactions_from_account(self, account_data, db_account, user_id, 
                                        detect_transfer_func=None, auto_categorize_func=None, 
                                        get_category_id_func=None):
        """
        Create Expense model instances from processed account data, applying transfer detection
        and auto-categorization.
        
        Parameters:
        - account_data: Processed account data from process_raw_accounts()
        - db_account: Database Account model instance
        - user_id: User ID of the account owner
        - detect_transfer_func: Function to detect internal transfers
        - auto_categorize_func: Function for auto-categorization
        - get_category_id_func: Function to get or create a category by name
        
        Returns:
        - Tuple of (list of transactions, imported_count)
        """
        transactions_to_add = []
        imported_count = 0
        
        # Process each transaction in the account data
        for trans in account_data.get('transactions', []):
            try:
                # Create model instance for each transaction
                transaction, is_transfer = self.create_transaction_instance(
                    trans,
                    db_account,
                    user_id,
                    detect_transfer_func,
                    auto_categorize_func,
                    get_category_id_func
                )
                
                if transaction:
                    transactions_to_add.append(transaction)
                    imported_count += 1
            except Exception as e:
                self.app.logger.error(f"Error creating transaction: {str(e)}")
                # Continue with next transaction
                continue
                
        return transactions_to_add, imported_count

    def create_transaction_instance(self, trans_data, db_account, user_id, 
                                  detect_transfer_func=None, auto_categorize_func=None,
                                  get_category_id_func=None):
        """
        Create a single transaction model instance with transfer detection and categorization.
        
        Parameters:
        - trans_data: Dictionary with transaction data
        - db_account: Database Account model instance
        - user_id: User ID of the account owner
        - detect_transfer_func: Function to detect internal transfers
        - auto_categorize_func: Function for auto-categorization
        - get_category_id_func: Function to get or create a category by name
        
        Returns:
        - Tuple of (Transaction model instance, is_transfer boolean)
        """
        from app import Expense  # Import here to avoid circular imports
        
        # Skip transactions without required fields
        if not all(key in trans_data for key in ['external_id', 'date', 'description', 'amount']):
            return None, False
            
        # Check for existing transaction to avoid duplicates
        # Note: This requires a database connection, so this check is better done outside
        # But we'll include the logic here for completeness
        try:
            # This import and check might need to be done differently depending on your app structure
            # from app import db, Expense
            # existing = Expense.query.filter_by(
            #     user_id=user_id,
            #     external_id=trans_data.get('external_id'),
            #     import_source='simplefin'
            # ).first()
            # if existing:
            #     return None, False
            pass
        except Exception as e:
            self.app.logger.warning(f"Could not check for existing transaction: {str(e)}")
        
        # Detect internal transfer if function provided
        is_transfer = False
        source_account_id = db_account.id if db_account else None
        destination_account_id = None
        
        if detect_transfer_func and source_account_id:
            try:
                is_transfer, source_account_id, destination_account_id = detect_transfer_func(
                    trans_data.get('description', ''),
                    trans_data.get('raw_amount', trans_data.get('amount', 0)),  # Use raw amount with sign
                    source_account_id
                )
                
                if is_transfer:
                    # Override transaction type for transfers
                    transaction_type = 'transfer'
                else:
                    # Not a transfer, use the type from data
                    transaction_type = trans_data.get('transaction_type', 'expense')
            except Exception as e:
                self.app.logger.error(f"Error in transfer detection: {str(e)}")
                is_transfer = False
                transaction_type = trans_data.get('transaction_type', 'expense')
        else:
            # No transfer detection, use the type from data
            transaction_type = trans_data.get('transaction_type', 'expense')
        
        # Create the transaction instance
        transaction = Expense(
            description=trans_data.get('description', 'Unknown Transaction'),
            amount=trans_data.get('amount', 0),
            date=trans_data.get('date'),
            card_used=db_account.name if db_account else "Unknown Account",
            transaction_type=transaction_type,
            split_method='equal',  # Default for imports
            paid_by=user_id,
            user_id=user_id,
            account_id=source_account_id,
            destination_account_id=destination_account_id,
            external_id=trans_data.get('external_id'),
            import_source='simplefin',
            split_with=None  # Personal expense by default
        )
        
        # Apply auto-categorization for non-transfers
        if transaction_type != 'transfer':
            category_id = None
            
            # Try auto-categorization first if function provided
            if auto_categorize_func:
                try:
                    category_id = auto_categorize_func(
                        trans_data.get('description', ''),
                        user_id
                    )
                except Exception as e:
                    self.app.logger.error(f"Error in auto-categorization: {str(e)}")
            
            # If auto-categorization didn't find a match but SimpleFin provided a category name,
            # try to find or create a matching category
            if not category_id and trans_data.get('category_name') and get_category_id_func:
                try:
                    category_id = get_category_id_func(
                        trans_data.get('category_name'),
                        trans_data.get('description'),
                        user_id
                    )
                except Exception as e:
                    self.app.logger.error(f"Error in category lookup: {str(e)}")
            
            # Set the category if we found one
            if category_id:
                transaction.category_id = category_id
        
        return transaction, is_transfer