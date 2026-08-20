import json
import secrets
from datetime import timedelta

from app import create_app
from app.services.subscription_service import SubscriptionService
from app.utils.time import utc_now

# Configuration for the private coupon
DISCOUNT_PERCENT = 50
EXPIRES_DAYS = 180
MAX_USES = 5

app = create_app()
service = SubscriptionService()

with app.app_context():
    # Generate a strong unguessable coupon code
    code = 'PRV-' + secrets.token_hex(16).upper()
    expires_at = utc_now() + timedelta(days=EXPIRES_DAYS)
    coupon = service.create_coupon(code, DISCOUNT_PERCENT, expires_at=expires_at, max_uses=MAX_USES)
    print(json.dumps({
        'code': coupon.get('code'),
        'discount_percent': coupon.get('discount_percent'),
        'expires_at': str(coupon.get('expires_at')),
        'max_uses': coupon.get('max_uses'),
        'uses': coupon.get('uses')
    }, indent=2))
