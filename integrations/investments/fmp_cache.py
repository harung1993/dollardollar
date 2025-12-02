import os
import json
import time
from datetime import datetime, timedelta
import requests

class FMPCache:
    """
    Cache for Financial Modeling Prep API responses
    Reduces unnecessary API calls by storing responses locally
    """
    
    def __init__(self, cache_dir='instance/cache/fmp', expire_hours=24):
        """
        Initialize the cache
        
        Args:
            cache_dir: Directory to store cache files
            expire_hours: Hours before cache expires (default: 24 hours)
        """
        self.cache_dir = cache_dir
        self.expire_seconds = expire_hours * 3600
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        # Stats for monitoring
        self.stats = {
            'hits': 0,
            'misses': 0,
            'api_calls': 0
        }
    
    def _get_cache_filename(self, endpoint, params):
        """Generate a unique filename for the request"""
        # Sort params to ensure consistent filename for same requests with different param order
        params_str = json.dumps(params, sort_keys=True)
        # Create a hash from the endpoint and params
        cache_key = f"{endpoint}_{hash(params_str)}"
        return os.path.join(self.cache_dir, f"{cache_key.replace('/', '_')}.json")
    
    def get(self, api_url, endpoint, api_key, params=None):
        """
        Get data from cache or API
        
        Args:
            api_url: Base API URL
            endpoint: API endpoint
            api_key: API key
            params: Additional parameters for the request (excluding API key)
            
        Returns:
            API response data
        """
        if params is None:
            params = {}
            
        # Add API key to params
        request_params = params.copy()
        request_params['apikey'] = api_key
        
        # Check if response is in cache
        cache_file = self._get_cache_filename(endpoint, params)
        
        if os.path.exists(cache_file):
            # Read cache file
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid
            if time.time() - cache_data['timestamp'] < self.expire_seconds:
                self.stats['hits'] += 1
                return cache_data['data']
        
        # Cache miss or expired, make API request
        self.stats['misses'] += 1
        self.stats['api_calls'] += 1
        
        full_url = f"{api_url}/{endpoint}"
        response = requests.get(full_url, params=request_params)
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status code {response.status_code}: {response.text}")
        
        # Parse response data
        data = response.json()
        
        # Save to cache
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        return data
    
    def clear_expired(self):
        """Clear expired cache files"""
        count = 0
        for filename in os.listdir(self.cache_dir):
            cache_file = os.path.join(self.cache_dir, filename)
            
            if os.path.isfile(cache_file) and cache_file.endswith('.json'):
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    if time.time() - cache_data['timestamp'] >= self.expire_seconds:
                        os.remove(cache_file)
                        count += 1
                except (json.JSONDecodeError, KeyError):
                    # Invalid cache file, remove it
                    os.remove(cache_file)
                    count += 1
        
        return count
    
    def clear_all(self):
        """Clear all cache files"""
        count = 0
        for filename in os.listdir(self.cache_dir):
            cache_file = os.path.join(self.cache_dir, filename)
            
            if os.path.isfile(cache_file) and cache_file.endswith('.json'):
                os.remove(cache_file)
                count += 1
        
        return count
    
    def get_stats(self):
        """Get cache stats"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'api_calls': self.stats['api_calls'],
            'hit_rate': f"{hit_rate:.2f}%",
            'api_calls_saved': self.stats['hits']
        }