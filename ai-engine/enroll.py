import os
import cv2
import pickle
import numpy as np
import insightface
from insightface.app import FaceAnalysis

print("[1/3] Loading face detection model (buffalo_s)...")
app = FaceAnalysis(name="buffalo_s", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))

DATASET_DIR = "students_dataset"
known_embeddings = {}

print("[2/3] Scanning dataset folder...")
if not os.path.exists(DATASET_DIR):
    print(f"Error: {DATASET_DIR} folder not found!")
    exit(1)

students = [d for d in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, d))]
print(f"Found student folders: {students}")

for roll_no in students:
    student_dir = os.path.join(DATASET_DIR, roll_no)
    vectors = []
    
    images = [f for f in os.listdir(student_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"Checking Roll {roll_no}: Found {len(images)} image(s)")
    
    for img_name in images:
        img_path = os.path.join(student_dir, img_name)
        img = cv2.imread(img_path)
        if img is None:
            print(f"  [!] Could not read image: {img_name}")
            continue

        faces = app.get(img)
        if len(faces) > 0:
            faces = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
            vectors.append(faces[0].embedding)
            print(f"  [+] Detected face in {img_name}")
        else:
            print(f"  [-] No face detected in {img_name}. Check lighting/angle.")

    if vectors:
        known_embeddings[roll_no] = np.mean(vectors, axis=0)
        print(f"==> Successfully enrolled: {roll_no}")
    else:
        print(f"==> Failed to enroll {roll_no}: No valid face found.")

print("[3/3] Saving vectors to embeddings.pkl...")
with open("embeddings.pkl", "wb") as f:
    pickle.dump(known_embeddings, f)

print(f"Done! Enrolled {len(known_embeddings)} student(s).")
