from datetime import datetime, timedelta
import hmac
import hashlib

import razorpay
from flask import Blueprint, current_app, jsonify, request
from razorpay.errors import BadRequestError, GatewayError, ServerError

from app import mongo
from app.config import Config
from app.utils.auth import token_required

subscription_bp = Blueprint('subscription', __name__)

fallback_razorpay_orders = {}
fallback_subscriptions = {}

# Initialize the Razorpay client. Credentials come from environment variables
# (Config.RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET) so that secrets are never
# hard-coded in source files.
razorpay_client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))


def _get_current_user():
    """Return the current user dict set by the token_required decorator."""
    return request.current_user


def _is_real_user(user):
    """True when a request has an authenticated account, including fallback accounts."""
    if not user:
        return False
    user_id = str(user.get('_id', ''))
    return user_id != 'guest'


def _order_amount_for_tier(tier):
    """Return the order amount (in paise) for the given tier, or None."""
    return Config.RAZORPAY_ORDER_AMOUNTS.get(tier)


def _razorpay_order_error_response(exc):
    """Return a user-safe response for Razorpay order creation failures."""
    error_message = str(exc).lower()
    if any(term in error_message for term in ('auth', 'credential', 'key')):
        return jsonify({
            'error': 'Razorpay authentication failed. Check your key id and key secret.'
        }), 401
    if isinstance(exc, (GatewayError, ServerError)):
        return jsonify({
            'error': 'Razorpay is temporarily unavailable. Please try again in a moment.'
        }), 502
    return jsonify({'error': 'Razorpay could not create the order'}), 500


def _subscription_status_payload(tier, status='active', interviews_used=0,
                                 start_date=None, end_date=None):
    """Build the subscription status response for Mongo and fallback users."""
    plan_info = Config.SUBSCRIPTION_TIERS.get(tier, Config.SUBSCRIPTION_TIERS['free'])
    monthly_limit = plan_info['monthly_interviews']
    interviews_remaining = (
        max(0, monthly_limit - interviews_used)
        if monthly_limit != float('inf')
        else 'unlimited'
    )
    monthly_limit_response = monthly_limit if monthly_limit != float('inf') else 'unlimited'

    return {
        'tier': tier,
        'status': status,
        'interviews_used_this_month': interviews_used,
        'interviews_remaining': interviews_remaining,
        'monthly_limit': monthly_limit_response,
        'features': plan_info['features'],
        'subscription_start_date': start_date,
        'subscription_end_date': end_date,
    }


def _store_fallback_subscription(user_id, tier, razorpay_order_id=None,
                                 razorpay_payment_id=None):
    """Activate a paid plan in memory when MongoDB is unavailable locally."""
    start_date = datetime.utcnow()
    fallback_subscriptions[str(user_id)] = {
        'tier': tier,
        'status': 'active',
        'interviews_used_this_month': 0,
        'subscription_start_date': start_date,
        'subscription_end_date': start_date + timedelta(days=30),
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
    }


@subscription_bp.route('/plans', methods=['GET'])
def get_plans():
    """Get all available subscription plans"""
    return jsonify({
        'plans': Config.SUBSCRIPTION_TIERS
    }), 200


@subscription_bp.route('/status', methods=['GET'])
@token_required
def get_subscription_status():
    """Get current user's subscription status"""
    current_user = _get_current_user()
    user_id = current_user['_id']

    # Handle guest users (no account) - return free tier by default
    if user_id == 'guest':
        return jsonify(_subscription_status_payload('free')), 200

    fallback_subscription = fallback_subscriptions.get(str(user_id))
    if fallback_subscription:
        end_date = fallback_subscription.get('subscription_end_date')
        if end_date and datetime.utcnow() > end_date:
            fallback_subscriptions.pop(str(user_id), None)
        else:
            return jsonify(_subscription_status_payload(
                fallback_subscription.get('tier', 'free'),
                fallback_subscription.get('status', 'active'),
                fallback_subscription.get('interviews_used_this_month', 0),
                fallback_subscription.get('subscription_start_date'),
                fallback_subscription.get('subscription_end_date'),
            )), 200

    # Handle demo users (stored in memory, not MongoDB)
    if str(user_id).startswith('demo_'):
        return jsonify(_subscription_status_payload('free')), 200

    try:
        user_data = mongo.db.users.find_one({'_id': user_id})
    except Exception:
        user_data = None

    if not user_data:
        return jsonify(_subscription_status_payload('free')), 200

    tier = user_data.get('subscription_tier', 'free')
    plan_info = Config.SUBSCRIPTION_TIERS.get(tier, Config.SUBSCRIPTION_TIERS['free'])

    # Calculate interviews remaining
    interviews_used = user_data.get('interviews_used_this_month', 0)
    monthly_limit = plan_info['monthly_interviews']
    interviews_remaining = max(0, monthly_limit - interviews_used) if monthly_limit != float('inf') else float('inf')

    # Check if subscription needs reset (new month)
    subscription_end = user_data.get('subscription_end_date')
    if subscription_end and datetime.utcnow() > subscription_end:
        # Reset monthly usage
        mongo.db.users.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'interviews_used_this_month': 0,
                    'subscription_start_date': datetime.utcnow(),
                    'subscription_end_date': datetime.utcnow() + timedelta(days=30)
                }
            }
        )
        interviews_used = 0
        interviews_remaining = monthly_limit

    return jsonify({
        'tier': tier,
        'status': user_data.get('subscription_status', 'active'),
        'interviews_used_this_month': interviews_used,
        'interviews_remaining': interviews_remaining,
        'monthly_limit': monthly_limit if monthly_limit != float('inf') else 'unlimited',
        'features': plan_info['features'],
        'subscription_start_date': user_data.get('subscription_start_date'),
        'subscription_end_date': user_data.get('subscription_end_date'),
    }), 200


@subscription_bp.route('/create-order', methods=['POST'])
@token_required
def create_razorpay_order():
    """Create a Razorpay order for a subscription tier.

    The selected tier is mapped to a fixed amount (in paise) on the server so
    the order value can never be tampered with by the client. Returns the
    order id, amount and currency needed to launch the Razorpay checkout
    modal.
    """
    current_user = _get_current_user()
    data = request.get_json(silent=True) or {}
    tier = (data.get('tier') or '').lower()

    if not _is_real_user(current_user):
        return jsonify({'error': 'Please sign in with an account before making a payment'}), 401

    if tier not in ['basic', 'pro']:
        return jsonify({'error': 'Invalid subscription tier'}), 400

    amount = _order_amount_for_tier(tier)
    if not amount or amount < 100:
        return jsonify({'error': 'Order amount must be at least 100 paise'}), 400

    if not Config.RAZORPAY_KEY_ID or not Config.RAZORPAY_KEY_SECRET:
        return jsonify({
            'error': 'Razorpay is not configured yet. Add Razorpay key id and secret to enable payments.'
        }), 501

    receipt = 'sub_{}_{}_{}'.format(
        tier[:1],
        hashlib.sha1(str(current_user['_id']).encode('utf-8')).hexdigest()[:8],
        int(datetime.utcnow().timestamp())
    )

    try:
        order = razorpay_client.order.create(data={
            'amount': amount,
            'currency': Config.RAZORPAY_CURRENCY,
            'receipt': receipt,
            'payment_capture': 1,
            'notes': {
                'subscription_tier': tier,
                'user_id': str(current_user['_id']),
                'email': current_user.get('email', ''),
            },
        })
    except (BadRequestError, GatewayError, ServerError) as exc:
        return _razorpay_order_error_response(exc)
    except Exception:
        current_app.logger.exception('Unexpected Razorpay order creation failure')
        return jsonify({
            'error': 'Unable to contact Razorpay. Please try again in a moment.'
        }), 502

    # Persist the order -> tier mapping so the correct plan is activated after
    # signature verification, without trusting any client-supplied value.
    order_record = {
        'order_id': order['id'],
        'user_id': str(current_user['_id']),
        'email': current_user.get('email', ''),
        'tier': tier,
        'amount': order['amount'],
        'currency': order['currency'],
        'status': 'created',
        'created_at': datetime.utcnow(),
    }
    fallback_razorpay_orders[order['id']] = order_record.copy()

    try:
        mongo.db.razorpay_orders.insert_one(order_record)
    except Exception:
        # Local/demo mode can still verify the payment against the in-memory
        # order above. A production deployment should keep MongoDB available.
        pass

    return jsonify({
        'order_id': order['id'],
        'amount': order['amount'],
        'currency': order['currency'],
        'key_id': Config.RAZORPAY_KEY_ID,
    }), 200


@subscription_bp.route('/verify-payment', methods=['POST'])
@token_required
def verify_razorpay_payment():
    """Verify the Razorpay payment signature and activate the subscription.

    Signature algorithm (per Razorpay docs):
        HMAC-SHA256(<razorpay_order_id>|<razorpay_payment_id>, KEY_SECRET)
    The generated digest must equal the ``razorpay_signature`` returned by
    Razorpay. On mismatch the payment is rejected and the subscription is **not**
    marked as paid.
    """
    current_user = _get_current_user()
    data = request.get_json(silent=True) or {}
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return jsonify({'error': 'Missing required payment fields'}), 400

    if not _is_real_user(current_user):
        return jsonify({'error': 'Please sign in with an account before making a payment'}), 401

    if not Config.RAZORPAY_KEY_SECRET:
        return jsonify({'error': 'Razorpay is not configured'}), 500

    try:
        order_record = mongo.db.razorpay_orders.find_one({'order_id': razorpay_order_id})
    except Exception:
        order_record = None

    if not order_record:
        order_record = fallback_razorpay_orders.get(razorpay_order_id)

    if not order_record or str(order_record.get('user_id')) != str(current_user.get('_id')):
        return jsonify({'error': 'Payment order was not found for this user'}), 400

    if order_record.get('status') == 'paid':
        return jsonify({'error': 'Payment has already been processed'}), 400

    server_order_id = order_record.get('order_id')
    tier = order_record.get('tier')

    if tier not in ['basic', 'pro'] or not server_order_id:
        return jsonify({'error': 'Payment order has an invalid plan'}), 400

    # --- Signature verification (HMAC-SHA256) ---
    msg = '{}|{}'.format(server_order_id, razorpay_payment_id)
    expected_signature = hmac.new(
        Config.RAZORPAY_KEY_SECRET.encode('utf-8'),
        msg.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, razorpay_signature):
        # Signature mismatch: do NOT mark the subscription as paid.
        return jsonify({'error': 'Signature verification failed'}), 400

    # --- Activate subscription ---
    if tier in ['basic', 'pro']:
        activated_in_mongo = False
        try:
            result = mongo.db.users.update_one(
                {'_id': current_user['_id']},
                {
                    '$set': {
                        'subscription_tier': tier,
                        'subscription_status': 'active',
                        'subscription_start_date': datetime.utcnow(),
                        'subscription_end_date': datetime.utcnow() + timedelta(days=30),
                        'razorpay_order_id': razorpay_order_id,
                        'razorpay_payment_id': razorpay_payment_id,
                        'interviews_used_this_month': 0,
                    }
                }
            )
            activated_in_mongo = result.matched_count > 0
        except Exception:
            activated_in_mongo = False

        if activated_in_mongo:
            try:
                mongo.db.razorpay_orders.update_one(
                    {'order_id': razorpay_order_id},
                    {'$set': {'status': 'paid', 'payment_id': razorpay_payment_id}}
                )
            except Exception:
                pass
        else:
            _store_fallback_subscription(
                current_user['_id'], tier, razorpay_order_id, razorpay_payment_id
            )

        if razorpay_order_id in fallback_razorpay_orders:
            fallback_razorpay_orders[razorpay_order_id]['status'] = 'paid'
            fallback_razorpay_orders[razorpay_order_id]['payment_id'] = razorpay_payment_id

    return jsonify({
        'status': 'success',
        'message': 'Payment verified successfully',
        'tier': tier,
    }), 200


@subscription_bp.route('/cancel', methods=['POST'])
@token_required
def cancel_subscription():
    """Cancel the user's subscription (downgrade to the free tier).

    Razorpay Standard Checkout creates one-time payments, so there is no
    recurring subscription object to cancel at the gateway. We downgrade the
    user locally instead.
    """
    current_user = _get_current_user()

    if not _is_real_user(current_user):
        return jsonify({'error': 'No active subscription found'}), 404

    try:
        result = mongo.db.users.update_one(
            {'_id': current_user['_id']},
            {
                '$set': {
                    'subscription_tier': 'free',
                    'subscription_status': 'canceled',
                    'subscription_end_date': datetime.utcnow(),
                    'razorpay_order_id': None,
                }
            }
        )
        if result.matched_count == 0:
            return jsonify({'error': 'No active subscription found'}), 404
        return jsonify({
            'message': 'Subscription canceled. You are now on the free plan.'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
