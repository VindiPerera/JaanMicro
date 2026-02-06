#!/usr/bin/env python3
"""Create sample arrears loan for testing"""

from app import create_app, db
from app.models import Loan, Customer, Branch, User, LoanPayment
from datetime import date, timedelta
from decimal import Decimal

app = create_app('development')
with app.app_context():
    # Get existing data
    branch = Branch.query.first()
    customer = Customer.query.first()
    user = User.query.filter_by(role='admin').first()

    if not branch or not customer or not user:
        print('Missing required data')
        exit(1)

    print(f'Using branch: {branch.name}')
    print(f'Using customer: {customer.full_name}')
    print(f'Using user: {user.username}')

    # Create a sample loan in arrears
    import random
    loan_number = f'ARREARS-{random.randint(1000, 9999)}'
    loan = Loan(
        loan_number=loan_number,
        customer_id=customer.id,
        branch_id=branch.id,
        loan_type='Type 1 - 9 week loan',
        loan_amount=Decimal('50000.00'),
        interest_rate=Decimal('10.00'),
        interest_type='flat',
        duration_months=3,
        duration_weeks=9,
        installment_amount=Decimal('6111.11'),
        installment_frequency='weekly',
        disbursed_amount=Decimal('50000.00'),
        total_payable=Decimal('55000.00'),
        paid_amount=Decimal('18333.33'),
        outstanding_amount=Decimal('36666.67'),
        penalty_amount=Decimal('1000.00'),
        application_date=date.today() - timedelta(days=120),
        approval_date=date.today() - timedelta(days=115),
        disbursement_date=date.today() - timedelta(days=110),
        first_installment_date=date.today() - timedelta(days=103),
        maturity_date=date.today() - timedelta(days=10),  # Past due - 10 days ago
        status='active',
        approved_by=user.id,
        created_by=user.id,
        purpose='Sample arrears loan for testing arrears report'
    )

    db.session.add(loan)
    db.session.commit()

    # Add some payments (3 out of 9 installments paid)
    payment1 = LoanPayment(
        loan_id=loan.id,
        payment_date=date.today() - timedelta(days=100),
        payment_amount=Decimal('6111.11'),
        principal_amount=Decimal('5555.56'),
        interest_amount=Decimal('555.55'),
        penalty_amount=Decimal('0.00'),
        payment_method='cash',
        collected_by=user.id,
        notes='First payment'
    )
    
    payment2 = LoanPayment(
        loan_id=loan.id,
        payment_date=date.today() - timedelta(days=93),
        payment_amount=Decimal('6111.11'),
        principal_amount=Decimal('5555.56'),
        interest_amount=Decimal('555.55'),
        penalty_amount=Decimal('0.00'),
        payment_method='cash',
        collected_by=user.id,
        notes='Second payment'
    )
    
    payment3 = LoanPayment(
        loan_id=loan.id,
        payment_date=date.today() - timedelta(days=86),
        payment_amount=Decimal('6111.11'),
        collected_by=user.id,
        notes='Third payment'
    )

    db.session.add_all([payment1, payment2, payment3])
    db.session.commit()

    print(f'\nCreated sample arrears loan: {loan.loan_number}')
    print(f'Customer: {customer.full_name}')
    print(f'Loan Amount: LKR {loan.loan_amount}')
    print(f'Disbursement Date: {loan.disbursement_date}')
    print(f'Maturity Date: {loan.maturity_date} (Overdue by {(date.today() - loan.maturity_date).days} days)')
    print(f'Installments: 9 weekly payments of LKR {loan.installment_amount}')
    print(f'Payments Made: 3 installments (LKR {loan.paid_amount})')
    print(f'Outstanding Principal: LKR {loan.outstanding_amount - loan.penalty_amount}')
    print(f'Penalty: LKR {loan.penalty_amount}')
    print(f'Total Arrears Expected: LKR {loan.outstanding_amount + loan.penalty_amount}')

    # Calculate expected arrears values
    disbursed = Decimal(str(loan.disbursed_amount))
    principal_paid = loan.get_total_paid_principal()
    outstanding_principal = disbursed - principal_paid
    interest_paid = loan.get_total_paid_interest()
    total_expected_interest = loan.get_total_expected_interest()
    remaining_interest = total_expected_interest - interest_paid
    penalty = Decimal(str(loan.penalty_amount or 0))
    total_arrears = outstanding_principal + remaining_interest + penalty

    print(f'\nCalculated Arrears Breakdown:')
    print(f'Outstanding Principal: LKR {outstanding_principal}')
    print(f'Remaining Interest: LKR {remaining_interest}')
    print(f'Penalty: LKR {penalty}')
    print(f'Total Arrears: LKR {total_arrears}')