from datetime import datetime, timedelta
import hmac
import hashlib

import razorpay
from flask import Blueprint, current_app, jsonify, request
from razorpay.errors import BadRequestError, GatewayError, ServerError

from app import mongo
from app.config import Config
from app.services.subscription_service import SubscriptionService
from app.utils.auth import token_required

subscription_bp = Blueprint('subscription', __name__)
subscription_service = SubscriptionService()

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
            'error': 'Razorpay authentication failed. Please check your RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in backend/.env.'
        }), 400
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

    # Use the subscription service for consistent handling
    subscription = subscription_service.get_user_subscription(user_id)
    return jsonify(subscription), 200


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

    is_demo_mode = data.get('demo_mode') is True

    if not is_demo_mode:
        if not Config.RAZORPAY_KEY_ID or not Config.RAZORPAY_KEY_SECRET:
            return jsonify({
                'error': 'Razorpay is not configured yet. Add Razorpay key id and secret to enable payments, or use Demo mode.'
            }), 400

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
                'error': 'Unable to contact Razorpay. Please try again in a moment or use Demo mode.'
            }), 502
    else:
        # Create a simulated demo order for local testing
        demo_id = 'order_demo_{}_{}'.format(tier, int(datetime.utcnow().timestamp()))
        order = {
            'id': demo_id,
            'amount': amount,
            'currency': Config.RAZORPAY_CURRENCY,
            'is_demo': True,
        }

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
        'is_demo': order.get('is_demo', False),
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
        'key_id': Config.RAZORPAY_KEY_ID or 'rzp_demo_key',
        'is_demo': order.get('is_demo', False),
    }), 200


@subscription_bp.route('/verify-payment', methods=['POST'])
@token_required
def verify_razorpay_payment():
    """Verify the Razorpay payment signature and activate the subscription."""
    current_user = _get_current_user()
    data = request.get_json(silent=True) or {}
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id') or 'pay_demo_123'
    razorpay_signature = data.get('razorpay_signature') or 'demo_signature'

    if not razorpay_order_id:
        return jsonify({'error': 'Missing required payment order ID'}), 400

    if not _is_real_user(current_user):
        return jsonify({'error': 'Please sign in with an account before making a payment'}), 401

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

    # --- Signature verification (HMAC-SHA256 or Demo mode) ---
    is_demo_order = order_record.get('is_demo') or server_order_id.startswith('order_demo_')
    if not is_demo_order:
        if not Config.RAZORPAY_KEY_SECRET:
            return jsonify({'error': 'Razorpay is not configured'}), 500

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
        subscription_service.cancel_subscription(current_user['_id'])
        return jsonify({
            'message': 'Subscription canceled. You are now on the free plan.'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========================
# Enhanced Subscription Routes
# ========================

@subscription_bp.route('/usage-stats', methods=['GET'])
@token_required
def get_usage_stats():
    """Get detailed usage statistics for the current user"""
    current_user = _get_current_user()
    user_id = current_user['_id']

    try:
        stats = subscription_service.get_usage_stats(user_id)
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/billing-history', methods=['GET'])
@token_required
def get_billing_history():
    """Get billing history for the current user"""
    current_user = _get_current_user()
    user_id = current_user['_id']

    try:
        limit = request.args.get('limit', 50, type=int)
        history = subscription_service.get_billing_history(user_id, limit=limit)
        return jsonify({'billing_history': history}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/upgrade', methods=['POST'])
@token_required
def upgrade_subscription():
    """Upgrade to a higher tier subscription"""
    current_user = _get_current_user()
    user_id = current_user['_id']
    data = request.get_json(silent=True) or {}
    new_tier = (data.get('tier') or '').lower()

    if not _is_real_user(current_user):
        return jsonify({'error': 'Please sign in before upgrading'}), 401

    if new_tier not in ['basic', 'pro']:
        return jsonify({'error': 'Invalid subscription tier'}), 400

    try:
        subscription = subscription_service.upgrade_subscription(
            user_id,
            new_tier,
            razorpay_order_id=data.get('razorpay_order_id'),
            razorpay_payment_id=data.get('razorpay_payment_id')
        )
        return jsonify({
            'message': f'Successfully upgraded to {new_tier} plan',
            'subscription': subscription
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/trial/start', methods=['POST'])
@token_required
def start_trial():
    """Start a free trial for a user"""
    current_user = _get_current_user()
    user_id = current_user['_id']
    data = request.get_json(silent=True) or {}
    tier = (data.get('tier') or 'pro').lower()
    trial_days = data.get('trial_days', 7)

    if not _is_real_user(current_user):
        return jsonify({'error': 'Please sign in to start a trial'}), 401

    if tier not in ['basic', 'pro']:
        return jsonify({'error': 'Invalid subscription tier for trial'}), 400

    try:
        # Check if user already has an active subscription
        current_sub = subscription_service.get_user_subscription(user_id)
        if current_sub['tier'] != 'free':
            return jsonify({
                'error': f'You already have an active {current_sub["tier"]} subscription'
            }), 400

        subscription = subscription_service.start_trial(user_id, tier, trial_days)
        return jsonify({
            'message': f'Trial for {tier} plan started',
            'subscription': subscription
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/features', methods=['GET'])
@token_required
def get_available_features():
    """Get list of features available to current user"""
    current_user = _get_current_user()
    user_id = current_user['_id']

    try:
        features = subscription_service.get_available_features(user_id)
        return jsonify({'features': features}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/has-feature/<feature_name>', methods=['GET'])
@token_required
def check_feature_access(feature_name):
    """Check if user has access to a specific feature"""
    current_user = _get_current_user()
    user_id = current_user['_id']

    try:
        has_access = subscription_service.has_feature(user_id, feature_name)
        return jsonify({
            'feature': feature_name,
            'has_access': has_access
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

