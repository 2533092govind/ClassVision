const sqlite3 = require("sqlite3").verbose();
const path = require("path");

const dbPath = path.join(__dirname, "classvision.db");
const db = new sqlite3.Database(dbPath);

db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,
      role TEXT NOT NULL,
      display_name TEXT NOT NULL
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS students (
      roll_number TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      semester TEXT DEFAULT '3rd Sem',
      branch TEXT DEFAULT 'BCA'
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS subjects (
      subject_code TEXT PRIMARY KEY,
      subject_name TEXT NOT NULL,
      faculty TEXT NOT NULL
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS attendance_records (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      roll_number TEXT,
      subject_code TEXT,
      date TEXT,
      slot TEXT,
      status TEXT,
      UNIQUE(roll_number, subject_code, date, slot)
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS timetable (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      day_of_week TEXT,
      time_slot TEXT,
      subject_code TEXT,
      room_no TEXT
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS marks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      roll_number TEXT,
      subject_code TEXT,
      exam_type TEXT,
      max_marks INTEGER,
      obtained_marks REAL,
      UNIQUE(roll_number, subject_code, exam_type)
    )
  `);

  // Seed Users
  const insUser = "INSERT OR REPLACE INTO users (username, password, role, display_name) VALUES (?, ?, ?, ?)";
  db.run(insUser, ["faculty", "faculty123", "FACULTY", "Faculty Administration"]);
  db.run(insUser, ["25261102114", "pass123", "STUDENT", "Govind Singh"]);
  db.run(insUser, ["25261102115", "pass123", "STUDENT", "Aditi Mishra"]);
  db.run(insUser, ["25261102116", "pass123", "STUDENT", "Sankalp Sachan"]);
  db.run(insUser, ["25261102117", "pass123", "STUDENT", "Hanshika Sharma"]);

  // Seed Students
  const insStudent = "INSERT OR IGNORE INTO students (roll_number, name, semester, branch) VALUES (?, ?, ?, ?)";
  db.run(insStudent, ["25261102114", "Govind Singh", "3rd Sem", "BCA"]);
  db.run(insStudent, ["25261102115", "Aditi Mishra", "3rd Sem", "BCA"]);
  db.run(insStudent, ["25261102116", "Sankalp Sachan", "3rd Sem", "BCA"]);
  db.run(insStudent, ["25261102117", "Hanshika Sharma", "3rd Sem", "BCA"]);

  // Seed Subjects
  const insSubject = "INSERT OR REPLACE INTO subjects (subject_code, subject_name, faculty) VALUES (?, ?, ?)";
  db.run(insSubject, ["BCA3001T", "Python Programming", "Dr. A. Verma"]);
  db.run(insSubject, ["BCA3002T", "Operating Systems", "Prof. S. Srivastava"]);
  db.run(insSubject, ["BCA3003T", "Emerging Technologies", "Dr. R. K. Singh"]);
  db.run(insSubject, ["BCA3004T", "Internet and Web Technology", "Er. N. Dixit"]);
  db.run(insSubject, ["BCA3005T", "Software Engineering", "Prof. P. Agrawal"]);

  // Seed Timetable
  db.run("DELETE FROM timetable", () => {
    const insSlot = "INSERT INTO timetable (day_of_week, time_slot, subject_code, room_no) VALUES (?, ?, ?, ?)";
    db.run(insSlot, ["Monday", "09:00 AM - 10:00 AM", "BCA3001T", "Computer Lab-2"]);
    db.run(insSlot, ["Monday", "10:00 AM - 11:00 AM", "BCA3002T", "LH-201"]);
    db.run(insSlot, ["Monday", "11:30 AM - 12:30 PM", "BCA3004T", "Web Design Lab"]);
    db.run(insSlot, ["Monday", "01:30 PM - 02:30 PM", "BCA3005T", "LH-201"]);

    db.run(insSlot, ["Tuesday", "09:00 AM - 10:00 AM", "BCA3003T", "LH-202"]);
    db.run(insSlot, ["Tuesday", "10:00 AM - 11:00 AM", "BCA3001T", "Computer Lab-2"]);
    db.run(insSlot, ["Tuesday", "11:30 AM - 12:30 PM", "BCA3002T", "LH-201"]);
    db.run(insSlot, ["Tuesday", "01:30 PM - 02:30 PM", "BCA3004T", "Web Design Lab"]);

    db.run(insSlot, ["Wednesday", "09:00 AM - 10:00 AM", "BCA3005T", "LH-201"]);
    db.run(insSlot, ["Wednesday", "10:00 AM - 11:00 AM", "BCA3003T", "LH-202"]);
    db.run(insSlot, ["Wednesday", "11:30 AM - 12:30 PM", "BCA3001T", "Computer Lab-2"]);

    db.run(insSlot, ["Thursday", "09:00 AM - 10:00 AM", "BCA3004T", "Web Design Lab"]);
    db.run(insSlot, ["Thursday", "10:00 AM - 11:00 AM", "BCA3005T", "LH-201"]);
    db.run(insSlot, ["Thursday", "11:30 AM - 12:30 PM", "BCA3002T", "LH-201"]);

    db.run(insSlot, ["Friday", "09:00 AM - 10:00 AM", "BCA3003T", "LH-202"]);
    db.run(insSlot, ["Friday", "10:00 AM - 11:00 AM", "BCA3001T", "Computer Lab-2"]);
    db.run(insSlot, ["Friday", "11:30 AM - 12:30 PM", "BCA3004T", "Web Design Lab"]);
  });

  // Seed Marks
  const insMark = "INSERT OR REPLACE INTO marks (roll_number, subject_code, exam_type, max_marks, obtained_marks) VALUES (?, ?, ?, ?, ?)";
  db.run(insMark, ["25261102114", "BCA3001T", "Sessional 1", 30, 28.5]);
  db.run(insMark, ["25261102114", "BCA3002T", "Sessional 1", 30, 26.0]);
  db.run(insMark, ["25261102114", "BCA3003T", "Sessional 1", 30, 27.5]);
  db.run(insMark, ["25261102114", "BCA3004T", "Sessional 1", 30, 29.0]);
  db.run(insMark, ["25261102114", "BCA3005T", "Sessional 1", 30, 25.5]);
});

console.log("ClassVision Database verified and seeded.");
module.exports = db;
