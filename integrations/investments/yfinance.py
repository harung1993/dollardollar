import os
import json
import time
import logging
from datetime import datetime, timedelta
import yfinance as yf

# Dictionary of common stock exchanges with their Yahoo Finance suffix and country
STOCK_EXCHANGES = {
    'US': {'suffix': '', 'name': 'United States (Default)', 'currency': 'USD'},
    'L': {'suffix': '.L', 'name': 'London Stock Exchange', 'currency': 'GBP'},
    'TO': {'suffix': '.TO', 'name': 'Toronto Stock Exchange', 'currency': 'CAD'},
    'PA': {'suffix': '.PA', 'name': 'Euronext Paris', 'currency': 'EUR'},
    'AS': {'suffix': '.AS', 'name': 'Euronext Amsterdam', 'currency': 'EUR'},
    'BR': {'suffix': '.BR', 'name': 'Euronext Brussels', 'currency': 'EUR'},
    'MI': {'suffix': '.MI', 'name': 'Borsa Italiana', 'currency': 'EUR'},
    'MC': {'suffix': '.MC', 'name': 'Bolsa de Madrid', 'currency': 'EUR'},
    'HK': {'suffix': '.HK', 'name': 'Hong Kong Stock Exchange', 'currency': 'HKD'},
    'AX': {'suffix': '.AX', 'name': 'Australian Securities Exchange', 'currency': 'AUD'},
    'SZ': {'suffix': '.SZ', 'name': 'Shenzhen Stock Exchange', 'currency': 'CNY'},
    'SS': {'suffix': '.SS', 'name': 'Shanghai Stock Exchange', 'currency': 'CNY'},
    'T': {'suffix': '.T', 'name': 'Tokyo Stock Exchange', 'currency': 'JPY'},
    'KS': {'suffix': '.KS', 'name': 'Korea Exchange', 'currency': 'KRW'},
    'KL': {'suffix': '.KL', 'name': 'Bursa Malaysia', 'currency': 'MYR'},
    'JK': {'suffix': '.JK', 'name': 'Indonesia Stock Exchange', 'currency': 'IDR'},
    'TA': {'suffix': '.TA', 'name': 'Tel Aviv Stock Exchange', 'currency': 'ILS'},
    'DE': {'suffix': '.DE', 'name': 'Deutsche Börse XETRA', 'currency': 'EUR'},
    'F': {'suffix': '.F', 'name': 'Frankfurt Stock Exchange', 'currency': 'EUR'},
    'SW': {'suffix': '.SW', 'name': 'SIX Swiss Exchange', 'currency': 'CHF'},
    'MX': {'suffix': '.MX', 'name': 'Mexican Stock Exchange', 'currency': 'MXN'},
    'SA': {'suffix': '.SA', 'name': 'B3 (Brazil)', 'currency': 'BRL'},
    'VI': {'suffix': '.VI', 'name': 'Vienna Stock Exchange', 'currency': 'EUR'},
    'CO': {'suffix': '.CO', 'name': 'Copenhagen Stock Exchange', 'currency': 'DKK'},
    'HE': {'suffix': '.HE', 'name': 'Helsinki Stock Exchange', 'currency': 'EUR'},
    'ST': {'suffix': '.ST', 'name': 'Stockholm Stock Exchange', 'currency': 'SEK'}
}

class YFinanceCache:
    """
    Cache wrapper for yfinance API calls to respect rate limits
    With support for international markets
    """
    def __init__(self, cache_dir='instance/yfcache', expire_seconds=86400):  # Default: 24 hours
        self.cache_dir = cache_dir
        self.expire_seconds = expire_seconds
        self.hits = 0
        self.misses = 0
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    def get_ticker_info(self, symbol, exchange=None):
        """
        Get basic info for a ticker with caching
        
        Args:
            symbol (str): The stock symbol (e.g., 'AAPL')
            exchange (str): Optional exchange code (e.g., 'L' for London)
        
        Returns:
            dict: Stock data or None if not found
        """
        # Format the symbol with exchange suffix if provided
        formatted_symbol = self._format_symbol(symbol, exchange)
        
        # Create cache key based on the full symbol
        cache_key = f"info_{formatted_symbol}"
        cached_data = self._get_from_cache(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            # Make a new API call
            ticker = yf.Ticker(formatted_symbol)
            info = ticker.info
            
            if not info or len(info) <= 1:
                self.logger.warning(f"No data found for {formatted_symbol}")
                return None
            
            # Get exchange info for currency
            exchange_info = STOCK_EXCHANGES.get(exchange or 'US', STOCK_EXCHANGES['US'])
            
            # Add most relevant properties to a clean dict
            data = {
                'symbol': symbol.upper(),  # Original symbol without suffix
                'formatted_symbol': formatted_symbol,  # Full symbol with exchange
                'exchange': exchange or 'US',
                'exchange_name': exchange_info['name'],
                'currency_code': info.get('currency', exchange_info['currency']),
                'name': info.get('shortName', info.get('longName', symbol)),
                'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'change': info.get('regularMarketChange', 0),
                'percent_change': info.get('regularMarketChangePercent', 0),
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'description': info.get('longBusinessSummary', ''),
                'website': info.get('website', ''),
                'country': info.get('country', '')
            }
            
            # Cache the result
            self._save_to_cache(cache_key, data)
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting info for {formatted_symbol}: {str(e)}")
            return None
    
    def get_ticker_history(self, symbol, exchange=None, period="1mo"):
        """
        Get price history for a ticker with caching
        
        Args:
            symbol (str): The stock symbol (e.g., 'AAPL')
            exchange (str): Optional exchange code (e.g., 'L' for London)
            period (str): Time period for history (1d, 1mo, 3mo, 1y, etc.)
        
        Returns:
            list: Price history data or None if not found
        """
        # Format the symbol with exchange suffix if provided
        formatted_symbol = self._format_symbol(symbol, exchange)
        
        cache_key = f"history_{formatted_symbol}_{period}"
        cached_data = self._get_from_cache(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            # Make a new API call
            ticker = yf.Ticker(formatted_symbol)
            history = ticker.history(period=period)
            
            # Convert to dict for JSON serialization
            history_data = []
            for index, row in history.iterrows():
                history_data.append({
                    'date': index.strftime('%Y-%m-%d'),
                    'open': row.get('Open', 0),
                    'high': row.get('High', 0),
                    'low': row.get('Low', 0),
                    'close': row.get('Close', 0),
                    'volume': row.get('Volume', 0)
                })
            
            # Cache the result
            self._save_to_cache(cache_key, history_data)
            return history_data
            
        except Exception as e:
            self.logger.error(f"Error getting history for {formatted_symbol}: {str(e)}")
            return None
    
    def _format_symbol(self, symbol, exchange=None):
        """Format symbol with exchange suffix if provided"""
        if not exchange or exchange.upper() == 'US':
            return symbol.upper()
        
        exchange_suffix = STOCK_EXCHANGES.get(exchange.upper(), {}).get('suffix', '')
        if not exchange_suffix:
            self.logger.warning(f"Unknown exchange: {exchange}, using symbol as-is")
            return symbol.upper()
        
        # Check if symbol already has the suffix
        if symbol.upper().endswith(exchange_suffix.upper()):
            return symbol.upper()
        
        return f"{symbol.upper()}{exchange_suffix}"
    
    def get_available_exchanges(self):
        """Get list of available exchanges"""
        return {k: v['name'] for k, v in STOCK_EXCHANGES.items()}
    
    def _get_cache_path(self, key):
        """Get the file path for a cache key"""
        return os.path.join(self.cache_dir, f"{key}.json")
    
    def _get_from_cache(self, key):
        """Retrieve data from cache if it exists and is not expired"""
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            self.misses += 1
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)
            
            # Check if cache is expired
            timestamp = cached.get('timestamp', 0)
            if time.time() - timestamp >= self.expire_seconds:
                self.misses += 1
                return None
            
            self.hits += 1
            return cached.get('data')
            
        except Exception as e:
            self.logger.error(f"Error reading cache file {cache_path}: {str(e)}")
            self.misses += 1
            return None
    
    def _save_to_cache(self, key, data):
        """Save data to cache with timestamp"""
        cache_path = self._get_cache_path(key)
        
        try:
            cache_data = {
                'timestamp': time.time(),
                'data': data
            }
            
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
                
        except Exception as e:
            self.logger.error(f"Error saving to cache file {cache_path}: {str(e)}")
    
    def get_stats(self):
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_requests': total_requests,
            'cache_hits': self.hits,
            'cache_misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'cache_expiry': f"{self.expire_seconds // 3600} hours"
        }
    
    def clear_expired(self):
        """Clear expired cache entries"""
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    with open(file_path, 'r') as f:
                        cached = json.load(f)
                    
                    timestamp = cached.get('timestamp', 0)
                    if time.time() - timestamp >= self.expire_seconds:
                        os.remove(file_path)
                        count += 1
                except:
                    # If the file is corrupt, remove it
                    os.remove(file_path)
                    count += 1
        
        return count
    
    def clear_all(self):
        """Clear all cache entries"""
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                os.remove(os.path.join(self.cache_dir, filename))
                count += 1
        
        return count

# Function to create stock data object for compatibility with existing code
def get_stock_data_yfinance(symbol, cache_instance=None, exchange=None):
    """
    Get stock data from Yahoo Finance (compatible with FMP function)
    
    Args:
        symbol (str): The stock symbol (e.g., 'AAPL')
        cache_instance (YFinanceCache): Optional cache instance
        exchange (str): Optional exchange code (e.g., 'L' for London)
    
    Returns:
        dict: Stock data in the same format as the original FMP function
    """
    if cache_instance is None:
        cache_instance = YFinanceCache()
        
    data = cache_instance.get_ticker_info(symbol, exchange)
    if not data:
        return None
        
    # Return in same format as the FMP function for compatibility
    return data