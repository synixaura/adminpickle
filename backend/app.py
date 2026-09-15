import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from backend.config import Config
from backend.models.mock_db import db, sqla

oauth = OAuth()

def create_app():
    # Resolve absolute paths for frontend templates & static assets
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.abspath(os.path.join(base_dir, '../frontend/templates'))
    static_dir = os.path.abspath(os.path.join(base_dir, '../frontend/static'))

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(Config)

    # Initialize Database Connection
    sqla.init_app(app)

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
