import unittest
from decimal import Decimal

from app.loans.routes import _get_installment_advance_breakdown


class _DummyLoan:
    def __init__(self, installment_amount, schedule, advance_balance, recommended_amount):
        self.installment_amount = installment_amount
        self._schedule = schedule
        self._advance_balance = advance_balance
        self._recommended_amount = recommended_amount

    def generate_payment_schedule(self):
        return self._schedule

    def calculate_available_advance_balance(self, schedule=None):
        return Decimal(str(self._advance_balance))

    def get_next_installment_amount(self):
        return self._recommended_amount


class TestPaymentAdvanceDeduction(unittest.TestCase):
    def test_partial_next_due_uses_remaining_cash_amount(self):
        loan = _DummyLoan(
            installment_amount=Decimal('10667.00'),
            schedule=[
                {
                    'is_skipped': False,
                    'status': 'partial',
                    'amount': 10667.0,
                    'remaining_amount': 10334.0,
                    'advance_applied_amount': 333.0,
                }
            ],
            advance_balance=Decimal('0.00'),
            recommended_amount=10334.0,
        )

        breakdown = _get_installment_advance_breakdown(loan)
        self.assertEqual(breakdown['installment_amount'], Decimal('10667.00'))
        self.assertEqual(breakdown['remaining_due_amount'], Decimal('10334.00'))
        self.assertEqual(breakdown['auto_deducted_advance'], Decimal('333.00'))
        self.assertEqual(breakdown['advance_balance'], Decimal('0.00'))

    def test_skipped_installments_are_ignored_for_next_due(self):
        loan = _DummyLoan(
            installment_amount=Decimal('2000.00'),
            schedule=[
                {
                    'is_skipped': True,
                    'status': 'overdue',
                    'amount': 2000.0,
                    'remaining_amount': 2000.0,
                    'advance_applied_amount': 0.0,
                },
                {
                    'is_skipped': False,
                    'status': 'pending',
                    'amount': 2000.0,
                    'remaining_amount': 2000.0,
                    'advance_applied_amount': 0.0,
                },
            ],
            advance_balance=Decimal('0.00'),
            recommended_amount=2000.0,
        )

        breakdown = _get_installment_advance_breakdown(loan)
        self.assertEqual(breakdown['installment_amount'], Decimal('2000.00'))
        self.assertEqual(breakdown['remaining_due_amount'], Decimal('2000.00'))
        self.assertEqual(breakdown['auto_deducted_advance'], Decimal('0.00'))

    def test_fallback_uses_recommended_amount_when_no_due_found(self):
        loan = _DummyLoan(
            installment_amount=Decimal('1000.00'),
            schedule=[],
            advance_balance=Decimal('25.00'),
            recommended_amount=700.0,
        )

        breakdown = _get_installment_advance_breakdown(loan)
        self.assertEqual(breakdown['installment_amount'], Decimal('1000.00'))
        self.assertEqual(breakdown['remaining_due_amount'], Decimal('700.00'))
        self.assertEqual(breakdown['auto_deducted_advance'], Decimal('0.00'))
        self.assertEqual(breakdown['advance_balance'], Decimal('25.00'))


if __name__ == '__main__':
    unittest.main()
