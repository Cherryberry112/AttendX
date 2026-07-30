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
    Tolerant: succeeds as long as at least 3 of 5 frames produce a valid embedding.
    """
    identity = get_jwt_identity()
    student = User.query.filter_by(id=identity["id"], type="student").first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data   = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body missing or invalid JSON"}), 400

    frames = data.get("frames", [])
    if len(frames) < 3:
        return jsonify({"error": "At least 3 frames required for enrollment"}), 400

    try:
        from ml.face_detector import detect_and_embed
    except ImportError as e:
        return jsonify({"error": f"ML module not available: {e}"}), 500

    embeddings   = []
    failed_steps = []

    for idx, frame_b64 in enumerate(frames):
        try:
            # Strip data URL prefix if present
            if "," in frame_b64:
                frame_b64 = frame_b64.split(",", 1)[1]

            # Validate base64 padding
            missing_padding = len(frame_b64) % 4
            if missing_padding:
                frame_b64 += "=" * (4 - missing_padding)

            img_bytes = base64.b64decode(frame_b64)
            embedding = detect_and_embed(img_bytes)

            if embedding is not None:
                embeddings.append(embedding)
                print(f"[INFO] Step {idx+1}: embedding extracted (dim={len(embedding)})")
            else:
                failed_steps.append(idx + 1)
                print(f"[WARNING] Step {idx+1}: no face detected — skipping this frame")

        except Exception as e:
            failed_steps.append(idx + 1)
            print(f"[WARNING] Step {idx+1}: processing error — {e}")

    if len(embeddings) < 3:
        return jsonify({
            "error": (
                f"Only {len(embeddings)}/5 frames produced a usable face. "
                f"Failed steps: {failed_steps}. "
                "Please retry in a brighter area and keep your face within the oval."
            )
        }), 422

    # Average and re-normalize
    master = np.mean(embeddings, axis=0).astype(np.float32)
    norm   = np.linalg.norm(master)
    if norm < 1e-7:
        return jsonify({"error": "Embedding computation failed — all frames were too similar or blank"}), 500

    master = master / norm

    student.face_embedding = json.dumps(master.tolist())
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Database commit failed: {e}")
        return jsonify({"error": "Database error — could not save face embedding. Please try again."}), 500

    print(f"[SUCCESS] Saved 512-dim face embedding for {student.username} (id={student.id}). "
          f"Used {len(embeddings)}/5 frames, skipped steps {failed_steps}.")

    return jsonify({
        "message": "Face enrolled successfully",
        "frames_used": len(embeddings),
        "frames_total": len(frames),
        "skipped_steps": failed_steps,
    }), 200


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
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    frame_b64 = data.get("frame", "")
    course_id = data.get("course_id")

    if not frame_b64 or not course_id:
        return jsonify({"error": "frame and course_id required"}), 400

    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(frame_b64)
    except Exception as e:
        return jsonify({"error": f"Invalid base64 frame: {e}"}), 400

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    enrolled = []
    for s in course.students:
        if s.face_embedding:
            try:
                emb = np.array(json.loads(s.face_embedding), dtype=np.float32)
                enrolled.append({
                    "student_id": s.id,
                    "sid":        s.student_id,
                    "name":       s.username,
                    "embedding":  emb,
                })
            except Exception:
                pass

    try:
        from ml.face_matcher import find_match
        results = find_match(img_bytes, enrolled, threshold=0.45)
    except ImportError:
        results = []
    except Exception as e:
        print(f"[ERROR] Face scan error: {e}")
        results = []

    return jsonify({"matches": results}), 200
