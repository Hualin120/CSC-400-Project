from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from sqlalchemy import or_, extract
from datetime import datetime, timedelta, date, time

from forms import (
    LoginForm, RegisterForm, VerifyEmailForm, ForgotPasswordForm,
    ResetPasswordForm, TransactionForm
)

from models import db, User, EmailToken, sha256, AccountBook, Income, Expense
from email_utils import send_email
from auth_utils import send_verification_code, can_resend_verify_code, build_reset_password_html
from auth_routes import auth_bp
from csv_routes import csv_bp
from collections import OrderedDict

load_dotenv(override=True)
print("MAILJET_API_KEY loaded?", bool(os.getenv("MAILJET_API_KEY")))
print("MAILJET_API_SECRET loaded?", bool(os.getenv("MAILJET_API_SECRET")))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# blue print
app.register_blueprint(auth_bp)
app.register_blueprint(csv_bp, url_prefix='/csv')

@app.before_request
def ensure_tables_exits():
    db.create_all()
    
login_manager = LoginManager(app)
login_manager.login_view = 'login'

print("Connected to:", app.config["SQLALCHEMY_DATABASE_URI"])


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/')
def index():
    return render_template('index.html')


# -------------------
# LOGIN
# -------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        identifier = form.identifier.data.strip()
        password = form.password.data

        user = User.query.filter(
            or_(User.email == identifier.lower(), User.username == identifier)
        ).first()

        if user and check_password_hash(user.password, password):
            login_user(user)

            if not getattr(user, "is_email_verified", False):
                return redirect(url_for("verify_email"))

            return redirect(url_for('dashboard'))

        flash('Login failed. Check your email/username and password.', 'danger')

    return render_template('login.html', form=form)


# -------------------
# LOGOUT
# -------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# -------------------
# REGISTER (send OTP)
# -------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        username = form.username.data.strip()

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html', form=form)

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('register.html', form=form)

        hashed = generate_password_hash(form.password.data, method='pbkdf2:sha256')

        user = User(username=username, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()

        default_book = AccountBook(
            bookname = 'General',
            user_id = user.id,
            is_default = True
        )

        db.session.add(default_book)
        db.session.commit()

        session['current_account_book'] = default_book.id

        send_verification_code(
            user,
            subject="Verify your SpendSense account",
        )

        login_user(user)
        flash("Account created! Check your email for a verification code.", "success")
        session["skip_verify_autosend_once"] = True
        session["verify_last_sent_at"] = datetime.utcnow().isoformat()
        return redirect(url_for('verify_email'))

    return render_template('register.html', form=form)


# -------------------
# VERIFY EMAIL (OTP)
# -------------------
@app.route('/verify-email', methods=['GET', 'POST'])
@login_required
def verify_email():
    if getattr(current_user, "is_email_verified", False):
        return redirect(url_for("dashboard"))

    form = VerifyEmailForm()

    if request.method == "GET":
        if session.pop("skip_verify_autosend_once", False):
            return render_template("verify_email.html", form=form)

        now = datetime.utcnow()
        last_sent_iso = session.get("verify_last_sent_at")
        last_sent = datetime.fromisoformat(last_sent_iso) if last_sent_iso else None

        if (not last_sent) or (now - last_sent > timedelta(seconds=60)):
            send_verification_code(
                current_user,
                subject="Verify your SpendSense account",
                flash_on_success="We sent a verification code to your email."
            )
            session["verify_last_sent_at"] = now.isoformat()

    if form.validate_on_submit():
        code = form.code.data.strip()

        tok = (
            EmailToken.query
            .filter_by(user_id=current_user.id, purpose="verify", used=False)
            .order_by(EmailToken.created_at.desc())
            .first()
        )

        if not tok:
            flash("No active verification code found. Please resend a new one.", "danger")
            return render_template("verify_email.html", form=form)

        if tok.expires_at < datetime.utcnow():
            flash("That code expired. Please resend a new one.", "danger")
            return render_template("verify_email.html", form=form)

        if tok.token_hash != sha256(code):
            flash("Invalid code. Try again.", "danger")
            return render_template("verify_email.html", form=form)

        tok.used = True
        current_user.is_email_verified = True
        db.session.commit()

        flash("Email verified!", "success")
        return redirect(url_for("dashboard"))

    return render_template("verify_email.html", form=form)


@app.route("/verify-email/resend")
@login_required
def resend_verify_email():
    if getattr(current_user, "is_email_verified", False):
        return redirect(url_for("dashboard"))

    if not can_resend_verify_code(current_user.id, max_in_window=3, window_minutes=15):
        flash("Too many resend attempts. Please wait a bit and try again.", "warning")
        session["skip_verify_autosend_once"] = True
        return redirect(url_for("verify_email"))

    send_verification_code(
        current_user,
        subject="Your new SpendSense verification code",
        flash_on_success="New code sent! Check your email."
    )

    return redirect(url_for("verify_email"))


# -------------------
# FORGOT PASSWORD (send link)
# -------------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        flash("If that email exists, a reset link was sent.", "info")

        if user:
            raw = EmailToken.new_link_token()
            tok = EmailToken(
                user_id=user.id,
                purpose="reset",
                token_hash=sha256(raw),
                expires_at=datetime.utcnow() + timedelta(minutes=30),
                used=False
            )
            db.session.add(tok)
            db.session.commit()

            base = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000")
            link = f"{base}/reset-password/{raw}"

            html = build_reset_password_html(user.username, link)

            try:
                send_email(user.email, "Reset your SpendSense password", html, to_name=user.username)
            except Exception as e:
                print("Mailjet send failed:", e)

        return redirect(url_for("login"))

    return render_template("forgot_password.html", form=form)


@app.route("/reset-password/<raw_token>", methods=["GET", "POST"])
def reset_password(raw_token):
    form = ResetPasswordForm()

    tok = EmailToken.query.filter_by(
        purpose="reset",
        token_hash=sha256(raw_token),
        used=False
    ).first()

    if not tok or tok.expires_at < datetime.utcnow():
        flash("Reset link is invalid or expired.", "danger")
        return redirect(url_for("forgot_password"))

    if form.validate_on_submit():
        user = User.query.get(tok.user_id)
        user.password = generate_password_hash(form.password.data, method="pbkdf2:sha256")
        tok.used = True
        db.session.commit()

        flash("Password updated. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", form=form)


@app.route("/dashboard")
@login_required
def dashboard():
    current_year = date.today().year
    selected_year = request.args.get("year", str(current_year))
    selected_months = request.args.getlist("months")

    if selected_year == "all":
        selected_months = list(range(1, 13))
    elif selected_months:
        selected_months = [int(month) for month in selected_months]
    else:
        selected_months = list(range(1, 13))

    account_books = AccountBook.query.filter_by(user_id=current_user.id).all()
    account_book_ids = [book.id for book in account_books]

    all_user_incomes = []
    all_user_expenses = []

    if account_book_ids:
        all_user_incomes = (
            Income.query
            .filter(Income.account_book_id.in_(account_book_ids))
            .all()
        )

        all_user_expenses = (
            Expense.query
            .filter(Expense.account_book_id.in_(account_book_ids))
            .all()
        )

    transaction_years = [
        transaction.date.year
        for transaction in (all_user_incomes + all_user_expenses)
        if transaction.date
    ]

    earliest_year = min(transaction_years) if transaction_years else current_year
    year_options = list(range(earliest_year, current_year + 1))

    if selected_year != "all":
        try:
            selected_year_int = int(selected_year)
        except ValueError:
            selected_year = str(current_year)
            selected_year_int = current_year
    else:
        selected_year_int = None

    if selected_year != "all" and (selected_year_int < earliest_year or selected_year_int > current_year):
        selected_year = str(current_year)
        selected_year_int = current_year

    filtered_incomes = []
    filtered_expenses = []

    for income in all_user_incomes:
        if selected_year == "all":
            filtered_incomes.append(income)
        elif income.date.year == selected_year_int and income.date.month in selected_months:
            filtered_incomes.append(income)

    for expense in all_user_expenses:
        if selected_year == "all":
            filtered_expenses.append(expense)
        elif expense.date.year == selected_year_int and expense.date.month in selected_months:
            filtered_expenses.append(expense)

    total_income = sum(income.amount for income in filtered_incomes)
    total_expense = sum(expense.amount for expense in filtered_expenses)
    net_balance = total_income - total_expense
    number_of_account_books = len(account_books)

    recent_income = sorted(filtered_incomes, key=lambda x: x.date, reverse=True)[:3]
    recent_expenses = sorted(filtered_expenses, key=lambda x: x.date, reverse=True)[:3]

    account_books_overview = []
    for book in account_books:
        if selected_year == "all":
            book_incomes = list(book.incomes)
            book_expenses = list(book.expenses)
        else:
            book_incomes = [
                income for income in book.incomes
                if income.date.year == selected_year_int and income.date.month in selected_months
            ]
            book_expenses = [
                expense for expense in book.expenses
                if expense.date.year == selected_year_int and expense.date.month in selected_months
            ]

        book_total_income = sum(income.amount for income in book_incomes)
        book_total_expense = sum(expense.amount for expense in book_expenses)
        book_balance = book_total_income - book_total_expense

        account_books_overview.append({
            "id": book.id,
            "bookname": book.bookname,
            "total_income": book_total_income,
            "total_expense": book_total_expense,
            "balance": book_balance
        })

    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }

    chart_data = OrderedDict()

    if selected_year == "all":
        for year in range(earliest_year, current_year + 1):
            chart_data[str(year)] = {"income": 0, "expense": 0}

        for income in filtered_incomes:
            label = str(income.date.year)
            if label in chart_data:
                chart_data[label]["income"] += float(income.amount)

        for expense in filtered_expenses:
            label = str(expense.date.year)
            if label in chart_data:
                chart_data[label]["expense"] += float(expense.amount)

    else:
        for month in sorted(selected_months):
            label = f"{month_names[month]} {selected_year_int}"
            chart_data[label] = {"income": 0, "expense": 0}

        for income in filtered_incomes:
            label = f"{month_names[income.date.month]} {income.date.year}"
            if label in chart_data:
                chart_data[label]["income"] += float(income.amount)

        for expense in filtered_expenses:
            label = f"{month_names[expense.date.month]} {expense.date.year}"
            if label in chart_data:
                chart_data[label]["expense"] += float(expense.amount)

    chart_labels = list(chart_data.keys())
    chart_income_data = [chart_data[label]["income"] for label in chart_labels]
    chart_expense_data = [chart_data[label]["expense"] for label in chart_labels]

    return render_template(
        "dashboard.html",
        total_income=total_income,
        total_expense=total_expense,
        net_balance=net_balance,
        number_of_account_books=number_of_account_books,
        recent_income=recent_income,
        recent_expenses=recent_expenses,
        account_books_overview=account_books_overview,
        selected_year=selected_year,
        selected_months=selected_months,
        year_options=year_options,
        chart_labels=chart_labels,
        chart_income_data=chart_income_data,
        chart_expense_data=chart_expense_data
    )

@app.route("/transactions", methods=["GET"])
@login_required
def transactions():
    account_books = AccountBook.query.filter_by(user_id=current_user.id).all()

    if not account_books:
        flash('Please create an account book', 'info')
        return redirect(url_for('create_account_book'))

    current_book_id = session.get('current_account_book')
    if not current_book_id or current_book_id not in [b.id for b in account_books]:
        current_book_id = account_books[0].id
        session['current_account_book'] = current_book_id

    current_book = AccountBook.query.get(current_book_id)

    all_incomes = Income.query.filter_by(account_book_id=current_book_id).order_by(Income.date.desc()).all()
    all_expenses = Expense.query.filter_by(account_book_id=current_book_id).order_by(Expense.date.desc()).all()

    current_year = date.today().year

    # Transactions page default = all years
    selected_year = request.args.get("year", "all")
    selected_months = request.args.getlist("months")

    if selected_year == "all":
        selected_months = list(range(1, 13))
    elif selected_months:
        selected_months = [int(m) for m in selected_months]
    else:
        selected_months = list(range(1, 13))

    transaction_years = [
        t.date.year for t in (all_incomes + all_expenses) if t.date
    ]
    earliest_year = min(transaction_years) if transaction_years else current_year
    year_options = list(range(earliest_year, current_year + 1))

    if selected_year != "all":
        try:
            selected_year_int = int(selected_year)
        except ValueError:
            selected_year = "all"
            selected_year_int = None
            selected_months = list(range(1, 13))
    else:
        selected_year_int = None

    filtered_incomes = [
        income for income in all_incomes
        if selected_year == "all"
        or (income.date.year == selected_year_int and income.date.month in selected_months)
    ]

    filtered_expenses = [
        expense for expense in all_expenses
        if selected_year == "all"
        or (expense.date.year == selected_year_int and expense.date.month in selected_months)
    ]

    total_income = sum(income.amount for income in filtered_incomes)
    total_expense = sum(expense.amount for expense in filtered_expenses)
    balance = total_income - total_expense

    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }

    chart_data = OrderedDict()

    if selected_year == "all":
        for year in range(earliest_year, current_year + 1):
            chart_data[str(year)] = {"income": 0, "expense": 0}

        for income in filtered_incomes:
            label = str(income.date.year)
            if label in chart_data:
                chart_data[label]["income"] += float(income.amount)

        for expense in filtered_expenses:
            label = str(expense.date.year)
            if label in chart_data:
                chart_data[label]["expense"] += float(expense.amount)

    else:
        for month in sorted(selected_months):
            label = f"{month_names[month]} {selected_year_int}"
            chart_data[label] = {"income": 0, "expense": 0}

        for income in filtered_incomes:
            label = f"{month_names[income.date.month]} {income.date.year}"
            if label in chart_data:
                chart_data[label]["income"] += float(income.amount)

        for expense in filtered_expenses:
            label = f"{month_names[expense.date.month]} {expense.date.year}"
            if label in chart_data:
                chart_data[label]["expense"] += float(expense.amount)

    chart_labels = list(chart_data.keys())
    chart_income_data = [chart_data[label]["income"] for label in chart_labels]
    chart_expense_data = [chart_data[label]["expense"] for label in chart_labels]

    form = TransactionForm()

    return render_template(
        "transactions.html",
        incomes=filtered_incomes,
        expenses=filtered_expenses,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        account_books=account_books,
        current_book=current_book,
        form=form,
        today_date=date.today().strftime('%Y-%m-%d'),
        selected_months=selected_months,
        selected_year=selected_year,
        year_options=year_options,
        chart_labels=chart_labels,
        chart_income_data=chart_income_data,
        chart_expense_data=chart_expense_data
    )


@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    form = TransactionForm()

    current_book_id = session.get('current_account_book')

    if not current_book_id:
        flash('Please select an account book first.', 'danger')
        return redirect(url_for('transactions'))

    current_book = AccountBook.query.filter_by(
        id=current_book_id,
        user_id=current_user.id
    ).first()

    if not current_book:
        flash('Invalid account book selected.', 'danger')
        return redirect(url_for('transactions'))

    if form.validate_on_submit():
        try:
            transaction_date = form.date.data or date.today()

            if form.type.data == 'income':
                transaction = Income(
                    description=form.description.data,
                    category=form.category.data,
                    amount=form.amount.data,
                    date=transaction_date,
                    account_book_id=current_book_id
                )
            else:
                transaction = Expense(
                    description=form.description.data,
                    category=form.category.data,
                    amount=form.amount.data,
                    date=transaction_date,
                    account_book_id=current_book_id
                )

            db.session.add(transaction)
            db.session.commit()
            flash('Transaction added successfully!', 'success')
            return redirect(url_for('transactions'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding transaction: {str(e)}', 'danger')
            return redirect(url_for('transactions'))

    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{getattr(form, field).label.text}: {error}', 'danger')

    return redirect(url_for('transactions'))


@app.route('/delete_transaction/<string:type>/<int:id>', methods=['POST'])
@login_required
def delete_transaction(type, id):
    try:
        if type == 'income':
            transaction = Income.query.join(AccountBook).filter(
                Income.id == id,
                AccountBook.user_id == current_user.id
            ).first_or_404()
        else:
            transaction = Expense.query.join(AccountBook).filter(
                Expense.id == id,
                AccountBook.user_id == current_user.id
            ).first_or_404()

        db.session.delete(transaction)
        db.session.commit()
        flash('Transaction deleted successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting transaction: {str(e)}', 'danger')

    return redirect(url_for('transactions'))


@app.route('/create_account_book', methods=['GET', 'POST'])
@login_required
def create_account_book():
    if request.method == 'GET':
        return render_template('create_account_book.html')

    if request.method == 'POST':
        book_name = request.form.get('book_name', '').strip()

        if not book_name:
            flash('Account book name cannot be empty', 'danger')
            return redirect(url_for('create_account_book'))

        new_book = AccountBook(
            bookname=book_name,
            user_id=current_user.id
        )

        try:
            db.session.add(new_book)
            db.session.commit()

            session['current_account_book'] = new_book.id

            flash(f'Account book "{book_name}" created successfully!', 'success')
            return redirect(url_for('transactions'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating account book. Please try again.', 'danger')
            return redirect(url_for('create_account_book'))


@app.route('/switch_account_book/<int:book_id>')
@login_required
def switch_account_book(book_id):
    book = AccountBook.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()
    session['current_account_book'] = book_id
    return redirect(url_for('transactions'))


@app.route('/delete_account_book/<int:book_id>', methods=['POST'])
@login_required
def delete_account_book(book_id):
    try:
        book = AccountBook.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()

        if book.is_default:
            flash(f'Cannot delete "{book.bookname}" because it is your default account book.', 'danger')
            return redirect(url_for('transactions'))

        all_books = AccountBook.query.filter_by(user_id=current_user.id).all()

        current_book_id = session.get('current_account_book')
        need_switch = (current_book_id == book_id)

        db.session.delete(book)
        db.session.commit()

        flash(f'Account book "{book.bookname}" has been deleted.', 'success')

        if need_switch and len(all_books) > 1:
            remaining_books = [b for b in all_books if b.id != book_id]
            if remaining_books:
                session['current_account_book'] = remaining_books[0].id

        return redirect(url_for('transactions'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting account book: {str(e)}', 'danger')
        return redirect(url_for('transactions'))


@app.route("/budgets")
@login_required
def budgets_list():
    return "Budgets page placeholder"


@app.route("/analytics")
@login_required
def analytics():
    return "Analytics page placeholder"


@app.route("/settings")
@login_required
def settings():
    return "Settings page placeholder"


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)