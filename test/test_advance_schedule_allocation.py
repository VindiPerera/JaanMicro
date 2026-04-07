"""Regression coverage for advance-credit display in loan schedules."""
from datetime import date
from decimal import Decimal
import unittest

from app import create_app, db
from app.models import Branch, Customer, Loan, LoanPayment, User


class AdvanceScheduleAllocationTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        user = User(
            username='admin',
            email='admin@example.com',
            password_hash='test',
            full_name='Admin User',
            nic_number='ADMIN-NIC',
            role='admin',
        )
        branch = Branch(branch_code='B001', name='Main Branch')
        db.session.add_all([user, branch])
        db.session.flush()

        customer = Customer(
            customer_id='C001',
            branch_id=branch.id,
            full_name='Test Customer',
            nic_number='CUSTOMER-NIC',
            phone_primary='0710000000',
            address_line1='Address',
            city='Colombo',
            district='Colombo',
            created_by=user.id,
        )
        db.session.add(customer)
        db.session.flush()

        self.loan = Loan(
            loan_number='TEST-ADV-001',
            customer_id=customer.id,
            branch_id=branch.id,
            loan_type='type1_9weeks',
            loan_amount=Decimal('80000.00'),
            disbursed_amount=Decimal('80000.00'),
            total_payable=Decimal('96000.00'),
            paid_amount=Decimal('21667.00'),
            outstanding_amount=Decimal('74333.00'),
            advance_balance=Decimal('333.00'),
            interest_rate=Decimal('10.00'),
            interest_type='reducing_balance',
            duration_months=0,
            duration_weeks=9,
            installment_amount=Decimal('10667.00'),
            installment_frequency='weekly',
            status='active',
            application_date=date(2026, 4, 7),
            disbursement_date=date(2026, 4, 7),
            first_installment_date=date(2026, 4, 14),
            maturity_date=date(2026, 6, 9),
            created_by=user.id,
        )
        db.session.add(self.loan)
        db.session.flush()

        db.session.add_all([
            LoanPayment(
                loan_id=self.loan.id,
                payment_date=date(2026, 4, 14),
                payment_amount=Decimal('11000.00'),
                principal_amount=Decimal('10333.33'),
                interest_amount=Decimal('666.67'),
                penalty_amount=Decimal('0.00'),
                balance_after=Decimal('85000.00'),
                payment_method='cash',
            ),
            LoanPayment(
                loan_id=self.loan.id,
                payment_date=date(2026, 4, 21),
                payment_amount=Decimal('10667.00'),
                principal_amount=Decimal('10086.44'),
                interest_amount=Decimal('580.56'),
                penalty_amount=Decimal('0.00'),
                balance_after=Decimal('74333.00'),
                payment_method='cash',
            ),
        ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def test_advance_credit_is_applied_to_next_paid_installment(self):
        schedule = self.loan.generate_payment_schedule()

        # Installment view is "amount applied to this installment", not raw
        # receipt amount. Any excess is tracked as advance carried.
        self.assertEqual(schedule[0]['paid_amount'], 10667.0)
        self.assertEqual(schedule[0]['cash_paid_amount'], 10667.0)
        self.assertEqual(schedule[0]['cash_received_on_due_date'], 11000.0)
        self.assertEqual(schedule[0]['advance_applied_amount'], 0.0)
        self.assertEqual(schedule[0]['advance_generated_amount'], 333.0)

        self.assertEqual(schedule[1]['paid_amount'], 10667.0)
        self.assertEqual(schedule[1]['cash_paid_amount'], 10334.0)
        self.assertEqual(schedule[1]['cash_received_on_due_date'], 10667.0)
        self.assertEqual(schedule[1]['advance_applied_amount'], 333.0)
        self.assertEqual(schedule[1]['advance_generated_amount'], 333.0)
        self.assertEqual(schedule[1]['remaining_amount'], 0.0)
        self.assertEqual(schedule[1]['status'], 'paid')

        self.assertEqual(schedule[2]['paid_amount'], 0.0)
        self.assertEqual(schedule[2]['remaining_amount'], 10667.0)
        self.assertEqual(self.loan.get_next_installment_amount(), 10334.0)


if __name__ == '__main__':
    unittest.main()
