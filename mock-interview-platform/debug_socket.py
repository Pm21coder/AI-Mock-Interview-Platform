import socket

def send_request(path):
    with socket.create_connection(('127.0.0.1', 5000), timeout=10) as sock:
        req = f'GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n'
        sock.sendall(req.encode('utf-8'))
        resp = sock.recv(4096)
        print(path, resp.split(b'\r\n')[0])

if __name__ == '__main__':
    send_request('/health')
    send_request('/api/auth/register')
