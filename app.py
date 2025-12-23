"""
DollarDollar - Personal Finance & Expense Tracking Application
Main application entry point (modularized version)

The original monolithic app.py has been refactored into a modular structure:
- Models: src/models/
- Services: src/services/
- Utilities: src/utils/
- Integrations: integrations/
- Configuration: src/config.py
- Extensions: src/extensions.py

Original code is preserved in app_old.py for reference.
"""

import os
from src import create_app
from src.cli import register_commands

# Create the Flask application using the application factory
app = create_app()

# Register CLI commands
register_commands(app)

# Set OpenSSL legacy provider (for compatibility)
os.environ['OPENSSL_LEGACY_PROVIDER'] = '1'

if __name__ == '__main__':
    # Run the development server
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
