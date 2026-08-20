import json
import secrets
from datetime import timedelta

from app import create_app
from app.utils.time import utc_now

app = create_app()

MASTER_TIER_CONFIG = [
    ('MASTER-BASIC-' + secrets.token_hex(8).upper(), 'basic'),
    ('MASTER-PRO-' + secrets.token_hex(8).upper(), 'pro'),
]

with app.app_context():
    from app import mongo
    coupons = []
    from app.services.subscription_service import SubscriptionService
    service = SubscriptionService()
    for code, tier in MASTER_TIER_CONFIG:
        try:
            coupon = service.create_coupon(code, 0, expires_at=utc_now() + timedelta(days=3650), max_uses=None, grant_unlimited=True, grant_tier=tier)
            coupons.append(coupon)
        except Exception as e:
            print('Failed to create coupon', code, e)

    print(json.dumps([{ 'code': c['code'], 'grant_tier': c['grant_tier'], 'grant_unlimited': c['grant_unlimited']} for c in coupons], indent=2))
