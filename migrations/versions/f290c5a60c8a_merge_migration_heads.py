"""Merge migration heads

Revision ID: f290c5a60c8a
Revises: 6f560e6847da, cc9ecdea3fb3
Create Date: 2026-02-06 12:00:06.348217

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f290c5a60c8a'
down_revision = ('6f560e6847da', 'cc9ecdea3fb3')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
