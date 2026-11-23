from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from backend.app import limiter
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
@limiter.limit("30 per minute")
def player_action(player_id):
    return jsonify({"success": False, "message": "Action no longer supported"}), 400
