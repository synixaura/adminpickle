import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from backend.app import oauth
from backend.models.mock_db import db

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('login.html')

@auth_bp.route('/login/google')
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    # Store next redirect target if provided and strictly safe (relative path, no protocol-relative //)
    next_page = request.args.get('next')
    if next_page and next_page.startswith('/') and not next_page.startswith('//'):
        session['next_url'] = next_page

    # Ensure scheme is https when running on Vercel/production or behind SSL proxy
    scheme = 'https' if (request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https' or current_app.config.get('IS_PRODUCTION')) else 'http'
    redirect_uri = url_for('auth.google_callback', _external=True, _scheme=scheme)
    return oauth.google.authorize_redirect(redirect_uri, prompt='select_account')

@auth_bp.route('/login/google/callback')
def google_callback():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    # Check for error query parameter from OAuth provider (e.g. user cancelled)
    if 'error' in request.args:
        error_desc = request.args.get('error_description') or request.args.get('error')
        logger.warning(f"Google OAuth callback received error: {error_desc}")
        flash('Google sign-in was cancelled or failed.', 'danger')
        return redirect(url_for('auth.login'))

    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        logger.error(f"Error authorizing access token: {e}")
        flash('Failed to complete Google authentication. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    # Extract user information from OpenID Connect token or userinfo endpoint
    userinfo = token.get('userinfo')
    if not userinfo:
        try:
            userinfo = oauth.google.userinfo(token=token)
        except Exception as e:
            logger.error(f"Error fetching userinfo from Google: {e}")

    if not userinfo or not userinfo.get('email'):
        flash('Unable to retrieve verified email from Google.', 'danger')
        return redirect(url_for('auth.login'))

    google_email = userinfo['email'].strip().lower()
    allowed_emails = current_app.config.get('ALLOWED_ADMIN_EMAILS', [])

    # If not found, reload .env in case it was updated while the server was running
    if google_email not in allowed_emails:
        from dotenv import load_dotenv
        import os
        load_dotenv(override=True)
        allowed_emails = [
            e.strip().lower()
            for e in os.environ.get('ALLOWED_ADMIN_EMAILS', '').split(',')
            if e.strip()
        ]
        current_app.config['ALLOWED_ADMIN_EMAILS'] = allowed_emails

    print(f"[AUTH] Google signed-in email: '{google_email}' | Allowed list: {allowed_emails}")

    # Access control: verify against allowed admin emails
    if google_email not in allowed_emails:
        logger.warning(f"Unauthorized admin login attempt by: {google_email}")
        flash('This Google account is not authorized for admin access.', 'danger')
        return redirect(url_for('auth.login'))

    # Retrieve or provision AdminUser in the database
    name = userinfo.get('name') or userinfo.get('given_name') or google_email.split('@')[0].capitalize()
    avatar_url = userinfo.get('picture')
    admin_user = db.get_or_create_admin_by_google(email=google_email, name=name, avatar_url=avatar_url)

    if not admin_user:
        flash('Failed to load or provision admin account. Please contact platform operations.', 'danger')
        return redirect(url_for('auth.login'))

    login_user(admin_user, remember=False)
    flash(f"Welcome back, {admin_user.name}!", "success")

    next_page = session.pop('next_url', None)
    if not next_page or not next_page.startswith('/') or next_page.startswith('//'):
        next_page = url_for('dashboard.index')
    return redirect(next_page)

@auth_bp.route('/logout')
def logout():
    logout_user()
    for key in list(session.keys()):
        if key not in ('_remember', '_flashes'):
            session.pop(key, None)
    flash('You have been logged out successfully.', 'info')
    response = redirect(url_for('auth.login'))
    cookie_name = current_app.config.get('REMEMBER_COOKIE_NAME', 'remember_token')
    response.delete_cookie(cookie_name)
    return response


