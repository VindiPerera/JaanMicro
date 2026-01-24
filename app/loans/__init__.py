"""Loans blueprint"""
from flask import Blueprint

loans_bp = Blueprint('loans', __name__)

from app.loans import routes
