import base64
import json
import numpy as np
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import Student
from ml.face_detector import detect_and_embed
from ml.face_matcher import find_match

face_bp = Blueprint("face", __name__)

# ── Enrollment ────────────────────────────────────────────────────────────────

@face_bp.post("/enroll")
@jwt_required()
def enroll():
    """
    Receive 5 Base64-encoded frame captures, extract embeddings,
    average them into one master embedding, and save to DB.
    Body: { "frames": ["data:image/jpeg;base64,...", ...] }
    """
    identity = get_jwt_identity()
    student = Student.query.filter_by(user_id=identity["id"]).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json()
    frames = data.get("frames", [])
    if len(frames) != 5:
        return jsonify({"error": "Exactly 5 frames required"}), 400

    embeddings = []
    for frame_b64 in frames:
        # Strip data URI prefix if present
        if "," in frame_b64:
            frame_b64 = frame_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(frame_b64)
        embedding = detect_and_embed(img_bytes)
        if embedding is None:
            return jsonify({"error": "Face not detected in one or more frames. Please retry."}), 422
        embeddings.append(embedding)

    master = np.mean(embeddings, axis=0)
    master = master / np.linalg.norm(master)  # normalize

    student.face_embedding = json.dumps(master.tolist())
    student.face_enrolled = True
    db.session.commit()
    return jsonify({"message": "Face enrolled successfully"}), 200


# ── Live Scan ─────────────────────────────────────────────────────────────────

@face_bp.post("/scan")
@jwt_required()
def scan():
    """
    Receive a single Base64 frame, detect all faces, match against
    enrolled students in the given course.
    Body: { "frame": "data:image/jpeg;base64,...", "course_id": 1 }
    Returns: [{ student_id, name, sid, confidence, bbox }]
    """
    data = request.get_json()
    frame_b64 = data.get("frame", "")
    course_id  = data.get("course_id")

    if not frame_b64 or not course_id:
        return jsonify({"error": "frame and course_id required"}), 400

    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]
    img_bytes = base64.b64decode(frame_b64)

    # Load enrolled students for this course
    from models import Enrollment, Course
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    enrolled = []
    for e in course.enrollments:
        s = e.student
        if s.face_enrolled and s.face_embedding:
            emb = np.array(json.loads(s.face_embedding), dtype=np.float32)
            enrolled.append({
                "student_id": s.id,
                "sid": s.student_id,
                "name": s.user.name,
                "embedding": emb,
            })

    results = find_match(img_bytes, enrolled, threshold=0.45)
    return jsonify({"matches": results}), 200
