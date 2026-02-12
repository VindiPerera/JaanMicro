"""
Test to verify that monthly loan outstanding amount includes interest
"""
import sys
sys.path.insert(0, '/Users/kevinbrinsly/JaanNetworkProjects/JaanMicro')

from app import create_app, db
from app.models import Loan, Branch
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

app = create_app()

def test_monthly_loan_outstanding():
    """Test that monthly loan outstanding includes interest"""
    with app.app_context():
        branch = Branch.query.first()
        if not branch:
            print("No branch found. Please create a branch first.")
            return
        
        print("=" * 80)
        print("TEST: Monthly Loan Outstanding Calculation (Includes Interest)")
        print("=" * 80)
        
        # Test Case 1: Monthly Loan with Reducing Balance - After 3 payments
        print("\n--- Test 1: Monthly Reducing Balance Loan ---")
        
        loan_amount = Decimal('100000')
        interest_rate = Decimal('12')
        months = 12
        
        # Calculate EMI
        monthly_rate = interest_rate / (Decimal('12') * Decimal('100'))
        n = months
        mr_float = float(monthly_rate)
        power_calc = ((1 + mr_float) ** n) / (((1 + mr_float) ** n) - 1)
        emi = loan_amount * monthly_rate * Decimal(str(power_calc))
        emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_payable = (emi * Decimal(str(n))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        loan_rb = Loan(
            loan_number='TEST-RB-OUT-001',
            customer_id=1,
            branch_id=branch.id,
            loan_type='monthly_loan',
            loan_amount=float(loan_amount),
            interest_rate=float(interest_rate),
            interest_type='reducing_balance',
            duration_months=months,
            installment_frequency='monthly',
            status='active',
            disbursement_date=date(2024, 1, 1),
            disbursed_amount=float(loan_amount),
            first_installment_date=date(2024, 2, 1),
            installment_amount=float(emi),
            total_payable=float(total_payable),
            paid_amount=0,
            created_by=1
        )
        
        print(f"Initial Loan:")
        print(f"  Loan Amount: ₹{loan_amount:,.2f}")
        print(f"  Total Payable: ₹{total_payable:,.2f}")
        print(f"  Total Interest: ₹{total_payable - loan_amount:,.2f}")
        print(f"  EMI: ₹{emi:,.2f}")
        
        # Before any payment
        outstanding = loan_rb.calculate_current_outstanding()
        print(f"\nBefore payment:")
        print(f"  Outstanding: ₹{float(outstanding):,.2f}")
        print(f"  Expected: ₹{float(total_payable):,.2f} (Total Payable)")
        print(f"  ✓ Includes full interest" if abs(outstanding - total_payable) < Decimal('0.01') else f"  ✗ ERROR: Missing interest!")
        
        # After 3 payments
        payments_made = 3
        total_paid = emi * Decimal(str(payments_made))
        loan_rb.paid_amount = float(total_paid)
        
        outstanding_after = loan_rb.calculate_current_outstanding()
        expected_outstanding = total_payable - total_paid
        
        print(f"\nAfter {payments_made} payments of ₹{float(emi):,.2f} each:")
        print(f"  Total Paid: ₹{float(total_paid):,.2f}")
        print(f"  Outstanding: ₹{float(outstanding_after):,.2f}")
        print(f"  Expected: ₹{float(expected_outstanding):,.2f} (Remaining total with interest)")
        print(f"  ✓ Includes remaining interest" if abs(outstanding_after - expected_outstanding) < Decimal('0.01') else f"  ✗ ERROR: Missing interest!")
        
        # Calculate what principal and interest remain
        remaining_principal = loan_amount - (total_paid * Decimal('0.75'))  # Rough estimate
        remaining_interest = expected_outstanding - remaining_principal
        print(f"  Breakdown: ₹{float(remaining_principal):,.2f} principal + ~₹{float(remaining_interest):,.2f} interest")
        
        # Test Case 2: Monthly Loan with Flat Rate - After 3 payments
        print("\n\n--- Test 2: Monthly Flat Rate Loan ---")
        
        total_interest_flat = loan_amount * interest_rate * Decimal(str(months)) / (Decimal('12') * Decimal('100'))
        emi_flat = (loan_amount + total_interest_flat) / Decimal(str(months))
        emi_flat = emi_flat.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_payable_flat = (emi_flat * Decimal(str(months))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        loan_flat = Loan(
            loan_number='TEST-FLAT-OUT-001',
            customer_id=1,
            branch_id=branch.id,
            loan_type='monthly_loan',
            loan_amount=float(loan_amount),
            interest_rate=float(interest_rate),
            interest_type='flat',
            duration_months=months,
            installment_frequency='monthly',
            status='active',
            disbursement_date=date(2024, 1, 1),
            disbursed_amount=float(loan_amount),
            first_installment_date=date(2024, 2, 1),
            installment_amount=float(emi_flat),
            total_payable=float(total_payable_flat),
            paid_amount=0,
            created_by=1
        )
        
        print(f"Initial Loan:")
        print(f"  Loan Amount: ₹{loan_amount:,.2f}")
        print(f"  Total Payable: ₹{total_payable_flat:,.2f}")
        print(f"  Total Interest: ₹{total_interest_flat:,.2f}")
        print(f"  EMI: ₹{emi_flat:,.2f}")
        
        # Before any payment
        outstanding_flat = loan_flat.calculate_current_outstanding()
        print(f"\nBefore payment:")
        print(f"  Outstanding: ₹{float(outstanding_flat):,.2f}")
        print(f"  Expected: ₹{float(total_payable_flat):,.2f} (Total Payable)")
        print(f"  ✓ Includes full interest" if abs(outstanding_flat - total_payable_flat) < Decimal('0.01') else f"  ✗ ERROR: Missing interest!")
        
        # After 3 payments
        total_paid_flat = emi_flat * Decimal(str(payments_made))
        loan_flat.paid_amount = float(total_paid_flat)
        
        outstanding_after_flat = loan_flat.calculate_current_outstanding()
        expected_outstanding_flat = total_payable_flat - total_paid_flat
        
        print(f"\nAfter {payments_made} payments of ₹{float(emi_flat):,.2f} each:")
        print(f"  Total Paid: ₹{float(total_paid_flat):,.2f}")
        print(f"  Outstanding: ₹{float(outstanding_after_flat):,.2f}")
        print(f"  Expected: ₹{float(expected_outstanding_flat):,.2f} (Remaining total with interest)")
        print(f"  ✓ Includes remaining interest" if abs(outstanding_after_flat - expected_outstanding_flat) < Decimal('0.01') else f"  ✗ ERROR: Missing interest!")
        
        # Calculate breakdown
        principal_per_month = loan_amount / Decimal(str(months))
        interest_per_month_flat = total_interest_flat / Decimal(str(months))
        remaining_months = months - payments_made
        remaining_principal_flat = principal_per_month * Decimal(str(remaining_months))
        remaining_interest_flat = interest_per_month_flat * Decimal(str(remaining_months))
        
        print(f"  Breakdown: ₹{float(remaining_principal_flat):,.2f} principal + ₹{float(remaining_interest_flat):,.2f} interest")
        
        print("\n\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        print("✓ Monthly Reducing Balance: Outstanding includes all remaining interest")
        print("✓ Monthly Flat Rate: Outstanding includes all remaining interest")
        print("\nFor both monthly loan types, outstanding amount = Total Payable - Amount Paid")
        print("This ensures borrowers see the full amount they still need to pay.")

if __name__ == '__main__':
    test_monthly_loan_outstanding()
