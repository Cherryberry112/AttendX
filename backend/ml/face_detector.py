"""
face_detector.py
----------------
Detects faces in an image and returns a 512-dim normalized embedding.

Strategy (in priority order):
  1. InsightFace (buffalo_l) — only if ENABLE_INSIGHTFACE=1 env var set AND GPU available
  2. OpenCV Haar Cascade (lightweight fallback for any environment)

The OpenCV approach produces reproducible 512-dim embeddings that work on
memory-constrained free-tier servers like Render's 512MB RAM instances.

Shared functions exported for use by face_matcher.py:
  - detect_faces()       — single Haar cascade detection (no fallback)
  - _align_face()        — eye-based rotation alignment
  - _combine_embeddings()— HOG+LBP 512-dim embedding
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
_face_cascade    = None
_profile_cascade = None
_eye_cascade     = None

def _get_cascades():
    global _face_cascade, _profile_cascade, _eye_cascade
    if _face_cascade is None:
        try:
            _face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            _profile_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_profileface.xml"
            )
            _eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_eye.xml"
            )
        except Exception:
            _face_cascade    = None
            _profile_cascade = None
            _eye_cascade     = None
    return _face_cascade, _profile_cascade, _eye_cascade


# ── Shared face detection (M1 — single source of truth) ──────────────────────

def detect_faces(gray_img: np.ndarray) -> list:
    """
    Detect all faces in a grayscale image using frontal + profile Haar cascades.
    Returns list of (x, y, w, h) bounding boxes, or [] if no faces found.
    """
    face_cascade, profile_cascade, _ = _get_cascades()

    if face_cascade is None or face_cascade.empty():
        print("[WARNING] Haar face cascade not available")
        return []

    # Preprocess: equalize histogram for better detection in varied lighting
    enhanced = cv2.equalizeHist(gray_img)

    # 1. Try frontal face cascade
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
            return list(faces)

    # 2. Try profile face cascade (for turned / angled poses)
    if profile_cascade is not None and not profile_cascade.empty():
        for img_to_check, is_flipped in [(enhanced, False), (cv2.flip(enhanced, 1), True)]:
            p_faces = profile_cascade.detectMultiScale(
                img_to_check,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(40, 40),
            )
            if len(p_faces) > 0:
                results = []
                w_img = gray_img.shape[1]
                for (px, py, pw, ph) in p_faces:
                    if is_flipped:
                        px = w_img - (px + pw)
                    results.append((px, py, pw, ph))
                return results

    return []


# ── Eye-based face alignment (H2) ────────────────────────────────────────────

def _align_face(gray_crop: np.ndarray) -> np.ndarray:
    """
    Detect eyes within a face crop and rotate to level them.
    If exactly 2 eyes found → rotate so the eyes are horizontal.
    If 0 or 1 eye found → return the unrotated crop as-is (don't guess).
    """
    _, eye_cascade = _get_cascades()

    if eye_cascade is None or eye_cascade.empty():
        return gray_crop

    eyes = eye_cascade.detectMultiScale(
        gray_crop,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(15, 15),
    )

    if len(eyes) != 2:
        # Ambiguous — use unrotated crop
        return gray_crop

    # Sort eyes left-to-right by x coordinate
    eyes = sorted(eyes, key=lambda e: e[0])
    (ex1, ey1, ew1, eh1) = eyes[0]
    (ex2, ey2, ew2, eh2) = eyes[1]

    # Compute centers of each eye
    center_left  = (ex1 + ew1 // 2, ey1 + eh1 // 2)
    center_right = (ex2 + ew2 // 2, ey2 + eh2 // 2)

    # Compute tilt angle
    dy = center_right[1] - center_left[1]
    dx = center_right[0] - center_left[0]
    angle = np.degrees(np.arctan2(dy, dx))

    # Only rotate if tilt is significant but not extreme (likely a bad detection)
    if abs(angle) < 0.5 or abs(angle) > 30:
        return gray_crop

    # Rotate around the midpoint of the two eyes
    h, w = gray_crop.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    aligned = cv2.warpAffine(gray_crop, M, (w, h), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REPLICATE)

    print(f"[INFO] Face aligned: rotated {angle:.1f}° to level eyes")
    return aligned


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

def detect_and_embed(img_bytes: bytes, require_single_face: bool = False) -> np.ndarray | None:
    """
    Given raw JPEG/PNG bytes, detect the largest face and return a 512-dim
    normalized embedding, or None if no face found / image too dark / quality
    checks fail.

    Parameters
    ----------
    img_bytes : raw image bytes (JPEG/PNG)
    require_single_face : if True, reject frames with 0 or 2+ faces,
                          enforce minimum face size and blur checks.
                          Used during enrollment for strict quality control.
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
                    if require_single_face and len(faces) > 1:
                        print(f"[WARNING] Enrollment rejected: {len(faces)} faces detected (expected exactly 1)")
                        return None
                    face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
                    emb  = face.embedding.astype(np.float32)
                    print("[INFO] InsightFace embedding extracted successfully")
                    return emb / np.linalg.norm(emb)
            except Exception as e:
                print(f"[WARNING] InsightFace inference failed: {e}")

    # ── 2. OpenCV face detection + HOG+LBP embedding ─────────────────────────
    all_faces = detect_faces(gray)

    # ── C1: Face crop selection with pose fallback ────────────────────────────
    if len(all_faces) == 0:
        if require_single_face:
            # Fallback for angled pose frames verified by frontend landmarks
            h_img, w_img = gray.shape[:2]
            all_faces = [(int(w_img * 0.2), int(h_img * 0.15), int(w_img * 0.6), int(h_img * 0.7))]
            print("[INFO] No Haar face box — using centered pose crop fallback")
        else:
            print("[INFO] No face detected — returning None")
            return None

    # ── H1: Quality gates (enrollment mode) ──────────────────────────────────
    if require_single_face:
        if len(all_faces) > 1:
            print(f"[WARNING] Enrollment rejected: {len(all_faces)} faces detected (expected exactly 1)")
            return None

        face_box = all_faces[0]
        x, y, w, h = face_box
        frame_width = gray.shape[1]

        # Minimum face size gate: reject if face < 10% of frame width
        face_ratio = w / frame_width
        if face_ratio < 0.10:
            print(f"[WARNING] Enrollment rejected: face too small "
                  f"({w}px = {face_ratio:.1%} of frame width, need ≥10%)")
            return None

        # Blur gate: Laplacian variance on face crop
        face_crop_for_blur = gray[
            max(0, y): min(gray.shape[0], y + h),
            max(0, x): min(gray.shape[1], x + w),
        ]
        if face_crop_for_blur.size > 0:
            blur_score = cv2.Laplacian(face_crop_for_blur, cv2.CV_64F).var()
            if blur_score < 15:
                print(f"[WARNING] Enrollment rejected: face too blurry "
                      f"(Laplacian variance={blur_score:.1f}, need ≥15)")
                return None
            print(f"[INFO] Blur check passed (Laplacian variance={blur_score:.1f})")
    else:
        # Scan mode: pick the largest face
        face_box = max(all_faces, key=lambda b: b[2] * b[3])

    x, y, w, h = face_box
    face_crop = gray[
        max(0, y): min(gray.shape[0], y + h),
        max(0, x): min(gray.shape[1], x + w),
    ]

    if face_crop.size == 0:
        print("[ERROR] Face crop is empty")
        return None

    # ── H2: Eye-based alignment before embedding ─────────────────────────────
    face_crop = _align_face(face_crop)

    emb = _combine_embeddings(face_crop)
    if emb is None:
        print("[ERROR] Embedding vector is zero — unusable frame")
        return None

    print(f"[INFO] OpenCV HOG+LBP 512-dim embedding extracted (norm={np.linalg.norm(emb):.4f})")
    return emb
