"""
Simple test to demonstrate monthly loan outstanding calculation includes interest
"""
from decimal import Decimal, ROUND_HALF_UP

def test_monthly_loan_outstanding_logic():
    """Test the logic for calculating outstanding with interest"""
    
    print("=" * 80)
    print("MONTHLY LOAN OUTSTANDING CALCULATION - INCLUDES INTEREST")
    print("=" * 80)
    
    # Test Case 1: Reducing Balance
    print("\n--- Test 1: Monthly Reducing Balance ---")
    
    loan_amount = Decimal('100000')
    interest_rate = Decimal('12')
    months = 12
    
    # Calculate EMI
    monthly_rate = interest_rate / (Decimal('12') * Decimal('100'))
    mr_float = float(monthly_rate)
    power_calc = ((1 + mr_float) ** months) / (((1 + mr_float) ** months) - 1)
    emi = loan_amount * monthly_rate * Decimal(str(power_calc))
    emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_payable = (emi * Decimal(str(months))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_interest = total_payable - loan_amount
    
    print(f"Loan Amount: ₹{loan_amount:,.2f}")
    print(f"Interest Rate: {interest_rate}% per annum")
    print(f"Duration: {months} months")
    print(f"EMI: ₹{emi:,.2f}")
    print(f"Total Payable: ₹{total_payable:,.2f}")
    print(f"Total Interest: ₹{total_interest:,.2f}")
    
    # Scenario: After 3 EMI payments
    payments_made = 3
    total_paid = emi * Decimal(str(payments_made))
    
    # Outstanding calculation: Total Payable - Total Paid
    outstanding = total_payable - total_paid
    
    print(f"\nAfter {payments_made} payments:")
    print(f"  Amount Paid: ₹{total_paid:,.2f}")
    print(f"  Outstanding: ₹{outstanding:,.2f}")
    print(f"\n  This includes:")
    print(f"    • Remaining principal to be paid")
    print(f"    • ALL remaining interest to be paid over {months - payments_made} months")
    print(f"  ✓ Borrower knows exact total amount remaining")
    
    # Test Case 2: Flat Rate
    print("\n\n--- Test 2: Monthly Flat Rate ---")
    
    total_interest_flat = loan_amount * interest_rate * Decimal(str(months)) / (Decimal('12') * Decimal('100'))
    total_payable_flat = loan_amount + total_interest_flat
    emi_flat = (total_payable_flat / Decimal(str(months))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    print(f"Loan Amount: ₹{loan_amount:,.2f}")
    print(f"Interest Rate: {interest_rate}% per annum")
    print(f"Duration: {months} months")
    print(f"EMI: ₹{emi_flat:,.2f}")
    print(f"Total Payable: ₹{total_payable_flat:,.2f}")
    print(f"Total Interest: ₹{total_interest_flat:,.2f}")
    
    # Scenario: After 3 EMI payments
    total_paid_flat = emi_flat * Decimal(str(payments_made))
    
    # Outstanding calculation: Total Payable - Total Paid
    outstanding_flat = total_payable_flat - total_paid_flat
    
    # Break down remaining
    remaining_principal = (loan_amount / Decimal(str(months))) * Decimal(str(months - payments_made))
    remaining_interest = (total_interest_flat / Decimal(str(months))) * Decimal(str(months - payments_made))
    
    print(f"\nAfter {payments_made} payments:")
    print(f"  Amount Paid: ₹{total_paid_flat:,.2f}")
    print(f"  Outstanding: ₹{outstanding_flat:,.2f}")
    print(f"\n  This includes:")
    print(f"    • Remaining principal: ₹{remaining_principal:,.2f}")
    print(f"    • Remaining interest: ₹{remaining_interest:,.2f}")
    print(f"  ✓ Borrower knows exact total amount remaining")
    
    # Comparison
    print("\n\n" + "=" * 80)
    print("KEY POINT: OUTSTANDING = TOTAL PAYABLE - AMOUNT PAID")
    print("=" * 80)
    print("\nFor MONTHLY LOANS (both types):")
    print("  Outstanding Amount = (Principal + Interest Still Owed)")
    print("\nThis gives borrowers the complete picture:")
    print("  ✓ Shows full remaining obligation")
    print("  ✓ Includes all future interest to be paid")
    print("  ✓ Not just current principal or accrued interest")
    
    print("\n\n" + "=" * 80)
    print("OTHER LOAN TYPES (Type 1, 54 Daily, Type 4, etc.)")
    print("=" * 80)
    print("  • Unchanged - use existing calculation logic")
    print("  • Only monthly_loan type is affected by this fix")

if __name__ == '__main__':
    test_monthly_loan_outstanding_logic()
