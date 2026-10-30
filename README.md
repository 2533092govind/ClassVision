# ClassVision ERP

[![Node.js](https://img.shields.io/badge/Node.js-v18+-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![InsightFace](https://img.shields.io/badge/InsightFace-buffalo__s-FF6F00)](https://github.com/deepinsight/insightface)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)

> **Autonomous AI Computer Vision Attendance & Academic ERP Suite**
> Complete role-based portal separation for Students and Faculty with real-time biometric face verification, liveness detection, and academic tracking.

---

## Overview
ClassVision bridges edge computer vision with enterprise college management. It eliminates manual classroom roll calls by running real-time facial recognition paired with dynamic landmark micromovement liveness verification to prevent photo spoofing.

The system features two isolated client applications backed by a shared transactional REST API engine:
- **Student ERP Console:** Personal attendance analytics, weekly lecture schedule, and CIE examination grading.
- **Faculty Management Portal:** Session roster inspector, manual override console, and live WebRTC camera attendance scanner.

---

## Key Modules

### 1. Biometric Attendance Engine (ai-engine/)
- **Deep Feature Extraction:** InsightFace (buffalo_s) generating 512-D normalized face embeddings.
- **Cosine Similarity Matching:** Sub-second identity classification across stored cohort embeddings.
- **Dynamic Anti-Spoofing:** Real-time eye aspect ratio (EAR) and facial landmark motion checks.
- **Bulk Transaction Sync:** Pushes verified attendance rosters directly to the Express backend via REST.

### 2. Faculty Administration Portal (/faculty.html)
- Standalone instructor workspace (zero student navigation components).
- Dynamic session filtering by Subject Code, Date, and Lecture Slot.
- Instant CSV attendance report generator.
- Continuous Internal Evaluation (CIE) test & lab grading recorder.
- In-browser WebRTC camera scanner (/camera.html) for phone/laptop attendance taking.

### 3. Student ERP Dashboard (/index.html)
- Dedicated student interface optimized for mobile and desktop viewports.
- Real-time overall and subject-level attendance compliance tracking (75% threshold indicator).
- Full Monday�Friday weekly lecture timetable with lab and classroom allocations.
- Continuous evaluation marks sheet (Sessional 1, Sessional 2, Lab Evaluations).

---

## Configured Curriculum (3rd Semester BCA)

| Code | Subject Name | Faculty | Room / Lab |
| :--- | :--- | :--- | :--- |
| **BCA3001T** | Python Programming | Dr. A. Verma | Computer Lab-2 |
| **BCA3002T** | Operating Systems | Prof. S. Srivastava | LH-201 |
| **BCA3003T** | Emerging Technologies | Dr. R. K. Singh | LH-202 |
| **BCA3004T** | Internet and Web Technology | Er. N. Dixit | Web Design Lab |
| **BCA3005T** | Software Engineering | Prof. P. Agrawal | LH-201 |

---

## Quick Start & Installation

### Option A: One-Click Windows Setup
```bash
setup.bat
run.bat
```

### Option B: Manual Setup
```bash
# Server Setup
cd server
npm install
node index.js

# AI Engine Setup
cd ../ai-engine
python -m venv venv
.\venv\Scripts\activate
pip install opencv-python numpy requests insightface onnxruntime
python recognize.py
```

---

## Default Access Credentials

| Role | Username / Identifier | Default Password | Target Workspace |
| :--- | :--- | :--- | :--- |
| **Student** | 25261102114 | pass123 | Student ERP Dashboard |
| **Faculty** | faculty | faculty123 | Faculty Academic Console |

---

## License
This project is open-source under the MIT License.
