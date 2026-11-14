import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    IS_PRODUCTION = bool(os.environ.get('VERCEL') or os.environ.get('FLASK_ENV') == 'production')
    DEBUG = not IS_PRODUCTION and (os.environ.get('DEBUG', 'True').lower() in ('true', '1'))

    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required and must not be empty.")

    # Base URL for OAuth callbacks and server links (e.g. https://admin.picklelegends.ph)
    ADMIN_BASE_URL = os.environ.get('ADMIN_BASE_URL', '').rstrip('/')

    # Database connection with driver resilience and SSL enforcement for remote PostgreSQL
    raw_db_url = os.environ.get('DATABASE_URL')
    if raw_db_url:
        raw_db_url = raw_db_url.strip()
        if raw_db_url.startswith('postgres://'):
            raw_db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)

    # Dynamic driver selection to support both psycopg (v3) and psycopg2 across environments
    if raw_db_url and raw_db_url.startswith("postgresql://") and not raw_db_url.startswith("postgresql+"):
        try:
            import psycopg  # type: ignore # noqa: F401
            raw_db_url = raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        except ImportError:
            try:
                import psycopg2  # type: ignore # noqa: F401
                raw_db_url = raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            except ImportError:
                pass
    elif not raw_db_url:
        # Safe fallback: /tmp on Vercel read-only filesystem
        instance_dir = "/tmp" if os.environ.get("VERCEL") else os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        raw_db_url = f"sqlite:///{os.path.join(instance_dir, 'adminpickle.db')}"

    if 'postgresql' in raw_db_url and 'sslmode' not in raw_db_url:
        separator = '&' if '?' in raw_db_url else '?'
        raw_db_url = f"{raw_db_url}{separator}sslmode=require"
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security & Session Hardening
    PERMANENT_SESSION_LIFETIME = 3600   # 60 minutes idle timeout
    SESSION_COOKIE_HTTPONLY = True      # Protect against XSS cookie theft
    SESSION_COOKIE_SECURE = IS_PRODUCTION  # Enforce HTTPS transmission in production
    SESSION_COOKIE_SAMESITE = 'Lax'     # Protect against CSRF
    
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = IS_PRODUCTION
    REMEMBER_COOKIE_SAMESITE = 'Lax'

    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    # Allowed Admin Google Emails (comma-separated list, lowercased & stripped)
    ALLOWED_ADMIN_EMAILS = [
        e.strip().lower()
        for e in os.environ.get('ALLOWED_ADMIN_EMAILS', '').split(',')
        if e.strip()
    ]

    # Supabase Storage Configuration (for permanent cloud photo uploads)
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '').strip()
    SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'avatars').strip()
