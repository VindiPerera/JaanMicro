"""
apply_migrations.py
-------------------
Manually applies two pending Alembic migrations directly via SQLite, then
stamps the Alembic version table so `flask db upgrade` stays in sync.

Migrations applied (in order):
  1. eaddc2aa7d1f  – adds `drive_link` column to `loans`
  2. 2018cb036eaf  – adds `reschedule_date` column to `loan_schedule_overrides`

Usage (on the server):
    cd /var/www/html/JaanMicro
    source venv/bin/activate
    python apply_migrations.py
"""

import sqlite3
import os
import sys

# ── Configuration ──────────────────────────────────────────────────────────────
# Resolve database path relative to this script's directory (same as Flask does)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'instance', 'jaanmicro.db')

# Ordered list of (revision_id, description, SQL statements)
MIGRATIONS = [
    (
        'eaddc2aa7d1f',
        'add drive_link to loans',
        [
            "ALTER TABLE loans ADD COLUMN drive_link VARCHAR(500)",
        ],
    ),
    (
        '2018cb036eaf',
        'add reschedule_date to loan_schedule_overrides',
        [
            "ALTER TABLE loan_schedule_overrides ADD COLUMN reschedule_date DATE",
        ],
    ),
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):
    print(f"  {msg}")

def ok(msg):
    print(f"  [OK]  {msg}")

def warn(msg):
    print(f"  [SKIP] {msg}")

def err(msg):
    print(f"  [ERR]  {msg}", file=sys.stderr)

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def table_exists(cursor, table):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cursor.fetchone() is not None

def get_current_revision(cursor):
    """Return the current Alembic head revision, or None."""
    if not table_exists(cursor, 'alembic_version'):
        return None
    cursor.execute("SELECT version_num FROM alembic_version")
    row = cursor.fetchone()
    return row[0] if row else None

def set_revision(cursor, revision_id):
    if table_exists(cursor, 'alembic_version'):
        cursor.execute("DELETE FROM alembic_version")
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (revision_id,))
    else:
        warn("alembic_version table not found – skipping version stamp")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  JaanMicro – Manual Migration Script")
    print("=" * 60)

    # Verify database file exists
    if not os.path.exists(DB_PATH):
        err(f"Database not found at: {DB_PATH}")
        err("Check that the Flask app has been initialised (tables created) first.")
        sys.exit(1)

    log(f"Database : {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    current_rev = get_current_revision(cursor)
    log(f"Current Alembic revision : {current_rev or '(none)'}")
    print()

    applied_any = False

    for revision_id, description, statements in MIGRATIONS:
        print(f"  Migration [{revision_id}] : {description}")

        all_done = True  # assume already applied until proven otherwise

        for sql in statements:
            # Parse table/column from the ALTER TABLE statement for the check
            parts = sql.split()
            # e.g. ALTER TABLE loans ADD COLUMN drive_link VARCHAR(500)
            table  = parts[2]
            column = parts[5]

            if column_exists(cursor, table, column):
                warn(f"Column `{table}.{column}` already exists – skipping")
            else:
                log(f"Executing: {sql}")
                try:
                    cursor.execute(sql)
                    conn.commit()
                    ok(f"Column `{table}.{column}` added successfully")
                    all_done = False
                    applied_any = True
                except sqlite3.OperationalError as exc:
                    err(f"Failed to execute SQL: {exc}")
                    conn.rollback()
                    conn.close()
                    sys.exit(1)

        # Stamp the Alembic version table after each migration
        log(f"Stamping Alembic version → {revision_id}")
        set_revision(cursor, revision_id)
        conn.commit()
        ok(f"Alembic version stamped to {revision_id}")
        print()

    conn.close()

    print("=" * 60)
    if applied_any:
        print("  All migrations applied successfully!")
    else:
        print("  Nothing to do – all columns already exist.")
    print("  Final Alembic revision:", MIGRATIONS[-1][0])
    print("=" * 60)

if __name__ == '__main__':
    main()
