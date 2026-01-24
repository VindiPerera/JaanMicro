"""Main routes"""
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app.main import main_bp
from app.models import Customer, Loan, Investment, Pawning, User
from app import db
from sqlalchemy import func
from datetime import datetime, timedelta

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    # Get statistics based on user role
    stats = {
        'total_customers': Customer.query.filter_by(status='active').count(),
        'total_users': User.query.filter_by(is_active=True).count(),
        'kyc_pending': Customer.query.filter_by(kyc_verified=False, status='active').count(),
    }
    
    # Loan statistics
    active_loans = Loan.query.filter_by(status='active').all()
    stats['active_loans'] = len(active_loans)
    stats['total_loan_outstanding'] = sum(float(loan.outstanding_amount or 0) for loan in active_loans)
    stats['total_loan_disbursed'] = db.session.query(func.sum(Loan.disbursed_amount)).filter(
        Loan.status.in_(['active', 'completed'])
    ).scalar() or 0
    
    # Investment statistics
    active_investments = Investment.query.filter_by(status='active').all()
    stats['active_investments'] = len(active_investments)
    stats['total_investment_amount'] = sum(inv.current_amount or 0 for inv in active_investments)
    
    # Pawning statistics
    active_pawnings = Pawning.query.filter_by(status='active').all()
    stats['active_pawnings'] = len(active_pawnings)
    stats['total_pawning_outstanding'] = sum(pawn.outstanding_principal or 0 for pawn in active_pawnings)
    
    # Recent activities
    recent_loans = Loan.query.order_by(Loan.created_at.desc()).limit(5).all()
    recent_customers = Customer.query.order_by(Customer.created_at.desc()).limit(5).all()
    
    # Overdue loans
    today = datetime.utcnow().date()
    overdue_loans = Loan.query.filter(
        Loan.status == 'active',
        Loan.first_installment_date < today,
        Loan.outstanding_amount > 0
    ).order_by(Loan.first_installment_date).limit(10).all()
    
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
                         due_soon_pawnings=due_soon_pawnings)

@main_bp.route('/index')
def index():
    """Redirect to dashboard or login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))
