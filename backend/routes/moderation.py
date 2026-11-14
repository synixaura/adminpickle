from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from backend.app import limiter
from backend.models.mock_db import db

moderation_bp = Blueprint('moderation', __name__)

@moderation_bp.route('/moderation')
@login_required
def moderation_view():
    return render_template(
        'moderation.html',
        reports=db.reported_players
    )

@moderation_bp.route('/api/moderation/dismiss', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def dismiss_report_api():
    data = request.get_json() or {}
    report_id = data.get('report_id')
    if not report_id:
        return jsonify({"success": False, "message": "Report ID is required."}), 400

    success, msg = db.dismiss_report(report_id, current_user.name)
    if success:
        return jsonify({"success": True, "message": msg, "remaining_count": len(db.reported_players)})
    return jsonify({"success": False, "message": msg}), 404

@moderation_bp.route('/api/moderation/warn', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def warn_report_api():
    data = request.get_json() or {}
    report_id = data.get('report_id')
    if not report_id:
        return jsonify({"success": False, "message": "Report ID is required."}), 400

    success, msg = db.warn_and_dismiss_report(report_id, current_user.name)
    if success:
        return jsonify({"success": True, "message": msg, "remaining_count": len(db.reported_players)})
    return jsonify({"success": False, "message": msg}), 404

@moderation_bp.route('/api/moderation/action', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def report_action():
    data = request.get_json() or {}
    report_id = data.get('report_id')
    action = data.get('action')  # warning, dismiss, mute, ban

    if action == 'warning':
        success, msg = db.warn_and_dismiss_report(report_id, current_user.name)
        return jsonify({"success": success, "message": msg, "remaining_count": len(db.reported_players)})
    elif action == 'dismiss':
        success, msg = db.dismiss_report(report_id, current_user.name)
        return jsonify({"success": success, "message": msg, "remaining_count": len(db.reported_players)})
    
    return jsonify({"success": False, "message": "Invalid action."}), 400
