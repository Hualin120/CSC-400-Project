'''
models.py is blueprint of how data tables are structured in the database.
Like user table, it defines what fields are there, their types, constraints etc.
'''

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
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