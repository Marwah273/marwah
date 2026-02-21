import argparse
import os
import re
import sqlite3

DB = os.path.join(os.path.dirname(__file__), 'students.db')


def valid_id(s):
    if not re.match(r'^[A-Za-z0-9-]{3,12}$', s):
        raise argparse.ArgumentTypeError('student_id must be 3-12 chars, alphanumeric or -')
    return s


def ensure_table(conn):
    conn.execute('''
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        class_name TEXT,
        score REAL NOT NULL,
        max_score REAL NOT NULL
    )
    ''')


def upsert_student(student_id, full_name, class_name, score, max_score):
    conn = sqlite3.connect(DB)
    ensure_table(conn)
    cur = conn.cursor()
    cur.execute('REPLACE INTO students(student_id, full_name, class_name, score, max_score) VALUES (?, ?, ?, ?, ?)',
                (student_id, full_name, class_name, score, max_score))
    conn.commit()
    conn.close()
    print(f'Inserted/updated {student_id} — {full_name} [{class_name}] ({score}/{max_score})')


def list_students():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT student_id, full_name, class_name, score, max_score FROM students ORDER BY student_id')
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print('No students found.')
        return
    for r in rows:
        sid, name, class_name, score, mx = r
        print(f'{sid}: {name} [{class_name or "-"}] — {score}/{mx}')


def main():
    p = argparse.ArgumentParser(description='Add or update a student record in students.db')
    p.add_argument('--id', type=valid_id, help='Student ID (3-12 chars, alnum or -)')
    p.add_argument('--name', help='Full name of the student')
    p.add_argument('--class-name', default='', help='Class name of the student (e.g. 4A)')
    p.add_argument('--score', type=float, help='Score obtained')
    p.add_argument('--max', type=float, default=100.0, help='Maximum possible score (default 100)')
    p.add_argument('--list', action='store_true', help='List all students')
    args = p.parse_args()

    if args.list:
        list_students()
        return

    if not args.id:
        # interactive prompt
        sid = input('Student ID: ').strip()
        sid = valid_id(sid)
        name = input('Full name: ').strip()
        class_name = input('Class name [optional]: ').strip()
        score = float(input('Score: ').strip())
        mx = input('Max score [100]: ').strip() or '100'
        upsert_student(sid, name, class_name, score, float(mx))
        return

    if not args.name or args.score is None:
        p.error('When using --id you must also provide --name and --score')

    upsert_student(args.id, args.name, args.class_name, args.score, args.max)


if __name__ == '__main__':
    main()
