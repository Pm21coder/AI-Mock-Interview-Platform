import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def run_test():
    test_email = f"test_razorpay_{int(datetime.now().timestamp())}@example.com"
    test_password = "TestPassword123!"

    print('[1] Registering')
    r = requests.post(f"{BASE_URL}/api/auth/register", json={"email": test_email, "password": test_password, "full_name": "Test User"})
    print('register status', r.status_code, r.text[:200])
    if r.status_code not in (200,201):
        return

    print('[2] Logging in')
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": test_email, "password": test_password})
    print('login status', r.status_code, r.text[:200])
    if r.status_code != 200:
        return
    token = r.json().get('token')
    print('got token', token[:20])

    headers = {'Authorization': f'Bearer {token}'}
    print('[3] Create order (non-demo)')
    r = requests.post(f"{BASE_URL}/api/subscription/create-order", json={'tier':'basic','demo_mode':False}, headers=headers)
    print('create-order status', r.status_code)
    print('body', r.text[:1000])

if __name__ == '__main__':
    run_test()
