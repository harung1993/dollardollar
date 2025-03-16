r"""29a41de6a866d56c36aba5159f45257c"""
#!/usr/bin/env python
"""
This script completely resets the database by deleting the existing database file
and creating a new empty one with the current schema.
"""

import os
import sys
from app import app, db

def reset_database():
    """Delete existing database and create a new empty one with the current schema"""
    try:
        print("Starting database reset...")
        
        # Enter application context
        with app.app_context():
            # Get the database URI
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            print(f"Database URI: {db_uri}")
            
            # Create all tables with the current schema
            db.drop_all()
            print("Dropped all tables.")
            
            db.create_all()
            print("Created new database with current schema.")
        
        print("\nDatabase has been successfully reset!")
        print("The database is now empty. The first user to sign up will automatically become an admin.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Auto-confirm when running in Docker
    if os.environ.get('DOCKER_ENV') == 'true' or not sys.stdin.isatty():
        reset_database()
    else:
        print("DollarDollar Database Reset Utility")
        print("---------------------------------")
        print("WARNING: This will delete all data in your database!")
        confirm = input("Are you sure you want to proceed? (y/n): ").lower()
        
        if confirm == 'y':
            reset_database()
        else:
            print("Database reset cancelled. No changes were made.")