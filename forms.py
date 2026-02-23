'''
forms.py is blueprint of how user input forms are structured and validated in the web application.
Like, when user wants to register or login, forms.py defines the fields and validation rules for those forms.
'''

from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=30)])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField('Comfirm password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    identifier = StringField('Username or Email',validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=1, max=128)])
    submit = SubmitField('Login')

class VerifyEmailForm(FlaskForm):
    code = StringField("Verification Code", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verify")

class ForgotPasswordForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send reset link")

class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    submit = SubmitField("Reset Password")