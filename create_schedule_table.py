"""Manually create loan_schedule_overrides table"""
from app import db, create_app
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Check if table exists
    result = db.session.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='loan_schedule_overrides'"
    ))
    table_exists = result.fetchone() is not None
    
    if not table_exists:
        print("Creating loan_schedule_overrides table...")
        
        # Create the table
        db.session.execute(text("""
            CREATE TABLE loan_schedule_overrides (
                id INTEGER NOT NULL PRIMARY KEY,
                loan_id INTEGER NOT NULL,
                installment_number INTEGER NOT NULL,
                custom_due_date DATE,
                is_skipped BOOLEAN,
                created_by INTEGER NOT NULL,
                created_at DATETIME,
                updated_by INTEGER,
                updated_at DATETIME,
                notes TEXT,
                FOREIGN KEY(created_by) REFERENCES users (id),
                FOREIGN KEY(loan_id) REFERENCES loans (id),
                FOREIGN KEY(updated_by) REFERENCES users (id),
                CONSTRAINT unique_loan_installment_override UNIQUE (loan_id, installment_number)
            )
        """))
        
        # Create index
        db. session.execute(text(
            "CREATE INDEX ix_loan_schedule_overrides_loan_id ON loan_schedule_overrides (loan_id)"
        ))
        
        db.session.commit()
        print("Table created successfully!")
    else:
        print("Table already exists!")
