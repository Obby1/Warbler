from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from wtforms.fields.html5 import EmailField


class MessageForm(FlaskForm):
    """Form for adding/editing messages."""

    text = TextAreaField('text', validators=[DataRequired()])


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6)])
    image_url = StringField('(Optional) Image URL')


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=6)])

class ProfileForm(FlaskForm):
    """Form for editing a user's profile. Need to make sure when
    this data is submitted, it matches the routes in app.py"""

    username = StringField("Username", validators=[DataRequired(), Length(max=20)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    image_url = StringField("Image URL")
    header_image_url = StringField("Header Image URL")
    bio = StringField("Bio", validators=[Length(max=140)])
    location = StringField("Location", validators=[Length(max=140)])
    password = PasswordField("Password", validators=[DataRequired()])