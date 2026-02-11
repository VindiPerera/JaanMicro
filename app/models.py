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

# Association tables
regional_manager_branches = db.Table('regional_manager_branches',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('branch_id', db.Integer, db.ForeignKey('branches.id'), primary_key=True)
)

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
    nic_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    role = db.Column(db.String(50), nullable=False, default='staff')  # admin, regional_manager, manager, staff, loan_collector, accountant
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
    created_investments = db.relationship('Investment', foreign_keys='Investment.created_by', backref='creator', lazy='dynamic')
    created_pawnings = db.relationship('Pawning', foreign_keys='Pawning.created_by', backref='creator', lazy='dynamic')
    regional_branches = db.relationship('Branch', secondary=regional_manager_branches, backref='regional_managers', lazy='dynamic')
    
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
            'regional_manager': {
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
    customer_type = db.Column(db.Text, default='["customer"]')  # JSON array of types: customer, investor, guarantor, family_guarantor
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
    
    @property
    def customer_types(self):
        """Get customer types as a list"""
        try:
            return json.loads(self.customer_type) if self.customer_type else ['customer']
        except (json.JSONDecodeError, TypeError):
            # Handle legacy string values
            return [self.customer_type] if self.customer_type else ['customer']
    
    @customer_types.setter
    def customer_types(self, value):
        """Set customer types as JSON"""
        if isinstance(value, list):
            self.customer_type = json.dumps(value)
        else:
            self.customer_type = json.dumps([value] if value else ['customer'])
    
    @property
    def customer_type_display(self):
        """Get customer types as a readable string"""
        type_names = {
            'customer': 'Customer',
            'investor': 'Loan Borrower',
            'guarantor': 'Guarantor',
            'family_guarantor': 'Family Guarantor'
        }
        types = self.customer_types
        return ', '.join(type_names.get(t, t.title()) for t in types)
    
    def has_customer_type(self, customer_type):
        """Check if customer has a specific type"""
        return customer_type in self.customer_types
    
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
    loan_type = db.Column(db.String(50), nullable=False)  # Type 1 - 9 week loan, Type 2, etc.
    loan_amount = db.Column(db.Numeric(15, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(5, 2), nullable=False)  # Annual percentage rate
    interest_type = db.Column(db.String(30), default='reducing_balance')  # flat, reducing_balance
    duration_months = db.Column(db.Integer, nullable=False)
    duration_weeks = db.Column(db.Integer)  # For weekly loan types
    duration_days = db.Column(db.Integer)  # For daily loan types
    installment_amount = db.Column(db.Numeric(15, 2), nullable=False)
    installment_frequency = db.Column(db.String(20), default='monthly')  # weekly, monthly, quarterly
    
    # Amounts
    disbursed_amount = db.Column(db.Numeric(15, 2))
    total_payable = db.Column(db.Numeric(15, 2))
    paid_amount = db.Column(db.Numeric(15, 2), default=0)
    outstanding_amount = db.Column(db.Numeric(15, 2))
    penalty_amount = db.Column(db.Numeric(15, 2), default=0)
    documentation_fee = db.Column(db.Numeric(15, 2), default=0)  # 1% documentation cost
    
    # Dates
    application_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    approval_date = db.Column(db.Date)
    disbursement_date = db.Column(db.Date)
    first_installment_date = db.Column(db.Date)
    maturity_date = db.Column(db.Date)
    closing_date = db.Column(db.Date)  # Date when loan was actually closed/completed
    
    # Status and Approval (Multi-stage workflow)
    # Status flow: pending -> pending_staff_approval -> pending_manager_approval -> initiated -> active
    status = db.Column(db.String(30), default='pending')  # pending, pending_staff_approval, pending_manager_approval, initiated, active, completed, defaulted, rejected, deactivated
    
    # Staff approval (first stage)
    staff_approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    staff_approval_date = db.Column(db.Date)
    staff_approval_notes = db.Column(db.Text)
    
    # Manager approval (second stage)
    manager_approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    manager_approval_date = db.Column(db.Date)
    manager_approval_notes = db.Column(db.Text)
    
    # Admin approval (final stage)
    admin_approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    admin_approval_date = db.Column(db.Date)
    admin_approval_notes = db.Column(db.Text)
    
    # Legacy fields (kept for backward compatibility)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approval_notes = db.Column(db.Text)
    approval_date = db.Column(db.Date)
    
    # Rejection
    rejection_reason = db.Column(db.Text)
    
    # Deactivation
    deactivation_reason = db.Column(db.Text)
    deactivation_date = db.Column(db.Date)
    deactivated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Purpose and Security
    purpose = db.Column(db.Text)
    security_details = db.Column(db.Text)  # Collateral information
    document_path = db.Column(db.String(255))  # Uploaded document (PDF)
    guarantor_ids = db.Column(db.Text)  # Comma-separated guarantor customer IDs
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    referred_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # User who brought/sourced this loan
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Relationships
    payments = db.relationship('LoanPayment', backref='loan', lazy='dynamic', cascade='all, delete-orphan')
    staff_approver = db.relationship('User', foreign_keys=[staff_approved_by], backref='staff_approved_loans')
    manager_approver = db.relationship('User', foreign_keys=[manager_approved_by], backref='manager_approved_loans')
    admin_approver = db.relationship('User', foreign_keys=[admin_approved_by], backref='admin_approved_loans')
    referrer = db.relationship('User', foreign_keys=[referred_by], backref='referred_loans')
    deactivator = db.relationship('User', foreign_keys=[deactivated_by], backref='deactivated_loans')
    
    def calculate_emi(self):
        """Calculate EMI based on loan parameters and loan type"""
        from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
        
        loan_amount = Decimal(str(self.loan_amount))
        interest_rate = Decimal(str(self.interest_rate))
        
        # Check if this is a Type 1 - 9 week loan
        if self.loan_type and 'Type 1' in self.loan_type and self.duration_weeks:
            # Type 1: Interest = Interest rate * 2
            # Installment = ((100 + Interest) * Loan Amount) / (100 * weeks)
            interest = interest_rate * Decimal('2')
            installment = ((Decimal('100') + interest) * loan_amount) / (Decimal('100') * Decimal(str(self.duration_weeks)))
            # Floor to whole number to get exact total
            return float(installment.quantize(Decimal('1'), rounding=ROUND_DOWN))
        
        # Check if this is a 54 Daily loan
        if self.loan_type and '54' in self.loan_type and self.duration_days:
            # Same formula as Type 1 but using days instead of weeks
            # Installment = ((100 + Interest) * Loan Amount) / (100 * days)
            interest = interest_rate * Decimal('2')
            installment = ((Decimal('100') + interest) * loan_amount) / (Decimal('100') * Decimal(str(self.duration_days)))
            # Floor to whole number to get exact total
            return float(installment.quantize(Decimal('1'), rounding=ROUND_DOWN))
        
        # Check if this is a Type 4 Micro Loan (weekly)
        if self.loan_type and 'Micro' in self.loan_type and self.duration_weeks and self.duration_months:
            # Type 4 Micro: Full Interest = Interest Rate * Months
            # Weeks = Months * 4
            # Installment = LA * ((Full Interest + 100) / 100) / Weeks
            full_interest = interest_rate * Decimal(str(self.duration_months))
            installment = (loan_amount * ((full_interest + Decimal('100')) / Decimal('100'))) / Decimal(str(self.duration_weeks))
            return float(installment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        # Check if this is a Type 4 Daily Loan
        if self.loan_type and 'Type 4' in self.loan_type and 'Daily' in self.loan_type and self.duration_days and self.duration_months:
            # Type 4 Daily: Full Interest = Interest Rate * Months
            # Days = Months * 25
            # Installment = LA * ((Full Interest + 100) / 100) / Days
            full_interest = interest_rate * Decimal(str(self.duration_months))
            installment = (loan_amount * ((full_interest + Decimal('100')) / Decimal('100'))) / Decimal(str(self.duration_days))
            return float(installment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        # Standard calculation methods
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
        
        # Check if this is a flat rate loan type (Type1 9weeks, 54 Daily, Type4 loans)
        is_flat_rate_loan = (self.loan_type and (
            'type1' in self.loan_type.lower() or 
            '54' in self.loan_type.lower() or 
            'type4' in self.loan_type.lower() or 
            'micro' in self.loan_type.lower() or
            'daily' in self.loan_type.lower()
        )) or self.interest_type == 'flat'
        
        if is_flat_rate_loan:
            # For flat interest loans, use total_payable if available
            if self.total_payable:
                total_interest = Decimal(str(self.total_payable)) - loan_amount
            else:
                # Fallback: calculate based on duration
                if self.duration_weeks:
                    # For weekly loans, calculate using weeks
                    interest = interest_rate * Decimal('2')
                    total_interest = (loan_amount * interest) / Decimal('100')
                elif self.duration_days:
                    # For daily loans
                    interest = interest_rate * Decimal('2')
                    total_interest = (loan_amount * interest) / Decimal('100')
                else:
                    # Monthly loans
                    duration = Decimal(str(self.duration_months))
                    total_interest = (loan_amount * interest_rate * duration) / (Decimal('12') * Decimal('100'))
        else:
            # For reducing balance, calculate based on total payable amount
            if self.total_payable:
                total_interest = Decimal(str(self.total_payable)) - loan_amount
            else:
                # Fallback calculation
                duration = Decimal(str(self.duration_months))
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
        
        # Check if this is a flat rate loan type (Type1 9weeks, 54 Daily, Type4 loans)
        is_flat_rate_loan = (self.loan_type and (
            'type1' in self.loan_type.lower() or 
            '54' in self.loan_type.lower() or 
            'type4' in self.loan_type.lower() or 
            'micro' in self.loan_type.lower() or
            'daily' in self.loan_type.lower()
        )) or self.interest_type == 'flat'
        
        if is_flat_rate_loan:
            # For flat interest loans, calculate remaining total payable amount
            # Use total_payable if available, otherwise calculate it
            if self.total_payable:
                total_expected = Decimal(str(self.total_payable))
            else:
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
    
    def generate_payment_schedule(self):
        """Generate payment schedule based on loan type and frequency"""
        from decimal import Decimal, ROUND_HALF_UP
        from datetime import timedelta, datetime
        
        # Allow schedule generation for disbursed, active, and completed loans
        if self.status not in ['disbursed', 'active', 'completed']:
            return []
        
        # Determine first installment date
        first_date = self.first_installment_date
        if not first_date:
            # If first_installment_date is not set, use disbursement_date or approval_date
            if self.disbursement_date:
                first_date = self.disbursement_date
            elif self.approval_date:
                first_date = self.approval_date
            elif self.application_date:
                first_date = self.application_date
            else:
                # No valid date found, cannot generate schedule
                return []
        
        schedule = []
        installment_amount = Decimal(str(self.installment_amount))
        total_payable = Decimal(str(self.total_payable or self.loan_amount))
        loan_amount = Decimal(str(self.loan_amount))
        
        # Determine number of installments and frequency delta based on loan type
        if self.duration_days and ('daily' in self.loan_type.lower() or '54' in self.loan_type):
            # Daily installments
            num_installments = self.duration_days
            frequency_delta = timedelta(days=1)
            frequency_name = 'Daily'
        elif self.duration_weeks and ('week' in self.loan_type.lower() or 'micro' in self.loan_type.lower()):
            # Weekly installments
            num_installments = self.duration_weeks
            frequency_delta = timedelta(weeks=1)
            frequency_name = 'Weekly'
        else:
            # Monthly installments
            num_installments = self.duration_months
            frequency_delta = None  # Will use relativedelta for months
            frequency_name = 'Monthly'
        
        # Get total paid amount
        total_paid = Decimal(str(self.paid_amount or 0))
        
        # Calculate total interest
        total_interest = total_payable - loan_amount
        
        # Generate schedule
        cumulative_expected = Decimal('0')
        
        for i in range(num_installments):
            installment_num = i + 1
            
            # Calculate due date
            if frequency_delta:
                due_date = first_date + (frequency_delta * i)
            else:
                # For monthly, use relativedelta
                due_date = first_date + relativedelta(months=i)
            
            # Determine installment amount (last installment adjusts for rounding)
            if installment_num == num_installments:
                # Last installment: total payable minus all previous installments
                current_installment = total_payable - cumulative_expected
            else:
                current_installment = installment_amount
            
            cumulative_expected += current_installment
            
            # Calculate principal and interest breakdown
            # For most loan types, split evenly across installments
            interest_per_installment = total_interest / Decimal(str(num_installments))
            principal_per_installment = loan_amount / Decimal(str(num_installments))
            
            # Adjust last installment for rounding
            if installment_num == num_installments:
                interest = current_installment - principal_per_installment
                principal = principal_per_installment
            else:
                interest = interest_per_installment
                principal = principal_per_installment
            
            # Determine status based on payments
            status = 'pending'
            installment_threshold = installment_amount * Decimal(str(installment_num))
            
            if total_paid >= installment_threshold:
                status = 'paid'
            elif total_paid >= (installment_threshold - current_installment) and total_paid > 0:
                status = 'partial'
            elif due_date < datetime.utcnow().date():
                status = 'overdue'
            
            schedule.append({
                'installment_number': installment_num,
                'due_date': due_date,
                'amount': float(current_installment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'principal': float(principal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'interest': float(interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'status': status
            })
        
        return schedule
    
    def get_arrears_details(self):
        """Calculate arrears details for overdue payments"""
        from decimal import Decimal
        from datetime import date
        
        if self.status not in ['active', 'completed']:
            return {
                'total_overdue_amount': Decimal('0'),
                'overdue_installments': 0,
                'days_overdue': 0,
                'oldest_overdue_date': None
            }
        
        schedule = self.generate_payment_schedule()
        total_overdue = Decimal('0')
        overdue_count = 0
        oldest_overdue_date = None
        today = date.today()
        
        for installment in schedule:
            if installment['status'] == 'overdue':
                total_overdue += Decimal(str(installment['amount']))
                overdue_count += 1
                if oldest_overdue_date is None or installment['due_date'] < oldest_overdue_date:
                    oldest_overdue_date = installment['due_date']
        
        days_overdue = 0
        if oldest_overdue_date and oldest_overdue_date < today:
            days_overdue = (today - oldest_overdue_date).days
        
        return {
            'total_overdue_amount': total_overdue,
            'overdue_installments': overdue_count,
            'days_overdue': days_overdue,
            'oldest_overdue_date': oldest_overdue_date
        }
    
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
    balance_after = db.Column(db.Numeric(15, 2))  # Outstanding balance after this payment
    
    payment_method = db.Column(db.String(50))  # cash, bank_transfer, cheque, etc.
    reference_number = db.Column(db.String(100))
    receipt_number = db.Column(db.String(100))  # Receipt number for this payment
    notes = db.Column(db.Text)
    
    collected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    collected_by_user = db.relationship('User', foreign_keys=[collected_by], backref='collected_payments')
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


