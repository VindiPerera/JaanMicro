#!/usr/bin/env python3
"""
Test payment deletion status transition - Simple scenario
"""
import sys
sys.path.insert(0, '/Users/alexchamara/Office/JaanMicro')

from app import create_app, db
from app.models import Loan, LoanPayment, Branch, Customer
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date

app = create_app('development')

def test_simple_deletion_status_transition():
    """Test simple case: Add 1 payment that completes loan, then delete it"""
    with app.app_context():
        print("\n" + "=" * 80)
        print("TEST: Simple Payment Deletion - Delete Payment That Completes Loan")
        print("=" * 80)
        
        # Get or create a test branch and customer
        branch = Branch.query.first()
        customer = Customer.query.first()
        if not branch or not customer:
            print("ERROR: No branch or customer found")
            return False
        
        # Create a test loan
        loan = Loan(
            loan_number=f'TEST-SIMPLE-{datetime.now().timestamp()}',
            customer_id=customer.id,
            branch_id=branch.id,
            loan_type='monthly_loan',
            loan_amount=Decimal('5000.00'),
            interest_rate=10,
            interest_type='flat',
            duration_months=2,
            installment_frequency='monthly',
            installment_amount=Decimal('2750.00'),
            status='active',
            disbursement_date=date(2024, 1, 1),
            disbursed_amount=Decimal('5000.00'),
            total_payable=Decimal('5500.00'),
            first_installment_date=date(2024, 2, 1),
            created_by=1
        )
        
        db.session.add(loan)
        db.session.commit()
        print(f"\n✓ Created test loan: {loan.loan_number}")
        print(f"  - Loan Amount: Rs. {loan.loan_amount}")
        print(f"  - Total Payable: Rs. {loan.total_payable}")
        print(f"  - Initial Status: {loan.status}")
        
        # Add payment 1
        payment1 = LoanPayment(
            loan_id=loan.id,
            payment_amount=Decimal('2750.00'),
            principal_amount=Decimal('2500.00'),
            interest_amount=Decimal('250.00'),
            payment_date=date(2024, 2, 1),
            payment_method='cash',
            collected_by=1,
            receipt_number='RECEIPT-001'
        )
        db.session.add(payment1)
        loan.paid_amount = Decimal('2750.00')
        db.session.commit()
        print(f"\n✓ Added Payment 1: Rs. 2750.00")
        print(f"  - Paid: Rs. {loan.paid_amount}")
        print(f"  - Outstanding: Rs. {loan.calculate_current_outstanding() if loan.status == 'active' else '(cannot calc - not active)'}")
        print(f"  - Status: {loan.status}")
        
        # Add payment 2 - completes the loan
        payment2 = LoanPayment(
            loan_id=loan.id,
            payment_amount=Decimal('2750.00'),
            principal_amount=Decimal('2500.00'),
            interest_amount=Decimal('250.00'),
            payment_date=date(2024, 3, 1),
            payment_method='cash',
            collected_by=1,
            receipt_number='RECEIPT-002'
        )
        db.session.add(payment2)
        loan.paid_amount = Decimal('5500.00')
        # Manually update status as would happen in payment processing
        loan.outstanding_amount = Decimal('0.00')
        loan.status = 'completed'
        loan.closing_date = date(2024, 3, 1)
        db.session.commit()
        print(f"\n✓ Added Payment 2: Rs. 2750.00 (COMPLETES LOAN)")
        print(f"  - Paid: Rs. {loan.paid_amount}")
        print(f"  - Total Payable: Rs. {loan.total_payable}")
        print(f"  - Outstanding: Rs. {loan.outstanding_amount}")
        print(f"  - Status: {loan.status}")
        
        # Now delete payment 2 - this should NOT change status since payment 1 is still there
        # The outstanding would be: 5500 - 2750 = 2750
        print(f"\n" + "-" * 80)
        print("NOW: Deleting Payment 2 (the completing payment)...")
        print("-" * 80)
        
        from app.loans.routes import _refresh_loan_financial_state
        
        print(f"\nBefore deletion:")
        print(f"  - Status: {loan.status}")
        print(f"  - Outstanding (stored): Rs. {loan.outstanding_amount}")
        print(f"  - Paid Amount: Rs. {loan.paid_amount}")
        
        # Delete payment 2
        loan.paid_amount = (Decimal(str(loan.paid_amount or 0)) - Decimal('2750.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        _refresh_loan_financial_state(loan)
        db.session.delete(payment2)
        db.session.commit()
        
        print(f"\nAfter deletion and refresh:")
        print(f"  - Status: {loan.status}")
        print(f"  - Outstanding (stored): Rs. {loan.outstanding_amount}")
        print(f"  - Paid Amount: Rs. {loan.paid_amount}")
        
        # Verify the result
        print(f"\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        
        success = False
        if loan.status == 'active':
            print(f"\n✅ SUCCESS: Status reverted to 'active' after deleting completing payment")
            success = True
        else:
            print(f"\n❌ FAILED: Status is '{loan.status}', expected 'active'")
        
        print(f"  - Expected Outstanding: Rs. 2750.00 (5500 - 2750)")
        print(f"  - Actual Outstanding: Rs. {loan.outstanding_amount}")
        print(f"  - Status: {loan.status}")
        
        # Cleanup
        db.session.delete(payment1)
        db.session.delete(loan)
        db.session.commit()
        
        return success

if __name__ == '__main__':
    success = test_simple_deletion_status_transition()
    sys.exit(0 if success else 1)
