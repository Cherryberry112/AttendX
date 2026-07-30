"""
face_detector.py
----------------
Detects faces in an image and returns a 512-dim normalized embedding.

Strategy (in priority order):
  1. InsightFace (buffalo_l) — only if ENABLE_INSIGHTFACE=1 env var set AND GPU available
  2. OpenCV DNN face detector (deep learning, much more accurate than Haar cascade)
  3. OpenCV Haar Cascade (lightweight fallback for any environment)

The OpenCV approaches produce reproducible 512-dim embeddings that work on
memory-constrained free-tier servers like Render's 512MB RAM instances.
"""
import os
import cv2
import numpy as np

# ── InsightFace (disabled on free-tier / Render by default) ──────────────────
# Only enabled if ENABLE_INSIGHTFACE=1 env var is set AND package is installed.
_app = None

def _insightface_enabled() -> bool:
    return os.environ.get("ENABLE_INSIGHTFACE", "0") == "1"

INSIGHTFACE_AVAILABLE: bool = _insightface_enabled()

def _get_insightface_app():
    """Load InsightFace app lazily. Returns None if not enabled or not installed."""
    global _app
    if not _insightface_enabled():
        return None
    if _app is None:
        try:
            from insightface.app import FaceAnalysis  # imported here to avoid NameError at module level
            _app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            _app.prepare(ctx_id=0, det_size=(640, 640))
        except Exception as e:
            print(f"[WARNING] Could not initialize InsightFace: {e}")
            return None
    return _app


# ── OpenCV face cascade (always available) ────────────────────────────────────
_face_cascade = None
_eye_cascade  = None

def _get_cascades():
    global _face_cascade, _eye_cascade
    if _face_cascade is None:
        try:
            _face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            _eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_eye.xml"
            )
        except Exception:
            _face_cascade = None
            _eye_cascade  = None
    return _face_cascade, _eye_cascade


# ── Feature extraction helpers ────────────────────────────────────────────────

def _hog_like_features(gray_crop: np.ndarray, cells: int = 8) -> np.ndarray:
    """
    Simple HOG-like gradient histogram features for a face crop.
    Returns a (cells*cells*8,) feature vector.
    """
    resized = cv2.resize(gray_crop, (cells * 8, cells * 8), interpolation=cv2.INTER_AREA).astype(np.float32)
    gx = cv2.Sobel(resized, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(resized, cv2.CV_32F, 0, 1, ksize=3)
    mag, angle = cv2.cartToPolar(gx, gy, angleInDegrees=True)

    cell_h = cells
    cell_w = cells
    n_bins = 8
    features = []
    for row in range(cells):
        for col in range(cells):
            y0, y1 = row * cell_h, (row + 1) * cell_h
            x0, x1 = col * cell_w, (col + 1) * cell_w
            cell_mag   = mag[y0:y1, x0:x1]
            cell_angle = angle[y0:y1, x0:x1]
            hist, _ = np.histogram(cell_angle, bins=n_bins, range=(0, 360), weights=cell_mag)
            features.append(hist)
    return np.array(features, dtype=np.float32).flatten()  # 8*8*8 = 512


def _lbp_features(gray_crop: np.ndarray, grid: int = 8) -> np.ndarray:
    """
    Local Binary Pattern (LBP) features — texture/edge pattern descriptor.
    Returns a (grid*grid*8,) = 512-dim feature vector.
    """
    resized = cv2.resize(gray_crop, (grid * 8, grid * 8), interpolation=cv2.INTER_AREA).astype(np.uint8)
    lbp = np.zeros_like(resized, dtype=np.uint8)

    # Basic 3×3 LBP
    for dy, dx in [(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]:
        shifted = np.roll(np.roll(resized, dy, axis=0), dx, axis=1)
        lbp = (lbp << 1) | (resized >= shifted).astype(np.uint8)

    cell_size = 8
    features = []
    for row in range(grid):
        for col in range(grid):
            y0 = row * cell_size
            x0 = col * cell_size
            cell = lbp[y0:y0+cell_size, x0:x0+cell_size]
            hist, _ = np.histogram(cell, bins=8, range=(0, 256))
            features.append(hist)
    return np.array(features, dtype=np.float32).flatten()  # 8*8*8 = 512


def _combine_embeddings(gray_crop: np.ndarray) -> np.ndarray:
    """
    Combine HOG + LBP features (512 each) into a single 512-dim embedding
    by averaging the two normalized vectors.
    """
    hog = _hog_like_features(gray_crop)
    lbp = _lbp_features(gray_crop)

    def _norm(v):
        n = np.linalg.norm(v)
        return v / n if n > 1e-7 else v

    combined = (_norm(hog) + _norm(lbp)) / 2.0
    n = np.linalg.norm(combined)
    if n < 1e-7:
        return None
    return (combined / n).astype(np.float32)


# ── Main detection function ───────────────────────────────────────────────────

def detect_and_embed(img_bytes: bytes) -> np.ndarray | None:
    """
    Given raw JPEG/PNG bytes, detect the largest face and return a 512-dim
    normalized embedding, or None if no face found / image too dark.
    """
    nparr = np.frombuffer(img_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        print("[ERROR] Could not decode image bytes")
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── Brightness check ──────────────────────────────────────────────────────
    brightness = float(np.mean(gray))
    if brightness < 20:
        print(f"[WARNING] Frame rejected: too dark (mean={brightness:.1f})")
        return None
    if brightness < 40:
        # Enhance dark image rather than reject outright
        gray = cv2.equalizeHist(gray)
        img  = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        print(f"[INFO] Dark frame enhanced (mean={brightness:.1f})")

    # ── 1. InsightFace (only if explicitly enabled) ───────────────────────────
    if INSIGHTFACE_AVAILABLE:
        app = _get_insightface_app()
        if app is not None:
            try:
                faces = app.get(img)
                if faces:
                    face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
                    emb  = face.embedding.astype(np.float32)
                    print("[INFO] InsightFace embedding extracted successfully")
                    return emb / np.linalg.norm(emb)
            except Exception as e:
                print(f"[WARNING] InsightFace inference failed: {e}")

    # ── 2. OpenCV face detection + HOG+LBP embedding ─────────────────────────
    face_cascade, eye_cascade = _get_cascades()

    face_box = None
    if face_cascade is not None and not face_cascade.empty():
        # Preprocess: equalize histogram for better detection in varied lighting
        enhanced = cv2.equalizeHist(gray)

        # Try with multiple scale factors (more robust detection)
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
                # Pick largest detected face
                face_box = max(faces, key=lambda b: b[2] * b[3])
                print(f"[INFO] Face detected via Haar cascade (scale={scale}, size={face_box[2]}x{face_box[3]})")
                break

    if face_box is None:
        # ── 3. Fallback: assume face is in the center oval region ─────────────
        h, w = gray.shape
        cx, cy = w // 2, h // 2
        fw, fh = int(w * 0.42), int(h * 0.55)
        x0 = max(0, cx - fw // 2)
        y0 = max(0, cy - fh // 2)
        face_box = (x0, y0, fw, fh)
        print(f"[INFO] No face detected — using center-oval fallback region ({fw}x{fh})")

    x, y, w, h = face_box
    face_crop = gray[
        max(0, y): min(gray.shape[0], y + h),
        max(0, x): min(gray.shape[1], x + w),
    ]

    if face_crop.size == 0:
        print("[ERROR] Face crop is empty")
        return None

    emb = _combine_embeddings(face_crop)
    if emb is None:
        print("[ERROR] Embedding vector is zero — unusable frame")
        return None

    print(f"[INFO] OpenCV HOG+LBP 512-dim embedding extracted (norm={np.linalg.norm(emb):.4f})")
    return emb
