"""Customer management routes"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json
from app import db
from app.customers import customers_bp
from app.models import Customer, ActivityLog, SystemSettings
from app.customers.forms import CustomerForm, KYCForm
from app.utils.decorators import permission_required
from app.utils.helpers import allowed_file, generate_customer_id, get_current_branch_id, should_filter_by_branch

@customers_bp.route('/')
@login_required
@permission_required('add_customers')
def list_customers():
    """List all customers"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status = request.args.get('status', '', type=str)
    customer_type = request.args.get('customer_type', '', type=str)
    
    query = Customer.query
    
    # Filter by current branch if needed
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id:
            query = query.filter_by(branch_id=current_branch_id)
    
    if search:
        query = query.filter(
            db.or_(
                Customer.full_name.ilike(f'%{search}%'),
                Customer.customer_id.ilike(f'%{search}%'),
                Customer.nic_number.ilike(f'%{search}%'),
                Customer.phone_primary.ilike(f'%{search}%')
            )
        )
    
    if status:
        query = query.filter_by(status=status)
    
    if customer_type:
        query = query.filter_by(customer_type=customer_type)
    
    customers = query.order_by(Customer.created_at.desc()).paginate(
        page=page, per_page=current_app.config['ITEMS_PER_PAGE'], error_out=False
    )
    
    return render_template('customers/list.html',
                         title='Customers',
                         customers=customers,
                         search=search,
                         status=status,
                         customer_type=customer_type)

@customers_bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('add_customers')
def add_customer():
    """Add new customer"""
    form = CustomerForm()
    
    if form.validate_on_submit():
        settings = SystemSettings.get_settings()
        customer_id = generate_customer_id(settings.customer_id_prefix)
        
        customer = Customer(
            customer_id=customer_id,
            branch_id=get_current_branch_id(),
            full_name=form.full_name.data,
            nic_number=form.nic_number.data,
            customer_type=form.customer_type.data,
            date_of_birth=form.date_of_birth.data,
            gender=form.gender.data,
            marital_status=form.marital_status.data,
            phone_primary=form.phone_primary.data,
            phone_secondary=form.phone_secondary.data,
            email=form.email.data,
            address_line1=form.address_line1.data,
            address_line2=form.address_line2.data,
            city=form.city.data,
            district=form.district.data,
            postal_code=form.postal_code.data,
            occupation=form.occupation.data,
            employer_name=form.employer_name.data,
            monthly_income=form.monthly_income.data,
            employment_type=form.employment_type.data,
            emergency_contact_name=form.emergency_contact_name.data,
            emergency_contact_phone=form.emergency_contact_phone.data,
            emergency_contact_relation=form.emergency_contact_relation.data,
            guarantor_name=form.guarantor_name.data,
            guarantor_nic=form.guarantor_nic.data,
            guarantor_phone=form.guarantor_phone.data,
            guarantor_address=form.guarantor_address.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        db.session.add(customer)
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='create_customer',
            entity_type='customer',
            description=f'Created customer: {customer.full_name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'Customer {customer.full_name} added successfully!', 'success')
        return redirect(url_for('customers.view_customer', id=customer.id))
    
    return render_template('customers/add.html', title='Add Customer', form=form)

@customers_bp.route('/<int:id>')
@login_required
def view_customer(id):
    """View customer details"""
    customer = Customer.query.get_or_404(id)
    
    # Check if customer belongs to current branch
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and customer.branch_id != current_branch_id:
            flash('Access denied: Customer does not belong to your branch.', 'danger')
            return redirect(url_for('customers.list_customers'))
    
    # Get related records
    loans = customer.loans.order_by(db.desc('created_at')).all()
    investments = customer.investments.order_by(db.desc('created_at')).all()
    pawnings = customer.pawnings.order_by(db.desc('created_at')).all()
    
    return render_template('customers/view.html',
                         title=f'Customer: {customer.full_name}',
                         customer=customer,
                         loans=loans,
                         investments=investments,
                         pawnings=pawnings)

@customers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('edit_customers')
def edit_customer(id):
    """Edit customer details"""
    customer = Customer.query.get_or_404(id)
    
    # Check if customer belongs to current branch
    if should_filter_by_branch():
        current_branch_id = get_current_branch_id()
        if current_branch_id and customer.branch_id != current_branch_id:
            flash('Access denied: Customer does not belong to your branch.', 'danger')
            return redirect(url_for('customers.list_customers'))
    
    form = CustomerForm(obj=customer)
    
    if form.validate_on_submit():
        customer.full_name = form.full_name.data
        customer.nic_number = form.nic_number.data
        customer.customer_type = form.customer_type.data
        customer.date_of_birth = form.date_of_birth.data
        customer.gender = form.gender.data
        customer.marital_status = form.marital_status.data
        customer.phone_primary = form.phone_primary.data
        customer.phone_secondary = form.phone_secondary.data
        customer.email = form.email.data
        customer.address_line1 = form.address_line1.data
        customer.address_line2 = form.address_line2.data
        customer.city = form.city.data
        customer.district = form.district.data
        customer.postal_code = form.postal_code.data
        customer.occupation = form.occupation.data
        customer.employer_name = form.employer_name.data
        customer.monthly_income = form.monthly_income.data
        customer.employment_type = form.employment_type.data
        customer.emergency_contact_name = form.emergency_contact_name.data
        customer.emergency_contact_phone = form.emergency_contact_phone.data
        customer.emergency_contact_relation = form.emergency_contact_relation.data
        customer.guarantor_name = form.guarantor_name.data
        customer.guarantor_nic = form.guarantor_nic.data
        customer.guarantor_phone = form.guarantor_phone.data
        customer.guarantor_address = form.guarantor_address.data
        customer.notes = form.notes.data
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='update_customer',
            entity_type='customer',
            entity_id=customer.id,
            description=f'Updated customer: {customer.full_name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash('Customer information updated successfully!', 'success')
        return redirect(url_for('customers.view_customer', id=customer.id))
    
    return render_template('customers/edit.html',
                         title=f'Edit Customer: {customer.full_name}',
                         form=form,
                         customer=customer)

@customers_bp.route('/<int:id>/kyc', methods=['GET', 'POST'])
@login_required
@permission_required('edit_customers')
def customer_kyc(id):
    """Manage customer KYC"""
    customer = Customer.query.get_or_404(id)
    form = KYCForm()
    
    if form.validate_on_submit():
        # Handle file uploads
        upload_folder = current_app.config['UPLOAD_FOLDER']
        customer_folder = os.path.join(upload_folder, 'customers', str(customer.id))
        os.makedirs(customer_folder, exist_ok=True)
        
        if form.nic_front_image.data:
            file = form.nic_front_image.data
            if allowed_file(file.filename):
                filename = secure_filename(f'nic_front_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{file.filename.rsplit(".", 1)[1].lower()}')
                filepath = os.path.join(customer_folder, filename)
                file.save(filepath)
                customer.nic_front_image = f'uploads/customers/{customer.id}/{filename}'
        
        if form.nic_back_image.data:
            file = form.nic_back_image.data
            if allowed_file(file.filename):
                filename = secure_filename(f'nic_back_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{file.filename.rsplit(".", 1)[1].lower()}')
                filepath = os.path.join(customer_folder, filename)
                file.save(filepath)
                customer.nic_back_image = f'uploads/customers/{customer.id}/{filename}'
        
        if form.photo.data:
            file = form.photo.data
            if allowed_file(file.filename):
                filename = secure_filename(f'photo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{file.filename.rsplit(".", 1)[1].lower()}')
                filepath = os.path.join(customer_folder, filename)
                file.save(filepath)
                customer.photo = f'uploads/customers/{customer.id}/{filename}'
        
        if form.proof_of_address.data:
            file = form.proof_of_address.data
            if allowed_file(file.filename):
                filename = secure_filename(f'address_proof_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{file.filename.rsplit(".", 1)[1].lower()}')
                filepath = os.path.join(customer_folder, filename)
                file.save(filepath)
                customer.proof_of_address = f'uploads/customers/{customer.id}/{filename}'
        
        if form.kyc_verified.data:
            customer.kyc_verified = True
            customer.kyc_verified_by = current_user.id
            customer.kyc_verified_date = datetime.utcnow()
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='update_kyc',
            entity_type='customer',
            entity_id=customer.id,
            description=f'Updated KYC for customer: {customer.full_name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash('KYC information updated successfully!', 'success')
        return redirect(url_for('customers.view_customer', id=customer.id))
    
    return render_template('customers/kyc.html',
                         title=f'KYC: {customer.full_name}',
                         form=form,
                         customer=customer)

@customers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('delete_customers')
def delete_customer(id):
    """Delete customer"""
    customer = Customer.query.get_or_404(id)
    
    # Check if customer has active loans, investments, or pawnings
    if customer.loans.filter_by(status='active').count() > 0:
        flash('Cannot delete customer with active loans!', 'danger')
        return redirect(url_for('customers.view_customer', id=id))
    
    if customer.investments.filter_by(status='active').count() > 0:
        flash('Cannot delete customer with active investments!', 'danger')
        return redirect(url_for('customers.view_customer', id=id))
    
    if customer.pawnings.filter_by(status='active').count() > 0:
        flash('Cannot delete customer with active pawnings!', 'danger')
        return redirect(url_for('customers.view_customer', id=id))
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        action='delete_customer',
        entity_type='customer',
        entity_id=customer.id,
        description=f'Deleted customer: {customer.full_name}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    
    db.session.delete(customer)
    db.session.commit()
    
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers.list_customers'))
