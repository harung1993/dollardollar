import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_change_in_production")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///instance/expenses.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "True").lower() == "true"
    DISABLE_SIGNUPS = os.environ.get("DISABLE_SIGNUPS", "False").lower() == "true"
    LOCAL_LOGIN_DISABLE = os.getenv("LOCAL_LOGIN_DISABLE", "False").lower() == "true"

    # SimpleFin settings
    SIMPLEFIN_ENABLED = os.getenv("SIMPLEFIN_ENABLED", "True").lower() == "true"
    SIMPLEFIN_SETUP_TOKEN_URL = os.getenv(
        "SIMPLEFIN_SETUP_TOKEN_URL", "https://beta-bridge.simplefin.org/setup-token"
    )

    # Email settings
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME"))

    # Development credentials
    DEV_USER_EMAIL = os.getenv("DEV_USER_EMAIL", "dev@example.com")
    DEV_USER_PASSWORD = os.getenv("DEV_USER_PASSWORD", "dev")

    # OpenID Connect settings
    OIDC_ENABLED = os.getenv("OIDC_ENABLED", "False").lower() == "true"
    OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID")
    OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET")
    OIDC_PROVIDER_NAME = os.getenv("OIDC_PROVIDER_NAME", "OpenID")
    OIDC_DISCOVERY_URL = os.getenv("OIDC_DISCOVERY_URL")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class DevelopmentConfig(Config):
    """Development environment configuration"""

    DEBUG = True
    DEVELOPMENT_MODE = True


class ProductionConfig(Config):
    """Production environment configuration"""

    DEBUG = False
    DEVELOPMENT_MODE = False


class TestingConfig(Config):
    """Testing environment configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Return the appropriate configuration object based on environment"""
    env = os.getenv("FLASK_ENV", "production")
    return config_by_name.get(env, ProductionConfig)
