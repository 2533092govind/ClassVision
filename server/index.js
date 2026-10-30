const express = require("express");
const cors = require("cors");
const path = require("path");
const db = require("./database");

const app = express();
app.use(cors());
app.use(express.json({ limit: "25mb" }));

// Serve Static Frontend Apps
app.use(express.static(path.join(__dirname, "../client")));

// Authentication
app.post("/api/auth/login", (req, res) => {
  const { username, password, role } = req.body;
  if (!username || !password || !role) return res.status(400).json({ error: "Missing fields" });

  const user = db.prepare("SELECT * FROM users WHERE username = ? AND password = ? AND role = ?").get(username.trim(), password.trim(), role);
  if (!user) return res.status(401).json({ error: "Invalid credentials" });

  res.json({
    status: "success",
    user: { username: user.username, role: user.role, displayName: user.display_name }
  });
});

// Subjects & Timetable
app.get("/api/subjects", (req, res) => res.json(db.prepare("SELECT * FROM subjects").all()));

app.get("/api/timetable", (req, res) => {
  const schedule = db.prepare(`
    SELECT t.day_of_week, t.time_slot, t.room_no, s.subject_code, s.subject_name, s.faculty
    FROM timetable t JOIN subjects s ON t.subject_code = s.subject_code
    ORDER BY CASE t.day_of_week 
      WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 
      WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 ELSE 6 END
  `).all();
  res.json(schedule);
});

// Marks
app.get("/api/marks/:rollNumber", (req, res) => {
  res.json(db.prepare(`
    SELECT m.exam_type, m.max_marks, m.obtained_marks, s.subject_code, s.subject_name
    FROM marks m JOIN subjects s ON m.subject_code = s.subject_code
    WHERE m.roll_number = ?
  `).all(req.params.rollNumber));
});

app.post("/api/marks/update", (req, res) => {
  const { roll_number, subject_code, exam_type, max_marks, obtained_marks } = req.body;
  db.prepare(`
    INSERT OR REPLACE INTO marks (roll_number, subject_code, exam_type, max_marks, obtained_marks)
    VALUES (?, ?, ?, ?, ?)
  `).run(roll_number, subject_code, exam_type, max_marks, obtained_marks);
  res.json({ status: "success" });
});

// Faculty Session
app.get("/api/attendance/session", (req, res) => {
  const { subject_code, date, slot } = req.query;
  res.json(db.prepare(`
    SELECT s.roll_number, s.name, COALESCE(ar.status, 'ABSENT') as status
    FROM students s
    LEFT JOIN attendance_records ar 
      ON s.roll_number = ar.roll_number 
      AND ar.subject_code = ? AND ar.date = ? AND ar.slot = ?
  `).all(subject_code, date, slot));
});

// Bulk Attendance ingestion from AI
app.post("/api/attendance/bulk", (req, res) => {
  const { subject_code, date, slot, attendance } = req.body;
  const insertStmt = db.prepare(`
    INSERT OR REPLACE INTO attendance_records (roll_number, subject_code, date, slot, status)
    VALUES (?, ?, ?, ?, ?)
  `);
  const tx = db.transaction((records) => {
    for (const r of records) {
      insertStmt.run(r.roll_number, subject_code, date, slot, r.status);
    }
  });
  tx(attendance);
  res.json({ status: "success", count: attendance.length });
});

// Student Profile
app.get("/api/student/:rollNumber", (req, res) => {
  const { rollNumber } = req.params;
  const student = db.prepare("SELECT * FROM students WHERE roll_number = ?").get(rollNumber);
  if (!student) return res.status(404).json({ error: "Student not found" });

  const totalClasses = db.prepare("SELECT COUNT(*) as count FROM attendance_records WHERE roll_number = ?").get(rollNumber).count;
  const attendedClasses = db.prepare("SELECT COUNT(*) as count FROM attendance_records WHERE roll_number = ? AND status = 'PRESENT'").get(rollNumber).count;
  const percentage = totalClasses > 0 ? ((attendedClasses / totalClasses) * 100).toFixed(1) : "100.0";

  const subjectStats = db.prepare(`
    SELECT s.subject_code, s.subject_name, s.faculty,
      COUNT(ar.id) as total,
      SUM(CASE WHEN ar.status = 'PRESENT' THEN 1 ELSE 0 END) as attended
    FROM subjects s
    LEFT JOIN attendance_records ar ON s.subject_code = ar.subject_code AND ar.roll_number = ?
    GROUP BY s.subject_code, s.subject_name, s.faculty
  `).all(rollNumber);

  res.json({ student, overallPercentage: parseFloat(percentage), totalClasses, attendedClasses, subjectStats });
});

const PORT = 5000;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`ClassVision Active on http://0.0.0.0:${PORT}`);
});
