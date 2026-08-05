import numpy as np

def find_match(faces: list[dict], enrolled: list[dict], threshold: float = 0.50) -> list[dict]:
    results = []
    for face in faces:
        desc = np.array(face["descriptor"], dtype=np.float32)
        best_dist = float('inf')
        second_dist = float('inf')
        best_student = None
        
        for s in enrolled:
            student_best = min(
                np.linalg.norm(desc - emb)
                for emb in s["embeddings"]
            )
            if student_best < best_dist:
                second_dist = best_dist
                best_dist = student_best
                best_student = s
            elif student_best < second_dist:
                second_dist = student_best
        
        margin = second_dist - best_dist
        base = {
            "student_id": best_student["student_id"] if best_student else None,
            "sid": best_student["sid"] if best_student else None,
            "name": best_student["name"] if best_student else "Unknown",
            "confidence": round(1 - best_dist, 4),
            "bbox": face.get("bbox"),
        }
        if best_student and best_dist <= threshold and margin >= 0.10:
            results.append(base)
        else:
            base["student_id"] = None
            base["sid"] = None
            base["name"] = "Unknown"
            results.append(base)
    return results
