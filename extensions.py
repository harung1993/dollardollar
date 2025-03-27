from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_apscheduler import APScheduler

"""
Flask extensions module.
Initializes and configures Flask extensions used throughout the application.
These extensions will be attached to the Flask app in the app.py file.
"""

# Create extension instances
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
scheduler = APScheduler()

login_manager.login_view = "auth.login"