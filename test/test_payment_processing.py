"""
Test payment processing for monthly loans with reducing balance and flat rate interest
"""
import sys
sys.path.insert(0, '/Users/kevinbrinsly/JaanNetworkProjects/JaanMicro')

from app import create_app, db
from app.models import Loan, LoanPayment, Branch
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date

# Create app context
app = create_app()

def test_payment_processing():
    """Test payment processing for both reducing balance and flat rate loans"""
    with app.app_context():
        print("=" * 80)
        print("TESTING PAYMENT PROCESSING FOR MONTHLY LOANS")
        print("=" * 80)
        
        # Get a sample branch
        branch = Branch.query.first()
        if not branch:
            print("No branch found. Please create a branch first.")
            return
        
        # Test Case 1: Reducing Balance Loan - Make 3 payments
        print("\n" + "=" * 80)
        print("TEST 1: Reducing Balance Loan - 3 Payments")
        print("=" * 80)
        
        # Create test loan
        loan_rb = Loan(
            loan_number='TEST-RB-PAY-001',
            customer_id=1,
            branch_id=branch.id,
            loan_type='monthly_loan',
            loan_amount=100000,
            interest_rate=12,
            interest_type='reducing_balance',
            duration_months=12,
            installment_frequency='monthly',
            status='active',
            disbursement_date=date(2024, 1, 1),
            disbursed_amount=100000,
            first_installment_date=date(2024, 2, 1),
            created_by=1
        )
        
        # Calculate EMI
        loan_amount = Decimal('100000')
        interest_rate = Decimal('12')
        monthly_rate = interest_rate / (Decimal('12') * Decimal('100'))
        n = 12
        mr_float = float(monthly_rate)
        power_calc = ((1 + mr_float) ** n) / (((1 + mr_float) ** n) - 1)
        emi = loan_amount * monthly_rate * Decimal(str(power_calc))
        emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_payable = (emi * Decimal(str(n))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        loan_rb.installment_amount = float(emi)
        loan_rb.total_payable = float(total_payable)
        loan_rb.paid_amount = 0
        loan_rb.outstanding_amount = float(loan_amount)
        
        print(f"Initial Loan Details:")
        print(f"  Loan Amount: ₹{loan_rb.loan_amount:,.2f}")
        print(f"  Interest Rate: {loan_rb.interest_rate}% per annum")
        print(f"  EMI: ₹{loan_rb.installment_amount:,.2f}")
        print(f"  Total Payable: ₹{loan_rb.total_payable:,.2f}")
        
        # Get payment schedule
        schedule = loan_rb.generate_payment_schedule()
        
        print(f"\n--- PAYMENT SCHEDULE (First 3 Months) ---")
        print(f"{'#':<4} {'EMI':<12} {'Principal':<12} {'Interest':<12}")
        print("-" * 45)
        for i in range(3):
            inst = schedule[i]
            print(f"{inst['installment_number']:<4} "
                  f"₹{inst['amount']:<11,.2f} "
                  f"₹{inst['principal']:<11,.2f} "
                  f"₹{inst['interest']:<11,.2f}")
        
        print("\n--- SIMULATING PAYMENTS ---")
        
        # Simulate making 3 payments
        outstanding = Decimal(str(loan_rb.disbursed_amount))
        total_paid = Decimal('0')
        
        for payment_num in range(1, 4):
            payment_amount = emi
            
            # Calculate interest on current outstanding
            interest = (outstanding * monthly_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            principal = payment_amount - interest
            
            outstanding = (outstanding - principal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_paid += payment_amount
            
            print(f"\nPayment {payment_num}:")
            print(f"  Payment Amount: ₹{float(payment_amount):,.2f}")
            print(f"  Interest: ₹{float(interest):,.2f}")
            print(f"  Principal: ₹{float(principal):,.2f}")
            print(f"  Remaining Balance: ₹{float(outstanding):,.2f}")
        
        print(f"\nTotal Paid: ₹{float(total_paid):,.2f}")
        print(f"Remaining Outstanding: ₹{float(outstanding):,.2f}")
        
        # Test Case 2: Flat Rate Loan - Make 3 payments
        print("\n\n" + "=" * 80)
        print("TEST 2: Flat Rate Loan - 3 Payments")
        print("=" * 80)
        
        loan_flat = Loan(
            loan_number='TEST-FLAT-PAY-001',
            customer_id=1,
            branch_id=branch.id,
            loan_type='monthly_loan',
            loan_amount=100000,
            interest_rate=12,
            interest_type='flat',
            duration_months=12,
            installment_frequency='monthly',
            status='active',
            disbursement_date=date(2024, 1, 1),
            disbursed_amount=100000,
            first_installment_date=date(2024, 2, 1),
            created_by=1
        )
        
        # Calculate flat rate EMI
        loan_amount_flat = Decimal('100000')
        total_interest_flat = loan_amount_flat * interest_rate * Decimal('12') / (Decimal('12') * Decimal('100'))
        emi_flat = (loan_amount_flat + total_interest_flat) / Decimal('12')
        emi_flat = emi_flat.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_payable_flat = (emi_flat * Decimal('12')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        loan_flat.installment_amount = float(emi_flat)
        loan_flat.total_payable = float(total_payable_flat)
        loan_flat.paid_amount = 0
        loan_flat.outstanding_amount = float(loan_amount_flat)
        
        print(f"Initial Loan Details:")
        print(f"  Loan Amount: ₹{loan_flat.loan_amount:,.2f}")
        print(f"  Interest Rate: {loan_flat.interest_rate}% per annum")
        print(f"  EMI: ₹{loan_flat.installment_amount:,.2f}")
        print(f"  Total Payable: ₹{loan_flat.total_payable:,.2f}")
        
        # Get payment schedule
        schedule_flat = loan_flat.generate_payment_schedule()
        
        print(f"\n--- PAYMENT SCHEDULE (First 3 Months) ---")
        print(f"{'#':<4} {'EMI':<12} {'Principal':<12} {'Interest':<12}")
        print("-" * 45)
        for i in range(3):
            inst = schedule_flat[i]
            print(f"{inst['installment_number']:<4} "
                  f"₹{inst['amount']:<11,.2f} "
                  f"₹{inst['principal']:<11,.2f} "
                  f"₹{inst['interest']:<11,.2f}")
        
        print("\n--- SIMULATING PAYMENTS ---")
        
        # For flat rate, interest per installment is fixed
        interest_per_installment = total_interest_flat / Decimal('12')
        principal_per_installment = loan_amount_flat / Decimal('12')
        
        outstanding_flat = loan_amount_flat
        total_paid_flat = Decimal('0')
        total_payable_remaining = Decimal(str(loan_flat.total_payable))
        
        for payment_num in range(1, 4):
            payment_amount_flat = emi_flat
            
            interest_flat = interest_per_installment
            principal_flat = principal_per_installment
            
            outstanding_flat = (outstanding_flat - principal_flat).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_paid_flat += payment_amount_flat
            total_payable_remaining -= payment_amount_flat
            
            print(f"\nPayment {payment_num}:")
            print(f"  Payment Amount: ₹{float(payment_amount_flat):,.2f}")
            print(f"  Interest: ₹{float(interest_flat):,.2f}")
            print(f"  Principal: ₹{float(principal_flat):,.2f}")
            print(f"  Remaining Principal: ₹{float(outstanding_flat):,.2f}")
            print(f"  Remaining Total Payable: ₹{float(total_payable_remaining):,.2f}")
        
        print(f"\nTotal Paid: ₹{float(total_paid_flat):,.2f}")
        print(f"Remaining Principal: ₹{float(outstanding_flat):,.2f}")
        print(f"Remaining Total Payable: ₹{float(total_payable_remaining):,.2f}")
        
        # Comparison
        print("\n\n" + "=" * 80)
        print("KEY DIFFERENCES IN PAYMENT PROCESSING")
        print("=" * 80)
        print("\nREDUCING BALANCE:")
        print("  - Interest calculated on CURRENT outstanding balance")
        print("  - Interest decreases with each payment")
        print("  - Principal increases with each payment")
        print("  - After 3 payments of ₹8,884.88 each:")
        print(f"    • Total Paid: ₹{float(total_paid):,.2f}")
        print(f"    • Remaining: ₹{float(outstanding):,.2f}")
        
        print("\nFLAT RATE:")
        print("  - Interest calculated on ORIGINAL loan amount and fixed")
        print("  - Interest same for each payment")
        print("  - Principal same for each payment")
        print("  - After 3 payments of ₹9,333.33 each:")
        print(f"    • Total Paid: ₹{float(total_paid_flat):,.2f}")
        print(f"    • Remaining Principal: ₹{float(outstanding_flat):,.2f}")
        print(f"    • Remaining Total Payable: ₹{float(total_payable_remaining):,.2f}")
        
        print("\n✓ Payment processing tests completed successfully!")

if __name__ == '__main__':
    test_payment_processing()
