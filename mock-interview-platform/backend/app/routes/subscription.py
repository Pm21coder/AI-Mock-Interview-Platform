from datetime import datetime, timedelta
import hmac
import hashlib

import razorpay
from flask import Blueprint, jsonify, request
from razorpay.errors import BadRequestError

from app import mongo
from app.config import Config
from app.utils.auth import token_required

subscription_bp = Blueprint('subscription', __name__)

# Initialize the Razorpay client. Credentials come from environment variables
# (Config.RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET) so that secrets are never
# hard-coded in source files.
razorpay_client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))


def _get_current_user():
    """Return the current user dict set by the token_required decorator."""
    return request.current_user


def _is_real_user(user):
    """True when the user is backed by MongoDB (not a guest/demo account)."""
    if not user:
        return False
    user_id = str(user.get('_id', ''))
    return user_id != 'guest' and not user_id.startswith('demo_')


def _order_amount_for_tier(tier):
    """Return the order amount (in paise) for the given tier, or None."""
    return Config.RAZORPAY_ORDER_AMOUNTS.get(tier)


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
        plan_info = Config.SUBSCRIPTION_TIERS['free']
        return jsonify({
            'tier': 'free',
            'status': 'active',
            'interviews_used_this_month': 0,
            'interviews_remaining': plan_info['monthly_interviews'],
            'monthly_limit': plan_info['monthly_interviews'],
            'features': plan_info['features'],
            'subscription_start_date': None,
            'subscription_end_date': None,
        }), 200

    # Handle demo users (stored in memory, not MongoDB)
    if str(user_id).startswith('demo_'):
        plan_info = Config.SUBSCRIPTION_TIERS['free']
        return jsonify({
            'tier': 'free',
            'status': 'active',
            'interviews_used_this_month': 0,
            'interviews_remaining': plan_info['monthly_interviews'],
            'monthly_limit': plan_info['monthly_interviews'],
            'features': plan_info['features'],
            'subscription_start_date': None,
            'subscription_end_date': None,
        }), 200

    try:
        user_data = mongo.db.users.find_one({'_id': user_id})
    except Exception:
        user_data = None

    if not user_data:
        plan_info = Config.SUBSCRIPTION_TIERS['free']
        return jsonify({
            'tier': 'free',
            'status': 'active',
            'interviews_used_this_month': 0,
            'interviews_remaining': plan_info['monthly_interviews'],
            'monthly_limit': plan_info['monthly_interviews'],
            'features': plan_info['features'],
            'subscription_start_date': None,
            'subscription_end_date': None,
        }), 200

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

    # Fall back to UPI when Razorpay is not configured yet (matches the
    # behaviour previously offered while Stripe was unconfigured).
    if not Config.RAZORPAY_KEY_ID or not Config.RAZORPAY_KEY_SECRET:
        return jsonify({
            'error': 'Razorpay is not configured yet. Please use UPI payment or contact support.',
            'upi_available': True,
            'tier': tier,
            'upi_info': {
                'upi_id': Config.UPI_ID,
                'upi_name': Config.UPI_NAME,
                'amount': Config.UPI_AMOUNTS.get(tier, ''),
                'price': Config.SUBSCRIPTION_TIERS[tier]['price']
            }
        }), 501

    try:
        order = razorpay_client.order.create({
            'amount': amount,
            'currency': Config.RAZORPAY_CURRENCY,
            'receipt': 'sub_{}_{}_{}'.format(
                tier, str(current_user['_id']), int(datetime.utcnow().timestamp())
            ),
            'payment_capture': 1,
        })
    except BadRequestError as exc:
        error_message = str(exc)
        if any(term in error_message.lower() for term in ('auth', 'credential', 'key')):
            return jsonify({'error': 'Razorpay authentication failed'}), 401
        return jsonify({'error': 'Razorpay could not create the order'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Persist the order -> tier mapping so the correct plan is activated after
    # signature verification, without trusting any client-supplied value.
    try:
        mongo.db.razorpay_orders.insert_one({
            'order_id': order['id'],
            'user_id': str(current_user['_id']),
            'email': current_user.get('email', ''),
            'tier': tier,
            'amount': order['amount'],
            'currency': order['currency'],
            'status': 'created',
            'created_at': datetime.utcnow(),
        })
    except Exception:
        # Do not expose an order that cannot be associated with the user and
        # plan during verification.
        return jsonify({'error': 'Unable to prepare the payment order'}), 500

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

    if not Config.RAZORPAY_KEY_SECRET:
        return jsonify({'error': 'Razorpay is not configured'}), 500

    # --- Signature verification (HMAC-SHA256) ---
    msg = '{}|{}'.format(razorpay_order_id, razorpay_payment_id)
    expected_signature = hmac.new(
        Config.RAZORPAY_KEY_SECRET.encode('utf-8'),
        msg.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, razorpay_signature):
        # Signature mismatch: do NOT mark the subscription as paid.
        return jsonify({'error': 'Signature verification failed'}), 400

    # --- Activate subscription (only for real MongoDB-backed users) ---
    try:
        order_record = mongo.db.razorpay_orders.find_one({'order_id': razorpay_order_id})
    except Exception:
        order_record = None

    if not order_record or str(order_record.get('user_id')) != str(current_user.get('_id')):
        return jsonify({'error': 'Payment order was not found for this user'}), 400

    if order_record.get('status') == 'paid':
        return jsonify({'error': 'Payment has already been processed'}), 400

    tier = order_record.get('tier')

    if _is_real_user(current_user) and tier in ['basic', 'pro']:
        try:
            mongo.db.users.update_one(
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
            mongo.db.razorpay_orders.update_one(
                {'order_id': razorpay_order_id},
                {'$set': {'status': 'paid', 'payment_id': razorpay_payment_id}}
            )
        except Exception:
            return jsonify({
                'error': 'Payment verified but subscription could not be activated'
            }), 500

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


@subscription_bp.route('/upi-info', methods=['GET'])
def get_upi_info():
    """Get UPI payment information for manual transfer"""
    return jsonify({
        'upi_id': Config.UPI_ID,
        'upi_name': Config.UPI_NAME,
        'plans': {
            'basic': {
                'name': 'Basic Plan',
                'price': Config.SUBSCRIPTION_TIERS['basic']['price'],
                'currency': 'USD',
                'upi_amount': Config.UPI_AMOUNTS['basic']
            },
            'pro': {
                'name': 'Pro Plan',
                'price': Config.SUBSCRIPTION_TIERS['pro']['price'],
                'currency': 'USD',
                'upi_amount': Config.UPI_AMOUNTS['pro']
            }
        }
    }), 200


@subscription_bp.route('/upi-payment', methods=['POST'])
@token_required
def create_upi_payment():
    """Create a UPI payment request and return payment details"""
    current_user = _get_current_user()
    data = request.get_json(silent=True) or {}
    tier = data.get('tier', '').lower()
    transaction_id = data.get('transaction_id', '')

    if tier not in ['basic', 'pro']:
        return jsonify({'error': 'Invalid subscription tier'}), 400

    if not transaction_id:
        return jsonify({'error': 'Transaction ID is required'}), 400

    # Get user info
    user_data = mongo.db.users.find_one({'_id': current_user['_id']})
    if not user_data:
        return jsonify({'error': 'User not found'}), 404

    # Store pending subscription with transaction ID
    # In production, you would verify the transaction with your bank/Payment gateway
    # For now, we'll store it and mark as pending verification
    try:
        payment_record = {
            'user_id': str(current_user['_id']),
            'email': user_data['email'],
            'tier': tier,
            'transaction_id': transaction_id,
            'amount': Config.SUBSCRIPTION_TIERS[tier]['price'],
            'status': 'pending_verification',
            'created_at': datetime.utcnow(),
        }

        # Store in a pending_payments collection
        mongo.db.pending_payments.insert_one(payment_record)

        return jsonify({
            'message': 'Payment request submitted successfully',
            'status': 'pending_verification',
            'transaction_id': transaction_id,
            'upi_id': Config.UPI_ID,
            'tier': tier,
            'note': 'Your subscription will be activated within 24 hours after payment verification'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
