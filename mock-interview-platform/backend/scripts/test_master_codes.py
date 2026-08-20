import json
from datetime import datetime
from app import create_app

app = create_app()
client = app.test_client()

email = f"master.tester+{int(datetime.utcnow().timestamp())}@example.com"
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

codes = [
    'MASTER-BASIC-E8E588F630E6E93F',
    'MASTER-PRO-16BAEA3245C7D44A'
]

for code in codes:
    print('\nTesting validate-coupon for', code)
    rv3 = client.post('/api/subscription/validate-coupon', json={'coupon_code': code}, headers=headers)
    print('status', rv3.status_code)
    print(rv3.get_data(as_text=True))

# Try create-order with PRO and master-pro code
print('\nTesting create-order with master PRO code')
rv4 = client.post('/api/subscription/create-order', json={'tier': 'pro', 'coupon_code': codes[1]}, headers=headers)
print('create-order status', rv4.status_code)
print(rv4.get_data(as_text=True))
