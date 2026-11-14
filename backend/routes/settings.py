from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from backend.app import limiter
from backend.models.mock_db import db

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
def settings_view():
    return render_template(
        'settings.html',
        total_courts=db.total_courts,
        court_descriptions=db.get_court_descriptions(),
        contacts=db.get_court_crew_contacts(),
        audit_logs=db.audit_logs
    )

@settings_bp.route('/api/settings/courts', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def update_courts():
    data = request.get_json() or {}
    court_count = data.get('court_count')
    court_descriptions = data.get('court_descriptions')

    if court_count is None and court_descriptions is None:
        return jsonify({"success": False, "message": "Court count or descriptions are required."}), 400

    admin_name = getattr(current_user, 'name', 'Admin')

    new_count = db.total_courts
    if court_count is not None:
        _, new_count = db.set_total_courts(court_count, admin_name, descriptions=court_descriptions)
    elif court_descriptions is not None:
        db.set_court_descriptions(court_descriptions, admin=admin_name)

    return jsonify({
        "success": True,
        "court_count": new_count,
        "court_descriptions": db.get_court_descriptions(),
        "message": f"Venue courts and descriptions successfully updated."
    })


@settings_bp.route('/api/settings/contacts', methods=['GET'])
@login_required
def get_contacts():
    return jsonify({
        "success": True,
        "contacts": db.get_court_crew_contacts()
    })

@settings_bp.route('/api/settings/contacts', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def update_contacts():
    data = request.get_json() or {}
    contacts = data.get('contacts')
    if not isinstance(contacts, list):
        return jsonify({"success": False, "message": "Contacts list is required."}), 400

    admin_name = getattr(current_user, 'name', 'Admin')
    ok = db.set_court_crew_contacts(contacts, admin=admin_name)
    if ok:
        return jsonify({
            "success": True,
            "contacts": db.get_court_crew_contacts(),
            "message": "Court crew contacts successfully updated."
        })
    return jsonify({"success": False, "message": "Failed to update contacts."}), 500
