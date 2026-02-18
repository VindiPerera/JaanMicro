"""Customer forms"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, DateField, SelectField, TextAreaField, DecimalField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length, ValidationError
from app.models import Customer
from datetime import datetime, date, timedelta

def calculate_dob_from_nic(nic):
    """Calculate date of birth from Sri Lankan NIC"""
    nic = nic.strip().upper()
    
    if len(nic) == 10 and nic[-1] in ['V', 'X'] and nic[:-1].isdigit():
        # Old NIC: 9 digits + V/X
        year = 1900 + int(nic[:2])
        day_of_year = int(nic[2:5])
    elif len(nic) == 12 and nic.isdigit():
        # New NIC: 12 digits
        year = int(nic[:4])
        day_of_year = int(nic[4:7])
    else:
        return None
    
    # Adjust for gender (female days start from 500+)
    if day_of_year > 500:
        day_of_year -= 500
    
    # Create date from year and day of year
    try:
        dob = date(year, 1, 1) + timedelta(days=day_of_year - 1)
        return dob
    except ValueError:
        return None

def calculate_age(dob):
    """Calculate age from date of birth"""
    if not dob:
        return None
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age

class CustomerForm(FlaskForm):
    """Customer registration form"""
    # Personal Information
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=200)])
    nic_number = StringField('NIC Number', validators=[DataRequired(), Length(max=20)])
    
    # Customer Type - Multiple selection with checkboxes
    customer_type_customer = BooleanField('Customer')
    customer_type_investor = BooleanField('Loan Borrower')
    customer_type_guarantor = BooleanField('Guarantor')
    customer_type_family_guarantor = BooleanField('Family Guarantor')
    
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    gender = SelectField('Gender', choices=[('', 'Select'), ('male', 'Male'), ('female', 'Female'), ('other', 'Other')], validators=[Optional()])
    marital_status = SelectField('Marital Status', choices=[('', 'Select'), ('single', 'Single'), ('married', 'Married'), ('divorced', 'Divorced'), ('widowed', 'Widowed')], validators=[Optional()])

    profile_picture = FileField('Profile Picture', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    
    # KYC Documents - All optional, validation handled in custom validate method
    nic_front_image = FileField('NIC Front Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Images and PDFs only!')
    ])
    nic_back_image = FileField('NIC Back Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Images and PDFs only!')
    ])
    photo = FileField('Customer Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    proof_of_address = FileField('Proof of Address', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Images and PDFs only!')
    ])
    bank_book_image = FileField('Bank Book Front Page', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Images and PDFs only!')
    ])
    
    # Contact Information
    phone_primary = StringField('Primary Phone', validators=[DataRequired(), Length(max=20)])
    phone_secondary = StringField('Secondary Phone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    address_line1 = StringField('Address Line 1', validators=[DataRequired(), Length(max=255)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=255)])
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    district = SelectField('District', choices=[
        ('', 'Select District'),
        ('Ampara', 'Ampara'),
        ('Anuradhapura', 'Anuradhapura'),
        ('Badulla', 'Badulla'),
        ('Batticaloa', 'Batticaloa'),
        ('Colombo', 'Colombo'),
        ('Galle', 'Galle'),
        ('Gampaha', 'Gampaha'),
        ('Hambantota', 'Hambantota'),
        ('Jaffna', 'Jaffna'),
        ('Kalutara', 'Kalutara'),
        ('Kandy', 'Kandy'),
        ('Kegalle', 'Kegalle'),
        ('Kilinochchi', 'Kilinochchi'),
        ('Kurunegala', 'Kurunegala'),
        ('Mannar', 'Mannar'),
        ('Matale', 'Matale'),
        ('Matara', 'Matara'),
        ('Monaragala', 'Monaragala'),
        ('Mullaitivu', 'Mullaitivu'),
        ('Nuwara Eliya', 'Nuwara Eliya'),
        ('Polonnaruwa', 'Polonnaruwa'),
        ('Puttalam', 'Puttalam'),
        ('Ratnapura', 'Ratnapura'),
        ('Trincomalee', 'Trincomalee'),
        ('Vavuniya', 'Vavuniya')
    ], validators=[DataRequired()])
    postal_code = StringField('Postal Code', validators=[Optional(), Length(max=10)])
    
    # Employment Information
    occupation = StringField('Occupation', validators=[Optional(), Length(max=100)])
    employer_name = StringField('Employer Name', validators=[Optional(), Length(max=200)])
    monthly_income = DecimalField('Monthly Income', validators=[Optional()], places=2)
    employment_type = SelectField('Employment Type', choices=[('', 'Select'), ('permanent', 'Permanent'), ('contract', 'Contract'), ('self_employed', 'Self Employed'), ('unemployed', 'Unemployed')], validators=[Optional()])
    
    # Emergency Contact
    emergency_contact_name = StringField('Emergency Contact Name', validators=[Optional(), Length(max=200)])
    emergency_contact_phone = StringField('Emergency Contact Phone', validators=[Optional(), Length(max=20)])
    emergency_contact_relation = StringField('Relation', validators=[Optional(), Length(max=50)])
    
    # Guarantor Information
    guarantor_name = StringField('Guarantor Name', validators=[Optional(), Length(max=200)])
    guarantor_nic = StringField('Guarantor NIC', validators=[Optional(), Length(max=20)])
    guarantor_phone = StringField('Guarantor Phone', validators=[Optional(), Length(max=20)])
    guarantor_address = TextAreaField('Guarantor Address', validators=[Optional()])

    # Bank Information
    bank_name = StringField('Bank Name', validators=[Optional(), Length(max=100)])
    bank_branch = StringField('Bank Branch', validators=[Optional(), Length(max=100)])
    bank_account_number = StringField('Account Number', validators=[Optional(), Length(max=30)])
    bank_account_type = SelectField('Account Type', choices=[('', 'Select'), ('savings', 'Savings'), ('current', 'Current'), ('fixed', 'Fixed Deposit')], validators=[Optional()])
    
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Member')
    
    def __init__(self, *args, **kwargs):
        # Extract custom parameters before calling super().__init__
        self.original_nic = kwargs.pop('original_nic', None)
        is_edit = kwargs.pop('is_edit', False)
        customer = kwargs.get('obj')
        
        # Get original NIC from obj if available and not already set
        if customer and not self.original_nic:
            self.original_nic = customer.nic_number
        
        super(CustomerForm, self).__init__(*args, **kwargs)
        
        # Initialize customer type checkboxes only for GET requests (when obj is provided)
        if customer:
            customer_types = customer.customer_types
            self.customer_type_customer.data = 'customer' in customer_types
            self.customer_type_investor.data = 'investor' in customer_types
            self.customer_type_guarantor.data = 'guarantor' in customer_types
            self.customer_type_family_guarantor.data = 'family_guarantor' in customer_types
        elif not is_edit:
            # Default for new customers
            self.customer_type_customer.data = True
        
        # Make KYC fields required only when adding new customer
        if not is_edit:
            # For new customers, make KYC documents required (except Customer Photo which is optional)
            self.nic_front_image.validators.insert(0, DataRequired('NIC Front Image is required'))
            self.nic_back_image.validators.insert(0, DataRequired('NIC Back Image is required'))
            self.proof_of_address.validators.insert(0, DataRequired('Proof of Address is required'))
        else:
            # For editing, make KYC documents optional (remove DataRequired if present)
            for field in [self.nic_front_image, self.nic_back_image, self.photo, self.proof_of_address]:
                field.validators = [v for v in field.validators if not isinstance(v, DataRequired)]
    
    def validate_nic_number(self, field):
        if field.data != self.original_nic:
            customer = Customer.query.filter_by(nic_number=field.data).first()
            if customer:
                raise ValidationError('NIC number already registered.')
            
            # Check age from NIC
            dob = calculate_dob_from_nic(field.data)
            if dob:
                age = calculate_age(dob)
                if age is not None and age < 18:
                    raise ValidationError('Customer must be 18 years or older to register.')
    
    def validate(self, extra_validators=None):
        """Custom validation to ensure at least one customer type is selected"""
        if not super().validate(extra_validators=extra_validators):
            return False
        
        # Check if at least one customer type is selected
        customer_types = [
            self.customer_type_customer.data,
            self.customer_type_investor.data,
            self.customer_type_guarantor.data,
            self.customer_type_family_guarantor.data
        ]
        
        if not any(customer_types):
            self.customer_type_customer.errors.append('At least one customer type must be selected.')
            return False
        
        return True

class KYCForm(FlaskForm):
    """KYC verification form"""
    kyc_verified = BooleanField('Verify KYC')
    submit = SubmitField('Update KYC')
