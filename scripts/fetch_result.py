import urllib.request
u='http://127.0.0.1:5000/student/S1001'
print('Fetching',u)
b=urllib.request.urlopen(u,timeout=5).read().decode('utf-8',errors='replace')
lines=b.splitlines()
found=False
for i,l in enumerate(lines):
    if '%' in l or '100.0' in l or '100' in l:
        print(i+1, l.strip())
        found=True
if not found:
    print('No percent or 100 found')
