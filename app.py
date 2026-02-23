from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
load_dotenv(override=True)
print("MAILJET_API_KEY loaded?", bool(os.getenv("MAILJET_API_KEY")))
print("MAILJET_API_SECRET loaded?", bool(os.getenv("MAILJET_API_SECRET")))
from sqlalchemy import or_
from datetime import datetime, timedelta

from forms import LoginForm, RegisterForm, VerifyEmailForm, ForgotPasswordForm, ResetPasswordForm
from models import db, User, EmailToken, sha256
from email_utils import send_email


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
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
# REGISTER (send OTP)
# -------------------
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
        hashed = generate_password_hash(form.password.data, method='pbkdf2:sha256')

        # Store hash in password column
        user = User(username=username, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()

        # Create verification OTP (6 digits) and email it
        code = EmailToken.new_otp()
        tok = EmailToken(
            user_id=user.id,
            purpose="verify",
            token_hash=sha256(code),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            used=False
        )
        db.session.add(tok)
        db.session.commit()

        html = f"""
        <p>Welcome to <b>SpendSense</b>!</p>
        <p>Your verification code is:</p>
        <h2 style="letter-spacing:2px;">{code}</h2>
        <p>This code expires in 10 minutes.</p>
        """

        try:
            send_email(user.email, "Verify your SpendSense account", html, to_name=user.username)
        except Exception as e:
            # If email fails, user still exists; you can let them resend code later
            print("Mailjet send failed:", e)
            flash("Account created, but we couldn't send the verification email. Try resending the code.", "warning")

        # Optional: log them in so they can access /verify-email immediately
        login_user(user)

        flash("Account created! Check your email for a verification code.", "success")
        return redirect(url_for('verify_email'))

    return render_template('register.html', form=form)


# -------------------
# VERIFY EMAIL (OTP)
# -------------------
@app.route('/verify-email', methods=['GET', 'POST'])
@login_required
def verify_email():
    # Already verified? Send to dashboard
    if getattr(current_user, "is_email_verified", False):
        return redirect(url_for("dashboard"))

    form = VerifyEmailForm()

    if form.validate_on_submit():
        code = form.code.data.strip()

        # get the newest active verify token
        tok = (EmailToken.query
               .filter_by(user_id=current_user.id, purpose="verify", used=False)
               .order_by(EmailToken.created_at.desc())
               .first())

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

    code = EmailToken.new_otp()
    tok = EmailToken(
        user_id=current_user.id,
        purpose="verify",
        token_hash=sha256(code),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        used=False
    )
    db.session.add(tok)
    db.session.commit()

    html = f"""
    <p>Your new SpendSense verification code is:</p>
    <h2 style="letter-spacing:2px;">{code}</h2>
    <p>This code expires in 10 minutes.</p>
    """

    try:
        send_email(current_user.email, "Your new SpendSense verification code", html, to_name=current_user.username)
        flash("New code sent! Check your email.", "info")
    except Exception as e:
        print("Mailjet send failed:", e)
        flash("Could not send email right now. Please try again.", "danger")

    return redirect(url_for("verify_email"))


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
            flash('Login successful!', 'success')

            # If you want to force verification before using app:
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
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# -------------------
# DASHBOARD
# -------------------
@app.route('/dashboard')
@login_required
def dashboard():
    # Optional: enforce verification
    if not getattr(current_user, "is_email_verified", False):
        return redirect(url_for("verify_email"))

    return render_template('dashboard.html')


# -------------------
# FORGOT PASSWORD (send link)
# -------------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        # Always show same response (prevents email enumeration)
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

            html = f"""
            <p>Click the link below to reset your SpendSense password (expires in 30 minutes):</p>
            <p><a href="{link}">{link}</a></p>
            """

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


# -------------------
# OTHER ROUTES (placeholders)
# -------------------
@app.route("/transactions")
@login_required
def transactions_list():
    return "Transactions page placeholder"

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