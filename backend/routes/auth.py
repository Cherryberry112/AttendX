import re
import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from __init__ import db
from models import User, Notification

auth_bp = Blueprint("auth", __name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

STUDENT_ID_REGEX = re.compile(r"^\d{4}-\d{1,2}-\d{2}-\d{3}$")
EMAIL_REGEX      = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _check(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def _valid_email(email: str) -> bool:
    return bool(email) and bool(EMAIL_REGEX.match(email.strip()))

# ── Routes ────────────────────────────────────────────────────────────────────

@auth_bp.post("/register")
def register():
    data = request.get_json() or {}

    # ── Mandatory fields ──
    username = (data.get("username") or "").strip()
    email    = (data.get("email")    or "").strip()
    password = (data.get("password") or "")
    user_type = (data.get("type")   or "").strip().lower()

    if not username:
        return jsonify({"error": "Full name is required"}), 400
    if not email:
        return jsonify({"error": "Email is required"}), 400
    if not _valid_email(email):
        return jsonify({"error": "Please enter a valid email address"}), 400
    if not password:
        return jsonify({"error": "Password is required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    # ── Role — only teacher or student allowed ──
    if user_type not in ("teacher", "student"):
        return jsonify({"error": "Registration is only available for teachers and students"}), 400

    # ── Duplicate email check ──
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # ── Student-specific validations (student_id mandatory, guardian optional) ──
    student_id      = None
    guardian_number = None
    if user_type == "student":
        student_id = (data.get("student_id") or "").strip()
        if not student_id:
            return jsonify({"error": "Student ID is required for students"}), 400
        if not STUDENT_ID_REGEX.match(student_id):
            return jsonify({"error": "Student ID must be in format YYYY-D-DD-DDD (e.g. 2022-3-60-110)"}), 400
        if User.query.filter_by(student_id=student_id).first():
            return jsonify({"error": "Student ID already exists"}), 409
        guardian_number = (data.get("guardian_number") or "").strip() or None

    # ── Create user ──
    user = User(
        type=user_type,
        username=username,
        email=email,
        password=_hash(password),
        phone=(data.get("phone") or "").strip() or None,
        student_id=student_id,
        guardian_number=guardian_number,
    )
    db.session.add(user)
    db.session.commit()

    # ── Send welcome email (non-blocking, only to valid addresses) ──
    try:
        from utils.notifications import send_registration_email
        send_registration_email(user.username, user.email, user.type)
    except Exception as exc:
        print(f"[EMAIL] Registration email error: {exc}")

    return jsonify({"message": "Account created successfully", "id": user.id}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=data["email"].strip()).first()
    if not user or not _check(data["password"], user.password):
        return jsonify({"error": "Invalid credentials"}), 401

    identity = {"id": user.id, "type": user.type, "username": user.username}
    token = create_access_token(identity=identity)
    return jsonify({
        "token":    token,
        "type":     user.type,
        "username": user.username,
        "id":       user.id,
    }), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    identity = get_jwt_identity()
    user = User.query.get(identity["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id":               user.id,
        "username":         user.username,
        "email":            user.email,
        "type":             user.type,
        "phone":            user.phone,
        "student_id":       user.student_id,
        "guardian_number":  user.guardian_number,
    }), 200


@auth_bp.get("/test-email")
def test_email():
    """Debug: GET /api/auth/test-email?to=your@email.com — shows exact error on failure."""
    import os
    to = request.args.get("to", "").strip()
    if not to:
        return jsonify({"error": "Pass ?to=your@email.com"}), 400

    sender   = os.environ.get("MAIL_SENDER", "")
    brevo    = os.environ.get("BREVO_API_KEY", "")
    password = os.environ.get("MAIL_APP_PASSWORD", "").replace(" ", "")

    if not brevo and (not sender or not password):
        return jsonify({
            "error": "No email credentials found — set BREVO_API_KEY in Render",
            "BREVO_API_KEY":  "(empty)",
            "MAIL_SENDER":    sender or "(empty)",
        }), 500

    from utils.notifications import _send
    ok, err = _send(to, "AttendX Email Test", "<h2>It works!</h2><p>Email configured correctly.</p>")
    if ok:
        return jsonify({"status": "sent", "to": to, "from": sender}), 200
    else:
        return jsonify({
            "status": "failed",
            "error":  err,
            "MAIL_SENDER": sender,
        }), 500

# ── Notifications ─────────────────────────────────────────────────────────────

@auth_bp.get("/notifications")
@jwt_required()
def get_notifications():
    identity = get_jwt_identity()
    notifs = Notification.query.filter_by(user_id=identity["id"]).order_by(Notification.created_at.desc()).all()
    result = []
    for n in notifs:
        result.append({
            "id": n.id,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": str(n.created_at)
        })
    return jsonify(result), 200

@auth_bp.post("/notifications/read_all")
@jwt_required()
def read_all_notifications():
    identity = get_jwt_identity()
    Notification.query.filter_by(user_id=identity["id"], is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "Notifications marked as read"}), 200
