import hmac
import hashlib
import time
from datetime import datetime

from app import create_app
from app.config import Config


def test_master_codes_activate_unlimited():
    app = create_app()
    client = app.test_client()

    # Register a fresh user
    email = f"integration.master+{int(datetime.utcnow().timestamp())}@example.com"
    rv = client.post('/api/auth/register', json={'email': email, 'password': 'TestPass1!'})
    assert rv.status_code in (200, 201)
    data = rv.get_json()
    token = data.get('token') if isinstance(data, dict) else None
    # If token wasn't returned, log in to retrieve it
    if not token:
        rv2 = client.post('/api/auth/login', json={'email': email, 'password': 'TestPass1!'})
        assert rv2.status_code in (200, 201)
        token = rv2.get_json().get('token')

    assert token
    headers = {'Authorization': f'Bearer {token}'}

    master_codes = [
        'MASTER-BASIC-E8E588F630E6E93F',
        'MASTER-PRO-16BAEA3245C7D44A',
    ]

    for code in master_codes:
        # create order for the appropriate tier inferred from code (basic/pro)
        expected_tier = 'pro' if 'PRO' in code else 'basic'
        rv_order = client.post('/api/subscription/create-order', json={'tier': expected_tier, 'coupon_code': code}, headers=headers)
        assert rv_order.status_code == 200, f"create-order failed: {rv_order.get_data(as_text=True)}"
        order_data = rv_order.get_json()
        order_id = order_data.get('order_id')
        assert order_id

        # Simulate a Razorpay payment: craft a fake payment id and HMAC signature
        fake_payment_id = f'pay_test_{int(time.time() * 1000)}'
        msg = f"{order_id}|{fake_payment_id}".encode('utf-8')
        secret = (Config.RAZORPAY_KEY_SECRET or '').encode('utf-8')
        signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        rv_verify = client.post('/api/subscription/verify-payment', json={
            'razorpay_order_id': order_id,
            'razorpay_payment_id': fake_payment_id,
            'razorpay_signature': signature,
        }, headers=headers)
        assert rv_verify.status_code == 200, f"verify-payment failed: {rv_verify.get_data(as_text=True)}"

        # Fetch subscription status
        rv_status = client.get('/api/subscription/status', headers=headers)
        assert rv_status.status_code == 200
        status = rv_status.get_json()
        assert status.get('tier') == expected_tier

        # Two acceptable success modes (environment-dependent):
        # 1) The user document was updated in Mongo and the subscription is unlimited
        # 2) Mongo was unavailable and a fallback in-memory subscription was created
        if status.get('subscription_end_date') is None and status.get('monthly_limit') == 'unlimited':
            # Success: unlimited applied
            continue

        # Otherwise assert fallback subscription was applied
        import jwt
        from app.config import Config as _Config
        from app.services.subscription_service import fallback_subscriptions as _fallback
        payload = jwt.decode(token, _Config.JWT_SECRET_KEY, algorithms=['HS256'])
        uid = payload.get('user_id')
        assert uid is not None
        fb = _fallback.get(str(uid)) or _fallback.get(uid)
        assert fb is not None, f"No fallback subscription found for user {uid}; status={status}"
        # If coupon was unlimited, fallback should have subscription_end_date == None
        assert fb.get('subscription_end_date') is None
        assert fb.get('subscription_monthly_limit') is None

