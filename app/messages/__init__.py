"""Messages blueprint"""
from flask import Blueprint

messages_bp = Blueprint('messages', __name__)

from app.messages import routes
