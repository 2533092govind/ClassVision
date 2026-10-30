const express = require("express");
const cors = require("cors");
const path = require("path");
const db = require("./database");

const app = express();
app.use(cors());
app.use(express.json());

// Serve client directory
app.use(express.static(path.join(__dirname, "../client")));

// 1. Fetch all subjects for the faculty dropdown
app.get("/api/subjects", (req, res) => {
  const subjects = db.prepare("SELECT * FROM subjects").all();
  res.json(subjects);
});

// 2. Fetch all enrolled students
app.get("/api/students", (req, res) => {
  const students = db.prepare("SELECT * FROM students").all();
  res.json(students);
});

// 3. Bulk attendance intake from recognition engine
app.post("/api/attendance/bulk", (req, res) => {
  const { subject_code, date, slot, attendance } = req.body;
  if (!subject_code || !date || !slot || !Array.isArray(attendance)) {
    return res.status(400).json({ error: "Missing required fields." });
  }

  const insertStmt = db.prepare(`
    INSERT OR REPLACE INTO attendance_records (roll_number, subject_code, date, slot, status)
    VALUES (?, ?, ?, ?, ?)
  `);

  const transaction = db.transaction((records) => {
    for (const record of records) {
      insertStmt.run(record.roll_number, subject_code, date, slot, record.status);
    }
  });

  try {
    transaction(attendance);
    res.json({ status: "success", count: attendance.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 4. Fetch specific session summary for faculty preview
app.get("/api/attendance/session", (req, res) => {
  const { subject_code, date, slot } = req.query;
  const records = db.prepare(`
    SELECT ar.roll_number, s.name, ar.status
    FROM attendance_records ar
    JOIN students s ON ar.roll_number = s.roll_number
    WHERE ar.subject_code = ? AND ar.date = ? AND ar.slot = ?
  `).all(subject_code, date, slot);

  res.json(records);
});

// 5. Individual student portal data
app.get("/api/student/:rollNumber", (req, res) => {
  const { rollNumber } = req.params;

  const student = db.prepare("SELECT roll_number, name FROM students WHERE roll_number = ?").get(rollNumber);
  if (!student) {
    return res.status(404).json({ error: "Student not found in ERP records." });
  }

  const totalClasses = db.prepare("SELECT COUNT(*) as count FROM attendance_records WHERE roll_number = ?").get(rollNumber).count;
  const attendedClasses = db.prepare("SELECT COUNT(*) as count FROM attendance_records WHERE roll_number = ? AND status = 'PRESENT'").get(rollNumber).count;

  const percentage = totalClasses > 0 ? ((attendedClasses / totalClasses) * 100).toFixed(1) : "100.0";

  const subjects = db.prepare(`
    SELECT 
      ar.subject_code,
      s.subject_name,
      COUNT(*) as total,
      SUM(CASE WHEN ar.status = 'PRESENT' THEN 1 ELSE 0 END) as attended
    FROM attendance_records ar
    JOIN subjects s ON ar.subject_code = s.subject_code
    WHERE ar.roll_number = ?
    GROUP BY ar.subject_code
  `).all(rollNumber);

  res.json({
    student,
    overallPercentage: parseFloat(percentage),
    totalClasses,
    attendedClasses,
    subjectStats: subjects
  });
});

const PORT = 5000;
app.listen(PORT, () => console.log(`ERP Portal running at http://localhost:${PORT}`));
