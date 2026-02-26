"""add_final_approver_to_loans

Revision ID: b3e9f1a2c8d7
Revises: 076bc2b4d0f1
Create Date: 2026-02-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3e9f1a2c8d7'
down_revision = '076bc2b4d0f1'
branch_labels = None
depends_on = None


def upgrade():
    # Add final_approver_id column to loans table
    # This stores the designated Admin or Accountant user who must do the final approval
    op.add_column('loans', sa.Column('final_approver_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('loans', 'final_approver_id')
