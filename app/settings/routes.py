"""Settings routes"""
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
import os
from app import db
from app.settings import settings_bp
from app.models import SystemSettings, User, ActivityLog
from app.settings.forms import SystemSettingsForm, UserForm, UserEditForm
from app.utils.decorators import admin_required, permission_required
from app.utils.helpers import allowed_file

@settings_bp.route('/')
@login_required
@permission_required('manage_settings')
def index():
    """Settings dashboard"""
    settings = SystemSettings.get_settings()
    return render_template('settings/index.html', title='Settings', settings=settings)

@settings_bp.route('/system', methods=['GET', 'POST'])
@login_required
@permission_required('manage_settings')
def system_settings():
    """System settings"""
    settings = SystemSettings.get_settings()
    form = SystemSettingsForm(obj=settings)
    
    if form.validate_on_submit():
        settings.app_name = form.app_name.data
        settings.theme_color = form.theme_color.data
        settings.currency = form.currency.data
        settings.currency_symbol = form.currency_symbol.data
        settings.company_name = form.company_name.data
        settings.company_address = form.company_address.data
        settings.company_phone = form.company_phone.data
        settings.company_email = form.company_email.data
        settings.company_registration = form.company_registration.data
        
        # Loan settings
        settings.default_loan_interest_rate = form.default_loan_interest_rate.data
        settings.default_loan_duration = form.default_loan_duration.data
        settings.interest_calculation_method = form.interest_calculation_method.data
        settings.late_payment_penalty_percentage = form.late_payment_penalty_percentage.data
        settings.grace_period_days = form.grace_period_days.data
        
        # Investment settings
        settings.default_investment_interest_rate = form.default_investment_interest_rate.data
        settings.minimum_investment_amount = form.minimum_investment_amount.data
        
        # Pawning settings
        settings.default_pawning_interest_rate = form.default_pawning_interest_rate.data
        settings.default_pawning_duration = form.default_pawning_duration.data
        settings.maximum_loan_to_value_ratio = form.maximum_loan_to_value_ratio.data
        
        # Auto-numbering
        settings.loan_number_prefix = form.loan_number_prefix.data
        settings.investment_number_prefix = form.investment_number_prefix.data
        settings.pawning_number_prefix = form.pawning_number_prefix.data
        settings.customer_id_prefix = form.customer_id_prefix.data
        
        # Handle logo upload
        if form.logo.data:
            file = form.logo.data
            if allowed_file(file.filename):
                upload_folder = current_app.config['UPLOAD_FOLDER']
                branding_folder = os.path.join(upload_folder, 'branding')
                os.makedirs(branding_folder, exist_ok=True)
                
                filename = secure_filename('logo.png')
                filepath = os.path.join(branding_folder, filename)
                file.save(filepath)
                settings.logo_path = 'uploads/branding/logo.png'
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='update_system_settings',
            description='Updated system settings',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash('System settings updated successfully!', 'success')
        return redirect(url_for('settings.system_settings'))
    
    return render_template('settings/system.html',
                         title='System Settings',
                         form=form,
                         settings=settings)

@settings_bp.route('/users')
@login_required
@admin_required
def list_users():
    """List all users"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('settings/users.html', title='Users', users=users)

@settings_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """Add new user"""
    form = UserForm()
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            phone=form.phone.data,
            role=form.role.data,
            is_active=form.is_active.data,
            can_add_customers=form.can_add_customers.data,
            can_edit_customers=form.can_edit_customers.data,
            can_delete_customers=form.can_delete_customers.data,
            can_manage_loans=form.can_manage_loans.data,
            can_approve_loans=form.can_approve_loans.data,
            can_manage_investments=form.can_manage_investments.data,
            can_manage_pawnings=form.can_manage_pawnings.data,
            can_view_reports=form.can_view_reports.data,
            can_manage_settings=form.can_manage_settings.data,
            can_collect_payments=form.can_collect_payments.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='create_user',
            entity_type='user',
            description=f'Created user: {user.username} with role: {user.role}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'User {user.username} created successfully with {user.role} permissions!', 'success')
        return redirect(url_for('settings.list_users'))
    
    return render_template('settings/add_user.html', title='Add User', form=form)

@settings_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    """Edit user"""
    user = User.query.get_or_404(id)
    form = UserEditForm(obj=user)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.full_name = form.full_name.data
        user.phone = form.phone.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        user.can_add_customers = form.can_add_customers.data
        user.can_edit_customers = form.can_edit_customers.data
        user.can_delete_customers = form.can_delete_customers.data
        user.can_manage_loans = form.can_manage_loans.data
        user.can_approve_loans = form.can_approve_loans.data
        user.can_manage_investments = form.can_manage_investments.data
        user.can_manage_pawnings = form.can_manage_pawnings.data
        user.can_view_reports = form.can_view_reports.data
        user.can_manage_settings = form.can_manage_settings.data
        user.can_collect_payments = form.can_collect_payments.data
        
        if form.password.data:
            user.set_password(form.password.data)
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='update_user',
            entity_type='user',
            entity_id=user.id,
            description=f'Updated user: {user.username}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash('User updated successfully!', 'success')
        return redirect(url_for('settings.list_users'))
    
    return render_template('settings/edit_user.html',
                         title=f'Edit User: {user.username}',
                         form=form,
                         user=user)

@settings_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    """Delete user"""
    user = User.query.get_or_404(id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('settings.list_users'))
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        action='delete_user',
        entity_type='user',
        entity_id=user.id,
        description=f'Deleted user: {user.username}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('settings.list_users'))

@settings_bp.route('/api/role-permissions/<role>')
@login_required
@admin_required
def get_role_permissions(role):
    """API endpoint to get default permissions for a role"""
    permissions = UserForm.get_role_permissions(role)
    return jsonify(permissions)

@settings_bp.route('/users/bulk-update-permissions', methods=['POST'])
@login_required
@admin_required
def bulk_update_permissions():
    """Update permissions for all users based on their roles"""
    try:
        updated_count = 0
        users = User.query.all()
        
        for user in users:
            if user.role in ['staff', 'loan_collector', 'accountant', 'manager', 'admin']:
                user.set_role_permissions()
                updated_count += 1
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='bulk_update_permissions',
            description=f'Bulk updated permissions for {updated_count} users based on their roles',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Successfully updated permissions for {updated_count} users based on their roles!', 'success')
        return jsonify({'success': True, 'updated_count': updated_count})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
