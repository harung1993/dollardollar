r"""29a41de6a866d56c36aba5159f45257c"""
"""
OIDC Authentication module for DollarDollar Bill Y'all
Provides OpenID Connect integration
"""

import os
import secrets
import hashlib
import base64
import time
import json
import logging
from datetime import datetime
from urllib.parse import urlencode
import requests
from flask import Flask, current_app, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, current_user, login_required

# OIDC helper functions
def generate_code_verifier():
    """Generate a secure code verifier for PKCE"""
    code_verifier = secrets.token_urlsafe(64)
    # Ensure it's at most 128 characters
    return code_verifier[:128]

def generate_code_challenge(code_verifier):
    """Generate a code challenge from the code verifier"""
    code_challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode().rstrip('=')
    return code_challenge

def generate_state_token():
    """Generate a secure state token to prevent CSRF"""
    return secrets.token_urlsafe(32)

def set_oidc_session(key, value):
    """Securely store OIDC data in session"""
    session[f'oidc_{key}'] = value

def get_oidc_session(key, default=None, delete=False):
    """Securely retrieve OIDC data from session"""
    session_key = f'oidc_{key}'
    value = session.get(session_key, default)
    if delete and session_key in session:
        del session[session_key]
    return value

def is_oidc_enabled():
    """Check if OIDC authentication is enabled"""
    return current_app.config.get('OIDC_ENABLED', False)

def setup_oidc_config(app):
    """Configure OIDC settings from environment variables using discovery endpoint"""
    oidc_enabled = os.getenv('OIDC_ENABLED', 'False').lower() == 'true'
    
    # Configure LOCAL_LOGIN_DISABLE regardless of OIDC status
    app.config['LOCAL_LOGIN_DISABLE'] = os.getenv('LOCAL_LOGIN_DISABLE', 'False').lower() == 'true'
    
    if oidc_enabled:
        app.config['OIDC_ENABLED'] = True
        app.config['OIDC_CLIENT_ID'] = os.getenv('OIDC_CLIENT_ID')
        app.config['OIDC_CLIENT_SECRET'] = os.getenv('OIDC_CLIENT_SECRET')
        app.config['OIDC_PROVIDER_NAME'] = os.getenv('OIDC_PROVIDER_NAME', 'SSO')
        
        # Try explicit discovery URL first
        discovery_url = os.getenv('OIDC_DISCOVERY_URL')
        
        # If no explicit discovery URL, try to construct it from issuer
        if not discovery_url:
            issuer = os.getenv('OIDC_ISSUER')
            if issuer:
                # Ensure issuer URL has trailing slash for proper joining
                if not issuer.endswith('/'):
                    issuer = f"{issuer}/"
                discovery_url = f"{issuer}.well-known/openid-configuration"
                app.logger.info(f"Constructed discovery URL from issuer: {discovery_url}")
        
        if discovery_url:
            try:
                # Fetch OpenID configuration from discovery endpoint
                app.logger.info(f"Fetching OIDC configuration from: {discovery_url}")
                response = requests.get(discovery_url, timeout=10)
                if response.status_code == 200:
                    config = response.json()
                    
                    # Set OIDC endpoints from discovery document
                    app.config['OIDC_ISSUER'] = config.get('issuer')
                    app.config['OIDC_AUTH_URI'] = config.get('authorization_endpoint')
                    app.config['OIDC_TOKEN_URI'] = config.get('token_endpoint')
                    app.config['OIDC_USERINFO_URI'] = config.get('userinfo_endpoint')
                    app.config['OIDC_JWKS_URI'] = config.get('jwks_uri')
                    app.config['OIDC_LOGOUT_URI'] = config.get('end_session_endpoint')
                    
                    app.logger.info(f"OIDC configuration loaded from discovery endpoint")
                    app.logger.debug(f"  Auth: {app.config['OIDC_AUTH_URI']}")
                    app.logger.debug(f"  Token: {app.config['OIDC_TOKEN_URI']}")
                    app.logger.debug(f"  Userinfo: {app.config['OIDC_USERINFO_URI']}")
                    app.logger.debug(f"  Logout: {app.config['OIDC_LOGOUT_URI']}")
                else:
                    app.logger.error(f"Failed to fetch OIDC configuration from {discovery_url}: {response.status_code}")
            except Exception as e:
                app.logger.error(f"Error loading OIDC discovery document: {str(e)}")
        
        # Fall back to individually specified endpoints if discovery failed
        # or specific endpoints are missing
        if not app.config.get('OIDC_AUTH_URI'):
            app.config['OIDC_AUTH_URI'] = os.getenv('OIDC_AUTH_URI')
            app.logger.info(f"Using manually configured Auth URI: {app.config['OIDC_AUTH_URI']}")
            
        if not app.config.get('OIDC_TOKEN_URI'):
            app.config['OIDC_TOKEN_URI'] = os.getenv('OIDC_TOKEN_URI')
            app.logger.info(f"Using manually configured Token URI: {app.config['OIDC_TOKEN_URI']}")
            
        if not app.config.get('OIDC_USERINFO_URI'):
            app.config['OIDC_USERINFO_URI'] = os.getenv('OIDC_USERINFO_URI')
            app.logger.info(f"Using manually configured Userinfo URI: {app.config['OIDC_USERINFO_URI']}")
            
        if not app.config.get('OIDC_LOGOUT_URI'):
            app.config['OIDC_LOGOUT_URI'] = os.getenv('OIDC_LOGOUT_URI')
            app.logger.info(f"Using manually configured Logout URI: {app.config['OIDC_LOGOUT_URI']}")
        
        if not app.config.get('OIDC_ISSUER'):
            app.config['OIDC_ISSUER'] = os.getenv('OIDC_ISSUER')
        
        # Common configuration
        app.config['OIDC_REDIRECT_URI'] = os.getenv('APP_URL', 'http://localhost:5006') + '/oidc/callback'
        app.config['OIDC_SCOPES'] = ['openid', 'email', 'profile']
        
        # Check if all required endpoints are configured
        missing_endpoints = []
        if not app.config.get('OIDC_AUTH_URI'):
            missing_endpoints.append('OIDC_AUTH_URI')
        if not app.config.get('OIDC_TOKEN_URI'):
            missing_endpoints.append('OIDC_TOKEN_URI')
        if not app.config.get('OIDC_USERINFO_URI'):
            missing_endpoints.append('OIDC_USERINFO_URI')
            
        if missing_endpoints:
            app.logger.error(f"Missing required OIDC endpoints: {', '.join(missing_endpoints)}")
            app.logger.error("OIDC authentication will not work properly without these endpoints")
        
        app.logger.info(f"OIDC authentication is enabled using {app.config['OIDC_PROVIDER_NAME']}")
        
        # Log whether local login is disabled
        if app.config['LOCAL_LOGIN_DISABLE']:
            app.logger.info("Local password login is disabled")
        else:
            app.logger.info("Local password login is enabled")
    else:
        app.config['OIDC_ENABLED'] = False
        app.logger.info("OIDC authentication is disabled")
    
    return oidc_enabled

def register_oidc_routes(app, User, db):
    """Register OIDC routes with the Flask application"""
    
    @app.route('/login/oidc')
    def login_oidc():
        """Initiate OIDC authentication with PKCE flow for enhanced security"""
        if not is_oidc_enabled():
            flash('OIDC authentication is not enabled.')
            return redirect(url_for('login'))
        
        try:
            # Generate and store PKCE code_verifier
            code_verifier = generate_code_verifier()
            code_challenge = generate_code_challenge(code_verifier)
            set_oidc_session('code_verifier', code_verifier)
            
            # Generate state parameter to prevent CSRF
            state = generate_state_token()
            set_oidc_session('state', state)
            
            # Store the original URL to redirect after authentication
            redirect_to = request.args.get('next', url_for('dashboard'))
            set_oidc_session('redirect_to', redirect_to)
            
            # Build authorization request URL
            params = {
                'response_type': 'code',
                'client_id': current_app.config['OIDC_CLIENT_ID'],
                'redirect_uri': current_app.config['OIDC_REDIRECT_URI'],
                'scope': ' '.join(current_app.config['OIDC_SCOPES']),
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256',
                'nonce': secrets.token_urlsafe(16)  # Prevents replay attacks
            }
            
            # Add optional prompt parameter if provided
            prompt = request.args.get('prompt')
            if prompt:
                params['prompt'] = prompt
                
            # Add login hint if provided (pre-fills email)
            login_hint = request.args.get('login_hint')
            if login_hint:
                params['login_hint'] = login_hint
            
            auth_url = f"{current_app.config['OIDC_AUTH_URI']}?{urlencode(params)}"
            return redirect(auth_url)
            
        except Exception as e:
            current_app.logger.error(f"Error initiating OIDC authentication: {str(e)}")
            flash('An error occurred while initiating authentication.')
            return redirect(url_for('login'))

    @app.route('/oidc/callback')
    def oidc_callback():
        """Handle OIDC callback with proper security validation"""
        if not is_oidc_enabled():
            flash('OIDC authentication is not enabled.')
            return redirect(url_for('login'))
        
        try:
            # Get the authorization code from the callback
            code = request.args.get('code')
            if not code:
                raise ValueError("No authorization code received")
            
            # Verify state parameter to prevent CSRF
            callback_state = request.args.get('state')
            stored_state = get_oidc_session('state', delete=True)
            
            if not callback_state or callback_state != stored_state:
                current_app.logger.warning("Invalid state parameter in OIDC callback")
                flash('Authentication failed: Invalid state parameter.')
                return redirect(url_for('login'))
            
            # Get the code verifier from session
            code_verifier = get_oidc_session('code_verifier', delete=True)
            if not code_verifier:
                current_app.logger.warning("Missing code verifier in OIDC callback")
                flash('Authentication failed: Missing code verifier.')
                return redirect(url_for('login'))
            
            # Exchange the code for tokens
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': current_app.config['OIDC_REDIRECT_URI'],
                'client_id': current_app.config['OIDC_CLIENT_ID'],
                'client_secret': current_app.config['OIDC_CLIENT_SECRET'],
                'code_verifier': code_verifier
            }
            
            # Make token request
            token_response = requests.post(
                current_app.config['OIDC_TOKEN_URI'],
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            if token_response.status_code != 200:
                current_app.logger.error(f"Token exchange failed: {token_response.text}")
                flash('Authentication failed: Unable to validate credentials.')
                return redirect(url_for('login'))
            
            tokens = token_response.json()
            
            # Get user info from ID token or userinfo endpoint
            if 'id_token' in tokens:
                # Save the ID token for logout
                set_oidc_session('id_token', tokens['id_token'])
            
            # Get user info from userinfo endpoint
            userinfo_response = requests.get(
                current_app.config['OIDC_USERINFO_URI'],
                headers={'Authorization': f"Bearer {tokens['access_token']}"},
                timeout=10
            )
            
            if userinfo_response.status_code != 200:
                current_app.logger.error(f"Userinfo request failed: {userinfo_response.text}")
                flash('Authentication failed: Unable to retrieve user information.')
                return redirect(url_for('login'))
            
            user_info = userinfo_response.json()
            
            # Verify we got basic required user info
            if 'sub' not in user_info:
                current_app.logger.error("Missing sub claim in OIDC userinfo")
                flash('Authentication failed: Incomplete user information received.')
                return redirect(url_for('login'))
            
            # Create or get the user
            user = User.from_oidc(user_info)
            
            if not user:
                flash('Authentication failed: Unable to create or find user.')
                return redirect(url_for('login'))
            
            # Login the user
            login_user(user)
            
            # Redirect to the original requested URL or dashboard
            redirect_to = get_oidc_session('redirect_to', url_for('dashboard'), delete=True)
            return redirect(redirect_to)
            
        except Exception as e:
            current_app.logger.error(f"Error processing OIDC callback: {str(e)}")
            flash('An error occurred during authentication. Please try again.')
            return redirect(url_for('login'))

    @app.route('/logout/oidc')
    @login_required
    def logout_oidc():
        """Properly handle complete logout for both local and OIDC sessions"""
        if not is_oidc_enabled():
            return redirect(url_for('logout'))
        
        # Check if this user is authenticated via OIDC
        has_oidc = hasattr(current_user, 'oidc_id') and current_user.oidc_id is not None
        
        # Get the stored ID token before logout
        id_token = get_oidc_session('id_token', None, delete=True)
        
        # Get the logout endpoint
        logout_endpoint = current_app.config.get('OIDC_LOGOUT_URI')
        
        # Log out from the app first
        logout_user()
        
        # Set a session flag for logout message before clearing session data
        session['show_logout_message'] = True
        
        # Clear any OIDC-related session data
        for key in list(session.keys()):
            if key.startswith('oidc_'):
                session.pop(key, None)
        
        # If we have both a logout endpoint and this was an OIDC user, try to perform a complete logout
        if logout_endpoint and has_oidc and id_token:
            try:
                # Build the post-logout redirect URL
                app_url = request.host_url.rstrip('/')
                post_logout_redirect_uri = f"{app_url}{url_for('login')}"
                
                # Construct logout parameters
                logout_params = {
                    'post_logout_redirect_uri': post_logout_redirect_uri,
                    'id_token_hint': id_token
                }
                
                # Build the complete URL with parameters
                from urllib.parse import urlencode
                full_logout_url = f"{logout_endpoint}?{urlencode(logout_params)}"
                
                current_app.logger.info(f"Redirecting to OIDC provider logout: {full_logout_url}")
                return redirect(full_logout_url)
            except Exception as e:
                current_app.logger.error(f"Error during OIDC logout redirect: {str(e)}")
                # Continue to local logout fallback if there's an error
        
        # Default behavior: redirect to the app's login page directly
        return redirect(url_for('login'))