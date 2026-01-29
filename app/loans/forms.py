"""Loan forms"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, DecimalField, IntegerField, DateField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length

class LoanForm(FlaskForm):
    """Loan application form"""
    customer_id = SelectField('Customer', coerce=int, choices=[], validators=[DataRequired()])
    loan_type = SelectField('Loan Type', choices=[
        ('', 'Select'),
        ('type1_9weeks', 'Type 1 - 9 Week Loan'),
        ('monthly_loan', 'Monthly Loan'),
    ], validators=[DataRequired()])
    loan_purpose = SelectField('Loan Purpose', choices=[
        ('', 'Select'),
        ('personal', 'Personal Loan'),
        ('business', 'Business Loan'),
        ('education', 'Education Loan'),
        ('vehicle', 'Vehicle Loan'),
        ('home', 'Home Loan'),
        ('agriculture', 'Agriculture Loan'),
        ('other', 'Other')
    ], validators=[Optional()])
    
    loan_amount = DecimalField('Loan Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    duration_weeks = IntegerField('Duration (Weeks)', validators=[Optional(), NumberRange(min=1, max=52)])
    interest_rate = DecimalField('Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0, max=100)], places=2)
    interest_type = SelectField('Interest Type', choices=[
        ('reducing_balance', 'Reducing Balance'),
        ('flat', 'Flat Rate')
    ], validators=[Optional()])
    
    duration_months = IntegerField('Duration (Months)', validators=[Optional(), NumberRange(min=1, max=360)])
    installment_frequency = SelectField('Installment Frequency', choices=[
        ('monthly', 'Monthly'),
        ('weekly', 'Weekly'),
        ('quarterly', 'Quarterly')
    ], validators=[Optional()])
    
    application_date = DateField('Application Date', validators=[DataRequired()])
    purpose = TextAreaField('Purpose of Loan', validators=[Optional()])
    security_details = TextAreaField('Security/Collateral Details', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('active', 'Active')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    document = FileField('Upload Document (PDF)', validators=[Optional(), FileAllowed(['pdf'], 'PDF files only!')])
    
    submit = SubmitField('Save Loan')

class LoanApprovalForm(FlaskForm):
    """Loan approval form"""
    approval_status = SelectField('Approval Status', choices=[
        ('', 'Select'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], validators=[DataRequired()])
    approval_date = DateField('Approval Date', validators=[DataRequired()])
    approved_amount = DecimalField('Approved Amount', validators=[Optional(), NumberRange(min=0)], places=2)
    disbursement_date = DateField('Disbursement Date', validators=[Optional()])
    disbursement_method = SelectField('Disbursement Method', choices=[
        ('', 'Select'),
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque')
    ], validators=[Optional()])
    disbursement_reference = StringField('Disbursement Reference', validators=[Optional(), Length(max=100)])
    first_installment_date = DateField('First Installment Date', validators=[Optional()])
    approval_notes = TextAreaField('Approval Notes', validators=[Optional()])
    rejection_reason = TextAreaField('Rejection Reason', validators=[Optional()])
    send_notification = BooleanField('Send SMS/Email Notification', default=True)
    submit = SubmitField('Submit')

class LoanPaymentForm(FlaskForm):
    """Loan payment form"""
    payment_date = DateField('Payment Date', validators=[DataRequired()])
    payment_amount = DecimalField('Payment Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    principal_amount = DecimalField('Principal Amount', validators=[Optional(), NumberRange(min=0)], places=2)
    interest_amount = DecimalField('Interest Amount', validators=[Optional(), NumberRange(min=0)], places=2)
    penalty_amount = DecimalField('Penalty Amount', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    payment_method = SelectField('Payment Method', choices=[
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('card', 'Card'),
        ('online', 'Online Payment')
    ], validators=[DataRequired()])
    reference_number = StringField('Reference Number', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notes', validators=[Optional()])
    send_receipt = BooleanField('Send Payment Receipt', default=True)
    submit = SubmitField('Add Payment')
