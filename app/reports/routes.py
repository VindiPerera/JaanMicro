"""Reports routes"""
from flask import render_template, request, make_response, current_app, send_from_directory, abort
from flask_login import login_required
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import os
from app import db
from app.reports import reports_bp
from app.models import Customer, Loan, LoanPayment, Investment, InvestmentTransaction, Pawning, PawningPayment
from app.utils.decorators import permission_required
import io
import csv

@reports_bp.route('/')
@login_required
@permission_required('view_reports')
def index():
    """Reports dashboard"""
    # Calculate quick statistics
    from decimal import Decimal
    
    # Customer statistics
    total_customers = Customer.query.count()
    active_customers = Customer.query.filter_by(status='active').count()
    
    # Loan statistics
    total_loan_disbursed = db.session.query(func.sum(Loan.disbursed_amount)).filter(
        Loan.status.in_(['active', 'completed'])
    ).scalar() or 0
    active_loans = Loan.query.filter_by(status='active').count()
    
    # Investment statistics
    total_investment_amount = db.session.query(func.sum(Investment.principal_amount)).scalar() or 0
    active_investments = Investment.query.filter_by(status='active').count()
    
    # Pawning statistics
    active_pawnings = Pawning.query.filter_by(status='active').count()
    total_pawning_amount = db.session.query(func.sum(Pawning.loan_amount)).filter_by(status='active').scalar() or 0
    
    # Today's activity
    from datetime import date
    today = date.today()
    
    todays_loan_payments = db.session.query(func.sum(LoanPayment.payment_amount)).filter(
        LoanPayment.payment_date == today
    ).scalar() or 0
    
    todays_new_loans = Loan.query.filter(
        func.date(Loan.created_at) == today
    ).count()
    
    todays_new_customers = Customer.query.filter(
        func.date(Customer.created_at) == today
    ).count()
    
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
    loan_type = request.args.get('loan_type', '')
    
    query = Loan.query
    
    if start_date:
        query = query.filter(Loan.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Loan.created_at <= datetime.strptime(end_date, '%Y-%m-%d'))
    if status:
        query = query.filter_by(status=status)
    if loan_type:
        query = query.filter_by(loan_type=loan_type)
    
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
    
    # Loan by type
    type_breakdown = db.session.query(
        Loan.loan_type,
        func.count(Loan.id),
        func.sum(Loan.loan_amount)
    ).group_by(Loan.loan_type).all()
    
    return render_template('reports/loan_report.html',
                         title='Loan Report',
                         loans=loans,
                         loan_payments=loan_payments,
                         summary=summary,
                         status_breakdown=status_breakdown,
                         type_breakdown=type_breakdown,
                         start_date=start_date,
                         end_date=end_date,
                         status=status,
                         loan_type=loan_type)

@reports_bp.route('/collections')
@login_required
@permission_required('view_reports')
def collection_report():
    """Collection reports"""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Loan payments
    loan_query = LoanPayment.query
    if start_date:
        loan_query = loan_query.filter(LoanPayment.payment_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        loan_query = loan_query.filter(LoanPayment.payment_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    loan_payments = loan_query.order_by(LoanPayment.payment_date.desc()).all()
    total_loan_collection = sum(float(p.payment_amount) for p in loan_payments)
    
    # Pawning payments
    pawning_query = PawningPayment.query
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
    
    # Add counts for each customer
    for customer in customers:
        customer.active_loans_count = Loan.query.filter_by(customer_id=customer.id, status='active').count()
        customer.active_investments_count = Investment.query.filter_by(customer_id=customer.id, status='active').count()
        customer.active_pawnings_count = Pawning.query.filter_by(customer_id=customer.id, status='active').count()
    
    # Statistics
    summary = {
        'total_customers': Customer.query.count(),
        'active_customers': Customer.query.filter_by(status='active').count(),
        'kyc_verified': Customer.query.filter_by(kyc_verified=True).count(),
        'kyc_pending': Customer.query.filter_by(kyc_verified=False).count(),
        'customers_with_loans': db.session.query(func.count(func.distinct(Loan.customer_id))).filter_by(status='active').scalar() or 0,
        'customers_with_investments': db.session.query(func.count(func.distinct(Investment.customer_id))).filter_by(status='active').scalar() or 0,
        'customers_with_pawnings': db.session.query(func.count(func.distinct(Pawning.customer_id))).filter_by(status='active').scalar() or 0
    }
    
    # Geographic distribution
    district_breakdown = db.session.query(
        Customer.district,
        func.count(Customer.id).label('count')
    ).group_by(Customer.district).order_by(func.count(Customer.id).desc()).limit(10).all()
    
    # Occupation distribution
    occupation_breakdown = db.session.query(
        Customer.occupation,
        func.count(Customer.id).label('count')
    ).group_by(Customer.occupation).order_by(func.count(Customer.id).desc()).limit(10).all()
    
    # Get all available districts for filter dropdown
    available_districts = db.session.query(Customer.district).distinct().filter(Customer.district != None).order_by(Customer.district).all()
    available_districts = [d[0] for d in available_districts if d[0]]  # Convert to list and filter out None values
    
    return render_template('reports/customer_report.html',
                         title='Customer Report',
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
    """Investment reports"""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    investment_type = request.args.get('investment_type', '')
    
    query = Investment.query
    
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
    type_breakdown = db.session.query(
        Investment.investment_type,
        func.count(Investment.id),
        func.sum(Investment.current_amount)
    ).group_by(Investment.investment_type).all()
    
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
    maturing_soon = Investment.query.filter(
        Investment.maturity_date <= thirty_days,
        Investment.status == 'active'
    ).all()
    
    return render_template('reports/investment_report.html',
                         title='Investment Report',
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
    status_breakdown = db.session.query(
        Pawning.status,
        func.count(Pawning.id),
        func.sum(Pawning.outstanding_principal)
    ).group_by(Pawning.status).all()
    
    # Get overdue pawnings
    from datetime import date
    today = date.today()
    overdue_pawnings = Pawning.query.filter(
        Pawning.maturity_date < today,
        Pawning.status == 'active'
    ).all()
    
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

@reports_bp.route('/export/loans')
@login_required
@permission_required('view_reports')
def export_loans():
    """Export loans to CSV"""
    loans = Loan.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Loan Number', 'Customer', 'Loan Type', 'Loan Amount', 'Interest Rate', 
                    'Duration', 'Outstanding Amount', 'Status', 'Created Date'])
    
    # Write data
    for loan in loans:
        writer.writerow([
            loan.loan_number,
            loan.customer.full_name,
            loan.loan_type,
            loan.loan_amount,
            loan.interest_rate,
            loan.duration_months,
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
