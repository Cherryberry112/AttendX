import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Course, Attendance, course_students, CourseRequest, Notification

admin_bp = Blueprint("admin", __name__)

def _require_admin(identity):
    return identity.get("type") == "admin"

# ── Dashboard Stats ──────────────────────────────────────────────────────────

@admin_bp.get("/stats")
@jwt_required()
def stats():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({
        "total_users":    User.query.count(),
        "total_students": User.query.filter_by(type="student").count(),
        "total_teachers": User.query.filter_by(type="teacher").count(),
        "total_courses":  Course.query.count(),
        "total_attendance": Attendance.query.count(),
    }), 200

# ── Users CRUD ───────────────────────────────────────────────────────────────

@admin_bp.get("/users")
@jwt_required()
def list_users():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{
        "id": u.id, "username": u.username, "email": u.email, "type": u.type,
        "student_id": u.student_id, "phone": u.phone,
        "guardian_number": u.guardian_number,
        "created_at": str(u.created_at),
    } for u in users]), 200


@admin_bp.post("/users")
@jwt_required()
def create_user():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    # Delegate to auth register logic
    from routes.auth import register
    return register()


@admin_bp.put("/users/<int:user_id>")
@jwt_required()
def update_user(user_id):
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.get_json()
    if "username" in data:        user.username = data["username"]
    if "email" in data:           user.email = data["email"]
    if "phone" in data:           user.phone = data["phone"]
    if "student_id" in data:      user.student_id = data["student_id"]
    if "guardian_number" in data:  user.guardian_number = data["guardian_number"]
    if "password" in data and data["password"]:
        user.password = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
    db.session.commit()
    return jsonify({"message": "User updated"}), 200


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

# ── Courses CRUD ─────────────────────────────────────────────────────────────

@admin_bp.get("/courses")
@jwt_required()
def list_courses():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    courses = Course.query.order_by(Course.created_at.desc()).all()
    result = []
    for c in courses:
        teacher_name = c.teacher.username if c.teacher else "Unassigned"
        enrolled_count = c.students.count()
        result.append({
            "id": c.id, "name": c.name, "section": c.section,
            "teacher": teacher_name,
            "teacher_id": c.teacher_id,
            "enrolled": enrolled_count,
        })
    return jsonify(result), 200

# ── Requests Management ──────────────────────────────────────────────────────

@admin_bp.get("/requests")
@jwt_required()
def list_requests():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    requests = CourseRequest.query.filter_by(status="pending").all()
    result = []
    for r in requests:
        user = User.query.get(r.user_id)
        course = Course.query.get(r.course_id)
        if not user or not course: continue
        result.append({
            "id": r.id,
            "user_id": user.id,
            "user_name": user.username,
            "user_role": user.type,
            "course_id": course.id,
            "course_name": f"{course.name} ({course.section or 'N/A'})",
            "status": r.status,
            "created_at": str(r.created_at)
        })
    return jsonify(result), 200

@admin_bp.post("/requests/<int:req_id>/approve")
@jwt_required()
def approve_request(req_id):
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    req = CourseRequest.query.get(req_id)
    if not req or req.status != "pending":
        return jsonify({"error": "Request not found or already processed"}), 404
    
    user = User.query.get(req.user_id)
    course = Course.query.get(req.course_id)
    
    if user.type == "student":
        course.students.append(user)
        msg = f"Your request to enroll in {course.name} was approved."
    elif user.type == "teacher":
        course.teacher_id = user.id
        msg = f"Your request to teach {course.name} was approved."
    else:
        return jsonify({"error": "Invalid user role"}), 400
        
    req.status = "approved"
    notif = Notification(user_id=user.id, message=msg)
    db.session.add(notif)
    db.session.commit()
    return jsonify({"message": "Request approved"}), 200

@admin_bp.post("/requests/<int:req_id>/deny")
@jwt_required()
def deny_request(req_id):
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    req = CourseRequest.query.get(req_id)
    if not req or req.status != "pending":
        return jsonify({"error": "Request not found or already processed"}), 404
        
    user = User.query.get(req.user_id)
    course = Course.query.get(req.course_id)
    
    req.status = "denied"
    msg = f"Your request for {course.name} was denied."
    notif = Notification(user_id=user.id, message=msg)
    db.session.add(notif)
    db.session.commit()
    return jsonify({"message": "Request denied"}), 200

@admin_bp.post("/courses")
@jwt_required()
def create_course():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json()
    if not data.get("name"):
        return jsonify({"error": "Course name is required"}), 400
    teacher_id = data.get("teacher_id")
    if teacher_id:
        teacher = User.query.filter_by(id=teacher_id, type="teacher").first()
        if not teacher:
            return jsonify({"error": "Teacher not found"}), 404
    course = Course(name=data["name"], section=data.get("section"), teacher_id=teacher_id)
    db.session.add(course)
    db.session.flush()

    # Enroll students if provided
    student_ids = data.get("student_ids", [])
    for sid in student_ids:
        student = User.query.filter_by(id=sid, type="student").first()
        if student:
            course.students.append(student)

    db.session.commit()
    return jsonify({"message": "Course created", "id": course.id}), 201


@admin_bp.put("/courses/<int:course_id>")
@jwt_required()
def update_course(course_id):
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    data = request.get_json()
    if "name" in data:
        course.name = data["name"]
    if "section" in data:
        course.section = data["section"]
    if "teacher_id" in data:
        course.teacher_id = data["teacher_id"]
    if "student_ids" in data:
        # Replace enrolled students
        course.students = []
        for sid in data["student_ids"]:
            student = User.query.filter_by(id=sid, type="student").first()
            if student:
                course.students.append(student)
    db.session.commit()
    return jsonify({"message": "Course updated"}), 200


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

# ── Attendance Log ───────────────────────────────────────────────────────────

@admin_bp.get("/attendance")
@jwt_required()
def attendance_log():
    identity = get_jwt_identity()
    if not _require_admin(identity):
        return jsonify({"error": "Forbidden"}), 403
    records = (Attendance.query
               .order_by(Attendance.date.desc(), Attendance.created_at.desc())
               .limit(200).all())
    result = []
    for r in records:
        student = User.query.get(r.student_id)
        course = Course.query.get(r.course_id)
        result.append({
            "id": r.id,
            "date": str(r.date),
            "student_name": student.username if student else "Unknown",
            "student_id": student.student_id if student else "N/A",
            "course": course.name if course else "N/A",
            "teacher": course.teacher.username if course and course.teacher else "N/A",
        })
    return jsonify(result), 200
