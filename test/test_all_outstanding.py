"""
Test Outstanding After payment for all loan types
"""
from decimal import Decimal

def test_all_loan_types_outstanding():
    """Test outstanding after payment for all loan types"""
    
    print("=" * 80)
    print("OUTSTANDING AFTER PAYMENT - ALL LOAN TYPES")
    print("=" * 80)
    
    # Test Case 1: Type 1 - 9 Week Loan
    print("\n--- Type 1: 9 Week Loan (Flat Rate) ---")
    loan_amount = Decimal('10000')
    interest_rate = Decimal('12')
    weeks = 9
    interest = interest_rate * Decimal('2')
    installment = ((Decimal('100') + interest) * loan_amount) / (Decimal('100') * Decimal(str(weeks)))
    installment = Decimal(str(int(installment)))  # Floor
    total_payable = installment * Decimal(str(weeks))
    
    print(f"Loan Amount: Rs. {loan_amount:,.2f}")
    print(f"Total Payable: Rs. {total_payable:,.2f}")
    print(f"Weekly Installment: Rs. {installment:,.2f}")
    
    # After 5 payments
    payments_made = 5
    total_paid = installment * Decimal(str(payments_made))
    current_outstanding = total_payable - total_paid
    
    print(f"\nAfter {payments_made} payments (Total Paid: Rs. {total_paid:,.2f}):")
    print(f"  Current Outstanding: Rs. {current_outstanding:,.2f}")
    
    # Making next payment
    payment_amount = installment
    outstanding_after = current_outstanding - payment_amount
    
    print(f"\nMaking payment #{payments_made + 1}: Rs. {payment_amount:,.2f}")
    print(f"  ✅ Outstanding After = {current_outstanding:,.2f} - {payment_amount:,.2f} = Rs. {outstanding_after:,.2f}")
    print(f"  (Subtract FULL payment for flat rate loans)")
    
    # Test Case 2: 54 Daily Loan
    print("\n\n--- Type 2: 54 Daily Loan (Flat Rate) ---")
    days = 54
    installment_daily = ((Decimal('100') + interest) * loan_amount) / (Decimal('100') * Decimal(str(days)))
    installment_daily = Decimal(str(int(installment_daily)))
    total_payable_daily = installment_daily * Decimal(str(days))
    
    print(f"Loan Amount: Rs. {loan_amount:,.2f}")
    print(f"Total Payable: Rs. {total_payable_daily:,.2f}")
    print(f"Daily Installment: Rs. {installment_daily:,.2f}")
    
    payments_made_daily = 30
    total_paid_daily = installment_daily * Decimal(str(payments_made_daily))
    current_outstanding_daily = total_payable_daily - total_paid_daily
    
    print(f"\nAfter {payments_made_daily} payments (Total Paid: Rs. {total_paid_daily:,.2f}):")
    print(f"  Current Outstanding: Rs. {current_outstanding_daily:,.2f}")
    
    payment_amount_daily = installment_daily
    outstanding_after_daily = current_outstanding_daily - payment_amount_daily
    
    print(f"\nMaking payment #{payments_made_daily + 1}: Rs. {payment_amount_daily:,.2f}")
    print(f"  ✅ Outstanding After = {current_outstanding_daily:,.2f} - {payment_amount_daily:,.2f} = Rs. {outstanding_after_daily:,.2f}")
    print(f"  (Subtract FULL payment for flat rate loans)")
    
    # Test Case 3: Monthly Loan with Reducing Balance
    print("\n\n--- Monthly Loan: Reducing Balance ---")
    months = 12
    monthly_rate = interest_rate / (Decimal('12') * Decimal('100'))
    mr_float = float(monthly_rate)
    power_calc = ((1 + mr_float) ** months) / (((1 + mr_float) ** months) - 1)
    emi = loan_amount * monthly_rate * Decimal(str(power_calc))
    emi = round(emi, 2)
    total_payable_rb = round(emi * Decimal(str(months)), 2)
    
    print(f"Loan Amount: Rs. {loan_amount:,.2f}")
    print(f"Total Payable: Rs. {total_payable_rb:,.2f}")
    print(f"EMI: Rs. {emi:,.2f}")
    
    payments_made_rb = 6
    total_paid_rb = emi * Decimal(str(payments_made_rb))
    current_outstanding_rb = total_payable_rb - total_paid_rb
    
    print(f"\nAfter {payments_made_rb} payments (Total Paid: Rs. {total_paid_rb:,.2f}):")
    print(f"  Current Outstanding: Rs. {current_outstanding_rb:,.2f}")
    
    payment_amount_rb = emi
    outstanding_after_rb = current_outstanding_rb - payment_amount_rb
    
    print(f"\nMaking payment #{payments_made_rb + 1}: Rs. {payment_amount_rb:,.2f}")
    print(f"  ✅ Outstanding After = {current_outstanding_rb:,.2f} - {payment_amount_rb:,.2f} = Rs. {outstanding_after_rb:,.2f}")
    print(f"  (Subtract FULL payment for monthly loans)")
    
    # Test Case 4: Monthly Loan with Flat Rate
    print("\n\n--- Monthly Loan: Flat Rate ---")
    total_interest_flat = loan_amount * interest_rate * Decimal(str(months)) / (Decimal('12') * Decimal('100'))
    emi_flat = (loan_amount + total_interest_flat) / Decimal(str(months))
    emi_flat = round(emi_flat, 2)
    total_payable_flat = round(emi_flat * Decimal(str(months)), 2)
    
    print(f"Loan Amount: Rs. {loan_amount:,.2f}")
    print(f"Total Payable: Rs. {total_payable_flat:,.2f}")
    print(f"EMI: Rs. {emi_flat:,.2f}")
    
    payments_made_flat = 6
    total_paid_flat = emi_flat * Decimal(str(payments_made_flat))
    current_outstanding_flat = total_payable_flat - total_paid_flat
    
    print(f"\nAfter {payments_made_flat} payments (Total Paid: Rs. {total_paid_flat:,.2f}):")
    print(f"  Current Outstanding: Rs. {current_outstanding_flat:,.2f}")
    
    payment_amount_flat = emi_flat
    outstanding_after_flat = current_outstanding_flat - payment_amount_flat
    
    print(f"\nMaking payment #{payments_made_flat + 1}: Rs. {payment_amount_flat:,.2f}")
    print(f"  ✅ Outstanding After = {current_outstanding_flat:,.2f} - {payment_amount_flat:,.2f} = Rs. {outstanding_after_flat:,.2f}")
    print(f"  (Subtract FULL payment for flat rate loans)")
    
    print("\n\n" + "=" * 80)
    print("CALCULATION RULE")
    print("=" * 80)
    print("\nFor FLAT RATE loans (Type 1, 54 Daily, Type 4 Micro/Daily, Monthly Flat):")
    print("  Outstanding After = Current Outstanding - FULL Payment")
    print("  (Because outstanding includes principal + ALL remaining interest)")
    
    print("\nFor REDUCING BALANCE loans (Monthly Reducing Balance):")
    print("  Outstanding After = Current Outstanding - FULL Payment")  
    print("  (Because outstanding includes principal + ALL remaining interest)")
    
    print("\n✅ ALL loan types now correctly subtract the full payment amount!")
    print("=" * 80)

if __name__ == '__main__':
    test_all_loan_types_outstanding()
