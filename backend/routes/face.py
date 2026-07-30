import base64
import json
import numpy as np
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Course

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
    student = User.query.filter_by(id=identity["id"], type="student").first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json()
    frames = data.get("frames", [])
    if len(frames) != 5:
        return jsonify({"error": "Exactly 5 frames required"}), 400

    try:
        from ml.face_detector import detect_and_embed
    except ImportError as e:
        return jsonify({"error": f"ML module import failure: {e}"}), 500

    embeddings = []
    for idx, frame_b64 in enumerate(frames):
        if "," in frame_b64:
            frame_b64 = frame_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(frame_b64)
        embedding = detect_and_embed(img_bytes)
        if embedding is None:
            return jsonify({"error": f"Face not detected clearly or room too dark in step {idx+1}. Please retry in a brighter room."}), 422
        embeddings.append(embedding)

    master = np.mean(embeddings, axis=0)
    master = master / np.linalg.norm(master)

    student.face_embedding = json.dumps(master.tolist())
    db.session.commit()
    print(f"[SUCCESS] Saved 512-dim face embedding for student {student.username} (id={student.id}) into Supabase DB.")
    return jsonify({"message": "Face enrolled and vector embedding saved successfully to database"}), 200


# ── Live Scan ─────────────────────────────────────────────────────────────────

@face_bp.post("/scan")
@jwt_required()
def scan():
    """
    Receive a single Base64 frame, detect all faces, match against
    enrolled students in the given course.
    Body: { "frame": "data:image/jpeg;base64,...", "course_id": 1 }
    Returns: { "matches": [{ student_id, name, sid, confidence, bbox }] }
    """
    data = request.get_json()
    frame_b64 = data.get("frame", "")
    course_id = data.get("course_id")

    if not frame_b64 or not course_id:
        return jsonify({"error": "frame and course_id required"}), 400

    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]
    img_bytes = base64.b64decode(frame_b64)

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    enrolled = []
    for s in course.students:
        if s.face_embedding:
            emb = np.array(json.loads(s.face_embedding), dtype=np.float32)
            enrolled.append({
                "student_id": s.id,
                "sid": s.student_id,
                "name": s.username,
                "embedding": emb,
            })

    try:
        from ml.face_matcher import find_match
        results = find_match(img_bytes, enrolled, threshold=0.45)
    except ImportError:
        results = []

    return jsonify({"matches": results}), 200
