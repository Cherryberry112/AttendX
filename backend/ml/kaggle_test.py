# AttendX Kaggle Test Notebook
# Run this in a Kaggle Notebook to validate ML logic before deployment
# Enable GPU accelerator for faster processing

# Cell 1: Install dependencies
# !pip install insightface onnxruntime opencv-python-headless numpy Pillow -q

import cv2
import numpy as np
import base64
import json
from io import BytesIO
from PIL import Image
import insightface
from insightface.app import FaceAnalysis

# Cell 2: Load InsightFace model
app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))
print("Model loaded ✅")

# Cell 3: Test face detection on a sample image
# Upload a test image to Kaggle working directory first
def load_test_image(path):
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Image not found: {path}")
    return img

def get_embedding(img: np.ndarray) -> np.ndarray | None:
    faces = app.get(img)
    if not faces:
        return None
    face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
    emb = face.embedding.astype(np.float32)
    return emb / np.linalg.norm(emb)

# Cell 4: Cosine similarity test
def cosine_sim(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

# Cell 5: End-to-end test with two images
# img1 = load_test_image("/kaggle/working/person_a_1.jpg")
# img2 = load_test_image("/kaggle/working/person_a_2.jpg")
# img3 = load_test_image("/kaggle/working/person_b.jpg")
#
# emb1 = get_embedding(img1)
# emb2 = get_embedding(img2)
# emb3 = get_embedding(img3)
#
# print(f"Same person similarity: {cosine_sim(emb1, emb2):.4f} (expect > 0.45)")
# print(f"Diff person similarity: {cosine_sim(emb1, emb3):.4f} (expect < 0.45)")

# Cell 6: Multi-angle enrollment simulation
def simulate_enrollment(image_paths: list) -> np.ndarray:
    """
    Given paths to 5 images of the same person from different angles,
    returns averaged + normalized master embedding.
    """
    embeddings = []
    for path in image_paths:
        img = load_test_image(path)
        emb = get_embedding(img)
        if emb is not None:
            embeddings.append(emb)
    if not embeddings:
        raise ValueError("No faces detected in any provided image")
    master = np.mean(embeddings, axis=0)
    return master / np.linalg.norm(master)

print("All cells ready. Uncomment test sections to run with your images.")
