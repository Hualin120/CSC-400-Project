from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from forms import LoginForm, RegisterForm, TransactionForm
from models import db, User, Transaction
from dotenv import load_dotenv
from sqlalchemy import or_


load_dotenv(override=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

print("Connected to:", app.config["SQLALCHEMY_DATABASE_URI"])

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
def index():
    return render_template('index.html')


# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        username = form.username.data.strip()

        # Prevent duplicate email
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html', form=form)

        # Prevent duplicate username
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('register.html', form=form)

        # Hash password
        hashed = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256'
        )

        # Store hash in password column
        user = User(
            username=username,
            email=email,
            password=hashed
        )

        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        identifier = form.identifier.data.strip()
        password = form.password.data

        # To check users username or email is correct. So use can login with username or email
        user = User.query.filter(or_(User.email == identifier.lower(), User.username == identifier)).first()

        # Check hashed password stored in password column
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))

        flash('Login failed. Check your email and password.', 'danger')

    return render_template('login.html', form=form)

# LOGOUT
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# DASHBOARD
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# -------------------
# OTHER ROUTES
# -------------------
# expenses and incomes
@app.route("/transactions", methods=['GET'])
@login_required
def transactions():
    filter_type = request.args.get('filter', 'all')
    
    query = Transaction.query.filter_by(user_id=current_user.id)

    if filter_type == 'income':
        query = query.filter_by(type='income')

    elif filter_type == 'expense':
        query = query.filter_by(type='expense')
    
    transactions = query.order_by(Transaction.date.desc()).all()

    form = TransactionForm()
    
    return render_template('transactions.html', transactions=transactions, current_filter=filter_type, form=form)


@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    
    if form.validate_on_submit():
        transaction = Transaction(
            type=form.type.data,
            description=form.description.data,
            category=form.category.data,
            amount=form.amount.data,
            user_id=current_user.id
        )
        db.session.add(transaction)
        db.session.commit()
        flash('Transaction added successfully!', 'success')

    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('transactions'))



@app.route('/delete_transaction/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    transaction = Transaction.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted.', 'success')
    return redirect(url_for('transactions'))



@app.route("/budgets")
@login_required
def budgets_list():
    pass

@app.route("/analytics")
@login_required
def analytics():
    pass

@app.route("/settings")
@login_required
def settings():
    pass

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
