"""SocketIO event handlers for real-time messaging."""
from flask_socketio import join_room, leave_room
from flask_login import current_user
from app import socketio, db
from app.models import MessageRecipient


@socketio.on('connect')
def handle_connect():
    """When a user connects, join their personal room for targeted pushes."""
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')
        # Send current unread count immediately on connect
        count = MessageRecipient.query.filter_by(
            user_id=current_user.id, is_read=False, is_deleted=False
        ).count()
        socketio.emit('unread_count', {'count': count}, room=f'user_{current_user.id}')


@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(f'user_{current_user.id}')


@socketio.on('request_unread_count')
def handle_request_unread():
    """Client explicitly requests their unread count."""
    if current_user.is_authenticated:
        count = MessageRecipient.query.filter_by(
            user_id=current_user.id, is_read=False, is_deleted=False
        ).count()
        socketio.emit('unread_count', {'count': count}, room=f'user_{current_user.id}')
