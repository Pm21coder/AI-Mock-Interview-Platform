import urllib.request

try:
    with urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=5) as resp:
        print(resp.status)
        print(resp.read().decode())
except Exception as exc:
    print(type(exc).__name__, exc)
