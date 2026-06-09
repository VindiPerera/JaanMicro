"""Schedule checks for 54 daily loan variants."""
from datetime import date
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.models import Loan  # noqa: E402


class DailyLoanScheduleTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def _loan(self, loan_type):
        return Loan(
            loan_number=f'TEST-{loan_type}',
            customer_id=1,
            branch_id=1,
            loan_type=loan_type,
            loan_amount=1000,
            interest_rate=10,
            interest_type='flat',
            duration_days=4,
            duration_months=0,
            installment_amount=300,
            installment_frequency='daily',
            total_payable=1200,
            paid_amount=0,
            status='active',
            first_installment_date=date(2026, 6, 12),  # Friday
            created_by=1,
        )

    def test_original_54_daily_includes_saturday_and_skips_sunday(self):
        schedule = self._loan('54_daily').generate_payment_schedule()

        self.assertEqual(
            [item['due_date'] for item in schedule],
            [
                date(2026, 6, 12),  # Friday
                date(2026, 6, 13),  # Saturday
                date(2026, 6, 15),  # Monday
                date(2026, 6, 16),  # Tuesday
            ],
        )

    def test_monday_friday_54_daily_skips_saturday_and_sunday(self):
        schedule = self._loan('54_daily_monday_friday').generate_payment_schedule()

        self.assertEqual(
            [item['due_date'] for item in schedule],
            [
                date(2026, 6, 12),  # Friday
                date(2026, 6, 15),  # Monday
                date(2026, 6, 16),  # Tuesday
                date(2026, 6, 17),  # Wednesday
            ],
        )


if __name__ == '__main__':
    unittest.main()
