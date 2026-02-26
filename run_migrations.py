"""
run_migrations.py
-----------------
Executes pending column migrations on the production database.

Migrations:
  1. 076bc2b4d0f1 – adds `advance_balance` to loans
  2. b3e9f1a2c8d7 – adds `final_approver_id` to loans

Usage:
    cd /var/www/html/JaanMicro
    source venv/bin/activate
    python run_migrations.py
"""

import sys
import os

# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

MIGRATIONS = [
    {
        'revision': '076bc2b4d0f1',
        'table': 'loans',
        'column': 'advance_balance',
        'sql': 'ALTER TABLE loans ADD COLUMN advance_balance DECIMAL(15,2) DEFAULT 0',
        'description': 'Add advance_balance column to loans',
    },
    {
        'revision': 'b3e9f1a2c8d7',
        'table': 'loans',
        'column': 'final_approver_id',
        'sql': 'ALTER TABLE loans ADD COLUMN final_approver_id INTEGER',
        'description': 'Add final_approver_id column to loans',
    },
]


def main():
    print()
    print('=' * 60)
    print('  JaanMicro – Run Pending Migrations')
    print('=' * 60)
    print()

    try:
        from app import create_app, db
        from sqlalchemy import inspect, text
    except ImportError as e:
        print(f'  ❌ ERROR: {e}')
        print('  Make sure you activated the venv first:')
        print('    source venv/bin/activate')
        sys.exit(1)

    app = create_app()
    added = 0
    skipped = 0
    errors = 0

    with app.app_context():
        inspector = inspect(db.engine)

        for mig in MIGRATIONS:
            columns = [c['name'] for c in inspector.get_columns(mig['table'])]
            label = f"{mig['table']}.{mig['column']}"

            print(f"  [{mig['revision']}] {mig['description']}")

            if mig['column'] in columns:
                print(f"  ⏭️   SKIP: `{label}` already exists")
                skipped += 1
            else:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text(mig['sql']))
                        conn.commit()
                    print(f"  ✅  SUCCESS: `{label}` added")
                    added += 1
                except Exception as e:
                    print(f"  ❌  ERROR: `{label}` – {e}")
                    errors += 1

            print()

    # Summary
    print('=' * 60)
    if errors > 0:
        print(f'  ⚠️  Completed with {errors} error(s)!')
    elif added > 0:
        print(f'  ✅  Done! {added} column(s) added, {skipped} already existed.')
    else:
        print(f'  ✅  Database already up-to-date. Nothing to do.')
    print('=' * 60)
    print()
    
    if errors > 0:
        print('  ⚠️  Fix the errors above, then run again.')
    else:
        print('  Now restart the service:')
        print('    sudo systemctl restart jaanmicro')
    print()

    sys.exit(1 if errors > 0 else 0)


if __name__ == '__main__':
    main()
