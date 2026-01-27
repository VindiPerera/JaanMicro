"""Main routes"""
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app.main import main_bp
from app.models import Customer, Loan, Investment, Pawning, User
from app import db
from sqlalchemy import func
from datetime import datetime, timedelta
from app.utils.helpers import get_current_branch_id, get_current_branch, should_filter_by_branch

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    current_branch_id = get_current_branch_id()
    should_filter = should_filter_by_branch()
    
    # Get statistics based on user role
    customer_query = Customer.query.filter_by(status='active')
    if should_filter and current_branch_id:
        customer_query = customer_query.filter_by(branch_id=current_branch_id)
    
    stats = {
        'total_customers': customer_query.count(),
        'total_users': User.query.filter_by(is_active=True).count(),
        'kyc_pending': customer_query.filter_by(kyc_verified=False).count(),
    }
    
    # Loan statistics
    loan_query = Loan.query.filter_by(status='active')
    if should_filter and current_branch_id:
        loan_query = loan_query.filter_by(branch_id=current_branch_id)
    active_loans = loan_query.all()
    stats['active_loans'] = len(active_loans)
    stats['total_loan_outstanding'] = sum(float(loan.outstanding_amount or 0) for loan in active_loans)
    
    loan_disbursed_query = Loan.query.filter(Loan.status.in_(['active', 'completed']))
    if should_filter and current_branch_id:
        loan_disbursed_query = loan_disbursed_query.filter_by(branch_id=current_branch_id)
    stats['total_loan_disbursed'] = db.session.query(func.sum(Loan.disbursed_amount)).filter(
        Loan.status.in_(['active', 'completed'])
    ).scalar() or 0
    
    # Investment statistics
    investment_query = Investment.query.filter_by(status='active')
    if should_filter and current_branch_id:
        investment_query = investment_query.filter_by(branch_id=current_branch_id)
    active_investments = investment_query.all()
    stats['active_investments'] = len(active_investments)
    stats['total_investment_amount'] = sum(inv.current_amount or 0 for inv in active_investments)
    
    # Pawning statistics
    pawning_query = Pawning.query.filter_by(status='active')
    if should_filter and current_branch_id:
        pawning_query = pawning_query.filter_by(branch_id=current_branch_id)
    active_pawnings = pawning_query.all()
    stats['active_pawnings'] = len(active_pawnings)
    stats['total_pawning_outstanding'] = sum(pawn.outstanding_principal or 0 for pawn in active_pawnings)
    
    # Recent activities
    recent_loans_query = Loan.query
    if should_filter and current_branch_id:
        recent_loans_query = recent_loans_query.filter_by(branch_id=current_branch_id)
    recent_loans = recent_loans_query.order_by(Loan.created_at.desc()).limit(5).all()
    
    recent_customers_query = Customer.query
    if should_filter and current_branch_id:
        recent_customers_query = recent_customers_query.filter_by(branch_id=current_branch_id)
    recent_customers = recent_customers_query.order_by(Customer.created_at.desc()).limit(5).all()
    
    # Overdue loans
    today = datetime.utcnow().date()
    overdue_loans_query = Loan.query.filter(
        Loan.status == 'active',
        Loan.first_installment_date < today,
        Loan.outstanding_amount > 0
    )
    if should_filter and current_branch_id:
        overdue_loans_query = overdue_loans_query.filter_by(branch_id=current_branch_id)
    overdue_loans = overdue_loans_query.order_by(Loan.first_installment_date).limit(10).all()
    
    # Due pawnings
    due_soon_pawnings = Pawning.query.filter(
        Pawning.status.in_(['active', 'extended']),
        Pawning.maturity_date <= today + timedelta(days=30)
    ).order_by(Pawning.maturity_date).limit(10).all()
    
    return render_template('main/dashboard.html',
                         title='Dashboard',
                         stats=stats,
                         recent_loans=recent_loans,
                         recent_customers=recent_customers,
                         overdue_loans=overdue_loans,
                         due_soon_pawnings=due_soon_pawnings,
                         current_branch=get_current_branch())

@main_bp.route('/index')
def index():
    """Redirect to dashboard or login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))
