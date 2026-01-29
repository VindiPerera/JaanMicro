"""Database models for JAANmicro"""
from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from sqlalchemy import Numeric, func
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User and Authentication Models
class User(UserMixin, db.Model):
    """User model for staff members"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(50), nullable=False, default='staff')  # admin, manager, staff, loan_collector, accountant
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)  # Nullable for admin users who can access all branches
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Permissions
    can_add_customers = db.Column(db.Boolean, default=True)
    can_edit_customers = db.Column(db.Boolean, default=True)
    can_delete_customers = db.Column(db.Boolean, default=False)
    can_manage_loans = db.Column(db.Boolean, default=True)
    can_approve_loans = db.Column(db.Boolean, default=False)
    can_manage_investments = db.Column(db.Boolean, default=True)
    can_manage_pawnings = db.Column(db.Boolean, default=True)
    can_view_reports = db.Column(db.Boolean, default=True)
    can_view_collection_reports = db.Column(db.Boolean, default=False)
    can_manage_settings = db.Column(db.Boolean, default=False)
    can_collect_payments = db.Column(db.Boolean, default=True)
    can_verify_kyc = db.Column(db.Boolean, default=False)
    
    # Relationships
    created_customers = db.relationship('Customer', foreign_keys='Customer.created_by', backref='created_by_user', lazy='dynamic')
    created_loans = db.relationship('Loan', foreign_keys='Loan.created_by', backref='creator', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        if self.role == 'admin':
            return True
        return getattr(self, f'can_{permission}', False)
    
    def set_role_permissions(self, role=None):
        """Set default permissions based on role"""
        if role is None:
            role = self.role
            
        permissions_map = {
            'staff': {
                'can_add_customers': True,
                'can_edit_customers': True,
                'can_delete_customers': False,
                'can_manage_loans': True,
                'can_approve_loans': False,
                'can_manage_investments': False,
                'can_manage_pawnings': True,
                'can_view_reports': False,
                'can_view_collection_reports': False,
                'can_manage_settings': False,
                'can_collect_payments': True,
                'can_verify_kyc': False
            },
            'loan_collector': {
                'can_add_customers': False,
                'can_edit_customers': True,
                'can_delete_customers': False,
                'can_manage_loans': True,
                'can_approve_loans': False,
                'can_manage_investments': False,
                'can_manage_pawnings': False,
                'can_view_reports': True,
                'can_view_collection_reports': True,
                'can_manage_settings': False,
                'can_collect_payments': True,
                'can_verify_kyc': False
            },
            'accountant': {
                'can_add_customers': True,
                'can_edit_customers': True,
                'can_delete_customers': False,
                'can_manage_loans': True,
                'can_approve_loans': True,
                'can_manage_investments': True,
                'can_manage_pawnings': True,
                'can_view_reports': True,
                'can_view_collection_reports': True,
                'can_manage_settings': False,
                'can_collect_payments': True,
                'can_verify_kyc': False
            },
            'manager': {
                'can_add_customers': True,
                'can_edit_customers': True,
                'can_delete_customers': True,
                'can_manage_loans': True,
                'can_approve_loans': True,
                'can_manage_investments': True,
                'can_manage_pawnings': True,
                'can_view_reports': True,
                'can_view_collection_reports': True,
                'can_manage_settings': True,
                'can_collect_payments': True,
                'can_verify_kyc': True
            },
            'admin': {
                'can_add_customers': True,
                'can_edit_customers': True,
                'can_delete_customers': True,
                'can_manage_loans': True,
                'can_approve_loans': True,
                'can_manage_investments': True,
                'can_manage_pawnings': True,
                'can_view_reports': True,
                'can_view_collection_reports': True,
                'can_manage_settings': True,
                'can_collect_payments': True,
                'can_verify_kyc': False
            }
        }
        
        permissions = permissions_map.get(role, {})
        for permission, value in permissions.items():
            setattr(self, permission, value)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Branch Model
class Branch(db.Model):
    """Branch model for multi-branch support"""
    __tablename__ = 'branches'
    
    id = db.Column(db.Integer, primary_key=True)
    branch_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='branch', lazy='dynamic', foreign_keys='User.branch_id')
    customers = db.relationship('Customer', backref='branch', lazy='dynamic')
    loans = db.relationship('Loan', backref='branch', lazy='dynamic')
    investments = db.relationship('Investment', backref='branch', lazy='dynamic')
    pawnings = db.relationship('Pawning', backref='branch', lazy='dynamic')
    
    def __repr__(self):
        return f'<Branch {self.name}>'

# Customer and KYC Models
class Customer(db.Model):
    """Customer model with KYC information"""
    __tablename__ = 'customers'

    # Bank Information
    bank_name = db.Column(db.String(100))
    bank_branch = db.Column(db.String(100))
    bank_account_number = db.Column(db.String(30))
    bank_account_type = db.Column(db.String(30))
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    
    # Personal Information
    full_name = db.Column(db.String(200), nullable=False, index=True)
    nic_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    customer_type = db.Column(db.String(20), default='customer')  # customer, investor, guarantor
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    marital_status = db.Column(db.String(20))
    profile_picture = db.Column(db.String(255))
    
    # Contact Information
    phone_primary = db.Column(db.String(20), nullable=False)
    phone_secondary = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address_line1 = db.Column(db.String(255), nullable=False)
    address_line2 = db.Column(db.String(255))
    city = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)  # Required field - Must be a Sri Lankan district
    postal_code = db.Column(db.String(10))
    
    # Employment Information
    occupation = db.Column(db.String(100))
    employer_name = db.Column(db.String(200))
    monthly_income = db.Column(db.Numeric(15, 2))
    employment_type = db.Column(db.String(50))  # permanent, contract, self_employed, etc.
    
    # KYC Information
    kyc_verified = db.Column(db.Boolean, default=False)
    kyc_verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    kyc_verified_date = db.Column(db.DateTime)
    nic_front_image = db.Column(db.String(255))
    nic_back_image = db.Column(db.String(255))
    photo = db.Column(db.String(255))
    proof_of_address = db.Column(db.String(255))
    additional_documents = db.Column(db.Text)  # JSON array of document paths
    
    # Emergency Contact
    emergency_contact_name = db.Column(db.String(200))
    emergency_contact_phone = db.Column(db.String(20))
    emergency_contact_relation = db.Column(db.String(50))
    
    # Guarantor Information (if needed)
    guarantor_name = db.Column(db.String(200))
    guarantor_nic = db.Column(db.String(20))
    guarantor_phone = db.Column(db.String(20))
    guarantor_address = db.Column(db.Text)
    
    # Status and Metadata
    status = db.Column(db.String(20), default='active')  # active, inactive, blacklisted
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loans = db.relationship('Loan', backref='customer', lazy='dynamic', cascade='all, delete-orphan')
    investments = db.relationship('Investment', backref='customer', lazy='dynamic', cascade='all, delete-orphan')
    pawnings = db.relationship('Pawning', backref='customer', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_total_loan_amount(self):
        """Get total outstanding loan amount"""
        return sum(loan.outstanding_amount for loan in self.loans.filter_by(status='active').all())
    
    def get_total_investment_amount(self):
        """Get total investment amount"""
        return sum(inv.current_amount for inv in self.investments.filter_by(status='active').all())
    
    def __repr__(self):
        return f'<Customer {self.customer_id} - {self.full_name}>'

# Loan Models
class Loan(db.Model):
    """Loan model for managing customer loans"""
    __tablename__ = 'loans'
    
    id = db.Column(db.Integer, primary_key=True)
    loan_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    
    # Loan Details
    loan_type = db.Column(db.String(50), nullable=False)  # business, personal, education, etc.
    loan_amount = db.Column(db.Numeric(15, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(5, 2), nullable=False)  # Annual percentage rate
    interest_type = db.Column(db.String(30), default='reducing_balance')  # flat, reducing_balance
    duration_months = db.Column(db.Integer, nullable=False)
    installment_amount = db.Column(db.Numeric(15, 2), nullable=False)
    installment_frequency = db.Column(db.String(20), default='monthly')  # weekly, monthly, quarterly
    
    # Amounts
    disbursed_amount = db.Column(db.Numeric(15, 2))
    total_payable = db.Column(db.Numeric(15, 2))
    paid_amount = db.Column(db.Numeric(15, 2), default=0)
    outstanding_amount = db.Column(db.Numeric(15, 2))
    penalty_amount = db.Column(db.Numeric(15, 2), default=0)
    
    # Dates
    application_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    approval_date = db.Column(db.Date)
    disbursement_date = db.Column(db.Date)
    first_installment_date = db.Column(db.Date)
    maturity_date = db.Column(db.Date)
    
    # Status and Approval
    status = db.Column(db.String(20), default='pending')  # pending, approved, active, completed, defaulted, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approval_notes = db.Column(db.Text)
    
    # Purpose and Security
    purpose = db.Column(db.Text)
    security_details = db.Column(db.Text)  # Collateral information
    document_path = db.Column(db.String(255))  # Uploaded document (PDF)
    guarantor_ids = db.Column(db.Text)  # Comma-separated guarantor customer IDs
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Relationships
    payments = db.relationship('LoanPayment', backref='loan', lazy='dynamic', cascade='all, delete-orphan')
    
    def calculate_emi(self):
        """Calculate EMI based on loan parameters"""
        from decimal import Decimal, ROUND_HALF_UP
        
        loan_amount = Decimal(str(self.loan_amount))
        interest_rate = Decimal(str(self.interest_rate))
        
        if self.interest_type == 'reducing_balance':
            # EMI = [P x R x (1+R)^N]/[(1+R)^N-1]
            monthly_rate = interest_rate / (Decimal('12') * Decimal('100'))
            n = self.duration_months
            if monthly_rate > 0:
                # Use float for power calculation, then convert back
                mr_float = float(monthly_rate)
                power_calc = ((1 + mr_float) ** n) / (((1 + mr_float) ** n) - 1)
                emi = loan_amount * monthly_rate * Decimal(str(power_calc))
            else:
                emi = loan_amount / Decimal(str(n))
        else:  # flat rate
            total_interest = loan_amount * interest_rate * Decimal(str(self.duration_months)) / (Decimal('12') * Decimal('100'))
            emi = (loan_amount + total_interest) / Decimal(str(self.duration_months))
        
        return float(emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def get_total_paid_principal(self):
        """Get total principal amount paid"""
        from decimal import Decimal
        total = self.payments.with_entities(func.sum(LoanPayment.principal_amount)).scalar()
        return Decimal(str(total or 0))
    
    def get_total_paid_interest(self):
        """Get total interest amount paid"""
        from decimal import Decimal
        total = self.payments.with_entities(func.sum(LoanPayment.interest_amount)).scalar()
        return Decimal(str(total or 0))
    
    def get_total_expected_interest(self):
        """Get total interest expected for this loan based on interest type"""
        from decimal import Decimal, ROUND_HALF_UP
        
        loan_amount = Decimal(str(self.disbursed_amount or self.loan_amount))
        interest_rate = Decimal(str(self.interest_rate))
        duration = Decimal(str(self.duration_months))
        
        if self.interest_type == 'flat':
            # For flat interest: Total Interest = Principal × Rate × Time
            total_interest = (loan_amount * interest_rate * duration) / (Decimal('12') * Decimal('100'))
        else:
            # For reducing balance, calculate based on total payable amount
            if self.total_payable:
                total_interest = Decimal(str(self.total_payable)) - loan_amount
            else:
                # Fallback calculation
                total_interest = (loan_amount * interest_rate * duration) / (Decimal('12') * Decimal('100'))
        
        return total_interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calculate_accrued_interest(self):
        """Calculate accrued interest since last payment or disbursement - only for reducing balance loans"""
        from decimal import Decimal, ROUND_HALF_UP
        from datetime import datetime, date
        
        # Accrued interest only applies to reducing balance loans
        if self.status != 'active' or not self.disbursement_date or self.interest_type == 'flat':
            return Decimal('0')
        
        # Get the date from which to calculate accrued interest
        last_payment = self.payments.order_by(LoanPayment.payment_date.desc()).first()
        start_date = last_payment.payment_date if last_payment else self.disbursement_date
        
        # Calculate days since last payment/disbursement
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        elif isinstance(start_date, datetime):
            start_date = start_date.date()
            
        today = date.today()
        days_elapsed = (today - start_date).days
        
        if days_elapsed <= 0:
            return Decimal('0')
        
        # Current outstanding principal
        disbursed = Decimal(str(self.disbursed_amount or self.loan_amount))
        paid_principal = self.get_total_paid_principal()
        current_principal = disbursed - paid_principal
        
        if current_principal <= 0:
            return Decimal('0')
        
        # Calculate accrued interest
        annual_rate = Decimal(str(self.interest_rate)) / Decimal('100')
        daily_rate = annual_rate / Decimal('365')
        accrued_interest = current_principal * daily_rate * Decimal(str(days_elapsed))
        
        return accrued_interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calculate_current_outstanding(self):
        """Calculate current outstanding amount including accrued interest (reducing balance) or remaining balance (flat)"""
        from decimal import Decimal, ROUND_HALF_UP
        
        if self.status != 'active':
            return Decimal('0')
        
        # Current outstanding principal
        disbursed = Decimal(str(self.disbursed_amount or self.loan_amount))
        paid_principal = self.get_total_paid_principal()
        outstanding_principal = disbursed - paid_principal
        
        if self.interest_type == 'flat':
            # For flat interest loans, calculate remaining total payable amount
            total_expected = disbursed + self.get_total_expected_interest()
            total_paid = Decimal(str(self.paid_amount or 0))
            outstanding = total_expected - total_paid
        else:
            # For reducing balance loans, add accrued interest
            accrued_interest = self.calculate_accrued_interest()
            outstanding = outstanding_principal + accrued_interest
        
        # Add any penalty amount
        penalty = Decimal(str(self.penalty_amount or 0))
        total_outstanding = outstanding + penalty
        
        return max(Decimal('0'), total_outstanding.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def update_outstanding_amount(self):
        """Update the outstanding_amount field with current calculation"""
        self.outstanding_amount = float(self.calculate_current_outstanding())
    
    def __repr__(self):
        return f'<Loan {self.loan_number}>'

class LoanPayment(db.Model):
    """Loan payment/installment records"""
    __tablename__ = 'loan_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=False, index=True)
    
    payment_date = db.Column(db.Date, nullable=False, index=True)
    payment_amount = db.Column(db.Numeric(15, 2), nullable=False)
    principal_amount = db.Column(db.Numeric(15, 2))
    interest_amount = db.Column(db.Numeric(15, 2))
    penalty_amount = db.Column(db.Numeric(15, 2), default=0)
    
    payment_method = db.Column(db.String(50))  # cash, bank_transfer, cheque, etc.
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    collected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LoanPayment {self.id}>'

# Investment Models
class Investment(db.Model):
    """Investment/Savings model"""
    __tablename__ = 'investments'
    
    id = db.Column(db.Integer, primary_key=True)
    investment_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    
    # Investment Details
    investment_type = db.Column(db.String(50), nullable=False)  # fixed_deposit, savings, recurring_deposit
    principal_amount = db.Column(db.Numeric(15, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(5, 2), nullable=False)
    duration_months = db.Column(db.Integer)
    maturity_amount = db.Column(db.Numeric(15, 2))
    current_amount = db.Column(db.Numeric(15, 2))
    
    # Dates
    start_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    maturity_date = db.Column(db.Date)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, matured, closed
    
    # Payment frequency for recurring deposits
    installment_amount = db.Column(db.Numeric(15, 2))
    installment_frequency = db.Column(db.String(20))  # monthly, quarterly
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Relationships
    transactions = db.relationship('InvestmentTransaction', backref='investment', lazy='dynamic', cascade='all, delete-orphan')
    
    def calculate_maturity_amount(self):
        """Calculate maturity amount"""
        from decimal import Decimal, ROUND_HALF_UP
        
        principal = Decimal(str(self.principal_amount))
        interest_rate = Decimal(str(self.interest_rate))
        duration = Decimal(str(self.duration_months))
        
        interest = principal * interest_rate * duration / (Decimal('12') * Decimal('100'))
        total = principal + interest
        return float(total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def __repr__(self):
        return f'<Investment {self.investment_number}>'

class InvestmentTransaction(db.Model):
    """Investment transaction records"""
    __tablename__ = 'investment_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    investment_id = db.Column(db.Integer, db.ForeignKey('investments.id'), nullable=False, index=True)
    
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    transaction_type = db.Column(db.String(20), nullable=False)  # deposit, withdrawal, interest_credit
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    balance_after = db.Column(db.Numeric(15, 2))
    
    payment_method = db.Column(db.String(50))
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<InvestmentTransaction {self.id}>'

# Pawning Models
class Pawning(db.Model):
    """Pawning/Pledged loan model - Sri Lankan style"""
    __tablename__ = 'pawnings'
    
    id = db.Column(db.Integer, primary_key=True)
    pawning_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    
    # Item Details (Gold-focused for Sri Lankan pawning)
    item_description = db.Column(db.Text, nullable=False)
    item_type = db.Column(db.String(50), default='gold')  # gold, jewelry, electronics, documents, etc.
    item_weight = db.Column(db.Numeric(10, 3))  # Weight in grams (precise for gold)
    item_purity = db.Column(db.String(20))  # 24K, 22K, 18K, etc.
    karats = db.Column(db.Numeric(4, 2))  # Numerical karat value (24.00, 22.00, 18.00)
    number_of_items = db.Column(db.Integer, default=1)  # Number of pieces
    market_value_per_gram = db.Column(db.Numeric(15, 2))  # Current gold rate per gram
    total_market_value = db.Column(db.Numeric(15, 2))  # Total appraised value
    item_photos = db.Column(db.Text)  # JSON array of photo paths
    
    # Loan Details (Sri Lankan calculation method)
    loan_amount = db.Column(db.Numeric(15, 2), nullable=False)  # Principal amount given
    interest_rate = db.Column(db.Numeric(5, 2), nullable=False)  # Monthly interest rate %
    loan_to_value_ratio = db.Column(db.Numeric(5, 2))  # Percentage of market value (typically 60-80%)
    
    # Period tracking
    duration_months = db.Column(db.Integer, nullable=False)  # Original agreed period
    grace_period_days = db.Column(db.Integer, default=30)  # Days after due date before auction
    
    # Interest tracking (Sri Lankan method: monthly interest payments)
    interest_per_month = db.Column(db.Numeric(15, 2))  # Fixed monthly interest amount
    total_interest_paid = db.Column(db.Numeric(15, 2), default=0)  # Interest paid so far
    interest_due = db.Column(db.Numeric(15, 2), default=0)  # Unpaid interest accumulated
    principal_paid = db.Column(db.Numeric(15, 2), default=0)  # Principal repayments
    outstanding_principal = db.Column(db.Numeric(15, 2))  # Remaining principal
    
    # Penalty for overdue
    penalty_rate = db.Column(db.Numeric(5, 2), default=0)  # Additional penalty rate if overdue
    total_penalty = db.Column(db.Numeric(15, 2), default=0)
    
    # Dates
    pawning_date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    maturity_date = db.Column(db.Date, nullable=False)  # Original maturity date
    extended_date = db.Column(db.Date)  # If renewed/extended
    last_interest_payment_date = db.Column(db.Date)  # Track last interest payment
    redemption_date = db.Column(db.Date)
    auction_date = db.Column(db.Date)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, redeemed, extended, overdue, auctioned
    is_overdue = db.Column(db.Boolean, default=False)
    
    # Renewal/Extension tracking
    times_extended = db.Column(db.Integer, default=0)
    extension_notes = db.Column(db.Text)
    
    # Storage Information
    storage_location = db.Column(db.String(100))
    storage_box_number = db.Column(db.String(50))
    storage_notes = db.Column(db.Text)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Relationships
    payments = db.relationship('PawningPayment', backref='pawning', lazy='dynamic', cascade='all, delete-orphan')
    
    def calculate_monthly_interest(self):
        """Calculate monthly interest amount (Sri Lankan method)"""
        from decimal import Decimal, ROUND_HALF_UP
        
        loan_amount = Decimal(str(self.loan_amount))
        interest_rate = Decimal(str(self.interest_rate))
        monthly_interest = loan_amount * interest_rate / Decimal('100')
        return float(monthly_interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def calculate_total_interest_due(self):
        """Calculate total interest due based on months elapsed"""
        from decimal import Decimal, ROUND_HALF_UP
        
        if not self.pawning_date:
            return 0
        
        # Calculate months from pawning date to now or redemption date
        end_date = self.redemption_date if self.redemption_date else datetime.utcnow().date()
        months_elapsed = ((end_date.year - self.pawning_date.year) * 12 + 
                         (end_date.month - self.pawning_date.month))
        
        if months_elapsed < 0:
            months_elapsed = 0
        
        loan_amount = Decimal(str(self.loan_amount))
        interest_rate = Decimal(str(self.interest_rate))
        months = Decimal(str(months_elapsed))
        
        interest = loan_amount * interest_rate / Decimal('100') * months
        return float(interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def get_redemption_amount(self):
        """Calculate total amount needed to redeem the item"""
        total = float(self.outstanding_principal or self.loan_amount)
        total += float(self.interest_due or 0)
        total += float(self.total_penalty or 0)
        return round(total, 2)
    
    def check_overdue_status(self):
        """Check if pawning is overdue"""
        if self.status not in ['active', 'extended']:
            return False
        
        due_date = self.extended_date if self.extended_date else self.maturity_date
        grace_end = due_date + relativedelta(days=self.grace_period_days)
        
        today = datetime.utcnow().date()
        return today > grace_end
    
    def calculate_interest_for_period(self, from_date, to_date):
        """Calculate interest for a specific period"""
        if not from_date or not to_date:
            return 0
        
        days = (to_date - from_date).days
        months = Decimal(str(days)) / Decimal('30.0')  # Approximate months
        
        from decimal import Decimal, ROUND_HALF_UP
        loan_amount = Decimal(str(self.loan_amount))
        interest_rate = Decimal(str(self.interest_rate))
        interest = loan_amount * interest_rate / Decimal('100') * months
        return float(interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def __repr__(self):
        return f'<Pawning {self.pawning_number}>'

class PawningPayment(db.Model):
    """Pawning payment records - supports interest-only and redemption payments"""
    __tablename__ = 'pawning_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    pawning_id = db.Column(db.Integer, db.ForeignKey('pawnings.id'), nullable=False, index=True)
    
    payment_date = db.Column(db.Date, nullable=False, index=True)
    payment_amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_type = db.Column(db.String(30))  # interest_payment, partial_principal, full_redemption, penalty
    
    # Breakdown of payment
    interest_amount = db.Column(db.Numeric(15, 2), default=0)
    principal_amount = db.Column(db.Numeric(15, 2), default=0)
    penalty_amount = db.Column(db.Numeric(15, 2), default=0)
    
    # Balance tracking after this payment
    interest_balance_after = db.Column(db.Numeric(15, 2))
    principal_balance_after = db.Column(db.Numeric(15, 2))
    
    # Period covered by this interest payment
    interest_period_from = db.Column(db.Date)
    interest_period_to = db.Column(db.Date)
    
    payment_method = db.Column(db.String(50))
    reference_number = db.Column(db.String(100))
    receipt_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    collected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PawningPayment {self.id}>'

# System Settings Model
class SystemSettings(db.Model):
    """System-wide settings and configurations"""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Branding
    app_name = db.Column(db.String(100), default='JAANmicro')
    logo_path = db.Column(db.String(255))
    favicon_path = db.Column(db.String(255))
    theme_color = db.Column(db.String(7), default='#2c3e50')
    
    # Regional Settings
    currency = db.Column(db.String(10), default='LKR')
    currency_symbol = db.Column(db.String(10), default='Rs.')
    date_format = db.Column(db.String(20), default='%Y-%m-%d')
    timezone = db.Column(db.String(50), default='UTC')
    
    # Business Settings
    company_name = db.Column(db.String(200))
    company_address = db.Column(db.Text)
    company_phone = db.Column(db.String(20))
    company_email = db.Column(db.String(120))
    company_registration = db.Column(db.String(100))
    
    # Loan Settings
    default_loan_interest_rate = db.Column(db.Numeric(5, 2), default=12.0)
    default_loan_duration = db.Column(db.Integer, default=12)
    interest_calculation_method = db.Column(db.String(30), default='reducing_balance')
    late_payment_penalty_percentage = db.Column(db.Numeric(5, 2), default=2.0)
    grace_period_days = db.Column(db.Integer, default=7)
    
    # Investment Settings
    default_investment_interest_rate = db.Column(db.Numeric(5, 2), default=8.0)
    minimum_investment_amount = db.Column(db.Numeric(15, 2), default=10000)
    
    # Pawning Settings
    default_pawning_interest_rate = db.Column(db.Numeric(5, 2), default=15.0)
    default_pawning_duration = db.Column(db.Integer, default=6)
    maximum_loan_to_value_ratio = db.Column(db.Numeric(5, 2), default=70.0)
    
    # Auto-numbering Settings
    loan_number_prefix = db.Column(db.String(10), default='LN')
    investment_number_prefix = db.Column(db.String(10), default='INV')
    pawning_number_prefix = db.Column(db.String(10), default='PWN')
    customer_id_prefix = db.Column(db.String(10), default='CUST')
    
    # Notification Settings
    email_notifications = db.Column(db.Boolean, default=False)
    sms_notifications = db.Column(db.Boolean, default=False)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_settings():
        """Get system settings, create default if not exists"""
        settings = SystemSettings.query.first()
        if not settings:
            settings = SystemSettings()
            db.session.add(settings)
            db.session.commit()
        return settings
    
    def __repr__(self):
        return f'<SystemSettings {self.app_name}>'

# Activity Log Model
class ActivityLog(db.Model):
    """Activity log for audit trail"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))  # customer, loan, investment, etc.
    entity_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<ActivityLog {self.action}>'


