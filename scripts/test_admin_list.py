#!/usr/bin/env python3
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


def fetch_list():
    url = f"{ROOT}/admin/list"
    resp = opener.open(url)
    return resp.getcode(), resp.read().decode('utf-8')


if __name__ == '__main__':
    print('Attempting token login...')
    code = token_login()
    print('Login returned', code)
    print('Cookies:', list(cj))
    print('Fetching admin list...')
    code, body = fetch_list()
    print('List returned', code)
    lines = body.split('\n')
    print('---SNIPPET---')
    for ln in lines[:12]:
        print(ln)
    print('---END---')
