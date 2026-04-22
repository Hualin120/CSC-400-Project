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
from models import db, User, AccountBook, UserProfile
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


'''
When user click login with google, it will trigger this Blueprint route. Given information from def get_google_oauth(),
then create nonce.

nonce just like hash password. It's an important security mechanisms. For example, when you go to amusement park,
the staff will give you a random code(maybe?) when you buy the ticket. When you play any rides, they will ask the code, without it
you cannot play it.

If someone steal your ticket, but don't have the code, they can't impersonate you.
'''
@auth_bp.route('/login/google')
def login_google():
    try:
        google = get_google_oauth()
        redirect_uri = url_for('auth.authorize_google', _external=True)

        # 1. Generate a safe random string as the nonce
        nonce = secrets.token_urlsafe(16)
        # 2. Store the nonce in the session so that it can be retrieved during callbacks.
        session['google_nonce'] = nonce

        '''
        After what we did above, we jump to def authorize_google(), which is the next route in the bottom.
        Of course, this is after the user has authorized Google.
        '''
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
        '''
        Just like what we said above, we checking the 'ticket(code)'
        '''
        nonce = session.pop('google_nonce', None)
        
        # 2. When parsing user information, pass the nonce as a parameter.
        user_info = google.parse_id_token(token, nonce=nonce)

        email = user_info.get('email')

        given_name = user_info.get('given_name', '') 
        family_name = user_info.get('family_name', '') 
        full_name = user_info.get('name', '')
        
        # generate username
        name_from_google = given_name or full_name or email.split('@')[0]
        username = generate_unique_username(name_from_google)


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

            user_profile = UserProfile(
                user_id=user.id,
                first_name=given_name or None,
                last_name=family_name or None
            )
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


            flash(f"Welcome {username}! Your account has been created.", "success")

        else:

            # users might already exists, but may be missing a UserProfile
            profile = UserProfile.query.filter_by(user_id=user.id).first()
            if not profile:
                profile = UserProfile(
                    user_id=user.id,
                    first_name=given_name or None,
                    last_name=family_name or None
                )
                db.session.add(profile)
                db.session.commit()
        
        # login user
        login_user(user)
        
        # optional
        session['oauth_provider'] = 'google'
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        current_app.logger.error(f"Error during Google authorization: {str(e)}")
        flash("Google authorization failed. Please try again.", "danger")
        return redirect(url_for('login'))


'''
For this, just prevent duplicate usernames. 
If 3 users have the same username in google, we will put a number behind.
'''
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