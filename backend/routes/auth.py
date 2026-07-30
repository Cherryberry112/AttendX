import re
import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from __init__ import db
from models import User

auth_bp = Blueprint("auth", __name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

STUDENT_ID_REGEX = re.compile(r"^\d{4}-\d{1,2}-\d{2}-\d{3}$")

def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _check(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ── Routes ───────────────────────────────────────────────────────────────────

@auth_bp.post("/register")
def register():
    data = request.get_json()
    required = ["username", "email", "password", "type"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    user_type = data["type"].lower()
    if user_type not in ("admin", "teacher", "student"):
        return jsonify({"error": "Invalid user type"}), 400

    # Duplicate email check
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    # Student-specific validations
    student_id = None
    guardian_number = None
    if user_type == "student":
        student_id = data.get("student_id", "").strip()
        if not student_id:
            return jsonify({"error": "Student ID is required for students"}), 400
        if not STUDENT_ID_REGEX.match(student_id):
            return jsonify({"error": "Student ID must be in format YYYY-D-DD-DDD (e.g. 2022-3-60-110)"}), 400
        if User.query.filter_by(student_id=student_id).first():
            return jsonify({"error": "Student ID already exists"}), 409
        guardian_number = data.get("guardian_number", "").strip() or None

    user = User(
        type=user_type,
        username=data["username"],
        email=data["email"],
        password=_hash(data["password"]),
        phone=data.get("phone", "").strip() or None,
        student_id=student_id,
        guardian_number=guardian_number,
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User registered successfully", "id": user.id}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=data["email"]).first()
    if not user or not _check(data["password"], user.password):
        return jsonify({"error": "Invalid credentials"}), 401

    identity = {"id": user.id, "type": user.type, "username": user.username}
    token = create_access_token(identity=identity)

    # Send welcome login email asynchronously (non-blocking)
    try:
        from utils.notifications import send_welcome_email
        send_welcome_email(user.username, user.email, user.type)
    except Exception as e:
        print(f"[EMAIL] Welcome email skipped: {e}")

    return jsonify({
        "token": token,
        "type": user.type,
        "username": user.username,
        "id": user.id,
    }), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    identity = get_jwt_identity()
    user = User.query.get(identity["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "type": user.type,
        "phone": user.phone,
        "student_id": user.student_id,
        "guardian_number": user.guardian_number,
    }), 200
