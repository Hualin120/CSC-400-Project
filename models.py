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

    # NEW: email verification status
    is_email_verified = db.Column(db.Boolean, nullable=False, default=False)

    role = db.Column(db.Enum('user', 'admin', name='user_role'), nullable=False, default='user')
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum('income', 'expense', name='transaction_type'), nullable=False)
    description = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False) 
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)


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