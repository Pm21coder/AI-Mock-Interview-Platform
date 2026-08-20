import json
import traceback
import hmac
import hashlib
import time
from datetime import datetime
from app import create_app

app = create_app()
client = app.test_client()

email = f"live.master.full+{int(datetime.utcnow().timestamp())}@example.com"
print('Registering', email)
rv = client.post('/api/auth/register', json={'email': email, 'password': 'TestPass1!'})
print('register status', rv.status_code)
print(rv.get_data(as_text=True))

if rv.status_code not in (200, 201):
    raise SystemExit('Register failed')

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

print('\nVALIDATE COUPON')
rvv = client.post('/api/subscription/validate-coupon', json={'coupon_code': code}, headers=headers)
print('validate status', rvv.status_code)
print(rvv.get_data(as_text=True))

print('\nCREATE ORDER')
rvc = client.post('/api/subscription/create-order', json={'tier': 'pro', 'coupon_code': code}, headers=headers)
print('create-order status', rvc.status_code)
print(rvc.get_data(as_text=True))

if rvc.status_code != 200:
    raise SystemExit('create-order failed')

order = rvc.get_json()
order_id = order.get('order_id')

# Simulate a payment by creating a fake payment id and signing it with server secret
fake_payment_id = f'pay_{int(time.time())}'
secret = app.config.get('RAZORPAY_KEY_SECRET')
if not secret:
    print('\nNo RAZORPAY_KEY_SECRET configured, cannot simulate verify-payment signature. Skipping verify step.')
else:
    msg = f"{order_id}|{fake_payment_id}"
    signature = hmac.new(secret.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    print('\nVERIFY PAYMENT (simulated)')
    rvv2 = client.post('/api/subscription/verify-payment', json={
        'razorpay_order_id': order_id,
        'razorpay_payment_id': fake_payment_id,
        'razorpay_signature': signature,
    }, headers=headers)
    print('verify status', rvv2.status_code)
    print(rvv2.get_data(as_text=True))

    print('\nGET SUBSCRIPTION STATUS')
    rvs = client.get('/api/subscription/status', headers=headers)
    print('status status', rvs.status_code)
    print(rvs.get_data(as_text=True))

print('\nDone')
