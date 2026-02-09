"""Borrower management routes"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
from dateutil.relativedelta import relativedelta
from app import db
from app.investments import investments_bp
from app.models import Investment, InvestmentTransaction, Customer, ActivityLog, SystemSettings
from app.investments.forms import InvestmentForm, InvestmentTransactionForm
from app.utils.decorators import permission_required
from app.utils.helpers import generate_investment_number, get_current_branch_id, should_filter_by_branch, get_branch_filter_for_query

@investments_bp.route('/')
@login_required
@permission_required('manage_investments')
def list_investments():
    """List all borrowers"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    investment_type = request.args.get('investment_type', '')
    
    query = Investment.query
    
    # Filter by accessible branches
    branch_filter = get_branch_filter_for_query(Investment.branch_id)
    if branch_filter is not None:
        query = query.filter(branch_filter)
    
    if search:
        query = query.join(Customer).filter(
            db.or_(
                Investment.investment_number.ilike(f'%{search}%'),
                Customer.full_name.ilike(f'%{search}%'),
                Customer.customer_id.ilike(f'%{search}%')
            )
        )
    
    if status:
        query = query.filter_by(status=status)
    
    if investment_type:
        query = query.filter_by(investment_type=investment_type)
    
    investments = query.order_by(Investment.created_at.desc()).paginate(
        page=page, per_page=current_app.config['ITEMS_PER_PAGE'], error_out=False
    )
    
    return render_template('investments/list.html',
                         title='Borrowers',
                         investments=investments,
                         search=search,
                         status=status,
                         investment_type=investment_type)

@investments_bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('manage_investments')
def add_investment():
    """Add new borrower"""
    form = InvestmentForm()
    settings = SystemSettings.get_settings()
    
    # Get customers for dropdown
    customer_query = Customer.query.filter_by(status='active', kyc_verified=True)
    
    # Apply branch filtering
    customer_branch_filter = get_branch_filter_for_query(Customer.branch_id)
    if customer_branch_filter is not None:
        customer_query = customer_query.filter(customer_branch_filter)
    
    customers = customer_query.order_by(Customer.full_name).all()
    form.customer_id.choices = [(0, 'Select Customer')] + [(c.id, f'{c.customer_id} - {c.full_name}') for c in customers]
    
    # Pre-fill interest rate from settings on GET request
    if request.method == 'GET':
        form.interest_rate.data = settings.default_investment_interest_rate
    
    if form.validate_on_submit():
        # Validate customer selection
        if form.customer_id.data == 0:
            flash('Please select a customer!', 'error')
            return render_template('investments/add.html', title='Add Borrower', form=form)
        
        # Get customer to determine branch
        customer = Customer.query.get(form.customer_id.data)
        if not customer:
            flash('Customer not found!', 'error')
            return render_template('investments/add.html', title='Add Borrower', form=form)
        
        if not customer.branch_id:
            flash('Customer does not have a valid branch assigned!', 'error')
            return render_template('investments/add.html', title='Add Borrower', form=form)
        
        # Validate minimum investment amount
        if form.principal_amount.data < settings.minimum_investment_amount:
            flash(f'Principal amount cannot be less than Rs. {settings.minimum_investment_amount}!', 'error')
            return render_template('investments/add.html', title='Add Borrower', form=form)
        
        investment_number = generate_investment_number(settings.investment_number_prefix)
        
        # Calculate maturity amount
        if form.duration_months.data:
            from decimal import Decimal, ROUND_HALF_UP
            
            principal = Decimal(str(form.principal_amount.data))
            interest_rate = Decimal(str(form.interest_rate.data))
            duration = Decimal(str(form.duration_months.data))
            
            interest = principal * interest_rate * duration / (Decimal('12') * Decimal('100'))
            maturity_amount = principal + interest
            maturity_amount = float(maturity_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        else:
            maturity_amount = form.principal_amount.data
        
        maturity_date = None
        if form.duration_months.data:
            maturity_date = form.start_date.data + relativedelta(months=form.duration_months.data)
        
        investment = Investment(
            investment_number=investment_number,
            customer_id=form.customer_id.data,
            branch_id=customer.branch_id,
            investment_type=form.investment_type.data,
            principal_amount=form.principal_amount.data,
            interest_rate=form.interest_rate.data,
            duration_months=form.duration_months.data,
            maturity_amount=maturity_amount,
            current_amount=form.principal_amount.data,
            start_date=form.start_date.data,
            maturity_date=maturity_date,
            installment_amount=form.installment_amount.data,
            installment_frequency=form.installment_frequency.data,
            created_by=current_user.id,
            notes=form.notes.data
        )
        
        db.session.add(investment)
        db.session.flush()  # Flush to get the investment ID
        
        # Create initial transaction
        transaction = InvestmentTransaction(
            investment_id=investment.id,
            transaction_date=form.start_date.data,
            transaction_type='deposit',
            amount=form.principal_amount.data,
            balance_after=form.principal_amount.data,
            processed_by=current_user.id,
            notes='Initial deposit'
        )
        db.session.add(transaction)
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='create_investment',
            entity_type='investment',
            description=f'Created investment: {investment.investment_number}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'Borrower {investment.investment_number} created successfully!', 'success')
        return redirect(url_for('investments.view_investment', id=investment.id))

    return render_template('investments/add.html', title='Add Borrower', form=form)

@investments_bp.route('/<int:id>')
@login_required
def view_investment(id):
    """View borrower details"""
    investment = Investment.query.get_or_404(id)
    
    # Check branch access
    from app.utils.helpers import get_user_accessible_branch_ids
    accessible_branch_ids = get_user_accessible_branch_ids()
    if accessible_branch_ids and investment.branch_id not in accessible_branch_ids:
        flash('Access denied: Investment not found in accessible branches.', 'danger')
        return redirect(url_for('investments.list_investments'))
    
    transactions = investment.transactions.order_by(InvestmentTransaction.transaction_date.desc()).all()
    
    return render_template('investments/view.html',
                         title=f'Borrower: {investment.investment_number}',
                         investment=investment,
                         transactions=transactions)

@investments_bp.route('/<int:id>/transaction', methods=['GET', 'POST'])
@login_required
@permission_required('manage_investments')
def add_transaction(id):
    """Add borrower transaction"""
    investment = Investment.query.get_or_404(id)
    
    # Check branch access
    from app.utils.helpers import get_user_accessible_branch_ids
    accessible_branch_ids = get_user_accessible_branch_ids()
    if accessible_branch_ids and investment.branch_id not in accessible_branch_ids:
        flash('Access denied: Borrower not found in accessible branches.', 'danger')
        return redirect(url_for('investments.list_investments'))

    if investment.status not in ['active']:
        flash('Cannot add transaction for this borrower!', 'warning')
        return redirect(url_for('investments.view_investment', id=id))
    
    form = InvestmentTransactionForm()
    
    if form.validate_on_submit():
        amount = form.amount.data
        transaction_type = form.transaction_type.data
        
        # Calculate new balance
        if transaction_type in ['deposit', 'interest_credit']:
            new_balance = investment.current_amount + amount
        else:  # withdrawal
            if amount > investment.current_amount:
                flash('Withdrawal amount exceeds current balance!', 'danger')
                return redirect(url_for('investments.add_transaction', id=id))
            new_balance = investment.current_amount - amount
        
        transaction = InvestmentTransaction(
            investment_id=investment.id,
            transaction_date=form.transaction_date.data,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=new_balance,
            payment_method=form.payment_method.data,
            reference_number=form.reference_number.data,
            notes=form.notes.data,
            processed_by=current_user.id
        )
        
        db.session.add(transaction)
        
        # Update investment balance
        investment.current_amount = new_balance
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='add_investment_transaction',
            entity_type='investment',
            entity_id=investment.id,
            description=f'Added {transaction_type} for borrower: {investment.investment_number}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('investments.view_investment', id=id))
    
    return render_template('investments/transaction.html',
                         title=f'Add Transaction: {investment.investment_number}',
                         form=form,
                         investment=investment)
