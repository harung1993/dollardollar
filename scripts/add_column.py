r"""29a41de6a866d56c36aba5159f45257c"""
# save as update_db.py
from sqlalchemy import create_engine, text, inspect
import os

# Get database URI from environment or use default
db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI', 'postgresql://postgres:postgres@db:5432/dollardollar')

# Connect to database
engine = create_engine(db_uri)

# Check if column exists and add it if it doesn't
with engine.connect() as connection:
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'user_color' not in columns:
        print("Adding missing user_color column...")
        try:
            connection.execute(text('ALTER TABLE users ADD COLUMN user_color VARCHAR(7) DEFAULT \'#15803d\''))
            connection.commit()
            print("Successfully added user_color column!")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("user_color column already exists")