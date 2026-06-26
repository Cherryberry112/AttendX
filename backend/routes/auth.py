import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from __init__ import db
from models import User, Teacher, Student

auth_bp = Blueprint("auth", __name__)

# ── Helper ──────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _check(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ── Routes ──────────────────────────────────────────────────────────────────

@auth_bp.post("/register")
def register():
    data = request.get_json()
    required = ["name", "email", "password", "role"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    role = data["role"].lower()
    if role not in ("admin", "teacher", "student"):
        return jsonify({"error": "Invalid role"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        name=data["name"],
        email=data["email"],
        password=_hash(data["password"]),
        role=role,
    )
    db.session.add(user)
    db.session.flush()  # get user.id before commit

    if role == "teacher":
        profile = Teacher(user_id=user.id, department=data.get("department"), phone=data.get("phone"))
        db.session.add(profile)
    elif role == "student":
        if not data.get("student_id"):
            return jsonify({"error": "student_id is required for students"}), 400
        if Student.query.filter_by(student_id=data["student_id"]).first():
            return jsonify({"error": "Student ID already exists"}), 409
        profile = Student(
            user_id=user.id,
            student_id=data["student_id"],
            department=data.get("department"),
            batch=data.get("batch"),
        )
        db.session.add(profile)

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

    identity = {"id": user.id, "role": user.role, "name": user.name}
    token = create_access_token(identity=identity)
    return jsonify({"token": token, "role": user.role, "name": user.name, "id": user.id}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    identity = get_jwt_identity()
    user = User.query.get(identity["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"id": user.id, "name": user.name, "email": user.email, "role": user.role}), 200
