"""Pawning forms"""
from datetime import datetime
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SelectField, DecimalField, IntegerField, DateField, TextAreaField, StringField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length

class PawningForm(FlaskForm):
    """Pawning form - Sri Lankan style with gold-focused fields"""
    customer_id = SelectField('Customer', coerce=int, choices=[], validators=[DataRequired()])
    
    # Item Details (Gold-focused)
    item_description = TextAreaField('Item Description', validators=[DataRequired()], 
                                    render_kw={'placeholder': 'E.g., Gold chain, Gold ring, Bangles, etc.'})
    item_type = SelectField('Item Category', choices=[
        ('gold', 'Gold'),
        ('jewelry', 'Gold Jewelry'),
        ('silver', 'Silver'),
        ('electronics', 'Electronics'),
        ('vehicle', 'Vehicle'),
        ('documents', 'Property Documents'),
        ('other', 'Other')
    ], validators=[DataRequired()], default='gold')
    
    number_of_items = IntegerField('Number of Items/Pieces', validators=[Optional(), NumberRange(min=1)], default=1)
    item_weight = DecimalField('Item Weight (grams)', validators=[Optional(), NumberRange(min=0)], places=3,
                              render_kw={'placeholder': 'Weight in grams'})
    item_purity = SelectField('Gold Purity/Karats', choices=[
        ('', 'Select Purity'),
        ('24K', '24 Karat (99.9% pure)'),
        ('22K', '22 Karat (91.6% pure)'),
        ('18K', '18 Karat (75% pure)'),
        ('14K', '14 Karat (58.3% pure)'),
        ('other', 'Other')
    ], validators=[Optional()])
    karats = DecimalField('Karat Value', validators=[Optional(), NumberRange(min=0, max=24)], places=2)
    
    market_value_per_gram = DecimalField('Market Rate per Gram (LKR)', validators=[Optional(), NumberRange(min=0)], 
                                        places=2, render_kw={'placeholder': 'Current gold rate per gram'})
    total_market_value = DecimalField('Total Appraised Value (LKR)', validators=[DataRequired(), NumberRange(min=0)], 
                                     places=2)
    item_photo = FileField('Item Photos', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    
    # Loan Details
    loan_amount = DecimalField('Loan Amount (LKR)', validators=[DataRequired(), NumberRange(min=0)], places=2,
                              render_kw={'placeholder': 'Amount to be given'})
    loan_to_value_ratio = DecimalField('Loan-to-Value Ratio (%)', validators=[Optional(), NumberRange(min=0, max=100)], 
                                      places=2, default=70, render_kw={'placeholder': 'Typically 60-80%'})
    interest_rate = DecimalField('Interest Rate (% per month)', validators=[DataRequired(), NumberRange(min=0, max=100)], 
                                places=2, render_kw={'placeholder': 'Monthly interest rate'})
    
    # Period
    duration_months = IntegerField('Duration (months)', validators=[DataRequired(), NumberRange(min=1, max=120)], 
                                  default=6, render_kw={'placeholder': 'Loan period in months'})
    grace_period_days = IntegerField('Grace Period (days)', validators=[Optional(), NumberRange(min=0, max=90)], 
                                    default=30, render_kw={'placeholder': 'Days after maturity before auction'})
    
    pawning_date = DateField('Pawning Date', validators=[DataRequired()], default=datetime.now)
    
    # Storage Details
    storage_location = StringField('Storage Location', validators=[Optional(), Length(max=100)],
                                  render_kw={'placeholder': 'E.g., Safe A, Vault 2'})
    storage_box_number = StringField('Box/Locker Number', validators=[Optional(), Length(max=50)])
    storage_notes = TextAreaField('Storage Notes', validators=[Optional()])
    
    notes = TextAreaField('Additional Notes', validators=[Optional()])
    submit = SubmitField('Save Pawning')

class PawningPaymentForm(FlaskForm):
    """Pawning payment form - supports interest payment and redemption"""
    payment_date = DateField('Payment Date', validators=[DataRequired()], default=datetime.now)
    payment_type = SelectField('Payment Type', choices=[
        ('interest_payment', 'Interest Payment Only'),
        ('partial_redemption', 'Partial Payment (Interest + Principal)'),
        ('full_redemption', 'Full Redemption (Settle & Collect Item)'),
        ('penalty', 'Penalty Payment')
    ], validators=[DataRequired()], default='interest_payment')
    
    # Payment amounts
    payment_amount = DecimalField('Total Payment Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    interest_amount = DecimalField('Interest Amount', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    principal_amount = DecimalField('Principal Amount', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    penalty_amount = DecimalField('Penalty Amount', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    
    # Interest period being paid (for interest payments)
    interest_period_from = DateField('Interest Period From', validators=[Optional()])
    interest_period_to = DateField('Interest Period To', validators=[Optional()])
    
    payment_method = SelectField('Payment Method', choices=[
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('card', 'Debit/Credit Card'),
        ('online', 'Online Payment')
    ], validators=[DataRequired()], default='cash')
    reference_number = StringField('Reference/Cheque Number', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Payment Notes', validators=[Optional()])
    
    # For full redemption
    confirm_redemption = BooleanField('Confirm item has been returned to customer', default=False)
    
    submit = SubmitField('Process Payment')
