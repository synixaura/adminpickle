"""
Admin Dashboard Routes
Handles dashboard stats, system log displays, and quick admin action triggers.
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from backend.app import limiter
from backend.models.mock_db import db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """Renders the main admin dashboard page with live metrics, recent events, and system audit logs."""
    return render_template(
        'dashboard.html',
        metrics=db.metrics,
        recent_events=db.get_event_posts()[:3],
        total_courts=db.total_courts,
        logs=db.system_logs
    )


@dashboard_bp.route('/api/action/quick_announcement', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def quick_announcement():
    """Posts a quick announcement to player boards."""
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    desc = data.get('description', '').strip()
    image_url = data.get('image_url', '').strip()

    if not title:
        return jsonify({"success": False, "message": "Announcement title is required."}), 400

    author_name = getattr(current_user, 'name', 'Admin')
    new_post = db.create_event_post(
        title=title,
        event_type="Announcement",
        description=desc,
        image_url=image_url,
        author=author_name
    )

    return jsonify({
        "success": True,
        "event": new_post.to_dict(),
        "message": f"Announcement '{title}' published to player board!"
    })


@dashboard_bp.route('/api/action/block_slot', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def block_slot():
    """Emergency action: Blocks court slot A3 for maintenance."""
    db.add_audit_log("Emergency Blocked Court Slot A3", current_user.name)
    return jsonify({"success": True, "message": "Court slot A3 temporarily blocked for system maintenance."})


@dashboard_bp.route('/api/action/issue_warning', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def issue_warning():
    """Broadcasts a conduct warning to platform users."""
    data = request.get_json() or {}
    msg = data.get('reason', 'General Conduct Warning')

    db.add_audit_log(f"Issued System Warning: {msg}", current_user.name)
    return jsonify({"success": True, "message": f"Global alert broadcasted: {msg}"})
