from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Teacher, Student, Course, Enrollment, AttendanceSession, AttendanceRecord, ActivityLog
import bcrypt, json

admin_bp = Blueprint("admin", __name__)

def _require_admin(identity):
    return identity.get("role") == "admin"

# ── Dashboard Stats ──────────────────────────────────────────────────────────

@admin_bp.get("/stats")
@jwt_required()
def stats():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({
        "total_users":    User.query.count(),
        "total_students": Student.query.count(),
        "total_teachers": Teacher.query.count(),
        "total_courses":  Course.query.count(),
        "total_sessions": AttendanceSession.query.filter_by(status="confirmed").count(),
    }), 200

# ── Users CRUD ───────────────────────────────────────────────────────────────

@admin_bp.get("/users")
@jwt_required()
def list_users():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{"id": u.id, "name": u.name, "email": u.email, "role": u.role,
                     "created_at": str(u.created_at)} for u in users]), 200


@admin_bp.post("/users")
@jwt_required()
def create_user():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    # Delegate to auth register logic
    from routes.auth import register
    return register()


@admin_bp.delete("/users/<int:user_id>")
@jwt_required()
def delete_user(user_id):
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"}), 200

# ── Courses ──────────────────────────────────────────────────────────────────

@admin_bp.get("/courses")
@jwt_required()
def list_courses():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    courses = Course.query.order_by(Course.created_at.desc()).all()
    result = []
    for c in courses:
        teacher_name = c.teacher.user.name if c.teacher else "Unassigned"
        result.append({"id": c.id, "name": c.name, "code": c.code,
                        "teacher": teacher_name, "enrolled": c.enrollments.count()})
    return jsonify(result), 200


@admin_bp.delete("/courses/<int:course_id>")
@jwt_required()
def delete_course(course_id):
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    db.session.delete(course)
    db.session.commit()
    return jsonify({"message": "Course deleted"}), 200

# ── Attendance Log ────────────────────────────────────────────────────────────

@admin_bp.get("/attendance")
@jwt_required()
def attendance_log():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    sessions = AttendanceSession.query.order_by(AttendanceSession.created_at.desc()).limit(100).all()
    result = []
    for s in sessions:
        present = AttendanceRecord.query.filter_by(session_id=s.id, present=True).count()
        total   = AttendanceRecord.query.filter_by(session_id=s.id).count()
        result.append({
            "id": s.id, "course": s.course.name if s.course else "N/A",
            "course_code": s.course.code if s.course else "",
            "teacher": s.teacher.user.name if s.teacher else "N/A",
            "date": str(s.date), "status": s.status,
            "present": present, "total": total,
        })
    return jsonify(result), 200
