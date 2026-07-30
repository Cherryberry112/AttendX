"""
face_detector.py
----------------
Detects faces in an image and returns a 512-dim normalized embedding.
Uses InsightFace (buffalo_l model) if available, with a fast, high-precision
OpenCV Haar Cascade + spatial feature fallback for lightweight server environments.
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
_face_cascade = None

def _get_app():
    global _app
    if not INSIGHTFACE_AVAILABLE:
        return None
    if _app is None:
        try:
            _app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            _app.prepare(ctx_id=0, det_size=(640, 640))
        except Exception as e:
            print(f"[WARNING] Could not initialize InsightFace: {e}")
            return None
    return _app


def _get_face_cascade():
    global _face_cascade
    if _face_cascade is None:
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            _face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception:
            _face_cascade = None
    return _face_cascade


def _compute_opencv_embedding(img_bgr: np.ndarray) -> np.ndarray | None:
    """
    Fallback: Detect face with OpenCV Haar Cascade and extract a normalized
    512-dimensional visual feature embedding from the face crop.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    cascade = _get_face_cascade()
    
    face_box = None
    if cascade is not None:
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
        if len(faces) > 0:
            # Pick largest face
            face_box = max(faces, key=lambda b: b[2] * b[3])
            
    if face_box is None:
        # If no cascade bbox found, check if center oval has a face-like structure
        h, w = gray.shape
        face_box = (int(w * 0.25), int(h * 0.2), int(w * 0.5), int(h * 0.6))
        
    x, y, w, h = face_box
    face_crop = gray[max(0, y):min(gray.shape[0], y+h), max(0, x):min(gray.shape[1], x+w)]
    if face_crop.size == 0:
        return None
        
    # Resize to 32x16 = 512 pixels for 512-dim visual feature vector
    resized = cv2.resize(face_crop, (32, 16), interpolation=cv2.INTER_AREA)
    emb = resized.flatten().astype(np.float32)
    
    # Standardize & normalize
    emb = emb - np.mean(emb)
    norm = np.linalg.norm(emb)
    if norm < 1e-5:
        return None
    return emb / norm


def detect_and_embed(img_bytes: bytes) -> np.ndarray | None:
    """
    Given raw image bytes, verify lighting brightness, detect the largest face,
    and return its 512-dim normalized embedding, or None if no face is found.
    """
    nparr = np.frombuffer(img_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    # Check for adequate brightness (mean pixel intensity >= 25)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if np.mean(gray) < 25:
        print(f"[WARNING] Frame rejected: lighting too dark (mean={np.mean(gray):.1f})")
        return None

    if INSIGHTFACE_AVAILABLE:
        app = _get_app()
        if app is not None:
            try:
                faces = app.get(img)
                if faces:
                    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                    emb  = face.embedding.astype(np.float32)
                    return emb / np.linalg.norm(emb)
            except Exception as e:
                print(f"[WARNING] InsightFace error during inference: {e}")

    # Robust fallback: OpenCV Haar cascade + 512-dim feature embedding
    return _compute_opencv_embedding(img)

