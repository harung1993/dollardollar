"""Authentication API endpoints"""
from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from werkzeug.security import check_password_hash, generate_password_hash
from src.models.user import User
from src.extensions import db
from datetime import timedelta

# Create namespace
ns = Namespace('auth', description='Authentication operations')

# Define request/response models for Swagger documentation
login_model = ns.model('Login', {
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password')
})

register_model = ns.model('Register', {
    'username': fields.String(required=True, description='Username'),
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password')
})

token_response = ns.model('TokenResponse', {
    'access_token': fields.String(description='JWT access token'),
    'refresh_token': fields.String(description='JWT refresh token'),
    'user': fields.Raw(description='User information')
})

user_response = ns.model('UserResponse', {
    'id': fields.Integer(description='User ID'),
    'username': fields.String(description='Username'),
    'email': fields.String(description='User email'),
    'default_currency_code': fields.String(description='Default currency'),
    'created_at': fields.DateTime(description='Account creation date')
})


@ns.route('/login')
class Login(Resource):
    @ns.doc('login')
    @ns.expect(login_model)
    def post(self):
        """Login with email and password"""
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return {'message': 'Email and password required'}, 400

        # Note: User.id IS the email in this schema
        user = User.query.filter_by(id=email).first()

        if not user or not user.check_password(password):
            return {'message': 'Invalid email or password'}, 401

        # Create tokens
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'email': user.id},  # id IS the email
            expires_delta=timedelta(hours=24)
        )
        refresh_token = create_refresh_token(
            identity=user.id,
            expires_delta=timedelta(days=30)
        )

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,  # This is the email
                'name': user.name,
                'email': user.id,  # id IS the email
                'default_currency_code': user.default_currency_code
            }
        }, 200


@ns.route('/register')
class Register(Resource):
    @ns.doc('register')
    @ns.expect(register_model)
    def post(self):
        """Register a new user"""
        data = request.get_json()
        name = data.get('username')  # API expects 'username' but model uses 'name'
        email = data.get('email')
        password = data.get('password')

        if not name or not email or not password:
            return {'message': 'Name, email, and password required'}, 400

        # Check if user already exists (id IS the email)
        if User.query.filter_by(id=email).first():
            return {'message': 'Email already registered'}, 400

        # Create new user
        new_user = User(
            id=email,  # id IS the email
            name=name,
            default_currency_code='USD'
        )
        new_user.set_password(password)  # Use the set_password method

        db.session.add(new_user)
        db.session.commit()

        # Create tokens
        access_token = create_access_token(
            identity=new_user.id,
            additional_claims={'email': new_user.id},
            expires_delta=timedelta(hours=24)
        )
        refresh_token = create_refresh_token(
            identity=new_user.id,
            expires_delta=timedelta(days=30)
        )

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': new_user.id,
                'name': new_user.name,
                'email': new_user.id,
                'default_currency_code': new_user.default_currency_code
            }
        }, 201


@ns.route('/refresh')
class RefreshToken(Resource):
    @ns.doc('refresh_token', security='Bearer')
    @jwt_required(refresh=True)
    def post(self):
        """Refresh access token using refresh token"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return {'message': 'User not found'}, 404

        new_access_token = create_access_token(
            identity=current_user_id,
            additional_claims={'email': user.email},
            expires_delta=timedelta(hours=24)
        )

        return {'access_token': new_access_token}, 200


@ns.route('/me')
class CurrentUser(Resource):
    @ns.doc('get_current_user', security='Bearer')
    @jwt_required()
    @ns.marshal_with(user_response)
    def get(self):
        """Get current user information"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return {'message': 'User not found'}, 404

        return {
            'id': user.id,
            'name': user.name,
            'email': user.id,  # id IS the email
            'default_currency_code': user.default_currency_code,
            'created_at': user.created_at
        }, 200


@ns.route('/logout')
class Logout(Resource):
    @ns.doc('logout', security='Bearer')
    @jwt_required()
    def post(self):
        """Logout (client should discard tokens)"""
        # Note: With JWT, logout is handled client-side by discarding tokens
        # For blacklisting, you'd need to implement a token blocklist
        return {'message': 'Successfully logged out'}, 200
