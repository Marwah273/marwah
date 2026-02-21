import urllib.request, urllib.error
URL='http://127.0.0.1:5000/result?student_id=S1001'
print('Requesting', URL)
try:
    resp = urllib.request.urlopen(URL, timeout=5)
    code = resp.getcode()
    body = resp.read().decode('utf-8', errors='replace')
    print('Status:', code)
    print('---SNIPPET---')
    for ln in body.split('\n')[:20]:
        print(ln)
    print('---END---')
except Exception as e:
    print('Error:', repr(e))
