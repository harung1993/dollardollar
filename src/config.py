"""
Application configuration
Centralized configuration loaded from environment variables
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    # Secret key
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback_secret_key_change_in_production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Application settings
    DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE', 'True').lower() == 'true'
    DISABLE_SIGNUPS = os.getenv('DISABLE_SIGNUPS', 'False').lower() == 'true'
    LOCAL_LOGIN_DISABLE = os.getenv('LOCAL_LOGIN_DISABLE', 'False').lower() == 'true'
    
    # SimpleFin
    SIMPLEFIN_ENABLED = os.getenv('SIMPLEFIN_ENABLED', 'True').lower() == 'true'
    SIMPLEFIN_SETUP_TOKEN_URL = os.getenv('SIMPLEFIN_SETUP_TOKEN_URL', 'https://beta-bridge.simplefin.org/setup-token')
    
    # Investments
    INVESTMENT_TRACKING_ENABLED = os.getenv('INVESTMENT_TRACKING_ENABLED', 'False').lower() == 'true'
    FMP_API_KEY = os.getenv('FMP_API_KEY', None)
    FMP_API_URL = os.getenv('FMP_API_URL', 'https://financialmodelingprep.com/api/v3')
    
    # Email configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))
    
    # Timezone
    TIMEZONE = 'EST'
    
    # Demo mode
    DEMO_TIMEOUT_MINUTES = int(os.getenv('DEMO_TIMEOUT_MINUTES', 10))
    MAX_CONCURRENT_DEMO_SESSIONS = int(os.getenv('MAX_CONCURRENT_DEMO_SESSIONS', 10))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

def get_config():
    """Get the appropriate configuration"""
    return Config()
