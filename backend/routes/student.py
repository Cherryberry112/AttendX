from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Student, Enrollment, AttendanceRecord, AttendanceSession, Course

student_bp = Blueprint("student", __name__)

def _get_student(identity):
    return Student.query.filter_by(user_id=identity["id"]).first()

@student_bp.get("/profile")
@jwt_required()
def get_profile():
    identity = get_jwt_identity()
    student = _get_student(identity)
    if not student:
        return jsonify({"error": "Student profile not found"}), 404
    u = student.user
    return jsonify({
        "id": student.id,
        "name": u.name,
        "email": u.email,
        "student_id": student.student_id,
        "department": student.department,
        "batch": student.batch,
        "face_enrolled": student.face_enrolled,
        "total_courses": student.enrollments.count(),
    }), 200


@student_bp.get("/courses")
@jwt_required()
def get_courses():
    identity = get_jwt_identity()
    student = _get_student(identity)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    result = []
    for e in student.enrollments:
        course = e.course
        total_sessions = AttendanceSession.query.filter_by(
            course_id=course.id, status="confirmed").count()
        attended = (
            AttendanceRecord.query
            .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
            .filter(
                AttendanceSession.course_id == course.id,
                AttendanceSession.status == "confirmed",
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.present == True,
            ).count()
        )
        pct = round((attended / total_sessions * 100) if total_sessions else 0, 1)
        teacher_name = course.teacher.user.name if course.teacher else "N/A"
        result.append({
            "id": course.id,
            "name": course.name,
            "code": course.code,
            "teacher": teacher_name,
            "total_sessions": total_sessions,
            "attended": attended,
            "percentage": pct,
        })
    return jsonify(result), 200
