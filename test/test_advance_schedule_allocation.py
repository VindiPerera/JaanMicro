"""Regression coverage for advance-credit display in loan schedules."""
from datetime import date, timedelta
from decimal import Decimal
import unittest

from app import create_app, db
from app.models import Branch, Customer, Loan, LoanPayment, LoanScheduleOverride, User


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

        self.assertEqual(schedule[2]['paid_amount'], 333.0)
        self.assertEqual(schedule[2]['cash_paid_amount'], 0.0)
        self.assertEqual(schedule[2]['advance_applied_amount'], 333.0)
        self.assertEqual(schedule[2]['remaining_amount'], 10334.0)
        self.assertEqual(schedule[2]['status'], 'partial')
        self.assertEqual(self.loan.calculate_available_advance_balance(schedule=schedule), Decimal('0.00'))
        self.assertEqual(self.loan.get_next_installment_amount(), 10334.0)

    def test_prepaid_future_installments_remain_paid_after_last_receipt_date(self):
        prepaid_loan = Loan(
            loan_number='TEST-ADV-002',
            customer_id=self.loan.customer_id,
            branch_id=self.loan.branch_id,
            loan_type='type1_9weeks',
            loan_amount=Decimal('2500.00'),
            disbursed_amount=Decimal('2500.00'),
            total_payable=Decimal('3000.00'),
            paid_amount=Decimal('3000.00'),
            outstanding_amount=Decimal('0.00'),
            advance_balance=Decimal('0.00'),
            interest_rate=Decimal('10.00'),
            interest_type='flat',
            duration_months=0,
            duration_weeks=3,
            installment_amount=Decimal('1000.00'),
            installment_frequency='weekly',
            status='completed',
            application_date=date(2026, 4, 1),
            disbursement_date=date(2026, 4, 1),
            first_installment_date=date(2026, 4, 1),
            maturity_date=date(2026, 4, 15),
            created_by=self.loan.created_by,
        )
        db.session.add(prepaid_loan)
        db.session.flush()

        db.session.add(LoanPayment(
            loan_id=prepaid_loan.id,
            payment_date=date(2026, 4, 1),
            payment_amount=Decimal('3000.00'),
            principal_amount=Decimal('2500.00'),
            interest_amount=Decimal('500.00'),
            penalty_amount=Decimal('0.00'),
            balance_after=Decimal('0.00'),
            payment_method='cash',
        ))
        db.session.commit()

        schedule = prepaid_loan.generate_payment_schedule()
        self.assertEqual([inst['status'] for inst in schedule], ['paid', 'paid', 'paid'])
        self.assertEqual([inst['paid_amount'] for inst in schedule], [1000.0, 1000.0, 1000.0])

    def test_advance_balance_matches_schedule_with_skipped_installment(self):
        skipped_loan = Loan(
            loan_number='TEST-ADV-003',
            customer_id=self.loan.customer_id,
            branch_id=self.loan.branch_id,
            loan_type='type1_9weeks',
            loan_amount=Decimal('20000.00'),
            disbursed_amount=Decimal('20000.00'),
            total_payable=Decimal('24000.00'),
            paid_amount=Decimal('10800.00'),
            outstanding_amount=Decimal('13200.00'),
            advance_balance=Decimal('0.00'),
            interest_rate=Decimal('10.00'),
            interest_type='flat',
            duration_months=0,
            duration_weeks=9,
            installment_amount=Decimal('2667.00'),
            installment_frequency='weekly',
            status='active',
            application_date=date(2026, 3, 6),
            disbursement_date=date(2026, 3, 6),
            first_installment_date=date(2026, 3, 6),
            maturity_date=date(2026, 5, 8),
            created_by=self.loan.created_by,
        )
        db.session.add(skipped_loan)
        db.session.flush()

        db.session.add(LoanScheduleOverride(
            loan_id=skipped_loan.id,
            installment_number=1,
            is_skipped=True,
            created_by=self.loan.created_by,
            notes='Regression setup',
        ))

        db.session.add_all([
            LoanPayment(
                loan_id=skipped_loan.id,
                payment_date=date(2026, 3, 11),
                payment_amount=Decimal('2700.00'),
                principal_amount=Decimal('2300.00'),
                interest_amount=Decimal('400.00'),
                penalty_amount=Decimal('0.00'),
                balance_after=Decimal('21300.00'),
                payment_method='cash',
            ),
            LoanPayment(
                loan_id=skipped_loan.id,
                payment_date=date(2026, 3, 18),
                payment_amount=Decimal('2700.00'),
                principal_amount=Decimal('2300.00'),
                interest_amount=Decimal('400.00'),
                penalty_amount=Decimal('0.00'),
                balance_after=Decimal('18600.00'),
                payment_method='cash',
            ),
            LoanPayment(
                loan_id=skipped_loan.id,
                payment_date=date(2026, 3, 25),
                payment_amount=Decimal('2700.00'),
                principal_amount=Decimal('2300.00'),
                interest_amount=Decimal('400.00'),
                penalty_amount=Decimal('0.00'),
                balance_after=Decimal('15900.00'),
                payment_method='cash',
            ),
            LoanPayment(
                loan_id=skipped_loan.id,
                payment_date=date(2026, 4, 1),
                payment_amount=Decimal('2700.00'),
                principal_amount=Decimal('2300.00'),
                interest_amount=Decimal('400.00'),
                penalty_amount=Decimal('0.00'),
                balance_after=Decimal('13200.00'),
                payment_method='cash',
            ),
        ])
        db.session.commit()

        schedule = skipped_loan.generate_payment_schedule()
        first_partial = next(
            inst for inst in schedule if not inst.get('is_skipped') and inst['status'] == 'partial'
        )
        self.assertEqual(first_partial['advance_brought_amount'], 132.0)
        self.assertEqual(first_partial['advance_applied_amount'], 132.0)
        self.assertEqual(first_partial['cash_paid_amount'], 0.0)
        self.assertEqual(first_partial['remaining_amount'], 2535.0)
        self.assertEqual(skipped_loan.calculate_available_advance_balance(schedule=schedule), Decimal('0.00'))
        self.assertEqual(skipped_loan.get_next_installment_amount(), 2535.0)

    def test_rescheduled_skipped_installments_do_not_create_false_arrears(self):
        today = date.today()
        first_installment_date = today - timedelta(days=67)

        loan = Loan(
            loan_number='TEST-ADV-004',
            customer_id=self.loan.customer_id,
            branch_id=self.loan.branch_id,
            loan_type='type1_9weeks',
            loan_amount=Decimal('15000.00'),
            disbursed_amount=Decimal('15000.00'),
            total_payable=Decimal('18000.00'),
            paid_amount=Decimal('16000.00'),
            outstanding_amount=Decimal('2000.00'),
            advance_balance=Decimal('0.00'),
            interest_rate=Decimal('10.00'),
            interest_type='flat',
            duration_months=0,
            duration_weeks=9,
            installment_amount=Decimal('2000.00'),
            installment_frequency='weekly',
            status='active',
            application_date=first_installment_date,
            disbursement_date=first_installment_date,
            first_installment_date=first_installment_date,
            maturity_date=first_installment_date + timedelta(weeks=9),
            created_by=self.loan.created_by,
        )
        db.session.add(loan)
        db.session.flush()

        db.session.add_all([
            LoanScheduleOverride(
                loan_id=loan.id,
                installment_number=1,
                is_skipped=True,
                reschedule_date=today - timedelta(days=4),
                created_by=self.loan.created_by,
                notes='Rescheduled and paid on new date',
            ),
            LoanScheduleOverride(
                loan_id=loan.id,
                installment_number=9,
                is_skipped=True,
                reschedule_date=today + timedelta(days=3),
                created_by=self.loan.created_by,
                notes='Future reschedule',
            ),
        ])

        payment_dates = [
            first_installment_date + timedelta(weeks=1),
            first_installment_date + timedelta(weeks=2),
            first_installment_date + timedelta(weeks=3),
            first_installment_date + timedelta(weeks=4),
            first_installment_date + timedelta(weeks=5),
            first_installment_date + timedelta(weeks=6),
            first_installment_date + timedelta(weeks=7),
            today - timedelta(days=4),
        ]
        for payment_date in payment_dates:
            db.session.add(LoanPayment(
                loan_id=loan.id,
                payment_date=payment_date,
                payment_amount=Decimal('2000.00'),
                principal_amount=Decimal('1942.49'),
                interest_amount=Decimal('57.51'),
                penalty_amount=Decimal('0.00'),
                balance_after=Decimal('0.00'),
                payment_method='cash',
            ))

        db.session.commit()

        arrears = loan.get_arrears_details()
        self.assertEqual(arrears['total_overdue_amount'], Decimal('0'))
        self.assertEqual(arrears['overdue_installments'], 0)
        self.assertEqual(arrears['days_overdue'], 0)


if __name__ == '__main__':
    unittest.main()
