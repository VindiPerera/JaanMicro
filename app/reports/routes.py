"""Reports routes"""
from flask import render_template, request, make_response, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import os
from app import db
from app.reports import reports_bp
from app.models import Customer, Loan, LoanPayment, Investment, InvestmentTransaction, Pawning, PawningPayment
from app.utils.decorators import permission_required
from app.utils.helpers import get_current_branch_id, should_filter_by_branch
import io
import csv

@reports_bp.route('/')
@login_required
def index():
    """Reports dashboard"""
    # Allow access if user has either view_reports or view_collection_reports permission
    if not (current_user.has_permission('view_reports') or current_user.has_permission('view_collection_reports')):
        abort(403)
    
    # Calculate quick statistics
    from decimal import Decimal
    
    # Get branch filtering info
    current_branch_id = get_current_branch_id()
    should_filter = should_filter_by_branch()
    
    # Customer statistics
    customer_query = Customer.query
    if should_filter and current_branch_id:
        customer_query = customer_query.filter_by(branch_id=current_branch_id)
    
    total_customers = customer_query.count()
    active_customers = customer_query.filter_by(status='active').count()
    
    # Loan statistics
    loan_query = Loan.query
    if should_filter and current_branch_id:
        loan_query = loan_query.filter_by(branch_id=current_branch_id)
    
    total_loan_disbursed = db.session.query(func.sum(Loan.disbursed_amount)).filter(
        Loan.status.in_(['active', 'completed'])
    )
    if should_filter and current_branch_id:
        total_loan_disbursed = total_loan_disbursed.filter(Loan.branch_id == current_branch_id)
    total_loan_disbursed = total_loan_disbursed.scalar() or 0
    
    active_loans = loan_query.filter_by(status='active').count()
    
    # Investment statistics
    investment_query = Investment.query
    if should_filter and current_branch_id:
        investment_query = investment_query.filter_by(branch_id=current_branch_id)
    
    total_investment_amount = db.session.query(func.sum(Investment.principal_amount))
    if should_filter and current_branch_id:
        total_investment_amount = total_investment_amount.filter(Investment.branch_id == current_branch_id)
    total_investment_amount = total_investment_amount.scalar() or 0
    
    active_investments = investment_query.filter_by(status='active').count()
    
    # Pawning statistics
    pawning_query = Pawning.query
    if should_filter and current_branch_id:
        pawning_query = pawning_query.filter_by(branch_id=current_branch_id)
    
    active_pawnings = pawning_query.filter_by(status='active').count()
    total_pawning_amount = db.session.query(func.sum(Pawning.loan_amount)).filter_by(status='active')
    if should_filter and current_branch_id:
        total_pawning_amount = total_pawning_amount.filter(Pawning.branch_id == current_branch_id)
    total_pawning_amount = total_pawning_amount.scalar() or 0
    
    # Today's activity
    from datetime import date
    today = date.today()
    
    todays_loan_payments_query = db.session.query(func.sum(LoanPayment.payment_amount)).join(Loan).filter(
        LoanPayment.payment_date == today
    )
    if should_filter and current_branch_id:
        todays_loan_payments_query = todays_loan_payments_query.filter(Loan.branch_id == current_branch_id)
    todays_loan_payments = todays_loan_payments_query.scalar() or 0
    
    todays_new_loans_query = Loan.query.filter(
        func.date(Loan.created_at) == today
    )
    if should_filter and current_branch_id:
        todays_new_loans_query = todays_new_loans_query.filter_by(branch_id=current_branch_id)
    todays_new_loans = todays_new_loans_query.count()
    
    todays_new_customers_query = Customer.query.filter(
        func.date(Customer.created_at) == today
    )
    if should_filter and current_branch_id:
        todays_new_customers_query = todays_new_customers_query.filter_by(branch_id=current_branch_id)
    todays_new_customers = todays_new_customers_query.count()
    
    stats = {
        'total_customers': total_customers,
        'active_customers': active_customers,
        'total_loan_disbursed': float(total_loan_disbursed),
        'active_loans': active_loans,
        'total_investment_amount': float(total_investment_amount),
        'active_investments': active_investments,
        'active_pawnings': active_pawnings,
        'total_pawning_amount': float(total_pawning_amount),
        'todays_collections': float(todays_loan_payments),
        'todays_new_loans': todays_new_loans,
        'todays_new_customers': todays_new_customers
    }
    
    return render_template('reports/index.html', title='Reports', stats=stats)

@reports_bp.route('/loans')
@login_required
@permission_required('view_reports')
def loan_report():
    """Loan reports"""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status = request.args.get('status', '')
    loan_purpose = request.args.get('loan_purpose', '')
    
    query = Loan.query
    
    # Apply branch filtering
    current_branch_id = get_current_branch_id()
    if should_filter_by_branch() and current_branch_id:
        query = query.filter_by(branch_id=current_branch_id)
    
    if start_date:
        query = query.filter(Loan.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Loan.created_at <= datetime.strptime(end_date, '%Y-%m-%d'))
    if status:
        query = query.filter_by(status=status)
    if loan_purpose:
        query = query.filter_by(loan_purpose=loan_purpose)
    
    loans = query.all()
    
    # Calculate payment stats for each loan
    loan_payments = {}
    for loan in loans:
        payment_stats = db.session.query(
            func.sum(LoanPayment.principal_amount),
            func.sum(LoanPayment.interest_amount)
        ).filter(LoanPayment.loan_id == loan.id)
        
        if start_date:
            payment_stats = payment_stats.filter(LoanPayment.payment_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            payment_stats = payment_stats.filter(LoanPayment.payment_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        principal, interest = payment_stats.first()
        from decimal import Decimal
        principal_dec = Decimal(str(principal or 0))
        interest_dec = Decimal(str(interest or 0))
        total_dec = principal_dec + interest_dec
        
        # Calculate expected interest based on loan type
        expected_interest = loan.get_total_expected_interest()
        interest_variance = interest_dec - expected_interest
        
        loan_payments[loan.id] = {
            'principal': float(principal_dec),
            'interest': float(interest_dec),
            'total': float(total_dec),
            'expected_interest': float(expected_interest),
            'interest_variance': float(interest_variance),
            'interest_type': loan.interest_type
        }
    
    # Calculate overall statistics
    principal_collected = sum(p['principal'] for p in loan_payments.values())
    interest_collected = sum(p['interest'] for p in loan_payments.values())
    total_collected = principal_collected + interest_collected
    
    # Calculate statistics
    summary = {
        'total_loans': len(loans),
        'total_disbursed': sum(float(loan.disbursed_amount or 0) for loan in loans),
        'total_outstanding': sum(float(loan.outstanding_amount or 0) for loan in loans),
        'total_collected': total_collected,
        'principal_collected': principal_collected,
        'interest_profit': interest_collected
    }
    
    # Loan by status
    status_breakdown = db.session.query(
        Loan.status,
        func.count(Loan.id),
        func.sum(Loan.outstanding_amount)
    ).group_by(Loan.status).all()
    
    # Loan by purpose
    purpose_breakdown = db.session.query(
        Loan.loan_purpose,
        func.count(Loan.id),
        func.sum(Loan.loan_amount)
    ).group_by(Loan.loan_purpose).all()
    
    return render_template('reports/loan_report.html',
                         title='Loan Report',
                         loans=loans,
                         loan_payments=loan_payments,
                         summary=summary,
                         status_breakdown=status_breakdown,
                         purpose_breakdown=purpose_breakdown,
                         start_date=start_date,
                         end_date=end_date,
                         status=status,
                         loan_purpose=loan_purpose)

@reports_bp.route('/collections')
@login_required
@permission_required('view_collection_reports')
def collection_report():
    """Collection reports"""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Get branch filtering info
    current_branch_id = get_current_branch_id()
    should_filter = should_filter_by_branch()
    
    # Loan payments
    loan_query = LoanPayment.query.join(Loan)
    if should_filter and current_branch_id:
        loan_query = loan_query.filter(Loan.branch_id == current_branch_id)
    if start_date:
        loan_query = loan_query.filter(LoanPayment.payment_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        loan_query = loan_query.filter(LoanPayment.payment_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    loan_payments = loan_query.order_by(LoanPayment.payment_date.desc()).all()
    total_loan_collection = sum(float(p.payment_amount) for p in loan_payments)
    
    # Pawning payments
    pawning_query = PawningPayment.query.join(Pawning)
    if should_filter and current_branch_id:
        pawning_query = pawning_query.filter(Pawning.branch_id == current_branch_id)
    if start_date:
        pawning_query = pawning_query.filter(PawningPayment.payment_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        pawning_query = pawning_query.filter(PawningPayment.payment_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    pawning_payments = pawning_query.order_by(PawningPayment.payment_date.desc()).all()
    total_pawning_collection = sum(float(p.payment_amount) for p in pawning_payments)
    
    # Calculate summary
    summary = {
        'total_count': len(loan_payments) + len(pawning_payments),
        'total_amount': total_loan_collection + total_pawning_collection,
        'total_principal': sum(float(p.principal_amount or 0) for p in loan_payments) + sum(float(p.principal_amount or 0) for p in pawning_payments),
        'total_interest': sum(float(p.interest_amount or 0) for p in loan_payments) + sum(float(p.interest_amount or 0) for p in pawning_payments)
    }
    
    # Daily collection breakdown
    daily_breakdown = db.session.query(
        LoanPayment.payment_date,
        func.sum(LoanPayment.payment_amount)
    ).group_by(LoanPayment.payment_date).order_by(LoanPayment.payment_date.desc()).limit(30).all()
    
    return render_template('reports/collection_report.html',
                         title='Collection Report',
                         loan_payments=loan_payments,
                         pawning_payments=pawning_payments,
                         summary=summary,
                         daily_breakdown=daily_breakdown,
                         start_date=start_date,
                         end_date=end_date)

@reports_bp.route('/customers')
@login_required
@permission_required('view_reports')
def customer_report():
    """Customer reports"""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status = request.args.get('status', '')
    kyc_status = request.args.get('kyc_status', '')
    district = request.args.get('district', '')
    
    query = Customer.query
    
    # Apply branch filtering
    current_branch_id = get_current_branch_id()
    if should_filter_by_branch() and current_branch_id:
        query = query.filter_by(branch_id=current_branch_id)
    
    # Date filtering
    if start_date:
        query = query.filter(Customer.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        # Add one day to include the end date
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(Customer.created_at < end_datetime)
    
    # Status filtering
    if status:
        query = query.filter_by(status=status)
    if kyc_status == 'verified':
        query = query.filter_by(kyc_verified=True)
    elif kyc_status == 'pending':
        query = query.filter_by(kyc_verified=False)
    
    # District filtering
    if district:
        query = query.filter_by(district=district)
    
    customers = query.all()
    
    # Add counts for each customer (also filtered by branch)
    for customer in customers:
        loan_count_query = Loan.query.filter_by(customer_id=customer.id, status='active')
        investment_count_query = Investment.query.filter_by(customer_id=customer.id, status='active')
        pawning_count_query = Pawning.query.filter_by(customer_id=customer.id, status='active')
        
        if should_filter_by_branch() and current_branch_id:
            loan_count_query = loan_count_query.filter_by(branch_id=current_branch_id)
            investment_count_query = investment_count_query.filter_by(branch_id=current_branch_id)
            pawning_count_query = pawning_count_query.filter_by(branch_id=current_branch_id)
        
        customer.active_loans_count = loan_count_query.count()
        customer.active_investments_count = investment_count_query.count()
        customer.active_pawnings_count = pawning_count_query.count()
    
    # Statistics
    summary = {
        'total_customers': query.count(),
        'active_customers': query.filter_by(status='active').count(),
        'kyc_verified': query.filter_by(kyc_verified=True).count(),
        'kyc_pending': query.filter_by(kyc_verified=False).count(),
    }
    
    # Get counts for customers with active products (filtered by branch)
    loan_customer_query = db.session.query(func.count(func.distinct(Loan.customer_id)))
    investment_customer_query = db.session.query(func.count(func.distinct(Investment.customer_id)))
    pawning_customer_query = db.session.query(func.count(func.distinct(Pawning.customer_id)))
    
    if should_filter_by_branch() and current_branch_id:
        loan_customer_query = loan_customer_query.filter(Loan.branch_id == current_branch_id)
        investment_customer_query = investment_customer_query.filter(Investment.branch_id == current_branch_id)
        pawning_customer_query = pawning_customer_query.filter(Pawning.branch_id == current_branch_id)
    
    summary.update({
        'customers_with_loans': loan_customer_query.filter(Loan.status == 'active').scalar() or 0,
        'customers_with_investments': investment_customer_query.filter(Investment.status == 'active').scalar() or 0,
        'customers_with_pawnings': pawning_customer_query.filter(Pawning.status == 'active').scalar() or 0
    })
    
    # Geographic distribution
    district_query = db.session.query(
        Customer.district,
        func.count(Customer.id).label('count')
    )
    if should_filter_by_branch() and current_branch_id:
        district_query = district_query.filter(Customer.branch_id == current_branch_id)
    district_breakdown = district_query.group_by(Customer.district).order_by(func.count(Customer.id).desc()).limit(10).all()
    
    # Occupation distribution
    occupation_query = db.session.query(
        Customer.occupation,
        func.count(Customer.id).label('count')
    )
    if should_filter_by_branch() and current_branch_id:
        occupation_query = occupation_query.filter(Customer.branch_id == current_branch_id)
    occupation_breakdown = occupation_query.group_by(Customer.occupation).order_by(func.count(Customer.id).desc()).limit(10).all()
    
    # Get all available districts for filter dropdown
    districts_query = db.session.query(Customer.district).distinct().filter(Customer.district != None)
    if should_filter_by_branch() and current_branch_id:
        districts_query = districts_query.filter(Customer.branch_id == current_branch_id)
    available_districts = districts_query.order_by(Customer.district).all()
    available_districts = [d[0] for d in available_districts if d[0]]  # Convert to list and filter out None values
    
    return render_template('reports/customer_report.html',
                         title='Member Report',
                         customers=customers,
                         summary=summary,
                         district_breakdown=district_breakdown,
                         occupation_breakdown=occupation_breakdown,
                         available_districts=available_districts,
                         start_date=start_date,
                         end_date=end_date,
                         status=status,
                         kyc_status=kyc_status,
                         district=district)

@reports_bp.route('/investments')
@login_required
@permission_required('view_reports')
def investment_report():
    """Borrower reports"""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    investment_type = request.args.get('investment_type', '')
    
    query = Investment.query
    
    # Apply branch filtering
    current_branch_id = get_current_branch_id()
    if should_filter_by_branch() and current_branch_id:
        query = query.filter_by(branch_id=current_branch_id)
    
    if start_date:
        query = query.filter(Investment.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Investment.created_at <= datetime.strptime(end_date, '%Y-%m-%d'))
    if investment_type:
        query = query.filter_by(investment_type=investment_type)
    
    investments = query.all()
    
    # Calculate interest paid/accrued (this is expense for the company)
    total_interest_expense = sum(float(inv.current_amount - inv.principal_amount) for inv in investments if inv.current_amount and inv.current_amount > inv.principal_amount)
    total_current = sum(float(inv.current_amount) for inv in investments if inv.current_amount)
    total_maturity = sum(float(inv.maturity_amount) for inv in investments if inv.maturity_amount)
    
    # Statistics
    summary = {
        'total_investments': len(investments),
        'total_principal': sum(float(inv.principal_amount) for inv in investments),
        'current_amount': total_current,
        'total_maturity': total_maturity,
        'total_interest_paid': total_interest_expense,
        'interest_expense': total_interest_expense  # This is a cost/expense
    }
    
    # Type breakdown
    type_breakdown_query = db.session.query(
        Investment.investment_type,
        func.count(Investment.id),
        func.sum(Investment.current_amount)
    )
    if should_filter_by_branch() and current_branch_id:
        type_breakdown_query = type_breakdown_query.filter(Investment.branch_id == current_branch_id)
    type_breakdown = type_breakdown_query.group_by(Investment.investment_type).all()
    
    # Get investments by type for display
    investments_by_type = []
    for inv_type, count, total in type_breakdown:
        investments_by_type.append({
            'investment_type': inv_type,
            'count': count,
            'total': float(total or 0)
        })
    
    # Get maturing investments (within next 30 days)
    from datetime import date, timedelta
    thirty_days = date.today() + timedelta(days=30)
    maturing_query = Investment.query.filter(
        Investment.maturity_date <= thirty_days,
        Investment.status == 'active'
    )
    if should_filter_by_branch() and current_branch_id:
        maturing_query = maturing_query.filter_by(branch_id=current_branch_id)
    maturing_soon = maturing_query.all()
    
    return render_template('reports/investment_report.html',
                         title='Borrower Report',
                         investments=investments,
                         summary=summary,
                         type_breakdown=type_breakdown,
                         investments_by_type=investments_by_type,
                         maturing_soon=maturing_soon,
                         start_date=start_date,
                         end_date=end_date,
                         investment_type=investment_type)

@reports_bp.route('/pawnings')
@login_required
@permission_required('view_reports')
def pawning_report():
    """Pawning reports"""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status = request.args.get('status', '')
    item_type = request.args.get('item_type', '')
    
    query = Pawning.query
    
    # Apply branch filtering
    current_branch_id = get_current_branch_id()
    if should_filter_by_branch() and current_branch_id:
        query = query.filter_by(branch_id=current_branch_id)
    
    if start_date:
        query = query.filter(Pawning.pawning_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Pawning.pawning_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if status:
        query = query.filter_by(status=status)
    if item_type:
        query = query.filter_by(item_type=item_type)
    
    pawnings = query.all()
    
    # Calculate total interest collected from pawning payments
    total_interest_collected = db.session.query(func.sum(PawningPayment.interest_amount)).join(
        Pawning, PawningPayment.pawning_id == Pawning.id
    )
    if start_date:
        total_interest_collected = total_interest_collected.filter(PawningPayment.payment_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        total_interest_collected = total_interest_collected.filter(PawningPayment.payment_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if status:
        total_interest_collected = total_interest_collected.filter(Pawning.status == status)
    
    interest_profit = float(total_interest_collected.scalar() or 0)
    
    # Statistics
    from decimal import Decimal
    total_loan = sum(Decimal(str(pawn.loan_amount)) for pawn in pawnings)
    total_outstanding = sum(Decimal(str(pawn.outstanding_principal or 0)) for pawn in pawnings if pawn.status == 'active')
    total_collected = sum(Decimal(str(pawn.principal_paid or 0)) + Decimal(str(pawn.total_interest_paid or 0)) for pawn in pawnings)
    
    summary = {
        'total_pawnings': len(pawnings),
        'total_loan_amount': float(total_loan),
        'total_outstanding': float(total_outstanding),
        'total_collected': float(total_collected),
        'interest_profit': interest_profit
    }
    
    # Status breakdown
    status_breakdown_query = db.session.query(
        Pawning.status,
        func.count(Pawning.id),
        func.sum(Pawning.outstanding_principal)
    )
    if should_filter_by_branch() and current_branch_id:
        status_breakdown_query = status_breakdown_query.filter(Pawning.branch_id == current_branch_id)
    status_breakdown = status_breakdown_query.group_by(Pawning.status).all()
    
    # Get overdue pawnings
    from datetime import date
    today = date.today()
    overdue_query = Pawning.query.filter(
        Pawning.maturity_date < today,
        Pawning.status == 'active'
    )
    if should_filter_by_branch() and current_branch_id:
        overdue_query = overdue_query.filter_by(branch_id=current_branch_id)
    overdue_pawnings = overdue_query.all()
    
    return render_template('reports/pawning_report.html',
                         title='Pawning Report',
                         pawnings=pawnings,
                         summary=summary,
                         status_breakdown=status_breakdown,
                         overdue_pawnings=overdue_pawnings,
                         today=today,
                         start_date=start_date,
                         end_date=end_date,
                         status=status,
                         item_type=item_type)

@reports_bp.route('/arrears')
@login_required
@permission_required('view_reports')
def arrears_report():
    """Arrears report - overdue amounts that customers need to pay"""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status = request.args.get('status', 'active')  # Default to active
    product_type = request.args.get('product_type', '')  # loan, pawning, or all
    
    # Get branch filtering info
    current_branch_id = get_current_branch_id()
    should_filter = should_filter_by_branch()
    
    from datetime import date
    today = date.today()
    
    arrears_data = []
    
    # Loan arrears - only active loans past maturity date
    if product_type in ['', 'loan']:
        # Temporarily show all active loans for debugging
        loan_query = Loan.query.filter_by(status='active')
        
        if should_filter and current_branch_id:
            loan_query = loan_query.filter_by(branch_id=current_branch_id)
        
        if start_date:
            loan_query = loan_query.filter(Loan.disbursement_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            loan_query = loan_query.filter(Loan.disbursement_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        loans = loan_query.all()
        
        # Filter loans that are actually overdue (past maturity date)
        overdue_loans = []
        for loan in loans:
            if loan.maturity_date and loan.maturity_date < today:
                overdue_loans.append(loan)
        
        loans = overdue_loans
        
        for loan in loans:
            from decimal import Decimal, ROUND_HALF_UP
            
            # Calculate what's left to pay
            disbursed = Decimal(str(loan.disbursed_amount or loan.loan_amount))
            principal_paid = loan.get_total_paid_principal()
            outstanding_principal = disbursed - principal_paid
            
            # Calculate remaining interest based on loan type
            interest_paid = loan.get_total_paid_interest()
            
            # Handle special loan types that use flat interest calculations
            if loan.loan_type in ['type1_9weeks', '54_daily', 'type4_micro', 'type4_daily']:
                # For these special types, calculate total expected interest based on the original calculation
                from decimal import Decimal, ROUND_HALF_UP
                
                disbursed = Decimal(str(loan.disbursed_amount or loan.loan_amount))
                interest_rate = Decimal(str(loan.interest_rate))
                
                if loan.loan_type == 'type1_9weeks':
                    # Type 1: Interest = Interest rate * 2, Total Interest = (Interest * disbursed) / 100
                    total_interest = (interest_rate * Decimal('2') * disbursed) / Decimal('100')
                elif loan.loan_type == '54_daily':
                    # 54 Daily: Same as Type 1
                    total_interest = (interest_rate * Decimal('2') * disbursed) / Decimal('100')
                elif loan.loan_type == 'type4_micro':
                    # Type 4 Micro: Full Interest = Interest Rate * Months
                    months = Decimal(str(loan.duration_months))
                    total_interest = (interest_rate * months * disbursed) / Decimal('100')
                elif loan.loan_type == 'type4_daily':
                    # Type 4 Daily: Same as Type 4 Micro
                    months = Decimal(str(loan.duration_months))
                    total_interest = (interest_rate * months * disbursed) / Decimal('100')
                else:
                    # Fallback
                    total_interest = loan.get_total_expected_interest()
                
                remaining_interest = total_interest - interest_paid
            elif loan.interest_type == 'flat':
                # Standard flat interest loans
                total_expected_interest = loan.get_total_expected_interest()
                remaining_interest = total_expected_interest - interest_paid
            else:
                # For reducing balance loans
                # The remaining interest is not fixed - it depends on remaining principal
                # Show accrued interest + estimated future interest on remaining principal
                accrued_interest = loan.calculate_accrued_interest()
                
                # Estimate remaining interest based on outstanding principal
                # This is an approximation for arrears reporting
                if loan.duration_months and outstanding_principal > 0:
                    # Calculate remaining months (approximate)
                    total_paid = Decimal(str(loan.paid_amount or 0))
                    installment = Decimal(str(loan.installment_amount))
                    if installment > 0:
                        paid_installments = (total_paid / installment).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                        remaining_installments = max(Decimal('0'), Decimal(str(loan.duration_months)) - paid_installments)
                        
                        # Estimate average interest per remaining installment
                        # This is a rough estimate: (Outstanding Principal * Rate * Remaining Time) / 2
                        # Divided by 2 because principal reduces over time
                        annual_rate = Decimal(str(loan.interest_rate)) / Decimal('100')
                        remaining_time = remaining_installments / Decimal('12')
                        estimated_future_interest = (outstanding_principal * annual_rate * remaining_time) / Decimal('2')
                        remaining_interest = accrued_interest + estimated_future_interest
                    else:
                        remaining_interest = accrued_interest
                else:
                    remaining_interest = accrued_interest
            
            # Total arrears
            penalty = Decimal(str(loan.penalty_amount or 0))
            total_arrears = outstanding_principal + remaining_interest + penalty
            
            # Calculate overdue status (all arrears are overdue by definition)
            from datetime import date
            overdue_days = 0
            is_overdue = True  # All arrears are overdue
            if loan.maturity_date:
                days_diff = (date.today() - loan.maturity_date).days
                overdue_days = max(0, days_diff)  # Ensure non-negative
            
            arrears_data.append({
                'product_type': 'Loan',
                'reference_number': loan.loan_number,
                'customer_name': loan.customer.full_name,
                'customer_id': loan.customer.customer_id,
                'disbursement_date': loan.disbursement_date,
                'maturity_date': loan.maturity_date,
                'original_amount': float(disbursed),
                'principal_outstanding': float(outstanding_principal),
                'interest_outstanding': float(remaining_interest),
                'penalty': float(penalty),
                'total_arrears': float(total_arrears),
                'is_overdue': is_overdue,
                'overdue_days': overdue_days,
                'loan_type': loan.loan_type,
                'interest_type': loan.interest_type
            })
    
    # Pawning arrears - only active pawnings past maturity date
    if product_type in ['', 'pawning']:
        # Temporarily show all active pawnings for debugging
        pawning_query = Pawning.query.filter_by(status='active')
        
        if should_filter and current_branch_id:
            pawning_query = pawning_query.filter_by(branch_id=current_branch_id)
        
        if start_date:
            pawning_query = pawning_query.filter(Pawning.pawning_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            pawning_query = pawning_query.filter(Pawning.pawning_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        pawnings = pawning_query.all()
        
        # Filter pawnings that are actually overdue (past maturity date)
        overdue_pawnings = []
        for pawning in pawnings:
            maturity_date = pawning.extended_date or pawning.maturity_date
            if maturity_date and maturity_date < today:
                overdue_pawnings.append(pawning)
        
        pawnings = overdue_pawnings
        
        for pawning in pawnings:
            from decimal import Decimal
            
            # Calculate what's left to pay
            loan_amount = Decimal(str(pawning.loan_amount))
            principal_paid = Decimal(str(pawning.principal_paid or 0))
            outstanding_principal = loan_amount - principal_paid
            
            # Calculate interest due
            interest_due = Decimal(str(pawning.interest_due or 0))
            penalty = Decimal(str(pawning.total_penalty or 0))
            
            total_arrears = outstanding_principal + interest_due + penalty
            
            # Calculate overdue status (all arrears are overdue by definition)
            from datetime import date
            overdue_days = 0
            is_overdue = True  # All arrears are overdue
            maturity_date = pawning.extended_date or pawning.maturity_date
            if maturity_date:
                days_diff = (date.today() - maturity_date).days
                overdue_days = max(0, days_diff)  # Ensure non-negative
            
            arrears_data.append({
                'product_type': 'Pawning',
                'reference_number': pawning.pawning_number,
                'customer_name': pawning.customer.full_name,
                'customer_id': pawning.customer.customer_id,
                'disbursement_date': pawning.pawning_date,
                'maturity_date': maturity_date,
                'original_amount': float(loan_amount),
                'principal_outstanding': float(outstanding_principal),
                'interest_outstanding': float(interest_due),
                'penalty': float(penalty),
                'total_arrears': float(total_arrears),
                'is_overdue': is_overdue,
                'overdue_days': overdue_days,
                'loan_type': pawning.item_type,
                'interest_type': 'monthly'
            })
    
    # Sort by total arrears descending
    arrears_data.sort(key=lambda x: x['total_arrears'], reverse=True)
    
    # Calculate summary statistics
    from decimal import Decimal
    total_arrears = sum(Decimal(str(item['total_arrears'])) for item in arrears_data)
    total_principal = sum(Decimal(str(item['principal_outstanding'])) for item in arrears_data)
    total_interest = sum(Decimal(str(item['interest_outstanding'])) for item in arrears_data)
    total_penalty = sum(Decimal(str(item['penalty'])) for item in arrears_data)
    
    overdue_items = [item for item in arrears_data if item['is_overdue']]
    overdue_amount = sum(Decimal(str(item['total_arrears'])) for item in overdue_items)
    
    summary = {
        'total_accounts': len(arrears_data),
        'total_arrears': float(total_arrears),
        'total_principal': float(total_principal),
        'total_interest': float(total_interest),
        'total_penalty': float(total_penalty),
        'overdue_accounts': len(overdue_items),
        'overdue_amount': float(overdue_amount)
    }
    
    # Breakdown by product type
    loan_arrears = [item for item in arrears_data if item['product_type'] == 'Loan']
    pawning_arrears = [item for item in arrears_data if item['product_type'] == 'Pawning']
    
    product_breakdown = [
        {
            'product_type': 'Loan',
            'count': len(loan_arrears),
            'total_arrears': sum(item['total_arrears'] for item in loan_arrears)
        },
        {
            'product_type': 'Pawning',
            'count': len(pawning_arrears),
            'total_arrears': sum(item['total_arrears'] for item in pawning_arrears)
        }
    ]
    
    return render_template('reports/arrears_report.html',
                         title='Arrears Report',
                         arrears_data=arrears_data,
                         summary=summary,
                         product_breakdown=product_breakdown,
                         start_date=start_date,
                         end_date=end_date,
                         status=status,
                         product_type=product_type)

@reports_bp.route('/export/loans')
@login_required
@permission_required('view_reports')
def export_loans():
    """Export loans to CSV"""
    query = Loan.query
    
    # Apply branch filtering
    current_branch_id = get_current_branch_id()
    if should_filter_by_branch() and current_branch_id:
        query = query.filter_by(branch_id=current_branch_id)
    
    loans = query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Loan Number', 'Customer', 'Loan Purpose', 'Calculation Type', 'Loan Amount', 'Interest Rate', 
                    'Duration', 'Outstanding Amount', 'Status', 'Created Date'])
    
    # Write data
    for loan in loans:
        # Handle duration display
        if loan.duration_weeks:
            duration = f"{loan.duration_weeks} weeks"
        elif loan.duration_months:
            duration = f"{loan.duration_months} months"
        else:
            duration = "N/A"
            
        writer.writerow([
            loan.loan_number,
            loan.customer.full_name,
            loan.loan_purpose or 'N/A',
            loan.loan_type or 'N/A',
            loan.loan_amount,
            loan.interest_rate,
            duration,
            loan.outstanding_amount,
            loan.status,
            loan.created_at.strftime('%Y-%m-%d')
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=loans_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return response

@reports_bp.route('/customer/<int:customer_id>/kyc/<document_type>')
@login_required
@permission_required('view_reports')
def view_kyc_document(customer_id, document_type):
    """View customer KYC documents"""
    customer = Customer.query.get_or_404(customer_id)
    
    # Define allowed document types and their corresponding fields
    document_fields = {
        'nic_front': customer.nic_front_image,
        'nic_back': customer.nic_back_image,
        'photo': customer.photo,
        'proof_of_address': customer.proof_of_address
    }
    
    if document_type not in document_fields:
        abort(404)
    
    document_path = document_fields[document_type]
    if not document_path:
        abort(404, description="Document not found")
    
    # Construct full path
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
    full_path = os.path.join(upload_folder, document_path)
    
    if not os.path.exists(full_path):
        abort(404, description="Document file not found")
    
    # Get directory and filename
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    
    return send_from_directory(directory, filename)
