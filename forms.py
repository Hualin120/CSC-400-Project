'''
forms.py is the blueprint for how user input forms are structured and validated
throughout the web application.

For example, when a user registers, logs in, adds a transaction, or creates a
budget, this file defines the fields that appear on the form and the validation
rules that must be followed.
'''

from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SelectField, FloatField, DateField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional, Regexp, ValidationError
from datetime import date
from calendar import month_name


class RegisterForm(FlaskForm):
    # Collects the basic information needed to create a new user account.
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=30)])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=50)])

    # Password must be at least 8 characters, and the confirmation must match it.
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField('Confirm password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])

    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    # Allows the user to log in using either their username or email.
    identifier = StringField('Username or Email', validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=1, max=128)])

    submit = SubmitField('Login')


class VerifyEmailForm(FlaskForm):
    # Stores the 6-digit verification code that is emailed to the user.
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
    # Gets the user's email so a password reset link can be sent.
    email = EmailField("Email", validators=[DataRequired(), Email()])

    submit = SubmitField("Send reset link")


class ResetPasswordForm(FlaskForm):
    # Lets the user create a new password after using the reset link.
    password = PasswordField("New Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )

    submit = SubmitField("Reset Password")


# Custom validator that prevents users from entering a transaction date in the future.
def validate_transaction_date(form, field):
    if field.data and field.data > date.today():
        raise ValidationError("Transaction date cannot be in the future.")


class TransactionForm(FlaskForm):
    # The transaction type determines whether the money is income or an expense.
    type = SelectField('Transaction type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()])

    # Basic transaction details entered by the user.
    description = StringField('Description', validators=[DataRequired(), Length(max=120)])

    # Category choices are limited so transactions stay consistent for charts and summaries.
    category = SelectField('Category', choices=[
        # Income categories
        ('Salary', 'Salary'), ('Part Time', 'Part Time'), ('Freelance', 'Freelance'), ('Allowance', 'Allowance'), ('Refund', 'Refund'), ('Gift', 'Gift'),

        # Expense categories
        ('Housing', 'Housing'), ('Utilities', 'Utilities'), ('Groceries', 'Groceries'), ('Food', 'Food'), ('Transportation', 'Transportation'), ('Insurance', 'Insurance'),
        ('Subscriptions', 'Subscriptions'), ('Entertainment', 'Entertainment'), ('Shopping', 'Shopping'), ('Medical', 'Medical'), ('Travel', 'Travel'), ('Other', 'Other')
    ], validators=[DataRequired()])

    # Amount must be greater than 0 so users cannot save invalid transactions.
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])

    # Date is optional, but if selected, it cannot be a future date.
    date = DateField(
        'Transaction Date',
        validators=[Optional(), validate_transaction_date],
        default=date.today
    )

    submit = SubmitField('Add Transaction')


class BudgetForm(FlaskForm):
    # Links the budget to one of the user's account books.
    account_book_id = SelectField("Account Book", coerce=int, validators=[DataRequired()])

    # Budgets are only created for expense categories since they track spending limits.
    category = SelectField(
        'Category',
        choices=[
            ('Housing', 'Housing'), ('Utilities', 'Utilities'), ('Groceries', 'Groceries'), ('Food', 'Food'), ('Transportation', 'Transportation'), ('Insurance', 'Insurance'),
            ('Subscriptions', 'Subscriptions'), ('Entertainment', 'Entertainment'), ('Shopping', 'Shopping'), ('Medical', 'Medical'), ('Travel', 'Travel'), ('Other', 'Other')
        ],
        validators=[DataRequired()]
    )

    # Budget amount must be a positive number.
    amount = FloatField(
        "Budget Amount",
        validators=[DataRequired(), NumberRange(min=0.01, message="Budget amount must be greater than 0.")]
    )

    # Lets the user select which month the budget should apply to.
    month = SelectField(
        "Month",
        coerce=int,
        choices=[(i, month_name[i]) for i in range(1, 13)],
        validators=[DataRequired()]
    )

    # Only shows the current year and the next two years as budget options.
    current_year = date.today().year
    year = SelectField(
        "Year",
        coerce=int,
        choices=[(y, str(y)) for y in range(current_year, current_year + 3)],
        validators=[DataRequired()]
    )

    submit = SubmitField("Add Budget")

    # Prevents users from creating budgets for months or years that already passed.
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