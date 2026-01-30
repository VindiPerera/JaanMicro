"""Loan management routes"""
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os
from app import db
from app.loans import loans_bp
from app.models import Loan, LoanPayment, Customer, ActivityLog, SystemSettings
from app.loans.forms import LoanForm, LoanPaymentForm, LoanApprovalForm, StaffApprovalForm, ManagerApprovalForm, InitiateLoanForm, AdminApprovalForm
from app.utils.decorators import permission_required
from app.utils.helpers import generate_loan_number, get_current_branch_id, should_filter_by_branch

@loans_bp.route('/')
@login_required
@permission_required('manage_loans')
def list_loans():
    """List all loans"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    loan_type = request.args.get('loan_type', '')
    
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
        page=page, per_page=current_app.config['ITEMS_PER_PAGE'], error_out=False
    )
    
    return render_template('loans/list.html',
                         title='Loans',
                         loans=loans,
                         search=search,
                         status=status,
                         loan_type=loan_type)

@loans_bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('manage_loans')
def add_loan():
    """Add new loan"""
    form = LoanForm()
    
    # Get customers for dropdown
    customer_query = Customer.query.filter_by(status='active', kyc_verified=True)
    
    # Apply branch filtering if needed
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            customer_query = customer_query.filter_by(branch_id=current_branch_id)
    
    customers = customer_query.order_by(Customer.full_name).all()
    form.customer_id.choices = [(0, 'Select Customer')] + [(c.id, f'{c.customer_id} - {c.full_name}') for c in customers]
    
    # Pre-fill interest rate from settings on GET request
    if request.method == 'GET':
        settings = SystemSettings.get_settings()
        form.interest_rate.data = settings.default_loan_interest_rate
        form.application_date.data = datetime.now().date()
    
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
        
        settings = SystemSettings.get_settings()
        loan_number = generate_loan_number(settings.loan_number_prefix)
        
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
        if form.document.data:
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
        
        loan = Loan(
            loan_number=loan_number,
            customer_id=form.customer_id.data,
            branch_id=get_current_branch_id(),
            loan_type=form.loan_type.data,
            loan_amount=form.loan_amount.data,
            interest_rate=form.interest_rate.data,
            interest_type=form.interest_type.data,
            duration_months=duration_months,
            duration_weeks=duration_weeks,
            duration_days=duration_days,
            installment_amount=emi,
            installment_frequency='daily' if duration_days else ('weekly' if duration_weeks else form.installment_frequency.data),
            total_payable=total_payable,
            application_date=form.application_date.data,
            purpose=form.purpose.data,
            security_details=form.security_details.data,
            document_path=document_filename,
            guarantor_ids=request.form.get('guarantor_ids', ''),
            status='pending',  # All new loans start as pending and go through approval workflow
            created_by=current_user.id,
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
    
    payments = loan.payments.order_by(LoanPayment.payment_date.desc()).all()
    
    # Calculate current outstanding amount with accrued interest
    current_outstanding = loan.calculate_current_outstanding()
    accrued_interest = loan.calculate_accrued_interest()
    
    # Update the loan's stored outstanding amount to reflect current calculation
    loan.update_outstanding_amount()
    
    # Get guarantors
    guarantors = []
    if loan.guarantor_ids:
        guarantor_id_list = [int(gid.strip()) for gid in loan.guarantor_ids.split(',') if gid.strip()]
        if guarantor_id_list:
            guarantors = Customer.query.filter(Customer.id.in_(guarantor_id_list)).all()
    
    return render_template('loans/view.html',
                         title=f'Loan: {loan.loan_number}',
                         loan=loan,
                         payments=payments,
                         guarantors=guarantors,
                         current_outstanding=current_outstanding,
                         accrued_interest=accrued_interest)

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
            # Set initial outstanding amount to disbursed amount (principal only initially)
            loan.outstanding_amount = loan.approved_amount or loan.loan_amount
            
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
    if current_user.role != 'admin':
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
            
            # Set initial outstanding amount to disbursed amount
            loan.outstanding_amount = loan.approved_amount or loan.loan_amount
            
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
            total_interest = (disbursed * Decimal(str(loan.interest_rate)) * Decimal(str(loan.duration_months))) / (Decimal('12') * Decimal('100'))
            installment_interest = total_interest / Decimal(str(loan.duration_months))
            
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
        Customer.customer_type.in_(['guarantor', 'family_guarantor']),
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
            'customer_type_display': 'Family Guarantor' if guarantor.customer_type == 'family_guarantor' else 'Guarantor',
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

