"""
Database Initialization & Table Migration Script for AdminPickle.
Creates database tables in PostgreSQL / Supabase cleanly without mock data.
"""
import sys
import os
from sqlalchemy import text
from backend.app import create_app
from backend.models.mock_db import (
    sqla, AdminUser, User, ConfirmedBooking, OpenPlaySession,
    SessionParticipant, PlayerRating, EventPost, AuditLog, PlatformSetting
)
from werkzeug.security import generate_password_hash


def is_production_database(db_url: str) -> bool:
    if not db_url:
        return False
    lower = db_url.lower()
    if any(k in lower for k in ('supabase', 'neon.tech', 'rds.amazonaws.com', 'aws.')):
        return True
    if any(k in lower for k in ('localhost', '127.0.0.1', 'sqlite', 'test')):
        return False
    return True


def init_database(reset=False):
    if os.environ.get('CONFIRM_WIPE') != 'yes':
        print("[ABORTED] Refusing to initialize database: CONFIRM_WIPE=yes environment variable is required.")
        sys.exit(1)

    db_url = os.environ.get('DATABASE_URL', '')
    if is_production_database(db_url):
        print("[ABORTED] Refusing to initialize database: DATABASE_URL points to a production database.")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        display_uri = db_uri.split('@')[-1] if '@' in db_uri else db_uri
        print(f"[*] Connecting to database: {display_uri}")

        if reset or '--reset' in sys.argv or '--drop' in sys.argv:
            print("[!] Dropping old/previous tables...")
            sqla.session.execute(text("""
                DROP TABLE IF EXISTS players CASCADE;
                DROP TABLE IF EXISTS users CASCADE;
                DROP TABLE IF EXISTS confirmed_bookings CASCADE;
                DROP TABLE IF EXISTS open_play_sessions CASCADE;
                DROP TABLE IF EXISTS session_participants CASCADE;
                DROP TABLE IF EXISTS player_ratings CASCADE;
                DROP TABLE IF EXISTS direct_bookings CASCADE;
                DROP TABLE IF EXISTS event_posts CASCADE;
                DROP TABLE IF EXISTS moderation_reports CASCADE;
                DROP TABLE IF EXISTS audit_logs CASCADE;
                DROP TABLE IF EXISTS platform_settings CASCADE;
                DROP TABLE IF EXISTS admin_users CASCADE;
            """))
            sqla.session.commit()
            print("[+] Successfully dropped old tables.")

        print("[*] Creating all database tables...")
        sqla.create_all()
        print("[+] All database tables created successfully!")
        print("[*] Administrator accounts are provisioned exclusively through authorized Google OAuth login.")
        print("\n[✓] Database initialization complete! Clean database ready.")


if __name__ == '__main__':
    reset_flag = '--reset' in sys.argv or '--drop' in sys.argv
    init_database(reset=reset_flag)
