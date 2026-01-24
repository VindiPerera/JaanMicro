"""Investments blueprint"""
from flask import Blueprint

investments_bp = Blueprint('investments', __name__)

from app.investments import routes
