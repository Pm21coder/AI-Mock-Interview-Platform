import json
import urllib.request
import urllib.error

url = 'http://127.0.0.1:5000/api/auth/register'
req = urllib.request.Request(
    url,
    data=json.dumps({'email': 'curluser@example.com', 'password': 'test12345'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(resp.status)
        print(resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('HTTP', e.code)
    print(e.read().decode('utf-8'))
except Exception as e:
    print(type(e).__name__, e)
