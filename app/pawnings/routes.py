"""Pawning management routes"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import json
from app import db
from app.pawnings import pawnings_bp
from app.models import Pawning, PawningPayment, Customer, ActivityLog, SystemSettings
from app.pawnings.forms import PawningForm, PawningPaymentForm
from app.utils.decorators import permission_required
from app.utils.helpers import generate_pawning_number, allowed_file, get_current_branch_id, should_filter_by_branch

@pawnings_bp.route('/')
@login_required
@permission_required('manage_pawnings')
def list_pawnings():
    """List all pawnings"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    query = Pawning.query
    
    # Filter by current branch if needed
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            query = query.filter_by(branch_id=current_branch_id)
    
    if search:
        query = query.join(Customer).filter(
            db.or_(
                Pawning.pawning_number.ilike(f'%{search}%'),
                Customer.full_name.ilike(f'%{search}%'),
                Customer.customer_id.ilike(f'%{search}%')
            )
        )
    
    if status:
        query = query.filter_by(status=status)
    
    pawnings = query.order_by(Pawning.created_at.desc()).paginate(
        page=page, per_page=current_app.config['ITEMS_PER_PAGE'], error_out=False
    )
    
    return render_template('pawnings/list.html',
                         title='Pawnings',
                         pawnings=pawnings,
                         search=search,
                         status=status,
                         today=datetime.now().date())

@pawnings_bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('manage_pawnings')
def add_pawning():
    """Add new pawning - Sri Lankan method"""
    form = PawningForm()
    
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
        form.interest_rate.data = settings.default_pawning_interest_rate
    
    if form.validate_on_submit():
        # Validate customer selection
        if form.customer_id.data == 0:
            flash('Please select a customer!', 'error')
            return render_template('pawnings/add.html', title='Add Pawning', form=form)
        
        # Get customer to determine branch
        customer = Customer.query.get(form.customer_id.data)
        if not customer:
            flash('Customer not found!', 'error')
            return render_template('pawnings/add.html', title='Add Pawning', form=form)
        
        if not customer.branch_id:
            flash('Customer does not have a valid branch assigned!', 'error')
            return render_template('pawnings/add.html', title='Add Pawning', form=form)
        
        # Calculate loan-to-value ratio
        from decimal import Decimal, ROUND_HALF_UP
        
        total_value = Decimal(str(form.total_market_value.data))
        loan_amt = Decimal(str(form.loan_amount.data))
        ltv_ratio = float((loan_amt / total_value * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if total_value > 0 else 0
        
        # Convert for database storage
        loan_amt = float(loan_amt)
        total_value = float(total_value)
        
        # Get settings for max LTV check
        settings = SystemSettings.get_settings()
        max_ltv = float(settings.maximum_loan_to_value_ratio or 80)
        
        if ltv_ratio > max_ltv:
            flash(f'Loan amount cannot exceed {max_ltv}% of appraised value (Max: LKR {total_value * max_ltv / 100:.2f})!', 'error')
            return render_template('pawnings/add.html', title='Add Pawning', form=form)
        
        pawning_number = generate_pawning_number(settings.pawning_number_prefix)
        
        # Calculate maturity date from duration
        maturity_date = form.pawning_date.data + relativedelta(months=form.duration_months.data)
        
        # Calculate monthly interest (Sri Lankan method)
        from decimal import Decimal, ROUND_HALF_UP
        
        loan_amount_decimal = Decimal(str(loan_amt))
        interest_rate_decimal = Decimal(str(form.interest_rate.data))
        monthly_interest = loan_amount_decimal * interest_rate_decimal / Decimal('100')
        monthly_interest = float(monthly_interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        # Extract karat value from purity selection
        karat_value = None
        if form.item_purity.data and form.item_purity.data != 'other':
            karat_value = float(form.item_purity.data.replace('K', ''))
        elif form.karats.data:
            karat_value = float(form.karats.data)
        
        pawning = Pawning(
            pawning_number=pawning_number,
            customer_id=form.customer_id.data,
            branch_id=customer.branch_id,
            item_description=form.item_description.data,
            item_type=form.item_type.data,
            item_weight=form.item_weight.data,
            item_purity=form.item_purity.data if form.item_purity.data != 'other' else None,
            karats=karat_value,
            number_of_items=form.number_of_items.data or 1,
            market_value_per_gram=form.market_value_per_gram.data,
            total_market_value=form.total_market_value.data,
            loan_amount=form.loan_amount.data,
            interest_rate=form.interest_rate.data,
            loan_to_value_ratio=ltv_ratio,
            duration_months=form.duration_months.data,
            grace_period_days=form.grace_period_days.data or 30,
            interest_per_month=monthly_interest,
            interest_due=0,
            principal_paid=0,
            outstanding_principal=form.loan_amount.data,
            total_interest_paid=0,
            total_penalty=0,
            pawning_date=form.pawning_date.data,
            maturity_date=maturity_date,
            storage_location=form.storage_location.data,
            storage_box_number=form.storage_box_number.data,
            storage_notes=form.storage_notes.data,
            created_by=current_user.id,
            notes=form.notes.data,
            status='active'
        )
        
        db.session.add(pawning)
        db.session.flush()  # Get the ID
        
        # Handle file uploads for item photos
        if form.item_photo.data:
            upload_folder = current_app.config['UPLOAD_FOLDER']
            pawning_folder = os.path.join(upload_folder, 'pawnings', str(pawning.id))
            os.makedirs(pawning_folder, exist_ok=True)
            
            photos = []
            for file in request.files.getlist('item_photo'):
                if file and allowed_file(file.filename):
                    filename = secure_filename(f'item_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{file.filename}')
                    filepath = os.path.join(pawning_folder, filename)
                    file.save(filepath)
                    photos.append(f'uploads/pawnings/{pawning.id}/{filename}')
            
            if photos:
                pawning.item_photos = json.dumps(photos)
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='create_pawning',
            entity_type='pawning',
            entity_id=pawning.id,
            description=f'Created pawning: {pawning.pawning_number} for {pawning.customer.full_name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'Pawning {pawning.pawning_number} created successfully! Monthly interest: LKR {monthly_interest:.2f}', 'success')
        return redirect(url_for('pawnings.view_pawning', id=pawning.id))
    
    return render_template('pawnings/add.html', title='Add Pawning', form=form)

@pawnings_bp.route('/<int:id>')
@login_required
def view_pawning(id):
    """View pawning details - Sri Lankan style"""
    pawning = Pawning.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and pawning.branch_id != current_branch_id:
            flash('Access denied: Pawning not found in current branch.', 'danger')
            return redirect(url_for('pawnings.list_pawnings'))
    
    payments = pawning.payments.order_by(PawningPayment.payment_date.desc()).all()
    
    # Parse item photos
    photos = []
    if pawning.item_photos:
        try:
            photos = json.loads(pawning.item_photos)
        except:
            pass
    
    # Calculate current interest due
    from decimal import Decimal
    total_interest_due = Decimal(str(pawning.calculate_total_interest_due()))
    total_interest_paid = Decimal(str(pawning.total_interest_paid or 0))
    interest_unpaid = float(total_interest_due - total_interest_paid)
    
    # Calculate months elapsed
    months_elapsed = 0
    if pawning.pawning_date:
        today = datetime.now().date()
        months_elapsed = ((today.year - pawning.pawning_date.year) * 12 + 
                         (today.month - pawning.pawning_date.month))
    
    # Check if overdue
    is_overdue = pawning.check_overdue_status()
    
    return render_template('pawnings/view.html',
                         title=f'Pawning: {pawning.pawning_number}',
                         pawning=pawning,
                         payments=payments,
                         photos=photos,
                         interest_unpaid=interest_unpaid,
                         months_elapsed=months_elapsed,
                         is_overdue=is_overdue,
                         today=datetime.now().date())

@pawnings_bp.route('/<int:id>/payment', methods=['GET', 'POST'])
@login_required
@permission_required('collect_payments')
def add_payment(id):
    """Add pawning payment - Sri Lankan method (interest-only or redemption)"""
    pawning = Pawning.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and pawning.branch_id != current_branch_id:
            flash('Access denied: Pawning not found in current branch.', 'danger')
            return redirect(url_for('pawnings.list_pawnings'))
    
    if pawning.status not in ['active', 'extended', 'overdue']:
        flash('Cannot add payment for this pawning!', 'warning')
        return redirect(url_for('pawnings.view_pawning', id=id))
    
    form = PawningPaymentForm()
    
    # Calculate interest due up to today
    months_elapsed = 0
    if pawning.pawning_date:
        today = datetime.now().date()
        months_elapsed = ((today.year - pawning.pawning_date.year) * 12 + 
                         (today.month - pawning.pawning_date.month))
        if today.day < pawning.pawning_date.day:
            months_elapsed -= 1
        months_elapsed = max(0, months_elapsed)
    
    from decimal import Decimal
    interest_per_month = Decimal(str(pawning.interest_per_month or 0))
    total_interest_due = interest_per_month * Decimal(str(months_elapsed))
    total_interest_paid = Decimal(str(pawning.total_interest_paid or 0))
    interest_unpaid = total_interest_due - total_interest_paid
    
    if form.validate_on_submit():
        from decimal import Decimal, ROUND_HALF_UP
        
        payment_amount = Decimal(str(form.payment_amount.data))
        payment_type = form.payment_type.data
        
        interest_amt = Decimal(str(form.interest_amount.data or 0))
        principal_amt = Decimal(str(form.principal_amount.data or 0))
        penalty_amt = Decimal(str(form.penalty_amount.data or 0))
        
        # Validate payment breakdown (allow 1 cent difference for rounding)
        breakdown_total = interest_amt + principal_amt + penalty_amt
        if abs(payment_amount - breakdown_total) > Decimal('0.01'):
            flash('Payment breakdown does not match total payment amount!', 'error')
            return render_template('pawnings/payment.html', 
                                 title=f'Add Payment: {pawning.pawning_number}',
                                 form=form, pawning=pawning,
                                 interest_unpaid=interest_unpaid,
                                 months_elapsed=months_elapsed)
        
        # For full redemption, validate all amounts are paid
        if payment_type == 'full_redemption':
            if not form.confirm_redemption.data:
                flash('Please confirm that the item has been returned to the customer!', 'error')
                return render_template('pawnings/payment.html', 
                                     title=f'Add Payment: {pawning.pawning_number}',
                                     form=form, pawning=pawning,
                                     interest_unpaid=interest_unpaid,
                                     months_elapsed=months_elapsed)
            
            outstanding_principal = Decimal(str(pawning.outstanding_principal or 0))
            total_penalty = Decimal(str(pawning.total_penalty or 0))
            total_due = float(outstanding_principal + interest_unpaid + total_penalty)
            if payment_amount < total_due - 0.01:  # Allow small rounding difference
                flash(f'Full redemption requires payment of LKR {total_due:.2f}!', 'error')
                return render_template('pawnings/payment.html', 
                                     title=f'Add Payment: {pawning.pawning_number}',
                                     form=form, pawning=pawning,
                                     interest_unpaid=interest_unpaid,
                                     months_elapsed=months_elapsed)
        
        # Determine interest period
        interest_from = pawning.last_interest_payment_date or pawning.pawning_date
        interest_to = form.payment_date.data
        
        if form.interest_period_from.data and form.interest_period_to.data:
            interest_from = form.interest_period_from.data
            interest_to = form.interest_period_to.data
        
        # Create payment record
        payment = PawningPayment(
            pawning_id=pawning.id,
            payment_date=form.payment_date.data,
            payment_amount=payment_amount,
            payment_type=payment_type,
            interest_amount=interest_amt,
            principal_amount=principal_amt,
            penalty_amount=penalty_amt,
            interest_period_from=interest_from,
            interest_period_to=interest_to,
            payment_method=form.payment_method.data,
            reference_number=form.reference_number.data,
            receipt_number=f'PWN-RCP-{pawning.id}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            notes=form.notes.data,
            collected_by=current_user.id
        )
        
        # Update pawning balances
        pawning.total_interest_paid = (pawning.total_interest_paid or 0) + interest_amt
        pawning.principal_paid = (pawning.principal_paid or 0) + principal_amt
        pawning.outstanding_principal = (pawning.outstanding_principal or pawning.loan_amount) - principal_amt
        pawning.total_penalty = (pawning.total_penalty or 0) - penalty_amt  # Reduce penalty balance
        
        # Update interest due
        pawning.interest_due = max(0, interest_unpaid - interest_amt)
        
        # Update last interest payment date if interest was paid
        if interest_amt > 0:
            pawning.last_interest_payment_date = form.payment_date.data
        
        # Record balance after payment
        payment.interest_balance_after = pawning.interest_due
        payment.principal_balance_after = pawning.outstanding_principal
        
        # Update status based on payment type
        if payment_type == 'full_redemption' or (pawning.outstanding_principal <= 0.01 and interest_unpaid - interest_amt <= 0.01):
            pawning.status = 'redeemed'
            pawning.redemption_date = form.payment_date.data
            pawning.outstanding_principal = 0
            pawning.interest_due = 0
        
        db.session.add(payment)
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='add_pawning_payment',
            entity_type='pawning',
            entity_id=pawning.id,
            description=f'Added {payment_type} payment for pawning: {pawning.pawning_number} - LKR {payment_amount:.2f}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        if payment_type == 'full_redemption':
            flash(f'Payment processed! Item redeemed and returned to customer. Receipt: {payment.receipt_number}', 'success')
        else:
            flash(f'Payment of LKR {payment_amount:.2f} recorded successfully! Receipt: {payment.receipt_number}', 'success')
        
        return redirect(url_for('pawnings.view_pawning', id=id))
    
    return render_template('pawnings/payment.html',
                         title=f'Add Payment: {pawning.pawning_number}',
                         form=form,
                         pawning=pawning,
                         interest_unpaid=interest_unpaid,
                         months_elapsed=months_elapsed)

@pawnings_bp.route('/<int:id>/redeem', methods=['POST'])
@login_required
@permission_required('manage_pawnings')
def redeem_pawning(id):
    """Mark pawning as redeemed"""
    pawning = Pawning.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and pawning.branch_id != current_branch_id:
            flash('Access denied: Pawning not found in current branch.', 'danger')
            return redirect(url_for('pawnings.list_pawnings'))
    
    # Calculate outstanding amounts
    from decimal import Decimal
    total_interest_due = Decimal(str(pawning.calculate_total_interest_due()))
    total_interest_paid = Decimal(str(pawning.total_interest_paid or 0))
    interest_unpaid = total_interest_due - total_interest_paid
    
    if pawning.outstanding_principal > 0 or interest_unpaid > 0 or (pawning.total_penalty or 0) > 0:
        outstanding_principal = Decimal(str(pawning.outstanding_principal or 0))
        total_penalty = Decimal(str(pawning.total_penalty or 0))
        total_due = float(outstanding_principal + interest_unpaid + total_penalty)
        flash(f'Cannot redeem pawning with outstanding amount of LKR {total_due:.2f}! Please clear all dues first.', 'warning')
        return redirect(url_for('pawnings.view_pawning', id=id))
    
    pawning.status = 'redeemed'
    pawning.redemption_date = datetime.utcnow().date()
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        action='redeem_pawning',
        entity_type='pawning',
        entity_id=pawning.id,
        description=f'Redeemed pawning: {pawning.pawning_number}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    
    db.session.commit()
    
    flash('Pawning marked as redeemed! Item can be returned to customer.', 'success')
    return redirect(url_for('pawnings.view_pawning', id=id))

@pawnings_bp.route('/<int:id>/extend', methods=['POST'])
@login_required
@permission_required('manage_pawnings')
def extend_pawning(id):
    """Extend/renew pawning period"""
    pawning = Pawning.query.get_or_404(id)
    
    # Check branch access
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and pawning.branch_id != current_branch_id:
            flash('Access denied: Pawning not found in current branch.', 'danger')
            return redirect(url_for('pawnings.list_pawnings'))
    
    if pawning.status not in ['active', 'extended', 'overdue']:
        flash('Cannot extend this pawning!', 'warning')
        return redirect(url_for('pawnings.view_pawning', id=id))
    
    # Get extension period from form
    extend_months = int(request.form.get('extend_months', 3))
    
    # Require interest to be paid up before extension
    from decimal import Decimal
    total_interest_due = Decimal(str(pawning.calculate_total_interest_due()))
    total_interest_paid = Decimal(str(pawning.total_interest_paid or 0))
    interest_unpaid = float(total_interest_due - total_interest_paid)
    
    if interest_unpaid > 10:  # Allow small rounding difference
        flash(f'Please pay outstanding interest (LKR {interest_unpaid:.2f}) before extending the pawning period!', 'warning')
        return redirect(url_for('pawnings.view_pawning', id=id))
    
    # Calculate new maturity date
    current_maturity = pawning.extended_date if pawning.extended_date else pawning.maturity_date
    new_maturity = current_maturity + relativedelta(months=extend_months)
    
    pawning.extended_date = new_maturity
    pawning.times_extended = (pawning.times_extended or 0) + 1
    pawning.status = 'extended'
    pawning.is_overdue = False
    
    extension_note = f'Extended by {extend_months} months until {new_maturity.strftime("%Y-%m-%d")} (Extension #{pawning.times_extended})'
    if pawning.extension_notes:
        pawning.extension_notes += f'\n{extension_note}'
    else:
        pawning.extension_notes = extension_note
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        action='extend_pawning',
        entity_type='pawning',
        entity_id=pawning.id,
        description=f'Extended pawning: {pawning.pawning_number} by {extend_months} months',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    
    db.session.commit()
    
    flash(f'Pawning period extended by {extend_months} months! New maturity date: {new_maturity.strftime("%Y-%m-%d")}', 'success')
    return redirect(url_for('pawnings.view_pawning', id=id))

@pawnings_bp.route('/<int:id>/mark-auction', methods=['POST'])
@login_required
@permission_required('manage_pawnings')
def mark_auction(id):
    """Mark pawning for auction"""
    pawning = Pawning.query.get_or_404(id)
    
    if pawning.status == 'redeemed':
        flash('Cannot auction a redeemed pawning!', 'warning')
        return redirect(url_for('pawnings.view_pawning', id=id))
    
    auction_date_str = request.form.get('auction_date')
    if auction_date_str:
        pawning.auction_date = datetime.strptime(auction_date_str, '%Y-%m-%d').date()
    else:
        pawning.auction_date = datetime.utcnow().date()
    
    pawning.status = 'auctioned'
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        action='mark_auction',
        entity_type='pawning',
        entity_id=pawning.id,
        description=f'Marked pawning for auction: {pawning.pawning_number}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    
    db.session.commit()
    
    flash(f'Pawning marked for auction on {pawning.auction_date.strftime("%Y-%m-%d")}', 'success')
    return redirect(url_for('pawnings.view_pawning', id=id))
