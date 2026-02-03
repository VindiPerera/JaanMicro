"""Script to clear all database records except admin users"""
from app import create_app, db
from app.models import (
    User, Branch, Customer, Loan, LoanPayment, 
    Investment, InvestmentTransaction, Pawning, PawningPayment,
    SystemSettings, ActivityLog
)

def clear_database_except_admin():
    """Clear all data from database except admin users"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get admin users to preserve
            admin_users = User.query.filter_by(role='admin').all()
            admin_ids = [user.id for user in admin_users]
            
            if not admin_users:
                print("Warning: No admin users found in database!")
                confirm = input("Continue clearing all data? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("Operation cancelled.")
                    return
            else:
                print(f"Found {len(admin_users)} admin user(s) to preserve:")
                for user in admin_users:
                    print(f"  - {user.username} ({user.email})")
                
                confirm = input("\nProceed with clearing all other data? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("Operation cancelled.")
                    return
            
            print("\nClearing database...")
            
            # Delete activity logs
            print("- Deleting activity logs...")
            ActivityLog.query.delete()
            
            # Delete loan-related data
            print("- Deleting loan payments...")
            LoanPayment.query.delete()
            
            print("- Deleting loans...")
            Loan.query.delete()
            
            # Delete investment-related data
            print("- Deleting investment transactions...")
            InvestmentTransaction.query.delete()
            
            print("- Deleting investments...")
            Investment.query.delete()
            
            # Delete pawning-related data
            print("- Deleting pawning payments...")
            PawningPayment.query.delete()
            
            print("- Deleting pawnings...")
            Pawning.query.delete()
            
            # Delete customers
            print("- Deleting customers...")
            Customer.query.delete()
            
            # Delete non-admin users
            print("- Deleting non-admin users...")
            User.query.filter(User.role != 'admin').delete()
            
            # Delete branches
            print("- Deleting branches...")
            Branch.query.delete()
            
            # Optionally clear system settings
            # SystemSettings.query.delete()
            
            # Commit all deletions
            db.session.commit()
            
            print("\n✓ Database cleared successfully!")
            print(f"✓ Preserved {len(admin_users)} admin user(s)")
            
            # Show remaining users
            remaining_users = User.query.all()
            print(f"\nRemaining users in database: {len(remaining_users)}")
            for user in remaining_users:
                print(f"  - {user.username} ({user.role})")
                
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error clearing database: {str(e)}")
            raise

if __name__ == '__main__':
    clear_database_except_admin()
