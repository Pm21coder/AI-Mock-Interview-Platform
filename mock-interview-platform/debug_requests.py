import json
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:5000'

requests = [
    ('register', '/api/auth/register', {'email': 'testuser@example.com', 'password': 'test12345'}),
    ('login', '/api/auth/login', {'email': 'testuser@example.com', 'password': 'test12345'}),
]

for name, path, payload in requests:
    try:
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print('---', name, resp.status)
            print(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as err:
        body = err.read().decode('utf-8')
        print('---', name, 'HTTPError', err.code)
        print(body)
    except Exception as exc:
        print('---', name, 'ERROR', type(exc).__name__, exc)
