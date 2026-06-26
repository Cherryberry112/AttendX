from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import Teacher, Course, Student, Enrollment, AttendanceSession, AttendanceRecord
from utils.excel import generate_attendance_excel
import io

teacher_bp = Blueprint("teacher", __name__)

def _get_teacher(identity):
    return Teacher.query.filter_by(user_id=identity["id"]).first()

# ── Profile ──────────────────────────────────────────────────────────────────

@teacher_bp.get("/profile")
@jwt_required()
def get_profile():
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    if not teacher:
        return jsonify({"error": "Teacher profile not found"}), 404
    u = teacher.user
    return jsonify({
        "id": teacher.id, "name": u.name, "email": u.email,
        "department": teacher.department, "phone": teacher.phone,
        "total_courses": teacher.courses.count(),
    }), 200


@teacher_bp.put("/profile")
@jwt_required()
def update_profile():
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    if not teacher:
        return jsonify({"error": "Teacher profile not found"}), 404
    data = request.get_json()
    u = teacher.user
    if "name" in data:       u.name = data["name"]
    if "department" in data: teacher.department = data["department"]
    if "phone" in data:      teacher.phone = data["phone"]
    db.session.commit()
    return jsonify({"message": "Profile updated"}), 200

# ── Courses ──────────────────────────────────────────────────────────────────

@teacher_bp.get("/courses")
@jwt_required()
def get_courses():
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404
    courses = []
    for c in teacher.courses:
        enrolled = c.enrollments.count()
        sessions = c.sessions.filter_by(status="confirmed").count()
        courses.append({"id": c.id, "name": c.name, "code": c.code,
                        "enrolled": enrolled, "sessions": sessions})
    return jsonify(courses), 200


@teacher_bp.post("/courses")
@jwt_required()
def add_course():
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404
    data = request.get_json()
    if not data.get("name") or not data.get("code"):
        return jsonify({"error": "Course name and code required"}), 400
    if Course.query.filter_by(code=data["code"]).first():
        return jsonify({"error": "Course code already exists"}), 409
    course = Course(name=data["name"], code=data["code"], teacher_id=teacher.id)
    db.session.add(course)
    db.session.commit()
    return jsonify({"message": "Course created", "id": course.id}), 201


@teacher_bp.get("/courses/<int:course_id>")
@jwt_required()
def get_course_detail(course_id):
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404

    enrollments = []
    for e in course.enrollments:
        s = e.student
        u = s.user
        enrollments.append({
            "student_id": s.id, "sid": s.student_id,
            "name": u.name, "face_enrolled": s.face_enrolled,
        })

    sessions = []
    for sess in course.sessions.order_by(AttendanceSession.date.desc()):
        present = AttendanceRecord.query.filter_by(session_id=sess.id, present=True).count()
        total   = AttendanceRecord.query.filter_by(session_id=sess.id).count()
        sessions.append({"id": sess.id, "date": str(sess.date),
                         "status": sess.status, "present": present, "total": total})

    return jsonify({"course": {"id": course.id, "name": course.name, "code": course.code},
                    "enrollments": enrollments, "sessions": sessions}), 200

# ── Enroll student into course ───────────────────────────────────────────────

@teacher_bp.post("/courses/<int:course_id>/enroll")
@jwt_required()
def enroll_student(course_id):
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404
    data = request.get_json()
    student = Student.query.filter_by(student_id=data.get("student_id")).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    if Enrollment.query.filter_by(student_id=student.id, course_id=course_id).first():
        return jsonify({"error": "Already enrolled"}), 409
    db.session.add(Enrollment(student_id=student.id, course_id=course_id))
    db.session.commit()
    return jsonify({"message": "Student enrolled"}), 201

# ── Attendance Sessions ──────────────────────────────────────────────────────

@teacher_bp.post("/courses/<int:course_id>/sessions")
@jwt_required()
def create_session(course_id):
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404
    sess = AttendanceSession(course_id=course_id, teacher_id=teacher.id, status="draft")
    db.session.add(sess)
    db.session.flush()
    # Pre-populate with enrolled students (all absent by default)
    for e in course.enrollments:
        db.session.add(AttendanceRecord(session_id=sess.id, student_id=e.student_id, present=False))
    db.session.commit()
    return jsonify({"session_id": sess.id}), 201


@teacher_bp.put("/sessions/<int:session_id>")
@jwt_required()
def update_session(session_id):
    """Update attendance records in draft and optionally confirm the session."""
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    sess = AttendanceSession.query.get(session_id)
    if not sess or sess.teacher_id != teacher.id:
        return jsonify({"error": "Session not found"}), 404
    if sess.status == "confirmed":
        return jsonify({"error": "Session already confirmed"}), 400

    data = request.get_json()
    # records: [{student_id: X, present: true/false}, ...]
    for rec in data.get("records", []):
        ar = AttendanceRecord.query.filter_by(session_id=session_id, student_id=rec["student_id"]).first()
        if ar:
            ar.present = rec.get("present", False)
            ar.confidence = rec.get("confidence")

    if data.get("confirm"):
        sess.status = "confirmed"

    db.session.commit()
    return jsonify({"message": "Session updated"}), 200


@teacher_bp.get("/sessions/<int:session_id>")
@jwt_required()
def get_session(session_id):
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    sess = AttendanceSession.query.get(session_id)
    if not sess or sess.teacher_id != teacher.id:
        return jsonify({"error": "Session not found"}), 404
    records = []
    for ar in sess.records:
        s = ar.student
        u = s.user if s else None
        records.append({
            "student_id": ar.student_id,
            "sid": s.student_id if s else None,
            "name": u.name if u else "Unknown",
            "present": ar.present,
            "confidence": ar.confidence,
        })
    return jsonify({"session": {"id": sess.id, "date": str(sess.date), "status": sess.status},
                    "records": records}), 200

# ── Excel Export ─────────────────────────────────────────────────────────────

@teacher_bp.get("/courses/<int:course_id>/excel")
@jwt_required()
def download_excel(course_id):
    identity = get_jwt_identity()
    teacher = _get_teacher(identity)
    course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404
    buf = generate_attendance_excel(course)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"{course.code}_attendance.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
