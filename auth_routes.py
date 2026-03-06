'''
When I doing this branch, im just still using @app.route. But when I test it (flask run), it just won't let me test it.
The reason is because app.py and auth_routhes.py, they both asking each other for information? 
Like app.py need to import auth_routes,
and auth_routes.py need to import app, mutual waiting, deadlock.

So I use Blueprint. To separate it. 
app.py is the main, and auth_routes.py is sub. It will first create app, and then create blueprint.
Just like an USB, you plug it in, and you could use it immediately. If even you don't have it, it won't affect app.py
'''
from flask import Blueprint, redirect, url_for, flash, session, current_app
from flask_login import login_user
from models import db, User
import os
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash
import secrets


auth_bp = Blueprint('auth', __name__)

oauth = OAuth()

# pip3 install Authlib requests
def get_google_oauth():
    """Get or create Google OAuth entities with proper metadata URL"""
    oauth = OAuth(current_app._get_current_object())
    GOOGLE_METADATA_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    
    return oauth.register(
        name='google',
        client_id=os.environ.get("CLIENT_ID"),
        client_secret=os.environ.get("CLIENT_SECRET"),
        server_metadata_url=GOOGLE_METADATA_URL,
        client_kwargs={'scope': 'openid profile email'},
    )


@auth_bp.route('/login/google')
def login_google():
    try:
        google = get_google_oauth()
        redirect_uri = url_for('auth.authorize_google', _external=True)

        # 1. Generate a safe random string as the nonce
        nonce = secrets.token_urlsafe(16)
        # 2. Store the nonce in the session so that it can be retrieved during callbacks.
        session['google_nonce'] = nonce

        return google.authorize_redirect(redirect_uri, nonce=nonce)
    
    except Exception as e:
        current_app.logger.error(f"Error during login: {str(e)}")
        flash("Google login failed. Please try again.", "danger")
        return redirect(url_for('login'))
    


@auth_bp.route("/authorize/google")
def authorize_google():
    try:
        google = get_google_oauth()

        # get access token
        token = google.authorize_access_token()
        
        # getting user infomation

        # 1. Retrieve the previously stored nonce from the session and delete it (it becomes invalid after one use).
        nonce = session.pop('google_nonce', None)
        
        # 2. When parsing user information, pass the nonce as a parameter.
        user_info = google.parse_id_token(token, nonce=nonce)

        email = user_info.get('email')
        
        # generate username from email，or getting more infomation from user_info
        name_from_google = user_info.get('name', '')

        if name_from_google:
            # use name from google as username
            base_username = name_from_google
        else:
            # if didn't get it, use email prefix as username
            base_username = email.split('@')[0]
        
        
        username = generate_unique_username(base_username)

        
        # check users are exist or not by email or oauth_id
        user = User.query.filter((User.email == email) | ((User.oauth_provider == 'google') & (User.oauth_id == user_info.get('sub')))).first()
        
        if not user:
            # we will make a random password for user, and they will never use it
            random_password = secrets.token_urlsafe(32)
            hashed_password = generate_password_hash(random_password, method='pbkdf2:sha256')
            
            user = User(
                username=username,
                email=email,
                password=hashed_password,
                is_oauth_user=True,
                oauth_provider='google',
                oauth_id=user_info.get('sub'),
                is_email_verified=True
            )

            db.session.add(user)
            db.session.commit()
            flash(f"Welcome {username}! Your account has been created.", "success")
        
        # login user
        login_user(user)
        
        # optional
        session['oauth_provider'] = 'google'
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        current_app.logger.error(f"Error during Google authorization: {str(e)}")
        flash("Google authorization failed. Please try again.", "danger")
        return redirect(url_for('login'))


def generate_unique_username(base_username):
    # Generate unique username
    # remove space, change into lowercase
    username = base_username.lower().replace(' ', '')
    
    # check whether the username exist or not
    if not User.query.filter_by(username=username).first():
        return username
    
    # if exist, add suffix
    counter = 1
    while True:
        new_username = f"{username}{counter}"
        if not User.query.filter_by(username=new_username).first():
            return new_username
        counter += 1