#!/usr/bin/env python3
"""Programmatic full admin CRUD test.
Performs: token-login -> add student (with an exam) -> verify in list -> add exam -> fetch student grades -> edit student name -> delete one exam -> delete student -> verify removal.
"""
import os
import http.cookiejar
import urllib.request
import urllib.parse
import sys

ROOT = 'http://127.0.0.1:5000'
TOKEN = os.getenv('ADMIN_TOKEN', 'setup-token-9X2w')

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def token_login():
    url = f"{ROOT}/admin/token-login?t={urllib.parse.quote(TOKEN)}"
    resp = opener.open(url)
    return resp.getcode()

def post_form(path, data):
    url = f"{ROOT}{path}"
    body = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=body)
    resp = opener.open(req)
    return resp.getcode(), resp.read().decode('utf-8')

def get(path):
    url = f"{ROOT}{path}"
    resp = opener.open(url)
    return resp.getcode(), resp.read().decode('utf-8')

if __name__ == '__main__':
    sid = 'TST123'
    name = 'Test Student'
    new_name = 'Updated Student'
    print('Token login...')
    print('login code', token_login())
    print('Adding student with exam...')
    code, _ = post_form('/admin/add', {'student_id': sid, 'full_name': name, 'exam_name': 'Term1', 'score': '85', 'max_score': '100'})
    print('add student code', code)

    code, body = get('/admin/list')
    print('list code', code)
    found = sid in body
    print('student in list?', found)
    if not found:
        print('FAILED: student not found in list')
        sys.exit(2)

    print('Add another exam...')
    code, _ = post_form(f'/admin/student/{urllib.parse.quote(sid)}', {'exam_name': 'Term2', 'score': '90', 'max_score': '100'})
    print('add exam code', code)

    code, body = get(f'/admin/student/{urllib.parse.quote(sid)}')
    print('student page code', code)
    # crude parse to find grade ids
    import re
    ids = re.findall(r"/admin/student/%s/delete/(\d+)" % sid, body)
    print('found grade ids:', ids)
    if not ids:
        print('FAILED: no exams found')
        sys.exit(3)
    gid = ids[0]

    print('Edit student name...')
    code, _ = post_form(f'/admin/student/{urllib.parse.quote(sid)}/edit', {'full_name': new_name})
    print('edit code', code)
    code, body = get('/admin/list')
    print('verify updated name present?', new_name in body)

    print('Delete one exam...')
    code, _ = get(f'/admin/student/{urllib.parse.quote(sid)}/delete/{gid}')
    print('delete exam code', code)

    code, body = get(f'/admin/student/{urllib.parse.quote(sid)}')
    print('remaining exams snippet:', body.split('\n')[:12])

    print('Delete student (POST)...')
    code, _ = post_form(f'/admin/student/{urllib.parse.quote(sid)}/delete', {})
    print('delete student code', code)

    code, body = get('/admin/list')
    print('final check student present?', sid in body)
    print('DONE')
