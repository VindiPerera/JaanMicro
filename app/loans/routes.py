"""Loan management routes"""
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os
from app import db
from app.loans import loans_bp
from app.models import Loan, LoanPayment, Customer, ActivityLog, SystemSettings, User
from app.loans.forms import LoanForm, LoanPaymentForm, LoanApprovalForm, StaffApprovalForm, ManagerApprovalForm, InitiateLoanForm, AdminApprovalForm, LoanDeactivationForm
from app.utils.decorators import permission_required, admin_required
from app.utils.helpers import generate_loan_number, get_current_branch_id, should_filter_by_branch

@loans_bp.route('/')
@login_required
@permission_required('manage_loans')
def list_loans():
    """List all loans"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    loan_type = request.args.get('loan_type', '')
    referred_by = request.args.get('referred_by', type=int)
    
    query = Loan.query
    
    # Filter by current branch if needed
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            query = query.filter_by(branch_id=current_branch_id)
    
    if search:
        query = query.join(Customer).filter(
            db.or_(
                Loan.loan_number.ilike(f'%{search}%'),
                Customer.full_name.ilike(f'%{search}%'),
                Customer.customer_id.ilike(f'%{search}%')
            )
        )
    
    if status:
        query = query.filter_by(status=status)
    
    if loan_type:
        query = query.filter_by(loan_type=loan_type)
    
    if referred_by:
        query = query.filter_by(referred_by=referred_by)
    
    loans = query.order_by(Loan.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get users for referrer filter
    user_query = User.query.filter_by(is_active=True)
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            user_query = user_query.filter_by(branch_id=current_branch_id)
    users = user_query.order_by(User.full_name).all()
    
    return render_template('loans/list.html',
                         title='Loans',
                         loans=loans,
                         search=search,
                         status=status,
                         loan_type=loan_type,
                         referred_by=referred_by,
                         users=users)

@loans_bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('manage_loans')
def add_loan():
    """Add new loan"""
    form = LoanForm()
    
    # Get users for referred_by dropdown
    user_query = User.query.filter_by(is_active=True)
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            user_query = user_query.filter_by(branch_id=current_branch_id)
    
    users = user_query.order_by(User.full_name).all()
    form.referred_by.choices = [(0, 'Select User (Optional)')] + [(u.id, f'{u.full_name} ({u.username})') for u in users]
    
    # Pre-fill interest rate from settings on GET request
    if request.method == 'GET':
        settings = SystemSettings.get_settings()
        form.interest_rate.data = settings.default_loan_interest_rate
        form.interest_type.data = settings.interest_calculation_method
        form.duration_months.data = settings.default_loan_duration
        form.installment_frequency.data = 'monthly'  # Default for monthly loans
    
    if form.validate_on_submit():
        # Custom validation based on loan type
        if form.loan_type.data == 'type1_9weeks':
            # For Type 1 loans, validate weeks instead of months
            if not form.duration_weeks.data:
                flash('Duration (Weeks) is required for Type 1 - 9 Week Loan!', 'error')
                return render_template('loans/add.html', title='Add Loan', form=form)
        elif form.loan_type.data == '54_daily':
            # For 54 Daily loans, validate days instead of months
            if not form.duration_days.data:
                flash('Duration (Days) is required for 54 Daily Loan!', 'error')
                return render_template('loans/add.html', title='Add Loan', form=form)
        elif form.loan_type.data == 'type4_micro':
            # For Type 4 Micro loans, validate months (will convert to weeks internally)
            if not form.duration_months.data:
                flash('Duration (Months) is required for Type 4 - Micro Loan!', 'error')
                return render_template('loans/add.html', title='Add Loan', form=form)
        elif form.loan_type.data == 'type4_daily':
            # For Type 4 Daily loans, validate months (will convert to days internally)
            if not form.duration_months.data:
                flash('Duration (Months) is required for Type 4 - Daily Loan!', 'error')
                return render_template('loans/add.html', title='Add Loan', form=form)
        elif form.loan_type.data == 'monthly_loan':
            # For Monthly loans, validate months, interest type, and installment frequency
            if not form.duration_months.data:
                flash('Duration (Months) is required for Monthly Loan!', 'error')
                return render_template('loans/add.html', title='Add Loan', form=form)
            if not form.interest_type.data:
                flash('Interest Type is required for Monthly Loan!', 'error')
                return render_template('loans/add.html', title='Add Loan', form=form)
        else:
            # For other loan types, validate months, interest type, and installment frequency
            if not form.duration_months.data:
                flash('Duration (Months) is required!', 'error')
                return render_template('loans/add.html', title='Add Loan', form=form)
            if not form.interest_type.data:
                flash('Interest Type is required!', 'error')
                return render_template('loans/add.html', title='Add Loan', form=form)
            if not form.installment_frequency.data:
                flash('Installment Frequency is required!', 'error')
                return render_template('loans/add.html', title='Add Loan', form=form)
        
        # Validate customer selection
        if form.customer_id.data == 0:
            flash('Please select a customer!', 'error')
            return render_template('loans/add.html', title='Add Loan', form=form)
        
        # Get customer to determine branch
        customer = Customer.query.get(form.customer_id.data)
        if not customer:
            flash('Customer not found!', 'error')
            return render_template('loans/add.html', title='Add Loan', form=form)
        
        if not customer.branch_id:
            flash('Customer does not have a valid branch assigned!', 'error')
            return render_template('loans/add.html', title='Add Loan', form=form)
        
        # Generate loan number with new format: YY/B##/TYPE/#####
        loan_number = generate_loan_number(loan_type=form.loan_type.data, branch_id=customer.branch_id)
        
        # Calculate EMI using Decimal arithmetic
        from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
        
        loan_amount = Decimal(str(form.loan_amount.data))
        interest_rate = Decimal(str(form.interest_rate.data))
        
        # Determine duration and calculation method based on loan type
        duration_weeks = None
        duration_days = None
        duration_months = form.duration_months.data
        
        # Check if this is a Type 1 - 9 week loan
        if form.loan_type.data == 'type1_9weeks':
            duration_weeks = form.duration_weeks.data or 9
            duration_months = 0  # Not used for weekly loans
            # Type 1 calculation: Interest = Interest rate * 2
            # Installment = ((100 + Interest) * Loan Amount) / (100 * weeks)
            interest = interest_rate * Decimal('2')
            emi = ((Decimal('100') + interest) * loan_amount) / (Decimal('100') * Decimal(str(duration_weeks)))
            # Floor to whole number to get exact total
            emi = emi.quantize(Decimal('1'), rounding=ROUND_DOWN)
            total_payable = (emi * Decimal(str(duration_weeks))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif form.loan_type.data == '54_daily':
            duration_days = form.duration_days.data or 54
            duration_months = 0  # Not used for daily loans
            # Same formula as Type 1 but using days instead of weeks
            # Installment = ((100 + Interest) * Loan Amount) / (100 * days)
            interest = interest_rate * Decimal('2')
            emi = ((Decimal('100') + interest) * loan_amount) / (Decimal('100') * Decimal(str(duration_days)))
            # Floor to whole number to get exact total
            emi = emi.quantize(Decimal('1'), rounding=ROUND_DOWN)
            total_payable = (emi * Decimal(str(duration_days))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif form.loan_type.data == 'type4_micro':
            # Type 4 Micro Loan: Uses months as input, converts to weeks
            # Full Interest = Interest Rate * Months
            # Weeks = Months * 4
            # Installment = LA * ((Full Interest + 100) / 100) / Weeks
            months = form.duration_months.data
            duration_weeks = months * 4
            full_interest = interest_rate * Decimal(str(months))
            emi = (loan_amount * ((full_interest + Decimal('100')) / Decimal('100'))) / Decimal(str(duration_weeks))
            emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_payable = (emi * Decimal(str(duration_weeks))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif form.loan_type.data == 'type4_daily':
            # Type 4 Daily Loan: Uses months as input, converts to days (1 month = 25 days)
            # Full Interest = Interest Rate * Months
            # Days = Months * 25
            # Installment = LA * ((Full Interest + 100) / 100) / Days
            months = form.duration_months.data
            duration_days = months * 25
            full_interest = interest_rate * Decimal(str(months))
            emi = (loan_amount * ((full_interest + Decimal('100')) / Decimal('100'))) / Decimal(str(duration_days))
            emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_payable = (emi * Decimal(str(duration_days))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif form.loan_type.data == 'monthly_loan':
            # Monthly Loan: Standard monthly calculation
            monthly_rate = interest_rate / (Decimal('12') * Decimal('100'))
            n = duration_months
            
            if form.interest_type.data == 'reducing_balance' and monthly_rate > 0:
                # EMI = [P x R x (1+R)^N]/[(1+R)^N-1]
                mr_float = float(monthly_rate)
                power_calc = ((1 + mr_float) ** n) / (((1 + mr_float) ** n) - 1)
                emi = loan_amount * monthly_rate * Decimal(str(power_calc))
            else:
                # Flat rate calculation
                total_interest = loan_amount * interest_rate * Decimal(str(n)) / (Decimal('12') * Decimal('100'))
                emi = (loan_amount + total_interest) / Decimal(str(n))
            
            emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_payable = (emi * Decimal(str(n))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            # Standard monthly calculation
            monthly_rate = interest_rate / (Decimal('12') * Decimal('100'))
            n = duration_months
            
            if form.interest_type.data == 'reducing_balance' and monthly_rate > 0:
                # Convert to float for power calculation, then back to Decimal
                mr_float = float(monthly_rate)
                power_calc = ((1 + mr_float) ** n) / (((1 + mr_float) ** n) - 1)
                emi = loan_amount * monthly_rate * Decimal(str(power_calc))
            else:
                total_interest = loan_amount * interest_rate * Decimal(str(n)) / (Decimal('12') * Decimal('100'))
                emi = (loan_amount + total_interest) / Decimal(str(n))
            
            emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_payable = (emi * Decimal(str(n))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Handle document upload
        document_filename = None
        if form.document.data and hasattr(form.document.data, 'filename') and form.document.data.filename:
            file = form.document.data
            filename = secure_filename(file.filename)
            # Create unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            document_filename = f"{timestamp}_{filename}"
            
            # Create upload directory if it doesn't exist
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'loans')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(upload_folder, document_filename)
            file.save(file_path)
            
            # Store relative path
            document_filename = f"loans/{document_filename}"
        
        # Calculate documentation fee (1% of loan amount)
        documentation_fee = (loan_amount * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Disbursed amount will be calculated during approval (loan amount minus documentation fee)
        # For pending loans, these remain None until approved
        actual_disbursed_amount = None
        
        loan = Loan(
            loan_number=loan_number,
            customer_id=form.customer_id.data,
            branch_id=customer.branch_id,
            loan_type=form.loan_type.data,
            loan_purpose=form.loan_purpose.data if form.loan_purpose.data else None,
            loan_amount=form.loan_amount.data,
            interest_rate=form.interest_rate.data,
            interest_type=form.interest_type.data,
            duration_months=duration_months,
            duration_weeks=duration_weeks,
            duration_days=duration_days,
            installment_amount=emi,
            installment_frequency='daily' if duration_days else ('weekly' if duration_weeks else form.installment_frequency.data),
            disbursed_amount=actual_disbursed_amount,
            total_payable=total_payable,
            outstanding_amount=None,  # Will be set during approval
            documentation_fee=documentation_fee,
            application_date=form.application_date.data,
            purpose=form.purpose.data,
            security_details=form.security_details.data,
            document_path=document_filename,
            guarantor_ids=request.form.get('guarantor_ids', ''),
            status='pending',  # All new loans start as pending and go through approval workflow
            created_by=current_user.id,
            referred_by=form.referred_by.data if form.referred_by.data != 0 else None,
            notes=form.notes.data
        )
        
        # Note: Disbursement details will be set during admin approval stage
        
        db.session.add(loan)
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='create_loan',
            entity_type='loan',
            description=f'Created loan: {loan.loan_number}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'Loan {loan.loan_number} created successfully!', 'success')
        return redirect(url_for('loans.view_loan', id=loan.id))
    
    return render_template('loans/add.html', title='Add Loan', form=form)

@loans_bp.route('/edit-loan-select')
@login_required
@admin_required
def edit_loan_select():
    """Select loan to edit (Admin only)"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status = request.args.get('status', '', type=str)
    loan_type = request.args.get('loan_type', '', type=str)
    
    query = Loan.query
    
    # Filter by current branch if needed
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            query = query.filter_by(branch_id=current_branch_id)
    
    if search:
        query = query.join(Customer).filter(
            db.or_(
                Loan.loan_number.ilike(f'%{search}%'),
                Customer.full_name.ilike(f'%{search}%'),
                Customer.customer_id.ilike(f'%{search}%')
            )
        )
    
    if status:
        query = query.filter_by(status=status)
    
    if loan_type:
        query = query.filter_by(loan_type=loan_type)
    
    loans = query.order_by(Loan.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    
    return render_template('loans/edit_select.html',
                         title='Edit Loan - Select Loan',
                         loans=loans,
                         search=search,
                         status=status,
                         loan_type=loan_type)

@loans_bp.route('/<int:id>')
@login_required
def view_loan(id):
    """View loan details"""
    loan = Loan.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and loan.branch_id != current_branch_id:
            flash('Access denied: Loan not found in current branch.', 'danger')
            return redirect(url_for('loans.list_loans'))
    
    # Calculate current outstanding amount with accrued interest
    current_outstanding = loan.calculate_current_outstanding()
    accrued_interest = loan.calculate_accrued_interest()
    
    # Update the loan's stored outstanding amount to reflect current calculation
    loan.update_outstanding_amount()
    db.session.commit()
    
    # Get guarantors
    guarantors = []
    if loan.guarantor_ids:
        guarantor_id_list = [int(gid.strip()) for gid in loan.guarantor_ids.split(',') if gid.strip()]
        if guarantor_id_list:
            guarantors = Customer.query.filter(Customer.id.in_(guarantor_id_list)).all()
    
    # Get arrears details
    arrears_details = loan.get_arrears_details()
    
    return render_template('loans/view.html',
                         title=f'Loan: {loan.loan_number}',
                         loan=loan,
                         guarantors=guarantors,
                         current_outstanding=current_outstanding,
                         accrued_interest=accrued_interest,
                         arrears_details=arrears_details)

@loans_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_loan(id):
    """Edit loan (Admin only)"""
    loan = Loan.query.get_or_404(id)
    
    form = LoanForm()
    
    # Get users for referred_by dropdown
    user_query = User.query.filter_by(is_active=True)
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            user_query = user_query.filter_by(branch_id=current_branch_id)
    
    users = user_query.order_by(User.full_name).all()
    form.referred_by.choices = [(0, 'Select User (Optional)')] + [(u.id, f'{u.full_name} ({u.username})') for u in users]
    
    if request.method == 'GET':
        # Pre-populate form with existing loan data
        customer = loan.customer
        form.customer_search.data = f"{customer.full_name} ({customer.customer_id})"
        form.customer_id.data = loan.customer_id
        form.referred_by.data = loan.referred_by if loan.referred_by else 0
        form.application_date.data = loan.application_date
        form.loan_type.data = loan.loan_type
        form.loan_purpose.data = loan.loan_purpose
        form.loan_amount.data = loan.loan_amount
        form.duration_weeks.data = loan.duration_weeks
        form.duration_days.data = loan.duration_days
        form.duration_months.data = loan.duration_months
        form.interest_rate.data = loan.interest_rate
        form.interest_type.data = loan.interest_type
        form.installment_frequency.data = loan.installment_frequency
        form.purpose.data = loan.purpose
        form.security_details.data = loan.security_details
        form.notes.data = loan.notes
    
    if form.validate_on_submit():
        # Custom validation based on loan type
        if form.loan_type.data == 'type1_9weeks':
            if not form.duration_weeks.data:
                flash('Duration (Weeks) is required for Type 1 - 9 Week Loan!', 'error')
                return render_template('loans/edit.html', title='Edit Loan', form=form, loan=loan)
        elif form.loan_type.data == '54_daily':
            if not form.duration_days.data:
                flash('Duration (Days) is required for 54 Daily Loan!', 'error')
                return render_template('loans/edit.html', title='Edit Loan', form=form, loan=loan)
        elif form.loan_type.data in ['type4_micro', 'type4_daily', 'monthly_loan']:
            if not form.duration_months.data:
                flash('Duration (Months) is required for this loan type!', 'error')
                return render_template('loans/edit.html', title='Edit Loan', form=form, loan=loan)
        
        # Validate customer selection
        if form.customer_id.data == 0:
            flash('Please select a customer!', 'error')
            return render_template('loans/edit.html', title='Edit Loan', form=form, loan=loan)
        
        # Get customer to determine branch
        customer = Customer.query.get(form.customer_id.data)
        if not customer:
            flash('Customer not found!', 'error')
            return render_template('loans/edit.html', title='Edit Loan', form=form, loan=loan)
        
        # Recalculate EMI and totals with updated values
        from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
        
        loan_amount = Decimal(str(form.loan_amount.data))
        interest_rate = Decimal(str(form.interest_rate.data))
        
        duration_weeks = None
        duration_days = None
        duration_months = form.duration_months.data
        
        # Calculate based on loan type
        if form.loan_type.data == 'type1_9weeks':
            duration_weeks = form.duration_weeks.data or 9
            duration_months = 0
            interest = interest_rate * Decimal('2')
            emi = ((Decimal('100') + interest) * loan_amount) / (Decimal('100') * Decimal(str(duration_weeks)))
            emi = emi.quantize(Decimal('1'), rounding=ROUND_DOWN)
            total_payable = (emi * Decimal(str(duration_weeks))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif form.loan_type.data == '54_daily':
            duration_days = form.duration_days.data or 54
            duration_months = 0
            interest = interest_rate * Decimal('2')
            emi = ((Decimal('100') + interest) * loan_amount) / (Decimal('100') * Decimal(str(duration_days)))
            emi = emi.quantize(Decimal('1'), rounding=ROUND_DOWN)
            total_payable = (emi * Decimal(str(duration_days))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif form.loan_type.data == 'type4_micro':
            months = form.duration_months.data
            duration_weeks = months * 4
            full_interest = interest_rate * Decimal(str(months))
            emi = (loan_amount * ((full_interest + Decimal('100')) / Decimal('100'))) / Decimal(str(duration_weeks))
            emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_payable = (emi * Decimal(str(duration_weeks))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif form.loan_type.data == 'type4_daily':
            months = form.duration_months.data
            duration_days = months * 30
            full_interest = interest_rate * Decimal(str(months))
            emi = (loan_amount * ((full_interest + Decimal('100')) / Decimal('100'))) / Decimal(str(duration_days))
            emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_payable = (emi * Decimal(str(duration_days))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif form.loan_type.data == 'monthly_loan':
            monthly_rate = interest_rate / (Decimal('12') * Decimal('100'))
            n = duration_months
            
            if form.interest_type.data == 'reducing_balance' and monthly_rate > 0:
                mr_float = float(monthly_rate)
                power_calc = ((1 + mr_float) ** n) / (((1 + mr_float) ** n) - 1)
                emi = loan_amount * monthly_rate * Decimal(str(power_calc))
            else:
                total_interest = loan_amount * interest_rate * Decimal(str(n)) / (Decimal('12') * Decimal('100'))
                emi = (loan_amount + total_interest) / Decimal(str(n))
            
            emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_payable = (emi * Decimal(str(n))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            monthly_rate = interest_rate / (Decimal('12') * Decimal('100'))
            n = duration_months
            
            if form.interest_type.data == 'reducing_balance' and monthly_rate > 0:
                mr_float = float(monthly_rate)
                power_calc = ((1 + mr_float) ** n) / (((1 + mr_float) ** n) - 1)
                emi = loan_amount * monthly_rate * Decimal(str(power_calc))
            else:
                total_interest = loan_amount * interest_rate * Decimal(str(n)) / (Decimal('12') * Decimal('100'))
                emi = (loan_amount + total_interest) / Decimal(str(n))
            
            emi = emi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_payable = (emi * Decimal(str(n))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Handle document upload
        if form.document.data and hasattr(form.document.data, 'filename') and form.document.data.filename:
            file = form.document.data
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            document_filename = f"{timestamp}_{filename}"
            
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'loans')
            os.makedirs(upload_folder, exist_ok=True)
            
            file_path = os.path.join(upload_folder, document_filename)
            file.save(file_path)
            
            loan.document_path = f"loans/{document_filename}"
        
        # Calculate documentation fee (1% of loan amount)
        documentation_fee = (loan_amount * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Update loan data
        loan.customer_id = form.customer_id.data
        loan.branch_id = customer.branch_id
        loan.loan_type = form.loan_type.data
        loan.loan_purpose = form.loan_purpose.data
        loan.loan_amount = form.loan_amount.data
        loan.interest_rate = form.interest_rate.data
        loan.interest_type = form.interest_type.data
        loan.duration_months = duration_months
        loan.duration_weeks = duration_weeks
        loan.duration_days = duration_days
        loan.installment_amount = emi
        loan.installment_frequency = 'daily' if duration_days else ('weekly' if duration_weeks else form.installment_frequency.data)
        loan.total_payable = total_payable
        loan.documentation_fee = documentation_fee
        loan.application_date = form.application_date.data
        loan.purpose = form.purpose.data
        loan.security_details = form.security_details.data
        loan.referred_by = form.referred_by.data if form.referred_by.data != 0 else None
        loan.notes = form.notes.data
        loan.updated_at = datetime.utcnow()
        
        # Recalculate disbursed amount if loan is already active
        if loan.status == 'active' and loan.approved_amount:
            loan.disbursed_amount = loan.approved_amount - documentation_fee
        
        # Update outstanding amount if needed for active loans
        if loan.status == 'active':
            # Recalculate outstanding as total payable minus paid amount
            loan.outstanding_amount = total_payable - (loan.paid_amount or Decimal('0'))
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='edit_loan',
            entity_type='loan',
            description=f'Edited loan: {loan.loan_number}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'Loan {loan.loan_number} updated successfully!', 'success')
        return redirect(url_for('loans.view_loan', id=loan.id))
    
    return render_template('loans/edit.html', title='Edit Loan', form=form, loan=loan)

@loans_bp.route('/<int:id>/approve', methods=['GET', 'POST'])
@login_required
@permission_required('approve_loans')
def approve_loan(id):
    """Approve loan"""
    loan = Loan.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and loan.branch_id != current_branch_id:
            flash('Access denied: Loan not found in current branch.', 'danger')
            return redirect(url_for('loans.list_loans'))
    
    if loan.status != 'pending':
        flash('Only pending loans can be approved!', 'warning')
        return redirect(url_for('loans.view_loan', id=id))
    
    form = LoanApprovalForm()
    
    if form.validate_on_submit():
        loan.approval_date = form.approval_date.data
        loan.approved_by = current_user.id
        loan.approval_notes = form.approval_notes.data
        
        if form.approval_status.data == 'approved':
            loan.status = 'active'
            loan.approved_amount = form.approved_amount.data or loan.loan_amount
            loan.disbursed_amount = loan.approved_amount or loan.loan_amount
            loan.disbursement_date = form.disbursement_date.data
            loan.disbursement_method = form.disbursement_method.data
            loan.disbursement_reference = form.disbursement_reference.data
            loan.first_installment_date = form.first_installment_date.data
            loan.maturity_date = loan.disbursement_date + relativedelta(months=loan.duration_months) if loan.disbursement_date else None
            # Set initial outstanding amount to total payable (principal + interest)
            loan.outstanding_amount = loan.total_payable if loan.total_payable else (loan.approved_amount or loan.loan_amount)
            
            # Log activity
            log = ActivityLog(
                user_id=current_user.id,
                action='approve_loan',
                entity_type='loan',
                entity_id=loan.id,
                description=f'Approved loan: {loan.loan_number}',
                ip_address=request.remote_addr
            )
            flash('Loan approved successfully!', 'success')
        else:
            loan.status = 'rejected'
            loan.rejection_reason = form.rejection_reason.data
            
            # Log activity
            log = ActivityLog(
                user_id=current_user.id,
                action='reject_loan',
                entity_type='loan',
                entity_id=loan.id,
                description=f'Rejected loan: {loan.loan_number}',
                ip_address=request.remote_addr
            )
            flash('Loan rejected!', 'warning')
        
        db.session.add(log)
        db.session.commit()
        
        return redirect(url_for('loans.view_loan', id=id))
    
    return render_template('loans/approve.html',
                         title=f'Approve Loan: {loan.loan_number}',
                         form=form,
                         loan=loan)

@loans_bp.route('/<int:id>/approve-staff', methods=['GET', 'POST'])
@login_required
@permission_required('manage_loans')
def approve_loan_staff(id):
    """Staff approval (First stage)"""
    loan = Loan.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and loan.branch_id != current_branch_id:
            flash('Access denied: Loan not found in current branch.', 'danger')
            return redirect(url_for('loans.list_loans'))
    
    # Check if loan is in correct status
    if loan.status != 'pending':
        flash('Only pending loans can be approved by staff!', 'warning')
        return redirect(url_for('loans.view_loan', id=id))
    
    # Check if user is staff (not manager or admin)
    if current_user.role not in ['staff', 'loan_collector']:
        flash('Only staff members can perform first-stage approval!', 'warning')
        return redirect(url_for('loans.view_loan', id=id))
    
    form = StaffApprovalForm()
    
    if form.validate_on_submit():
        if form.approval_status.data == 'approve':
            loan.status = 'pending_manager_approval'
            loan.staff_approved_by = current_user.id
            loan.staff_approval_date = form.approval_date.data
            loan.staff_approval_notes = form.approval_notes.data
            
            # Log activity
            log = ActivityLog(
                user_id=current_user.id,
                action='staff_approve_loan',
                entity_type='loan',
                entity_id=loan.id,
                description=f'Staff approved loan: {loan.loan_number}',
                ip_address=request.remote_addr
            )
            flash('Loan approved by staff! Awaiting manager approval.', 'success')
        else:
            loan.status = 'rejected'
            loan.rejection_reason = form.rejection_reason.data
            
            # Log activity
            log = ActivityLog(
                user_id=current_user.id,
                action='staff_reject_loan',
                entity_type='loan',
                entity_id=loan.id,
                description=f'Staff rejected loan: {loan.loan_number}',
                ip_address=request.remote_addr
            )
            flash('Loan rejected by staff!', 'warning')
        
        db.session.add(log)
        db.session.commit()
        
        return redirect(url_for('loans.view_loan', id=id))
    
    # Pre-fill form
    form.approval_date.data = datetime.now().date()
    
    return render_template('loans/approve_staff.html',
                         title=f'Staff Approval: {loan.loan_number}',
                         form=form,
                         loan=loan)

@loans_bp.route('/<int:id>/approve-manager', methods=['GET', 'POST'])
@login_required
def approve_loan_manager(id):
    """Manager approval (Second stage)"""
    loan = Loan.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and loan.branch_id != current_branch_id:
            flash('Access denied: Loan not found in current branch.', 'danger')
            return redirect(url_for('loans.list_loans'))
    
    # Check if loan is in correct status
    if loan.status != 'pending_manager_approval':
        flash('Only loans approved by staff can be approved by manager!', 'warning')
        return redirect(url_for('loans.view_loan', id=id))
    
    # Check if user is manager
    if current_user.role not in ['manager', 'accountant']:
        flash('Only managers can perform second-stage approval!', 'warning')
        return redirect(url_for('loans.view_loan', id=id))
    
    form = ManagerApprovalForm()
    
    if form.validate_on_submit():
        if form.approval_status.data == 'approve':
            loan.status = 'initiated'
            loan.manager_approved_by = current_user.id
            loan.manager_approval_date = form.approval_date.data
            loan.manager_approval_notes = form.approval_notes.data
            
            # Log activity
            log = ActivityLog(
                user_id=current_user.id,
                action='manager_approve_loan',
                entity_type='loan',
                entity_id=loan.id,
                description=f'Manager approved loan: {loan.loan_number}',
                ip_address=request.remote_addr
            )
            flash('Loan approved by manager! Loan is now initiated. Awaiting admin approval for disbursement.', 'success')
        else:
            loan.status = 'rejected'
            loan.rejection_reason = form.rejection_reason.data
            
            # Log activity
            log = ActivityLog(
                user_id=current_user.id,
                action='manager_reject_loan',
                entity_type='loan',
                entity_id=loan.id,
                description=f'Manager rejected loan: {loan.loan_number}',
                ip_address=request.remote_addr
            )
            flash('Loan rejected by manager!', 'warning')
        
        db.session.add(log)
        db.session.commit()
        
        return redirect(url_for('loans.view_loan', id=id))
    
    # Pre-fill form
    form.approval_date.data = datetime.now().date()
    
    return render_template('loans/approve_manager.html',
                         title=f'Manager Approval: {loan.loan_number}',
                         form=form,
                         loan=loan)

@loans_bp.route('/<int:id>/approve-admin', methods=['GET', 'POST'])
@login_required
def approve_loan_admin(id):
    """Admin approval (Final stage - Disburse loan)"""
    loan = Loan.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and loan.branch_id != current_branch_id:
            flash('Access denied: Loan not found in current branch.', 'danger')
            return redirect(url_for('loans.list_loans'))
    
    # Check if loan is in correct status
    if loan.status != 'initiated':
        flash('Only initiated loans can be approved by admin!', 'warning')
        return redirect(url_for('loans.view_loan', id=id))
    
    # Check if user is admin
    if current_user.role not in ['admin', 'regional_manager']:
        flash('Only admins can perform final approval and disbursement!', 'warning')
        return redirect(url_for('loans.view_loan', id=id))
    
    form = AdminApprovalForm()
    
    if form.validate_on_submit():
        if form.approval_status.data == 'approve':
            loan.status = 'active'
            loan.admin_approved_by = current_user.id
            loan.admin_approval_date = form.approval_date.data
            loan.admin_approval_notes = form.approval_notes.data
            
            # Set approved_by for legacy compatibility
            loan.approved_by = current_user.id
            loan.approval_date = form.approval_date.data
            loan.approval_notes = form.approval_notes.data
            
            # Set disbursement details
            loan.approved_amount = form.approved_amount.data or loan.loan_amount
            loan.disbursed_amount = loan.approved_amount or loan.loan_amount
            loan.disbursement_date = form.disbursement_date.data
            loan.disbursement_method = form.disbursement_method.data
            loan.disbursement_reference = form.disbursement_reference.data
            loan.first_installment_date = form.first_installment_date.data
            
            # Calculate maturity date based on loan type
            if loan.duration_days:
                loan.maturity_date = loan.disbursement_date + timedelta(days=loan.duration_days) if loan.disbursement_date else None
            elif loan.duration_weeks:
                loan.maturity_date = loan.disbursement_date + timedelta(weeks=loan.duration_weeks) if loan.disbursement_date else None
            else:
                loan.maturity_date = loan.disbursement_date + relativedelta(months=loan.duration_months) if loan.disbursement_date else None
            
            # Set initial outstanding amount to total payable (principal + interest)
            loan.outstanding_amount = loan.total_payable if loan.total_payable else (loan.approved_amount or loan.loan_amount)
            
            # Log activity
            log = ActivityLog(
                user_id=current_user.id,
                action='admin_approve_loan',
                entity_type='loan',
                entity_id=loan.id,
                description=f'Admin approved and disbursed loan: {loan.loan_number}',
                ip_address=request.remote_addr
            )
            flash('Loan approved and disbursed successfully!', 'success')
        else:
            loan.status = 'rejected'
            loan.rejection_reason = form.rejection_reason.data
            
            # Log activity
            log = ActivityLog(
                user_id=current_user.id,
                action='admin_reject_loan',
                entity_type='loan',
                entity_id=loan.id,
                description=f'Admin rejected loan: {loan.loan_number}',
                ip_address=request.remote_addr
            )
            flash('Loan rejected by admin!', 'warning')
        
        db.session.add(log)
        db.session.commit()
        
        return redirect(url_for('loans.view_loan', id=id))
    
    # Pre-fill form
    form.approval_date.data = datetime.now().date()
    form.approved_amount.data = loan.loan_amount
    form.disbursement_date.data = datetime.now().date()
    
    # Calculate first installment date based on loan type
    if loan.duration_days:
        form.first_installment_date.data = datetime.now().date() + timedelta(days=1)
    elif loan.duration_weeks:
        form.first_installment_date.data = datetime.now().date() + timedelta(days=7)
    else:
        form.first_installment_date.data = datetime.now().date() + timedelta(days=30)
    
    return render_template('loans/approve_admin.html',
                         title=f'Admin Approval: {loan.loan_number}',
                         form=form,
                         loan=loan)

@loans_bp.route('/<int:id>/deactivate', methods=['GET', 'POST'])
@login_required
@permission_required('manage_loans')
def deactivate_loan(id):
    """Deactivate loan"""
    loan = Loan.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and loan.branch_id != current_branch_id:
            flash('Access denied: Loan not found in current branch.', 'danger')
            return redirect(url_for('loans.list_loans'))
    
    # Check if user has admin role for deactivation
    if current_user.role not in ['admin', 'regional_manager']:
        flash('Only administrators can deactivate loans.', 'danger')
        return redirect(url_for('loans.view_loan', id=id))
    
    # Check if loan can be deactivated
    if loan.status in ['completed', 'defaulted', 'rejected', 'deactivated']:
        flash('This loan cannot be deactivated.', 'danger')
        return redirect(url_for('loans.view_loan', id=id))
    
    form = LoanDeactivationForm()
    if form.validate_on_submit():
        if not form.confirm_deactivation.data:
            flash('Please confirm deactivation.', 'warning')
            return redirect(url_for('loans.deactivate_loan', id=id))
        
        # Deactivate the loan
        loan.status = 'deactivated'
        loan.deactivation_reason = form.deactivation_reason.data
        loan.deactivation_date = form.deactivation_date.data
        loan.deactivated_by = current_user.id
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='deactivate_loan',
            entity_type='loan',
            entity_id=loan.id,
            description=f'Loan deactivated: {loan.loan_number} - Reason: {form.deactivation_reason.data}',
            ip_address=request.remote_addr
        )
        
        db.session.add(log)
        db.session.commit()
        
        flash('Loan deactivated successfully!', 'success')
        return redirect(url_for('loans.view_loan', id=id))
    
    return render_template('loans/deactivate.html',
                         title=f'Deactivate Loan: {loan.loan_number}',
                         form=form,
                         loan=loan)

@loans_bp.route('/<int:id>/payment', methods=['GET', 'POST'])
@login_required
@permission_required('collect_payments')
def add_payment(id):
    """Add loan payment"""
    loan = Loan.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and loan.branch_id != current_branch_id:
            flash('Access denied: Loan not found in current branch.', 'danger')
            return redirect(url_for('loans.list_loans'))
    
    if loan.status not in ['active', 'disbursed']:
        flash('Cannot add payment for this loan! Loan must be active.', 'warning')
        return redirect(url_for('loans.view_loan', id=id))
    
    form = LoanPaymentForm()
    
    if form.validate_on_submit():
        from decimal import Decimal, ROUND_HALF_UP
        
        payment_amount = Decimal(str(form.payment_amount.data)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Calculate current outstanding with accrued interest
        current_outstanding = loan.calculate_current_outstanding()
        accrued_interest = loan.calculate_accrued_interest()
        
        # Current outstanding principal (without accrued interest)
        disbursed = Decimal(str(loan.disbursed_amount or loan.loan_amount))
        paid_principal = loan.get_total_paid_principal()
        outstanding_principal = disbursed - paid_principal
        
        # Check if this is a full payment or overpayment
        is_full_payment = payment_amount >= current_outstanding or abs(payment_amount - current_outstanding) <= Decimal('0.05')
        
        # Calculate interest and principal splits based on loan type
        if loan.interest_type == 'flat':
            # For flat interest loans, calculate fixed interest per payment
            # Determine number of installments and period based on frequency
            if loan.installment_frequency == 'monthly':
                num_installments = loan.duration_months or 0
                period = Decimal('1') / Decimal('12')
            elif loan.installment_frequency == 'weekly':
                num_installments = loan.duration_weeks or 0
                period = Decimal('7') / Decimal('365')
            elif loan.installment_frequency == 'daily':
                num_installments = loan.duration_days or 0
                period = Decimal('1') / Decimal('365')
            else:
                num_installments = loan.duration_months or 0
                period = Decimal('1') / Decimal('12')
            
            time_in_years = Decimal(str(num_installments)) * period
            total_interest = (disbursed * Decimal(str(loan.interest_rate)) * time_in_years) / Decimal('100')
            installment_interest = total_interest / Decimal(str(num_installments)) if num_installments > 0 else Decimal('0')
            
            # For flat loans, determine if this is truly a full settlement (paying off entire remaining balance)
            total_paid = Decimal(str(loan.paid_amount or 0))
            total_payable = disbursed + total_interest
            remaining_total = total_payable - total_paid
            is_full_settlement = payment_amount >= remaining_total or abs(payment_amount - remaining_total) <= Decimal('0.05')
            
            if is_full_settlement:
                # Full settlement - pay all remaining interest and principal
                total_paid_interest = loan.get_total_paid_interest()
                remaining_interest = total_interest - Decimal(str(total_paid_interest))
                interest_amount = min(payment_amount, remaining_interest)
                principal_amount = payment_amount - interest_amount
            else:
                # Regular installment payment - use fixed interest per payment
                if loan.installment_amount and loan.installment_amount > 0 and abs(payment_amount - Decimal(str(loan.installment_amount))) <= Decimal('0.05'):
                    # This is a regular installment payment
                    interest_amount = installment_interest
                    principal_amount = payment_amount - interest_amount
                else:
                    # Partial or different amount - calculate proportionally
                    payment_ratio = payment_amount / Decimal(str(loan.installment_amount)) if loan.installment_amount else Decimal('1')
                    interest_amount = installment_interest * payment_ratio
                    principal_amount = payment_amount - interest_amount
        else:
            # For reducing balance loans (original logic)
            if is_full_payment:
                # For full payments, pay off accrued interest first, then principal
                interest_amount = min(payment_amount, accrued_interest)
                principal_amount = min(payment_amount - interest_amount, outstanding_principal)
                
                # Any remaining amount goes to interest (overpayment case)
                remaining = payment_amount - principal_amount - interest_amount
                if remaining > 0:
                    interest_amount += remaining
            else:
                # For partial payments, split based on loan terms
                if accrued_interest > 0:
                    # Pay accrued interest first if any exists
                    interest_amount = min(payment_amount, accrued_interest)
                    principal_amount = payment_amount - interest_amount
                else:
                    # Standard EMI split - calculate proportion
                    monthly_interest = outstanding_principal * (Decimal(str(loan.interest_rate)) / Decimal('1200'))
                    if payment_amount >= monthly_interest:
                        interest_amount = monthly_interest
                        principal_amount = payment_amount - interest_amount
                    else:
                        # If payment is less than monthly interest, all goes to interest
                        interest_amount = payment_amount
                        principal_amount = Decimal('0')
        # Ensure no negative amounts
        interest_amount = max(Decimal('0'), interest_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        principal_amount = max(Decimal('0'), principal_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        # Create payment record
        payment = LoanPayment(
            loan_id=loan.id,
            payment_date=form.payment_date.data,
            payment_amount=float(payment_amount),
            principal_amount=float(principal_amount),
            interest_amount=float(interest_amount),
            penalty_amount=float(form.penalty_amount.data or 0),
            payment_method=form.payment_method.data,
            reference_number=form.reference_number.data,
            notes=form.notes.data,
            collected_by=current_user.id
        )
        
        db.session.add(payment)
        
        # Update loan amounts - recalculate outstanding based on new payment
        loan.paid_amount = (Decimal(str(loan.paid_amount or 0)) + payment_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        loan.update_outstanding_amount()  # Use our new method to calculate current outstanding
        
        # Check if loan is fully paid
        if loan.calculate_current_outstanding() <= Decimal('0.02'):  # Allow for small rounding differences
            loan.status = 'completed'
            loan.outstanding_amount = Decimal('0')
            loan.closing_date = form.payment_date.data  # Set closing date to payment date
            
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='loan_payment',
            entity_type='loan',
            entity_id=loan.id,
            description=f'Payment of {payment_amount} for loan {loan.loan_number}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'Payment of {payment_amount} recorded successfully!', 'success')
        return redirect(url_for('loans.view_loan', id=id))
    
    # Set default values only for GET requests and calculate current amounts
    if request.method == 'GET':
        form.payment_amount.data = loan.installment_amount
        form.payment_date.data = datetime.now().date()
    
    # Get current outstanding amount with accrued interest for display
    current_outstanding = loan.calculate_current_outstanding()
    accrued_interest = loan.calculate_accrued_interest()
    
    # Update stored outstanding amount to match current calculation
    loan.update_outstanding_amount()
    db.session.commit()
    
    return render_template('loans/payment.html',
                         title=f'Add Payment: {loan.loan_number}',
                         form=form,
                         loan=loan,
                         current_outstanding=current_outstanding,
                         accrued_interest=accrued_interest)

@loans_bp.route('/search')
@login_required
@permission_required('manage_loans')
def search_loans():
    """Search loans page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    loan_type = request.args.get('loan_type', '', type=str)
    status = request.args.get('status', '', type=str)
    interest_type = request.args.get('interest_type', '', type=str)
    min_amount = request.args.get('min_amount', '', type=str)
    max_amount = request.args.get('max_amount', '', type=str)
    
    loans = None
    searched = False
    
    if search or loan_type or status or interest_type or min_amount or max_amount:
        searched = True
        query = Loan.query
        
        # Filter by current branch if needed
        if should_filter_by_branch():
            current_branch_id = get_current_branch_id()
            if current_branch_id:
                query = query.filter_by(branch_id=current_branch_id)
        
        if search:
            query = query.join(Customer).filter(
                db.or_(
                    Loan.loan_number.ilike(f'%{search}%'),
                    Customer.full_name.ilike(f'%{search}%'),
                    Customer.customer_id.ilike(f'%{search}%')
                )
            )
        
        if loan_type:
            query = query.filter_by(loan_type=loan_type)
        
        if status:
            query = query.filter_by(status=status)
        
        if interest_type:
            query = query.filter_by(interest_type=interest_type)
        
        if min_amount:
            try:
                query = query.filter(Loan.loan_amount >= float(min_amount))
            except ValueError:
                pass
        
        if max_amount:
            try:
                query = query.filter(Loan.loan_amount <= float(max_amount))
            except ValueError:
                pass
        
        loans = query.order_by(Loan.created_at.desc()).paginate(
            page=page, per_page=current_app.config['ITEMS_PER_PAGE'], error_out=False
        )
    
    return render_template('loans/search.html',
                         title='Search Loans',
                         loans=loans,
                         search=search,
                         loan_type=loan_type,
                         status=status,
                         interest_type=interest_type,
                         min_amount=min_amount,
                         max_amount=max_amount,
                         searched=searched)

# API endpoint for fetching guarantors
@loans_bp.route('/api/guarantors')
@login_required
@permission_required('manage_loans')
def get_guarantors():
    """Get KYC approved guarantors and family guarantors"""
    # Get the member ID to exclude (loan borrower cannot be their own guarantor)
    exclude_customer_id = request.args.get('exclude_customer_id', type=int)
    
    # Query customers who are guarantors or family guarantors and have KYC verified
    query = Customer.query.filter(
        db.or_(
            Customer.customer_type.like('%guarantor%'),
            Customer.customer_type.like('%family_guarantor%')
        ),
        Customer.kyc_verified == True
    )
    
    # Exclude the selected loan member
    if exclude_customer_id:
        query = query.filter(Customer.id != exclude_customer_id)
    
    # Filter by branch if needed
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            query = query.filter_by(branch_id=current_branch_id)
    
    guarantors = query.order_by(Customer.full_name).all()
    
    # Format guarantor data
    guarantor_list = []
    for guarantor in guarantors:
        guarantor_list.append({
            'id': guarantor.id,
            'full_name': guarantor.full_name,
            'nic_number': guarantor.nic_number,
            'phone_primary': guarantor.phone_primary,
            'customer_type': guarantor.customer_type,
            'customer_type_display': guarantor.customer_type_display,
            'address_line1': guarantor.address_line1,
            'address_line2': guarantor.address_line2 or '',
            'city': guarantor.city,
            'district': guarantor.district,
            'email': guarantor.email or ''
        })
    
    return jsonify({
        'success': True,
        'guarantors': guarantor_list
    })


# API endpoint for searching customers
@loans_bp.route('/api/search-customers')
@login_required
@permission_required('manage_loans')
def search_customers():
    """Search customers for loan assignment"""
    search_term = request.args.get('q', '', type=str).strip()
    
    if not search_term or len(search_term) < 2:
        return jsonify({'success': False, 'customers': []})
    
    # Query active and KYC verified customers
    query = Customer.query.filter(
        Customer.status == 'active',
        Customer.kyc_verified == True
    )
    
    # Filter by current branch if needed
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            query = query.filter_by(branch_id=current_branch_id)
    
    # Search by name, customer ID, or NIC number
    customers = query.filter(
        db.or_(
            Customer.full_name.ilike(f'%{search_term}%'),
            Customer.customer_id.ilike(f'%{search_term}%'),
            Customer.nic_number.ilike(f'%{search_term}%')
        )
    ).order_by(Customer.full_name).limit(10).all()
    
    # Format customer data
    customer_list = []
    for customer in customers:
        customer_list.append({
            'id': customer.id,
            'text': f'{customer.customer_id} - {customer.full_name} ({customer.nic_number})',
            'customer_id': customer.customer_id,
            'full_name': customer.full_name,
            'nic_number': customer.nic_number,
            'phone_primary': customer.phone_primary
        })
    
    return jsonify({
        'success': True,
        'customers': customer_list
    })


@loans_bp.route('/receipt-entry')
@login_required
@permission_required('collect_payments')
def receipt_entry():
    """Receipt entry page with weekly, daily, and monthly loan payment tables"""
    referrer = request.args.get('collector', type=int)
    
    # Get weekly loans (type1_9weeks and type4_micro)
    weekly_loans_query = Loan.query.filter(
        Loan.loan_type.in_(['type1_9weeks', 'type4_micro']),
        Loan.status == 'active'
    )
    
    # Get daily loans (54_daily and type4_daily)
    daily_loans_query = Loan.query.filter(
        Loan.loan_type.in_(['54_daily', 'type4_daily']),
        Loan.status == 'active'
    )
    
    # Get monthly loans (monthly_loan and other monthly types)
    monthly_loans_query = Loan.query.filter(
        Loan.loan_type.in_(['monthly_loan']),
        Loan.status == 'active'
    )
    
    # Filter by branch if needed
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            weekly_loans_query = weekly_loans_query.filter_by(branch_id=current_branch_id)
            daily_loans_query = daily_loans_query.filter_by(branch_id=current_branch_id)
            monthly_loans_query = monthly_loans_query.filter_by(branch_id=current_branch_id)
    
    # Filter by referrer if specified
    if referrer:
        weekly_loans_query = weekly_loans_query.filter(Loan.referred_by == referrer)
        daily_loans_query = daily_loans_query.filter(Loan.referred_by == referrer)
        monthly_loans_query = monthly_loans_query.filter(Loan.referred_by == referrer)
    
    weekly_loans = weekly_loans_query.order_by(Loan.created_at.desc()).all()
    daily_loans = daily_loans_query.order_by(Loan.created_at.desc()).all()
    monthly_loans = monthly_loans_query.order_by(Loan.created_at.desc()).all()
    
    # Get recent payments for each loan with collector info
    weekly_payments = []
    for loan in weekly_loans:
        recent_payments = loan.payments.order_by(LoanPayment.payment_date.desc()).limit(5).all()
        weekly_payments.append({
            'loan': loan,
            'recent_payments': recent_payments
        })
    
    daily_payments = []
    for loan in daily_loans:
        recent_payments = loan.payments.order_by(LoanPayment.payment_date.desc()).limit(5).all()
        daily_payments.append({
            'loan': loan,
            'recent_payments': recent_payments
        })
    
    monthly_payments = []
    for loan in monthly_loans:
        recent_payments = loan.payments.order_by(LoanPayment.payment_date.desc()).limit(5).all()
        monthly_payments.append({
            'loan': loan,
            'recent_payments': recent_payments
        })
    
    # Get all payments for payment history
    all_payments_query = LoanPayment.query.join(Loan)
    
    # Filter by branch if needed
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            all_payments_query = all_payments_query.filter(Loan.branch_id == current_branch_id)
    
    # Filter by referrer if specified
    if referrer:
        all_payments_query = all_payments_query.filter(Loan.referred_by == referrer)
    
    all_payments = all_payments_query.order_by(LoanPayment.payment_date.desc()).limit(100).all()
    
    # Get users for referrer dropdown
    users_query = User.query.filter_by(is_active=True)
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            users_query = users_query.filter_by(branch_id=current_branch_id)
    users = users_query.order_by(User.full_name).all()
    
    return render_template('loans/receipt_entry.html',
                         title='Receipt Entry',
                         weekly_payments=weekly_payments,
                         daily_payments=daily_payments,
                         monthly_payments=monthly_payments,
                         all_payments=all_payments,
                         users=users,
                         collector=referrer)
