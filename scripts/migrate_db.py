#!/usr/bin/env python3
import sqlite3
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
DB = os.path.join(ROOT, 'students.db')

def main():
    if not os.path.exists(DB):
        print('Database not found at', DB)
        return
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    # ensure grades table exists
    cur.execute('''
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        exam_name TEXT NOT NULL,
        score REAL NOT NULL,
        max_score REAL NOT NULL
    )
    ''')
    conn.commit()

    # If students.score is NOT NULL in the current schema, recreate students table
    info = cur.execute("PRAGMA table_info(students)").fetchall()
    col_info = {r[1]: r for r in info}
    if 'score' in col_info and col_info['score'][3] == 1:
        # score column has NOT NULL constraint (table_info col 3 == notnull)
        print('Recreating students table to allow NULL scores')
        cur.execute('ALTER TABLE students RENAME TO students_old')
        cur.execute('''
        CREATE TABLE students (
            student_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            class_name TEXT,
            score REAL,
            max_score REAL
        )
        ''')
        try:
            cur.execute('INSERT INTO students(student_id, full_name, class_name, score, max_score) SELECT student_id, full_name, class_name, score, max_score FROM students_old')
        except sqlite3.OperationalError:
            cur.execute('INSERT INTO students(student_id, full_name, class_name, score, max_score) SELECT student_id, full_name, NULL, score, max_score FROM students_old')
        cur.execute('DROP TABLE students_old')
        conn.commit()

    # Ensure class_name exists for existing databases
    info = cur.execute("PRAGMA table_info(students)").fetchall()
    cols = {r[1] for r in info}
    if 'class_name' not in cols:
        cur.execute('ALTER TABLE students ADD COLUMN class_name TEXT')
        conn.commit()

    cur.execute("SELECT student_id, full_name, score, max_score FROM students WHERE score IS NOT NULL")
    rows = cur.fetchall()
    moved = 0
    for sid, name, score, max_score in rows:
        if score is None:
            continue
        if max_score is None:
            max_score = 100
        cur.execute('INSERT INTO grades(student_id, exam_name, score, max_score) VALUES (?, ?, ?, ?)', (sid, 'Imported', score, max_score))
        cur.execute('UPDATE students SET score = NULL, max_score = NULL WHERE student_id = ?', (sid,))
        moved += 1
    conn.commit()
    conn.close()
    print(f'Migrated {moved} rows into grades')

if __name__ == '__main__':
    main()
