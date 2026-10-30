const db = require('./database');

// Insert sample subjects
const insertSubject = db.prepare(`
  INSERT OR IGNORE INTO subjects (subject_code, subject_name)
  VALUES (?, ?)
`);

insertSubject.run('BCA-301', 'Operating Systems');
insertSubject.run('BCA-302', 'Data Structures using C++');
insertSubject.run('BCA-303', 'Computer Networks');

// Insert sample students
const insertStudent = db.prepare(`
  INSERT OR IGNORE INTO students (roll_number, name, email)
  VALUES (?, ?, ?)
`);

insertStudent.run('25261102114', 'Govind Singh', 'govind@example.com');
insertStudent.run('25261102115', 'Aman Verma', 'aman@example.com');
insertStudent.run('25261102116', 'Rohan Gupta', 'rohan@example.com');

console.log('Sample students and subjects successfully seeded!');
