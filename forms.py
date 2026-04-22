'''
forms.py is blueprint of how user input forms are structured and validated in the web application.
Like, when user wants to register or login, forms.py defines the fields and validation rules for those forms.
'''

from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SelectField, FloatField, DateField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional, Regexp, ValidationError
from datetime import datetime, date
from calendar import month_name

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=30)])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField('Confirm password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    identifier = StringField('Username or Email',validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=1, max=128)])
    submit = SubmitField('Login')

class VerifyEmailForm(FlaskForm):
    code = StringField(
        "Verification Code",
        validators=[
            DataRequired(),
            Length(min=6, max=6),
            Regexp(r"^\d{6}$", message="Code must be exactly 6 digits.")
        ]
    )
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

# Ensures that the user cannot set a future date for any transactions.
def validate_transaction_date(form, field):
    if field.data and field.data > date.today():
        raise ValidationError("Transaction date cannot be in the future.")

class TransactionForm(FlaskForm):
    type = SelectField('Transaction type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired(), Length(max=120)])
    
    category = SelectField('Category', choices=[
        # Income category
        ('Salary', 'Salary'), ('Part Time', 'Part Time'), ('Freelance', 'Freelance'), ('Allowance', 'Allowance'), ('Refund', 'Refund'), ('Gift', 'Gift'),

        # Expense category
        ('Housing', 'Housing'), ('Utilities','Utilities'), ('Groceries', 'Groceries'), ('Food', 'Food'), ('Transportation','Transportation'), ('Insurance', 'Insurance'), 
        ('Subscriptions', 'Subscriptions'), ('Entertainment', 'Entertainment'), ('Shopping', 'Shopping'), ('Medical', 'Medical'), ('Travel', 'Travel'), ('Other', 'Other')
        ], validators=[DataRequired()])
    
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])

    date = DateField(
        'Transaction Date',
        validators=[Optional(), validate_transaction_date],
        default=date.today
    )
    submit = SubmitField('Add Transaction')

class BudgetForm(FlaskForm):
    account_book_id = SelectField("Account Book", coerce=int, validators=[DataRequired()])

    category = SelectField(
        'Category',
        choices=[
        ('Housing', 'Housing'), ('Utilities','Utilities'), ('Groceries', 'Groceries'), ('Food', 'Food'), ('Transportation','Transportation'), ('Insurance', 'Insurance'), 
        ('Subscriptions', 'Subscriptions'), ('Entertainment', 'Entertainment'), ('Shopping', 'Shopping'), ('Medical', 'Medical'), ('Travel', 'Travel'), ('Other', 'Other')
        ],
        validators=[DataRequired()]
    )

    amount = FloatField(
        "Budget Amount",
        validators=[DataRequired(), NumberRange(min=0.01, message="Budget amount must be greater than 0.")]
    )

    month = SelectField(
        "Month",
        coerce=int,
        choices=[(i, month_name[i]) for i in range(1, 13)],
        validators=[DataRequired()]
    )

    current_year = date.today().year
    year = SelectField(
        "Year",
        coerce=int,
        choices=[(y, str(y)) for y in range(current_year, current_year + 3)],
        validators=[DataRequired()]
    )

    submit = SubmitField("Add Budget")

    def validate_month(self, field):
        selected_month = self.month.data
        selected_year = self.year.data

        today = date.today()
        current_month = today.month
        current_year = today.year

        if selected_year < current_year:
            raise ValidationError("You cannot create a budget for a past year.")

        if selected_year == current_year and selected_month < current_month:
            raise ValidationError("You cannot create a budget for a past month.")