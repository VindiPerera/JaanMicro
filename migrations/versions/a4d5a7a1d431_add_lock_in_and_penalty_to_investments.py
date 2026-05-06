"""add_lock_in_and_penalty_to_investments

Revision ID: a4d5a7a1d431
Revises: b3e9f1a2c8d7
Create Date: 2026-04-27 15:34:06.422898

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4d5a7a1d431'
down_revision = 'b3e9f1a2c8d7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('investments', sa.Column('lock_in_period', sa.Integer(), nullable=True))
    op.add_column('investments', sa.Column('early_withdrawal_penalty', sa.Numeric(precision=15, scale=2), nullable=True))


def downgrade():
    op.drop_column('investments', 'early_withdrawal_penalty')
    op.drop_column('investments', 'lock_in_period')
