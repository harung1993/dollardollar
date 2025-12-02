"""
REST API Package for DollarDollar
Provides JSON API endpoints for React Native frontend
"""

from flask import Blueprint
from flask_restx import Api

# Create main API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Initialize Flask-RESTX API with Swagger documentation
api = Api(
    api_bp,
    version='1.0',
    title='DollarDollar API',
    description='REST API for DollarDollar expense tracking application',
    doc='/docs',  # Swagger UI available at /api/v1/docs
    authorizations={
        'Bearer': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Add JWT token as: Bearer <token>'
        }
    },
    security='Bearer'
)

# Import and register namespaces (will be created next)
from api.v1 import auth, analytics, transactions, accounts, budgets, categories, groups

# Register namespaces
api.add_namespace(auth.ns, path='/auth')
api.add_namespace(analytics.ns, path='/analytics')
api.add_namespace(transactions.ns, path='/transactions')
api.add_namespace(accounts.ns, path='/accounts')
api.add_namespace(budgets.ns, path='/budgets')
api.add_namespace(categories.ns, path='/categories')
api.add_namespace(groups.ns, path='/groups')
