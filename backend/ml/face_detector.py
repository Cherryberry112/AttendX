"""
face_detector.py
----------------
OpenCV DNN (ResNet-10 SSD) face detection + dlib 128-dim face embeddings.

Pipeline:
  1. OpenCV DNN — fast, accurate ResNet-10 SSD detector (confidence >= 0.7)
  2. dlib via face_recognition — 128-dim L2-normalized embeddings

Quality gates applied before embedding:
  - Brightness : mean(gray) >= 40
  - Blur       : Laplacian variance >= 100
  - Face size  : bounding box >= 100x100 pixels

Exported API:
  detect_faces_dnn(img)        -> list[(x,y,w,h)]   — largest face only
  extract_embedding(face_crop) -> np.ndarray(128,)   — or None
  detect_and_embed(img_bytes, require_single_face)   -> np.ndarray(128,) or None
"""
from __future__ import annotations
import os
import cv2
import numpy as np
import face_recognition
from typing import Optional

# ── DNN model paths ───────────────────────────────────────────────────────────
_MODELS_DIR   = os.path.join(os.path.dirname(__file__), "..", "models")
_PROTOTXT     = os.path.join(_MODELS_DIR, "deploy.prototxt")
_CAFFEMODEL   = os.path.join(_MODELS_DIR, "res10_300x300_ssd_iter_140000.caffemodel")

# ── Load DNN net once at module level (singleton) ─────────────────────────────
_dnn_net: Optional[cv2.dnn.Net] = None

def _get_dnn_net() -> Optional[cv2.dnn.Net]:
    global _dnn_net
    if _dnn_net is None:
        try:
            _dnn_net = cv2.dnn.readNetFromCaffe(_PROTOTXT, _CAFFEMODEL)
            print("[INFO] OpenCV DNN face detector loaded successfully")
        except Exception as e:
            print(f"[ERROR] Failed to load DNN face detector: {e}")
            _dnn_net = None
    return _dnn_net

# ── Warmup: force dlib model load at startup so first request doesn't timeout ─
try:
    _dummy = np.zeros((150, 150, 3), dtype=np.uint8)
    face_recognition.face_encodings(_dummy)
    print("[INFO] dlib face encoding model warmed up")
except Exception:
    pass


# ── DNN Face Detection ────────────────────────────────────────────────────────

def detect_faces_dnn(img: np.ndarray, conf_threshold: float = 0.7) -> list:
    """
    Detect faces using the ResNet-10 SSD DNN model.

    Parameters
    ----------
    img            : BGR image (np.ndarray)
    conf_threshold : minimum detection confidence (default 0.7)

    Returns
    -------
    List of (x, y, w, h) tuples for detections above threshold.
    Returns ONLY the largest face if multiple detected.
    Returns [] if net not loaded or no face found.
    """
    net = _get_dnn_net()
    if net is None:
        print("[ERROR] DNN net unavailable — cannot detect faces")
        return []

    h, w = img.shape[:2]

    blob = cv2.dnn.blobFromImage(
        cv2.resize(img, (300, 300)),
        scalefactor=1.0,
        size=(300, 300),
        mean=(104.0, 177.0, 123.0),
    )
    net.setInput(blob)
    detections = net.forward()  # shape: (1, 1, N, 7)

    boxes = []
    for i in range(detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        if confidence < conf_threshold:
            continue
        x1 = int(detections[0, 0, i, 3] * w)
        y1 = int(detections[0, 0, i, 4] * h)
        x2 = int(detections[0, 0, i, 5] * w)
        y2 = int(detections[0, 0, i, 6] * h)
        bw = x2 - x1
        bh = y2 - y1
        if bw > 0 and bh > 0:
            boxes.append((x1, y1, bw, bh, confidence))

    if not boxes:
        return []

    # Return only the largest face (by area) to avoid multi-face confusion
    largest = max(boxes, key=lambda b: b[2] * b[3])
    x, y, bw, bh, conf = largest
    print(f"[INFO] DNN detected face at ({x},{y}) size {bw}x{bh} conf={conf:.3f}")

    # Clamp to image bounds
    x  = max(0, x)
    y  = max(0, y)
    bw = min(bw, w - x)
    bh = min(bh, h - y)

    if len(boxes) > 1:
        print(f"[INFO] {len(boxes)} faces detected — using largest only")

    return [(x, y, bw, bh)]


# ── 128-dim dlib Embedding Extraction ────────────────────────────────────────

def extract_embedding(face_crop: np.ndarray) -> Optional[np.ndarray]:
    """
    Extract a 128-dim dlib face embedding from a face crop.

    Parameters
    ----------
    face_crop : face region as BGR or grayscale np.ndarray

    Returns
    -------
    np.ndarray of shape (128,) normalized via L2, or None if extraction fails.
    """
    if face_crop is None or face_crop.size == 0:
        print("[WARNING] extract_embedding: empty crop")
        return None

    # Convert to RGB — face_recognition expects RGB
    if len(face_crop.shape) == 2:
        # Grayscale → RGB
        rgb = cv2.cvtColor(face_crop, cv2.COLOR_GRAY2RGB)
    else:
        # BGR → RGB
        rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)

    h, w = rgb.shape[:2]

    # face_recognition.face_encodings expects (top, right, bottom, left) in PIL coords
    known_locations = [(0, w, h, 0)]

    try:
        encodings = face_recognition.face_encodings(rgb, known_face_locations=known_locations, num_jitters=0)
    except Exception as e:
        print(f"[ERROR] face_recognition.face_encodings failed: {e}")
        return None

    if not encodings:
        print("[WARNING] extract_embedding: no encoding returned by dlib")
        return None

    emb = np.array(encodings[0], dtype=np.float32)
    norm = np.linalg.norm(emb)
    if norm < 1e-7:
        print("[WARNING] extract_embedding: zero-norm embedding")
        return None

    return emb / norm


# ── Quality Gate Helpers ──────────────────────────────────────────────────────

def _check_brightness(gray: np.ndarray) -> Optional[str]:
    """Returns error reason string if too dark, else None."""
    brightness = float(np.mean(gray))
    if brightness < 40:
        print(f"[WARNING] Frame rejected: too dark (mean={brightness:.1f})")
        return "Too dark. Find better lighting."
    return None

def _check_blur(gray: np.ndarray) -> Optional[str]:
    """Returns error reason string if too blurry, else None."""
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    if variance < 100:
        print(f"[WARNING] Frame rejected: too blurry (Laplacian var={variance:.1f})")
        return "Image is blurry. Hold the phone steady."
    return None

def _check_face_size(w: int, h: int, min_px: int = 100) -> Optional[str]:
    """Returns error reason string if face box too small, else None."""
    if w < min_px or h < min_px:
        print(f"[WARNING] Face box too small: {w}x{h} (min {min_px}x{min_px})")
        return f"Face too small ({w}x{h}px). Move closer and fill the oval."
    return None


# ── Main Public Function ──────────────────────────────────────────────────────

def detect_and_embed(
    img_bytes: bytes,
    require_single_face: bool = False,
) -> Optional[np.ndarray]:
    """
    Given raw JPEG/PNG bytes, detect the largest face and return a 128-dim
    L2-normalized dlib embedding, or None on any failure.

    Parameters
    ----------
    img_bytes           : raw image bytes (JPEG/PNG)
    require_single_face : if True, return None if 0 or 2+ faces detected.
                          Used during enrollment for strict quality control.
                          NO central crop fallback — this was causing garbage captures.

    Returns
    -------
    np.ndarray of shape (128,) or None
    """
    # ── Decode image ─────────────────────────────────────────────────────────
    nparr = np.frombuffer(img_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        print("[ERROR] detect_and_embed: could not decode image bytes")
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── Quality: Brightness ───────────────────────────────────────────────────
    brightness_err = _check_brightness(gray)
    if brightness_err:
        return None

    # ── Quality: Blur (whole frame — early rejection) ─────────────────────────
    blur_err = _check_blur(gray)
    if blur_err:
        return None

    # ── DNN Face Detection ────────────────────────────────────────────────────
    boxes = detect_faces_dnn(img)

    # No face detected
    if not boxes:
        if require_single_face:
            print("[WARNING] detect_and_embed: no face detected (require_single_face=True)")
        else:
            print("[WARNING] detect_and_embed: no face detected — skipping (no fallback)")
        return None

    # Multiple faces (only if require_single_face)
    if require_single_face:
        # detect_faces_dnn already returns only 1 (the largest), but log it
        print(f"[INFO] detect_and_embed: {len(boxes)} face(s) after DNN — using largest")

    x, y, bw, bh = boxes[0]

    # ── Quality: Face size ────────────────────────────────────────────────────
    size_err = _check_face_size(bw, bh)
    if size_err:
        return None

    # ── Crop face (BGR — extract_embedding handles color conversion) ──────────
    face_crop = img[max(0, y):min(img.shape[0], y + bh),
                    max(0, x):min(img.shape[1], x + bw)]

    if face_crop.size == 0:
        print("[ERROR] detect_and_embed: face crop is empty after DNN detection")
        return None

    # ── Extract 128-dim dlib embedding ───────────────────────────────────────
    emb = extract_embedding(face_crop)
    if emb is None:
        print("[WARNING] detect_and_embed: dlib returned no encoding for crop")
        return None

    print(f"[INFO] dlib 128-dim embedding extracted (norm={np.linalg.norm(emb):.4f})")
    return emb
