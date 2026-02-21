#!/usr/bin/env python3
import os
import http.cookiejar
import urllib.request
import urllib.parse
import re

ROOT = 'http://127.0.0.1:5000'
ADMIN_PASS = os.getenv('ADMIN_PASS', '')
STUDENT_ID = os.getenv('STUDENT_ID', 'S1001')
FALLBACK_PASS = 'Marwah123'

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def password_login():
    url = f"{ROOT}/admin/login"
    pwd = ADMIN_PASS or FALLBACK_PASS
    data = urllib.parse.urlencode({'password': pwd}).encode('utf-8')
    req = urllib.request.Request(url, data=data)
    resp = opener.open(req)
    return resp.getcode()

def generate_share(student_id):
    url = f"{ROOT}/admin/student/{urllib.parse.quote(student_id)}/share"
    data = urllib.parse.urlencode({}).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    resp = opener.open(req)
    return resp.getcode()

def fetch_share_token(student_id):
    url = f"{ROOT}/admin/student/{urllib.parse.quote(student_id)}"
    resp = opener.open(url)
    body = resp.read().decode('utf-8', errors='replace')
    m = re.search(r"\?t=([A-Za-z0-9_\-]+)", body)
    return m.group(1) if m else None

if __name__ == '__main__':
    print('Logging in with admin password...')
    try:
        code = password_login()
    except Exception as e:
        print('Login request failed:', e)
        raise SystemExit(1)
    print('Login returned', code)
    print('Generating share token for', STUDENT_ID)
    try:
        gcode = generate_share(STUDENT_ID)
    except Exception as e:
        print('Generate request failed:', e)
        raise SystemExit(1)
    print('Generate returned', gcode)
    token = fetch_share_token(STUDENT_ID)
    if token:
        print('Share link:')
        print(f"{ROOT}/student/{STUDENT_ID}?t={token}")
    else:
        print('Failed to find share token on student page')
