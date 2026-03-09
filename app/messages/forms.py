"""Message forms"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length


class ComposeMessageForm(FlaskForm):
    """Compose a new message"""
    to_recipients = SelectMultipleField('To', coerce=int, validators=[DataRequired(message='Select at least one recipient')])
    cc_recipients = SelectMultipleField('Cc', coerce=int, validators=[])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=255)])
    body = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send Message')


class ReplyMessageForm(FlaskForm):
    """Reply to a message"""
    body = TextAreaField('Reply', validators=[DataRequired()])
    submit = SubmitField('Send Reply')
