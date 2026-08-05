import json
import numpy as np
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Course

face_bp = Blueprint("face", __name__)

@face_bp.post("/enroll")
@jwt_required()
def enroll():
    """
    Receive exactly 3 client-side 128-dim face-api.js embeddings, and store them 
    as a JSON array-of-arrays in the DB.
    """
    identity = get_jwt_identity()
    student  = User.query.filter_by(id=identity["id"], type="student").first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body missing or invalid JSON"}), 400

    embeddings = data.get("embeddings", [])
    
    # Validation
    if not isinstance(embeddings, list) or len(embeddings) != 3:
        return jsonify({"error": f"Exactly 3 embeddings required for enrollment (received {len(embeddings) if isinstance(embeddings, list) else 0})"}), 400
        
    for idx, emb in enumerate(embeddings):
        if not isinstance(emb, list) or len(emb) != 128:
            return jsonify({"error": f"Embedding at index {idx} is invalid (must be list of 128 floats)"}), 400
        for val in emb:
            if not isinstance(val, (int, float)) or not (-1.0 <= val <= 1.0):
                return jsonify({"error": f"Invalid value in embedding at index {idx}"}), 400

    student.face_embedding = json.dumps(embeddings)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Database commit failed: {e}")
        return jsonify({"error": "Database error — could not save face embedding. Please try again."}), 500

    print(f"[SUCCESS] Enrolled 3 face-api.js pose embeddings for {student.username} (id={student.id})")

    return jsonify({
        "message": "Face enrolled across 3 angles",
        "poses_stored": 3,
    }), 200

@face_bp.post("/scan")
@jwt_required()
def scan():
    """
    Receive client-side face-api.js descriptors and bboxes, and match against 
    enrolled students in the given course.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    faces = data.get("faces", [])
    course_id = data.get("course_id")

    if course_id is None:
        return jsonify({"error": "course_id required"}), 400

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    if not faces:
        return jsonify({"matches": []}), 200

    # Load enrolled students with embeddings
    enrolled = []
    for s in course.students:
        if not s.face_embedding:
            continue
        try:
            raw = json.loads(s.face_embedding)
            if raw and isinstance(raw[0], list):
                embeddings = [np.array(e, dtype=np.float32) for e in raw]
            else:
                embeddings = [np.array(raw, dtype=np.float32)]

            enrolled.append({
                "student_id": s.id,
                "sid":        s.student_id,
                "name":       s.username,
                "embeddings": embeddings,
            })
        except Exception:
            pass

    try:
        from ml.face_matcher import find_match
        results = find_match(faces, enrolled, threshold=0.50)
    except Exception as e:
        print(f"[ERROR] Face scan error: {e}")
        results = []

    return jsonify({"matches": results}), 200
