import os
import uuid
import logging
import requests
from flask import Blueprint, render_template, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from backend.models.mock_db import db

profile_bp = Blueprint('profile', __name__)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
ALLOWED_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif'
}

def allowed_file(filename, mimetype=None):
    if not filename or '.' not in filename:
        return False
    ext_ok = filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    if mimetype:
        return ext_ok and (mimetype.lower() in ALLOWED_MIME_TYPES)
    return ext_ok

def upload_to_supabase_storage(file_bytes, filename, content_type):
    """
    Uploads an avatar file to Supabase Storage via REST API.
    Returns the permanent public URL on success, or None on failure.
    """
    supabase_url = current_app.config.get('SUPABASE_URL')
    supabase_key = current_app.config.get('SUPABASE_KEY')
    bucket = current_app.config.get('SUPABASE_STORAGE_BUCKET', 'avatars')

    if not supabase_url or not supabase_key:
        return None

    # Construct the Supabase Storage object endpoint
    clean_url = supabase_url.rstrip('/')
    endpoint = f"{clean_url}/storage/v1/object/{bucket}/{filename}"
    
    headers = {
        'Authorization': f'Bearer {supabase_key}',
        'apikey': supabase_key,
        'Content-Type': content_type or 'application/octet-stream',
        'x-upsert': 'true'
    }

    try:
        response = requests.post(endpoint, data=file_bytes, headers=headers, timeout=10)
        if response.status_code in (200, 201):
            public_url = f"{clean_url}/storage/v1/object/public/{bucket}/{filename}"
            logger.info(f"Successfully uploaded {filename} to Supabase Storage bucket '{bucket}'")
            return public_url
        else:
            logger.error(f"Supabase Storage upload failed with status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error uploading to Supabase Storage: {e}")
        return None

@profile_bp.route('/profile')
@login_required
def profile_view():
    """Renders the Administrator Profile & Customization screen."""
    return render_template('profile.html', user=current_user)

@profile_bp.route('/api/profile/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    """Handles avatar file uploads and image URL updates for the current administrator."""
    # Check if a file was uploaded via multipart/form-data
    if 'avatar' in request.files:
        file = request.files['avatar']
        filename = getattr(file, 'filename', None)
        if not file or not filename:
            return jsonify({"success": False, "message": "No file selected."}), 400
        
        mimetype = getattr(file, 'mimetype', None) or 'image/jpeg'
        if allowed_file(filename, mimetype):
            ext = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:12]}.{ext}"
            
            # Read file bytes into memory for validation and upload
            file_bytes = file.read()
            
            # Security: Cap file size to 5MB
            if len(file_bytes) > 5 * 1024 * 1024:
                return jsonify({"success": False, "message": "File size exceeds 5MB limit."}), 400

            # 1. Try uploading to Supabase Storage (if configured)
            avatar_url = upload_to_supabase_storage(file_bytes, unique_filename, mimetype)

            # 2. Reliable Cloud Fallback: Convert to Base64 Data URL (saved directly in database)
            if not avatar_url:
                import base64
                b64_str = base64.b64encode(file_bytes).decode('utf-8')
                avatar_url = f"data:{mimetype};base64,{b64_str}"

            # Update database record with new avatar URL
            db.update_admin_avatar(current_user.id, avatar_url)
            return jsonify({
                "success": True,
                "avatar_url": avatar_url,
                "message": "Profile photo updated successfully!"
            })
        else:
            return jsonify({"success": False, "message": "Invalid file format. Please upload JPG, PNG, WEBP, or GIF."}), 400

    # Also handle JSON payload if user pasted an image link or data URL
    data = request.get_json(silent=True) or {}
    image_url = data.get('avatar_url', '').strip()
    if image_url:
        # Validate that it starts with https://, http://, data:image/, or /static/
        if not (image_url.startswith('https://') or image_url.startswith('http://') or image_url.startswith('data:image/') or image_url.startswith('/static/')):
            return jsonify({"success": False, "message": "Please provide a valid image URL or image data."}), 400
        db.update_admin_avatar(current_user.id, image_url)
        return jsonify({
            "success": True,
            "avatar_url": image_url,
            "message": "Profile photo updated successfully!"
        })

    return jsonify({"success": False, "message": "No image file or URL provided."}), 400

@profile_bp.route('/api/profile/update-info', methods=['POST'])
@login_required
def update_profile_info():
    """Updates admin display name and/or role title."""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    role = data.get('role', '').strip()

    if not name:
        return jsonify({"success": False, "message": "Display name cannot be blank."}), 400

    success, msg = db.update_admin_profile(current_user.id, name=name, role=role if role else "Administrator")
    if success:
        return jsonify({
            "success": True,
            "name": current_user.name,
            "role": current_user.role,
            "message": msg
        })
    return jsonify({"success": False, "message": msg}), 400
