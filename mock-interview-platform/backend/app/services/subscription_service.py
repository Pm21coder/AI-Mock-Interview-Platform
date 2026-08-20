"""
Comprehensive subscription management service.

Handles subscription lifecycle, usage tracking, billing history, and feature access.
"""

from datetime import datetime, timedelta
from enum import Enum
import logging
import math

# Lazy/robust mongo proxy to allow unit tests to patch nested attributes
# even when the PyMongo instance hasn't been initialized yet.
class _MongoProxy:
    def __getattr__(self, name):
        try:
            from app import mongo as _real_mongo
            attr = getattr(_real_mongo, name, None)
            # If the real PyMongo exposes None for an attribute (e.g. db before init),
            # return a dummy proxy so attribute access chaining (for mocks) doesn't fail.
            if attr is None:
                raise AttributeError()
            return attr
        except Exception:
            # Return a dummy object that gracefully handles chained attribute access and calls
            class _Dummy:
                def __getattr__(self, _):
                    return _Dummy()
                def __call__(self, *args, **kwargs):
                    return None
                def __iter__(self):
                    return iter(())
            return _Dummy()

mongo = _MongoProxy()
from app.config import Config
from app.utils.mongo_state import is_mongo_available, mark_mongo_unavailable
from app.utils.time import utc_now
import json
import os

logger = logging.getLogger(__name__)

# Used only when MongoDB is unavailable during local development. Keeping this
# alongside the subscription service ensures every feature gate and usage check
# reads the same temporary plan state.
fallback_subscriptions = {}


class SubscriptionStatus(Enum):
    """Subscription status states."""
    ACTIVE = 'active'
    CANCELED = 'canceled'
    PAST_DUE = 'past_due'
    TRIALING = 'trialing'
    EXPIRED = 'expired'


class SubscriptionTier(Enum):
    """Available subscription tiers."""
    FREE = 'free'
    BASIC = 'basic'
    PRO = 'pro'


class SubscriptionService:
    """Service for managing user subscriptions."""

    def __init__(self):
        """Initialize the subscription service."""
        self.config_tiers = Config.SUBSCRIPTION_TIERS
        self.razorpay_amounts = Config.RAZORPAY_ORDER_AMOUNTS
        # In-memory short-lived cache for subscription status to reduce DB/third-party
        # lookups under high load and improve responsiveness for frequent checks.
        # This cache is intentionally short-lived to avoid serving stale quota data
        # for users actively taking interviews.
        self._status_cache = {}
        self._status_cache_ttl_seconds = getattr(Config, 'SUBSCRIPTION_STATUS_CACHE_TTL', 5)
        self._category_cache = {}
        self._category_cache_ttl_seconds = getattr(Config, 'QUESTION_CATEGORY_CACHE_TTL', 15)

    @staticmethod
    def _is_unlimited_limit(limit):
        """Normalize unlimited-plan markers across legacy and current storage formats."""
        if limit is None:
            return True
        if isinstance(limit, str):
            return limit.lower() == 'unlimited'
        if isinstance(limit, float):
            return math.isinf(limit)
        return False

    def invalidate_cache(self, user_id):
        """Clear cached subscription and category data for a user."""
        if user_id is None:
            self._status_cache.clear()
            self._category_cache.clear()
            return
        key = str(user_id)
        self._status_cache.pop(key, None)
        self._category_cache.pop(key, None)

    # ========================
    # Core Subscription Methods
    # ========================

    def get_user_subscription(self, user_id):
        """
        Get complete subscription details for a user.

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            dict: Subscription details with tier, status, usage, features
        """
        # Fast-path: return cached subscription if it exists and is fresh.
        try:
            cached = self._status_cache.get(str(user_id))
            if cached:
                ts, data = cached
                if (datetime.utcnow() - ts).total_seconds() < self._status_cache_ttl_seconds:
                    return data
        except Exception:
            # If cache access fails for any reason, continue to compute live.
            pass

        user = None
        if is_mongo_available():
            try:
                user = mongo.db.users.find_one({'_id': user_id})
            except Exception as exc:
                mark_mongo_unavailable(exc)
                logger.warning('Error fetching subscription user %s: %s', user_id, exc)

        if not user:
            fallback_subscription = fallback_subscriptions.get(str(user_id))
            if fallback_subscription:
                return self._get_fallback_subscription(fallback_subscription)

            # Local development accounts use demo_* ids and are stored in the
            # JSON auth store, even when MongoDB is online for interview data.
            # Read their persisted usage instead of returning a new Free-plan
            # object on every request.
            local_user = self._find_local_user(user_id)
            if local_user:
                email, user_record, users = local_user
                return self._get_local_user_subscription(
                    user_id, email, user_record, users,
                )

            return self._free_tier_subscription()

        tier = user.get('subscription_tier', 'free')
        status = user.get('subscription_status', 'active')
        start_date = user.get('subscription_start_date')
        end_date = user.get('subscription_end_date')

        # Separate billing-cycle reset from subscription expiry handling.
        if self._should_reset_monthly_usage(user):
            self._reset_monthly_usage(user_id)
            interviews_used = 0
            end_date = user.get('subscription_end_date')
        else:
            interviews_used = user.get('interviews_used_this_month', 0)

        # A paid plan that has expired should be demoted to Free.
        if end_date and utc_now() > end_date and tier != 'free':
            self.downgrade_to_free(user_id)
            return self._free_tier_subscription()

        plan_info = self.config_tiers.get(tier, self.config_tiers['free'])
        # Allow user-level override for monthly limit (used for master/unlimited coupons)
        monthly_limit = user.get('subscription_monthly_limit', plan_info.get('monthly_interviews'))
        is_unlimited = self._is_unlimited_limit(monthly_limit)

        interviews_remaining = 'unlimited' if is_unlimited else max(0, monthly_limit - interviews_used)

        result = {
           'tier': tier,
           'status': status,
           'interviews_used_this_month': interviews_used,
           'interviews_remaining': interviews_remaining,
           'monthly_limit': 'unlimited' if is_unlimited else monthly_limit,
           'features': plan_info['features'],
           'subscription_start_date': start_date,
           'subscription_end_date': end_date,
           'plan_info': plan_info,
           'is_trial': user.get('is_trial', False),
           'trial_days_remaining': self._get_trial_days_remaining(user),
        }
        # Cache the computed subscription status for a short period to reduce
        # repeated DB reads from synchronous dashboard requests.
        try:
           self._status_cache[str(user_id)] = (datetime.utcnow(), result)
        except Exception:
           pass
        return result

    def create_subscription(self, user_id, tier, razorpay_order_id=None,
                          razorpay_payment_id=None, is_trial=False, coupon_code=None):
        """
        Create or activate a subscription for a user.

        Args:
            user_id: The user's MongoDB ObjectId
            tier: Subscription tier (basic, pro, free)
            razorpay_order_id: Razorpay order ID (optional)
            razorpay_payment_id: Razorpay payment ID (optional)
            is_trial: Whether this is a trial subscription

        Returns:
            dict: Updated subscription details
        """
        if tier not in ['free', 'basic', 'pro']:
            raise ValueError(f'Invalid subscription tier: {tier}')

        start_date = utc_now()
        # Free tier doesn't expire, paid tiers last 30 days
        duration_days = 30 if tier != 'free' else 365 * 100
        end_date = start_date + timedelta(days=duration_days)

        update_data = {
            'subscription_tier': tier,
            'subscription_status': 'active' if not is_trial else 'trialing',
            'subscription_start_date': start_date,
            'subscription_end_date': end_date,
            'interviews_used_this_month': 0,
            'is_trial': is_trial,
        }

        if razorpay_order_id:
            update_data['razorpay_order_id'] = razorpay_order_id
        if razorpay_payment_id:
            update_data['razorpay_payment_id'] = razorpay_payment_id

        try:
            result = mongo.db.users.update_one(
                {'_id': user_id},
                {'$set': update_data}
            )
            if result.matched_count == 0:
                logger.warning(f'User {user_id} not found for subscription creation')

            # Record in billing history. Include coupon if present.
            billing_amount = None
            if coupon_code:
                # Don't attempt to compute exact amount server-side unless order info provided
                # but record that a coupon was applied for audit.
                self._record_billing_event(
                    user_id, 'subscription_created', tier, start_date, end_date, amount=billing_amount, coupon_code=coupon_code
                )
            else:
                self._record_billing_event(
                    user_id, 'subscription_created', tier, start_date, end_date, amount=billing_amount
                )
        except Exception as e:
            logger.error(f'Error creating subscription for user {user_id}: {e}')
            raise

        return self.get_user_subscription(user_id)

    def upgrade_subscription(self, user_id, new_tier, razorpay_order_id=None,
                            razorpay_payment_id=None, coupon_code=None):
        """
        Upgrade a user's subscription to a higher tier.

        Args:
            user_id: The user's MongoDB ObjectId
            new_tier: New subscription tier
            razorpay_order_id: Razorpay order ID
            razorpay_payment_id: Razorpay payment ID

        Returns:
            dict: Updated subscription details
        """
        current_sub = self.get_user_subscription(user_id)
        current_tier = current_sub['tier']

        # Tier hierarchy: free < basic < pro
        tier_order = {'free': 0, 'basic': 1, 'pro': 2}
        if tier_order.get(new_tier, -1) <= tier_order.get(current_tier, -1):
            raise ValueError(f'Cannot upgrade from {current_tier} to {new_tier}')

        # Record old tier
        old_start = current_sub.get('subscription_start_date')
        old_end = current_sub.get('subscription_end_date')

        # Calculate prorated credit if applicable
        if current_tier != 'free' and old_end:
            remaining_days = max(0, (old_end - utc_now()).days)
            if remaining_days > 0:
                self._record_proration_credit(user_id, current_tier, remaining_days)

        return self.create_subscription(
            user_id, new_tier, razorpay_order_id, razorpay_payment_id, coupon_code=coupon_code
        )

    def downgrade_to_free(self, user_id):
        """
        Downgrade a user's subscription to the free tier.

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            dict: Updated subscription details
        """
        try:
            mongo.db.users.update_one(
                {'_id': user_id},
                {
                    '$set': {
                        'subscription_tier': 'free',
                        'subscription_status': 'canceled',
                        'subscription_end_date': utc_now(),
                    }
                }
            )
            self._record_billing_event(user_id, 'subscription_canceled', 'free')
        except Exception as e:
            logger.error(f'Error downgrading user {user_id}: {e}')
            raise

        return self.get_user_subscription(user_id)

    def cancel_subscription(self, user_id):
        """
        Cancel a user's subscription (downgrade to free).

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            dict: Updated subscription details
        """
        return self.downgrade_to_free(user_id)

    # ========================
    # Usage Tracking
    # ========================

    def check_interview_limit(self, user_id):
        """
        Check if user can create another interview.

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            tuple: (can_proceed: bool, error_info: dict|None)
        """
        sub = self.get_user_subscription(user_id)

        # Guest users can always proceed (no quota)
        if user_id == 'guest':
            return True, None

        # Unlimited plans can always proceed
        monthly_limit = sub['monthly_limit']
        if monthly_limit == 'unlimited':
            return True, None

        # Check actual limit
        if sub['interviews_remaining'] <= 0:
            required_tier = 'basic' if sub['tier'] == 'free' else 'pro'
            return False, {
                'error': 'Monthly interview limit reached',
                'code': 'interview_limit_reached',
                'tier': sub['tier'],
                'required_tier': required_tier,
                'monthly_limit': monthly_limit,
                'interviews_used': sub['interviews_used_this_month'],
                'message': f'You have used all {monthly_limit} interviews for this month. '
                          f'Upgrade to {required_tier.title()} to continue.',
                'upgrade_url': '/subscription',
            }

        return True, None

    def increment_interview_count(self, user_id):
        """
        Increment the monthly interview count for a user.

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            int: New interview count
        """
        if user_id == 'guest':
            return 1

        fallback_subscription = fallback_subscriptions.get(str(user_id))
        if fallback_subscription:
            fallback_subscription['interviews_used_this_month'] = (
                fallback_subscription.get('interviews_used_this_month', 0) + 1
            )
            self.invalidate_cache(user_id)
            return fallback_subscription['interviews_used_this_month']

        local_user = self._find_local_user(user_id)
        if local_user:
            email, user_record, users = local_user
            # First recover any sessions created before local-account usage was
            # persisted, then atomically advance the local counter.
            self._get_local_user_subscription(user_id, email, user_record, users)
            try:
                interviews_used = int(user_record.get('interviews_used_this_month', 0))
            except (TypeError, ValueError):
                interviews_used = 0

            new_count = interviews_used + 1
            user_record['interviews_used_this_month'] = new_count
            self._save_local_user(email, user_record, users)
            self.invalidate_cache(user_id)

            sub = self._get_local_user_subscription(user_id, email, user_record, users)
            remaining = sub['interviews_remaining']
            if isinstance(remaining, int) and remaining <= 2:
                self._send_usage_warning(user_id, sub)
            return new_count

        try:
            result = mongo.db.users.update_one(
                {'_id': user_id},
                {'$inc': {'interviews_used_this_month': 1}}
            )

            # Some PyMongo proxies or test doubles may return None — handle safely
            matched = getattr(result, 'matched_count', 0) if result is not None else 0
            if matched > 0:
                user = mongo.db.users.find_one({'_id': user_id})
                new_count = user.get('interviews_used_this_month', 0)
                self.invalidate_cache(user_id)

                # Check if user is approaching limit
                sub = self.get_user_subscription(user_id)
                remaining = sub['interviews_remaining']
                if isinstance(remaining, int) and remaining <= 2:
                    self._send_usage_warning(user_id, sub)

                return new_count

            # If no DB document matched, try fallback for demo/local accounts
            if str(user_id).startswith('demo_'):
                try:
                    local = self._find_local_user(user_id)
                    if local:
                        email, user_record, users = local
                        try:
                            user_record['interviews_used_this_month'] = int(user_record.get('interviews_used_this_month', 0)) + 1
                        except Exception:
                            user_record['interviews_used_this_month'] = 1
                        self._save_local_user(email, user_record, users)
                        self.invalidate_cache(user_id)

                        # Check limit warning for local user
                        sub = self.get_user_subscription(user_id)
                        remaining = sub['interviews_remaining']
                        if isinstance(remaining, int) and remaining <= 2:
                            self._send_usage_warning(user_id, sub)

                        return user_record['interviews_used_this_month']
                except Exception as lf_exc:
                    logger.warning('Failed to update local demo user interview count for %s: %s', user_id, lf_exc)

            logger.warning('No matching user document found to increment interviews for user %s', user_id)
        except Exception as e:
            logger.error(f'Error incrementing interview count for user {user_id}: {e}')

            # On exception, attempt local demo fallback before giving up
            if str(user_id).startswith('demo_'):
                try:
                    local = self._find_local_user(user_id)
                    if local:
                        email, user_record, users = local
                        try:
                            user_record['interviews_used_this_month'] = int(user_record.get('interviews_used_this_month', 0)) + 1
                        except Exception:
                            user_record['interviews_used_this_month'] = 1
                        self._save_local_user(email, user_record, users)
                        self.invalidate_cache(user_id)
                        return user_record['interviews_used_this_month']
                except Exception:
                    pass

        return 1

    def _find_local_user(self, user_id):
        """Return the persisted local auth record for a demo account, if any."""
        if not str(user_id).startswith('demo_'):
            return None

        try:
            # Import lazily to avoid a route/service import cycle at startup.
            from app.routes.auth import load_local_auth_users

            users = load_local_auth_users()
            for email, user in users.items():
                if str(user.get('_id')) == str(user_id):
                    return email, user, users
        except Exception as exc:
            logger.warning('Unable to load local subscription user %s: %s', user_id, exc)

        return None

    def _save_local_user(self, email, user_record, users):
        """Persist a changed local auth record without affecting other users."""
        try:
            from app.routes.auth import save_local_auth_users

            users[email] = user_record
            save_local_auth_users(users)
        except Exception as exc:
            logger.warning('Unable to save local subscription user %s: %s', email, exc)

    @staticmethod
    def _as_datetime(value):
        """Normalize datetimes loaded from the JSON local-auth store."""
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return None

        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except ValueError:
            return None

    def _count_local_interviews_since(self, user_id, start_date):
        """Recover sessions recorded before demo-account usage was persisted."""
        query = {'user_id': str(user_id)}
        if start_date:
            query['created_at'] = {'$gte': start_date}

        if not is_mongo_available():
            return 0

        try:
            return mongo.db.interviews.count_documents(query)
        except Exception as exc:
            mark_mongo_unavailable(exc)
            return 0

    def _get_local_user_subscription(self, user_id, email, user_record, users):
        """Build and persist subscription state for JSON-backed demo accounts."""
        now = utc_now()
        tier = user_record.get('subscription_tier', 'free')
        status = user_record.get('subscription_status', 'active')
        start_date = self._as_datetime(user_record.get('subscription_start_date'))
        end_date = self._as_datetime(user_record.get('subscription_end_date'))
        changed = False

        # Local accounts use the same 30-day billing cycle as database users.
        if not start_date or not end_date or now > end_date:
            start_date = now
            end_date = now + timedelta(days=30)
            user_record['subscription_start_date'] = start_date
            user_record['subscription_end_date'] = end_date
            user_record['interviews_used_this_month'] = 0
            changed = True

        try:
            interviews_used = int(user_record.get('interviews_used_this_month', 0))
        except (TypeError, ValueError):
            interviews_used = 0

        # Previous versions stored demo sessions in MongoDB but failed to
        # update the local auth record. Keep the larger value so this repair
        # never gives a user extra quota after a server restart.
        recovered_count = self._count_local_interviews_since(user_id, start_date)
        if recovered_count > interviews_used:
            interviews_used = recovered_count
            user_record['interviews_used_this_month'] = interviews_used
            changed = True

        if changed:
            self._save_local_user(email, user_record, users)

        plan_info = self.config_tiers.get(tier, self.config_tiers['free'])
        monthly_limit = plan_info['monthly_interviews']
        interviews_remaining = (
            max(0, monthly_limit - interviews_used)
            if monthly_limit is not None
            else 'unlimited'
        )

        return {
            'tier': tier,
            'status': status,
            'interviews_used_this_month': interviews_used,
            'interviews_remaining': interviews_remaining,
            'monthly_limit': monthly_limit if monthly_limit is not None else 'unlimited',
            'features': plan_info['features'],
            'subscription_start_date': start_date,
            'subscription_end_date': end_date,
            'plan_info': plan_info,
            'is_trial': user_record.get('is_trial', False),
            'trial_days_remaining': 0,
        }

    def get_usage_stats(self, user_id):
        """
        Get detailed usage statistics for a user.

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            dict: Usage statistics including interviews, features used, etc.
        """
        try:
            user = mongo.db.users.find_one({'_id': user_id})
            interviews = list(mongo.db.interviews.find(
                {'user_id': user_id}
            ).limit(100))
        except Exception:
            user = None
            interviews = []

        sub = self.get_user_subscription(user_id)

        return {
            'subscription': sub,
            'total_interviews': len(interviews),
            'interviews_this_month': sub['interviews_used_this_month'],
            'interviews_remaining': sub['interviews_remaining'],
            'interviews_by_category': self._count_interviews_by_category(interviews),
            'most_common_role': self._get_most_common_role(interviews),
            'average_score': self._get_average_score(interviews),
            'account_created': user.get('created_at') if user else None,
        }

    # ========================
    # Billing History
    # ========================

    def get_billing_history(self, user_id, limit=50):
        """
        Get billing history for a user.

        Args:
            user_id: The user's MongoDB ObjectId
            limit: Maximum number of records to return

        Returns:
            list: Billing history records
        """
        try:
            history = list(mongo.db.billing_history.find(
                {'user_id': user_id}
            ).sort('timestamp', -1).limit(limit))

            # Convert ObjectId to string for JSON serialization
            for record in history:
                if '_id' in record:
                    record['_id'] = str(record['_id'])
            return history
        except Exception as e:
            logger.error(f'Error fetching billing history for user {user_id}: {e}')
            return []

    def _record_billing_event(self, user_id, event_type, tier, start_date=None,
                             end_date=None, amount=None, coupon_code=None):
        """
        Record a billing event in the history.

        Args:
            user_id: The user's MongoDB ObjectId
            event_type: Type of event (subscription_created, upgraded, etc.)
            tier: Subscription tier
            start_date: Subscription start date
            end_date: Subscription end date
            amount: Amount paid (if applicable)
        """
        try:
            mongo.db.billing_history.insert_one({
                'user_id': user_id,
                'event_type': event_type,
                'tier': tier,
                'timestamp': utc_now(),
                'start_date': start_date,
                'end_date': end_date,
                'amount': amount,
                'coupon_code': coupon_code,
            })
        except Exception as e:
            logger.error(f'Error recording billing event for user {user_id}: {e}')

    def _record_proration_credit(self, user_id, tier, remaining_days):
        """Record a proration credit for unused days."""
        try:
            plan_price = self.config_tiers.get(tier, {}).get('price', 0)
            daily_rate = plan_price / 30
            credit = daily_rate * remaining_days

            mongo.db.billing_history.insert_one({
                'user_id': user_id,
                'event_type': 'proration_credit',
                'tier': tier,
                'timestamp': utc_now(),
                'amount': credit,
                'remaining_days': remaining_days,
            })
        except Exception as e:
            logger.error(f'Error recording proration credit for user {user_id}: {e}')

    # ========================
    # Coupon Management
    # ========================

    # ========================
    # Trial Period
    # ========================

    def start_trial(self, user_id, tier='pro', trial_days=7):
        """
        Start a trial subscription for a user.

        Args:
            user_id: The user's MongoDB ObjectId
            tier: Tier to trial
            trial_days: Number of days for trial

        Returns:
            dict: Updated subscription details
        """
        if tier not in ['basic', 'pro']:
            raise ValueError(f'Cannot trial tier: {tier}')

        start_date = utc_now()
        end_date = start_date + timedelta(days=trial_days)

        try:
            mongo.db.users.update_one(
                {'_id': user_id},
                {
                    '$set': {
                        'subscription_tier': tier,
                        'subscription_status': 'trialing',
                        'subscription_start_date': start_date,
                        'subscription_end_date': end_date,
                        'interviews_used_this_month': 0,
                        'is_trial': True,
                        'trial_start_date': start_date,
                    }
                }
            )
            self._record_billing_event(
                user_id, 'trial_started', tier, start_date, end_date
            )
        except Exception as e:
            logger.error(f'Error starting trial for user {user_id}: {e}')
            raise

        return self.get_user_subscription(user_id)

    def _get_trial_days_remaining(self, user):
        """Get the number of trial days remaining."""
        if not user.get('is_trial'):
            return 0

        end_date = user.get('subscription_end_date')
        if not end_date:
            return 0

        remaining = (end_date - utc_now()).days
        return max(0, remaining)

    # ========================
    # Coupon Management
    # ========================

    def create_coupon(self, code, discount_percent, expires_at=None, max_uses=None, **extra_fields):
        """Create a coupon document.

        Args:
            code: Coupon code string (case-insensitive)
            discount_percent: integer 1-100
            expires_at: optional datetime
            max_uses: optional integer
            extra_fields: dict of additional fields to store on coupon (optional)
        Returns: coupon dict
        """
        if not code or not isinstance(discount_percent, (int, float)):
            raise ValueError('Invalid coupon parameters')
        coupon = {
            'code': str(code).strip().upper(),
            'discount_percent': int(discount_percent),
            'created_at': utc_now(),
            'expires_at': expires_at,
            'max_uses': int(max_uses) if max_uses is not None else None,
            'uses': 0,
        }
        # Merge any additional optional fields (e.g., grant_unlimited, grant_tier)
        if extra_fields:
            for k, v in extra_fields.items():
                coupon[k] = v
        try:
            mongo.db.coupons.insert_one(coupon)
        except Exception as e:
            logger.error(f'Failed to create coupon {code}: {e}')
            raise
        return coupon

    def validate_and_redeem_coupon(self, code):
        """Atomically validate and reserve (redeem) a coupon.

        Returns discount_percent if successful, otherwise None.
        """
        if not code:
            return None
        code_norm = str(code).strip().upper()
        try:
            coupon = None
            # Try MongoDB first if available
            if is_mongo_available():
                try:
                    coupon = mongo.db.coupons.find_one({'code': code_norm})
                except Exception:
                    coupon = None

            # If coupon not found in Mongo, try fallback file for master coupons
            if not coupon:
                try:
                    data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'master_coupons.json')
                    if os.path.exists(data_path):
                        with open(data_path, 'r', encoding='utf-8') as f:
                            arr = json.load(f)
                        for c in arr:
                            if str(c.get('code', '')).strip().upper() == code_norm:
                                coupon = c
                                break
                except Exception:
                    coupon = None

            if not coupon:
                return None

            # Check expiry if available (Mongo datetime) or assume valid for string
            if coupon.get('expires_at'):
                try:
                    expires = coupon['expires_at']
                    if not isinstance(expires, str) and utc_now() > expires:
                        return None
                except Exception:
                    pass

            max_uses = coupon.get('max_uses')
            uses = coupon.get('uses', 0)
            if max_uses is not None and uses >= max_uses:
                return None

            # If coupon comes from Mongo, try to increment uses atomically
            if is_mongo_available() and coupon and coupon.get('_id'):
                try:
                    filter_q = {'code': code_norm}
                    if max_uses is not None:
                        filter_q['uses'] = {'$lt': max_uses}
                    res = mongo.db.coupons.update_one(filter_q, {'$inc': {'uses': 1}})
                    if not res or getattr(res, 'matched_count', 0) == 0:
                        return None
                except Exception:
                    # If updating failed, fall through and accept for now
                    pass

            # For fallback-file coupons (master coupons) we do not track uses
            return coupon.get('discount_percent')
        except Exception as e:
            logger.error(f'Coupon validation failed for {code}: {e}')
            return None

    def get_coupon_info(self, code):
        """Check coupon validity without redeeming it. Returns a dict with
        discount_percent, expires_at, max_uses, uses if coupon exists and is
        currently valid; otherwise returns None.
        """
        if not code:
            return None
        code_norm = str(code).strip().upper()
        try:
            coupon = None
            # Try MongoDB first if available
            if is_mongo_available():
                try:
                    coupon = mongo.db.coupons.find_one({'code': code_norm})
                except Exception:
                    coupon = None
            # If no coupon in Mongo, try fallback master coupon file
            if not coupon:
                try:
                    data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'master_coupons.json')
                    if os.path.exists(data_path):
                        with open(data_path, 'r', encoding='utf-8') as f:
                            arr = json.load(f)
                        for c in arr:
                            if str(c.get('code', '')).strip().upper() == code_norm:
                                coupon = c
                                break
                except Exception:
                    coupon = None

            if not coupon:
                return None

            # Normalize expiry check (works for both datetime from Mongo or string in file)
            if coupon.get('expires_at'):
                try:
                    expires = coupon['expires_at']
                    # If string, we won't parse strictly; assume valid for master coupons
                    if isinstance(expires, str):
                        # No check for string expiry; assume master coupons in file are valid
                        pass
                    else:
                        if utc_now() > expires:
                            return None
                except Exception:
                    pass

            # Check usage cap
            max_uses = coupon.get('max_uses')
            uses = coupon.get('uses', 0)
            if max_uses is not None and uses >= max_uses:
                return None

            return {
                'code': coupon.get('code'),
                'discount_percent': coupon.get('discount_percent'),
                'expires_at': coupon.get('expires_at'),
                'max_uses': coupon.get('max_uses'),
                'uses': coupon.get('uses', 0),
                # Include master-coupon specific fields so callers (e.g. verify-payment)
                # can honor behaviors like grant_unlimited and grant_tier even when
                # the coupon is defined in the fallback JSON file.
                'grant_unlimited': coupon.get('grant_unlimited', False),
                'grant_tier': coupon.get('grant_tier'),
                'subscription_monthly_limit': coupon.get('subscription_monthly_limit'),
            }
        except Exception as e:
            logger.error(f'Failed to read coupon info for {code}: {e}')
            return None

        """Get the number of trial days remaining."""
        if not user.get('is_trial'):
            return 0

        end_date = user.get('subscription_end_date')
        if not end_date:
            return 0

        remaining = (end_date - utc_now()).days
        return max(0, remaining)

    # ========================
    # Feature Access Control
    # ========================

    def has_feature(self, user_id, feature_name):
        """
        Check if a user has access to a specific feature.

        Args:
            user_id: The user's MongoDB ObjectId
            feature_name: Name of the feature

        Returns:
            bool: True if user has access to the feature
        """
        sub = self.get_user_subscription(user_id)
        features = sub.get('features', {})
        return features.get(feature_name, False)

    def get_available_features(self, user_id):
        """
        Get all features available to a user.

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            dict: Feature flags
        """
        sub = self.get_user_subscription(user_id)
        return sub.get('features', {})

    # ========================
    # Helper Methods
    # ========================

    def _free_tier_subscription(self):
        """Return a free tier subscription object."""
        plan_info = self.config_tiers.get('free', {})
        return {
            'tier': 'free',
            'status': 'active',
            'interviews_used_this_month': 0,
            'interviews_remaining': plan_info.get('monthly_interviews', 3),
            'monthly_limit': plan_info.get('monthly_interviews', 3),
            'features': plan_info.get('features', {}),
            'subscription_start_date': None,
            'subscription_end_date': None,
            'plan_info': plan_info,
            'is_trial': False,
            'trial_days_remaining': 0,
        }

    def _get_fallback_subscription(self, fallback_subscription):
        """Return a subscription payload for a locally stored paid plan."""
        tier = fallback_subscription.get('tier', 'free')
        end_date = fallback_subscription.get('subscription_end_date')
        if end_date and utc_now() > end_date:
            return self._free_tier_subscription()

        plan_info = self.config_tiers.get(tier, self.config_tiers['free'])
        monthly_limit = plan_info['monthly_interviews']
        interviews_used = fallback_subscription.get('interviews_used_this_month', 0)
        interviews_remaining = (
            max(0, monthly_limit - interviews_used)
            if monthly_limit is not None
            else 'unlimited'
        )

        return {
            'tier': tier,
            'status': fallback_subscription.get('status', 'active'),
            'interviews_used_this_month': interviews_used,
            'interviews_remaining': interviews_remaining,
            'monthly_limit': monthly_limit if monthly_limit is not None else 'unlimited',
            'features': plan_info['features'],
            'subscription_start_date': fallback_subscription.get('subscription_start_date'),
            'subscription_end_date': end_date,
            'plan_info': plan_info,
            'is_trial': False,
            'trial_days_remaining': 0,
        }

    def _should_reset_monthly_usage(self, user):
        """Check if monthly usage should be reset for a user plan cycle."""
        end_date = user.get('subscription_end_date')
        if not end_date:
            return True
        return utc_now() > end_date

    def _reset_monthly_usage(self, user_id):
        """Reset monthly usage counters."""
        try:
            now = utc_now()
            mongo.db.users.update_one(
                {'_id': user_id},
                {
                    '$set': {
                        'interviews_used_this_month': 0,
                        'subscription_start_date': now,
                        'subscription_end_date': now + timedelta(days=30),
                    }
                }
            )
        except Exception as e:
            logger.error(f'Error resetting monthly usage for user {user_id}: {e}')

    def _send_usage_warning(self, user_id, subscription):
        """Send a warning when user is approaching their limit."""
        logger.info(
            f'User {user_id} approaching limit: '
            f'{subscription["interviews_used_this_month"]}'
            f'/{subscription["monthly_limit"]}'
        )
        # TODO: Implement email notification

    def _count_interviews_by_category(self, interviews):
        """Count interviews by category."""
        counts = {}
        for interview in interviews:
            questions = interview.get('questions', [])
            for question in questions:
                category = question.get('category', 'unknown')
                counts[category] = counts.get(category, 0) + 1
        return counts

    def _get_most_common_role(self, interviews):
        """Get the most commonly practiced job role."""
        roles = {}
        for interview in interviews:
            role = interview.get('job_role', 'unknown')
            roles[role] = roles.get(role, 0) + 1
        return max(roles, key=roles.get) if roles else None

    def _get_average_score(self, interviews):
        """Calculate average score across all interviews."""
        if not interviews:
            return None

        total_score = 0
        count = 0
        for interview in interviews:
            feedback = interview.get('feedback', [])
            for item in feedback:
                if isinstance(item, dict) and 'score' in item:
                    total_score += item['score']
                    count += 1

        return total_score / count if count > 0 else None

    # ========================
    # Feature Access Methods
    # ========================

    def get_available_question_categories(self, user_id, subscription=None):
        """
        Get the list of question categories available to a user based on tier.

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            list: Available category names or 'all' for unlimited
        """
        sub = subscription or self.get_user_subscription(user_id)
        tier = sub['tier']
        plan_info = self.config_tiers.get(tier, {})
        
        categories_access = plan_info.get('question_categories', 'standard')
        
        if categories_access == 'all':
            return ['technical', 'behavioral', 'situational', 'system_design']
        else:
            # Free tier: standard categories only
            return ['technical', 'behavioral']

    def get_feedback_history_days(self, user_id):
        """
        Get the number of days feedback history should be retained for a user.

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            int or None: Days to retain (None = unlimited)
        """
        sub = self.get_user_subscription(user_id)
        tier = sub['tier']
        plan_info = self.config_tiers.get(tier, {})
        
        return plan_info.get('feedback_history_days', 7)

    def filter_feedback_by_history_limit(self, user_id, feedback_records):
        """
        Filter feedback records based on user's subscription tier.

        Args:
            user_id: The user's MongoDB ObjectId
            feedback_records: List of feedback records with timestamp

        Returns:
            list: Filtered feedback records
        """
        history_days = self.get_feedback_history_days(user_id)
        
        if history_days is None:
            # Unlimited history
            return feedback_records
        
        cutoff_date = utc_now() - timedelta(days=history_days)
        filtered = []
        
        for record in feedback_records:
            timestamp = record.get('timestamp') or record.get('created_at')
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except (ValueError, TypeError):
                        continue
                if timestamp >= cutoff_date:
                    filtered.append(record)
            else:
                # Keep records without timestamp
                filtered.append(record)
        
        return filtered

    def should_use_premium_ai_coaching(self, user_id):
        """
        Check if user should receive premium AI coaching (Pro tier feature).

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            bool: True if user has premium AI coaching
        """
        return self.has_feature(user_id, 'premium_ai_coaching')

    def has_advanced_analytics(self, user_id):
        """
        Check if user has access to advanced analytics (Pro tier feature).

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            bool: True if user has advanced analytics access
        """
        return self.has_feature(user_id, 'advanced_analytics')

    def has_email_support(self, user_id):
        """
        Check if user has access to email support (Basic+ tier feature).

        Args:
            user_id: The user's MongoDB ObjectId

        Returns:
            bool: True if user has email support
        """
        return self.has_feature(user_id, 'email_support')

    def get_plan_comparison(self):
        """
        Get a detailed comparison of all subscription plans.

        Returns:
            dict: Plan comparison with all features
        """
        comparison = {}
        
        for tier_name, tier_config in self.config_tiers.items():
            comparison[tier_name] = {
                'name': tier_config.get('name', ''),
                'price': tier_config.get('price', 0),
                'monthly_interviews': tier_config.get('monthly_interviews', 0),
                'feedback_history_days': tier_config.get('feedback_history_days'),
                'question_categories': tier_config.get('question_categories', 'standard'),
                'features': tier_config.get('features', {}),
            }
        
        return comparison
