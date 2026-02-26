"""
apply_migrations.py
-------------------
Comprehensive migration script that ensures every column required by the
current models.py exists in the production SQLite database.

It inspects each table, adds any missing columns, creates any missing tables,
and finally stamps the Alembic version so `flask db upgrade` stays in sync.

Safe to re-run – columns that already exist are silently skipped.

Usage (on the server):
    cd /var/www/html/JaanMicro
    source venv/bin/activate
    python apply_migrations.py
"""

import sqlite3
import os
import sys

# ── Configuration ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'instance', 'jaanmicro.db')

# Latest Alembic revision that this script brings the DB up to
LATEST_REVISION = 'b3e9f1a2c8d7'

# ── Every column that should exist, grouped by table ──────────────────────────
# Format: (table, column, SQL_type_with_default)
# These are only columns that were added AFTER the initial migration.
# The script will ADD them only if they are missing.

REQUIRED_COLUMNS = [
    # ── users ──────────────────────────────────────────────────────────────
    ('users', 'nic_number',              'VARCHAR(20)'),
    ('users', 'can_verify_kyc',          'BOOLEAN DEFAULT 0'),
    ('users', 'branch_id',              'INTEGER'),
    ('users', 'role',                    "VARCHAR(50) DEFAULT 'staff'"),

    # ── customers ──────────────────────────────────────────────────────────
    ('customers', 'profile_picture',     'VARCHAR(255)'),
    ('customers', 'bank_book_image',     'VARCHAR(255)'),
    ('customers', 'bank_name',           'VARCHAR(100)'),
    ('customers', 'bank_branch',         'VARCHAR(100)'),
    ('customers', 'bank_account_number', 'VARCHAR(30)'),
    ('customers', 'bank_account_type',   'VARCHAR(30)'),
    ('customers', 'customer_type',       "TEXT DEFAULT '[\"customer\"]'"),

    # ── loans ──────────────────────────────────────────────────────────────
    ('loans', 'loan_purpose',            'VARCHAR(50)'),
    ('loans', 'duration_weeks',          'INTEGER'),
    ('loans', 'duration_days',           'INTEGER'),
    ('loans', 'advance_balance',         'NUMERIC(15,2) DEFAULT 0'),
    ('loans', 'documentation_fee',       'NUMERIC(15,2) DEFAULT 0'),
    ('loans', 'closing_date',            'DATE'),
    ('loans', 'drive_link',              'VARCHAR(500)'),
    ('loans', 'document_path',           'VARCHAR(255)'),
    ('loans', 'referred_by',             'INTEGER'),

    # Multi-stage approval workflow
    ('loans', 'staff_approved_by',       'INTEGER'),
    ('loans', 'staff_approval_date',     'DATE'),
    ('loans', 'staff_approval_notes',    'TEXT'),
    ('loans', 'manager_approved_by',     'INTEGER'),
    ('loans', 'manager_approval_date',   'DATE'),
    ('loans', 'manager_approval_notes',  'TEXT'),
    ('loans', 'admin_approved_by',       'INTEGER'),
    ('loans', 'admin_approval_date',     'DATE'),
    ('loans', 'admin_approval_notes',    'TEXT'),
    ('loans', 'rejection_reason',        'TEXT'),

    # Deactivation
    ('loans', 'deactivation_reason',     'TEXT'),
    ('loans', 'deactivation_date',       'DATE'),
    ('loans', 'deactivated_by',          'INTEGER'),

    # Final approver (newest)
    ('loans', 'final_approver_id',       'INTEGER'),

    # ── loan_payments ──────────────────────────────────────────────────────
    ('loan_payments', 'receipt_number',  'VARCHAR(100)'),
    ('loan_payments', 'balance_after',   'NUMERIC(15,2)'),

    # ── loan_schedule_overrides ────────────────────────────────────────────
    ('loan_schedule_overrides', 'reschedule_date', 'DATE'),
]

# ── Tables that should exist (created fresh if missing) ───────────────────────
CREATE_TABLES = [
    (
        'loan_schedule_overrides',
        """
        CREATE TABLE IF NOT EXISTS loan_schedule_overrides (
            id INTEGER NOT NULL PRIMARY KEY,
            loan_id INTEGER NOT NULL,
            installment_number INTEGER NOT NULL,
            custom_due_date DATE,
            is_skipped BOOLEAN DEFAULT 0,
            reschedule_date DATE,
            created_by INTEGER NOT NULL,
            created_at DATETIME DEFAULT (datetime('now')),
            updated_by INTEGER,
            updated_at DATETIME DEFAULT (datetime('now')),
            notes TEXT,
            FOREIGN KEY(loan_id) REFERENCES loans(id),
            FOREIGN KEY(created_by) REFERENCES users(id),
            FOREIGN KEY(updated_by) REFERENCES users(id)
        )
        """
    ),
    (
        'regional_manager_branches',
        """
        CREATE TABLE IF NOT EXISTS regional_manager_branches (
            user_id INTEGER NOT NULL,
            branch_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, branch_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(branch_id) REFERENCES branches(id)
        )
        """
    ),
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):
    print(f'  {msg}')

def ok(msg):
    print(f'  ✅  {msg}')

def skip(msg):
    print(f'  ⏭️   {msg}')

def err(msg):
    print(f'  ❌  {msg}', file=sys.stderr)

def column_exists(cursor, table, column):
    cursor.execute(f'PRAGMA table_info({table})')
    return any(row[1] == column for row in cursor.fetchall())

def table_exists(cursor, table):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cursor.fetchone() is not None

def get_current_revision(cursor):
    if not table_exists(cursor, 'alembic_version'):
        return None
    cursor.execute('SELECT version_num FROM alembic_version')
    row = cursor.fetchone()
    return row[0] if row else None

def set_revision(cursor, revision_id):
    if not table_exists(cursor, 'alembic_version'):
        cursor.execute(
            'CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)'
        )
    cursor.execute('DELETE FROM alembic_version')
    cursor.execute(
        'INSERT INTO alembic_version (version_num) VALUES (?)', (revision_id,)
    )

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print('=' * 64)
    print('  JaanMicro – Comprehensive Migration Script')
    print('=' * 64)

    if not os.path.exists(DB_PATH):
        err(f'Database not found at: {DB_PATH}')
        err('Make sure the Flask app has been initialised first.')
        sys.exit(1)

    log(f'Database : {DB_PATH}')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    current_rev = get_current_revision(cursor)
    log(f'Current Alembic revision : {current_rev or "(none)"}')
    print()

    added = 0
    skipped_count = 0
    errors = 0

    # ── 1. Create any missing tables ──────────────────────────────────────
    print('  ── Step 1: Ensure tables exist ──')
    for tbl_name, create_sql in CREATE_TABLES:
        if table_exists(cursor, tbl_name):
            skip(f'Table `{tbl_name}` already exists')
        else:
            try:
                cursor.execute(create_sql)
                conn.commit()
                ok(f'Table `{tbl_name}` created')
                added += 1
            except sqlite3.OperationalError as exc:
                err(f'Failed to create table `{tbl_name}`: {exc}')
                errors += 1
    print()

    # ── 2. Add any missing columns ────────────────────────────────────────
    print('  ── Step 2: Ensure columns exist ──')
    for tbl, col, sql_type in REQUIRED_COLUMNS:
        if not table_exists(cursor, tbl):
            skip(f'Table `{tbl}` does not exist – skipping `{col}`')
            skipped_count += 1
            continue

        if column_exists(cursor, tbl, col):
            skip(f'`{tbl}.{col}` already exists')
            skipped_count += 1
        else:
            sql = f'ALTER TABLE {tbl} ADD COLUMN {col} {sql_type}'
            try:
                cursor.execute(sql)
                conn.commit()
                ok(f'`{tbl}.{col}` added  ({sql_type})')
                added += 1
            except sqlite3.OperationalError as exc:
                err(f'Failed: `{tbl}.{col}` – {exc}')
                errors += 1

    print()

    # ── 3. Stamp Alembic version ──────────────────────────────────────────
    print('  ── Step 3: Stamp Alembic version ──')
    try:
        set_revision(cursor, LATEST_REVISION)
        conn.commit()
        ok(f'Alembic version stamped → {LATEST_REVISION}')
    except Exception as exc:
        err(f'Failed to stamp version: {exc}')
        errors += 1

    conn.close()

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    print('=' * 64)
    if errors > 0:
        print(f'  ⚠️  Completed with {errors} ERROR(s)!')
    elif added > 0:
        print(f'  ✅  SUCCESS: {added} change(s) applied, {skipped_count} already up-to-date')
    else:
        print(f'  ✅  Nothing to do – database is already up-to-date ({skipped_count} columns checked)')
    print(f'  Final Alembic revision : {LATEST_REVISION}')
    print('=' * 64)
    print()

    sys.exit(1 if errors > 0 else 0)

if __name__ == '__main__':
    main()
