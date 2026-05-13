"""Add can_view_borrowings_report permission to users

Revision ID: f6c2a1b4d1e2
Revises: a4d5a7a1d431
Create Date: 2026-05-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6c2a1b4d1e2'
down_revision = 'a4d5a7a1d431'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'can_view_borrowings_report',
                sa.Boolean(),
                nullable=True,
                server_default=sa.text('0')
            )
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('can_view_borrowings_report')


if __name__ == '__main__':
    import sys
    import os

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, project_root)

    try:
        from app import create_app, db
        from sqlalchemy import inspect, text

        app = create_app()
        with app.app_context():
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]

            if 'can_view_borrowings_report' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        'ALTER TABLE users ADD COLUMN can_view_borrowings_report BOOLEAN DEFAULT 0'
                    ))
                    conn.commit()
                print('SUCCESS: Column "can_view_borrowings_report" added to users table.')
            else:
                print('INFO: Column "can_view_borrowings_report" already exists - no changes made.')

    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)
