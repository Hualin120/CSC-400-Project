from flask import Flask, render_template, redirect, url_for, flash, request, session, make_response, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from sqlalchemy import or_
import calendar
import re
from datetime import datetime, timedelta, date, time

from forms import (
    LoginForm, RegisterForm, VerifyEmailForm, ForgotPasswordForm,
    ResetPasswordForm, TransactionForm, BudgetForm
)

from models import db, User, EmailToken, sha256, AccountBook, Income, Expense, UserProfile, Budget
from utils.email_utils import send_email
from utils.auth_utils import send_verification_code, can_resend_verify_code, build_reset_password_html
from routes.google_routes import auth_bp
from routes.csv_routes import csv_bp
from collections import OrderedDict
from io import BytesIO

from utils.budget_utils import (
    build_budget_progress,
    get_available_budget_years,
    get_budget_summary,
    get_overall_budget_summary,
    get_overall_budget_warnings,
    get_top_budget_warnings,
    get_user_account_books
)

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


        user_profile = UserProfile(user_id=user.id)
        db.session.add(user_profile)
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

from calendar import month_name
from collections import OrderedDict
from datetime import date
from flask_login import login_required, current_user

@app.route("/dashboard")
@login_required
def dashboard():
    current_year = date.today().year
    selected_year = request.args.get("year", str(current_year))
    selected_months = request.args.getlist("months")

    if selected_year == "all":
        selected_months = list(range(1, 13))
    elif selected_months:
        selected_months = [int(m) for m in selected_months]
    else:
        selected_months = list(range(1, 13))

    account_books = AccountBook.query.filter_by(user_id=current_user.id).all()
    account_book_ids = [b.id for b in account_books]

    all_incomes = []
    all_expenses = []

    if account_book_ids:
        all_incomes = Income.query.filter(Income.account_book_id.in_(account_book_ids)).all()
        all_expenses = Expense.query.filter(Expense.account_book_id.in_(account_book_ids)).all()

    transaction_years = [t.date.year for t in (all_incomes + all_expenses) if t.date]
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

    def matches_filter(t):
        if selected_year == "all":
            return True
        return t.date.year == selected_year_int and t.date.month in selected_months

    filtered_incomes = [i for i in all_incomes if matches_filter(i)]
    filtered_expenses = [e for e in all_expenses if matches_filter(e)]

    total_income = sum(i.amount for i in filtered_incomes)
    total_expense = sum(e.amount for e in filtered_expenses)
    net_balance = total_income - total_expense
    number_of_account_books = len(account_books)

    recent_income = sorted(filtered_incomes, key=lambda x: x.date, reverse=True)[:3]
    recent_expenses = sorted(filtered_expenses, key=lambda x: x.date, reverse=True)[:3]

    account_books_overview = []
    for book in account_books:
        book_incomes = [i for i in book.incomes if matches_filter(i)]
        book_expenses = [e for e in book.expenses if matches_filter(e)]

        book_total_income = sum(i.amount for i in book_incomes)
        book_total_expense = sum(e.amount for e in book_expenses)
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

    # All Years -> yearly chart
    if selected_year == "all":
        for year in range(earliest_year, current_year + 1):
            chart_data[str(year)] = {"income": 0, "expense": 0}

        for income in filtered_incomes:
            chart_data[str(income.date.year)]["income"] += float(income.amount)

        for expense in filtered_expenses:
            chart_data[str(expense.date.year)]["expense"] += float(expense.amount)

    # One month -> date ranges inside the month
    elif len(selected_months) == 1:
        selected_month = selected_months[0]
        month_label = month_names[selected_month]
        last_day = calendar.monthrange(selected_year_int, selected_month)[1]

        week_ranges = [(1, 7), (8, 14), (15, 21), (22, 28)]
        if last_day >= 29:
            week_ranges.append((29, last_day))

        def make_range_label(start_day, end_day):
            if start_day == end_day:
                return f"{month_label} {start_day}"
            return f"{month_label} {start_day}–{end_day}"

        for start_day, end_day in week_ranges:
            chart_data[make_range_label(start_day, end_day)] = {"income": 0, "expense": 0}

        def get_range_label(day):
            for start_day, end_day in week_ranges:
                if start_day <= day <= end_day:
                    return make_range_label(start_day, end_day)
            return None

        for income in filtered_incomes:
            label = get_range_label(income.date.day)
            if label:
                chart_data[label]["income"] += float(income.amount)

        for expense in filtered_expenses:
            label = get_range_label(expense.date.day)
            if label:
                chart_data[label]["expense"] += float(expense.amount)

    # Multiple months -> monthly chart
    else:
        for month in sorted(selected_months):
            chart_data[f"{month_names[month]} {selected_year_int}"] = {"income": 0, "expense": 0}

        for income in filtered_incomes:
            key = f"{month_names[income.date.month]} {income.date.year}"
            if key in chart_data:
                chart_data[key]["income"] += float(income.amount)

        for expense in filtered_expenses:
            key = f"{month_names[expense.date.month]} {expense.date.year}"
            if key in chart_data:
                chart_data[key]["expense"] += float(expense.amount)

    chart_labels = list(chart_data.keys())
    chart_income_data = [chart_data[label]["income"] for label in chart_labels]
    chart_expense_data = [chart_data[label]["expense"] for label in chart_labels]

    # PIE CHART DATA = CATEGORY TOTAL DOLLAR AMOUNTS
    income_category_totals = OrderedDict()
    for income in filtered_incomes:
        category = income.category or "Other"
        income_category_totals[category] = income_category_totals.get(category, 0) + float(income.amount)

    expense_category_totals = OrderedDict()
    for expense in filtered_expenses:
        category = expense.category or "Other"
        expense_category_totals[category] = expense_category_totals.get(category, 0) + float(expense.amount)

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
        chart_expense_data=chart_expense_data,
        income_category_labels=list(income_category_totals.keys()),
        income_category_data=list(income_category_totals.values()),
        expense_category_labels=list(expense_category_totals.keys()),
        expense_category_data=list(expense_category_totals.values())
    )

@app.route("/transactions", methods=["GET"])
@login_required
def transactions():
    # To check whether use got at aleast 1 account book
    account_books = AccountBook.query.filter_by(user_id=current_user.id).all()

    # if not redirect to dashborad. But since we always have a default account book General, that shouldn't trigger 
    if not account_books:
        flash('No account book found. Please contact support.', 'danger')
        return redirect(url_for('dashboard'))

    # create account book
    current_book_id = session.get('current_account_book')
    if not current_book_id or current_book_id not in [b.id for b in account_books]:
        current_book_id = account_books[0].id
        session['current_account_book'] = current_book_id

    current_book = AccountBook.query.get(current_book_id)

    current_year = date.today().year
    selected_year = request.args.get("year", str(current_year))
    selected_months = request.args.getlist("months", type=int)

    if selected_year == "all":
        selected_months = list(range(1, 13))
    else:
        selected_year = int(selected_year)

    if not selected_months:
        selected_months = list(range(1, 13))

    all_incomes = Income.query.filter_by(account_book_id=current_book_id).order_by(Income.date.desc()).all()
    all_expenses = Expense.query.filter_by(account_book_id=current_book_id).order_by(Expense.date.desc()).all()

    transaction_years = [t.date.year for t in (all_incomes + all_expenses) if t.date]
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

    def matches_filter(t):
        if selected_year == "all":
            return True
        return t.date.year == selected_year_int and t.date.month in selected_months

    filtered_incomes = [income for income in all_incomes if matches_filter(income)]
    filtered_expenses = [expense for expense in all_expenses if matches_filter(expense)]

    total_income = sum(income.amount for income in filtered_incomes)
    total_expense = sum(expense.amount for expense in filtered_expenses)
    balance = total_income - total_expense

    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }

    chart_data = OrderedDict()

    # CASE 1: All Years selected -> chart by year
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

    # CASE 2: exactly one month selected -> chart by date ranges within that month
    elif len(selected_months) == 1:
        selected_month = selected_months[0]
        month_label = month_names[selected_month]
        last_day = calendar.monthrange(selected_year_int, selected_month)[1]

        week_ranges = [
            (1, 7),
            (8, 14),
            (15, 21),
            (22, 28)
        ]

        if last_day >= 29:
            week_ranges.append((29, last_day))

        def make_range_label(start_day, end_day):
            if start_day == end_day:
                return f"{month_label} {start_day}"
            return f"{month_label} {start_day}–{end_day}"

        for start_day, end_day in week_ranges:
            label = make_range_label(start_day, end_day)
            chart_data[label] = {"income": 0, "expense": 0}

        def get_range_label(day):
            for start_day, end_day in week_ranges:
                if start_day <= day <= end_day:
                    return make_range_label(start_day, end_day)
            return None

        for income in filtered_incomes:
            if income.date.month == selected_month:
                label = get_range_label(income.date.day)
                if label:
                    chart_data[label]["income"] += float(income.amount)

        for expense in filtered_expenses:
            if expense.date.month == selected_month:
                label = get_range_label(expense.date.day)
                if label:
                    chart_data[label]["expense"] += float(expense.amount)

    # CASE 3: multiple months selected in one year -> chart by month
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

    # PIE CHART DATA = CATEGORY TOTAL DOLLAR AMOUNTS
    income_category_totals = OrderedDict()
    for income in filtered_incomes:
        category = income.category or "Other"
        income_category_totals[category] = income_category_totals.get(category, 0) + float(income.amount)

    expense_category_totals = OrderedDict()
    for expense in filtered_expenses:
        category = expense.category or "Other"
        expense_category_totals[category] = expense_category_totals.get(category, 0) + float(expense.amount)

    form = TransactionForm()

    return render_template(
        "transactions.html",
        account_books=account_books,
        current_book=current_book,
        incomes=filtered_incomes,
        expenses=filtered_expenses,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        form=form,
        today_date=date.today().strftime('%Y-%m-%d'),
        selected_year=selected_year,
        selected_months=selected_months,
        year_options=year_options,
        chart_labels=chart_labels,
        chart_income_data=chart_income_data,
        chart_expense_data=chart_expense_data,
        income_category_labels=list(income_category_totals.keys()),
        income_category_data=list(income_category_totals.values()),
        expense_category_labels=list(expense_category_totals.keys()),
        expense_category_data=list(expense_category_totals.values())
    )

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    # getting information from form
    form = TransactionForm()

    # get current account book from session
    current_book_id = session.get('current_account_book')

    # to check the account book is current account book
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

    # to check if the form is valid
    if form.validate_on_submit():
        try:
            # use users select date, if not use today's date
            transaction_date = form.date.data or date.today()

            # create corresponding records based on the transaction type
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
        
    # display specific error messages when form validation fails
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{getattr(form, field).label.text}: {error}', 'danger')

    return redirect(url_for('transactions'))

@app.route('/edit-transaction/<string:type>/<int:id>', methods=['POST'])
@login_required
def edit_transaction(type, id):
    if type == 'income':
        transaction = Income.query.get_or_404(id)
    elif type == 'expense':
        transaction = Expense.query.get_or_404(id)
    else:
        flash('Invalid transaction type.', 'danger')
        return redirect(url_for('transactions'))

    try:
        transaction.amount = float(request.form.get('amount', 0))
        transaction.category = request.form.get('category', '').strip()
        transaction.description = request.form.get('description', '').strip()
        transaction.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()

        db.session.commit()
        flash(f'{type.capitalize()} updated successfully.', 'success')
    except ValueError:
        flash('Invalid date or amount.', 'danger')

    return redirect(url_for('transactions'))

@app.route('/delete_transaction/<string:type>/<int:id>', methods=['POST'])
@login_required
def delete_transaction(type, id):
    if type == 'income':
        transaction = Income.query.get_or_404(id)
    elif type == 'expense':
        transaction = Expense.query.get_or_404(id)
    else:
        flash('Invalid transaction type.', 'danger')
        return redirect(url_for('transactions'))

    db.session.delete(transaction)
    db.session.commit()
    flash(f'{type.capitalize()} deleted successfully.', 'success')
    return redirect(url_for('transactions'))

@app.route('/create_account_book', methods=['POST'])
@login_required
def create_account_book():
    # Get the name from front end, and remove space at the front and the end
    book_name = request.form.get('book_name', '').strip()
    
    # If the name is empty, redirect to transaction.html.
    if not book_name:
        flash('Account book name cannot be empty', 'danger')
        return redirect(url_for('transactions'))
    
    # create new account book
    new_book = AccountBook(
        bookname=book_name,
        user_id=current_user.id
    )
    
    try:
        db.session.add(new_book)
        db.session.commit()
        session['current_account_book'] = new_book.id
        flash(f'Account book "{book_name}" created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while creating account book. Please try again.', 'danger')
    
    return redirect(url_for('transactions'))


@app.route('/switch_account_book/<int:book_id>')
@login_required
def switch_account_book(book_id):
    # To cheack the account book is current account book 
    book = AccountBook.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()
    session['current_account_book'] = book_id
    return redirect(url_for('transactions'))


@app.route('/delete_account_book/<int:book_id>', methods=['POST'])
@login_required
def delete_account_book(book_id):
    # To cheack the account book is current account book 
    try:
        book = AccountBook.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()

        # If the current account book is default account book, it will redirect to transaction.html
        if book.is_default:
            flash(f'Cannot delete "{book.bookname}" because it is your default account book.', 'danger')
            return redirect(url_for('transactions'))

        # query all account book information
        all_books = AccountBook.query.filter_by(user_id=current_user.id).all()

        # get current account book
        current_book_id = session.get('current_account_book')
        need_switch = (current_book_id == book_id)

        # delete account book
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



@app.route('/profile')
@login_required
def profile():
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    phone = request.form.get('phone', '').strip()

    phone_pattern = re.compile(r'^\+?\d{10,15}$')

    if phone and not phone_pattern.match(phone):
        flash("Invalid phone number format.", "danger")
        return redirect(url_for('profile'))
    return render_template('profile.html', user=current_user, profile=user_profile)

@app.route('/avatar/<int:user_id>')
def avatar(user_id):
    # query users' avater 
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    if not profile or not profile.avatar:
        # no avatar; return default image.
        return send_file('static/images/default_avatar.png', mimetype='image/png')
    
    return make_response(profile.avatar, 200, {'Content-Type': profile.avatar_mime_type})

@app.route("/budgets", methods=["GET"])
@login_required
def budgets():
    form = BudgetForm()

    account_books = get_user_account_books(current_user.id)
    selected_book_id = request.args.get("account_book_id", type=int)

    selected_book = None
    if account_books:
        if selected_book_id:
            selected_book = next((book for book in account_books if book.id == selected_book_id), None)

        if not selected_book:
            selected_book = next((book for book in account_books if book.is_default), None)

        if not selected_book:
            selected_book = account_books[0]

    if account_books:
        form.account_book_id.choices = [(book.id, book.bookname) for book in account_books]
    else:
        form.account_book_id.choices = []

    today = date.today()
    selected_month = request.args.get("month", default=today.month, type=int)
    selected_year = request.args.get("year", default=today.year, type=int)

    form.month.data = today.month
    form.year.data = today.year

    if selected_book:
        form.account_book_id.data = selected_book.id

        budget_progress = build_budget_progress(
            current_user.id,
            selected_book.id,
            selected_month,
            selected_year
        )

        summary = get_budget_summary(
            current_user.id,
            selected_book.id,
            selected_month,
            selected_year
        )
    else:
        budget_progress = []
        summary = {
            "total_budget": 0.0,
            "total_spent": 0.0,
            "total_remaining": 0.0,
            "over_budget_count": 0,
            "warning_count": 0,
            "budget_count": 0,
        }

    return render_template(
        "budgets.html",
        form=form,
        account_books=account_books,
        selected_book=selected_book,
        budgets=budget_progress,
        total_budgeted=summary["total_budget"],
        total_spent=summary["total_spent"],
        total_remaining=summary["total_remaining"],
        selected_month=selected_month,
        selected_year=selected_year,
        month_name=month_name
    )

@app.route("/budgets/add_budget", methods=["POST"])
@login_required
def add_budget():
    form = BudgetForm()
    account_books = get_user_account_books(current_user.id)
    form.account_book_id.choices = [(book.id, book.bookname) for book in account_books]

    selected_book_id = request.form.get("account_book_id", type=int)

    if form.validate_on_submit():
        selected_book = AccountBook.query.filter_by(
            id=selected_book_id,
            user_id=current_user.id
        ).first()

        if not selected_book:
            flash("Invalid account book selected.", "danger")
            return redirect(url_for("budgets"))

        existing_budget = Budget.query.filter_by(
            user_id=current_user.id,
            account_book_id=selected_book.id,
            category=form.category.data,
            month=form.month.data,
            year=form.year.data
        ).first()

        if existing_budget:
            flash("A budget for that category already exists for this month and year in this account book.", "warning")
            return redirect(
                url_for(
                    "budgets",
                    account_book_id=selected_book.id,
                    month=form.month.data,
                    year=form.year.data
                )
            )

        new_budget = Budget(
            user_id=current_user.id,
            account_book_id=selected_book.id,
            category=form.category.data,
            amount=form.amount.data,
            month=form.month.data,
            year=form.year.data
        )

        db.session.add(new_budget)
        db.session.commit()

        flash("Budget added successfully.", "success")
        return redirect(
            url_for(
                "budgets",
                account_book_id=selected_book.id,
                month=form.month.data,
                year=form.year.data
            )
        )

    flash("Please fix the form errors and try again.", "danger")
    return redirect(
        url_for(
            "budgets",
            account_book_id=selected_book_id
        )
    )

@app.route("/budgets/<int:budget_id>/edit", methods=["POST"])
@login_required
def edit_budget(budget_id):
    budget = Budget.query.filter_by(
        id=budget_id,
        user_id=current_user.id
    ).first_or_404()

    account_book_id = request.form.get("account_book_id", type=int)
    category = request.form.get("category", "").strip()
    amount = request.form.get("amount", type=float)
    month = request.form.get("month", type=int)
    year = request.form.get("year", type=int)

    selected_book = AccountBook.query.filter_by(
        id=account_book_id,
        user_id=current_user.id
    ).first()

    if not selected_book:
        flash("Invalid account book selected.", "danger")
        return redirect(url_for("budgets"))

    if not category:
        flash("Category is required.", "danger")
        return redirect(url_for("budgets", account_book_id=selected_book.id, month=budget.month, year=budget.year))

    if amount is None or amount <= 0:
        flash("Budget amount must be greater than 0.", "danger")
        return redirect(url_for("budgets", account_book_id=selected_book.id, month=budget.month, year=budget.year))

    from datetime import date
    today = date.today()

    if year < today.year or (year == today.year and month < today.month):
        flash("You cannot move a budget to a past month.", "danger")
        return redirect(url_for("budgets", account_book_id=selected_book.id, month=budget.month, year=budget.year))

    existing_budget = Budget.query.filter(
        Budget.user_id == current_user.id,
        Budget.account_book_id == selected_book.id,
        Budget.category == category,
        Budget.month == month,
        Budget.year == year,
        Budget.id != budget.id
    ).first()

    if existing_budget:
        flash("A budget for that category already exists for this month and year in this account book.", "warning")
        return redirect(url_for("budgets", account_book_id=selected_book.id, month=month, year=year))

    budget.account_book_id = selected_book.id
    budget.category = category
    budget.amount = amount
    budget.month = month
    budget.year = year

    db.session.commit()

    flash("Budget updated successfully.", "success")
    return redirect(url_for("budgets", account_book_id=selected_book.id, month=month, year=year))

@app.route("/budgets/<int:budget_id>/delete", methods=["POST"])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(
        id=budget_id,
        user_id=current_user.id
    ).first_or_404()

    selected_book_id = budget.account_book_id

    db.session.delete(budget)
    db.session.commit()

    flash("Budget deleted successfully.", "success")
    return redirect(url_for("budgets", account_book_id=selected_book_id))

@app.route('/edit_profile', methods=['POST'])
@login_required
def edit_profile():
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.session.add(profile)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # only avatar
    avatar_file = request.files.get('avatar')

    avatar_updated = False

    if avatar_file and avatar_file.filename:
        allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif']

        if avatar_file.mimetype not in allowed_types:
            if is_ajax:
                return {"success": False, "message": "Invalid file type"}
            else:
                flash('Only PNG, JPEG, JPG, GIF allowed', 'danger')
                return redirect(url_for('profile'))

        profile.avatar = avatar_file.read()
        profile.avatar_mime_type = avatar_file.mimetype
        avatar_updated = True

    # edit profile, form
    profile_updated = False

    if not is_ajax:
        profile.first_name = request.form.get('first_name', '').strip() or None
        profile.middle_name = request.form.get('middle_name', '').strip() or None
        profile.last_name = request.form.get('last_name', '').strip() or None

        profile.phone = request.form.get('phone', '').strip() or None

        profile.address = request.form.get('address', '').strip() or None
        profile.city = request.form.get('city', '').strip() or None
        profile.state = request.form.get('state', '').strip() or None
        profile.zip_code = request.form.get('zip_code', '').strip() or None
        profile.country = request.form.get('country', '').strip() or None
        

        profile_updated = True

    db.session.commit()

    # depend on the type of information to send flash message 
    if is_ajax:
        if avatar_updated:
            flash('Avatar updated successfully!', 'success')
        return {"success": True}

        
    if profile_updated:
        flash('Profile updated successfully!', 'success')


    return redirect(url_for('profile'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)