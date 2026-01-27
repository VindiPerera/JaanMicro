"""Settings forms"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, DecimalField, IntegerField, TextAreaField, BooleanField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, NumberRange, Length, EqualTo, ValidationError
from app.models import User

class SystemSettingsForm(FlaskForm):
    """System settings form"""
    # Branding
    app_name = StringField('Application Name', validators=[DataRequired(), Length(max=100)])
    logo = FileField('Logo', validators=[FileAllowed(['png', 'jpg', 'jpeg'], 'Images only!')])
    theme_color = StringField('Theme Color', validators=[DataRequired(), Length(max=7)])
    
    # Regional
    currency = StringField('Currency Code', validators=[DataRequired(), Length(max=10)])
    currency_symbol = StringField('Currency Symbol', validators=[DataRequired(), Length(max=10)])
    
    # Company Information
    company_name = StringField('Company Name', validators=[Optional(), Length(max=200)])
    company_address = TextAreaField('Company Address', validators=[Optional()])
    company_phone = StringField('Company Phone', validators=[Optional(), Length(max=20)])
    company_email = StringField('Company Email', validators=[Optional(), Email(), Length(max=120)])
    company_registration = StringField('Registration Number', validators=[Optional(), Length(max=100)])
    
    # Loan Settings
    default_loan_interest_rate = DecimalField('Default Loan Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0, max=100)], places=2)
    default_loan_duration = IntegerField('Default Loan Duration (Months)', validators=[DataRequired(), NumberRange(min=1)])
    interest_calculation_method = SelectField('Interest Calculation Method', choices=[
        ('reducing_balance', 'Reducing Balance'),
        ('flat', 'Flat Rate')
    ], validators=[DataRequired()])
    late_payment_penalty_percentage = DecimalField('Late Payment Penalty (%)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    grace_period_days = IntegerField('Grace Period (Days)', validators=[DataRequired(), NumberRange(min=0)])
    
    # Investment Settings
    default_investment_interest_rate = DecimalField('Default Investment Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0, max=100)], places=2)
    minimum_investment_amount = DecimalField('Minimum Investment Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    
    # Pawning Settings
    default_pawning_interest_rate = DecimalField('Default Pawning Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0, max=100)], places=2)
    default_pawning_duration = IntegerField('Default Pawning Duration (Months)', validators=[DataRequired(), NumberRange(min=1)])
    maximum_loan_to_value_ratio = DecimalField('Maximum Loan-to-Value Ratio (%)', validators=[DataRequired(), NumberRange(min=0, max=100)], places=2)
    
    # Auto-numbering
    loan_number_prefix = StringField('Loan Number Prefix', validators=[DataRequired(), Length(max=10)])
    investment_number_prefix = StringField('Investment Number Prefix', validators=[DataRequired(), Length(max=10)])
    pawning_number_prefix = StringField('Pawning Number Prefix', validators=[DataRequired(), Length(max=10)])
    customer_id_prefix = StringField('Customer ID Prefix', validators=[DataRequired(), Length(max=10)])
    
    submit = SubmitField('Save Settings')

class UserForm(FlaskForm):
    """User creation form"""
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=200)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    role = SelectField('Role', choices=[
        ('staff', 'Staff'),
        ('loan_collector', 'Loan Collector'),
        ('accountant', 'Accountant'),
        ('manager', 'Manager'),
        ('admin', 'Administrator')
    ], validators=[DataRequired()])
    branch_id = SelectField('Branch', coerce=int, validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    
    # Permissions - removed defaults, will be set programmatically
    can_add_customers = BooleanField('Can Add Customers')
    can_edit_customers = BooleanField('Can Edit Customers')
    can_delete_customers = BooleanField('Can Delete Customers')
    can_manage_loans = BooleanField('Can Manage Loans')
    can_approve_loans = BooleanField('Can Approve Loans')
    can_manage_investments = BooleanField('Can Manage Investments')
    can_manage_pawnings = BooleanField('Can Manage Pawnings')
    can_view_reports = BooleanField('Can View Reports')
    can_manage_settings = BooleanField('Can Manage Settings')
    can_collect_payments = BooleanField('Can Collect Payments')
    
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        # Set branch choices
        from app.models import Branch
        self.branch_id.choices = [(0, '-- Select Branch --')] + [(b.id, f"{b.branch_code} - {b.name}") for b in Branch.query.filter_by(is_active=True).all()]
        
        # Set default permissions for staff role on new forms only if no data provided
        if not args and not kwargs.get('obj'):  # New form, no existing data
            # Set default role to staff if not provided
            if not self.role.data:
                self.role.data = 'staff'
            self._set_default_permissions_for_role('staff')
    
    def _set_default_permissions_for_role(self, role):
        """Set default permissions based on role"""
        defaults = self.get_role_permissions(role)
        for permission, value in defaults.items():
            if hasattr(self, permission):
                getattr(self, permission).data = value
    
    @staticmethod
    def get_role_permissions(role):
        """Get default permissions for a role"""
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
                'can_manage_settings': False,
                'can_collect_payments': True
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
                'can_manage_settings': False,
                'can_collect_payments': True
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
                'can_manage_settings': False,
                'can_collect_payments': True
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
                'can_manage_settings': True,
                'can_collect_payments': True
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
                'can_manage_settings': True,
                'can_collect_payments': True
            }
        }
        return permissions_map.get(role, {})
    
    submit = SubmitField('Create User')
    
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already exists.')
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

class UserEditForm(FlaskForm):
    """User edit form"""
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('New Password (leave blank to keep current)', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[
        EqualTo('password', message='Passwords must match')
    ])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=200)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    role = SelectField('Role', choices=[
        ('staff', 'Staff'),
        ('loan_collector', 'Loan Collector'),
        ('accountant', 'Accountant'),
        ('manager', 'Manager'),
        ('admin', 'Administrator')
    ], validators=[DataRequired()])
    branch_id = SelectField('Branch', coerce=int, validators=[Optional()])
    is_active = BooleanField('Active')
    
    # Permissions
    can_add_customers = BooleanField('Can Add Customers')
    can_edit_customers = BooleanField('Can Edit Customers')
    can_delete_customers = BooleanField('Can Delete Customers')
    can_manage_loans = BooleanField('Can Manage Loans')
    can_approve_loans = BooleanField('Can Approve Loans')
    can_manage_investments = BooleanField('Can Manage Investments')
    can_manage_pawnings = BooleanField('Can Manage Pawnings')
    can_view_reports = BooleanField('Can View Reports')
    can_manage_settings = BooleanField('Can Manage Settings')
    can_collect_payments = BooleanField('Can Collect Payments')
    
    submit = SubmitField('Update User')
    
    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        # Set branch choices
        from app.models import Branch
        self.branch_id.choices = [(0, '-- Select Branch --')] + [(b.id, f"{b.branch_code} - {b.name}") for b in Branch.query.filter_by(is_active=True).all()]
    
    @staticmethod
    def get_role_permissions(role):
        """Get default permissions for a role - same as UserForm"""
        return UserForm.get_role_permissions(role)

class BranchForm(FlaskForm):
    """Branch form"""
    branch_code = StringField('Branch Code', validators=[DataRequired(), Length(max=20)])
    name = StringField('Branch Name', validators=[DataRequired(), Length(max=200)])
    address = TextAreaField('Address', validators=[Optional()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    manager_id = SelectField('Manager', coerce=int, validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    
    submit = SubmitField('Save Branch')
    
    def __init__(self, *args, **kwargs):
        super(BranchForm, self).__init__(*args, **kwargs)
        from app.models import User
        # Get users who can be managers (admin or manager role)
        managers = User.query.filter(User.role.in_(['admin', 'manager']), User.is_active == True).all()
        self.manager_id.choices = [(0, '-- Select Manager --')] + [(user.id, f"{user.full_name} ({user.username})") for user in managers]
