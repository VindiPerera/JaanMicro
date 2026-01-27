"""Application factory and initialization"""
import os
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
        os.makedirs(os.path.join(upload_folder, 'investments'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'pawnings'), exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Route to serve uploaded files with security
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        from flask_login import login_required, current_user
        from flask import abort
        
        # Ensure user is logged in
        if not current_user.is_authenticated:
            abort(404)
        
        # Add basic security check for customer files
        if filename.startswith('customers/'):
            # User should have permission to view customers
            if not current_user.has_permission('view_customers'):
                abort(403)
        
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    # Register blueprints
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
    app.register_blueprint(investments_bp, url_prefix='/investments')
    app.register_blueprint(pawnings_bp, url_prefix='/pawnings')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    
    # Context processor for global variables
    @app.context_processor
    def inject_settings():
        from app.models import SystemSettings, Branch
        from app.utils.helpers import get_current_branch
        from flask_login import current_user
        from datetime import datetime
        settings = SystemSettings.get_settings()
        current_branch = get_current_branch()
        
        # Get active branches for admin users
        branches = []
        if current_user.is_authenticated and current_user.role == 'admin':
            branches = Branch.query.filter_by(is_active=True).order_by(Branch.name).all()
        
        return dict(
            system_settings=settings, 
            now=datetime.now, 
            today=datetime.now().date(), 
            current_branch=current_branch,
            branches=branches
        )
    
    return app
