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
    customer_type = SelectField('Customer Type', choices=[('customer', 'Customer'), ('investor', 'Loan Borrower'), ('guarantor', 'Guarantor'), ('family_guarantor', 'Family Guarantor')], validators=[DataRequired()])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    gender = SelectField('Gender', choices=[('', 'Select'), ('male', 'Male'), ('female', 'Female'), ('other', 'Other')], validators=[Optional()])
    marital_status = SelectField('Marital Status', choices=[('', 'Select'), ('single', 'Single'), ('married', 'Married'), ('divorced', 'Divorced'), ('widowed', 'Widowed')], validators=[Optional()])

    profile_picture = FileField('Profile Picture', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    
    # KYC Documents
    nic_front_image = FileField('NIC Front Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Images and PDFs only!')
    ])
    nic_back_image = FileField('NIC Back Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Images and PDFs only!')
    ])
    photo = FileField('Customer Photo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    proof_of_address = FileField('Proof of Address', validators=[
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
        super(CustomerForm, self).__init__(*args, **kwargs)
        self.original_nic = kwargs.get('obj').nic_number if kwargs.get('obj') else None
        
        # Make KYC fields required only when adding new customer (obj is None)
        # When editing (obj is provided), make them optional
        is_edit = kwargs.get('obj') is not None
        
        if not is_edit:
            # For new customers, make KYC documents required
            self.nic_front_image.validators.insert(0, DataRequired('NIC Front Image is required'))
            self.nic_back_image.validators.insert(0, DataRequired('NIC Back Image is required'))
            self.photo.validators.insert(0, DataRequired('Customer Photo is required'))
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

class KYCForm(FlaskForm):
    """KYC verification form"""
    kyc_verified = BooleanField('Verify KYC')
    submit = SubmitField('Update KYC')
