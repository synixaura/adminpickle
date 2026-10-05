from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from backend.models.mock_db import db

users_bp = Blueprint('users', __name__)

@users_bp.route('/users')
@login_required
def users_list():
    # it fetches all the players data in db & pass ot to users.html
    players_data = [p.to_dict() if hasattr(p, 'to_dict') else p for p in db.players]
    return render_template('users.html', players=players_data)

@users_bp.route('/api/users/<player_id>/action', methods=['POST'])
@login_required
def player_action(player_id):
    data = request.get_json() or {}
    action = data.get('action')

    if action == 'freeze':
        db.update_player_status(player_id, 'Frozen')
        db.add_audit_log(f"Froze account for player {player_id}", current_user.name)
        return jsonify({"success": True, "status": "Frozen", "message": f"Account {player_id} has been frozen."})

    elif action == 'ban':
        db.update_player_status(player_id, 'Banned')
        db.add_audit_log(f"Banned account for player {player_id}", current_user.name)
        return jsonify({"success": True, "status": "Banned", "message": f"Account {player_id} has been banned."})

    elif action == 'unban' or action == 'activate':
        db.update_player_status(player_id, 'Active')
        db.add_audit_log(f"Activated account for player {player_id}", current_user.name)
        return jsonify({"success": True, "status": "Active", "message": f"Account {player_id} is now Active."})

    elif action == 'reset_rating':
        db.reset_player_rating(player_id, 1500)
        db.add_audit_log(f"Reset Elo rating to 1500 for player {player_id}", current_user.name)
        return jsonify({"success": True, "elo": 1500, "message": f"Elo rating for {player_id} reset to 1500."})

    return jsonify({"success": False, "message": "Invalid action requested."}), 400
