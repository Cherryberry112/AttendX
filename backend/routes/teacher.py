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
    
    courses_list = [{
        "id": c.id,
        "name": c.name,
        "enrolled": c.students.count()
    } for c in teacher.taught_courses]

    return jsonify({
        "id": teacher.id,
        "username": teacher.username,
        "email": teacher.email,
        "phone": teacher.phone,
        "total_courses": len(courses_list),
        "courses": courses_list,
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


# ── My Students & Attendance Matrix ──────────────────────────────────────────

@teacher_bp.get("/students")
@jwt_required()
def get_teacher_students():
    """Get all distinct students enrolled across courses taught by the teacher."""
    try:
        identity = get_jwt_identity()
        teacher = _get_teacher(identity)
        if not teacher:
            return jsonify({"error": "Teacher not found"}), 404

        courses = teacher.taught_courses.all()
        if not courses:
            return jsonify([]), 200

        students_dict = {}
        for c in courses:
            for s in c.students.all():
                if s.id not in students_dict:
                    students_dict[s.id] = {
                        "id": s.id,
                        "student_id": s.student_id or f"STU-{s.id:04d}",
                        "username": s.username,
                        "email": s.email,
                        "courses": [],
                        "total_classes": 0,
                        "attended_classes": 0,
                    }
                students_dict[s.id]["courses"].append({"id": c.id, "name": c.name})

        for sid, sdata in students_dict.items():
            s_course_ids = [c["id"] for c in sdata["courses"]]
            total_sessions = (db.session.query(db.func.count(db.distinct(Attendance.date)))
                              .filter(Attendance.course_id.in_(s_course_ids)).scalar()) or 0
            attended_sessions = (db.session.query(db.func.count(Attendance.id))
                                 .filter(Attendance.student_id == sid, Attendance.course_id.in_(s_course_ids)).scalar()) or 0

            sdata["total_classes"] = total_sessions
            sdata["attended_classes"] = attended_sessions
            sdata["attendance_percentage"] = round((attended_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0.0

        return jsonify(list(students_dict.values())), 200
    except Exception as e:
        print(f"[ERROR] get_teacher_students failed: {e}")
        return jsonify({"error": str(e)}), 500


@teacher_bp.get("/courses/<int:course_id>/matrix")
@jwt_required()
def get_course_matrix(course_id):
    """Get student-by-session-date matrix for full course attendance export."""
    try:
        identity = get_jwt_identity()
        teacher = _get_teacher(identity)
        if not teacher:
            return jsonify({"error": "Teacher not found"}), 404
        course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
        if not course:
            return jsonify({"error": "Course not found"}), 404

        students = course.students.order_by(User.username).all()
        dates_query = (db.session.query(Attendance.date)
                       .filter(Attendance.course_id == course_id)
                       .distinct()
                       .order_by(Attendance.date.asc())
                       .all())
        dates = [str(d[0]) for d in dates_query]

        attendance_records = Attendance.query.filter_by(course_id=course_id).all()
        att_map = set((rec.student_id, str(rec.date)) for rec in attendance_records)

        student_matrix = []
        for s in students:
            s_att = {}
            present_count = 0
            for d_str in dates:
                is_present = (s.id, d_str) in att_map
                s_att[d_str] = "P" if is_present else "A"
                if is_present:
                    present_count += 1

            total_sessions = len(dates)
            pct = round((present_count / total_sessions * 100), 1) if total_sessions > 0 else 0.0
            student_matrix.append({
                "id": s.id,
                "student_id": s.student_id or f"STU-{s.id:04d}",
                "username": s.username,
                "email": s.email,
                "attendance": s_att,
                "total_attended": present_count,
                "total_sessions": total_sessions,
                "percentage": pct
            })

        return jsonify({
            "course": {"id": course.id, "name": course.name},
            "dates": dates,
            "students": student_matrix
        }), 200
    except Exception as e:
        print(f"[ERROR] get_course_matrix failed: {e}")
        return jsonify({"error": str(e)}), 500

