import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Course, Attendance, CourseRequest

student_bp = Blueprint("student", __name__)

def _get_student(identity):
    return User.query.filter_by(id=identity["id"], type="student").first()


@student_bp.get("/profile")
@jwt_required()
def get_profile():
    identity = get_jwt_identity()
    student = _get_student(identity)
    if not student:
        return jsonify({"error": "Student profile not found"}), 404
    face_ok = student.face_embedding is not None and student.face_embedding != ""
    return jsonify({
        "id": student.id,
        "username": student.username,
        "email": student.email,
        "student_id": student.student_id,
        "phone": student.phone,
        "guardian_number": student.guardian_number,
        "face_enrolled": face_ok,
        "total_courses": student.enrolled_courses.count(),
    }), 200


@student_bp.put("/profile")
@jwt_required()
def update_profile():
    identity = get_jwt_identity()
    student = _get_student(identity)
    if not student:
        return jsonify({"error": "Student profile not found"}), 404
    
    data = request.get_json()
    
    current_password = data.get("current_password")
    if not current_password:
        return jsonify({"error": "Current password is required to save changes"}), 400
        
    if not bcrypt.checkpw(current_password.encode(), student.password.encode()):
        return jsonify({"error": "Incorrect current password"}), 403

    if "username" in data: 
        student.username = data["username"]
    if "phone" in data:    
        student.phone = data["phone"]
    
    db.session.commit()
    return jsonify({"message": "Profile updated"}), 200


@student_bp.get("/courses")
@jwt_required()
def get_courses():
    identity = get_jwt_identity()
    student = _get_student(identity)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    result = []
    for course in student.enrolled_courses:
        # Total unique class dates for this course
        total_classes = (db.session.query(db.func.count(db.distinct(Attendance.date)))
                         .filter(Attendance.course_id == course.id).scalar()) or 0
        # How many this student attended
        attended = (Attendance.query
                    .filter_by(course_id=course.id, student_id=student.id)
                    .count())
        pct = round((attended / total_classes * 100) if total_classes else 0, 1)
        teacher_name = course.teacher.username if course.teacher else "N/A"
        result.append({
            "id": course.id,
            "name": course.name,
            "section": course.section,
            "teacher": teacher_name,
            "total_classes": total_classes,
            "attended": attended,
            "percentage": pct,
        })
    return jsonify(result), 200

@student_bp.get("/courses/available")
@jwt_required()
def get_available_courses():
    identity = get_jwt_identity()
    student = _get_student(identity)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    enrolled_ids = [c.id for c in student.enrolled_courses]
    # Also exclude courses they already requested
    requested_ids = [r.course_id for r in student.course_requests if r.status == "pending"]
    
    exclude_ids = enrolled_ids + requested_ids
    available = Course.query.filter(~Course.id.in_(exclude_ids) if exclude_ids else True).all()
    
    result = []
    for c in available:
        teacher_name = c.teacher.username if c.teacher else "Unassigned"
        result.append({
            "id": c.id,
            "name": c.name,
            "section": c.section,
            "teacher": teacher_name
        })
    return jsonify(result), 200

@student_bp.post("/requests")
@jwt_required()
def request_course():
    identity = get_jwt_identity()
    student = _get_student(identity)
    if not student:
        return jsonify({"error": "Student not found"}), 404
        
    data = request.get_json()
    course_id = data.get("course_id")
    if not course_id:
        return jsonify({"error": "Course ID required"}), 400
        
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
        
    # Check if already enrolled
    if course in student.enrolled_courses:
        return jsonify({"error": "Already enrolled"}), 400
        
    # Check if request already pending
    existing = CourseRequest.query.filter_by(user_id=student.id, course_id=course.id, status="pending").first()
    if existing:
        return jsonify({"error": "Request already pending"}), 400
        
    req = CourseRequest(user_id=student.id, course_id=course.id, status="pending")
    db.session.add(req)
    db.session.commit()
    
    return jsonify({"message": "Course requested successfully"}), 201


@student_bp.delete("/courses/<int:course_id>/unenroll")
@jwt_required()
def unenroll_course(course_id):
    identity = get_jwt_identity()
    student = _get_student(identity)
    if not student:
        return jsonify({"error": "Student not found"}), 404
        
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
        
    if course in student.enrolled_courses:
        student.enrolled_courses.remove(course)
        # Also remove attendance records for this student and course
        Attendance.query.filter_by(student_id=student.id, course_id=course.id).delete()
        db.session.commit()
        return jsonify({"message": "Successfully unenrolled from course"}), 200
    
    return jsonify({"error": "Not enrolled in this course"}), 400
