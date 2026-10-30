import cv2
import pickle
import numpy as np
import requests
import datetime
import insightface
from insightface.app import FaceAnalysis

print("[1/3] Loading face detection engine...")
app = FaceAnalysis(name="buffalo_s", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))

with open("embeddings.pkl", "rb") as f:
    known_embeddings = pickle.load(f)

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

SIMILARITY_THRESHOLD = 0.35
present_students = set()

print("[2/3] Starting camera feed...")
print("-> Press 's' to snapshot & submit attendance to ERP server.")
print("-> Press 'q' to quit.")

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    faces = app.get(frame)

    for face in faces:
        bbox = face.bbox.astype(int)
        embedding = face.embedding
        
        match_roll = None
        highest_score = -1.0

        for roll_no, known_emb in known_embeddings.items():
            score = float(cosine_similarity(embedding, known_emb))
            if score > highest_score:
                highest_score = score
                match_roll = roll_no

        if highest_score >= SIMILARITY_THRESHOLD and match_roll:
            present_students.add(match_roll)
            label = f"{match_roll} ({highest_score:.2f})"
            color = (0, 255, 0)
        else:
            label = f"Unknown ({highest_score:.2f})"
            color = (0, 0, 255)

        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
        cv2.putText(frame, label, (bbox[0], max(20, bbox[1] - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("ClassVision - Lecture Camera", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord('s'):
        print("[3/3] Finalizing lecture attendance snapshot...")
        break
    elif key == ord('q'):
        print("Camera closed without submitting.")
        cap.release()
        cv2.destroyAllWindows()
        exit()

cap.release()
cv2.destroyAllWindows()

today = datetime.date.today().isoformat()
subject_code = "BCA-301"
slot = "09:00 AM - 10:00 AM"

all_enrolled = list(known_embeddings.keys())
attendance_payload = []

for roll in all_enrolled:
    status = "PRESENT" if roll in present_students else "ABSENT"
    attendance_payload.append({
        "roll_number": roll,
        "status": status
    })

payload = {
    "subject_code": subject_code,
    "date": today,
    "slot": slot,
    "attendance": attendance_payload
}

try:
    res = requests.post("http://localhost:5000/api/attendance/bulk", json=payload)
    if res.status_code == 200:
        print(f"Attendance successfully logged in ERP for {len(attendance_payload)} student(s)!")
        print(f"Present list: {list(present_students)}")
    else:
        print(f"Server error: {res.text}")
except Exception as e:
    print(f"Failed to connect to backend: {e}")
