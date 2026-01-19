"""
User model
"""

from datetime import datetime, timedelta
import secrets
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from src.extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(120), primary_key=True)  # Using email as ID
    password_hash = db.Column(db.String(256))
    name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    default_currency_code = db.Column(db.String(3), db.ForeignKey('currencies.code'), nullable=True)
    default_currency = db.relationship('Currency', backref=db.backref('users', lazy=True))
    user_color = db.Column(db.String(7), default="#15803d")
    # OIDC related fields
    oidc_id = db.Column(db.String(255), nullable=True, index=True, unique=True)
    oidc_provider = db.Column(db.String(50), nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)   
    monthly_report_enabled = db.Column(db.Boolean, default=True)     
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    timezone = db.Column(db.String(50), nullable=True, default='UTC')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        try:
            return check_password_hash(self.password_hash, password)
        except ValueError:
            return False
        
    def generate_reset_token(self):
        """Generate a password reset token that expires in 1 hour"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        return self.reset_token
        
    def verify_reset_token(self, token):
        """Verify if the provided token is valid and not expired"""
        if not self.reset_token or self.reset_token != token:
            return False
        if not self.reset_token_expiry or self.reset_token_expiry < datetime.utcnow():
            return False
        return True
        
    def clear_reset_token(self):
        """Clear the reset token and expiry after use"""
        self.reset_token = None
        self.reset_token_expiry = None


class UserApiSettings(db.Model):
    __tablename__ = 'user_api_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False, unique=True)
    fmp_api_key = db.Column(db.String(100))  # Encrypted API key
    last_used = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('api_settings', uselist=False))
    
    def set_api_key(self, api_key):
        """Encrypt and store the API key"""
        if not api_key:
            self.fmp_api_key = None
            return
            
        # Simple encryption - in production use proper encryption
        import base64
        self.fmp_api_key = base64.b64encode(api_key.encode()).decode()
        
    def get_api_key(self):
        """Decrypt and return the API key"""
        if not self.fmp_api_key:
            return None
            
        # Simple decryption - in production use proper decryption
        import base64
        return base64.b64decode(self.fmp_api_key.encode()).decode()
