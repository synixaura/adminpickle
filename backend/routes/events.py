"""
Events & Announcements Blueprint
Handles creating, listing, deleting, and serving event postings (Tournaments, Open Play Days, Promos, Announcements)
both for the Admin Dashboard and player-facing client apps.
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from backend.app import limiter
from backend.models.mock_db import db

events_bp = Blueprint('events', __name__)


@events_bp.route('/events')
@login_required
def events_view():
    """Renders the admin Events & Announcements board."""
    posts = db.get_event_posts()
    return render_template(
        'events.html',
        events=posts,
        total_courts=db.total_courts
    )


@events_bp.route('/api/events/create', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def create_event():
    """Creates a new event or announcement post."""
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    event_type = data.get('event_type', 'Announcement').strip()
    date_str = data.get('date', '').strip()
    description = data.get('description', '').strip()
    image_url = data.get('image_url', '').strip()

    if not title:
        return jsonify({"success": False, "message": "Event title is required."}), 400

    author_name = getattr(current_user, 'name', 'Admin')
    new_post = db.create_event_post(
        title=title,
        event_type=event_type,
        date=date_str,
        description=description,
        image_url=image_url,
        author=author_name
    )

    return jsonify({
        "success": True,
        "event": new_post.to_dict(),
        "message": f"Successfully published {event_type}: '{title}'"
    })


@events_bp.route('/api/events/delete/<post_id>', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def delete_event(post_id):
    """Removes an event post."""
    author_name = getattr(current_user, 'name', 'Admin')
    success = db.delete_event_post(post_id, author_name)
    if success:
        return jsonify({"success": True, "message": "Event post deleted successfully."})
    return jsonify({"success": False, "message": "Event post not found."}), 404


@events_bp.route('/api/events', methods=['GET'])
def get_public_events():
    """
    Public JSON API for Player-facing mobile/web apps.
    Returns active event postings and current venue court count.
    """
    posts = [p.to_dict() for p in db.get_event_posts()]
    return jsonify({
        "success": True,
        "venue_name": "Current Paddle Club",
        "total_courts": db.total_courts,
        "events": posts
    })
