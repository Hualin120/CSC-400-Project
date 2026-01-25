from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
from forms import LoginForm, RegisterForm
from models import db, User
from dotenv import load_dotenv


load_dotenv(override=True)

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)



login_manager = LoginManager(app)
login_manager.login_view = 'login'



@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        
        else:
            flash('Login failed. Check your email and password.', 'danger')

    return render_template('login.html', form=form)




@app.route('/')
def index():
    return render_template('index.html')



@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')



@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
