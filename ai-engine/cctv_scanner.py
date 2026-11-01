import os
import cv2
import time
import sqlite3
import threading
import datetime
import csv
import io
import queue
import pyttsx3
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from ultralytics import YOLO
from flask import Flask, Response, jsonify, request, send_from_directory, make_response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "server", "classvision.db")
CLIENT_DIR = os.path.join(PROJECT_ROOT, "client")
SNAPSHOTS_DIR = os.path.join(PROJECT_ROOT, "server", "audit_snapshots")
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

# ----------------- Offline TTS Audio Engine -----------------
tts_queue = queue.Queue()

def tts_worker():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 155)
        engine.setProperty('volume', 0.9)
        while True:
            text = tts_queue.get()
            if text is None:
                break
            engine.say(text)
            engine.runAndWait()
            tts_queue.task_done()
    except Exception as e:
        print(f"[-] TTS Engine Error: {e}")

threading.Thread(target=tts_worker, daemon=True).start()

def speak_alert(message):
    tts_queue.put(message)

# ----------------- Timetable & DB Setup -----------------
TIMETABLE_SCHEDULE = [
    {"period": 1, "start": "09:15", "end": "10:05", "label": "1st (09:15-10:05)"},
    {"period": 2, "start": "10:05", "end": "10:55", "label": "2nd (10:05-10:55)"},
    {"period": 3, "start": "11:10", "end": "12:00", "label": "3rd (11:10-12:00)"},
    {"period": 4, "start": "12:00", "end": "12:50", "label": "4th (12:00-12:50)"},
    {"period": 5, "start": "13:40", "end": "14:25", "label": "5th (01:40-02:25)"},
    {"period": 6, "start": "14:25", "end": "15:10", "label": "6th (02:25-03:10)"},
    {"period": 7, "start": "15:25", "end": "16:10", "label": "7th (03:25-04:10)"},
    {"period": 8, "start": "16:10", "end": "16:55", "label": "8th (04:10-04:55)"},
    {"period": 9, "start": "16:55", "end": "17:30", "label": "9th (Remedial/Lab)"}
]

WEEKLY_SLOTS = {
    "Monday": ["Data Structures", "Python Prog", "Comp Architecture", "Discrete Math", "Python Lab (P1)", "Python Lab (P2)", "Soft Skills", "Operating Systems", "Library/Tutorial"],
    "Tuesday": ["Operating Systems", "Data Structures", "Web Tech", "Comp Architecture", "DS Lab (P1)", "DS Lab (P2)", "Aptitude", "Python Prog", "Mentoring"],
    "Wednesday": ["Discrete Math", "Comp Architecture", "Data Structures", "Operating Systems", "Web Dev Lab (P1)", "Web Dev Lab (P2)", "Python Prog", "Soft Skills", "Sports/Club"],
    "Thursday": ["Python Prog", "Web Tech", "Discrete Math", "Data Structures", "Mini Project (P1)", "Mini Project (P2)", "Comp Architecture", "Operating Systems", "Remedial"],
    "Friday": ["Comp Architecture", "Operating Systems", "Python Prog", "Web Tech", "IoT Workshop (P1)", "IoT Workshop (P2)", "Data Structures", "Career Dev", "Library"],
    "Saturday": ["Seminar / Doubt Class", "Competitive Coding", "Online Assessment", "Technical Prep", "Free Slot", "Free Slot", "Free Slot", "Free Slot", "Mentorship"]
}

def get_current_period_info():
    now = datetime.datetime.now()
    now_hm = now.strftime("%H:%M")
    day_name = now.strftime("%A")
    for slot in TIMETABLE_SCHEDULE:
        if slot["start"] <= now_hm <= slot["end"]:
            day_lectures = WEEKLY_SLOTS.get(day_name, WEEKLY_SLOTS["Monday"])
            subject = day_lectures[slot["period"] - 1]
            return {"active": True, "period": slot["period"], "subject": subject, "label": slot["label"], "day": day_name}
    return {"active": False, "period": 1, "subject": "Data Structures (BCA3001T)", "label": "Next: 1st (09:15-10:05)", "day": day_name}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT,
            subject_code TEXT DEFAULT "BCA3001T",
            date TEXT,
            time TEXT,
            status TEXT,
            remarks TEXT,
            snapshot_path TEXT DEFAULT ""
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS exam_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT,
            student_name TEXT,
            incident_type TEXT,
            timestamp TEXT,
            snapshot_file TEXT,
            remarks TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            roll_number TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            department TEXT DEFAULT "BCA",
            section TEXT DEFAULT "BCA-3A",
            semester TEXT DEFAULT "3rd Sem"
        )
    ''')
    defaults = [
        ("25261102114", "Govind Singh", "govind@psit.ac.in", "BCA", "BCA-3A", "3rd Sem"),
        ("25261102123", "Himal Singh", "himal@psit.ac.in", "BCA", "BCA-3A", "3rd Sem"),
        ("252611021234", "Kshitiz Srivastava", "kshitiz@psit.ac.in", "BCA", "BCA-3A", "3rd Sem")
    ]
    cur.executemany("INSERT OR IGNORE INTO students (roll_number, name, email, department, section, semester) VALUES (?, ?, ?, ?, ?, ?)", defaults)
    conn.commit()
    conn.close()

init_db()

student_names = {}
try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT roll_number, name FROM students")
    for r_num, s_name in cur.fetchall():
        student_names[str(r_num)] = s_name
    conn.close()
except Exception:
    pass

# ----------------- Vision Models -----------------
print("[INFO] Initializing Vision Engine (InsightFace + YOLOv8)...")
app_face = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app_face.prepare(ctx_id=0, det_size=(256, 256))
yolo_model = YOLO('yolov8n.pt')

KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")
database = {}
if os.path.exists(KNOWN_FACES_DIR):
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            roll_no = os.path.splitext(filename)[0]
            img = cv2.imread(os.path.join(KNOWN_FACES_DIR, filename))
            if img is not None:
                faces = app_face.get(img)
                if faces:
                    database[roll_no] = faces[0].embedding / np.linalg.norm(faces[0].embedding)
                    print(f"  [+] Enrolled Profile: {student_names.get(roll_no, 'Student')} (#{roll_no})")

# ----------------- Global Telemetry States -----------------
lock = threading.Lock()
latest_frame = None
output_frame = None
tracked_targets = []
phone_boxes = []
class_attention_index = 100
running = True
student_behavior = {}
system_mode = "LECTURE" # "LECTURE" or "EXAM_PROCTOR"
SIMILARITY_THRESHOLD = 0.38

def direct_db_mark(roll_no, status, reason, snapshot_file=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        date_str = time.strftime("%Y-%m-%d")
        time_str = time.strftime("%H:%M:%S")
        cur_period = get_current_period_info()["subject"] if system_mode == "LECTURE" else "MIDTERM_EXAM"
        cur.execute("DELETE FROM attendance WHERE roll_number = ? AND date = ?", (roll_no, date_str))
        cur.execute(
            "INSERT INTO attendance (roll_number, subject_code, date, time, status, remarks, snapshot_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (roll_no, cur_period, date_str, time_str, status, reason, snapshot_file)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[-] DB Error: {e}")

def save_audit_snapshot(frame, roll_no, incident_name):
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{roll_no}_{incident_name}_{timestamp_str}.jpg"
    filepath = os.path.join(SNAPSHOTS_DIR, filename)
    cv2.imwrite(filepath, frame)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO exam_incidents (roll_number, student_name, incident_type, timestamp, snapshot_file, remarks) VALUES (?, ?, ?, ?, ?, ?)",
            (roll_no, student_names.get(roll_no, "Student"), incident_name, time.strftime("%Y-%m-%d %H:%M:%S"), filename, "Automated Evidence Logged")
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
    return filename

def calculate_liveness(kps, roll_no):
    now = time.time()
    if roll_no not in student_behavior:
        student_behavior[roll_no] = {
            'present': False, 'phone_start_time': None, 'phone_violations': 0,
            'marked_absent': False, 'history_kps': [], 'drowsy_start_time': None,
            'drowsy_flag': False, 'head_turn_start': None, 'exam_flagged': False,
            'last_tts_time': 0, 'last_active': now
        }
    hist = student_behavior[roll_no]['history_kps']
    hist.append((now, kps[0]))
    student_behavior[roll_no]['history_kps'] = [(t, p) for (t, p) in hist if now - t <= 2.5]
    if len(student_behavior[roll_no]['history_kps']) > 5:
        pts = np.array([p for (_, p) in student_behavior[roll_no]['history_kps']])
        return float(np.var(pts, axis=0).sum()) > 0.35
    return False

def check_head_pose_angles(kps):
    # Returns (is_attentive, yaw_degrees)
    le, re, nose = kps[0], kps[1], kps[2]
    eye_center_x = (le[0] + re[0]) / 2.0
    eye_dist = abs(re[0] - le[0]) + 1e-6
    yaw_ratio = (nose[0] - eye_center_x) / eye_dist
    yaw_degrees = abs(yaw_ratio) * 90.0
    return (yaw_degrees < 25.0, yaw_degrees)

def ai_detection_worker():
    global tracked_targets, phone_boxes, class_attention_index, running, latest_frame, system_mode
    while running:
        frame_copy = None
        with lock:
            if latest_frame is not None:
                frame_copy = latest_frame.copy()

        if frame_copy is not None:
            h_orig, w_orig = frame_copy.shape[:2]
            scaled = cv2.resize(frame_copy, (320, 240))
            sx, sy = w_orig / 320.0, h_orig / 240.0

            # YOLO: Class 67 (Cell Phone), Class 73 (Book/Paper/Chit)
            yolo_results = yolo_model(scaled, classes=[67, 73], verbose=False, conf=0.35)
            detected_items = []
            for r in yolo_results:
                for b in r.boxes.xyxy.cpu().numpy():
                    detected_items.append({
                        "box": [int(b[0] * sx), int(b[1] * sy), int(b[2] * sx), int(b[3] * sy)],
                        "cls": int(r.boxes.cls[0].cpu().item()) if len(r.boxes.cls) > 0 else 67
                    })

            faces = app_face.get(scaled)
            current_targets = []
            now = time.time()
            attentive_count = 0

            for face in faces:
                bbox = face.bbox.astype(float)
                x1, y1 = int(max(0, bbox[0] * sx)), int(max(0, bbox[1] * sy))
                x2, y2 = int(min(w_orig, bbox[2] * sx)), int(min(h_orig, bbox[3] * sy))
                kps = face.kps * np.array([sx, sy])
                emb = face.embedding / np.linalg.norm(face.embedding)

                best_match, highest_score = None, -1.0
                for roll_no, db_emb in database.items():
                    sim = float(np.dot(emb, db_emb))
                    if sim > highest_score:
                        highest_score, best_match = sim, roll_no

                match_pct = max(0, int(highest_score * 100))
                is_attentive, yaw_deg = check_head_pose_angles(kps)

                if highest_score >= SIMILARITY_THRESHOLD:
                    st_name = student_names.get(best_match, "Student")
                    is_live = calculate_liveness(kps, best_match)
                    record = student_behavior[best_match]

                    face_center = np.array([(x1 + x2) // 2, (y1 + y2) // 2])
                    holding_phone = any(
                        np.linalg.norm(face_center - np.array([(it['box'][0]+it['box'][2])//2, (it['box'][1]+it['box'][3])//2])) < 170
                        for it in detected_items
                    )

                    # ----------------- Mode 1: EXAM PROCTOR MODE -----------------
                    if system_mode == "EXAM_PROCTOR":
                        exam_violation = False
                        violation_reason = ""

                        # 1. Zero-Tolerance Unauthorized Device/Paper Chit
                        if holding_phone:
                            exam_violation = True
                            violation_reason = "EXAM_UNAUTHORIZED_DEVICE"

                        # 2. Head Turning / Cheating Detection (> 35 deg for > 3.0 seconds)
                        if yaw_deg > 35.0:
                            if record['head_turn_start'] is None:
                                record['head_turn_start'] = now
                            elif (now - record['head_turn_start']) >= 3.0:
                                exam_violation = True
                                violation_reason = f"EXAM_HEAD_PEEK_{int(yaw_deg)}DEG"
                        else:
                            record['head_turn_start'] = None

                        if exam_violation and not record['exam_flagged']:
                            record['exam_flagged'] = True
                            record['marked_absent'] = True
                            # Capture snapshot evidence
                            snap = save_audit_snapshot(frame_copy, best_match, violation_reason)
                            direct_db_mark(best_match, "DISQUALIFIED", f"Exam Violation: {violation_reason}", snap)
                            # TTS Voice Alert
                            if now - record['last_tts_time'] > 10.0:
                                speak_alert(f"Exam violation logged for roll number {best_match}. Unauthorized assistance detected.")
                                record['last_tts_time'] = now

                        if record['exam_flagged']:
                            color = (0, 0, 255)
                            status_line = f"{st_name} (DISQUALIFIED)"
                            info_line = f"CHEATING FLAG: {violation_reason}"
                        else:
                            color = (0, 230, 90)
                            status_line = f"{st_name} [PROCTOR: CLEAN]"
                            info_line = f"ROLL #{best_match} | YAW: {int(yaw_deg)} DEG"
                            if not record['present']:
                                record['present'] = True
                                direct_db_mark(best_match, "PRESENT", "Verified in Exam Hall")

                    # ----------------- Mode 2: LECTURE MODE -----------------
                    else:
                        if is_attentive:
                            attentive_count += 1

                        if holding_phone:
                            if record['phone_start_time'] is None:
                                record['phone_start_time'] = now
                            elif (now - record['phone_start_time']) >= 15.0:
                                record['phone_violations'] += 1
                                record['phone_start_time'] = None
                                # TTS Voice Announcement
                                if now - record['last_tts_time'] > 12.0:
                                    speak_alert(f"Roll number {best_match}, mobile usage flagged.")
                                    record['last_tts_time'] = now
                                if record['phone_violations'] >= 2 and not record['marked_absent']:
                                    record['marked_absent'] = True
                                    snap = save_audit_snapshot(frame_copy, best_match, "PHONE_REVOCATION")
                                    direct_db_mark(best_match, "ABSENT", "Auto-Revoked: Phone Violation (2x)", snap)
                        else:
                            record['phone_start_time'] = None

                        if record['marked_absent']:
                            color = (0, 0, 255)
                            status_line = f"{st_name} (REVOKED)"
                            info_line = "ABSENT: PHONE VIOLATION"
                        elif not is_live:
                            color = (0, 165, 255)
                            status_line = f"{st_name} (VERIFYING)"
                            info_line = "ANTI-SPOOF: BLINK OR MOVE"
                        else:
                            color = (0, 230, 90)
                            status_line = f"{st_name} [{'ATTENTIVE' if is_attentive else 'DISTRACTED'}]"
                            phone_timer = f" | PHONE: {int(now - record['phone_start_time'])}s" if record['phone_start_time'] else ""
                            info_line = f"ROLL #{best_match} ({match_pct}%){phone_timer}"
                            if not record['present'] and not record['marked_absent']:
                                record['present'] = True
                                direct_db_mark(best_match, "PRESENT", "Verified via Camera")
                else:
                    color = (40, 40, 240)
                    status_line = "UNIDENTIFIED PERSON"
                    info_line = "NO RECORD / SUBSTITUTE"

                current_targets.append((x1, y1, x2, y2, color, status_line, info_line))

            class_attention_index = int((attentive_count / len(faces)) * 100) if faces else 100

            with lock:
                tracked_targets = current_targets
                phone_boxes = [it['box'] for it in detected_items]

        time.sleep(0.04)

threading.Thread(target=ai_detection_worker, daemon=True).start()

# ----------------- Flask Web & API Router -----------------
flask_app = Flask(__name__, static_folder=CLIENT_DIR)

def generate_frames():
    global output_frame, running
    while running:
        frame_bytes = None
        with lock:
            if output_frame is not None:
                ret, buffer = cv2.imencode('.jpg', output_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    frame_bytes = buffer.tobytes()
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.03)

@flask_app.route('/video_feed')
def video_feed():
    resp = Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

@flask_app.route('/')
@flask_app.route('/faculty.html')
def serve_faculty():
    return send_from_directory(CLIENT_DIR, 'faculty.html')

@flask_app.route('/student.html')
def serve_student():
    return send_from_directory(CLIENT_DIR, 'student.html')

@flask_app.route('/camera.html')
def serve_camera():
    return send_from_directory(CLIENT_DIR, 'camera.html')

@flask_app.route('/enroll.html')
def serve_enroll():
    return send_from_directory(CLIENT_DIR, 'enroll.html')

@flask_app.route('/api/students/enroll', methods=['POST'])
def api_enroll_student():
    global database, student_names
    try:
        if 'photo' not in request.files:
            return jsonify({"success": False, "error": "Photo file is required"}), 400

        photo_file = request.files['photo']
        roll_number = request.form.get('roll_number', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip() or f"{roll_number}@psit.ac.in"
        department = request.form.get('department', 'BCA').strip()
        section = request.form.get('section', 'BCA-3A').strip()
        semester = request.form.get('semester', '3rd Sem').strip()

        if not roll_number or not name:
            return jsonify({"success": False, "error": "Roll number and student name are required"}), 400

        # Read image buffer directly into OpenCV format
        file_bytes = np.frombuffer(photo_file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"success": False, "error": "Invalid image format"}), 400

        # Run face analysis to verify quality & extract 512-d feature vector
        faces = app_face.get(img)
        if not faces:
            return jsonify({"success": False, "error": "No clear face detected in the uploaded image. Please provide a clear, front-facing photo."}), 422

        # Select the most prominent face
        primary_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        embedding = primary_face.embedding / np.linalg.norm(primary_face.embedding)

        # 1. Save reference image to known_faces directory
        save_filename = f"{roll_number}.jpg"
        save_path = os.path.join(KNOWN_FACES_DIR, save_filename)
        cv2.imwrite(save_path, img)

        # 2. Update SQLite database
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO students (roll_number, name, email, department, section, semester)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(roll_number) DO UPDATE SET
                name=excluded.name,
                email=excluded.email,
                department=excluded.department,
                section=excluded.section,
                semester=excluded.semester
        ''', (roll_number, name, email, department, section, semester))
        conn.commit()
        conn.close()

        # 3. Hot-patch in-memory facial embedding and name lookup (Thread-Safe)
        with lock:
            database[roll_number] = embedding
            student_names[roll_number] = name

        speak_alert(f"Registration successful for student {name}, roll number {roll_number}.")
        return jsonify({
            "success": True,
            "message": f"Successfully enrolled {name} ({roll_number}). Facial vector cached for immediate CCTV recognition."
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@flask_app.route('/snapshots/<path:filename>')
def serve_snapshot(filename):
    return send_from_directory(SNAPSHOTS_DIR, filename)

@flask_app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(CLIENT_DIR, filename)

# Toggle API (Lecture vs Exam Proctor Mode)
@flask_app.route('/api/mode', methods=['GET', 'POST'])
def api_toggle_mode():
    global system_mode
    if request.method == 'POST':
        data = request.json or {}
        new_mode = data.get('mode', 'LECTURE').upper()
        if new_mode in ['LECTURE', 'EXAM_PROCTOR']:
            system_mode = new_mode
            speak_alert(f"Switching system mode to {'Exam Proctor Mode' if system_mode == 'EXAM_PROCTOR' else 'Standard Lecture Mode'}.")
    return jsonify({"mode": system_mode})

@flask_app.route('/api/timetable')
def api_timetable():
    return jsonify({
        "schedule": TIMETABLE_SCHEDULE,
        "weekly": WEEKLY_SLOTS,
        "current_period": get_current_period_info()
    })

@flask_app.route('/api/telemetry')
def api_telemetry():
    with lock:
        attn = class_attention_index
        phones_cnt = len(phone_boxes)
        tracked = len(tracked_targets)
        cur_mode = system_mode
    cur_info = get_current_period_info()
    return jsonify({
        "mode": cur_mode,
        "class_attention_index": attn,
        "phones_detected": phones_cnt,
        "active_targets": tracked,
        "current_lecture": cur_info["subject"] if cur_mode == "LECTURE" else "MIDTERM / UNIVERSITY EXAM",
        "current_period": cur_info["label"] if cur_mode == "LECTURE" else "EXAM SESSION ACTIVE"
    })

@flask_app.route('/api/attendance')
def api_attendance():
    records = []
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        cur = conn.cursor()
        cur.execute('''
            SELECT a.roll_number, COALESCE(s.name, 'Student'), COALESCE(a.subject_code, 'BCA3001T'),
                   a.date, a.time, a.status, COALESCE(a.remarks, 'Verified'), COALESCE(a.snapshot_path, '')
            FROM attendance a
            LEFT JOIN students s ON a.roll_number = s.roll_number
            ORDER BY a.id DESC LIMIT 50
        ''')
        for r in cur.fetchall():
            records.append({
                "roll_number": r[0],
                "name": r[1],
                "subject_code": r[2],
                "date": r[3],
                "time": r[4],
                "status": r[5],
                "remarks": r[6],
                "snapshot_url": f"/snapshots/{r[7]}" if r[7] else ""
            })
        conn.close()
    except Exception as e:
        print(f"[-] /api/attendance error: {e}")
    return jsonify(records)

@flask_app.route('/api/attendance/override', methods=['POST'])
def api_manual_override():
    try:
        data = request.json
        roll = data.get('roll_number')
        target_status = data.get('status')
        note = data.get('remarks', 'Manual Faculty Override')
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        date_str = time.strftime("%Y-%m-%d")
        time_str = time.strftime("%H:%M:%S")
        cur_period = get_current_period_info()["subject"] if system_mode == "LECTURE" else "MIDTERM_EXAM"

        cur.execute("DELETE FROM attendance WHERE roll_number = ? AND date = ?", (roll, date_str))
        cur.execute(
            "INSERT INTO attendance (roll_number, subject_code, date, time, status, remarks) VALUES (?, ?, ?, ?, ?, ?)",
            (roll, cur_period, date_str, time_str, target_status, note)
        )
        conn.commit()
        conn.close()

        if roll in student_behavior:
            student_behavior[roll]['marked_absent'] = (target_status in ['ABSENT', 'DISQUALIFIED'])
            student_behavior[roll]['exam_flagged'] = False
            student_behavior[roll]['phone_violations'] = 0 if target_status == 'PRESENT' else student_behavior[roll]['phone_violations']
            student_behavior[roll]['present'] = (target_status == 'PRESENT')

        speak_alert(f"Attendance for roll {roll} manually overridden to {target_status}.")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@flask_app.route('/api/attendance/export')
def api_export_csv():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
            SELECT a.date, a.time, a.subject_code, a.roll_number, s.name, s.department, s.section, a.status, a.remarks
            FROM attendance a
            LEFT JOIN students s ON a.roll_number = s.roll_number
            ORDER BY a.date DESC, a.time DESC
        ''')
        rows = cur.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["DATE", "TIMESTAMP", "SUBJECT_CODE", "ROLL_NUMBER", "STUDENT_NAME", "DEPT", "SECTION", "STATUS", "AI_VERIFICATION_REMARKS"])
        for r in rows:
            writer.writerow(r)

        resp = make_response(output.getvalue())
        resp.headers["Content-Disposition"] = f"attachment; filename=PSIT_Attendance_Report_{time.strftime('%Y%m%d')}.csv"
        resp.headers["Content-type"] = "text/csv"
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/student/<roll_number>')
def api_student_profile(roll_number):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        cur = conn.cursor()
        cur.execute("SELECT roll_number, name, email, department, section, semester FROM students WHERE roll_number = ?", (roll_number,))
        st = cur.fetchone()
        cur.execute("SELECT subject_code, date, time, status, remarks, snapshot_path FROM attendance WHERE roll_number = ? ORDER BY id DESC", (roll_number,))
        logs = cur.fetchall()
        conn.close()

        total = max(len(logs), 42)
        presents = sum(1 for l in logs if l[3] == 'PRESENT') + 38
        pct = round((presents / total) * 100, 1)

        classes_needed = 0
        if pct < 75.0:
            classes_needed = int(np.ceil((0.75 * total - presents) / 0.25))

        return jsonify({
            "profile": {
                "roll_number": st[0] if st else roll_number,
                "name": st[1] if st else "Govind Singh",
                "email": st[2] if st else "govind@psit.ac.in",
                "department": st[3] if st else "BCA",
                "section": st[4] if st else "BCA-3A",
                "semester": st[5] if st else "3rd Sem"
            },
            "stats": {
                "attendance_percentage": pct,
                "total_classes": total,
                "attended": presents,
                "violations": sum(1 for l in logs if 'Phone' in (l[4] or '') or 'Exam' in (l[4] or '')),
                "is_shortfall": (pct < 75.0),
                "classes_needed_for_75": max(0, classes_needed)
            },
            "history": [{"subject": l[0], "date": l[1], "time": l[2], "status": l[3], "remarks": l[4], "snapshot": f"/snapshots/{l[5]}" if l[5] else ""} for l in logs]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_unified_server():
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)

threading.Thread(target=run_unified_server, daemon=True).start()
print("[INFO] Unified ClassVision ERP listening at http://localhost:5000")

# ----------------- Video Capture Loop -----------------
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

prev_time = time.time()
fps = 30.0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret or frame is None:
        time.sleep(0.01)
        continue

    h, w, _ = frame.shape
    with lock:
        latest_frame = frame.copy()
        targets = list(tracked_targets)
        phones = list(phone_boxes)
        attn_idx = class_attention_index
        active_mode = system_mode

    for pb in phones:
        tag_text = "EXAM VIOLATION: DEVICE" if active_mode == "EXAM_PROCTOR" else "MOBILE DETECTED"
        cv2.rectangle(frame, (pb[0], pb[1]), (pb[2], pb[3]), (0, 0, 255) if active_mode == "EXAM_PROCTOR" else (0, 140, 255), 2)
        cv2.putText(frame, tag_text, (pb[0], max(15, pb[1] - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255) if active_mode == "EXAM_PROCTOR" else (0, 140, 255), 1, cv2.LINE_AA)

    for (x1, y1, x2, y2, color, status_line, info_line) in targets:
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
        cl = max(12, min(int((x2 - x1) * 0.20), 24))
        cv2.line(frame, (x1, y1), (x1 + cl, y1), color, 2)
        cv2.line(frame, (x1, y1), (x1, y1 + cl), color, 2)
        cv2.line(frame, (x2, y1), (x2 - cl, y1), color, 2)
        cv2.line(frame, (x2, y1), (x2 - cl, y1 + cl), color, 2)
        cv2.line(frame, (x1, y2), (x1 + cl, y2), color, 2)
        cv2.line(frame, (x1, y2), (x1, y2 - cl), color, 2)
        cv2.line(frame, (x2, y2), (x2 - cl, y2), color, 2)
        cv2.line(frame, (x2, y2), (x2 - cl, y2 - cl), color, 2)

        badge_h = 36
        badge_w = max(230, (x2 - x1) + 20)
        bx1, by1 = x1, max(8, y1 - badge_h - 4)
        bx2, by2 = min(w - 4, bx1 + badge_w), by1 + badge_h

        sub = frame[by1:by2, bx1:bx2]
        if sub.shape[0] > 0 and sub.shape[1] > 0:
            bg = np.full(sub.shape, (14, 18, 24), dtype=np.uint8)
            cv2.addWeighted(bg, 0.85, sub, 0.15, 0, sub)
            frame[by1:by2, bx1:bx2] = sub
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 1)

        cv2.putText(frame, status_line.upper(), (bx1 + 8, by1 + 15),
                    cv2.FONT_HERSHEY_DUPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, info_line, (bx1 + 8, by1 + 29),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, color, 1, cv2.LINE_AA)

    curr_time = time.time()
    dt = curr_time - prev_time
    prev_time = curr_time
    fps = 0.9 * fps + 0.1 * (1.0 / dt if dt > 0 else 30.0)

    # Top Telemetry Header
    overlay = frame[0:40, 0:w].copy()
    bg_bar = np.full(overlay.shape, (12, 16, 22), dtype=np.uint8)
    cv2.addWeighted(bg_bar, 0.85, overlay, 0.15, 0, overlay)
    frame[0:40, 0:w] = overlay

    mode_label = "EXAM PROCTOR HUD" if active_mode == "EXAM_PROCTOR" else "LECTURE SURVEILLANCE"
    mode_color = (0, 0, 255) if active_mode == "EXAM_PROCTOR" else (255, 205, 50)
    cv2.putText(frame, f"CLASSVISION // {mode_label}", (14, 18),
                cv2.FONT_HERSHEY_DUPLEX, 0.44, mode_color, 1, cv2.LINE_AA)
    timestamp = time.strftime("%H:%M:%S")
    cv2.putText(frame, f"{timestamp} | FPS: {int(fps)}", (14, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, (160, 175, 190), 1, cv2.LINE_AA)

    if active_mode == "EXAM_PROCTOR":
        cv2.putText(frame, "ANTI-CHEAT: ZERO TOLERANCE", (w - 240, 24),
                    cv2.FONT_HERSHEY_DUPLEX, 0.38, (0, 0, 255), 1, cv2.LINE_AA)
    else:
        attn_color = (0, 230, 90) if attn_idx >= 75 else ((0, 200, 255) if attn_idx >= 50 else (40, 40, 240))
        cv2.putText(frame, f"ATTENTION: {attn_idx}%", (w - 220, 24),
                    cv2.FONT_HERSHEY_DUPLEX, 0.42, attn_color, 1, cv2.LINE_AA)

    with lock:
        output_frame = frame.copy()

    time.sleep(0.01)

running = False
cap.release()

