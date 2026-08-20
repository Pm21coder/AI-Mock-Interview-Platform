import json
import traceback
from datetime import datetime
from app import create_app

app = create_app()
client = app.test_client()

email = f"live.master.test+{int(datetime.utcnow().timestamp())}@example.com"
print('Registering', email)
rv = client.post('/api/auth/register', json={'email': email, 'password': 'TestPass1!'})
print('register status', rv.status_code)
print(rv.get_data(as_text=True))

if rv.status_code not in (200, 201):
    raise SystemExit('Register failed')

# extract token if present
data = rv.get_json()
token = data.get('token') if isinstance(data, dict) else None
if not token:
    rv2 = client.post('/api/auth/login', json={'email': email, 'password': 'TestPass1!'})
    print('login status', rv2.status_code)
    print(rv2.get_data(as_text=True))
    if rv2.status_code not in (200, 201):
        raise SystemExit('Login failed')
    token = rv2.get_json().get('token')

headers = {'Authorization': f'Bearer {token}'}
code = 'MASTER-PRO-16BAEA3245C7D44A'

print('\nVALIDATE COUPON CALL')
rvv = client.post('/api/subscription/validate-coupon', json={'coupon_code': code}, headers=headers)
print('validate status', rvv.status_code)
print(rvv.get_data(as_text=True))

print('\nCREATE ORDER CALL')
try:
    rvc = client.post('/api/subscription/create-order', json={'tier': 'pro', 'coupon_code': code}, headers=headers)
    print('create-order status', rvc.status_code)
    print(rvc.get_data(as_text=True))
except Exception as e:
    print('Exception during create-order:')
    traceback.print_exc()
    # Try to call app.dispatch_request-like to see full stack? Already printed.

print('\nDone')
