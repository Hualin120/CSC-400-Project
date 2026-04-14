'''
models.py is blueprint of how data tables are structured in the database.
Like user table, it defines what fields are there, their types, constraints etc.
'''

import hashlib
import secrets
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

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

    # This will recor an id, so if the users change their email, for example
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
    __tablename__ = 'account_books'
    id = db.Column(db.Integer, primary_key=True)
    bookname = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='account_books')
    incomes = db.relationship('Income', backref='account_book', lazy=True, cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='account_book', lazy=True, cascade='all, delete-orphan')


class Income(db.Model):
    __tablename__ = 'incomes'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    account_book_id = db.Column(db.Integer, db.ForeignKey('account_books.id'), nullable=False)


class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    account_book_id = db.Column(db.Integer, db.ForeignKey('account_books.id'), nullable=False)


class UserProfile(db.Model):
    __tablename__ = 'user_profile'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(20), nullable=True)
    middle_name = db.Column(db.String(20), nullable=True)
    last_name = db.Column(db.String(20), nullable=True)

    address = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    zip_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    
    avatar = db.Column(db.LargeBinary)
    avatar_mime_type = db.Column(db.String(50))

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)


