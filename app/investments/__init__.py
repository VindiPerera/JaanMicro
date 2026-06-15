"""Borrowers blueprint"""
from flask import Blueprint, redirect, url_for, flash, current_app

investments_bp = Blueprint('investments', __name__)

@investments_bp.before_request
def check_borrowing_enabled():
    if not current_app.config.get('BORROWING_ENABLED', False):
        flash('The borrowings module is currently disabled.', 'warning')
        return redirect(url_for('main.dashboard'))

from app.investments import routes
