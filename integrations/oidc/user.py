r"""29a41de6a866d56c36aba5159f45257c"""
"""
OIDC User Model Extensions for DollarDollar Bill Y'all
Provides OIDC integration for User model
"""

import json
import secrets
import hashlib
from datetime import datetime
from flask import current_app
from sqlalchemy import Column, String, DateTime, Boolean

def extend_user_model(db, User):
    """
    Extends the User model with OIDC methods
    
    Args:
        db: SQLAlchemy database instance
        User: User model class to extend
    
    Returns:
        Updated User class with OIDC support
    """
    # Add OIDC user creation method
    @classmethod
    def from_oidc(cls, oidc_data, provider='authelia'):
        """Create or update a user from OIDC data with security best practices"""
        # Check if user exists by OIDC ID
        user = cls.query.filter_by(oidc_id=oidc_data.get('sub'), oidc_provider=provider).first()
        
        # If not found, check by email, but only if we have a verified email
        if not user and 'email' in oidc_data:
            # Many providers include email_verified claim
            email_verified = oidc_data.get('email_verified', True)  # Default to True for providers that don't send this
            
            if email_verified:
                user = cls.query.filter_by(id=oidc_data['email']).first()
            
        # If user exists, update OIDC details if needed
        if user:
            # Link local account with OIDC if not already linked
            if not user.oidc_id:
                user.oidc_id = oidc_data.get('sub')
                user.oidc_provider = provider
                db.session.commit()
            
            # Update any user profile information
            if 'name' in oidc_data and oidc_data['name'] != user.name:
                user.name = oidc_data['name']
                db.session.commit()
                
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            return user
            
        # Create new user if not found
        if 'email' in oidc_data:
            # Email is required for a new user
            # Generate a secure random password for the local account
            random_password = secrets.token_urlsafe(24)
            
            # Get the display name from OIDC data
            name = oidc_data.get('name', 
                            oidc_data.get('preferred_username', 
                                        oidc_data['email'].split('@')[0]))
            
            # Check if this will be the first user
            is_first_user = cls.query.count() == 0
            
            # Create the user object
            user = cls(
                id=oidc_data['email'],
                name=name,
                oidc_id=oidc_data.get('sub'),
                oidc_provider=provider,
                is_admin=is_first_user,  # Make first user admin
                last_login=datetime.utcnow()
            )
            
            # Set the random password
            user.set_password(random_password)
            
            # Generate user color based on email
            hash_object = hashlib.md5(user.id.encode())
            hash_hex = hash_object.hexdigest()
            r = int(hash_hex[:2], 16)
            g = int(hash_hex[2:4], 16)
            b = int(hash_hex[4:6], 16)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if brightness > 180:
                r = min(int(r * 0.7), 255)
                g = min(int(g * 0.7), 255)
                b = min(int(b * 0.7), 255)
            user.user_color = f'#{r:02x}{g:02x}{b:02x}'
            
            # Save to database
            db.session.add(user)
            db.session.commit()
            from app import create_default_categories  # Import at the top of the file if possible
            create_default_categories(user.id)
            # Add a log entry
            current_app.logger.info(f"New user created via OIDC: {user.id}, Admin: {is_first_user}")
            
            return user
            
        # If we can't create a user (no email), log and return None
        current_app.logger.error(f"Cannot create user from OIDC data: Missing email. Data: {json.dumps(oidc_data)}")
        return None
    
    # Attach the from_oidc method to the User class
    User.from_oidc = from_oidc
    
    return User

def create_oidc_migration(directory="migrations/versions"):
    """
    Create a migration script for adding OIDC fields to User model
    
    Args:
        directory: Directory to save the migration file
        
    Returns:
        Path to the created migration file
    """
    import os
    from datetime import datetime
    
    # Create migration content
    migration_content = """\"\"\"Add OIDC support fields to users table

Revision ID: add_oidc_fields
Revises: # Will be filled automatically
Create Date: {date}

\"\"\"
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_oidc_fields'
down_revision = None  # This will be filled automatically
branch_labels = None
depends_on = None


def upgrade():
    # Add OIDC-related columns to users table
    op.add_column('users', sa.Column('oidc_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('oidc_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime, nullable=True))
    
    # Create index for faster lookups by OIDC ID
    op.create_index(op.f('ix_users_oidc_id'), 'users', ['oidc_id'], unique=True)


def upgrade_with_check():
    # Check if columns already exist (for manual execution)
    inspector = sa.inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'oidc_id' not in columns:
        op.add_column('users', sa.Column('oidc_id', sa.String(255), nullable=True))
    
    if 'oidc_provider' not in columns:
        op.add_column('users', sa.Column('oidc_provider', sa.String(50), nullable=True))
    
    if 'last_login' not in columns:
        op.add_column('users', sa.Column('last_login', sa.DateTime, nullable=True))
    
    # Create index if it doesn't exist
    indices = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'ix_users_oidc_id' not in indices:
        op.create_index(op.f('ix_users_oidc_id'), 'users', ['oidc_id'], unique=True)


def downgrade():
    # Remove OIDC-related columns and index
    op.drop_index(op.f('ix_users_oidc_id'), table_name='users')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'oidc_provider')
    op.drop_column('users', 'oidc_id')
""".format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Ensure directory exists
    os.makedirs(directory, exist_ok=True)
    
    # Create migration file
    filename = os.path.join(directory, "add_oidc_fields.py")
    
    with open(filename, 'w') as f:
        f.write(migration_content)
    
    return filename