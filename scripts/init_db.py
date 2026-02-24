r"""29a41de6a866d56c36aba5159f45257c"""
from app import app, db

def init_database():
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

if __name__ == "__main__":
    init_database()