import os

from flask_apscheduler import APScheduler
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

import models  # noqa: F401  # Required for model discovery
from models.base import Base

"""
Flask extensions module.
Initializes and configures Flask extensions used throughout the application.
These extensions will be attached to the Flask app in the app.py file.
"""


# Create extension instances
db = SQLAlchemy()

engine: Engine = create_engine(
    os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///instance/expenses.db")
)
session: Session = sessionmaker(bind=engine)()


def init_db() -> None:
    Base.metadata.create_all(engine)


migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
scheduler = APScheduler()

login_manager.login_view = "auth.login"
