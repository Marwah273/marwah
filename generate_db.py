import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'students.db')

SAMPLE = [
    ('S1001', 'Amina Hassan', '4A', 92, 100),
    ('S1002', 'Omar Ali', '4A', 78, 100),
    ('S1003', 'Lina Yusuf', '4B', 64, 100),
    ('S1004', 'Khaled Reda', '4B', 48, 100)
]


def create_db():
    if os.path.exists(DB_PATH):
        print('Database already exists at', DB_PATH)
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE students (
        student_id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        class_name TEXT,
        score REAL,
        max_score REAL
    )
    ''')
    cur.executemany('INSERT INTO students(student_id, full_name, class_name, score, max_score) VALUES (?, ?, ?, ?, ?)', SAMPLE)
    # Create a separate grades table to support multiple exams per student
    cur.execute('''
    CREATE TABLE grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        exam_name TEXT NOT NULL,
        score REAL NOT NULL,
        max_score REAL NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )
    ''')
    # Add some sample grades for the sample students
    sample_grades = [
        ('S1001', 'Math Term 1', 92, 100),
        ('S1001', 'Math Term 2', 88, 100),
        ('S1002', 'Math Term 1', 78, 100),
        ('S1003', 'Math Term 1', 64, 100),
        ('S1004', 'Math Term 1', 48, 100),
    ]
    cur.executemany('INSERT INTO grades(student_id, exam_name, score, max_score) VALUES (?, ?, ?, ?)', sample_grades)
    conn.commit()
    conn.close()
    print('Created sample database at', DB_PATH)


if __name__ == '__main__':
    create_db()
