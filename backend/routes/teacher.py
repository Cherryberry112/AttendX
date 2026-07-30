from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Course, Attendance, course_students

teacher_bp = Blueprint("teacher", __name__)

def _get_teacher(identity):
    """Return User object if identity is a teacher."""
    user = User.query.filter_by(id=identity["id"], type="teacher").first()
    return user

# ── Profile ──────────────────────────────────────────────────────────────────

@teacher_bp.get("/profile")
@jwt_required()
def get_profile():
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    if not teacher:
        return jsonify({"error": "Teacher profile not found"}), 404
    return jsonify({
        "id": teacher.id,
        "username": teacher.username,
        "email": teacher.email,
        "phone": teacher.phone,
        "total_courses": teacher.taught_courses.count(),
    }), 200


@teacher_bp.put("/profile")
@jwt_required()
def update_profile():
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    if not teacher:
        return jsonify({"error": "Teacher profile not found"}), 404
    data = request.get_json()
    if "username" in data: teacher.username = data["username"]
    if "phone" in data:    teacher.phone = data["phone"]
    db.session.commit()
    return jsonify({"message": "Profile updated"}), 200

# ── Courses (Read-Only for teacher) ──────────────────────────────────────────

@teacher_bp.get("/courses")
@jwt_required()
def get_courses():
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404
    courses = []
    for c in teacher.taught_courses:
        enrolled = c.students.count()
        total_classes = (db.session.query(db.func.count(db.distinct(Attendance.date)))
                         .filter(Attendance.course_id == c.id).scalar()) or 0
        courses.append({
            "id": c.id, "name": c.name,
            "enrolled": enrolled, "total_classes": total_classes,
        })
    return jsonify(courses), 200


@teacher_bp.get("/courses/<int:course_id>")
@jwt_required()
def get_course_detail(course_id):
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404
    course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404

    # Enrolled students
    students_list = []
    for s in course.students:
        face_ok = s.face_embedding is not None and s.face_embedding != ""
        students_list.append({
            "id": s.id,
            "student_id": s.student_id,
            "username": s.username,
            "face_enrolled": face_ok,
        })

    # Attendance dates + per-date summary
    dates = (db.session.query(Attendance.date, db.func.count(Attendance.id))
             .filter(Attendance.course_id == course_id)
             .group_by(Attendance.date)
             .order_by(Attendance.date.desc())
             .all())
    total_enrolled = course.students.count()
    sessions = [{"date": str(d), "present": cnt, "total": total_enrolled} for d, cnt in dates]

    return jsonify({
        "course": {"id": course.id, "name": course.name},
        "students": students_list,
        "sessions": sessions,
    }), 200

# ── Take Attendance ──────────────────────────────────────────────────────────

@teacher_bp.post("/courses/<int:course_id>/attendance")
@jwt_required()
def record_attendance(course_id):
    """Record attendance for enrolled students.
    Body: { "date": "2026-07-28", "present_ids": [3, 5, 7] }
    """
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404
    course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404

    data = request.get_json()
    att_date = data.get("date", str(date.today()))
    present_ids = data.get("present_ids", [])

    recorded = 0
    for sid in present_ids:
        # Only allow enrolled students
        is_enrolled = db.session.query(course_students).filter_by(
            course_id=course_id, student_id=sid).first()
        if not is_enrolled:
            continue
        # Upsert attendance
        existing = Attendance.query.filter_by(
            date=att_date, student_id=sid, course_id=course_id).first()
        if not existing:
            db.session.add(Attendance(date=att_date, student_id=sid, course_id=course_id))
            recorded += 1

    db.session.commit()

    # Send attendance confirmation emails to present students (async, non-blocking)
    try:
        from utils.notifications import notify_students_attendance
        notify_students_attendance(present_ids, course.name, att_date, teacher.username)
    except Exception as e:
        print(f"[EMAIL] Attendance notification skipped: {e}")

    return jsonify({"message": f"Attendance recorded: {recorded} students", "recorded": recorded}), 201
