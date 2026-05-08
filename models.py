'''
models.py is blueprint of how data tables are structured in the database.
Like user table, it defines what fields are there, their types, constraints etc.
'''

import secrets
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialization of SQLAlchemy instance. 
db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)

    # stores hashed password (pbkdf2:sha256 hash string)
    password = db.Column(db.String(255), nullable=False)

    # To check is OAuth user or not
    is_oauth_user = db.Column(db.Boolean, nullable=False, default=False)

    # NEW: email verification status
    is_email_verified = db.Column(db.Boolean, nullable=False, default=False)

    # This will record what third-party platform login. Google, github, etc.
    oauth_provider = db.Column(db.String(20), nullable=True)

    # This will record an id, so if the users change their email,for example,
    # hualin@gmail.com -> hualin_new@gmail.com. If users do that, there's no way we could find
    # users' account. This id will also can prevent duplication account creation
    oauth_id = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class EmailToken(db.Model):
    """
    Stores OTP codes (verification) and reset tokens (password reset).
    We store only a SHA256 hash of the code/token for safety.
    """
    __tablename__ = "email_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # "verify" or "reset"
    purpose = db.Column(db.String(20), nullable=False)

    token_hash = db.Column(db.String(64), nullable=False)  # sha256 hex digest
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @staticmethod
    def new_otp() -> str:
        # 6-digit numeric code
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def new_link_token() -> str:
        # long random token for password reset links
        return secrets.token_urlsafe(32)

class AccountBook(db.Model):
    # Stores separate financial account books for each user.
    # Example: Personal, Savings, Travel, Business, etc.
    __tablename__ = 'account_books'

    id = db.Column(db.Integer, primary_key=True)

    # Name of the account book shown to the user.
    bookname = db.Column(db.String(50), nullable=False)

    # Links the account book to a specific user.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Determines whether this is the user's default account book.
    is_default = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship connections for easier database access.
    user = db.relationship('User', backref='account_books')

    # Automatically deletes transactions if the account book is deleted.
    incomes = db.relationship('Income', backref='account_book', lazy=True, cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='account_book', lazy=True, cascade='all, delete-orphan')

class Income(db.Model):
    # Stores all income transactions entered by the user.
    __tablename__ = 'incomes'
    
    id = db.Column(db.Integer, primary_key=True)

    # Short description explaining the transaction.
    description = db.Column(db.String(120), nullable=False)

    # Income category such as Salary, Freelance, Gift, etc.
    category = db.Column(db.String(50), nullable=False)

    # Dollar amount of the transaction.
    amount = db.Column(db.Float, nullable=False)

    # Date the transaction occurred.
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Connects the transaction to a specific account book.
    account_book_id = db.Column(db.Integer, db.ForeignKey('account_books.id'), nullable=False)

class Expense(db.Model):
    # Stores all expense transactions entered by the user.
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)

    # Short description explaining the expense.
    description = db.Column(db.String(120), nullable=False)

    # Expense category such as Food, Housing, Travel, etc.
    category = db.Column(db.String(50), nullable=False)

    # Dollar amount of the expense.
    amount = db.Column(db.Float, nullable=False)

    # Date the expense occurred.
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Connects the expense to a specific account book.
    account_book_id = db.Column(db.Integer, db.ForeignKey('account_books.id'), nullable=False)

class Budget(db.Model):
    # Stores monthly spending budgets by category.
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)

    # Connects the budget to a user and account book.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    account_book_id = db.Column(db.Integer, db.ForeignKey("account_books.id"), nullable=False)

    # Expense category the budget applies to.
    category = db.Column(db.String(50), nullable=False)

    # Maximum spending amount allowed for the category.
    amount = db.Column(db.Float, nullable=False)

    # Determines what month and year the budget belongs to.
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship connections for easier access between tables.
    user = db.relationship("User", backref=db.backref("budgets", lazy=True))
    account_book = db.relationship("AccountBook", backref=db.backref("budgets", lazy=True))

    # Prevents duplicate budgets for the same category, month, year, and account book.
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "account_book_id",
            "category",
            "month",
            "year",
            name="unique_budget_per_category_book_month_year"
        ),
    )

class UserProfile(db.Model):
    # Stores optional personal profile information for users.
    __tablename__ = 'user_profile'

    id = db.Column(db.Integer, primary_key=True)

    # User name information.
    first_name = db.Column(db.String(20), nullable=True)
    middle_name = db.Column(db.String(20), nullable=True)
    last_name = db.Column(db.String(20), nullable=True)

    # User contact information.
    phone = db.Column(db.String(20), nullable=True)

    # User address information.
    address = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    zip_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    
    # Stores the uploaded profile picture and file type.
    avatar = db.Column(db.LargeBinary)
    avatar_mime_type = db.Column(db.String(50))

    # Connects the profile information to a specific user.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)



