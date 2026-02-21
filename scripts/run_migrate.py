#!/usr/bin/env python3
"""Run migration by using token-login and POSTing to /admin/migrate.

Usage: .\.venv\Scripts\python.exe scripts\run_migrate.py
"""
import os
import http.cookiejar
import urllib.request
import urllib.parse

ROOT = 'http://127.0.0.1:5000'
TOKEN = os.getenv('ADMIN_TOKEN', 'setup-token-9X2w')

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def token_login():
    url = f"{ROOT}/admin/token-login?t={urllib.parse.quote(TOKEN)}"
    resp = opener.open(url)
    return resp.getcode()

def migrate():
    url = f"{ROOT}/admin/migrate"
    data = ''.encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    resp = opener.open(req)
    return resp.getcode()

if __name__ == '__main__':
    print('Attempting token login...')
    code = token_login()
    print('Login returned', code)
    print('Cookies:', list(cj))
    print('Calling migrate...')
    mcode = migrate()
    print('Migrate returned', mcode)
