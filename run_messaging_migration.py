"""
run_messaging_migration.py
--------------------------
Runs migration 5d16b1ccafe8 – "Add internal messaging tables".

Creates two new tables:
  • messages          – stores message subjects, body, sender, and threading
  • message_recipients – tracks per-user read/star/delete state for each message

Safe to re-run: tables that already exist are skipped without modification.
The Alembic version is updated to 5d16b1ccafe8 when all steps succeed.

Usage (on the server):
    cd /var/www/html/JaanMicro
    source venv/bin/activate
    python run_messaging_migration.py
"""

import sqlite3
import os
import sys

# ── Configuration ──────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, 'instance', 'jaanmicro.db')

REVISION       = '5d16b1ccafe8'
DOWN_REVISION  = 'b3e9f1a2c8d7'   # expected predecessor

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):   print(f'  {msg}')
def ok(msg):    print(f'  ✅  {msg}')
def skip(msg):  print(f'  ⏭️   {msg}')
def warn(msg):  print(f'  ⚠️   {msg}')
def err(msg):   print(f'  ❌  {msg}', file=sys.stderr)
def debug(msg): print(f'  🔍  [DEBUG] {msg}')


def table_exists(cursor, table):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    result = cursor.fetchone() is not None
    debug(f'table_exists({table!r}) → {result}')
    return result


def index_exists(cursor, index_name):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,)
    )
    result = cursor.fetchone() is not None
    debug(f'index_exists({index_name!r}) → {result}')
    return result


def get_current_revision(cursor):
    if not table_exists(cursor, 'alembic_version'):
        debug('alembic_version table not found')
        return None
    cursor.execute('SELECT version_num FROM alembic_version')
    row = cursor.fetchone()
    rev = row[0] if row else None
    debug(f'current Alembic revision → {rev!r}')
    return rev


def set_revision(cursor, revision_id):
    if not table_exists(cursor, 'alembic_version'):
        debug('Creating alembic_version table')
        cursor.execute(
            'CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)'
        )
    cursor.execute('DELETE FROM alembic_version')
    cursor.execute(
        'INSERT INTO alembic_version (version_num) VALUES (?)', (revision_id,)
    )
    debug(f'alembic_version set to {revision_id!r}')


# ── DDL ────────────────────────────────────────────────────────────────────────

CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER NOT NULL PRIMARY KEY,
    subject    VARCHAR(255) NOT NULL,
    body       TEXT NOT NULL,
    sender_id  INTEGER NOT NULL,
    parent_id  INTEGER,
    created_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY(sender_id) REFERENCES users(id),
    FOREIGN KEY(parent_id) REFERENCES messages(id)
)
"""

CREATE_MESSAGE_RECIPIENTS = """
CREATE TABLE IF NOT EXISTS message_recipients (
    id             INTEGER NOT NULL PRIMARY KEY,
    message_id     INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    recipient_type VARCHAR(5),
    is_read        BOOLEAN DEFAULT 0,
    read_at        DATETIME,
    is_starred     BOOLEAN DEFAULT 0,
    is_deleted     BOOLEAN DEFAULT 0,
    FOREIGN KEY(message_id) REFERENCES messages(id),
    FOREIGN KEY(user_id)    REFERENCES users(id),
    UNIQUE(message_id, user_id)
)
"""

INDEXES = [
    # (index_name,  table,               column)
    ('ix_messages_created_at',              'messages',           'created_at'),
    ('ix_messages_sender_id',               'messages',           'sender_id'),
    ('ix_message_recipients_message_id',    'message_recipients', 'message_id'),
    ('ix_message_recipients_user_id',       'message_recipients', 'user_id'),
]

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print('=' * 64)
    print('  JaanMicro – Migration 5d16b1ccafe8')
    print('  Add internal messaging tables')
    print('=' * 64)
    print()

    # ── Pre-flight checks ─────────────────────────────────────────────────
    debug(f'Base directory : {BASE_DIR}')
    debug(f'Database path  : {DB_PATH}')
    print()

    if not os.path.exists(DB_PATH):
        err(f'Database not found at: {DB_PATH}')
        err('Make sure the Flask app has been initialised first.')
        sys.exit(1)

    ok(f'Database found : {DB_PATH}')

    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print()

    # ── Check current Alembic state ───────────────────────────────────────
    print('  ── Step 0: Verify Alembic revision ──')
    current_rev = get_current_revision(cursor)
    log(f'Current revision : {current_rev or "(none)"}')
    log(f'Expected base    : {DOWN_REVISION}')
    log(f'Target revision  : {REVISION}')
    print()

    if current_rev == REVISION:
        skip('Migration already applied – revision is already 5d16b1ccafe8')
        skip('Nothing to do. Exiting.')
        conn.close()
        print()
        sys.exit(0)

    if current_rev != DOWN_REVISION:
        warn(
            f'Current revision ({current_rev}) does not match the expected '
            f'predecessor ({DOWN_REVISION}).'
        )
        warn('Proceeding anyway – tables will be created if they are missing.')
        print()

    errors = 0

    # ── Step 1: Create tables ─────────────────────────────────────────────
    print('  ── Step 1: Create tables ──')

    for tbl_name, ddl in [
        ('messages',           CREATE_MESSAGES),
        ('message_recipients', CREATE_MESSAGE_RECIPIENTS),
    ]:
        debug(f'Checking table `{tbl_name}`...')
        if table_exists(cursor, tbl_name):
            skip(f'Table `{tbl_name}` already exists – skipped')
        else:
            debug(f'Executing CREATE TABLE for `{tbl_name}`')
            try:
                cursor.execute(ddl)
                conn.commit()
                ok(f'Table `{tbl_name}` created successfully')
            except sqlite3.OperationalError as exc:
                err(f'Failed to create table `{tbl_name}`: {exc}')
                errors += 1

    print()

    # ── Step 2: Create indexes ────────────────────────────────────────────
    print('  ── Step 2: Create indexes ──')

    for idx_name, tbl_name, col_name in INDEXES:
        debug(f'Checking index `{idx_name}` on `{tbl_name}.{col_name}`...')
        if index_exists(cursor, idx_name):
            skip(f'Index `{idx_name}` already exists – skipped')
        else:
            sql = f'CREATE INDEX {idx_name} ON {tbl_name} ({col_name})'
            debug(f'Executing: {sql}')
            try:
                cursor.execute(sql)
                conn.commit()
                ok(f'Index `{idx_name}` created on `{tbl_name}.{col_name}`')
            except sqlite3.OperationalError as exc:
                err(f'Failed to create index `{idx_name}`: {exc}')
                errors += 1

    print()

    # ── Step 3: Verify table structure ───────────────────────────────────
    print('  ── Step 3: Verify table structure ──')

    for tbl_name in ('messages', 'message_recipients'):
        if table_exists(cursor, tbl_name):
            cursor.execute(f'PRAGMA table_info({tbl_name})')
            columns = cursor.fetchall()
            col_names = [c[1] for c in columns]
            debug(f'Columns in `{tbl_name}`: {col_names}')
            ok(f'`{tbl_name}` has {len(columns)} column(s): {", ".join(col_names)}')
        else:
            err(f'Table `{tbl_name}` does not exist after migration – something went wrong')
            errors += 1

    print()

    # ── Step 4: Stamp Alembic version ────────────────────────────────────
    print('  ── Step 4: Stamp Alembic version ──')

    if errors == 0:
        try:
            set_revision(cursor, REVISION)
            conn.commit()
            ok(f'Alembic version stamped → {REVISION}')
        except Exception as exc:
            err(f'Failed to stamp Alembic version: {exc}')
            errors += 1
    else:
        warn(f'Skipping version stamp because {errors} error(s) occurred above.')

    conn.close()
    print()

    # ── Summary ───────────────────────────────────────────────────────────
    print('  ── Summary ──')
    if errors == 0:
        ok('Migration 5d16b1ccafe8 completed successfully.')
        ok('Internal messaging tables are ready.')
    else:
        err(f'Migration finished with {errors} error(s). Review the output above.')

    print()
    sys.exit(0 if errors == 0 else 1)


if __name__ == '__main__':
    main()
