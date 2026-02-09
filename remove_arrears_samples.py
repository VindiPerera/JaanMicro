#!/usr/bin/env python3
"""Remove specific arrears sample loans from database"""

from app import create_app, db
from app.models import Loan, LoanPayment

app = create_app('development')
with app.app_context():
    # List of loan numbers to remove
    loan_numbers_to_remove = ['ARREARS-7220', 'ARREARS-2667', 'ARREARS-001']

    print("Removing specific arrears sample loans...")

    for loan_number in loan_numbers_to_remove:
        # Find the loan
        loan = Loan.query.filter_by(loan_number=loan_number).first()

        if loan:
            print(f"\nFound loan: {loan_number}")
            print(f"Customer: {loan.customer.full_name}")
            print(f"Amount: Rs. {loan.loan_amount}")
            print(f"Status: {loan.status}")

            # Delete associated payments first
            payments = LoanPayment.query.filter_by(loan_id=loan.id).all()
            if payments:
                print(f"Deleting {len(payments)} payment(s)...")
                for payment in payments:
                    db.session.delete(payment)

            # Delete the loan
            print(f"Deleting loan {loan_number}...")
            db.session.delete(loan)

            print(f"Successfully removed loan {loan_number}")
        else:
            print(f"Loan {loan_number} not found")

    # Commit all changes
    db.session.commit()
    print("\nAll specified loans have been removed from the database.")