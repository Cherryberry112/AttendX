"""
face_matcher.py
---------------
Detect all faces in a frame and match against enrolled student embeddings.
Supports multi-pose embeddings (new: list of N embeddings per student) and
single embeddings (old: one embedding per student).

For multi-pose students, compares scan embedding against ALL stored pose
embeddings and takes the BEST cosine similarity — this is the payoff of
proper multi-angle enrollment.
"""
import cv2
import numpy as np
from ml.face_detector import (
    detect_faces,
    _align_face,
    _combine_embeddings,
    _get_insightface_app,
    INSIGHTFACE_AVAILABLE,
)

# ── Max frame width for scan performance ─────────────────────────────────────
_MAX_SCAN_WIDTH = 640

# ── Confidence margin — prevent near-tie matches ─────────────────────────────
_MARGIN_THRESHOLD = 0.05


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)


def _best_match(scan_emb: np.ndarray, enrolled: list[dict]) -> tuple:
    """
    Find the best and second-best matching student for a scan embedding.

    For each enrolled student, compares scan_emb against ALL of their stored
    pose embeddings (enrolled[i]["embeddings"] is a list of np.ndarray).
    Takes the maximum cosine similarity across all poses as that student's score.

    Returns (best_score, second_best_score, best_student).
    """
    best_score        = -1.0
    second_best_score = -1.0
    best_student      = None

    for s in enrolled:
        # Compare against all pose embeddings; take the best
        student_best = max(
            cosine_similarity(scan_emb, emb)
            for emb in s["embeddings"]
        )
        if student_best > best_score:
            second_best_score = best_score
            best_score        = student_best
            best_student      = s
        elif student_best > second_best_score:
            second_best_score = student_best

    return best_score, second_best_score, best_student


def _make_result(best_student, best_score: float, second_best_score: float,
                 bbox: list, threshold: float) -> dict:
    """
    Produce a match result dict. Accepted only if:
      1. best_score >= threshold, AND
      2. (best_score - second_best_score) >= _MARGIN_THRESHOLD
    """
    margin = best_score - second_best_score

    if best_student and best_score >= threshold and margin >= _MARGIN_THRESHOLD:
        return {
            "student_id": best_student["student_id"],
            "sid":        best_student["sid"],
            "name":       best_student["name"],
            "confidence": round(best_score, 4),
            "bbox":       bbox,
        }
    return {
        "student_id": None,
        "sid":        None,
        "name":       "Unknown",
        "confidence": round(max(best_score, 0), 4),
        "bbox":       bbox,
    }


def find_match(img_bytes: bytes, enrolled: list[dict], threshold: float = 0.35) -> list[dict]:
    """
    Detect all faces in img_bytes, extract embeddings, and match each
    against enrolled student pose embeddings via cosine similarity.

    Parameters
    ----------
    img_bytes : raw image bytes (JPEG/PNG)
    enrolled  : list of dicts { student_id, sid, name, embeddings: [np.ndarray, ...] }
    threshold : minimum cosine similarity to count as a match

    Returns
    -------
    List of match dicts: { student_id, sid, name, confidence, bbox }
    Returns [] if no faces detected.
    """
    if not enrolled:
        return []

    nparr = np.frombuffer(img_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return []

    # Downscale for performance
    h_orig, w_orig = img.shape[:2]
    if w_orig > _MAX_SCAN_WIDTH:
        scale = _MAX_SCAN_WIDTH / w_orig
        img = cv2.resize(img, (_MAX_SCAN_WIDTH, int(h_orig * scale)), interpolation=cv2.INTER_AREA)
        print(f"[INFO] scan: downscaled {w_orig}x{h_orig} -> {_MAX_SCAN_WIDTH}x{int(h_orig * scale)}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if float(np.mean(gray)) < 40:
        gray = cv2.equalizeHist(gray)
        img  = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    # ── Try InsightFace if available ──────────────────────────────────────────
    if INSIGHTFACE_AVAILABLE:
        try:
            app = _get_insightface_app()
            if app is not None:
                faces = app.get(img)
                results = []
                for face in faces:
                    emb  = face.embedding.astype(np.float32)
                    emb  = emb / (np.linalg.norm(emb) + 1e-9)
                    bbox = [int(x) for x in face.bbox.tolist()]
                    best_score, second_best_score, best_student = _best_match(emb, enrolled)
                    result = _make_result(best_student, best_score, second_best_score, bbox, threshold)
                    results.append(result)
                    print(f"[INFO] InsightFace scan: best={best_score:.3f} margin={best_score-second_best_score:.3f} "
                          f"student={best_student['name'] if best_student else None}")
                return results
        except Exception as e:
            print(f"[WARNING] InsightFace scan failed: {e}")

    # ── OpenCV HOG+LBP matching ───────────────────────────────────────────────
    boxes = detect_faces(gray)
    if not boxes:
        return []

    results = []
    for (x, y, w, h) in boxes:
        face_crop = gray[max(0,y):min(gray.shape[0],y+h), max(0,x):min(gray.shape[1],x+w)]
        if face_crop.size == 0:
            continue

        face_crop = _align_face(face_crop)
        emb = _combine_embeddings(face_crop)
        if emb is None:
            continue

        bbox = [int(x), int(y), int(x+w), int(y+h)]
        best_score, second_best_score, best_student = _best_match(emb, enrolled)
        result = _make_result(best_student, best_score, second_best_score, bbox, threshold)
        results.append(result)
        print(f"[INFO] HOG+LBP scan: best={best_score:.3f} 2nd={second_best_score:.3f} "
              f"margin={best_score-second_best_score:.3f} "
              f"student={best_student['name'] if best_student else None}")

    return results
