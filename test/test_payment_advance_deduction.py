import unittest
from decimal import Decimal

from app.loans.routes import _resolve_payment_amount_with_optional_advance


class TestPaymentAdvanceDeduction(unittest.TestCase):
    def test_full_installment_with_advance_deducts_cash_collection(self):
        amount, auto_applied = _resolve_payment_amount_with_optional_advance(
            posted_amount=Decimal('10667.00'),
            use_advance_credit=True,
            installment_amount=Decimal('10667.00'),
            advance_to_apply=Decimal('333.00'),
        )
        self.assertEqual(amount, Decimal('10334.00'))
        self.assertTrue(auto_applied)

    def test_custom_amount_is_not_overridden(self):
        amount, auto_applied = _resolve_payment_amount_with_optional_advance(
            posted_amount=Decimal('9000.00'),
            use_advance_credit=True,
            installment_amount=Decimal('10667.00'),
            advance_to_apply=Decimal('333.00'),
        )
        self.assertEqual(amount, Decimal('9000.00'))
        self.assertFalse(auto_applied)

    def test_disabled_advance_keeps_full_amount(self):
        amount, auto_applied = _resolve_payment_amount_with_optional_advance(
            posted_amount=Decimal('10667.00'),
            use_advance_credit=False,
            installment_amount=Decimal('10667.00'),
            advance_to_apply=Decimal('333.00'),
        )
        self.assertEqual(amount, Decimal('10667.00'))
        self.assertFalse(auto_applied)

    def test_advance_capped_by_installment(self):
        amount, auto_applied = _resolve_payment_amount_with_optional_advance(
            posted_amount=Decimal('1000.00'),
            use_advance_credit=True,
            installment_amount=Decimal('1000.00'),
            advance_to_apply=Decimal('1500.00'),
        )
        self.assertEqual(amount, Decimal('0.00'))
        self.assertTrue(auto_applied)

    def test_installment_tolerance_still_auto_applies(self):
        amount, auto_applied = _resolve_payment_amount_with_optional_advance(
            posted_amount=Decimal('10667.03'),
            use_advance_credit=True,
            installment_amount=Decimal('10667.00'),
            advance_to_apply=Decimal('333.00'),
        )
        self.assertEqual(amount, Decimal('10334.00'))
        self.assertTrue(auto_applied)


if __name__ == '__main__':
    unittest.main()
