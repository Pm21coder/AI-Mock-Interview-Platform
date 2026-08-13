"""
Comprehensive subscription management service.

Handles subscription lifecycle, usage tracking, billing history, and feature access.
"""

from datetime import datetime, timedelta
from enum import Enum
import logging

from app import mongo
from app.config import Config

logger = logging.getLogger(__name__)


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
        try:
            user = mongo.db.users.find_one({'_id': user_id})
        except Exception as e:
            logger.error(f'Error fetching user {user_id}: {e}')
            user = None

        if not user:
            return self._free_tier_subscription()

        tier = user.get('subscription_tier', 'free')
        status = user.get('subscription_status', 'active')
        start_date = user.get('subscription_start_date')
        end_date = user.get('subscription_end_date')

        # Check if subscription has expired
        if end_date and datetime.utcnow() > end_date:
            # Auto-downgrade to free
            self.downgrade_to_free(user_id)
            return self._free_tier_subscription()

        # Reset monthly usage if needed
        if self._should_reset_monthly_usage(user):
            self._reset_monthly_usage(user_id)
            interviews_used = 0
        else:
            interviews_used = user.get('interviews_used_this_month', 0)

        plan_info = self.config_tiers.get(tier, self.config_tiers['free'])
        monthly_limit = plan_info['monthly_interviews']

        interviews_remaining = (
            max(0, monthly_limit - interviews_used)
            if monthly_limit != float('inf')
            else float('inf')
        )

        return {
            'tier': tier,
            'status': status,
            'interviews_used_this_month': interviews_used,
            'interviews_remaining': interviews_remaining,
            'monthly_limit': monthly_limit if monthly_limit != float('inf') else 'unlimited',
            'features': plan_info['features'],
            'subscription_start_date': start_date,
            'subscription_end_date': end_date,
            'plan_info': plan_info,
            'is_trial': user.get('is_trial', False),
            'trial_days_remaining': self._get_trial_days_remaining(user),
        }

    def create_subscription(self, user_id, tier, razorpay_order_id=None,
                          razorpay_payment_id=None, is_trial=False):
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

        start_date = datetime.utcnow()
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

            # Record in billing history
            self._record_billing_event(
                user_id, 'subscription_created', tier, start_date, end_date
            )
        except Exception as e:
            logger.error(f'Error creating subscription for user {user_id}: {e}')
            raise

        return self.get_user_subscription(user_id)

    def upgrade_subscription(self, user_id, new_tier, razorpay_order_id=None,
                            razorpay_payment_id=None):
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
            remaining_days = max(0, (old_end - datetime.utcnow()).days)
            if remaining_days > 0:
                self._record_proration_credit(user_id, current_tier, remaining_days)

        return self.create_subscription(
            user_id, new_tier, razorpay_order_id, razorpay_payment_id
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
                        'subscription_end_date': datetime.utcnow(),
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
            return False, {
                'error': 'Monthly interview limit reached',
                'tier': sub['tier'],
                'monthly_limit': monthly_limit,
                'interviews_used': sub['interviews_used_this_month'],
                'message': f'You have used all {monthly_limit} interviews for this month. '
                          f'Upgrade your plan to continue.'
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

        try:
            result = mongo.db.users.update_one(
                {'_id': user_id},
                {'$inc': {'interviews_used_this_month': 1}}
            )

            if result.matched_count > 0:
                user = mongo.db.users.find_one({'_id': user_id})
                new_count = user.get('interviews_used_this_month', 0)

                # Check if user is approaching limit
                sub = self.get_user_subscription(user_id)
                remaining = sub['interviews_remaining']
                if isinstance(remaining, int) and remaining <= 2:
                    self._send_usage_warning(user_id, sub)

                return new_count
        except Exception as e:
            logger.error(f'Error incrementing interview count for user {user_id}: {e}')

        return 1

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
                             end_date=None, amount=None):
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
                'timestamp': datetime.utcnow(),
                'start_date': start_date,
                'end_date': end_date,
                'amount': amount,
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
                'timestamp': datetime.utcnow(),
                'amount': credit,
                'remaining_days': remaining_days,
            })
        except Exception as e:
            logger.error(f'Error recording proration credit for user {user_id}: {e}')

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

        start_date = datetime.utcnow()
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

        remaining = (end_date - datetime.utcnow()).days
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

    def _should_reset_monthly_usage(self, user):
        """Check if monthly usage should be reset."""
        end_date = user.get('subscription_end_date')
        if not end_date:
            return False
        return datetime.utcnow() > end_date

    def _reset_monthly_usage(self, user_id):
        """Reset monthly usage counters."""
        try:
            now = datetime.utcnow()
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
