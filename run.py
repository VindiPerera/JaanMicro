#!/usr/bin/env python3
"""Application entry point"""
import os
import sys

def init_database():
    """Initialize the database"""
    from app import create_app, db
    app = create_app(os.getenv('FLASK_ENV') or 'development')
    with app.app_context():
        db.create_all()
        print("Database initialized!")

def create_admin_user():
    """Create an admin user"""
    from app import create_app, db
    from app.models import User, SystemSettings
    from werkzeug.security import generate_password_hash
    
    app = create_app(os.getenv('FLASK_ENV') or 'development')
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if admin already exists
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            print("Admin user already exists!")
            return
        
        admin = User(
            username='admin',
            email='admin@jaanmicro.com',
            password_hash=generate_password_hash('admin123'),
            full_name='System Administrator',
            role='admin',
            is_active=True
        )
        
        db.session.add(admin)
        
        # Create default system settings if not exists
        settings = SystemSettings.query.first()
        if not settings:
            settings = SystemSettings(
                app_name='JAANmicro',
                currency='LKR',
                theme_color='#2c3e50',
                interest_calculation_method='reducing_balance',
                late_payment_penalty_percentage=2.0
            )
            db.session.add(settings)
        
        try:
            db.session.commit()
            print("Admin user created successfully!")
            print("Username: admin")
            print("Password: admin123")
            print("Please change the password after first login!")
        except Exception as e:
            db.session.rollback()
            print("Error: {}".format(e))

if __name__ == '__main__':
    # Handle command-line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'create-admin':
            create_admin_user()
        elif command == 'init-db':
            init_database()
        else:
            print("Unknown command: {}".format(command))
            print("Available commands: create-admin, init-db")
            sys.exit(1)
    else:
        # Run the Flask development server
        from app import create_app
        app = create_app(os.getenv('FLASK_ENV') or 'development')
        app.run(host='0.0.0.0', port=5000, debug=True)
