import base64
import json
import numpy as np
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Course

face_bp = Blueprint("face", __name__)

# ── Per-frame Validation ───────────────────────────────────────────────────────

@face_bp.post("/validate-frame")
@jwt_required()
def validate_frame():
    """
    Validate a single frame for face enrollment quality.
    Called by the frontend after each MediaPipe-gated capture so the user gets
    server-side confirmation before the step is marked done.
    Body: { "frame": "data:image/jpeg;base64,..." }
    Returns: { "valid": true } or { "valid": false, "reason": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"valid": False, "reason": "Invalid request"}), 400

    frame_b64 = data.get("frame", "")
    if not frame_b64:
        return jsonify({"valid": False, "reason": "No frame provided"}), 400

    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]

    missing_padding = len(frame_b64) % 4
    if missing_padding:
        frame_b64 += "=" * (4 - missing_padding)

    try:
        img_bytes = base64.b64decode(frame_b64)
    except Exception:
        return jsonify({"valid": False, "reason": "Invalid image data"}), 400

    try:
        from ml.face_detector import detect_and_embed
        embedding = detect_and_embed(img_bytes, require_single_face=True)

        if embedding is not None:
            return jsonify({"valid": True}), 200
        else:
            return jsonify({
                "valid": False,
                "reason": "No clear face detected. Make sure your face is centered, "
                          "well-lit, in focus, and you are the only person in frame."
            }), 200
    except Exception as e:
        print(f"[ERROR] validate-frame exception: {e}")
        return jsonify({
            "valid": False,
            "reason": "Frame verification temporary error. Please hold steady."
        }), 200


# ── Enrollment ────────────────────────────────────────────────────────────────

@face_bp.post("/enroll")
@jwt_required()
def enroll():
    """
    Receive 5 Base64-encoded frame captures (one per pose), extract embeddings,
    and store them individually as a JSON array-of-arrays.

    Each frame has already been validated client-side (MediaPipe pose gate)
    and by /validate-frame. This endpoint does a final server-side quality check
    and stores all embeddings that pass (minimum 3 required).

    Body: { "frames": ["data:image/jpeg;base64,...", ...] }
    """
    identity = get_jwt_identity()
    student = User.query.filter_by(id=identity["id"], type="student").first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body missing or invalid JSON"}), 400

    frames = data.get("frames", [])
    if len(frames) < 3:
        return jsonify({"error": "At least 3 frames required for enrollment"}), 400

    try:
        from ml.face_detector import detect_and_embed
    except ImportError as e:
        return jsonify({"error": f"ML module not available: {e}"}), 500

    # ── Extract one embedding per pose frame ──────────────────────────────────
    pose_embeddings = []  # list of lists — one per successfully processed frame
    failed_steps    = []

    for idx, frame_b64 in enumerate(frames):
        try:
            if "," in frame_b64:
                frame_b64 = frame_b64.split(",", 1)[1]
            missing_padding = len(frame_b64) % 4
            if missing_padding:
                frame_b64 += "=" * (4 - missing_padding)
            img_bytes = base64.b64decode(frame_b64)
            embedding = detect_and_embed(img_bytes, require_single_face=True)

            if embedding is not None:
                pose_embeddings.append(embedding.tolist())
                print(f"[INFO] Step {idx+1}: pose embedding extracted (dim={len(embedding)})")
            else:
                failed_steps.append(idx + 1)
                print(f"[WARNING] Step {idx+1}: no face detected — skipping")

        except Exception as e:
            failed_steps.append(idx + 1)
            print(f"[WARNING] Step {idx+1}: processing error — {e}")

    if len(pose_embeddings) < 3:
        return jsonify({
            "error": (
                f"Only {len(pose_embeddings)}/{len(frames)} frames produced a usable face. "
                f"Failed steps: {failed_steps}. "
                "Please retry in a brighter area and keep your face clearly visible."
            )
        }), 422

    # ── Store all pose embeddings as JSON array-of-arrays ─────────────────────
    # Format: [[emb_pose1], [emb_pose2], ...] — each sub-list is a 512-dim float list
    student.face_embedding = json.dumps(pose_embeddings)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Database commit failed: {e}")
        return jsonify({"error": "Database error — could not save face embedding. Please try again."}), 500

    print(f"[SUCCESS] Saved {len(pose_embeddings)} pose embeddings for "
          f"{student.username} (id={student.id}). Skipped steps: {failed_steps}.")

    return jsonify({
        "message": "Face enrolled successfully",
        "poses_stored": len(pose_embeddings),
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
    Supports both the new multi-pose embedding format (list-of-lists)
    and the old single-vector format (flat list) for backwards compatibility.
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

    # ── Load enrolled students, supporting both embedding formats ─────────────
    enrolled = []
    for s in course.students:
        if s.face_embedding:
            try:
                raw = json.loads(s.face_embedding)
                # list-of-lists = new multi-pose format; flat list = old single-vector
                if raw and isinstance(raw[0], list):
                    embeddings = [np.array(e, dtype=np.float32) for e in raw]
                else:
                    embeddings = [np.array(raw, dtype=np.float32)]

                enrolled.append({
                    "student_id": s.id,
                    "sid":        s.student_id,
                    "name":       s.username,
                    "embeddings": embeddings,   # list of np.ndarray (1 old or N new)
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
