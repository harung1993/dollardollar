# session_timeout.py
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash, request
from flask_login import logout_user, current_user
import threading

class DemoTimeout:
    """
    Middleware to enforce demo user session timeouts
    """
    # Class-level variable to track active demo sessions
    _active_demo_sessions = {}
    _session_lock = threading.Lock()
    
    def __init__(self, app=None, timeout_minutes=10, demo_users=None, max_concurrent_sessions=5):
        self.timeout_minutes = timeout_minutes
        self.demo_users = demo_users or [
            'demo@example.com',
            'demo1@example.com', 
            'demo2@example.com'
        ]
        self.max_concurrent_sessions = max_concurrent_sessions
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask application"""
        app.before_request(self.check_session_timeout)
        app.after_request(self.update_last_active)
        
        # Add configuration values
        app.config.setdefault('DEMO_TIMEOUT_MINUTES', self.timeout_minutes)
        app.config.setdefault('DEMO_USERS', self.demo_users)
        app.config.setdefault('MAX_CONCURRENT_DEMO_SESSIONS', self.max_concurrent_sessions)
        
        # Make demo status checker available in templates
        @app.context_processor
        def inject_demo_status():
            return {
                'is_demo_user': self.is_demo_user,
                'get_remaining_time': self.get_remaining_time,
                'get_active_demo_sessions': self.get_active_demo_sessions
            }
        
        # Store the DemoTimeout instance in the app extensions
        app.extensions['demo_timeout'] = self
    
    def register_demo_session(self, user_id):
        """
        Register a new demo session, return True if successful
        """
        with self._session_lock:
            # Clean up expired sessions first
            current_time = datetime.utcnow()
            
            # Remove expired sessions
            self._active_demo_sessions = {
                uid: session_data for uid, session_data in self._active_demo_sessions.items() 
                if current_time < datetime.fromtimestamp(session_data['start_time']) + timedelta(minutes=self.timeout_minutes)
            }
            
            # Check current session count
            if len(self._active_demo_sessions) >= self.max_concurrent_sessions:
                return False
            
            # Register new session
            self._active_demo_sessions[user_id] = {
                'start_time': datetime.utcnow().timestamp(),
                'ip_address': request.remote_addr
            }
            return True
    
    def unregister_demo_session(self, user_id):
        """
        Unregister a demo session
        """
        with self._session_lock:
            if user_id in self._active_demo_sessions:
                del self._active_demo_sessions[user_id]
    
    def get_active_demo_sessions(self):
        """
        Get the number of currently active demo sessions
        """
        with self._session_lock:
            # Clean up expired sessions first
            current_time = datetime.utcnow()
            self._active_demo_sessions = {
                uid: session_data for uid, session_data in self._active_demo_sessions.items() 
                if current_time < datetime.fromtimestamp(session_data['start_time']) + timedelta(minutes=self.timeout_minutes)
            }
            return len(self._active_demo_sessions)
    
    def check_session_timeout(self):
        """Check if the demo session has expired"""
        # Skip for static resources and login/logout pages
        if (not request.path.startswith('/static') and 
            request.path not in ['/login', '/logout', '/demo', '/'] and 
            current_user.is_authenticated and
            self.is_demo_user(current_user.id)):
            
            # Check if session start time exists
            if 'demo_start_time' not in session:
                session['demo_start_time'] = datetime.utcnow().timestamp()
            
            # Check if session has expired
            start_time = datetime.fromtimestamp(session['demo_start_time'])
            if datetime.utcnow() > start_time + timedelta(minutes=self.timeout_minutes):
                # Session expired, clean up
                self.unregister_demo_session(current_user.id)
                
                # Reset demo data
                from app import reset_demo_data  # Import reset function
                reset_demo_data(current_user.id)
                
                # Log out user
                logout_user()
                session.clear()
                flash('Your demo session has expired. Thank you for trying our application!')
                return redirect(url_for('demo_login'))
    
    def update_last_active(self, response):
        """Update the last active time after each request"""
        user_id = None
        if current_user.is_authenticated:
            try:
                user_id = current_user.id
            except:
                # Handle detached user case
                return response
        if current_user.is_authenticated and self.is_demo_user(current_user.id):
            session['last_active'] = datetime.utcnow().timestamp()
        return response
    
    def is_demo_user(self, user_id):
        """Check if the current user is a demo user"""
        if not user_id:
            return False
            
        # Check if user is in demo users list or has a demo email pattern
        return (user_id in self.demo_users or 
                user_id in ['demo@example.com', 'demo1@example.com', 'demo2@example.com'] or
                user_id.endswith('@demo.com') or 
                'demo' in user_id.lower())
    
    def get_remaining_time(self):
        """Get the remaining time for the demo session in seconds"""
        if not current_user.is_authenticated or not self.is_demo_user(current_user.id):
            return None
            
        if 'demo_start_time' not in session:
            return self.timeout_minutes * 60
            
        start_time = datetime.fromtimestamp(session['demo_start_time'])
        end_time = start_time + timedelta(minutes=self.timeout_minutes)
        remaining = (end_time - datetime.utcnow()).total_seconds()
        
        return max(0, int(remaining))

# Decorator for routes that are time-limited in demo mode
def demo_time_limited(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If user is a demo user and session is expired, redirect to login
        if current_user.is_authenticated and hasattr(current_user, 'id'):
            from flask import current_app
            demo_timeout = current_app.extensions.get('demo_timeout')
            
            if demo_timeout and demo_timeout.is_demo_user(current_user.id):
                # Get demo timeout from app config
                timeout_minutes = current_app.config.get('DEMO_TIMEOUT_MINUTES', 10)
                
                # Check if session has expired
                if 'demo_start_time' in session:
                    start_time = datetime.fromtimestamp(session['demo_start_time'])
                    if datetime.utcnow() > start_time + timedelta(minutes=timeout_minutes):
                        # Reset demo data
                        from app import reset_demo_data
                        reset_demo_data(current_user.id)
                        
                        # Log out user
                        logout_user()
                        session.clear()
                        flash('Your demo session has expired. Thank you for trying our application!')
                        return redirect(url_for('demo_login'))
        
        return f(*args, **kwargs)
    return decorated_function