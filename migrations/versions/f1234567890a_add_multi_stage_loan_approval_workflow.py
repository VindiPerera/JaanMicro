"""add_multi_stage_loan_approval_workflow

Revision ID: f1234567890a
Revises: eb7e3d3d31df
Create Date: 2026-01-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1234567890a'
down_revision = 'eb7e3d3d31df'
branch_labels = None
depends_on = None


def upgrade():
    # Add new multi-stage approval fields to loans table
    # For SQLite, we need to add columns one at a time
    
    # Staff approval fields
    op.add_column('loans', sa.Column('staff_approved_by', sa.Integer(), nullable=True))
    op.add_column('loans', sa.Column('staff_approval_date', sa.Date(), nullable=True))
    op.add_column('loans', sa.Column('staff_approval_notes', sa.Text(), nullable=True))
    
    # Manager approval fields
    op.add_column('loans', sa.Column('manager_approved_by', sa.Integer(), nullable=True))
    op.add_column('loans', sa.Column('manager_approval_date', sa.Date(), nullable=True))
    op.add_column('loans', sa.Column('manager_approval_notes', sa.Text(), nullable=True))
    
    # Admin approval fields
    op.add_column('loans', sa.Column('admin_approved_by', sa.Integer(), nullable=True))
    op.add_column('loans', sa.Column('admin_approval_date', sa.Date(), nullable=True))
    op.add_column('loans', sa.Column('admin_approval_notes', sa.Text(), nullable=True))
    
    # Rejection reason field
    op.add_column('loans', sa.Column('rejection_reason', sa.Text(), nullable=True))
    
    # Note: approval_date column already exists, so we skip adding it
    # Note: SQLite doesn't support modifying column types easily, status VARCHAR(20) will work for new statuses


def downgrade():
    # Remove multi-stage approval fields from loans table
    op.drop_column('loans', 'rejection_reason')
    op.drop_column('loans', 'admin_approval_notes')
    op.drop_column('loans', 'admin_approval_date')
    op.drop_column('loans', 'admin_approved_by')
    op.drop_column('loans', 'manager_approval_notes')
    op.drop_column('loans', 'manager_approval_date')
    op.drop_column('loans', 'manager_approved_by')
    op.drop_column('loans', 'staff_approval_notes')
    op.drop_column('loans', 'staff_approval_date')
    op.drop_column('loans', 'staff_approved_by')
