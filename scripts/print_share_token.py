#!/usr/bin/env python3
import sqlite3
import sys

DB = 'students.db'
STUDENT_ID = 'S1001'

try:
    conn = sqlite3.connect(DB)
    cur = conn.execute('SELECT share_token FROM students WHERE student_id = ?', (STUDENT_ID,))
    row = cur.fetchone()
    if row and row[0]:
        print(row[0])
    else:
        # empty if not set
        print('')
except Exception as e:
    print('ERROR:' + str(e))
    sys.exit(1)
