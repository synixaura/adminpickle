import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    IS_PRODUCTION = bool(os.environ.get('VERCEL') or os.environ.get('FLASK_ENV') == 'production')
    DEBUG = not IS_PRODUCTION and (os.environ.get('DEBUG', 'True').lower() in ('true', '1'))

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'pickle-legends-admin-super-secret-key-2026'

    # Database connection with SSL enforcement for remote PostgreSQL
    raw_db_url = os.environ.get('DATABASE_URL') or 'sqlite:///adminpickle.db'
    if raw_db_url.startswith('postgres://'):
        raw_db_url = raw_db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif raw_db_url.startswith('postgresql://'):
        raw_db_url = raw_db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    if 'postgresql' in raw_db_url and 'sslmode' not in raw_db_url:
        separator = '&' if '?' in raw_db_url else '?'
        raw_db_url = f"{raw_db_url}{separator}sslmode=require"
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security & Session Hardening
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
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
