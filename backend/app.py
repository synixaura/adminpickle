import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
from flask import Flask, render_template, session, redirect, url_for, flash, current_app, request
from flask_login import LoginManager, current_user, logout_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix
from backend.config import Config
from backend.models.mock_db import db, sqla

oauth = OAuth()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])

def create_app():
    # Resolve absolute paths for frontend templates & static assets
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.abspath(os.path.join(base_dir, '../frontend/templates'))
    static_dir = os.path.abspath(os.path.join(base_dir, '../frontend/static'))

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(Config)

    # Configure SQLAlchemy Engine options for Serverless / Supabase connection pooling
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'postgresql' in db_uri:
        if os.environ.get('VERCEL'):
            from sqlalchemy.pool import NullPool
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'poolclass': NullPool,
                'pool_pre_ping': True,
            }
        else:
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'pool_pre_ping': True,
                'pool_recycle': 300,
                'pool_size': 5,
                'max_overflow': 2,
                'pool_timeout': 15,
            }

    # Trust Vercel reverse proxy headers (ensures request.is_secure is True and https scheme is preserved)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    # Initialize Database Connection
    sqla.init_app(app)

    with app.app_context():
        try:
            sqla.create_all()
        except Exception as e:
            print("[DB INIT WARNING]:", e)

    # Configure upload folder for profile pictures and assets (read-only safe on Vercel)
    if os.environ.get('VERCEL'):
        app.config['UPLOAD_FOLDER'] = '/tmp'
    else:
        upload_dir = os.path.join(static_dir, 'uploads')
        try:
            os.makedirs(upload_dir, exist_ok=True)
        except OSError:
            pass
        app.config['UPLOAD_FOLDER'] = upload_dir
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max upload

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access the admin platform.'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.get_user_by_id(user_id)

    # Initialize OAuth for Google Sign-In
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # Initialize CSRF Protection and Rate Limiting
    csrf.init_app(app)
    limiter.init_app(app)

    @app.before_request
    def enforce_session_security():
        session.permanent = True
        if current_user.is_authenticated:
            now = time.time()
            last_active = session.get('_last_active')
            idle_timeout = 60 * 60  # 60 minutes idle timeout
            if last_active and (now - last_active > idle_timeout):
                logout_user()
                session.clear()
                flash('Your session has expired due to 60 minutes of inactivity. Please sign in again.', 'info')
                return redirect(url_for('auth.login'))
            session['_last_active'] = now

            # Re-check on each request that the logged-in email is still in ALLOWED_ADMIN_EMAILS
            allowed_emails = app.config.get('ALLOWED_ADMIN_EMAILS', [])
            user_email = getattr(current_user, 'email', None)
            if not user_email or user_email.strip().lower() not in allowed_emails:
                logout_user()
                session.clear()
                flash('Your account is no longer authorized for admin access.', 'danger')
                return redirect(url_for('auth.login'))

    # Register Blueprints
    from backend.routes.auth import auth_bp
    from backend.routes.dashboard import dashboard_bp
    from backend.routes.users import users_bp
    from backend.routes.venues import venues_bp
    from backend.routes.events import events_bp
    from backend.routes.moderation import moderation_bp
    from backend.routes.settings import settings_bp
    from backend.routes.profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(venues_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(moderation_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(profile_bp)


    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', page_title="404 Not Found"), 404

    @app.after_request
    def set_security_headers(response):
        """Inject enterprise-grade HTTP security headers on all responses."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
        if app.config.get('IS_PRODUCTION'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        return response

    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            try:
                sqla.session.rollback()
            except Exception:
                pass
        try:
            sqla.session.remove()
        except Exception:
            pass

    return app

if __name__ == '__main__':
    app = create_app()
    print("==================================================")
    print("  Pickle Legends - Admin Platform Running!")
    print("  Access URL: http://127.0.0.1:5000")
    print("==================================================")
    app.run(host='0.0.0.0', port=5000, debug=True)
