"""Helper functions"""
import os
import uuid
from datetime import datetime
from flask import current_app, session
from werkzeug.utils import secure_filename
from app.models import Customer, Loan, Investment, Pawning, Branch

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def generate_customer_id(prefix='CUST'):
    """Generate unique customer ID"""
    last_customer = Customer.query.order_by(Customer.id.desc()).first()
    if last_customer:
        last_number = int(last_customer.customer_id.replace(prefix, ''))
        new_number = last_number + 1
    else:
        new_number = 1
    
    return f"{prefix}{new_number:06d}"

def generate_loan_number(prefix='LN'):
    """Generate unique loan number"""
    last_loan = Loan.query.order_by(Loan.id.desc()).first()
    if last_loan:
        last_number = int(last_loan.loan_number.replace(prefix, ''))
        new_number = last_number + 1
    else:
        new_number = 1
    
    return f"{prefix}{new_number:06d}"

def generate_investment_number(prefix='INV'):
    """Generate unique investment number"""
    last_investment = Investment.query.order_by(Investment.id.desc()).first()
    if last_investment:
        last_number = int(last_investment.investment_number.replace(prefix, ''))
        new_number = last_number + 1
    else:
        new_number = 1
    
    return f"{prefix}{new_number:06d}"

def generate_pawning_number(prefix='PWN'):
    """Generate unique pawning number"""
    last_pawning = Pawning.query.order_by(Pawning.id.desc()).first()
    if last_pawning:
        last_number = int(last_pawning.pawning_number.replace(prefix, ''))
        new_number = last_number + 1
    else:
        new_number = 1
    
    return f"{prefix}{new_number:06d}"

def format_currency(amount, currency_symbol='Rs.'):
    """Format amount as currency"""
    if amount is None:
        return f"{currency_symbol} 0.00"
    return f"{currency_symbol} {amount:,.2f}"

def calculate_age(birth_date):
    """Calculate age from birth date"""
    if not birth_date:
        return None
    
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def save_uploaded_file(file, folder, filename_prefix=None):
    """Save uploaded file and return the path"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        
        if filename_prefix:
            filename = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.{file_extension}"
        else:
            filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Create directory if it doesn't exist
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Return relative path for database storage
        return os.path.join(folder, filename)
    
    return None

def get_current_branch():
    """Get the current branch for the logged-in user"""
    branch_id = session.get('current_branch_id')
    if branch_id:
        return Branch.query.get(branch_id)
    return None

def get_current_branch_id():
    """Get the current branch ID for filtering queries"""
    return session.get('current_branch_id')

def should_filter_by_branch():
    """Check if current user should have branch filtering applied"""
    from flask_login import current_user
    from flask import session
    
    if not current_user.is_authenticated:
        return True
    
    if current_user.role == 'admin':
        # Admin can choose to filter by a specific branch or see all
        return session.get('current_branch_id') is not None
    
    # Regular users always filter by their assigned branch
    return True
