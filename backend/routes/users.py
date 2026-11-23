import os
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from backend.app import limiter
from backend.models.mock_db import db

users_bp = Blueprint('users', __name__)

SOFT_DELETE_PLAYERS = os.environ.get('SOFT_DELETE_PLAYERS', 'False').lower() in ('true', '1', 'yes')

@users_bp.route('/users')
@login_required
def users_list():
    # it fetches all the players data in db & pass ot to users.html
    players_data = [p.to_dict() if hasattr(p, 'to_dict') else p for p in db.players]
    return render_template('users.html', players=players_data)

@users_bp.route('/api/users/<player_id>/action', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def player_action(player_id):
    return jsonify({"success": False, "message": "Action no longer supported"}), 400

@users_bp.route('/api/users/<player_id>/delete', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def delete_player(player_id):
    # Enforce same admin authorization as other routes
    allowed_emails = current_app.config.get('ALLOWED_ADMIN_EMAILS', [])
    user_email = getattr(current_user, 'email', '')
    if not current_user.is_authenticated or (allowed_emails and user_email.strip().lower() not in allowed_emails):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    admin_name = getattr(current_user, 'name', 'Admin') or 'Admin'
    soft_delete = (
        current_app.config.get('SOFT_DELETE_PLAYERS', False)
        or SOFT_DELETE_PLAYERS
        or request.args.get('soft_delete', '').lower() in ('true', '1', 'yes')
    )

    success, result, status_code = db.delete_player(player_id, admin_name=admin_name, soft_delete=soft_delete)
    if success:
        return jsonify({"success": True, "counts": result}), status_code
    else:
        return jsonify({"success": False, "message": result.get("error", "Failed to delete player")}), status_code
