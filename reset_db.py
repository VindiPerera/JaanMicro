"""
Reset database to a completely fresh state.
Creates all tables via db.create_all() and sets up a default admin user.
"""
import os

# Delete existing database file if it exists
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'jaanmicro.db')
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted: {db_path}")
else:
    print(f"No existing DB found at: {db_path}")

from app import create_app, db
from app.models import User, SystemSettings, Branch

app = create_app()

with app.app_context():
    # Create all tables fresh
    db.create_all()
    print("All tables created.")

    # Create default branch
    branch = Branch(
        branch_code='MAIN',
        name='Main Branch',
        address='Head Office',
        is_active=True
    )
    db.session.add(branch)
    db.session.flush()

    # Create admin user (nic_number required - use a placeholder)
    admin = User(
        username='admin',
        email='admin@jaanmicro.com',
        full_name='Administrator',
        nic_number='000000000000',
        role='admin',
        is_active=True,
        branch_id=None  # admin has access to all branches
    )
    admin.set_password('admin123')
    db.session.add(admin)

    # Create default system settings (uses all defaults, no extra args needed)
    settings = SystemSettings()
    db.session.add(settings)

    db.session.commit()
    print("\nFresh database ready!")
    print("  Branch : Main Branch (MAIN)")
    print("  Admin  : username=admin  password=admin123")
    print("\nPlease change the admin password after first login.")
