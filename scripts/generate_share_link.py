#!/usr/bin/env python3
import os
import http.cookiejar
import urllib.request
import urllib.parse
import re

ROOT = 'http://127.0.0.1:5000'
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')
STUDENT_ID = os.getenv('STUDENT_ID', 'S1001')

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def token_login():
    if not ADMIN_TOKEN:
        print('No ADMIN_TOKEN set in environment; cannot token-login')
        return False
    url = f"{ROOT}/admin/token-login?t={urllib.parse.quote(ADMIN_TOKEN)}"
    resp = opener.open(url)
    return resp.getcode() in (200, 302)

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
    print('Token login...')
    ok = token_login()
    print('Login ok?', ok)
    if not ok:
        raise SystemExit(1)
    print('Requesting generate share for', STUDENT_ID)
    code = generate_share(STUDENT_ID)
    print('Generate POST returned', code)
    token = fetch_share_token(STUDENT_ID)
    if token:
        print('Share link:')
        print(f"{ROOT}/student/{STUDENT_ID}?t={token}")
    else:
        print('Failed to find share token in admin page')
