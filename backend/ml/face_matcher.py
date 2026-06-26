"""
face_matcher.py
---------------
Given raw image bytes and a list of enrolled student embeddings,
detect all faces and return cosine-similarity matches.
"""
import cv2
import numpy as np
from ml.face_detector import _get_app


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def find_match(img_bytes: bytes, enrolled: list[dict], threshold: float = 0.45) -> list[dict]:
    """
    Detect all faces in img_bytes, compare each against enrolled embeddings.

    Parameters
    ----------
    img_bytes : raw image bytes (JPEG/PNG)
    enrolled  : list of dicts with keys: student_id, sid, name, embedding (np.ndarray)
    threshold : minimum cosine similarity to count as a match

    Returns
    -------
    List of match dicts: { student_id, sid, name, confidence, bbox }
    Unmatched faces are returned with student_id=None.
    """
    nparr = np.frombuffer(img_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return []

    app   = _get_app()
    faces = app.get(img)
    results = []

    for face in faces:
        emb = face.embedding.astype(np.float32)
        emb = emb / (np.linalg.norm(emb) + 1e-9)
        bbox = [int(x) for x in face.bbox.tolist()]

        best_score  = -1.0
        best_student = None

        for s in enrolled:
            score = cosine_similarity(emb, s["embedding"])
            if score > best_score:
                best_score   = score
                best_student = s

        if best_student and best_score >= threshold:
            results.append({
                "student_id": best_student["student_id"],
                "sid":        best_student["sid"],
                "name":       best_student["name"],
                "confidence": round(best_score, 4),
                "bbox":       bbox,
            })
        else:
            results.append({
                "student_id": None,
                "sid":        None,
                "name":       "Unknown",
                "confidence": round(best_score, 4) if best_score > 0 else 0,
                "bbox":       bbox,
            })

    return results
