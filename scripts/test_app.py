"""
Quick test to verify the application can initialize
"""

try:
    print("Testing application initialization...")
    from src import create_app
    
    print("Creating app...")
    app = create_app()
    
    print("Checking app configuration...")
    print(f"  - App name: {app.name}")
    print(f"  - Debug mode: {app.debug}")
    print(f"  - Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')[:50]}...")
    
    print("Checking extensions...")
    print(f"  - Database: {'✓' if 'sqlalchemy' in app.extensions else '✗'}")
    print(f"  - Login Manager: {'✓' if 'login_manager' in app.extensions else '✗'}")
    print(f"  - Mail: {'✓' if 'mail' in app.extensions else '✗'}")
    print(f"  - Migrate: {'✓' if 'migrate' in app.extensions else '✗'}")
    
    print("\n✅ Application initialized successfully!")
    print("\nRegistered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  - {rule.endpoint}: {rule.rule}")
    
except Exception as e:
    print(f"\n❌ Error initializing application:")
    print(f"  {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
