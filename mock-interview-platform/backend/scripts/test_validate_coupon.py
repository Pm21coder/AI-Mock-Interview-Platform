import json
from datetime import datetime
from app import create_app

app = create_app()
client = app.test_client()

email = f"coupon.checker+{int(datetime.utcnow().timestamp())}@example.com"
print('Registering', email)
rv = client.post('/api/auth/register', json={'email': email, 'password': 'TestPass1!'})
print('register status', rv.status_code, rv.get_data(as_text=True))
if rv.status_code not in (200, 201):
    raise SystemExit('Register failed')

data = rv.get_json()
# extract token if present
token = data.get('token') if isinstance(data, dict) else None
if not token:
    rv2 = client.post('/api/auth/login', json={'email': email, 'password': 'TestPass1!'})
    print('login status', rv2.status_code, rv2.get_data(as_text=True))
    if rv2.status_code not in (200, 201):
        raise SystemExit('Login failed')
    token = rv2.get_json().get('token')

headers = {'Authorization': f'Bearer {token}'}
code = 'UPGRADE30-8F7K9Z'
rv3 = client.post('/api/subscription/validate-coupon', json={'coupon_code': code}, headers=headers)
print('validate-coupon status', rv3.status_code)
try:
    print(json.dumps(rv3.get_json(), indent=2, default=str))
except Exception:
    print('Response text:', rv3.get_data(as_text=True))
