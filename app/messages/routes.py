"""Messages routes"""
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app import socketio
from app.messages import messages_bp
from app.messages.forms import ComposeMessageForm, ReplyMessageForm
from app.models import Message, MessageRecipient, User
import bleach


def _sanitize(text):
    """Sanitize user-supplied text to prevent XSS."""
    return bleach.clean(text, tags=[], strip=True)


def _get_user_choices():
    """Return list of (id, full_name) for active users excluding current user."""
    users = User.query.filter(
        User.is_active == True,
        User.id != current_user.id
    ).order_by(User.full_name).all()
    return [(u.id, f'{u.full_name} ({u.role.title()})') for u in users]


@messages_bp.route('/')
@login_required
def inbox():
    """Inbox – messages received by current user."""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = (
        db.session.query(Message, MessageRecipient)
        .join(MessageRecipient, Message.id == MessageRecipient.message_id)
        .filter(
            MessageRecipient.user_id == current_user.id,
            MessageRecipient.is_deleted == False,
        )
        .order_by(Message.created_at.desc())
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = pagination.items  # list of (Message, MessageRecipient) tuples

    return render_template(
        'messages/inbox.html',
        title='Inbox',
        items=items,
        pagination=pagination,
    )


@messages_bp.route('/sent')
@login_required
def sent():
    """Sent messages."""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = (
        Message.query
        .filter_by(sender_id=current_user.id)
        .order_by(Message.created_at.desc())
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'messages/sent.html',
        title='Sent Messages',
        messages=pagination.items,
        pagination=pagination,
    )


@messages_bp.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
    """Compose a new message."""
    form = ComposeMessageForm()
    form.to_recipients.choices = _get_user_choices()
    form.cc_recipients.choices = _get_user_choices()

    # Pre-fill from query string (fullscreen button from popup)
    if request.method == 'GET':
        if request.args.get('subject'):
            form.subject.data = request.args.get('subject')
        if request.args.get('body'):
            form.body.data = request.args.get('body')

    if form.validate_on_submit():
        msg = Message(
            subject=_sanitize(form.subject.data),
            body=_sanitize(form.body.data),
            sender_id=current_user.id,
        )
        db.session.add(msg)
        db.session.flush()  # get msg.id

        # Add To recipients
        added_uids = set()
        for uid in form.to_recipients.data:
            db.session.add(MessageRecipient(
                message_id=msg.id, user_id=uid, recipient_type='to'))
            added_uids.add(uid)
        # Add Cc recipients
        for uid in (form.cc_recipients.data or []):
            if uid not in form.to_recipients.data:
                db.session.add(MessageRecipient(
                    message_id=msg.id, user_id=uid, recipient_type='cc'))
                added_uids.add(uid)

        db.session.commit()

        # Push real-time notification to each recipient
        for uid in added_uids:
            unread = MessageRecipient.query.filter_by(
                user_id=uid, is_read=False, is_deleted=False
            ).count()
            socketio.emit('new_message', {
                'id': msg.id,
                'subject': msg.subject,
                'sender': current_user.full_name,
                'preview': msg.body[:100],
            }, room=f'user_{uid}')
            socketio.emit('unread_count', {'count': unread}, room=f'user_{uid}')

        flash('Message sent successfully.', 'success')
        return redirect(url_for('messages.sent'))

    return render_template(
        'messages/compose.html',
        title='Compose Message',
        form=form,
    )


@messages_bp.route('/view/<int:message_id>')
@login_required
def view(message_id):
    """View a message. Auto-marks as read for recipient."""
    msg = Message.query.get_or_404(message_id)

    # Access check: sender or a recipient
    recipient_record = MessageRecipient.query.filter_by(
        message_id=message_id, user_id=current_user.id
    ).first()

    if msg.sender_id != current_user.id and not recipient_record:
        flash('You do not have permission to view this message.', 'danger')
        return redirect(url_for('messages.inbox'))

    # Mark as read
    if recipient_record and not recipient_record.is_read:
        recipient_record.is_read = True
        recipient_record.read_at = datetime.utcnow()
        db.session.commit()

        # Notify sender in real-time that their message was read
        socketio.emit('message_read', {
            'message_id': msg.id,
            'reader': current_user.full_name,
        }, room=f'user_{msg.sender_id}')

    # Collect all recipients grouped by type for display
    to_recipients = (
        MessageRecipient.query
        .filter_by(message_id=message_id, recipient_type='to')
        .all()
    )
    cc_recipients = (
        MessageRecipient.query
        .filter_by(message_id=message_id, recipient_type='cc')
        .all()
    )

    # Thread: parent + replies
    thread = []
    if msg.parent_id:
        parent = Message.query.get(msg.parent_id)
        if parent:
            thread.append(parent)
    thread.append(msg)
    replies = msg.replies.order_by(Message.created_at.asc()).all()
    thread.extend(replies)

    reply_form = ReplyMessageForm()

    return render_template(
        'messages/view.html',
        title=msg.subject,
        msg=msg,
        to_recipients=to_recipients,
        cc_recipients=cc_recipients,
        thread=thread,
        reply_form=reply_form,
        recipient_record=recipient_record,
    )


@messages_bp.route('/reply/<int:message_id>', methods=['POST'])
@login_required
def reply(message_id):
    """Reply to a message."""
    original = Message.query.get_or_404(message_id)

    # Access check
    recipient_record = MessageRecipient.query.filter_by(
        message_id=message_id, user_id=current_user.id
    ).first()
    if original.sender_id != current_user.id and not recipient_record:
        flash('You do not have permission to reply to this message.', 'danger')
        return redirect(url_for('messages.inbox'))

    form = ReplyMessageForm()
    if form.validate_on_submit():
        reply_msg = Message(
            subject=f'Re: {original.subject}',
            body=_sanitize(form.body.data),
            sender_id=current_user.id,
            parent_id=original.parent_id or original.id,
        )
        db.session.add(reply_msg)
        db.session.flush()

        # Send reply to original sender (if not self)
        reply_targets = set()
        if original.sender_id != current_user.id:
            reply_targets.add(original.sender_id)

        # Also include original To recipients (except self)
        for r in original.recipients.filter_by(recipient_type='to').all():
            if r.user_id != current_user.id:
                reply_targets.add(r.user_id)

        for uid in reply_targets:
            db.session.add(MessageRecipient(
                message_id=reply_msg.id, user_id=uid, recipient_type='to'))

        db.session.commit()

        # Push real-time notification to reply recipients
        for uid in reply_targets:
            unread = MessageRecipient.query.filter_by(
                user_id=uid, is_read=False, is_deleted=False
            ).count()
            socketio.emit('new_message', {
                'id': reply_msg.id,
                'subject': reply_msg.subject,
                'sender': current_user.full_name,
                'preview': reply_msg.body[:100],
            }, room=f'user_{uid}')
            socketio.emit('unread_count', {'count': unread}, room=f'user_{uid}')

        flash('Reply sent successfully.', 'success')
        return redirect(url_for('messages.view', message_id=original.parent_id or original.id))

    flash('Reply body is required.', 'danger')
    return redirect(url_for('messages.view', message_id=message_id))


@messages_bp.route('/delete/<int:message_id>', methods=['POST'])
@login_required
def delete(message_id):
    """Soft-delete a message from user's inbox."""
    recipient_record = MessageRecipient.query.filter_by(
        message_id=message_id, user_id=current_user.id
    ).first()
    if recipient_record:
        recipient_record.is_deleted = True
        db.session.commit()
        flash('Message deleted.', 'info')
    else:
        flash('Message not found in your inbox.', 'warning')
    return redirect(url_for('messages.inbox'))


@messages_bp.route('/star/<int:message_id>', methods=['POST'])
@login_required
def star(message_id):
    """Toggle star on a message."""
    recipient_record = MessageRecipient.query.filter_by(
        message_id=message_id, user_id=current_user.id
    ).first()
    if recipient_record:
        recipient_record.is_starred = not recipient_record.is_starred
        db.session.commit()
    return redirect(request.referrer or url_for('messages.inbox'))


@messages_bp.route('/starred')
@login_required
def starred():
    """Starred messages."""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = (
        db.session.query(Message, MessageRecipient)
        .join(MessageRecipient, Message.id == MessageRecipient.message_id)
        .filter(
            MessageRecipient.user_id == current_user.id,
            MessageRecipient.is_deleted == False,
            MessageRecipient.is_starred == True,
        )
        .order_by(Message.created_at.desc())
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'messages/inbox.html',
        title='Starred Messages',
        items=pagination.items,
        pagination=pagination,
    )


@messages_bp.route('/unread-count')
@login_required
def unread_count():
    """JSON endpoint returning unread message count (for polling)."""
    count = MessageRecipient.query.filter_by(
        user_id=current_user.id, is_read=False, is_deleted=False
    ).count()
    return jsonify({'unread': count})


@messages_bp.route('/api/users')
@login_required
def api_users():
    """JSON list of active users for the compose popup."""
    users = User.query.filter(
        User.is_active == True,
        User.id != current_user.id
    ).order_by(User.full_name).all()
    return jsonify(users=[
        {'id': u.id, 'text': f'{u.full_name} ({u.role.title()})'}
        for u in users
    ])


@messages_bp.route('/api/send', methods=['POST'])
@login_required
def api_send():
    """AJAX endpoint to send a message from the compose popup."""
    data = request.get_json()
    if not data:
        return jsonify({'ok': False, 'error': 'Invalid request'}), 400

    to_ids = data.get('to', [])
    cc_ids = data.get('cc', [])
    subject = _sanitize(data.get('subject', '').strip())
    body = _sanitize(data.get('body', '').strip())

    if not to_ids:
        return jsonify({'ok': False, 'error': 'Select at least one recipient'}), 400
    if not subject:
        return jsonify({'ok': False, 'error': 'Subject is required'}), 400
    if not body:
        return jsonify({'ok': False, 'error': 'Message body is required'}), 400

    msg = Message(
        subject=subject,
        body=body,
        sender_id=current_user.id,
    )
    db.session.add(msg)
    db.session.flush()

    added = set()
    for uid in to_ids:
        uid = int(uid)
        if uid not in added:
            db.session.add(MessageRecipient(
                message_id=msg.id, user_id=uid, recipient_type='to'))
            added.add(uid)
    for uid in cc_ids:
        uid = int(uid)
        if uid not in added:
            db.session.add(MessageRecipient(
                message_id=msg.id, user_id=uid, recipient_type='cc'))
            added.add(uid)

    db.session.commit()

    # Push real-time notification to each recipient
    for uid in added:
        unread = MessageRecipient.query.filter_by(
            user_id=uid, is_read=False, is_deleted=False
        ).count()
        socketio.emit('new_message', {
            'id': msg.id,
            'subject': msg.subject,
            'sender': current_user.full_name,
            'preview': msg.body[:100],
        }, room=f'user_{uid}')
        socketio.emit('unread_count', {'count': unread}, room=f'user_{uid}')

    return jsonify({'ok': True})


@messages_bp.route('/api/unread-count')
@login_required
def api_unread_count():
    """JSON endpoint returning unread message count for badge polling."""
    count = MessageRecipient.query.filter_by(
        user_id=current_user.id, is_read=False, is_deleted=False
    ).count()
    return jsonify({'count': count})
