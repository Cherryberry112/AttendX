"""
face_matcher.py
---------------
Detect all faces in a frame and match against enrolled student embeddings
using the same HOG+LBP pipeline as face_detector.py.
Works on any server (no InsightFace needed).

Uses shared detection/alignment/embedding functions from face_detector.py
(M1 — single source of truth, no duplicated detectMultiScale).
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

# ── Max frame width for scan performance (M2) ────────────────────────────────
_MAX_SCAN_WIDTH = 640


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)


def find_match(img_bytes: bytes, enrolled: list[dict], threshold: float = 0.35) -> list[dict]:
    """
    Detect all faces in img_bytes, extract HOG+LBP embeddings,
    and match each against enrolled student embeddings via cosine similarity.

    Parameters
    ----------
    img_bytes : raw image bytes (JPEG/PNG)
    enrolled  : list of dicts { student_id, sid, name, embedding (np.ndarray) }
    threshold : minimum cosine similarity to count as a match (0.35 default for HOG+LBP)

    Returns
    -------
    List of match dicts: { student_id, sid, name, confidence, bbox }
    Returns [] if no faces detected (C1 — no fallback).
    """
    nparr = np.frombuffer(img_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return []

    # ── M2: Downscale for performance ─────────────────────────────────────────
    h_orig, w_orig = img.shape[:2]
    if w_orig > _MAX_SCAN_WIDTH:
        scale = _MAX_SCAN_WIDTH / w_orig
        new_w = _MAX_SCAN_WIDTH
        new_h = int(h_orig * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        print(f"[INFO] scan: downscaled {w_orig}x{h_orig} → {new_w}x{new_h}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))

    # Enhance dark frames rather than reject
    if brightness < 40:
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
                    results.append(_make_result(best_student, best_score, second_best_score, bbox, threshold))
                return results
        except Exception as e:
            print(f"[WARNING] InsightFace scan failed: {e}")

    # ── OpenCV HOG+LBP matching (uses shared detect_faces — M1) ──────────────
    boxes = detect_faces(gray)

    # C1: No fallback — if no faces detected, return empty list
    if not boxes:
        return []

    results = []

    for (x, y, w, h) in boxes:
        face_crop = gray[
            max(0, y): min(gray.shape[0], y + h),
            max(0, x): min(gray.shape[1], x + w),
        ]
        if face_crop.size == 0:
            continue

        # H2: Apply same eye-based alignment as enrollment
        face_crop = _align_face(face_crop)

        emb = _combine_embeddings(face_crop)
        if emb is None:
            continue

        bbox = [int(x), int(y), int(x + w), int(y + h)]
        best_score, second_best_score, best_student = _best_match(emb, enrolled)
        results.append(_make_result(best_student, best_score, second_best_score, bbox, threshold))
        print(f"[INFO] scan match: best={best_score:.3f} 2nd={second_best_score:.3f} "
              f"margin={best_score - second_best_score:.3f} threshold={threshold} "
              f"student={best_student['name'] if best_student else None}")

    return results


def _best_match(emb: np.ndarray, enrolled: list[dict]) -> tuple:
    """
    Find the best and second-best matching student for an embedding.
    Returns (best_score, second_best_score, best_student).
    H4: Both scores needed for confidence margin check.
    """
    best_score        = -1.0
    second_best_score = -1.0
    best_student      = None

    for s in enrolled:
        score = cosine_similarity(emb, s["embedding"])
        if score > best_score:
            second_best_score = best_score
            best_score        = score
            best_student      = s
        elif score > second_best_score:
            second_best_score = score

    return best_score, second_best_score, best_student


# ── H4: Confidence margin on match decisions ─────────────────────────────────
_MARGIN_THRESHOLD = 0.05


def _make_result(best_student, best_score: float, second_best_score: float,
                 bbox: list, threshold: float) -> dict:
    """
    Produce a match result dict. A match is accepted only if:
      1. best_score >= threshold, AND
      2. (best_score - second_best_score) >= _MARGIN_THRESHOLD
    This prevents near-tie scores from producing false confident matches.
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
