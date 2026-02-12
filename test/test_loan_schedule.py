"""
Test the Loan model's generate_payment_schedule method with both reducing balance and flat rate
"""
import sys
sys.path.insert(0, '/Users/kevinbrinsly/JaanNetworkProjects/JaanMicro')

from app import create_app, db
from app.models import Loan, Customer, Branch
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date

# Create app context
app = create_app()

def test_monthly_loan_schedule():
    """Test monthly loan payment schedule generation"""
    with app.app_context():
        print("=" * 80)
        print("TESTING MONTHLY LOAN PAYMENT SCHEDULE GENERATION")
        print("=" * 80)
        
        # Test Case 1: Monthly Loan with Reducing Balance
        print("\n" + "=" * 80)
        print("TEST 1: Monthly Loan with Reducing Balance")
        print("=" * 80)
        
        # Get a sample branch (or create one if needed)
        branch = Branch.query.first()
        if not branch:
            print("No branch found. Please create a branch first.")
            return
        
        # Create a test loan object (not saving to database)
        loan_rb = Loan(
            loan_number='TEST-RB-001',
            customer_id=1,  # Assuming customer 1 exists
            branch_id=branch.id,
            loan_type='monthly_loan',
            loan_amount=100000,
            interest_rate=12,
            interest_type='reducing_balance',
            duration_months=12,
            installment_frequency='monthly',
            status='disbursed',
            disbursement_date=date(2024, 1, 1),
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
        
        print(f"Loan Amount: ₹{loan_rb.loan_amount:,.2f}")
        print(f"Interest Rate: {loan_rb.interest_rate}% per annum")
        print(f"Interest Type: {loan_rb.interest_type}")
        print(f"Duration: {loan_rb.duration_months} months")
        print(f"EMI: ₹{loan_rb.installment_amount:,.2f}")
        print(f"Total Payable: ₹{loan_rb.total_payable:,.2f}")
        print(f"Total Interest: ₹{loan_rb.total_payable - loan_rb.loan_amount:,.2f}")
        
        # Generate schedule
        schedule = loan_rb.generate_payment_schedule()
        
        print(f"\n--- PAYMENT SCHEDULE ---")
        print(f"{'#':<4} {'Due Date':<12} {'EMI':<12} {'Principal':<12} {'Interest':<12} {'Balance':<12}")
        print("-" * 80)
        
        total_emi = 0
        total_principal = 0
        total_interest = 0
        outstanding = loan_rb.loan_amount
        
        for inst in schedule:
            total_emi += inst['amount']
            total_principal += inst['principal']
            total_interest += inst['interest']
            outstanding -= inst['principal']
            
            print(f"{inst['installment_number']:<4} "
                  f"{inst['due_date'].strftime('%Y-%m-%d'):<12} "
                  f"₹{inst['amount']:<11,.2f} "
                  f"₹{inst['principal']:<11,.2f} "
                  f"₹{inst['interest']:<11,.2f} "
                  f"₹{outstanding:<11,.2f}")
        
        print("-" * 80)
        print(f"{'TOTAL':<17} ₹{total_emi:<11,.2f} ₹{total_principal:<11,.2f} ₹{total_interest:<11,.2f}")
        
        # Verify calculations
        print(f"\n--- VERIFICATION ---")
        print(f"Expected Total Payable: ₹{loan_rb.total_payable:,.2f}")
        print(f"Calculated Total EMI: ₹{total_emi:,.2f}")
        print(f"Difference: ₹{abs(loan_rb.total_payable - total_emi):,.2f}")
        
        # Test Case 2: Monthly Loan with Flat Rate
        print("\n\n" + "=" * 80)
        print("TEST 2: Monthly Loan with Flat Rate")
        print("=" * 80)
        
        loan_flat = Loan(
            loan_number='TEST-FLAT-001',
            customer_id=1,
            branch_id=branch.id,
            loan_type='monthly_loan',
            loan_amount=100000,
            interest_rate=12,
            interest_type='flat',
            duration_months=12,
            installment_frequency='monthly',
            status='disbursed',
            disbursement_date=date(2024, 1, 1),
            first_installment_date=date(2024, 2, 1),
            created_by=1
        )
        
        # Calculate flat rate EMI
        loan_amount_flat = Decimal('100000')
        interest_rate_flat = Decimal('12')
        total_interest_flat = loan_amount_flat * interest_rate_flat * Decimal('12') / (Decimal('12') * Decimal('100'))
        emi_flat = (loan_amount_flat + total_interest_flat) / Decimal('12')
        emi_flat = emi_flat.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_payable_flat = (emi_flat * Decimal('12')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        loan_flat.installment_amount = float(emi_flat)
        loan_flat.total_payable = float(total_payable_flat)
        loan_flat.paid_amount = 0
        
        print(f"Loan Amount: ₹{loan_flat.loan_amount:,.2f}")
        print(f"Interest Rate: {loan_flat.interest_rate}% per annum")
        print(f"Interest Type: {loan_flat.interest_type}")
        print(f"Duration: {loan_flat.duration_months} months")
        print(f"EMI: ₹{loan_flat.installment_amount:,.2f}")
        print(f"Total Payable: ₹{loan_flat.total_payable:,.2f}")
        print(f"Total Interest: ₹{loan_flat.total_payable - loan_flat.loan_amount:,.2f}")
        
        # Generate schedule
        schedule_flat = loan_flat.generate_payment_schedule()
        
        print(f"\n--- PAYMENT SCHEDULE ---")
        print(f"{'#':<4} {'Due Date':<12} {'EMI':<12} {'Principal':<12} {'Interest':<12} {'Balance':<12}")
        print("-" * 80)
        
        total_emi_flat = 0
        total_principal_flat = 0
        total_interest_flat = 0
        outstanding_flat = loan_flat.loan_amount
        
        for inst in schedule_flat:
            total_emi_flat += inst['amount']
            total_principal_flat += inst['principal']
            total_interest_flat += inst['interest']
            outstanding_flat -= inst['principal']
            
            print(f"{inst['installment_number']:<4} "
                  f"{inst['due_date'].strftime('%Y-%m-%d'):<12} "
                  f"₹{inst['amount']:<11,.2f} "
                  f"₹{inst['principal']:<11,.2f} "
                  f"₹{inst['interest']:<11,.2f} "
                  f"₹{outstanding_flat:<11,.2f}")
        
        print("-" * 80)
        print(f"{'TOTAL':<17} ₹{total_emi_flat:<11,.2f} ₹{total_principal_flat:<11,.2f} ₹{total_interest_flat:<11,.2f}")
        
        # Verify calculations
        print(f"\n--- VERIFICATION ---")
        print(f"Expected Total Payable: ₹{loan_flat.total_payable:,.2f}")
        print(f"Calculated Total EMI: ₹{total_emi_flat:,.2f}")
        print(f"Difference: ₹{abs(loan_flat.total_payable - total_emi_flat):,.2f}")
        
        # Comparison
        print("\n\n" + "=" * 80)
        print("COMPARISON: Reducing Balance vs Flat Rate")
        print("=" * 80)
        print(f"{'Parameter':<30} {'Reducing Balance':<20} {'Flat Rate':<20}")
        print("-" * 80)
        print(f"{'Loan Amount':<30} ₹{loan_rb.loan_amount:<19,.2f} ₹{loan_flat.loan_amount:<19,.2f}")
        print(f"{'EMI':<30} ₹{loan_rb.installment_amount:<19,.2f} ₹{loan_flat.installment_amount:<19,.2f}")
        print(f"{'Total Interest':<30} ₹{total_interest:<19,.2f} ₹{total_interest_flat:<19,.2f}")
        print(f"{'Total Payable':<30} ₹{loan_rb.total_payable:<19,.2f} ₹{loan_flat.total_payable:<19,.2f}")
        print(f"{'Interest %':<30} {(total_interest/loan_rb.loan_amount*100):<19.2f}% {(total_interest_flat/loan_flat.loan_amount*100):<19.2f}%")
        
        print("\n✓ Tests completed successfully!")

if __name__ == '__main__':
    test_monthly_loan_schedule()
