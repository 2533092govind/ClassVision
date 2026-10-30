const express = require("express");
const cors = require("cors");
const path = require("path");
const db = require("./database");

const app = express();
app.use(cors());
app.use(express.json({ limit: "25mb" }));
app.use(express.static(path.join(__dirname, "../client")));

app.post("/api/auth/login", (req, res) => {
  const { username, password, role } = req.body;
  db.get("SELECT * FROM users WHERE username = ? AND password = ? AND role = ?", [username, password, role], (err, user) => {
    if (err || !user) return res.status(401).json({ error: "Invalid credentials" });
    res.json({ status: "success", user: { username: user.username, role: user.role, displayName: user.display_name } });
  });
});

app.get("/api/subjects", (req, res) => {
  db.all("SELECT * FROM subjects", [], (err, rows) => res.json(rows || []));
});

app.get("/api/timetable", (req, res) => {
  db.all("SELECT t.*, s.subject_name, s.faculty FROM timetable t JOIN subjects s ON t.subject_code = s.subject_code", [], (err, rows) => res.json(rows || []));
});

app.get("/api/marks/:rollNumber", (req, res) => {
  db.all("SELECT m.*, s.subject_name FROM marks m JOIN subjects s ON m.subject_code = s.subject_code WHERE m.roll_number = ?", [req.params.rollNumber], (err, rows) => res.json(rows || []));
});

app.post("/api/marks/update", (req, res) => {
  const { roll_number, subject_code, exam_type, max_marks, obtained_marks } = req.body;
  db.run("INSERT OR REPLACE INTO marks (roll_number, subject_code, exam_type, max_marks, obtained_marks) VALUES (?, ?, ?, ?, ?)", [roll_number, subject_code, exam_type, max_marks, obtained_marks], () => res.json({ status: "success" }));
});

app.get("/api/attendance/session", (req, res) => {
  const { subject_code, date, slot } = req.query;
  db.all("SELECT s.roll_number, s.name, COALESCE(ar.status, 'ABSENT') as status FROM students s LEFT JOIN attendance_records ar ON s.roll_number = ar.roll_number AND ar.subject_code = ? AND ar.date = ? AND ar.slot = ?", [subject_code, date, slot], (err, rows) => res.json(rows || []));
});

app.post("/api/attendance/bulk", (req, res) => {
  const { subject_code, date, slot, attendance } = req.body;
  db.serialize(() => {
    const stmt = db.prepare("INSERT OR REPLACE INTO attendance_records (roll_number, subject_code, date, slot, status) VALUES (?, ?, ?, ?, ?)");
    for (const r of attendance) stmt.run(r.roll_number, subject_code, date, slot, r.status);
    stmt.finalize(() => res.json({ status: "success", count: attendance.length }));
  });
});

app.get("/api/student/:rollNumber", (req, res) => {
  const roll = req.params.rollNumber;
  db.get("SELECT * FROM students WHERE roll_number = ?", [roll], (err, student) => {
    if (!student) return res.status(404).json({ error: "Student not found" });
    db.get("SELECT COUNT(*) as c FROM attendance_records WHERE roll_number = ?", [roll], (err, t) => {
      const tot = t ? t.c : 0;
      db.get("SELECT COUNT(*) as c FROM attendance_records WHERE roll_number = ? AND status = 'PRESENT'", [roll], (err, a) => {
        const att = a ? a.c : 0;
        const pct = tot > 0 ? ((att / tot) * 100).toFixed(1) : "100.0";
        db.all("SELECT s.*, COUNT(ar.id) as total, SUM(CASE WHEN ar.status = 'PRESENT' THEN 1 ELSE 0 END) as attended FROM subjects s LEFT JOIN attendance_records ar ON s.subject_code = ar.subject_code AND ar.roll_number = ? GROUP BY s.subject_code", [roll], (err, stats) => {
          res.json({ student, overallPercentage: parseFloat(pct), totalClasses: tot, attendedClasses: att, subjectStats: stats || [] });
        });
      });
    });
  });
});

const PORT = 5000;
app.listen(PORT, "0.0.0.0", () => console.log(`ClassVision Active on http://0.0.0.0:${PORT}`));
