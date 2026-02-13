"""Test customer type update functionality"""
from app import create_app, db
from app.models import Customer
import json

app = create_app()
with app.app_context():
    # Get a sample customer
    customer = Customer.query.first()
    if customer:
        print('=== BEFORE UPDATE ===')
        print(f'Customer ID: {customer.customer_id}')
        print(f'Customer Type (raw): {repr(customer.customer_type)}')
        print(f'Customer Types (property): {customer.customer_types}')
        print(f'Customer Type Display: {customer.customer_type_display}')
        
        # Try updating customer types
        print('\n=== UPDATING ===')
        customer.customer_types = ['customer', 'investor', 'guarantor']
        print(f'After setter - raw: {repr(customer.customer_type)}')
        db.session.commit()
        
        print('\n=== AFTER COMMIT ===')
        db.session.refresh(customer)
        print(f'Customer Type (raw): {repr(customer.customer_type)}')
        print(f'Customer Types (property): {customer.customer_types}')
        print(f'Customer Type Display: {customer.customer_type_display}')
        
        # Revert back
        print('\n=== REVERTING ===')
        customer.customer_types = ['customer']
        db.session.commit()
        print(f'Reverted to: {customer.customer_types}')
