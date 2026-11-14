from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from backend.app import limiter
from backend.models.mock_db import db

venues_bp = Blueprint('venues', __name__)

# ---------------------------------------------------------------------------
#  Digital Booking Sheet Routes (Admin Pen-and-Paper Replacement)
# ---------------------------------------------------------------------------

@venues_bp.route('/booking-sheet')
@login_required
def booking_sheet_view():
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    selected_date = request.args.get('date', today_str)

    sheet_data = db.get_booking_sheet_matrix(selected_date)

    return render_template(
        'booking_sheet.html',
        selected_date=selected_date,
        time_slots=sheet_data['time_slots'],
        courts=sheet_data['courts'],
        matrix=sheet_data['matrix'],
        today_str=today_str
    )


@venues_bp.route('/api/booking-sheet/matrix')
@login_required
def get_booking_matrix():
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    date = request.args.get('date', today_str)
    sheet_data = db.get_booking_sheet_matrix(date)
    return jsonify({"success": True, **sheet_data})


@venues_bp.route('/api/booking-sheet/grid')
@login_required
def get_booking_grid():
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    date = request.args.get('date', today_str)
    court = request.args.get('court', 'Court 1')
    grid = db.get_booking_sheet_grid(date, court)
    return jsonify({"success": True, "grid": grid, "date": date, "court": court})



@venues_bp.route('/api/booking-sheet/save', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def save_booking():
    data = request.get_json() or {}
    date = data.get('date')
    court = data.get('court')
    time_slot = data.get('time_slot')
    customer_name = data.get('customer_name', '').strip()
    payment_status = data.get('payment_status', 'paid')
    payment_method = data.get('payment_method', 'Cash')
    amount_paid = data.get('amount_paid')
    rent_paddle = data.get('rent_paddle', False)
    paddle_count = data.get('paddle_count', 0)
    duration_hours = data.get('duration_hours', 1)

    if not date or not court or not time_slot or not customer_name:
        return jsonify({"success": False, "message": "Date, Court, Time Slot, and Customer Name are required."})

    success, msg = db.save_direct_booking(
        date=date,
        court=court,
        time_slot=time_slot,
        customer_name=customer_name,
        payment_status=payment_status,
        rent_paddle=rent_paddle,
        paddle_count=paddle_count,
        duration_hours=duration_hours,
        payment_method=payment_method,
        amount_paid=amount_paid
    )
    return jsonify({"success": success, "message": msg})


@venues_bp.route('/api/booking-sheet/clear', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def clear_booking():
    data = request.get_json() or {}
    date = data.get('date')
    court = data.get('court')
    time_slot = data.get('time_slot')

    if not date or not court or not time_slot:
        return jsonify({"success": False, "message": "Date, Court, and Time Slot are required."})

    success, msg = db.clear_direct_booking(date, court, time_slot)
    return jsonify({"success": success, "message": msg})

