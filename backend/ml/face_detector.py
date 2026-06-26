"""
face_detector.py
----------------
Detects faces in an image and returns a 512-dim ArcFace embedding
using InsightFace (buffalo_l model).
"""
import cv2
import numpy as np

try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False

_app = None

def _get_app():
    global _app
    if not INSIGHTFACE_AVAILABLE:
        return None
    if _app is None:
        _app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        _app.prepare(ctx_id=0, det_size=(640, 640))
    return _app


def detect_and_embed(img_bytes: bytes) -> np.ndarray | None:
    """
    Given raw image bytes, detect the largest face and return its
    512-dim normalized embedding, or None if no face is found.
    """
    nparr = np.frombuffer(img_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    if not INSIGHTFACE_AVAILABLE:
        # Mock embedding for local testing when insightface is missing
        print("[WARNING] insightface not installed. Returning mock face embedding.")
        rng = np.random.default_rng(hash(img_bytes) & 0xffffffff)
        emb = rng.standard_normal(512).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        return emb

    app   = _get_app()
    faces = app.get(img)
    if not faces:
        return None

    # Pick the largest face by bounding-box area
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    emb  = face.embedding.astype(np.float32)
    emb  = emb / np.linalg.norm(emb)
    return emb
