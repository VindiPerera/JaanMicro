"""Borrower forms"""
from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, IntegerField, DateField, TextAreaField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length

class InvestmentForm(FlaskForm):
    """Borrower form"""
    customer_id = SelectField('Customer', coerce=int, choices=[], validators=[DataRequired()])
    investment_type = SelectField('Borrower Type', choices=[
        ('', 'Select'),
        ('fixed_deposit', 'Fixed Deposit'),
        ('savings', 'Savings Account'),
        ('recurring_deposit', 'Recurring Deposit'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    
    principal_amount = DecimalField('Principal Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    interest_rate = DecimalField('Interest Rate (% per annum)', validators=[DataRequired(), NumberRange(min=0, max=100)], places=2)
    duration_months = IntegerField('Duration (Months)', validators=[Optional(), NumberRange(min=1, max=360)])
    
    start_date = DateField('Start Date', validators=[DataRequired()])
    
    installment_amount = DecimalField('Installment Amount', validators=[Optional(), NumberRange(min=0)], places=2)
    installment_frequency = SelectField('Installment Frequency', choices=[
        ('', 'Select'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly')
    ], validators=[Optional()])
    
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Borrower')

class InvestmentTransactionForm(FlaskForm):
    """Borrower transaction form"""
    transaction_date = DateField('Transaction Date', validators=[DataRequired()])
    transaction_type = SelectField('Transaction Type', choices=[
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('interest_credit', 'Interest Credit')
    ], validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    payment_method = SelectField('Payment Method', choices=[
        ('', 'Select'),
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('card', 'Card'),
        ('online', 'Online Payment')
    ], validators=[Optional()])
    reference_number = StringField('Reference Number', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Add Transaction')
