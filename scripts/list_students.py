import sqlite3
DB='students.db'
conn=sqlite3.connect(DB)
cur=conn.cursor()
cur.execute('SELECT student_id, full_name, class_name FROM students ORDER BY student_id LIMIT 50')
rows=cur.fetchall()
for r in rows:
    print(r[0], '-', r[1], f"[{r[2] or '-'}]")
conn.close()
