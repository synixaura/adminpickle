"""
Script to wipe all sample/mock data from development/local database tables.
"""
import os
import sys
from backend.app import create_app
from backend.models.mock_db import (
    sqla, User, ConfirmedBooking, OpenPlaySession,
    SessionParticipant, PlayerRating, EventPost, AuditLog, PlatformSetting
)

def is_production_database(db_url: str) -> bool:
    if not db_url:
        return False
    lower = db_url.lower()
    if any(k in lower for k in ('supabase', 'neon.tech', 'rds.amazonaws.com', 'aws.')):
        return True
    if any(k in lower for k in ('localhost', '127.0.0.1', 'sqlite', 'test')):
        return False
    return True

def clear_mock_data():
    if os.environ.get('CONFIRM_WIPE') != 'yes':
        print("[ABORTED] Refusing to clear data: CONFIRM_WIPE=yes environment variable is required.")
        sys.exit(1)

    db_url = os.environ.get('DATABASE_URL', '')
    if is_production_database(db_url):
        print("[ABORTED] Refusing to clear data: DATABASE_URL points to a production database.")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        print("[*] Clearing all sample/mock data from database tables...")
        
        SessionParticipant.query.delete()
        PlayerRating.query.delete()
        OpenPlaySession.query.delete()
        ConfirmedBooking.query.delete()
        EventPost.query.delete()
        User.query.delete()
        AuditLog.query.delete()
        
        sqla.session.commit()
        print("[✓] All sample/mock players, bookings, sessions, and events have been cleared!")

if __name__ == '__main__':
    clear_mock_data()
