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

def generate_customer_id(customer_type='customer', branch_id=None):
    """Generate unique customer ID based on type and branch"""
    # Get branch code
    if branch_id:
        try:
            branch = Branch.query.get(branch_id)
            branch_code = branch.branch_code if branch else 'BR'
        except:
            # Handle case where database is not available (e.g., testing)
            branch_code = f'BR{branch_id}'
    else:
        branch_code = 'BR'
    
    # Define prefixes based on customer type
    type_prefixes = {
        'customer': 'C',
        'investor': 'LB',  # Loan Borrower
        'guarantor': 'G',
        'family_guarantor': 'FG'
    }
    
    prefix = type_prefixes.get(customer_type, 'C')
    
    # Find the last customer of this type in this branch
    try:
        last_customer = Customer.query.filter(
            Customer.customer_type.like(f'%{customer_type}%'),
            Customer.branch_id == branch_id
        ).order_by(Customer.id.desc()).first()
        
        if last_customer and last_customer.customer_id.startswith(f"{branch_code}/{prefix}/"):
            # Extract the number from the existing ID
            try:
                last_number = int(last_customer.customer_id.split('/')[-1])
                new_number = last_number + 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            new_number = 1
    except:
        # Handle case where database is not available (e.g., testing)
        new_number = 1
    
    return f"{branch_code}/{prefix}/{new_number:04d}"

def get_loan_type_code(loan_type):
    """Map loan type to its code
    
    Args:
        loan_type: Loan type string from form (e.g., 'type1_9weeks', '54_daily', etc.)
    
    Returns:
        Loan type code (e.g., 'WS', 'DLS', 'MF', 'DL', 'ML')
    """
    loan_type_mapping = {
        'type1_9weeks': 'WS',      # 9 Week Loan - Weekly Short
        '54_daily': 'DLS',         # 54 Daily Loan - Daily Long Short
        'type4_micro': 'MF',       # Micro Loan - Micro Finance
        'type4_daily': 'DL',       # Daily Loan - Daily
        'monthly_loan': 'ML'       # Monthly Loan - Monthly
    }
    
    return loan_type_mapping.get(loan_type, 'ML')  # Default to ML if type not found

def generate_loan_number(loan_type=None, branch_id=None):
    """Generate unique loan number in format YY/B##/TYPE/#####
    
    Args:
        loan_type: Type of loan (e.g., 'type1_9weeks', '54_daily', etc.)
        branch_id: Branch ID for the loan
    
    Returns:
        Loan number in format: 26/B01/WL/00001
        - YY: 2-digit year (e.g., 26 for 2026)
        - B##: Branch code (e.g., B01)
        - TYPE: Loan type code (WS, DLS, MF, DL, ML)
        - #####: 5-digit sequential number
    """
    # Get current year (last 2 digits)
    year = datetime.now().strftime('%y')
    
    # Get branch code
    if branch_id:
        try:
            branch = Branch.query.get(branch_id)
            branch_code = branch.branch_code if branch else 'B01'
        except:
            branch_code = f'B{branch_id:02d}'
    else:
        branch_code = 'B01'
    
    # Get loan type code
    type_code = get_loan_type_code(loan_type) if loan_type else 'ML'
    
    # Find the last loan with the same year, branch, and type
    # This ensures sequential numbering per branch, type, and year
    try:
        # Query pattern: "26/B01/WS/%"
        pattern = f"{year}/{branch_code}/{type_code}/%"
        last_loan = Loan.query.filter(
            Loan.loan_number.like(pattern)
        ).order_by(Loan.id.desc()).first()
        
        if last_loan:
            # Extract the sequential number from the loan_number
            try:
                parts = last_loan.loan_number.split('/')
                if len(parts) == 4:
                    last_number = int(parts[3])
                    new_number = last_number + 1
                else:
                    new_number = 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            new_number = 1
    except:
        # Handle case where database is not available (e.g., testing)
        new_number = 1
    
    return f"{year}/{branch_code}/{type_code}/{new_number:05d}"

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

def generate_receipt_number(loan_id=None, payment_type='loan'):
    """Generate unique receipt number for payments
    
    Args:
        loan_id: ID of the loan (for loan payments)
        payment_type: 'loan' or 'pawning'
    
    Returns:
        Sequential numeric receipt number (e.g., 100001, 100002, etc.)
    """
    from app.models import LoanPayment, PawningPayment
    
    # Determine which model to query based on payment type
    if payment_type == 'loan':
        # Get the last loan payment receipt number
        last_payment = LoanPayment.query.filter(
            LoanPayment.receipt_number.isnot(None),
            LoanPayment.receipt_number != ''
        ).order_by(LoanPayment.id.desc()).first()
    else:
        # Get the last pawning payment receipt number
        last_payment = PawningPayment.query.filter(
            PawningPayment.receipt_number.isnot(None),
            PawningPayment.receipt_number != ''
        ).order_by(PawningPayment.id.desc()).first()
    
    if last_payment and last_payment.receipt_number:
        try:
            # Extract the numeric part and increment
            last_number = int(last_payment.receipt_number)
            new_number = last_number + 1
        except (ValueError, AttributeError):
            # If conversion fails, start from a base number
            new_number = 100001
    else:
        # Start from 100001 if no existing receipts
        new_number = 100001
    
    return str(new_number)

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

def get_user_accessible_branch_ids():
    """Get list of branch IDs that the current user can access"""
    from flask_login import current_user
    from flask import session
    
    if not current_user.is_authenticated:
        return []
    
    if current_user.role == 'admin':
        # Admin can access all branches
        return [b.id for b in Branch.query.filter_by(is_active=True).all()]
    
    if current_user.role == 'regional_manager':
        # Regional manager can access their assigned branches
        if current_user.regional_branches:
            return [b.id for b in current_user.regional_branches]
        else:
            # If no branches assigned, return empty list
            return []
    
    # Regular users can only access their own branch
    if current_user.branch_id:
        return [current_user.branch_id]
    
    return []

def get_current_branch_id():
    """Get the current branch ID for filtering queries"""
    from flask_login import current_user
    
    # First try to get from session (for admin and regional manager users who can switch branches)
    branch_id = session.get('current_branch_id')
    
    # If not in session and user is logged in, use user's branch
    if branch_id is None and current_user.is_authenticated:
        branch_id = current_user.branch_id
    
    # If still None, get any active branch as fallback
    if branch_id is None:
        # Try MAIN branch first
        default_branch = Branch.query.filter_by(branch_code='MAIN', is_active=True).first()
        if default_branch:
            branch_id = default_branch.id
        else:
            # If no MAIN branch, get any active branch
            any_branch = Branch.query.filter_by(is_active=True).first()
            if any_branch:
                branch_id = any_branch.id
    
    return branch_id

def get_branch_filter_for_query(model_branch_id_column=None):
    """Get branch filter condition for database queries
    
    Args:
        model_branch_id_column: The branch_id column of the model (e.g., Customer.branch_id)
                                 If None, returns condition for Branch.id
    """
    from flask_login import current_user
    from flask import session
    from sqlalchemy import or_
    
    if not current_user.is_authenticated:
        return None
    
    # Check if user has selected a specific branch in session
    session_branch_id = session.get('current_branch_id')
    if session_branch_id:
        if model_branch_id_column is not None:
            return model_branch_id_column == session_branch_id
        else:
            return Branch.id == session_branch_id
    
    # Get accessible branches
    accessible_branch_ids = get_user_accessible_branch_ids()
    if accessible_branch_ids:
        if model_branch_id_column is not None:
            return model_branch_id_column.in_(accessible_branch_ids)
        else:
            return Branch.id.in_(accessible_branch_ids)
    
    return None

def should_filter_by_branch():
    """Check if current user should have branch filtering applied"""
    from flask_login import current_user
    from flask import session
    
    if not current_user.is_authenticated:
        return True
    
    # If user has selected a specific branch, filter by it
    if session.get('current_branch_id') is not None:
        return True
    
    # Otherwise, check based on role
    if current_user.role == 'admin':
        # Admin can see all branches when no specific branch selected
        return False
    
    if current_user.role == 'regional_manager':
        # Regional managers should see their assigned branches
        return True
    
    # Regular users always filter by their assigned branch
    return True

def generate_receipt_number():
    """Generate a unique sequential receipt number for payments
    
    Returns:
        A sequential receipt number as string (e.g., '000001', '000002', etc.)
    """
    from app.models import LoanPayment, PawningPayment
    
    # Get the highest receipt number from both loan and pawning payments
    try:
        # Check loan payments
        last_loan_payment = LoanPayment.query.filter(
            LoanPayment.receipt_number.isnot(None),
            LoanPayment.receipt_number != ''
        ).order_by(LoanPayment.id.desc()).first()
        
        # Check pawning payments
        last_pawning_payment = PawningPayment.query.filter(
            PawningPayment.receipt_number.isnot(None),
            PawningPayment.receipt_number != ''
        ).order_by(PawningPayment.id.desc()).first()
        
        # Find the highest number
        highest_number = 0
        
        if last_loan_payment and last_loan_payment.receipt_number:
            try:
                loan_num = int(last_loan_payment.receipt_number)
                highest_number = max(highest_number, loan_num)
            except ValueError:
                pass
        
        if last_pawning_payment and last_pawning_payment.receipt_number:
            try:
                pawning_num = int(last_pawning_payment.receipt_number)
                highest_number = max(highest_number, pawning_num)
            except ValueError:
                pass
        
        # Generate next number
        next_number = highest_number + 1
        return f"{next_number:06d}"  # 6-digit zero-padded number
        
    except:
        # If database query fails, start from 1
        return "000001"
