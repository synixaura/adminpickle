"""
PickleLegends Admin & Player Platform - Unified Database Engine
Fully connected to shared PostgreSQL / Supabase database.
Matches the exact schema from Player App (player/model.py).
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import time
import os
import logging
import json
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
sqla = SQLAlchemy()


# ==============================================================================
# 1. CORE UNIFIED DATABASE MODELS
# ==============================================================================

class AdminUser(UserMixin, sqla.Model):
    """Admin Staff & Platform Administrators"""
    __tablename__ = 'admin_users'

    id = sqla.Column(sqla.Integer, primary_key=True, autoincrement=True)
    username = sqla.Column(sqla.String(80), unique=True, nullable=False)
    name = sqla.Column(sqla.String(100), nullable=False)
    email = sqla.Column(sqla.String(255), unique=True, nullable=True)
    role = sqla.Column(sqla.String(100), default='Lead Platform Admin')
    avatar_url = sqla.Column(sqla.Text, nullable=True)
    password_hash = sqla.Column(sqla.String(255), nullable=False)

    def __init__(self, id=None, username=None, name=None, email=None, role="Lead Platform Admin", avatar_url=None, password_hash=None, **kwargs):
        super().__init__(**kwargs)
        if id is not None:
            try:
                self.id = int(id)
            except (ValueError, TypeError):
                pass
        self.username = username
        self.name = name
        self.email = email
        self.role = role
        self.avatar_url = avatar_url
        self.password_hash = password_hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "avatar_url": self.avatar_url
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------

TIERS: List[Dict[str, Any]] = [
    {
        "name": "Bronze",
        "short": "Bronze",
        "min_xp": 0,
        "max_xp": 999,
        "index": 0,
        "color": "#CD7F32",
        "icon": "🥉"
    },
    {
        "name": "Silver",
        "short": "Silver",
        "min_xp": 1000,
        "max_xp": 2199,
        "index": 1,
        "color": "#94A3B8",
        "icon": "🥈"
    },
    {
        "name": "Gold",
        "short": "Gold",
        "min_xp": 2200,
        "max_xp": 3599,
        "index": 2,
        "color": "#F59E0B",
        "icon": "🥇"
    },
    {
        "name": "Platinum",
        "short": "Platinum",
        "min_xp": 3600,
        "max_xp": 5399,
        "index": 3,
        "color": "#00A884",
        "icon": "💎"
    },
    {
        "name": "Diamond",
        "short": "Diamond",
        "min_xp": 5400,
        "max_xp": 7999,
        "index": 4,
        "color": "#3B82F6",
        "icon": "💠"
    },
    {
        "name": "Master",
        "short": "Master",
        "min_xp": 8000,
        "max_xp": 11999,
        "index": 5,
        "color": "#8B5CF6",
        "icon": "👑"
    },
    {
        "name": "Emperor",
        "short": "Emperor",
        "min_xp": 12000,
        "max_xp": 999999,
        "index": 6,
        "color": "#EC4899",
        "icon": "⚡"
    },
]

TIER_BY_NAME: Dict[str, Dict[str, Any]] = {str(t["name"]).lower(): t for t in TIERS}


def get_tier_by_xp(xp: int) -> Dict[str, Any]:
    """Returns tier metadata corresponding to a given XP value."""
    clamped_xp = max(0, xp if isinstance(xp, int) else int(xp or 0))
    for t in reversed(TIERS):
        if clamped_xp >= int(t["min_xp"]):
            return t
    return TIERS[0]


def get_tier_divisions(xp: int):
    """
    Computes tier name and division (IV to I) for tiers below Master.
    Master and Emperor do not have subdivisions.
    """
    tier = get_tier_by_xp(xp)
    if tier["index"] in (5, 6):  # Master or Emperor
        return tier["name"], 1

    tier_span = int(tier["max_xp"]) - int(tier["min_xp"]) + 1
    div_size = tier_span / 4.0
    safe_xp = xp if isinstance(xp, int) else int(xp or 0)
    progress = max(0, safe_xp - int(tier["min_xp"]))

    div_index = min(3, int(progress / div_size))
    div_number = 4 - div_index
    roman = {4: "IV", 3: "III", 2: "II", 1: "I"}.get(div_number, "IV")
    return f"{tier['name']} {roman}", div_number


def skill_tier(rating):
    """Buckets numeric skill rating into Beginner, Intermediate, Advanced, Expert."""
    if rating is None:
        return "Unrated"
    try:
        val = float(rating)
    except (ValueError, TypeError):
        return str(rating) if rating else "Unrated"

    if val < 2.0:
        return "Novice"
    elif val < 3.0:
        return "Beginner"
    elif val < 4.0:
        return "Intermediate"
    elif val < 5.0:
        return "Advanced"
    else:
        return "Expert"


def get_effective_skill_level(user_obj_or_dict):
    """
    Returns the effective skill level representation for a player.
    Prefers verified DUPR rating if present and verified, otherwise falls back to self_reported_skill.
    """
    if isinstance(user_obj_or_dict, dict):
        dupr_verified = bool(user_obj_or_dict.get("dupr_verified"))
        dupr_rating = user_obj_or_dict.get("dupr_rating")
        self_reported = (
            user_obj_or_dict.get("self_reported_skill")
            or (f"{float(dupr_rating):.2f}" if dupr_rating is not None else None)
            or "Beginner"
        )
    else:
        dupr_verified = bool(getattr(user_obj_or_dict, "dupr_verified", False))
        dupr_rating = getattr(user_obj_or_dict, "dupr_rating", None)
        self_reported = (
            getattr(user_obj_or_dict, "self_reported_skill", None)
            or (f"{float(dupr_rating):.2f}" if dupr_rating is not None else None)
            or "Beginner"
        )

    if dupr_verified and dupr_rating is not None:
        try:
            num = float(dupr_rating)
            return {
                "effective_rating": num,
                "display_name": f"{num:.2f} DUPR",
                "tier": skill_tier(num),
                "is_verified": True
            }
        except (ValueError, TypeError):
            pass

    try:
        num = float(self_reported)
        return {
            "effective_rating": num,
            "display_name": f"{num:.2f} (Self-Reported)",
            "tier": skill_tier(num),
            "is_verified": False
        }
    except (ValueError, TypeError):
        pass

    clean_label = str(self_reported) if self_reported else "Beginner"
    return {
        "effective_rating": None,
        "display_name": clean_label,
        "tier": skill_tier(clean_label) if clean_label.replace('.', '', 1).isdigit() else clean_label,
        "is_verified": False
    }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------


class User(sqla.Model):
    """
    Player & Member Account Model (Shared directly with Player App)
    Matches player/model.py fields.
    """
    __tablename__ = 'users'

    handle = sqla.Column(sqla.String(100), primary_key=True)  # e.g. 'player_one', 'player_two'
    name = sqla.Column(sqla.String(100), nullable=False)
    email = sqla.Column(sqla.String(120), unique=True, nullable=True)
    contact = sqla.Column(sqla.String(50), nullable=True)
    bio = sqla.Column(sqla.Text, nullable=True)
    preferred_court = sqla.Column(sqla.String(150), default="Butuan Ground Zero Pickleball Yard")
    play_style = sqla.Column(sqla.String(100), default="Aggressive Kitchen Play")
    member_since = sqla.Column(sqla.String(50), default="July 2026")
    rank = sqla.Column(sqla.String(100), default="Bronze IV")
    rank_short = sqla.Column(sqla.String(50), default="Bronze")
    avatar = sqla.Column(sqla.Text, nullable=True)
    initials = sqla.Column(sqla.String(10), default="PL")
    elo = sqla.Column(sqla.Integer, default=0)
    xp = sqla.Column(sqla.Integer, default=0)
    max_xp = sqla.Column(sqla.Integer, default=1000)
    wins = sqla.Column(sqla.Integer, default=0)
    losses = sqla.Column(sqla.Integer, default=0)
    total_games = sqla.Column(sqla.Integer, default=0)
    win_rate = sqla.Column(sqla.String(20), default="0%")
    dupr_id = sqla.Column(sqla.String(50), nullable=True)
    dupr_rating = sqla.Column(sqla.Float, nullable=True)
    dupr_verified = sqla.Column(sqla.Boolean, default=False)
    dupr_last_synced = sqla.Column(sqla.Float, nullable=True)
    self_reported_skill = sqla.Column(sqla.String(50), default="Beginner")
    status = sqla.Column(sqla.String(20), default="Active")  # 'Active', 'Frozen', 'Banned'
    reports = sqla.Column(sqla.Integer, default=0)
    notes = sqla.Column(sqla.Text, nullable=True)
    created_at = sqla.Column(sqla.DateTime, default=datetime.now)

    def __init__(self, handle, name, email=None, contact="", bio="", preferred_court="Butuan Ground Zero Pickleball Yard",
                 play_style="Aggressive Kitchen Play", member_since="July 2026", rank=None,
                 rank_short=None, avatar=None, initials=None, elo=0, xp=0, max_xp=1000,
                 wins=0, losses=0, total_games=0, win_rate="0%", dupr_id=None, dupr_rating=None,
                 dupr_verified=False, self_reported_skill="Beginner", status="Active", reports=0, notes="", **kwargs):
        super().__init__(**kwargs)
        self.handle = handle
        self.name = name
        self.email = email or f"{handle}@picklelegends.ph"
        self.contact = contact
        self.bio = bio
        self.preferred_court = preferred_court
        self.play_style = play_style
        self.member_since = member_since
        self.xp = int(xp) if xp else 0
        computed_rank, _ = get_tier_divisions(self.xp)
        computed_meta = get_tier_by_xp(self.xp)
        self.rank = rank or computed_rank
        self.rank_short = rank_short or computed_meta["name"]
        self.avatar = avatar
        self.initials = initials or "".join([w[0].upper() for w in name.split()[:2]]) or "PL"
        self.elo = int(elo) if elo else 0
        self.max_xp = int(max_xp) if max_xp else computed_meta["max_xp"]
        self.wins = int(wins) if wins else 0
        self.losses = int(losses) if losses else 0
        self.total_games = int(total_games) if total_games else (self.wins + self.losses)
        self.win_rate = win_rate
        self.dupr_id = dupr_id
        self.dupr_rating = float(dupr_rating) if dupr_rating is not None else None
        self.dupr_verified = bool(dupr_verified)
        self.self_reported_skill = self_reported_skill
        self.status = status
        self.reports = int(reports) if reports else 0
        self.notes = notes

    @property
    def id(self):
        """Compatibility property for templates expecting player.id"""
        return self.handle

    @property
    def tier(self):
        """Returns the player's real competitive division rank (Bronze IV, Silver I, Gold II, etc.)"""
        display_rank, _ = get_tier_divisions(self.xp or 0)
        return display_rank

    @property
    def matches(self):
        return self.total_games

    def to_dict(self):
        user_xp = int(self.xp or 0)
        tier_meta = get_tier_by_xp(user_xp)
        display_rank, div_num = get_tier_divisions(user_xp)
        skill_info = get_effective_skill_level(self)

        min_xp = int(tier_meta.get("min_xp", 0))
        max_xp = int(tier_meta.get("max_xp", 1000))
        tier_span = max(1, max_xp - min_xp)
        tier_progress = max(0, min(tier_span, user_xp - min_xp))
        tier_pct = round((tier_progress / tier_span) * 100) if tier_meta.get("index", 0) < 6 else 100

        return {
            "id": self.handle,
            "handle": self.handle,
            "name": self.name,
            "email": self.email,
            "contact": self.contact,
            "bio": self.bio,
            "preferred_court": self.preferred_court,
            "play_style": self.play_style,
            "member_since": self.member_since,
            "rank": display_rank,
            "rank_short": tier_meta["name"],
            "current_tier": tier_meta["name"],
            "tier": display_rank,
            "tier_icon": tier_meta["icon"],
            "tier_color": tier_meta["color"],
            "tier_division": f"Division {div_num}" if tier_meta.get("index", 0) < 5 else "",
            "tier_min_xp": min_xp,
            "tier_max_xp": max_xp,
            "tier_progress_pct": tier_pct,
            "skill_level": skill_info["display_name"],
            "skill_tier": skill_info["tier"],
            "is_dupr_verified": skill_info["is_verified"],
            "avatar": self.avatar,
            "initials": self.initials or (self.name[0].upper() if self.name else "PL"),
            "elo": int(self.elo or 0),
            "xp": user_xp,
            "max_xp": max_xp,
            "wins": int(self.wins or 0),
            "losses": int(self.losses or 0),
            "total_games": int(self.total_games or 0),
            "matches": int(self.total_games or 0),
            "win_rate": self.win_rate or "0%",
            "dupr_id": self.dupr_id,
            "dupr_rating": self.dupr_rating,
            "dupr_verified": bool(self.dupr_verified),
            "self_reported_skill": self.self_reported_skill or "Beginner",
            "status": self.status,
            "reports": self.reports,
            "notes": self.notes
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------

    def __getitem__(self, key):
        if key == 'id':
            return self.handle
        if key == 'matches':
            return self.total_games
        if key == 'tier':
            return self.tier
        return getattr(self, key, None)

    def get(self, key, default=None):
        if key == 'id':
            return self.handle
        if key == 'matches':
            return self.total_games
        if key == 'tier':
            return self.tier
        return getattr(self, key, default)


class ConfirmedBooking(sqla.Model):
    """
    Confirmed Court Bookings (Shared with Player App)
    Matches confirmed_bookings in player/model.py.
    """
    __tablename__ = 'confirmed_bookings'

    id = sqla.Column(sqla.String(50), primary_key=True)  # e.g. 'BK-4081'
    court = sqla.Column(sqla.String(150), default="Butuan Ground Zero Pickleball Yard")
    court_no = sqla.Column(sqla.String(100), default="Court 1 (Main Championship)")
    customer_name = sqla.Column(sqla.String(100), default="Zask Paddler")
    date = sqla.Column(sqla.String(50), nullable=False)
    time = sqla.Column(sqla.String(50), nullable=False)
    duration = sqla.Column(sqla.String(50), default="2 hrs")
    amount_paid = sqla.Column(sqla.Float, default=600.0)
    payment_method = sqla.Column(sqla.String(50), default="GCash")
    staff_name = sqla.Column(sqla.String(100), default="Coach Dave Reyes")
    status = sqla.Column(sqla.String(50), default="Confirmed")
    flow_type = sqla.Column(sqla.String(50), default="direct")
    rent_paddle = sqla.Column(sqla.Boolean, default=False)
    paddle_count = sqla.Column(sqla.Integer, default=0)
    created_at = sqla.Column(sqla.DateTime, default=datetime.now)

    def __init__(self, id, court="Butuan Ground Zero Pickleball Yard", court_no="Court 1",
                 customer_name="Zask Paddler", date=None, time=None, duration="2 hrs",
                 amount_paid=600.0, payment_method="GCash", staff_name="Coach Dave Reyes",
                 status="Confirmed", flow_type="direct", rent_paddle=False, paddle_count=0, **kwargs):
        super().__init__(**kwargs)
        self.id = id
        self.court = court
        self.court_no = court_no
        self.customer_name = customer_name
        self.date = date or datetime.now().strftime("%B %d, %Y")
        self.time = time or "8:00 AM - 10:00 AM"
        self.duration = duration
        self.amount_paid = float(amount_paid) if amount_paid else 600.0
        self.payment_method = payment_method
        self.staff_name = staff_name
        self.status = status
        self.flow_type = flow_type
        self.rent_paddle = bool(rent_paddle)
        self.paddle_count = int(paddle_count) if rent_paddle else 0

    @property
    def payment_status(self):
        if self.status and self.status.lower() in ("unpaid", "pending"):
            return "unpaid"
        return "paid"

    def to_dict(self):
        return {
            "id": self.id,
            "court": self.court,
            "court_no": self.court_no,
            "customer_name": self.customer_name,
            "date": self.date,
            "time": self.time,
            "duration": self.duration,
            "amount_paid": self.amount_paid,
            "payment_method": self.payment_method,
            "staff_name": self.staff_name,
            "status": self.status,
            "payment_status": self.payment_status,
            "flow_type": self.flow_type,
            "rent_paddle": self.rent_paddle,
            "paddle_count": self.paddle_count,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------


class OpenPlaySession(sqla.Model):
    """
    Open Play Sessions (Shared with Player App)
    Matches open_play_sessions in player/model.py.
    """
    __tablename__ = 'open_play_sessions'

    id = sqla.Column(sqla.String(50), primary_key=True)  # e.g. 'op_1'
    title = sqla.Column(sqla.String(200), nullable=False)
    booking_id = sqla.Column(sqla.String(50), nullable=True)
    court = sqla.Column(sqla.String(150), default="Butuan Ground Zero Pickleball Yard")
    court_no = sqla.Column(sqla.String(100), default="Court 1 (Main Court)")
    date = sqla.Column(sqla.String(50), nullable=False)
    time = sqla.Column(sqla.String(50), nullable=False)
    staff_name = sqla.Column(sqla.String(100), default="Coach Dave Reyes")
    host_name = sqla.Column(sqla.String(100), default="Zask Paddler")
    host_handle = sqla.Column(sqla.String(100), default="zask_game")
    host_initials = sqla.Column(sqla.String(10), default="ZP")
    match_format = sqla.Column(sqla.String(100), default="Doubles 2v2 Round Robin")
    skill_level = sqla.Column(sqla.String(100), default="Intermediate (3.0 - 3.5)")
    max_players = sqla.Column(sqla.Integer, default=8)
    fee_per_player = sqla.Column(sqla.String(100), default="₱75 / player (Split Court Fee)")
    notes = sqla.Column(sqla.Text, nullable=True)
    status = sqla.Column(sqla.String(50), default="open")  # 'open', 'full', 'completed'
    court_count = sqla.Column(sqla.Integer, default=3)
    roster_state = sqla.Column(sqla.Text, nullable=True)
    session_data = sqla.Column(sqla.Text, nullable=True)
    created_at = sqla.Column(sqla.DateTime, default=datetime.now)

    def __init__(self, id, title, date=None, time=None, booking_id="BK-4081",
                 court="Butuan Ground Zero Pickleball Yard", court_no="Court 1",
                 staff_name="Coach Dave Reyes", host_name="Zask Paddler", host_handle="zask_game",
                 host_initials="ZP", match_format="Doubles 2v2 Round Robin", skill_level="Intermediate (3.0 - 3.5)",
                 max_players=8, fee_per_player="₱75 / player", notes="", status="open", court_count=3,
                 roster_state=None, session_data=None, **kwargs):
        super().__init__(**kwargs)
        self.roster_state = roster_state
        self.session_data = session_data
        self.id = id
        self.title = title
        self.booking_id = booking_id
        self.court = court
        self.court_no = court_no
        self.date = date or datetime.now().strftime("%B %d, %Y")
        self.time = time or "6:00 PM - 8:00 PM"
        self.staff_name = staff_name
        self.host_name = host_name
        self.host_handle = host_handle
        self.host_initials = host_initials
        self.match_format = match_format
        self.skill_level = skill_level
        self.max_players = int(max_players) if max_players else 8
        self.fee_per_player = fee_per_player
        self.notes = notes
        self.status = status
        self.court_count = int(court_count) if court_count else 3

    # Compatibility getters
    @property
    def start_time(self):
        if " - " in (self.time or ""):
            return self.time.split(" - ")[0].strip()
        return self.time or "8:00 AM"

    @property
    def end_time(self):
        if " - " in (self.time or ""):
            return self.time.split(" - ")[1].strip()
        return "10:00 AM"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "booking_id": self.booking_id,
            "court": self.court,
            "court_no": self.court_no,
            "date": self.date,
            "time": self.time,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "staff_name": self.staff_name,
            "host_name": self.host_name,
            "host_handle": self.host_handle,
            "host_initials": self.host_initials,
            "match_format": self.match_format,
            "skill_level": self.skill_level,
            "max_players": self.max_players,
            "court_count": self.court_count,
            "fee_per_player": self.fee_per_player,
            "notes": self.notes,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------


class SessionParticipant(sqla.Model):
    """Lineup / Joined Players in Open Play Sessions"""
    __tablename__ = 'session_participants'

    id = sqla.Column(sqla.String(50), primary_key=True)
    session_id = sqla.Column(sqla.String(50), nullable=False)
    player_id = sqla.Column(sqla.String(100), nullable=False)  # handle
    player_name = sqla.Column(sqla.String(100), nullable=False)
    initials = sqla.Column(sqla.String(10), default="PL")
    elo = sqla.Column(sqla.Integer, default=0)
    is_host = sqla.Column(sqla.Boolean, default=False)
    payment_status = sqla.Column(sqla.String(50), default="paid")  # 'paid', 'pending', 'expired'
    payment_method = sqla.Column(sqla.String(50), default="gcash")
    receipt = sqla.Column(sqla.Text, nullable=True)
    games_played = sqla.Column(sqla.Integer, default=0)
    rotation_status = sqla.Column(sqla.String(50), default="waiting")  # 'waiting', 'playing', 'resting'
    joined_at = sqla.Column(sqla.DateTime, default=datetime.now)

    def __init__(self, id, session_id, player_id, player_name, initials=None, elo=0,
                 is_host=False, payment_status="paid", payment_method="gcash", receipt=None, **kwargs):
        super().__init__(**kwargs)
        self.id = id
        self.session_id = session_id
        self.player_id = player_id
        self.player_name = player_name
        self.initials = initials or "".join([w[0].upper() for w in player_name.split()[:2]]) or "PL"
        self.elo = int(elo) if elo else 0
        self.is_host = bool(is_host)
        self.payment_status = payment_status
        self.payment_method = payment_method
        self.receipt = receipt
        self.games_played = 0
        self.rotation_status = "waiting"

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "initials": self.initials,
            "elo": self.elo,
            "is_host": self.is_host,
            "payment_status": self.payment_status,
            "payment_method": self.payment_method,
            "receipt": self.receipt,
            "games_played": self.games_played,
            "rotation_status": self.rotation_status,
            "joined_at": self.joined_at.strftime("%Y-%m-%d %H:%M:%S") if self.joined_at else ""
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------


class PlayerRating(sqla.Model):
    """Player Sportsmanship and Skill Ratings (Shared with Player App)"""
    __tablename__ = 'player_ratings'

    id = sqla.Column(sqla.String(100), primary_key=True)  # e.g. 'pr_1728000000_1'
    match_id = sqla.Column(sqla.String(100), nullable=True)
    session_id = sqla.Column(sqla.String(100), nullable=True)
    rater_id = sqla.Column(sqla.String(100), nullable=False)
    rated_player_id = sqla.Column(sqla.String(100), nullable=False)
    skill_rating = sqla.Column(sqla.Integer, default=3)
    skill_match = sqla.Column(sqla.String(50), default="about_right")
    sportsmanship_rating = sqla.Column(sqla.Integer, default=5)
    behavior_rating = sqla.Column(sqla.String(50), default="good_sport")
    role_in_match = sqla.Column(sqla.String(50), default="opponent")
    feedback_text = sqla.Column(sqla.Text, nullable=True)
    created_at = sqla.Column(sqla.DateTime, default=datetime.now)

    def __init__(self, id, rater_id, rated_player_id, match_id=None, session_id=None,
                 skill_rating=3, skill_match="about_right", sportsmanship_rating=5,
                 behavior_rating="good_sport", role_in_match="opponent", feedback_text=None, **kwargs):
        super().__init__(**kwargs)
        self.id = id
        self.rater_id = rater_id
        self.rated_player_id = rated_player_id
        self.match_id = match_id
        self.session_id = session_id
        self.skill_rating = int(skill_rating) if skill_rating else 3
        self.skill_match = skill_match
        self.sportsmanship_rating = int(sportsmanship_rating) if sportsmanship_rating else 5
        self.behavior_rating = behavior_rating
        self.role_in_match = role_in_match
        self.feedback_text = feedback_text

    def to_dict(self):
        return {
            "id": self.id,
            "match_id": self.match_id,
            "session_id": self.session_id,
            "rater_id": self.rater_id,
            "rated_player_id": self.rated_player_id,
            "skill_rating": self.skill_rating,
            "skill_match": self.skill_match,
            "sportsmanship_rating": self.sportsmanship_rating,
            "behavior_rating": self.behavior_rating,
            "role_in_match": self.role_in_match,
            "feedback_text": self.feedback_text,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------


class EventPost(sqla.Model):
    """Club Announcements & Tournaments Board"""
    __tablename__ = 'event_posts'

    id = sqla.Column(sqla.String(50), primary_key=True)  # e.g. 'EVT-101'
    title = sqla.Column(sqla.String(200), nullable=False)
    event_type = sqla.Column(sqla.String(100), default='Announcement')
    date = sqla.Column(sqla.String(100), nullable=True)
    description = sqla.Column(sqla.Text, nullable=True)
    image_url = sqla.Column(sqla.Text, nullable=True)
    author = sqla.Column(sqla.String(100), default='Karl Alegrado')
    status = sqla.Column(sqla.String(50), default='Published')
    created_at = sqla.Column(sqla.DateTime, default=datetime.now)

    def __init__(self, id, title, event_type="Announcement", date=None, description="",
                 image_url="", author="Karl Alegrado", status="Published", **kwargs):
        super().__init__(**kwargs)
        self.id = id
        self.title = title
        self.event_type = event_type
        self.date = date or datetime.now().strftime("%b %d, %Y")
        self.description = description or ""
        self.image_url = image_url or ""
        self.author = author
        self.status = status

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "event_type": self.event_type,
            "date": self.date,
            "description": self.description,
            "image_url": self.image_url,
            "author": self.author,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------


class AuditLog(sqla.Model):
    """Platform Audit Trail & Activity Logs"""
    __tablename__ = 'audit_logs'

    id = sqla.Column(sqla.Integer, primary_key=True, autoincrement=True)
    timestamp = sqla.Column(sqla.String(100), nullable=False)
    admin = sqla.Column(sqla.String(100), default='System (Auto)')
    action = sqla.Column(sqla.Text, nullable=False)
    ip = sqla.Column(sqla.String(50), default='192.168.1.45')
    status = sqla.Column(sqla.String(50), default='Completed')
    created_at = sqla.Column(sqla.DateTime, default=datetime.now)

    def __init__(self, action, admin="Karl Alegrado", timestamp=None, ip="192.168.1.45", status="Completed", **kwargs):
        super().__init__(**kwargs)
        self.action = action
        self.admin = admin
        self.timestamp = timestamp or ("Today, " + datetime.now().strftime("%H:%M:%S"))
        self.ip = ip
        self.status = status

    def to_dict(self):
        return {
            "id": f"LOG-{9000 + self.id}" if self.id else "LOG-AUTO",
            "timestamp": self.timestamp,
            "admin": self.admin,
            "action": self.action,
            "ip": self.ip,
            "status": self.status
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


class PlatformSetting(sqla.Model):
    """Configurable Key-Value Store for Platform Settings"""
    __tablename__ = 'platform_settings'

    key = sqla.Column(sqla.String(100), primary_key=True)
    value = sqla.Column(sqla.Text, nullable=True)
    updated_at = sqla.Column(sqla.DateTime, default=datetime.now, onupdate=datetime.now)

    def __init__(self, key, value, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self.value = str(value)


# Transient in-memory 2v2 Match Object for real-time court rotation
class Game:
    def __init__(self, id, session_id, court_number, team_a, team_b, status="in_progress"):
        self.id = id
        self.session_id = session_id
        self.court_number = int(court_number)
        self.team_a = team_a
        self.team_b = team_b
        self.team_a_score = 0
        self.team_b_score = 0
        self.started_at = datetime.now()
        self.ended_at = None
        self.status = status

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "court_number": self.court_number,
            "team_a": [p.player_name if hasattr(p, 'player_name') else p['player_name'] for p in self.team_a],
            "team_b": [p.player_name if hasattr(p, 'player_name') else p['player_name'] for p in self.team_b],
            "team_a_score": self.team_a_score,
            "team_b_score": self.team_b_score,
            "started_at": self.started_at.strftime("%H:%M:%S"),
            "ended_at": self.ended_at.strftime("%H:%M:%S") if self.ended_at else None,
            "status": self.status
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------


# ==============================================================================
# 2. BOOKING SHEET CONSTANTS & HELPERS
# ==============================================================================

BOOKING_TIME_SLOTS = [
    "06:00 AM", "07:00 AM", "08:00 AM", "09:00 AM", "10:00 AM", "11:00 AM",
    "12:00 PM", "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM",
    "06:00 PM", "07:00 PM", "08:00 PM", "09:00 PM", "10:00 PM", "11:00 PM", "12:00 AM"
]

BOOKING_COURTS = ["Court 1", "Court 2", "Court 3", "Court 4", "Court 5", "Court 6"]


def normalize_date_str(d_str):
    if not d_str:
        return ""
    d_str = str(d_str).strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(d_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return d_str


def parse_time_to_minutes(time_str):
    if not time_str:
        return 0
    t_str = time_str.strip().upper()
    if t_str.endswith("AM") and not t_str.endswith(" AM"):
        t_str = t_str[:-2] + " AM"
    elif t_str.endswith("PM") and not t_str.endswith(" PM"):
        t_str = t_str[:-2] + " PM"

    try:
        dt = datetime.strptime(t_str, "%I:%M %p")
        return dt.hour * 60 + dt.minute
    except ValueError:
        try:
            dt = datetime.strptime(t_str, "%H:%M")
            return dt.hour * 60 + dt.minute
        except ValueError:
            return 0


def normalize_time_slot(time_str):
    if not time_str:
        return ""
    t_str = str(time_str).strip().upper()
    if " - " in t_str:
        t_str = t_str.split(" - ")[0].strip()
    if t_str.endswith("AM") and not t_str.endswith(" AM"):
        t_str = t_str[:-2] + " AM"
    elif t_str.endswith("PM") and not t_str.endswith(" PM"):
        t_str = t_str[:-2] + " PM"

    try:
        dt = datetime.strptime(t_str, "%I:%M %p")
        return dt.strftime("%I:%M %p")
    except ValueError:
        try:
            dt = datetime.strptime(t_str, "%H:%M")
            return dt.strftime("%I:%M %p")
        except ValueError:
            return time_str.strip()


# ==============================================================================
# 3. DATABASE MANAGER & BUSINESS LOGIC ENGINE
# ==============================================================================

class DatabaseManager:
    """
    Database Manager
    Operates directly on PostgreSQL/Supabase database tables.
    """
    def __init__(self):
        self.time_slots = ["08:00 AM", "10:00 AM", "12:00 PM", "02:00 PM", "04:00 PM", "06:00 PM"]
        self.total_courts = 6
        self.courts = [f"Court {i}" for i in range(1, 7)]
        self.venues = [
            {"id": 1, "name": "Butuan Ground Zero Pickleball Yard", "courts": self.total_courts, "rate": "300 PHP/hr", "active": True},
            {"id": 2, "name": "PickleYard Butuan Arena", "courts": 4, "rate": "250 PHP/hr", "active": False},
        ]
        self.session_games = {}

    # --------------------------------------------------------------------------
    # ADMIN AUTHENTICATION & PROFILE
    # --------------------------------------------------------------------------
    def get_user_by_id(self, user_id):
        try:
            return AdminUser.query.get(int(user_id))
        except Exception as e:
            logger.error(f"Error in get_user_by_id: {e}")
            try:
                sqla.session.rollback()
            except Exception:
                pass
            return None

    def get_user_by_username(self, username):
        try:
            return AdminUser.query.filter_by(username=username).first()
        except Exception as e:
            logger.error(f"Error in get_user_by_username: {e}")
            try:
                sqla.session.rollback()
            except Exception:
                pass
            return None

    def get_admin_by_email(self, email):
        """Look up an AdminUser by their Google email (case-insensitive)."""
        if not email:
            return None
        try:
            return AdminUser.query.filter(
                sqla.func.lower(AdminUser.email) == email.strip().lower()
            ).first()
        except Exception as e:
            logger.error(f"Error in get_admin_by_email: {e}")
            try:
                sqla.session.rollback()
            except Exception:
                pass
            return None

    def get_or_create_admin_by_google(self, email, name, avatar_url=None):
        """
        Fetch existing AdminUser by email or username, or provision one on first Google login.
        Returns the AdminUser instance.
        """
        import secrets
        norm_email = email.strip().lower()
        
        # Ensure session is not in an aborted transaction state from previous calls
        try:
            sqla.session.rollback()
        except Exception:
            pass

        # 1. Match by email column
        user = self.get_admin_by_email(norm_email)
        if user:
            # Update name/avatar if not set or changed
            changed = False
            if name and not user.name:
                user.name = name
                changed = True
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
                changed = True
            if changed:
                try:
                    sqla.session.commit()
                except Exception:
                    sqla.session.rollback()
            return user

        # 2. Match existing legacy admin by username (if username == email or matches prefix)
        try:
            user_by_uname = AdminUser.query.filter(
                sqla.func.lower(AdminUser.username) == norm_email
            ).first()
            if user_by_uname:
                user_by_uname.email = norm_email
                if avatar_url and not user_by_uname.avatar_url:
                    user_by_uname.avatar_url = avatar_url
                try:
                    sqla.session.commit()
                    return user_by_uname
                except Exception:
                    sqla.session.rollback()
        except Exception as e:
            logger.error(f"Error querying admin by username in get_or_create: {e}")
            try:
                sqla.session.rollback()
            except Exception:
                pass

        # 3. Provision new AdminUser
        try:
            display_name = name if name and name.strip() else norm_email.split('@')[0].capitalize()
            sentinel_hash = generate_password_hash(secrets.token_hex(32))
            new_admin = AdminUser(
                username=norm_email,
                name=display_name,
                email=norm_email,
                role='Lead Platform Admin',
                avatar_url=avatar_url,
                password_hash=sentinel_hash
            )
            sqla.session.add(new_admin)
            sqla.session.commit()
            self.add_audit_log(f"Provisioned new admin account via Google Sign-In ({norm_email})", display_name)
            return new_admin
        except Exception as e:
            logger.error(f"[PROVISION ERROR] Could not create AdminUser for {norm_email}: {e}", exc_info=True)
            print(f"[PROVISION ERROR for {norm_email}]: {e}")
            sqla.session.rollback()
            # If race condition or duplicate username, retry fetch
            return self.get_admin_by_email(norm_email) or self.get_user_by_username(norm_email)

    def update_admin_profile(self, user_id, name=None, role=None):
        user = self.get_user_by_id(user_id)
        if not user:
            return False, "User not found."
        if name and name.strip():
            user.name = name.strip()
        if role and role.strip():
            user.role = role.strip()
        try:
            sqla.session.commit()
            self.add_audit_log(f"Updated admin profile for {user.username} (Name: '{user.name}', Role: '{user.role}')", user.name)
            return True, "Profile updated successfully."
        except Exception as e:
            sqla.session.rollback()
            return False, f"Failed to save profile: {str(e)}"

    def update_admin_avatar(self, user_id, avatar_url):
        user = self.get_user_by_id(user_id)
        if not user:
            return False, "User not found."
        user.avatar_url = avatar_url.strip()
        try:
            sqla.session.commit()
            self.add_audit_log(f"Updated profile photo for {user.name}", user.name)
            return True, "Avatar updated successfully."
        except Exception as e:
            sqla.session.rollback()
            return False, f"Failed to update avatar: {str(e)}"

    # --------------------------------------------------------------------------
    # PLAYERS & USERS DIRECTORY
    # --------------------------------------------------------------------------
    @property
    def players(self):
        try:
            return User.query.order_by(User.elo.desc()).all()
        except Exception:
            return []

    def get_player(self, handle):
        try:
            return User.query.get(handle)
        except Exception:
            return None

    def update_player_status(self, player_handle, new_status):
        try:
            player = User.query.get(player_handle)
            if player:
                player.status = new_status
                sqla.session.commit()
                return True
        except Exception:
            sqla.session.rollback()
        return False

    def reset_player_rating(self, player_handle, new_elo=0):
        try:
            player = User.query.get(player_handle)
            if player:
                player.elo = int(new_elo)
                sqla.session.commit()
                return True
        except Exception:
            sqla.session.rollback()
        return False

    # --------------------------------------------------------------------------
    # METRICS & AUDIT LOGS
    # --------------------------------------------------------------------------
    @property
    def metrics(self):
        try:
            total_players = User.query.count()
            active_bookings_count = ConfirmedBooking.query.count()
            open_play_count = OpenPlaySession.query.count()
            
            # Calculate live total revenue from confirmed bookings
            confirmed_bookings = ConfirmedBooking.query.filter(ConfirmedBooking.status.in_(['Confirmed', 'confirmed'])).all()
            total_rev_val = sum(float(b.amount_paid or 0) for b in confirmed_bookings)
            
            # Count distinct players involved in bookings or open play
            active_today = User.query.filter_by(status="Active").count()
        except Exception:
            total_players = 0
            active_bookings_count = 0
            total_rev_val = 0.0
            active_today = 0

        return {
            "total_users": total_players,
            "daily_active": active_today,
            "active_bookings": active_bookings_count,
            "total_revenue": f"₱{total_rev_val:,.2f}" if total_rev_val > 0 else "₱0.00",
            "latency_history": [
                {"time": "00:00", "latency": 15},
                {"time": "04:00", "latency": 12},
                {"time": "08:00", "latency": 18},
                {"time": "12:00", "latency": 25},
                {"time": "16:00", "latency": 20},
                {"time": "20:00", "latency": 16},
            ]
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------

    @property
    def audit_logs(self):
        try:
            logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(50).all()
            return [l.to_dict() for l in logs]
        except Exception:
            return []

    @property
    def system_logs(self):
        try:
            logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(20).all()
            return [l.to_dict() for l in logs]
        except Exception:
            return []

    def add_audit_log(self, action, admin="Karl Alegrado"):
        try:
            log_entry = AuditLog(action=action, admin=admin)
            sqla.session.add(log_entry)
            sqla.session.commit()
        except Exception:
            sqla.session.rollback()

    # --------------------------------------------------------------------------
    # MODERATION & REPORTS
    # --------------------------------------------------------------------------
    @property
    def reported_players(self):
        try:
            # Derive reported players directly from User records with reports > 0 or ratings with poor behavior
            reported_users = User.query.filter(User.reports > 0).all()
            reports = []
            for idx, u in enumerate(reported_users):
                reports.append({
                    "id": f"REP-{801 + idx}",
                    "player_id": u.handle,
                    "player_name": u.name,
                    "reporter": "Community Report",
                    "reason": u.notes or "Player reported for unsportsmanlike behavior / delay.",
                    "severity": "Medium",
                    "date": "Today, 19:40",
                    "status": "Pending Action"
                })
# ---------------------------------------------------------------------------)
            return reports
        except Exception:
            return []

    def dismiss_report(self, report_id, admin="Karl Alegrado"):
        self.add_audit_log(f"Dismissed player report {report_id}", admin)
        return True, f"Report {report_id} dismissed."

    def warn_and_dismiss_report(self, report_id, admin="Karl Alegrado"):
        self.add_audit_log(f"Issued formal conduct warning for {report_id}", admin)
        return True, f"Warning issued for {report_id}."

    # --------------------------------------------------------------------------
    # EVENT POSTS & ANNOUNCEMENTS
    # --------------------------------------------------------------------------
    def get_event_posts(self):
        try:
            return EventPost.query.order_by(EventPost.created_at.desc()).all()
        except Exception:
            return []

    def create_event_post(self, title, event_type="Announcement", date=None, description="", image_url="", author="Karl Alegrado"):
        try:
            counter = EventPost.query.count() + 101
            post_id = f"EVT-{counter}"
            while EventPost.query.get(post_id):
                counter += 1
                post_id = f"EVT-{counter}"

            new_post = EventPost(
                id=post_id,
                title=title.strip(),
                event_type=event_type,
                date=date.strip() if date else datetime.now().strftime("%b %d, %Y"),
                description=description.strip() if description else "",
                image_url=image_url.strip() if image_url else "",
                author=author
            )
            sqla.session.add(new_post)
            sqla.session.commit()
            self.add_audit_log(f"Published new {event_type}: '{new_post.title}'", author)
            return new_post
        except Exception:
            sqla.session.rollback()
            return EventPost(id="EVT-ERR", title=title, event_type=event_type)

    def delete_event_post(self, post_id, admin="Karl Alegrado"):
        try:
            post = EventPost.query.get(post_id)
            if post:
                title = post.title
                sqla.session.delete(post)
                sqla.session.commit()
                self.add_audit_log(f"Removed event post '{title}' ({post_id})", admin)
                return True
        except Exception:
            sqla.session.rollback()
        return False

    # --------------------------------------------------------------------------
    # VENUE & COURT SETTINGS
    # --------------------------------------------------------------------------
    def get_court_crew_contacts(self) -> list:
        """Returns list of court crew contact persons from PlatformSetting."""
        default_crew = [
            {
                "id": "crew_1",
                "name": "Cielo Dela Cruz",
                "role": "Owner",
                "role_type": "owner",
                "status": "On Duty",
                "phone": "+639171234567",
                "phone_display": "0917 123 4567"
            },
            {
                "id": "crew_2",
                "name": "Maria Dela Cruz",
                "role": "Staff",
                "role_type": "staff",
                "status": "On Duty",
                "phone": "+639181234567",
                "phone_display": "0918 123 4567"
            },
            {
                "id": "crew_3",
                "name": "Paolo Santos",
                "role": "Staff",
                "role_type": "staff",
                "status": "On Duty",
                "phone": "+639191234567",
                "phone_display": "0919 123 4567"
            }
        ]
        try:
            setting = PlatformSetting.query.get('court_crew_contacts')
            if setting and setting.value:
                parsed = json.loads(setting.value)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed
        except Exception:
            pass
        return getattr(self, '_court_crew_contacts', default_crew)

    def set_court_crew_contacts(self, contacts: list, admin: str = "Karl Alegrado") -> bool:
        """Saves custom court crew contacts in PlatformSetting."""
        if not isinstance(contacts, list):
            return False
        self._court_crew_contacts = contacts
        try:
            setting = PlatformSetting.query.get('court_crew_contacts')
            val = json.dumps(contacts)
            if not setting:
                setting = PlatformSetting(key='court_crew_contacts', value=val)
                sqla.session.add(setting)
            else:
                setting.value = val
            sqla.session.commit()
        except Exception:
            sqla.session.rollback()
        self.add_audit_log(f"Updated court crew contact list ({len(contacts)} contacts)", admin)
        return True

    def get_court_descriptions(self) -> Dict[str, str]:
        """Returns map of court number (e.g. '1', '2') to custom description."""
        try:
            setting = PlatformSetting.query.get('court_descriptions')
            if setting and setting.value:
                parsed = json.loads(setting.value)
                if isinstance(parsed, dict):
                    return parsed
        except Exception:
            pass
        return getattr(self, '_court_descriptions', {
            "1": "Main Court",
            "2": "Air-Con Indoor",
            "3": "Outdoor Pro",
            "4": "Training Yard",
            "5": "Covered Court",
            "6": "Side Yard"
        })

    def set_court_descriptions(self, descriptions: dict, admin: str = "Karl Alegrado") -> bool:
        """Saves custom court descriptions in PlatformSetting."""
        if not isinstance(descriptions, dict):
            return False
        self._court_descriptions = descriptions
        try:
            setting = PlatformSetting.query.get('court_descriptions')
            val = json.dumps(descriptions)
            if not setting:
                setting = PlatformSetting(key='court_descriptions', value=val)
                sqla.session.add(setting)
            else:
                setting.value = val
            sqla.session.commit()
        except Exception:
            sqla.session.rollback()
        self.add_audit_log("Updated venue court descriptions", admin)
        return True

    def set_total_courts(self, count, admin="Karl Alegrado", descriptions=None):
        try:
            count = max(1, min(20, int(count)))
        except (ValueError, TypeError):
            count = 6

        self.total_courts = count
        self.courts = [f"Court {i}" for i in range(1, count + 1)]
        if self.venues:
            self.venues[0]["courts"] = count

        if descriptions is not None and isinstance(descriptions, dict):
            self.set_court_descriptions(descriptions, admin=admin)

        try:
            setting = PlatformSetting.query.get('total_courts')
            if not setting:
                setting = PlatformSetting(key='total_courts', value=str(count))
                sqla.session.add(setting)
            else:
                setting.value = str(count)
            sqla.session.commit()
        except Exception:
            sqla.session.rollback()

        self.add_audit_log(f"Updated venue court capacity to {count} courts", admin)
        return True, count

    # --------------------------------------------------------------------------
    # DIGITAL BOOKING SHEET & CONFIRMED BOOKINGS
    # --------------------------------------------------------------------------
    def get_booking_sheet_matrix(self, date):
        norm_target_date = normalize_date_str(date)
        matrix = {}
        for slot in BOOKING_TIME_SLOTS:
            matrix[slot] = {court: {"status": "vacant"} for court in self.courts}

        try:
            # 1. Load Confirmed Bookings for this date
            all_bookings = ConfirmedBooking.query.all()
            for b in all_bookings:
                if normalize_date_str(b.date) != norm_target_date:
                    continue
                c_clean = b.court_no.split(" (")[0].strip() if "(" in (b.court_no or "") else (b.court_no or "").strip()
                if c_clean in self.courts:
                    # Parse duration in hours
                    dur_hours = 1
                    if b.duration:
                        d_str = str(b.duration).strip()
                        parts = d_str.split()
                        if parts and parts[0].isdigit():
                            dur_hours = max(1, int(parts[0]))

                    norm_time = normalize_time_slot(b.time)
                    if norm_time in BOOKING_TIME_SLOTS:
                        start_idx = BOOKING_TIME_SLOTS.index(norm_time)
                        pay_status = getattr(b, 'payment_status', 'paid')
                        pay_method = getattr(b, 'payment_method', 'Cash') or 'Cash'
                        amt_paid = float(getattr(b, 'amount_paid', 0) or 0)
                        for h in range(dur_hours):
                            if start_idx + h < len(BOOKING_TIME_SLOTS):
                                slot_name = BOOKING_TIME_SLOTS[start_idx + h]
                                matrix[slot_name][c_clean] = {
                                    "status": "booked",
                                    "customer_name": b.customer_name or "Booked Player",
                                    "payment_status": pay_status,
                                    "payment_method": pay_method,
                                    "amount_paid": amt_paid,
                                    "rent_paddle": bool(getattr(b, 'rent_paddle', False)),
                                    "paddle_count": getattr(b, 'paddle_count', 0) or 0,
                                    "duration_hours": dur_hours,
                                    "start_time_slot": norm_time,
                                    "booking_id": b.id
                                }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------

            # 2. Load Open Play Sessions for this date
            all_sessions = OpenPlaySession.query.all()
            for s in all_sessions:
                if normalize_date_str(s.date) != norm_target_date:
                    continue
                # Determine which courts are used
                used_courts = []
                c_base = s.court_no.split(" (")[0].strip() if "(" in (s.court_no or "") else (s.court_no or "").strip()
                if c_base in self.courts:
                    used_courts.append(c_base)

                if s.court_count and s.court_count > 1:
                    for i in range(1, min(s.court_count + 1, len(self.courts) + 1)):
                        c_name = f"Court {i}"
                        if c_name not in used_courts and c_name in self.courts:
                            used_courts.append(c_name)

                # Determine time range in minutes
                start_min = parse_time_to_minutes(s.start_time)
                end_min = parse_time_to_minutes(s.end_time)
                if end_min <= start_min:
                    end_min = start_min + 120

                for slot in BOOKING_TIME_SLOTS:
                    slot_min = parse_time_to_minutes(slot)
                    if start_min <= slot_min < end_min:
                        for court in used_courts:
                            if matrix[slot][court].get("status") == "vacant":
                                matrix[slot][court] = {
                                    "status": "open_play",
                                    "title": s.title or "Open Play",
                                    "time_range": s.time or "",
                                    "session_id": s.id
                                }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------
        except Exception as e:
            print(f"[!] Error building booking matrix: {e}")

        return {
            "date": date,
            "time_slots": BOOKING_TIME_SLOTS,
            "courts": self.courts,
            "matrix": matrix
        }


# ---------------------------------------------------------------------------
# RANKED & SKILL LEVEL ENGINE (100% Parity with Pickle-Legends)
# ---------------------------------------------------------------------------

    def get_booking_sheet_grid(self, date, court):
        sheet_data = self.get_booking_sheet_matrix(date)
        grid = {}
        for slot in BOOKING_TIME_SLOTS:
            grid[slot] = sheet_data["matrix"][slot].get(court, {"status": "vacant"})
        return grid

    def save_direct_booking(self, date, court, time_slot, customer_name, payment_status="paid", rent_paddle=False, paddle_count=0, duration_hours=1, payment_method="Cash", amount_paid=None):
        try:
            norm_date = normalize_date_str(date)
            norm_time = normalize_time_slot(time_slot)
            dur_int = max(1, int(duration_hours))
            pay_status = "paid" if str(payment_status).lower() == "paid" else "unpaid"
            pay_method = (payment_method or "Cash").strip()

            # Calculate amount paid if not explicitly provided
            if amount_paid is not None:
                try:
                    final_amount = float(amount_paid)
                except (ValueError, TypeError):
                    final_amount = 300.0 * dur_int + (50.0 * int(paddle_count) if rent_paddle else 0.0)
            else:
                final_amount = 300.0 * dur_int + (50.0 * int(paddle_count) if rent_paddle else 0.0)

            # Check for conflicts
            matrix_data = self.get_booking_sheet_matrix(date)
            if norm_time in BOOKING_TIME_SLOTS:
                start_idx = BOOKING_TIME_SLOTS.index(norm_time)
                for h in range(dur_int):
                    if start_idx + h < len(BOOKING_TIME_SLOTS):
                        chk_slot = BOOKING_TIME_SLOTS[start_idx + h]
                        cell = matrix_data["matrix"][chk_slot].get(court, {})
                        if cell.get("status") == "open_play":
                            return False, f"Cannot book: {court} at {chk_slot} is reserved for Open Play ({cell.get('title')})."
                        elif cell.get("status") == "booked" and cell.get("start_time_slot") != norm_time:
                            return False, f"Cannot book: {court} at {chk_slot} is already booked by {cell.get('customer_name')}."

            # Delete any existing booking starting at this slot to support editing/updating
            existing = ConfirmedBooking.query.all()
            for eb in existing:
                if normalize_date_str(eb.date) == norm_date:
                    c_clean = eb.court_no.split(" (")[0].strip() if "(" in (eb.court_no or "") else (eb.court_no or "").strip()
                    if c_clean == court and normalize_time_slot(eb.time) == norm_time:
                        sqla.session.delete(eb)
                        sqla.session.flush()
                        break

            b_id = f"BK-{int(time.time() * 1000) % 10000}"
            booking = ConfirmedBooking(
                id=b_id,
                court="Butuan Ground Zero Pickleball Yard",
                court_no=court,
                customer_name=customer_name.strip(),
                date=norm_date,
                time=norm_time,
                duration=f"{dur_int} hr{'s' if dur_int > 1 else ''}",
                amount_paid=final_amount,
                payment_method=pay_method,
                staff_name="Karl Alegrado",
                status="Confirmed" if pay_status == "paid" else "Unpaid",
                flow_type="direct",
                rent_paddle=bool(rent_paddle),
                paddle_count=int(paddle_count) if rent_paddle else 0
            )
            sqla.session.add(booking)
            sqla.session.commit()
            self.add_audit_log(f"Saved confirmed booking {b_id} for '{customer_name}' on {court} at {norm_time} ({pay_method} • ₱{final_amount:,.2f})")
            return True, f"Booking for '{customer_name}' on {court} saved successfully!"
        except Exception as e:
            sqla.session.rollback()
            return False, f"Failed to save booking: {str(e)}"

    def clear_direct_booking(self, date, court, time_slot):
        try:
            norm_date = normalize_date_str(date)
            norm_time = normalize_time_slot(time_slot)
            bookings = ConfirmedBooking.query.all()
            target_booking = None
            for b in bookings:
                if normalize_date_str(b.date) == norm_date:
                    c_clean = b.court_no.split(" (")[0].strip() if "(" in (b.court_no or "") else (b.court_no or "").strip()
                    if c_clean == court and normalize_time_slot(b.time) == norm_time:
                        target_booking = b
                        break

            if target_booking:
                c_name = target_booking.customer_name
                sqla.session.delete(target_booking)
                sqla.session.commit()
                self.add_audit_log(f"Cancelled booking for '{c_name}' on {court} at {norm_time}")
                return True, f"Booking for '{c_name}' cleared."
            return False, "No active booking found for this slot."
        except Exception as e:
            sqla.session.rollback()
            return False, f"Failed to clear booking: {str(e)}"

    # --------------------------------------------------------------------------
    # OPEN PLAY SESSIONS & FAIR ROTATIONS
    # --------------------------------------------------------------------------
    def get_open_play_sessions(self):
        try:
            return OpenPlaySession.query.order_by(OpenPlaySession.created_at.desc()).all()
        except Exception:
            return []

    def get_session(self, session_id):
        try:
            return OpenPlaySession.query.get(session_id)
        except Exception:
            return None

    def get_session_participants(self, session_id):
        try:
            return SessionParticipant.query.filter_by(session_id=session_id).order_by(SessionParticipant.joined_at.asc()).all()
        except Exception:
            return []

    def create_open_play_session(self, title, date, start_time, end_time, court_count=3, max_players=8):
        try:
            s_id = f"op_{OpenPlaySession.query.count() + 1}"
            while OpenPlaySession.query.get(s_id):
                s_id = f"op_{int(time.time() * 1000) % 10000}"

            time_str = f"{start_time} - {end_time}"
            new_session = OpenPlaySession(
                id=s_id,
                title=title.strip(),
                date=date.strip(),
                time=time_str,
                court="Butuan Ground Zero Pickleball Yard",
                court_no="Court 1 (Main Court)",
                staff_name="Karl Alegrado",
                host_name="Zask Paddler",
                host_handle="zask_game",
                host_initials="ZP",
                match_format="Doubles 2v2 Round Robin",
                skill_level="Intermediate (3.0 - 3.5)",
                max_players=int(max_players),
                court_count=int(court_count),
                status="open"
            )
            sqla.session.add(new_session)
            sqla.session.commit()
            self.add_audit_log(f"Created Open Play Session '{title}' ({s_id})")
            return new_session
        except Exception:
            sqla.session.rollback()
            return None

    def confirm_participant_payment(self, participant_id, admin="Karl Alegrado"):
        try:
            part = SessionParticipant.query.get(participant_id)
            if part:
                part.payment_status = "paid"
                sqla.session.commit()
                self.add_audit_log(f"Confirmed payment for Participant {participant_id} ({part.player_name})", admin)
                return True, f"Payment confirmed for {part.player_name}."
        except Exception:
            sqla.session.rollback()
        return False, "Participant not found."

    def remove_participant(self, participant_id, admin="Karl Alegrado"):
        try:
            part = SessionParticipant.query.get(participant_id)
            if part:
                pname = part.player_name
                sqla.session.delete(part)
                sqla.session.commit()
                self.add_audit_log(f"Removed participant {participant_id} ({pname})", admin)
                return True, f"Removed {pname} from session."
        except Exception:
            sqla.session.rollback()
        return False, "Participant not found."


# Global Singleton Instance
db = DatabaseManager()
