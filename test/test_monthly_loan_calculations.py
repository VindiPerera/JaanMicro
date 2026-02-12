"""
Test script to verify monthly loan calculations for reducing balance and flat rate interest
"""
from decimal import Decimal, ROUND_HALF_UP

def test_monthly_loan_calculations():
    """Test monthly loan calculations"""
    
    print("=" * 80)
    print("MONTHLY LOAN CALCULATION VERIFICATION")
    print("=" * 80)
    
    # Test Case 1: Monthly Loan with Reducing Balance
    print("\n" + "=" * 80)
    print("TEST CASE 1: Monthly Loan with Reducing Balance Interest")
    print("=" * 80)
    
    loan_amount = Decimal('100000')
    interest_rate = Decimal('12')  # 12% annual
    duration_months = 12
    
    print(f"Loan Amount: {loan_amount}")
    print(f"Interest Rate: {interest_rate}% per annum")
    print(f"Duration: {duration_months} months")
    print(f"Interest Type: Reducing Balance")
    
    # Calculate EMI using reducing balance formula
    monthly_rate = interest_rate / (Decimal('12') * Decimal('100'))
    print(f"\nMonthly Interest Rate: {monthly_rate} ({float(monthly_rate) * 100:.4f}%)")
    
    n = duration_months
    mr_float = float(monthly_rate)
    
    if mr_float > 0:
        power_calc = ((1 + mr_float) ** n) / (((1 + mr_float) ** n) - 1)
        emi = loan_amount * monthly_rate * Decimal(str(power_calc))
    else:
        emi = loan_amount / Decimal(str(n))
    
    emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_payable = (emi * Decimal(str(n))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_interest = total_payable - loan_amount
    
    print(f"\n--- CALCULATED VALUES ---")
    print(f"EMI (Monthly Installment): {emi}")
    print(f"Total Payable: {total_payable}")
    print(f"Total Interest: {total_interest}")
    print(f"Total Interest %: {(float(total_interest) / float(loan_amount) * 100):.2f}%")
    
    # Generate amortization schedule for reducing balance
    print(f"\n--- AMORTIZATION SCHEDULE (Reducing Balance) ---")
    print(f"{'Month':<6} {'EMI':<12} {'Principal':<12} {'Interest':<12} {'Balance':<12}")
    print("-" * 60)
    
    outstanding = loan_amount
    total_principal_paid = Decimal('0')
    total_interest_paid = Decimal('0')
    
    for month in range(1, duration_months + 1):
        # Calculate interest on outstanding balance
        monthly_interest = (outstanding * monthly_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Principal component
        if month == duration_months:
            # Last installment - pay off remaining
            principal = outstanding
            monthly_interest = emi - principal
        else:
            principal = (emi - monthly_interest).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Update outstanding
        outstanding = (outstanding - principal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        total_principal_paid += principal
        total_interest_paid += monthly_interest
        
        print(f"{month:<6} {float(emi):<12.2f} {float(principal):<12.2f} {float(monthly_interest):<12.2f} {float(outstanding):<12.2f}")
    
    print("-" * 60)
    print(f"{'TOTAL':<6} {float(emi * duration_months):<12.2f} {float(total_principal_paid):<12.2f} {float(total_interest_paid):<12.2f}")
    
    # Test Case 2: Monthly Loan with Flat Rate
    print("\n\n" + "=" * 80)
    print("TEST CASE 2: Monthly Loan with Flat Rate Interest")
    print("=" * 80)
    
    print(f"Loan Amount: {loan_amount}")
    print(f"Interest Rate: {interest_rate}% per annum")
    print(f"Duration: {duration_months} months")
    print(f"Interest Type: Flat Rate")
    
    # Calculate EMI using flat rate formula
    total_interest_flat = loan_amount * interest_rate * Decimal(str(duration_months)) / (Decimal('12') * Decimal('100'))
    emi_flat = (loan_amount + total_interest_flat) / Decimal(str(duration_months))
    emi_flat = emi_flat.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_payable_flat = (emi_flat * Decimal(str(duration_months))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    print(f"\n--- CALCULATED VALUES ---")
    print(f"Total Interest: {total_interest_flat}")
    print(f"EMI (Monthly Installment): {emi_flat}")
    print(f"Total Payable: {total_payable_flat}")
    print(f"Total Interest %: {(float(total_interest_flat) / float(loan_amount) * 100):.2f}%")
    
    # Generate payment schedule for flat rate
    print(f"\n--- PAYMENT SCHEDULE (Flat Rate) ---")
    print(f"{'Month':<6} {'EMI':<12} {'Principal':<12} {'Interest':<12} {'Balance':<12}")
    print("-" * 60)
    
    principal_per_month = (loan_amount / Decimal(str(duration_months))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    interest_per_month = (total_interest_flat / Decimal(str(duration_months))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    outstanding_flat = loan_amount
    total_principal_paid_flat = Decimal('0')
    total_interest_paid_flat = Decimal('0')
    
    for month in range(1, duration_months + 1):
        if month == duration_months:
            # Last installment - adjust for rounding
            principal = outstanding_flat
            interest = emi_flat - principal
        else:
            principal = principal_per_month
            interest = interest_per_month
        
        outstanding_flat = (outstanding_flat - principal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_principal_paid_flat += principal
        total_interest_paid_flat += interest
        
        print(f"{month:<6} {float(emi_flat):<12.2f} {float(principal):<12.2f} {float(interest):<12.2f} {float(outstanding_flat):<12.2f}")
    
    print("-" * 60)
    print(f"{'TOTAL':<6} {float(emi_flat * duration_months):<12.2f} {float(total_principal_paid_flat):<12.2f} {float(total_interest_paid_flat):<12.2f}")
    
    # Comparison
    print("\n\n" + "=" * 80)
    print("COMPARISON: Reducing Balance vs Flat Rate")
    print("=" * 80)
    print(f"{'Parameter':<30} {'Reducing Balance':<20} {'Flat Rate':<20}")
    print("-" * 80)
    print(f"{'EMI':<30} {float(emi):<20.2f} {float(emi_flat):<20.2f}")
    print(f"{'Total Interest':<30} {float(total_interest):<20.2f} {float(total_interest_flat):<20.2f}")
    print(f"{'Total Payable':<30} {float(total_payable):<20.2f} {float(total_payable_flat):<20.2f}")
    print(f"{'Interest % of Principal':<30} {(float(total_interest)/float(loan_amount)*100):<20.2f} {(float(total_interest_flat)/float(loan_amount)*100):<20.2f}")
    
    # Additional test cases
    print("\n\n" + "=" * 80)
    print("ADDITIONAL TEST CASES")
    print("=" * 80)
    
    test_cases = [
        {'amount': Decimal('50000'), 'rate': Decimal('18'), 'months': 6},
        {'amount': Decimal('200000'), 'rate': Decimal('15'), 'months': 24},
        {'amount': Decimal('75000'), 'rate': Decimal('10'), 'months': 18},
    ]
    
    for idx, case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {idx} ---")
        print(f"Loan Amount: {case['amount']}, Rate: {case['rate']}%, Duration: {case['months']} months")
        
        # Reducing Balance
        monthly_rate = case['rate'] / (Decimal('12') * Decimal('100'))
        n = case['months']
        mr_float = float(monthly_rate)
        power_calc = ((1 + mr_float) ** n) / (((1 + mr_float) ** n) - 1)
        emi_rb = case['amount'] * monthly_rate * Decimal(str(power_calc))
        emi_rb = emi_rb.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_rb = (emi_rb * Decimal(str(n))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        interest_rb = total_rb - case['amount']
        
        # Flat Rate
        interest_flat = case['amount'] * case['rate'] * Decimal(str(n)) / (Decimal('12') * Decimal('100'))
        emi_flat = (case['amount'] + interest_flat) / Decimal(str(n))
        emi_flat = emi_flat.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_flat = (emi_flat * Decimal(str(n))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        print(f"  Reducing Balance - EMI: {emi_rb}, Total Interest: {interest_rb}, Total: {total_rb}")
        print(f"  Flat Rate - EMI: {emi_flat}, Total Interest: {interest_flat}, Total: {total_flat}")

if __name__ == '__main__':
    test_monthly_loan_calculations()
