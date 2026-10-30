const express = require("express");
const cors = require("cors");
const path = require("path");
const db = require("./database");

const app = express();
app.use(cors());
app.use(express.json({ limit: "25mb" }));

app.use(express.static(path.join(__dirname, "../client")));

// Authentication
app.post("/api/auth/login", (req, res) => {
  const { username, password, role } = req.body;
  if (!username || !password || !role) return res.status(400).json({ error: "Missing fields" });

  db.get(
    "SELECT * FROM users WHERE username = ? AND password = ? AND role = ?",
    [username.trim(), password.trim(), role],
    (err, user) => {
      if (err || !user) return res.status(401).json({ error: "Invalid credentials" });
      res.json({
        status: "success",
        user: { username: user.username, role: user.role, displayName: user.display_name }
      });
    }
  );
});

// Subjects
app.get("/api/subjects", (req, res) => {
  db.all("SELECT * FROM subjects", [], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

// Timetable
app.get("/api/timetable", (req, res) => {
  const query = `
    SELECT t.day_of_week, t.time_slot, t.room_no, s.subject_code, s.subject_name, s.faculty
    FROM timetable t JOIN subjects s ON t.subject_code = s.subject_code
    ORDER BY CASE t.day_of_week 
      WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 
      WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 ELSE 6 END
  `;
  db.all(query, [], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

// Marks
app.get("/api/marks/:rollNumber", (req, res) => {
  const query = `
    SELECT m.exam_type, m.max_marks, m.obtained_marks, s.subject_code, s.subject_name
    FROM marks m JOIN subjects s ON m.subject_code = s.subject_code
    WHERE m.roll_number = ?
  `;
  db.all(query, [req.params.rollNumber], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

app.post("/api/marks/update", (req, res) => {
  const { roll_number, subject_code, exam_type, max_marks, obtained_marks } = req.body;
  const query = `
    INSERT OR REPLACE INTO marks (roll_number, subject_code, exam_type, max_marks, obtained_marks)
    VALUES (?, ?, ?, ?, ?)
  `;
  db.run(query, [roll_number, subject_code, exam_type, max_marks, obtained_marks], function(err) {
    if (err) return res.status(500).json({ error: err.message });
    res.json({ status: "success" });
  });
});

// Faculty Session Attendance
app.get("/api/attendance/session", (req, res) => {
  const { subject_code, date, slot } = req.query;
  const query = `
    SELECT s.roll_number, s.name, COALESCE(ar.status, 'ABSENT') as status
    FROM students s
    LEFT JOIN attendance_records ar 
      ON s.roll_number = ar.roll_number 
      AND ar.subject_code = ? AND ar.date = ? AND ar.slot = ?
  `;
  db.all(query, [subject_code, date, slot], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

// Bulk Ingestion
app.post("/api/attendance/bulk", (req, res) => {
  const { subject_code, date, slot, attendance } = req.body;
  const query = `
    INSERT OR REPLACE INTO attendance_records (roll_number, subject_code, date, slot, status)
    VALUES (?, ?, ?, ?, ?)
  `;
  
  db.serialize(() => {
    const stmt = db.prepare(query);
    for (const r of attendance) {
      stmt.run(r.roll_number, subject_code, date, slot, r.status);
    }
    stmt.finalize((err) => {
      if (err) return res.status(500).json({ error: err.message });
      res.json({ status: "success", count: attendance.length });
    });
  });
});

// Student Dashboard Profile
app.get("/api/student/:rollNumber", (req, res) => {
  const rollNumber = req.params.rollNumber;
  db.get("SELECT * FROM students WHERE roll_number = ?", [rollNumber], (err, student) => {
    if (err || !student) return res.status(404).json({ error: "Student not found" });

    db.get("SELECT COUNT(*) as count FROM attendance_records WHERE roll_number = ?", [rollNumber], (err, totRow) => {
      const totalClasses = totRow ? totRow.count : 0;

      db.get("SELECT COUNT(*) as count FROM attendance_records WHERE roll_number = ? AND status = 'PRESENT'", [rollNumber], (err, attRow) => {
        const attendedClasses = attRow ? attRow.count : 0;
        const percentage = totalClasses > 0 ? ((attendedClasses / totalClasses) * 100).toFixed(1) : "100.0";

        const statsQuery = `
          SELECT s.subject_code, s.subject_name, s.faculty,
            COUNT(ar.id) as total,
            SUM(CASE WHEN ar.status = 'PRESENT' THEN 1 ELSE 0 END) as attended
          FROM subjects s
          LEFT JOIN attendance_records ar ON s.subject_code = ar.subject_code AND ar.roll_number = ?
          GROUP BY s.subject_code, s.subject_name, s.faculty
        `;
        db.all(statsQuery, [rollNumber], (err, subjectStats) => {
          res.json({
            student,
            overallPercentage: parseFloat(percentage),
            totalClasses,
            attendedClasses,
            subjectStats: subjectStats || []
          });
        });
      });
    });
  });
});

const PORT = 5000;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`ClassVision Active on http://0.0.0.0:${PORT}`);
});
