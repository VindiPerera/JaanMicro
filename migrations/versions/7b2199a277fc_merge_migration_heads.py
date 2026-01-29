"""Merge migration heads

Revision ID: 7b2199a277fc
Revises: 5178112a3f36, dfcedfc3b4cd
Create Date: 2026-01-29 13:53:21.433114

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b2199a277fc'
down_revision = ('5178112a3f36', 'dfcedfc3b4cd')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
