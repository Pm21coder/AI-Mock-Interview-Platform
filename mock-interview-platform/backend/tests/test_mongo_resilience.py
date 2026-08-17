from unittest.mock import patch

from flask import Flask

from app.services.subscription_service import SubscriptionService


def test_subscription_lookup_skips_mongo_when_marked_unavailable():
    app = Flask(__name__)
    app.config['MONGO_AVAILABLE'] = False

    with app.app_context(), patch(
        'app.services.subscription_service.mongo.db.users.find_one'
    ) as find_one:
        subscription = SubscriptionService().get_user_subscription('offline-user')

    assert subscription['tier'] == 'free'
    find_one.assert_not_called()
