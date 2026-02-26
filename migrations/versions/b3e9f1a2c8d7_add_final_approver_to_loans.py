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


if __name__ == '__main__':
    import sys
    import os

    # Add the project root to the path so we can import the app
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    sys.path.insert(0, project_root)

    try:
        from app import create_app, db
        from sqlalchemy import inspect, text

        app = create_app()
        with app.app_context():
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('loans')]

            if 'final_approver_id' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE loans ADD COLUMN final_approver_id INTEGER'))
                    conn.commit()
                print('SUCCESS: Column "final_approver_id" added to the loans table.')
            else:
                print('INFO: Column "final_approver_id" already exists — no changes made.')

    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)
