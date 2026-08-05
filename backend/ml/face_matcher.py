"""
face_matcher.py
---------------
Detect all faces in a scan frame and match against enrolled student embeddings.

Uses:
  - OpenCV DNN (ResNet-10 SSD) for face detection
  - dlib 128-dim face embeddings via face_recognition
  - Euclidean distance matching (L2 on already-normalized vectors)

Match acceptance requires BOTH:
  1. best_distance <= threshold (0.50)
  2. second_best_distance - best_distance >= _MARGIN_THRESHOLD (0.10)

This prevents false positives when two students look similar.
"""
import cv2
import numpy as np
import face_recognition
from ml.face_detector import detect_faces_dnn, extract_embedding

# ── Config ────────────────────────────────────────────────────────────────────
_MAX_SCAN_WIDTH    = 640
_MARGIN_THRESHOLD  = 0.10   # Euclidean distance margin to beat runner-up


# ── Distance Function ─────────────────────────────────────────────────────────

def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Euclidean distance between two vectors.
    Both should be L2-normalized; lower = more similar.
    """
    return float(np.linalg.norm(a - b))


# ── Best Match Selection ──────────────────────────────────────────────────────

def _best_match(scan_emb: np.ndarray, enrolled: list) -> tuple:
    """
    Find the best and second-best matching student for a scan embedding.

    For each enrolled student, compute Euclidean distance against ALL of their
    stored pose embeddings. The student's score = MINIMUM distance across all
    poses (best match to any stored angle).

    Returns (best_distance, second_best_distance, best_student).
    Lower distance = better match.
    """
    best_dist        = float("inf")
    second_best_dist = float("inf")
    best_student     = None

    for s in enrolled:
        if not s.get("embeddings"):
            continue
        # Minimum distance across all stored pose embeddings
        student_best_dist = min(
            euclidean_distance(scan_emb, emb)
            for emb in s["embeddings"]
        )
        if student_best_dist < best_dist:
            second_best_dist = best_dist
            best_dist        = student_best_dist
            best_student     = s
        elif student_best_dist < second_best_dist:
            second_best_dist = student_best_dist

    return best_dist, second_best_dist, best_student


# ── Result Builder ────────────────────────────────────────────────────────────

def _make_result(best_student, best_dist: float, second_best_dist: float,
                 bbox: list, threshold: float) -> dict:
    """
    Produce a match result dict. Accepted ONLY if:
      1. best_dist <= threshold (0.50), AND
      2. second_best_dist - best_dist >= _MARGIN_THRESHOLD (0.10)

    Confidence returned as (1 - best_dist), clamped to [0, 1].
    """
    margin = second_best_dist - best_dist

    accepted = (
        best_student is not None
        and best_dist <= threshold
        and margin >= _MARGIN_THRESHOLD
    )

    if accepted:
        return {
            "student_id": best_student["student_id"],
            "sid":        best_student["sid"],
            "name":       best_student["name"],
            "confidence": round(max(0.0, 1.0 - best_dist), 4),
            "bbox":       bbox,
        }
    return {
        "student_id": None,
        "sid":        None,
        "name":       "Unknown",
        "confidence": round(max(0.0, 1.0 - best_dist), 4),
        "bbox":       bbox,
    }


# ── Main Scan Function ────────────────────────────────────────────────────────

def find_match(img_bytes: bytes, enrolled: list, threshold: float = 0.50) -> list:
    """
    Detect all faces in img_bytes, extract dlib 128-dim embeddings,
    and match each face against enrolled student embeddings.

    Parameters
    ----------
    img_bytes : raw image bytes (JPEG/PNG)
    enrolled  : list of dicts { student_id, sid, name, embeddings: [np.ndarray, ...] }
    threshold : max Euclidean distance to count as a match (default 0.50)

    Returns
    -------
    List of match dicts: { student_id, sid, name, confidence, bbox }
    Returns [] if no faces detected or enrolled list is empty.
    """
    if not enrolled:
        return []

    # ── Decode image ──────────────────────────────────────────────────────────
    nparr = np.frombuffer(img_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        print("[ERROR] find_match: could not decode image")
        return []

    # ── Downscale for performance (keep aspect ratio) ─────────────────────────
    h_orig, w_orig = img.shape[:2]
    if w_orig > _MAX_SCAN_WIDTH:
        scale = _MAX_SCAN_WIDTH / w_orig
        img   = cv2.resize(img, (_MAX_SCAN_WIDTH, int(h_orig * scale)),
                           interpolation=cv2.INTER_AREA)
        print(f"[INFO] scan: downscaled {w_orig}x{h_orig} -> {img.shape[1]}x{img.shape[0]}")

    # ── DNN Face Detection ────────────────────────────────────────────────────
    boxes = detect_faces_dnn(img)
    if not boxes:
        print("[INFO] scan: no faces detected in frame")
        return []

    # ── Per-face Matching ─────────────────────────────────────────────────────
    results = []
    for (x, y, bw, bh) in boxes:
        # Crop face (BGR — extract_embedding handles color conversion)
        face_crop = img[max(0, y):min(img.shape[0], y + bh),
                        max(0, x):min(img.shape[1], x + bw)]
        if face_crop.size == 0:
            continue

        # Extract 128-dim embedding
        emb = extract_embedding(face_crop)
        if emb is None:
            print("[WARNING] scan: could not embed face crop — skipping")
            continue

        bbox = [int(x), int(y), int(x + bw), int(y + bh)]

        # Match against enrolled students
        best_dist, second_best_dist, best_student = _best_match(emb, enrolled)
        result = _make_result(best_student, best_dist, second_best_dist, bbox, threshold)
        results.append(result)

        student_name = best_student["name"] if best_student else "—"
        print(
            f"[INFO] scan: best_dist={best_dist:.3f} "
            f"2nd_dist={second_best_dist:.3f} "
            f"margin={second_best_dist - best_dist:.3f} "
            f"student={student_name} "
            f"accepted={result['student_id'] is not None}"
        )

    return results
