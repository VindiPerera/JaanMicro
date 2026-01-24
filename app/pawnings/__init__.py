"""Pawnings blueprint"""
from flask import Blueprint

pawnings_bp = Blueprint('pawnings', __name__)

from app.pawnings import routes
