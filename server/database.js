const Database = require("better-sqlite3");
const path = require("path");

const dbPath = path.join(__dirname, "classvision.db");
const db = new Database(dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    display_name TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS students (
    roll_number TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    semester TEXT DEFAULT '3rd Sem',
    branch TEXT DEFAULT 'BCA'
  );

  CREATE TABLE IF NOT EXISTS subjects (
    subject_code TEXT PRIMARY KEY,
    subject_name TEXT NOT NULL,
    faculty TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS attendance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_number TEXT,
    subject_code TEXT,
    date TEXT,
    slot TEXT,
    status TEXT,
    UNIQUE(roll_number, subject_code, date, slot)
  );

  CREATE TABLE IF NOT EXISTS timetable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_of_week TEXT,
    time_slot TEXT,
    subject_code TEXT,
    room_no TEXT
  );

  CREATE TABLE IF NOT EXISTS marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_number TEXT,
    subject_code TEXT,
    exam_type TEXT,
    max_marks INTEGER,
    obtained_marks REAL,
    UNIQUE(roll_number, subject_code, exam_type)
  );
`);

// Seed Faculty and Student Credentials
const insertUser = db.prepare("INSERT OR REPLACE INTO users (username, password, role, display_name) VALUES (?, ?, ?, ?)");
insertUser.run("faculty", "faculty123", "FACULTY", "Faculty Administration");
insertUser.run("25261102114", "pass123", "STUDENT", "Govind Singh");
insertUser.run("25261102115", "pass123", "STUDENT", "Aditi Mishra");
insertUser.run("25261102116", "pass123", "STUDENT", "Sankalp Sachan");
insertUser.run("25261102117", "pass123", "STUDENT", "Hanshika Sharma");

// Cohort Students
const insertStudent = db.prepare("INSERT OR IGNORE INTO students (roll_number, name, semester, branch) VALUES (?, ?, ?, ?)");
insertStudent.run("25261102114", "Govind Singh", "3rd Sem", "BCA");
insertStudent.run("25261102115", "Aditi Mishra", "3rd Sem", "BCA");
insertStudent.run("25261102116", "Sankalp Sachan", "3rd Sem", "BCA");
insertStudent.run("25261102117", "Hanshika Sharma", "3rd Sem", "BCA");

// 5 Core BCA Subjects
const insertSubject = db.prepare("INSERT OR REPLACE INTO subjects (subject_code, subject_name, faculty) VALUES (?, ?, ?)");
insertSubject.run("BCA3001T", "Python Programming", "Dr. A. Verma");
insertSubject.run("BCA3002T", "Operating Systems", "Prof. S. Srivastava");
insertSubject.run("BCA3003T", "Emerging Technologies", "Dr. R. K. Singh");
insertSubject.run("BCA3004T", "Internet and Web Technology", "Er. N. Dixit");
insertSubject.run("BCA3005T", "Software Engineering", "Prof. P. Agrawal");

// Timetable Configuration
db.exec("DELETE FROM timetable");
const insertSlot = db.prepare("INSERT INTO timetable (day_of_week, time_slot, subject_code, room_no) VALUES (?, ?, ?, ?)");

insertSlot.run("Monday", "09:00 AM - 10:00 AM", "BCA3001T", "Computer Lab-2");
insertSlot.run("Monday", "10:00 AM - 11:00 AM", "BCA3002T", "LH-201");
insertSlot.run("Monday", "11:30 AM - 12:30 PM", "BCA3004T", "Web Design Lab");
insertSlot.run("Monday", "01:30 PM - 02:30 PM", "BCA3005T", "LH-201");

insertSlot.run("Tuesday", "09:00 AM - 10:00 AM", "BCA3003T", "LH-202");
insertSlot.run("Tuesday", "10:00 AM - 11:00 AM", "BCA3001T", "Computer Lab-2");
insertSlot.run("Tuesday", "11:30 AM - 12:30 PM", "BCA3002T", "LH-201");
insertSlot.run("Tuesday", "01:30 PM - 02:30 PM", "BCA3004T", "Web Design Lab");

insertSlot.run("Wednesday", "09:00 AM - 10:00 AM", "BCA3005T", "LH-201");
insertSlot.run("Wednesday", "10:00 AM - 11:00 AM", "BCA3003T", "LH-202");
insertSlot.run("Wednesday", "11:30 AM - 12:30 PM", "BCA3001T", "Computer Lab-2");

insertSlot.run("Thursday", "09:00 AM - 10:00 AM", "BCA3004T", "Web Design Lab");
insertSlot.run("Thursday", "10:00 AM - 11:00 AM", "BCA3005T", "LH-201");
insertSlot.run("Thursday", "11:30 AM - 12:30 PM", "BCA3002T", "LH-201");

insertSlot.run("Friday", "09:00 AM - 10:00 AM", "BCA3003T", "LH-202");
insertSlot.run("Friday", "10:00 AM - 11:00 AM", "BCA3001T", "Computer Lab-2");
insertSlot.run("Friday", "11:30 AM - 12:30 PM", "BCA3004T", "Web Design Lab");

// Seed Marks
const insertMark = db.prepare("INSERT OR REPLACE INTO marks (roll_number, subject_code, exam_type, max_marks, obtained_marks) VALUES (?, ?, ?, ?, ?)");
insertMark.run("25261102114", "BCA3001T", "Sessional 1", 30, 28.5);
insertMark.run("25261102114", "BCA3002T", "Sessional 1", 30, 26.0);
insertMark.run("25261102114", "BCA3003T", "Sessional 1", 30, 27.5);
insertMark.run("25261102114", "BCA3004T", "Sessional 1", 30, 29.0);
insertMark.run("25261102114", "BCA3005T", "Sessional 1", 30, 25.5);

console.log("ClassVision ERP Database upgraded with user accounts and credentials!");
module.exports = db;
