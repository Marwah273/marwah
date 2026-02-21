import sqlite3
conn=sqlite3.connect('students.db')
cur=conn.cursor()
cur.execute("PRAGMA table_info(students)")
print(cur.fetchall())
cur.execute("SELECT student_id, share_token FROM students ORDER BY student_id LIMIT 5")
print(cur.fetchall())
conn.close()
