"""Authentication routes"""
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user
from urllib.parse import urlparse
from datetime import datetime
from app import db
from app.auth import auth_bp
from app.models import User, ActivityLog, Branch
from app.auth.forms import LoginForm, ChangePasswordForm

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact administrator.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.utcnow()
        
        # Set current branch in session
        if user.branch_id:
            session['current_branch_id'] = user.branch_id
            session['current_branch_name'] = user.branch.name if user.branch else 'Unknown Branch'
        else:
            # Admin user - can access all branches, default to first active branch
            default_branch = Branch.query.filter_by(is_active=True).first()
            if default_branch:
                session['current_branch_id'] = default_branch.id
                session['current_branch_name'] = default_branch.name
            else:
                session['current_branch_id'] = None
                session['current_branch_name'] = 'All Branches'
        
        # Log activity
        log = ActivityLog(
            user_id=user.id,
            action='login',
            description=f'User {user.username} logged in to branch: {session.get("current_branch_name", "Unknown")}',
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(log)
        db.session.commit()
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.dashboard')
        
        flash(f'Welcome back, {user.full_name}!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth_bp.route('/logout')
def logout():
    """User logout"""
    if current_user.is_authenticated:
        log = ActivityLog(
            user_id=current_user.id,
            action='logout',
            description=f'User {current_user.username} logged out',
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(log)
        db.session.commit()
    
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change user password"""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('auth.change_password'))
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Your password has been changed successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/change_password.html', title='Change Password', form=form)
