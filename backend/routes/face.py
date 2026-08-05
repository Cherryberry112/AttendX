import base64
import json
import numpy as np
from datetime import datetime
import threading
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Course

face_bp = Blueprint("face", __name__)

_enrollment_jobs = {}   # job_id -> {status, poses_stored, error, student_id}


# ─────────────────────────────────────────────────────────────────────────────
# Helper: decode base64 frame string -> raw bytes
# ─────────────────────────────────────────────────────────────────────────────

def _decode_b64_frame(frame_b64: str):
    """Strip data-URI prefix, fix padding, and base64-decode. Returns bytes or raises."""
    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]
    missing_padding = len(frame_b64) % 4
    if missing_padding:
        frame_b64 += "=" * (4 - missing_padding)
    return base64.b64decode(frame_b64)


# ─────────────────────────────────────────────────────────────────────────────
# Per-frame Validation — called after client capture before storing locally
# ─────────────────────────────────────────────────────────────────────────────

@face_bp.post("/validate-frame")
@jwt_required()
def validate_frame():
    """
    Fast quality check for a single enrollment frame.
    Does NOT run dlib inference here — that's too slow on free-tier CPU (5-20s).
    Dlib 128-dim extraction happens ONLY at /enroll (3 frames, called once).

    Checks (all complete in <200ms on Render free tier):
      1. Brightness  — mean(gray) >= 40
      2. Blur        — Laplacian variance >= 100
      3. DNN detect  — ResNet-10 SSD face presence
      4. Face size   — bounding box >= 100x100 px

    Body:   { "frame": "data:image/jpeg;base64,..." }
    Returns: { "valid": true } or { "valid": false, "reason": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"valid": False, "reason": "Invalid request body"}), 400

    frame_b64 = data.get("frame", "")
    if not frame_b64:
        return jsonify({"valid": False, "reason": "No frame provided"}), 400

    try:
        img_bytes = _decode_b64_frame(frame_b64)
    except Exception:
        return jsonify({"valid": False, "reason": "Invalid image data"}), 400

    try:
        import cv2
        import numpy as np_
        from ml.face_detector import detect_faces_dnn, _check_brightness, _check_blur

        nparr = np_.frombuffer(img_bytes, np_.uint8)
        img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"valid": False, "reason": "Could not decode image"}), 400

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # ── 1. Brightness check (~instant) ────────────────────────────────────
        brightness_err = _check_brightness(gray)
        if brightness_err:
            return jsonify({"valid": False, "reason": brightness_err}), 200

        # ── 2. Blur check (~5ms) ──────────────────────────────────────────────
        blur_err = _check_blur(gray)
        if blur_err:
            return jsonify({"valid": False, "reason": blur_err}), 200

        # ── 3. DNN face detection (~50-100ms) ─────────────────────────────────
        boxes = detect_faces_dnn(img)
        if not boxes:
            return jsonify({
                "valid": False,
                "reason": "No face detected. Center your face, ensure good lighting, and fill the guide oval."
            }), 200

        # ── 4. Face size check ────────────────────────────────────────────────
        x, y, bw, bh = boxes[0]
        if bw < 100 or bh < 100:
            return jsonify({
                "valid": False,
                "reason": f"Face too small ({bw}x{bh}px). Move closer and fill the oval."
            }), 200

        print(f"[INFO] validate-frame: OK — face {bw}x{bh}px, quality checks passed")
        return jsonify({"valid": True}), 200

    except Exception as e:
        print(f"[ERROR] validate-frame exception: {e}")
        return jsonify({"valid": False, "reason": "Server error during validation — please retry."}), 200


# ─────────────────────────────────────────────────────────────────────────────
# Enrollment — receive 3 pose frames and store 128-dim embeddings
# ─────────────────────────────────────────────────────────────────────────────

def _process_enrollment_async(app, job_id, student_id, frames_b64_list):
    with app.app_context():
        try:
            from ml.face_detector import detect_and_embed
            pose_embeddings = []
            for idx, frame_b64 in enumerate(frames_b64_list):
                img_bytes = _decode_b64_frame(frame_b64)
                emb = detect_and_embed(img_bytes, require_single_face=True)
                if emb is not None:
                    pose_embeddings.append(emb.tolist())
                else:
                    raise ValueError(f"Step {idx+1} failed face extraction")
            
            student = User.query.get(student_id)
            if not student:
                raise ValueError("Student not found")
            
            student.face_embedding = json.dumps(pose_embeddings)
            db.session.commit()
            
            _enrollment_jobs[job_id] = {
                "status": "completed",
                "poses_stored": len(pose_embeddings),
                "student_id": student_id,
            }
            print(f"[SUCCESS] Async enrollment done: {job_id}")
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Async enrollment failed: {e}")
            _enrollment_jobs[job_id] = {
                "status": "failed",
                "error": str(e),
                "student_id": student_id,
            }


@face_bp.post("/enroll")
@jwt_required()
def enroll():
    """
    Receive exactly 3 server-validated pose frames, process 128-dim dlib
    embeddings asynchronously, and store them as a JSON array-of-arrays in the DB.

    Body:   { "frames": ["data:image/jpeg;base64,...", ...] }  (exactly 3)
    Returns: 202 Accepted with job_id for polling.
    """
    identity = get_jwt_identity()
    student  = User.query.filter_by(id=identity["id"], type="student").first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body missing or invalid JSON"}), 400

    frames = data.get("frames", [])
    if len(frames) != 3:
        return jsonify({
            "error": f"Exactly 3 frames required for enrollment (received {len(frames)})"
        }), 400

    job_id = f"enroll_{student.id}_{int(datetime.now().timestamp())}"
    _enrollment_jobs[job_id] = {"status": "processing", "student_id": student.id}

    thread = threading.Thread(
        target=_process_enrollment_async,
        args=(current_app._get_current_object(), job_id, student.id, frames),
        daemon=True
    )
    thread.start()

    return jsonify({
        "status": "processing",
        "job_id": job_id,
        "message": "Enrollment is processing in the background. Poll /face/enroll-status for updates."
    }), 202


@face_bp.get("/enroll-status/<job_id>")
@jwt_required()
def enroll_status(job_id):
    job = _enrollment_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Enrollment job not found"}), 404
    
    identity = get_jwt_identity()
    if job.get("student_id") != identity["id"]:
        return jsonify({"error": "Unauthorized"}), 403
        
    return jsonify(job), 200


# ─────────────────────────────────────────────────────────────────────────────
# Live Scan — detect + match faces against enrolled course students
# ─────────────────────────────────────────────────────────────────────────────

@face_bp.post("/scan")
@jwt_required()
def scan():
    """
    Receive a single scan frame, detect faces, and match against enrolled
    students in the given course using Euclidean distance on 128-dim dlib
    embeddings.

    Body:   { "frame": "data:image/jpeg;base64,...", "course_id": 1 }
    Returns: { "matches": [{ student_id, name, sid, confidence, bbox }] }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    frame_b64 = data.get("frame", "")
    course_id = data.get("course_id")

    if not frame_b64 or not course_id:
        return jsonify({"error": "frame and course_id required"}), 400

    try:
        img_bytes = _decode_b64_frame(frame_b64)
    except Exception as e:
        return jsonify({"error": f"Invalid base64 frame: {e}"}), 400

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    # ── Load enrolled students with 128-dim embeddings ─────────────────────
    enrolled = []
    for s in course.students:
        if not s.face_embedding:
            continue
        try:
            raw = json.loads(s.face_embedding)
            # list-of-lists = multi-pose (new 128-dim format)
            # flat list     = old single embedding (backwards compat)
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

    # ── Run matching ───────────────────────────────────────────────────────
    try:
        from ml.face_matcher import find_match
        results = find_match(img_bytes, enrolled, threshold=0.50)
    except ImportError:
        results = []
    except Exception as e:
        print(f"[ERROR] Face scan error: {e}")
        results = []

    return jsonify({"matches": results}), 200
