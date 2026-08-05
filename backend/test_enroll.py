import sys, base64, numpy as np, cv2
sys.path.insert(0, '.')

from ml.face_detector import detect_and_embed

def make_test_frame(brightness=140):
    img = np.ones((480, 640, 3), dtype=np.uint8) * brightness
    cv2.ellipse(img, (320, 240), (110, 140), 0, 0, 360, (200, 190, 180), -1)
    cv2.circle(img, (280, 195), 18, (60, 50, 40), -1)
    cv2.circle(img, (360, 195), 18, (60, 50, 40), -1)
    cv2.ellipse(img, (320, 280), (40, 20), 0, 0, 180, (140, 100, 90), 2)
    _, buf = cv2.imencode('.jpg', img)
    return buf.tobytes()

results = []
for i in range(5):
    raw = make_test_frame(brightness=120 + i*10)
    emb = detect_and_embed(raw)
    ok = emb is not None
    results.append(ok)
    shape_str = str(emb.shape) if emb is not None else "None"
    print(f"Frame {i+1}: {'OK' if ok else 'FAILED'} shape={shape_str}")

good = sum(results)
print(f"SUCCESS: {good}/5 frames produced embeddings")
if good >= 3:
    print("ENROLLMENT WOULD SUCCEED")
else:
    print("ENROLLMENT WOULD FAIL")
