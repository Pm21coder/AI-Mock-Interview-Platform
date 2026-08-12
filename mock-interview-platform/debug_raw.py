import socket

HOST = '127.0.0.1'
PORT = 5000

TESTS = [
    ('GET', '/health', None),
    ('GET', '/api/auth/register', None),
    ('POST', '/api/auth/register', '{"email":"testuser@example.com","password":"test12345"}'),
    ('POST', '/api/auth/login', '{"email":"testuser@example.com","password":"test12345"}'),
    ('POST', '/api/subscription/create-order', '{"tier":"basic"}'),
]

for method, path, body in TESTS:
    try:
        with socket.create_connection((HOST, PORT), timeout=10) as sock:
            headers = [
                f'{method} {path} HTTP/1.1',
                f'Host: {HOST}',
                'Connection: close',
            ]
            data = body.encode('utf-8') if body else b''
            if body:
                headers.append('Content-Type: application/json')
                headers.append(f'Content-Length: {len(data)}')
            request = '\r\n'.join(headers) + '\r\n\r\n'
            sock.sendall(request.encode('utf-8') + data)
            response = sock.recv(8192)
            print('---', method, path)
            print(response.decode('utf-8', errors='replace').split('\r\n\r\n')[0])
    except Exception as exc:
        print('---', method, path, 'ERROR', type(exc).__name__, exc)
