"""Application factory and initialization"""
import os
import sys
import hashlib

# Python 3.8 on some OpenSSL builds rejects the 'usedforsecurity' kwarg
# that reportlab passes to hashlib.md5(). Patch it out before reportlab loads.
if sys.version_info < (3, 9):
    _orig_md5 = hashlib.md5
    def _md5_compat(*args, **kwargs):
        kwargs.pop('usedforsecurity', None)
        return _orig_md5(*args, **kwargs)
    hashlib.md5 = _md5_compat

from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_name='default'):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Create upload folders if they don't exist
    upload_folder = app.config.get('UPLOAD_FOLDER')
    if upload_folder:
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'customers'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'loans'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'borrower'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'pawnings'), exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Route to serve uploaded files with security (fallback for /uploads/ URLs)
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        from flask_login import login_required, current_user
        from flask import abort
        
        # Ensure user is logged in
        if not current_user.is_authenticated:
            abort(404)
        
        # Strip leading 'uploads/' if present (handles old DB records with double prefix)
        if filename.startswith('uploads/'):
            filename = filename[len('uploads/'):]
        
        # Add basic security check for customer files
        if filename.startswith('customers/'):
            # User should have permission to view customers
            if not current_user.has_permission('edit_customers'):
                abort(403)
        
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    from app.auth import auth_bp
    from app.main import main_bp
    from app.customers import customers_bp
    from app.loans import loans_bp
    from app.investments import investments_bp
    from app.pawnings import pawnings_bp
    from app.reports import reports_bp
    from app.settings import settings_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(loans_bp, url_prefix='/loans')
    app.register_blueprint(investments_bp, url_prefix='/borrower')
    app.register_blueprint(pawnings_bp, url_prefix='/pawnings')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    
    # Jinja2 global helper: build the correct /static/uploads/... URL for any
    # stored upload path, regardless of whether it has an "uploads/" prefix or not.
    @app.template_global()
    def upload_url(path):
        """Return the full URL path for an uploaded file.
        Handles both old DB records (uploads/customers/1/file.jpg)
        and new DB records (customers/1/file.jpg)."""
        if not path:
            return ''
        # Strip leading 'uploads/' if present so we never get double uploads
        if path.startswith('uploads/'):
            path = path[len('uploads/'):]
        return f'/static/uploads/{path}'

    # Context processor for global variables
    @app.context_processor
    def inject_settings():
        from app.models import SystemSettings, Branch
        from app.utils.helpers import get_current_branch
        from flask_login import current_user
        from flask_wtf.csrf import generate_csrf
        from datetime import datetime
        settings = SystemSettings.get_settings()
        current_branch = get_current_branch()
        
        # Get active branches for admin and regional manager users
        branches = []
        if current_user.is_authenticated and current_user.role in ['admin', 'regional_manager']:
            branches = Branch.query.filter_by(is_active=True).order_by(Branch.name).all()
        
        return dict(
            system_settings=settings, 
            now=datetime.now, 
            today=datetime.now().date(), 
            current_branch=current_branch,
            branches=branches,
            csrf_token=generate_csrf
        )
    
    return app
