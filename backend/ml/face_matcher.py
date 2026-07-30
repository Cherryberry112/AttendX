"""
face_matcher.py
---------------
Detect all faces in a frame and match against enrolled student embeddings
using the same HOG+LBP pipeline as face_detector.py.
Works on any server (no InsightFace needed).
"""
import cv2
import numpy as np
from ml.face_detector import _get_cascades, _combine_embeddings, INSIGHTFACE_AVAILABLE


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)


def _detect_all_faces(img: np.ndarray) -> list[tuple]:
    """
    Detect all faces in an image.
    Returns list of (x, y, w, h) bounding boxes.
    Falls back to center-oval region if nothing detected.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.equalizeHist(gray)

    face_cascade, _ = _get_cascades()
    boxes = []

    if face_cascade is not None and not face_cascade.empty():
        for scale, neighbors, min_sz in [
            (1.05, 3, (50, 50)),
            (1.1,  4, (40, 40)),
            (1.15, 3, (30, 30)),
        ]:
            faces = face_cascade.detectMultiScale(
                enhanced,
                scaleFactor=scale,
                minNeighbors=neighbors,
                minSize=min_sz,
                flags=cv2.CASCADE_SCALE_IMAGE,
            )
            if len(faces) > 0:
                boxes = list(faces)
                break

    if not boxes:
        h, w = gray.shape
        cx, cy = w // 2, h // 2
        fw, fh = int(w * 0.42), int(h * 0.55)
        x0 = max(0, cx - fw // 2)
        y0 = max(0, cy - fh // 2)
        boxes = [(x0, y0, fw, fh)]
        print("[INFO] scan: no faces detected — using center-oval fallback")

    return boxes


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
    """
    nparr = np.frombuffer(img_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))

    # Enhance dark frames rather than reject
    if brightness < 40:
        gray = cv2.equalizeHist(gray)
        img  = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    # ── Try InsightFace if available ──────────────────────────────────────────
    if INSIGHTFACE_AVAILABLE:
        try:
            from ml.face_detector import _get_insightface_app
            app = _get_insightface_app()
            if app is not None:
                faces = app.get(img)
                results = []
                for face in faces:
                    emb  = face.embedding.astype(np.float32)
                    emb  = emb / (np.linalg.norm(emb) + 1e-9)
                    bbox = [int(x) for x in face.bbox.tolist()]
                    best_score, best_student = _best_match(emb, enrolled)
                    results.append(_make_result(best_student, best_score, bbox, threshold))
                return results
        except Exception as e:
            print(f"[WARNING] InsightFace scan failed: {e}")

    # ── OpenCV HOG+LBP matching ───────────────────────────────────────────────
    boxes   = _detect_all_faces(img)
    results = []

    for (x, y, w, h) in boxes:
        face_crop = gray[
            max(0, y): min(gray.shape[0], y + h),
            max(0, x): min(gray.shape[1], x + w),
        ]
        if face_crop.size == 0:
            continue

        emb = _combine_embeddings(face_crop)
        if emb is None:
            continue

        bbox = [int(x), int(y), int(x + w), int(y + h)]
        best_score, best_student = _best_match(emb, enrolled)
        results.append(_make_result(best_student, best_score, bbox, threshold))
        print(f"[INFO] scan match: best_score={best_score:.3f} threshold={threshold} student={best_student['name'] if best_student else None}")

    return results


def _best_match(emb: np.ndarray, enrolled: list[dict]) -> tuple:
    best_score   = -1.0
    best_student = None
    for s in enrolled:
        score = cosine_similarity(emb, s["embedding"])
        if score > best_score:
            best_score   = score
            best_student = s
    return best_score, best_student


def _make_result(best_student, best_score: float, bbox: list, threshold: float) -> dict:
    if best_student and best_score >= threshold:
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
