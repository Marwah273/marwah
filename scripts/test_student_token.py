import urllib.request, urllib.error

URL_BASE = 'http://127.0.0.1:5000'

def req(path):
    try:
        r = urllib.request.urlopen(URL_BASE + path, timeout=5)
        print(path, '->', r.getcode())
        data = r.read().decode('utf-8', errors='replace')
        print('\n'.join(data.split('\n')[:6]))
    except urllib.error.HTTPError as e:
        print(path, 'HTTPError', e.code)
        try:
            print(e.read().decode('utf-8')[:200])
        except Exception:
            pass
    except Exception as e:
        print(path, 'ERROR', type(e), e)

if __name__ == '__main__':
    req('/student/S1001')
    req('/student/S1001?t=wrong')
    # If you set STUDENT_TOKEN in your environment, replace below with that token
    req('/student/S1001?t=')
