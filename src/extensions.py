"""
Flask extensions initialization
All Flask extensions are initialized here and then imported by the application factory
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
import pytz

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
scheduler = APScheduler()

# Configure scheduler timezone
scheduler.timezone = pytz.timezone('EST')

def init_extensions(app):
    """Initialize all Flask extensions with the app"""
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    mail.init_app(app)
    migrate.init_app(app, db)
    scheduler.init_app(app)
    scheduler.start()
