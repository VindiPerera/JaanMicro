"""add_regional_manager_role_and_branches

Revision ID: 09271c8a10f1
Revises: f25d532fac6e
Create Date: 2026-02-09 15:29:08.728300

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '09271c8a10f1'
down_revision = 'f25d532fac6e'
branch_labels = None
depends_on = None


def upgrade():
    # Create regional_manager_branches association table
    op.create_table('regional_manager_branches',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'branch_id')
    )


def downgrade():
    # Drop regional_manager_branches association table
    op.drop_table('regional_manager_branches')
