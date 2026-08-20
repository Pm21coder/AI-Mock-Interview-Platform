from datetime import datetime, timedelta
import hmac
import hashlib

import razorpay
from flask import Blueprint, current_app, jsonify, request
from razorpay.errors import BadRequestError, GatewayError, ServerError

from app import mongo, limiter
from app.config import Config
from app.services.subscription_service import SubscriptionService, fallback_subscriptions
from app.services.audit_logger import get_audit_logger
from app.utils.auth import token_required
from app.utils.mongo_state import is_mongo_available, mark_mongo_unavailable
from app.utils.time import utc_now
from app.cache_utils import cache_response, optimize_response
from flask_limiter.util import get_remote_address
from flask import request

# Use per-user key when available to avoid IP-based 429s for authenticated users
def _user_or_ip_key():
    try:
        user = getattr(request, 'current_user', None)
        if user and user.get('_id'):
            return str(user.get('_id'))
    except Exception:
        pass
    return get_remote_address()

subscription_bp = Blueprint('subscription', __name__)
subscription_service = SubscriptionService()
audit_logger = get_audit_logger()

fallback_razorpay_orders = {}

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
    start_date = utc_now()
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
@limiter.exempt
@limiter.limit("60 per minute", key_func=_user_or_ip_key)
@token_required
def get_subscription_status():
    """Get current user's subscription status"""
    current_user = _get_current_user()
    user_id = current_user['_id']

    # Use the subscription service for consistent handling
    subscription = subscription_service.get_user_subscription(user_id)
    response = jsonify(subscription)
    # Quota changes when an interview starts, so this user-specific response
    # must never be reused by a browser or intermediary cache.
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response, 200


@subscription_bp.route('/create-order', methods=['POST'])
@token_required
@limiter.limit("10 per minute")  # Protect payment endpoints from abuse
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

    # Optional coupon application
    coupon_code = (data.get('coupon_code') or '').strip() or None
    discount_percent = None
    if coupon_code:
        # Validate and reserve (redeem) the coupon so it cannot be double-used
        discount_percent = subscription_service.validate_and_redeem_coupon(coupon_code)
        if discount_percent is None:
            return jsonify({'error': 'Invalid or expired coupon code'}), 400
        # Also fetch full coupon metadata (works for Mongo or fallback file) and
        # persist it with the order so verification need not re-query external
        # stores during the webhook/verify step.
        try:
            coupon_meta = subscription_service.get_coupon_info(coupon_code)
        except Exception:
            coupon_meta = None
        # Compute discounted amount (paise)
        try:
            discounted_amount = int(round(amount * (100 - discount_percent) / 100.0))
            # Razorpay requires at least 100 paise
            if discounted_amount < 100:
                discounted_amount = 100
            amount = discounted_amount
        except Exception:
            return jsonify({'error': 'Failed to apply coupon'}), 500
    else:
        coupon_meta = None

    # Demo/test-mode has been removed. Require real Razorpay credentials
    # to create an order. If Razorpay is not configured, return an explicit
    # error so administrators can correct the deployment configuration.
    if not Config.RAZORPAY_KEY_ID or not Config.RAZORPAY_KEY_SECRET:
        return jsonify({
            'error': 'Razorpay is not configured on the server. Please contact the site administrator.'
        }), 500

    receipt = 'sub_{}_{}_{}'.format(
        tier[:1],
        hashlib.sha1(str(current_user['_id']).encode('utf-8')).hexdigest()[:8],
        int(utc_now().timestamp())
    )

    try:
        notes = {
            'subscription_tier': tier,
            'user_id': str(current_user['_id']),
            'email': current_user.get('email', ''),
        }
        if coupon_code:
            notes['coupon_code'] = coupon_code
            notes['discount_percent'] = discount_percent

        order = razorpay_client.order.create(data={
            'amount': amount,
            'currency': Config.RAZORPAY_CURRENCY,
            'receipt': receipt,
            'payment_capture': 1,
            'notes': notes,
        }, timeout=Config.RAZORPAY_TIMEOUT_SECONDS)
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
        'is_demo': False,
        'created_at': utc_now(),
        'coupon_code': coupon_code,
        'discount_percent': discount_percent,
        'coupon_meta': coupon_meta,
    }
    # Keep an in-memory map for short-lived verification flows when MongoDB is
    # temporarily unavailable. This is not a test/demo fallback for production.
    fallback_razorpay_orders[order['id']] = order_record.copy()

    if is_mongo_available():
        try:
            mongo.db.razorpay_orders.insert_one(order_record)
        except Exception as exc:
            # If MongoDB insertion fails, persist the order in memory so the
            # verification step can still proceed in the current process.
            mark_mongo_unavailable(exc)
    
    # Log payment initiation
    audit_logger.log_payment_initiated(
        current_user['_id'], tier, order['amount'], order['currency'], order['id']
    )

    return jsonify({
        'order_id': order['id'],
        'amount': order['amount'],
        'currency': order['currency'],
        'key_id': Config.RAZORPAY_KEY_ID,
    }), 200


@subscription_bp.route('/verify-payment', methods=['POST'])
@token_required
def verify_razorpay_payment():
    """Verify the Razorpay payment signature and activate the subscription."""
    current_user = _get_current_user()
    data = request.get_json(silent=True) or {}
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')

    if not razorpay_order_id:
        return jsonify({'error': 'Missing required payment order ID'}), 400
    if not razorpay_payment_id or not razorpay_signature:
        return jsonify({'error': 'Missing payment verification parameters'}), 400

    if not _is_real_user(current_user):
        return jsonify({'error': 'Please sign in with an account before making a payment'}), 401

    order_record = None
    if is_mongo_available():
        try:
            order_record = mongo.db.razorpay_orders.find_one({'order_id': razorpay_order_id})
        except Exception as exc:
            mark_mongo_unavailable(exc)

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
    if not Config.RAZORPAY_KEY_SECRET:
        return jsonify({'error': 'Razorpay is not configured on the server'}), 500

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
        # Prefer coupon metadata attached to the order to avoid re-reading
        # external stores during verification. Fall back to DB/file lookups only
        # if order doesn't include it.
        coupon_doc = None
        coupon_code = order_record.get('coupon_code')
        # If the order_record already persisted coupon metadata (from create-order), use it
        if order_record.get('coupon_meta'):
            coupon_doc = order_record.get('coupon_meta')
        elif coupon_code:
            # Prefer Mongo if available
            if is_mongo_available():
                try:
                    coupon_doc = mongo.db.coupons.find_one({'code': coupon_code})
                except Exception:
                    coupon_doc = None
            # If not found in Mongo, consult the subscription service which
            # will read fallback master coupons from disk when applicable.
            if not coupon_doc:
                try:
                    coupon_doc = subscription_service.get_coupon_info(coupon_code)
                except Exception:
                    coupon_doc = None

        activated_in_mongo = False
        if is_mongo_available():
            try:
                # Build update document and honor grant_unlimited coupons
                set_fields = {
                    'subscription_tier': tier,
                    'subscription_status': 'active',
                    'subscription_start_date': utc_now(),
                    'subscription_end_date': utc_now() + timedelta(days=30),
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'interviews_used_this_month': 0,
                }

                if coupon_doc and coupon_doc.get('grant_unlimited'):
                    # Ensure the coupon is intended for this tier (or for all tiers when grant_tier is not set)
                    grant_tier = coupon_doc.get('grant_tier')
                    if not grant_tier or grant_tier == tier:
                        set_fields['subscription_end_date'] = None
                        # Use None to indicate unlimited monthly limit in user document
                        set_fields['subscription_monthly_limit'] = None

                result = mongo.db.users.update_one(
                    {'_id': current_user['_id']},
                    {'$set': set_fields}
                )
                activated_in_mongo = result.matched_count > 0
            except Exception as exc:
                mark_mongo_unavailable(exc)

        if activated_in_mongo:
            try:
                mongo.db.razorpay_orders.update_one(
                    {'order_id': razorpay_order_id},
                    {'$set': {'status': 'paid', 'payment_id': razorpay_payment_id}}
                )
            except Exception:
                pass
            
            # Log successful payment
            amount = order_record.get('amount', 0)
            audit_logger.log_payment_completed(
                current_user['_id'], tier, amount, razorpay_order_id, 
                razorpay_payment_id, 'success'
            )
        else:
            # Fallback subscription when MongoDB is unavailable
            _store_fallback_subscription(
                current_user['_id'], tier, razorpay_order_id, razorpay_payment_id
            )

            # If coupon grants unlimited, apply to fallback in-memory subscription as well
            if coupon_doc and coupon_doc.get('grant_unlimited'):
                fb = fallback_razorpay_orders.get(razorpay_order_id) or {}
                # fallback_subscriptions stores per-user fallback; set there if present
                user_key = str(current_user['_id'])
                if user_key in fallback_subscriptions:
                    fallback_subscriptions[user_key]['subscription_end_date'] = None
                    fallback_subscriptions[user_key]['subscription_monthly_limit'] = None

            # Log successful payment in fallback mode
            amount = order_record.get('amount', 0)
            audit_logger.log_payment_completed(
                current_user['_id'], tier, amount, razorpay_order_id,
                razorpay_payment_id, 'success'
            )

        if razorpay_order_id in fallback_razorpay_orders:
            fallback_razorpay_orders[razorpay_order_id]['status'] = 'paid'
            fallback_razorpay_orders[razorpay_order_id]['payment_id'] = razorpay_payment_id

    return jsonify({
        'status': 'success',
        'message': 'Payment verified successfully',
        'tier': tier,
    }), 200


@subscription_bp.route('/validate-coupon', methods=['POST'])
@token_required
def validate_coupon():
    """Validate a coupon code without redeeming it. Returns discount info
    and metadata so the frontend can preview discounted prices.

    Adds extra debug logging to help diagnose 'Resource not found' frontend
    errors and network failures by recording the incoming request and the
    coupon code being validated.
    """
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}

    coupon_code = (data.get('coupon_code') or '')
    coupon_code = coupon_code.strip() if isinstance(coupon_code, str) else None

    current_app.logger.info('validate-coupon called from %s with coupon_code=%s', request.remote_addr, bool(coupon_code))

    if not coupon_code:
        current_app.logger.warning('validate-coupon missing coupon_code payload. Full body: %s', data)
        return jsonify({'error': 'Missing coupon_code'}), 400

    try:
        info = subscription_service.get_coupon_info(coupon_code)
        if not info:
            current_app.logger.info('validate-coupon: code not found or expired: %s', coupon_code)
            # Detailed debug record for missing coupon
            try:
                import json as _json
                debug = {
                    'ts': utc_now().isoformat(),
                    'remote_addr': request.remote_addr,
                    'method': request.method,
                    'path': request.path,
                    'headers': {k: ('[REDACTED]' if k.lower() == 'authorization' else v) for k, v in request.headers.items()},
                    'body': data,
                    'coupon_code': coupon_code,
                    'result': 'not_found'
                }
                log_path = _json.dumps(debug) + "\n"
                # Append to debug log in repository's temp folder
                try:
                    from pathlib import Path as _Path
                    base = _Path(__file__).resolve().parents[2]
                    log_dir = base / 'logs'
                    log_dir.mkdir(parents=True, exist_ok=True)
                    log_file_path = log_dir / 'coupon_validation_debug.log'
                    with open(str(log_file_path), 'a', encoding='utf-8') as lf:
                        lf.write(log_path)
                except Exception:
                    # If writing file fails, still proceed — the main logger captured an event
                    pass
            except Exception:
                pass
            return jsonify({'error': 'Invalid or expired coupon code'}), 400

        current_app.logger.info('validate-coupon: found coupon %s (grant_unlimited=%s, grant_tier=%s)', info.get('code'), info.get('grant_unlimited'), info.get('grant_tier'))
        # Also append a success debug record to the debug log
        try:
            import json as _json
            debug = {
                'ts': utc_now().isoformat(),
                'remote_addr': request.remote_addr,
                'method': request.method,
                'path': request.path,
                'headers': {k: ('[REDACTED]' if k.lower() == 'authorization' else v) for k, v in request.headers.items()},
                'body': data,
                'coupon_code': coupon_code,
                'result': 'found',
                'coupon_meta': {
                    'grant_unlimited': info.get('grant_unlimited'),
                    'grant_tier': info.get('grant_tier'),
                    'code': info.get('code')
                }
            }
            try:
                from pathlib import Path as _Path
                base = _Path(__file__).resolve().parents[2]
                log_dir = base / 'logs'
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file_path = log_dir / 'coupon_validation_debug.log'
                with open(str(log_file_path), 'a', encoding='utf-8') as lf:
                    lf.write(_json.dumps(debug) + "\n")
            except Exception:
                pass
        except Exception:
            pass
        return jsonify({'coupon': info}), 200
    except Exception as e:
        current_app.logger.exception('Error validating coupon %s: %s', coupon_code, e)
        try:
            import json as _json
            debug = {
                'ts': utc_now().isoformat(),
                'remote_addr': request.remote_addr,
                'method': request.method,
                'path': request.path,
                'headers': {k: ('[REDACTED]' if k.lower() == 'authorization' else v) for k, v in request.headers.items()},
                'body': data,
                'coupon_code': coupon_code,
                'result': 'exception',
                'error': str(e)
            }
            try:
                from pathlib import Path as _Path
                base = _Path(__file__).resolve().parents[2]
                log_dir = base / 'logs'
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file_path = log_dir / 'coupon_validation_debug.log'
                with open(str(log_file_path), 'a', encoding='utf-8') as lf:
                    lf.write(_json.dumps(debug) + "\n")
            except Exception:
                pass
        except Exception:
            pass
        return jsonify({'error': 'Internal server error during coupon validation'}), 500

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
            razorpay_payment_id=data.get('razorpay_payment_id'),
            coupon_code=(data.get('coupon_code') or '').strip() or None,
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


@subscription_bp.route('/question-categories', methods=['GET'])
@token_required
def get_question_categories():
    """Get available question categories for the user's subscription tier"""
    try:
        current_user = _get_current_user()
        if not current_user:
            raise ValueError('Authenticated user is missing')

        user_id = current_user.get('_id')
        if not user_id:
            raise ValueError('Authenticated user ID is missing')

        # Fetch subscription only once. The previous implementation made two
        # sequential Mongo reads, doubling the failure latency.
        sub = subscription_service.get_user_subscription(user_id)
        categories = subscription_service.get_available_question_categories(
            user_id, subscription=sub,
        )
        response = {
            'available_categories': categories or ['technical', 'behavioral'],
            'tier': sub.get('tier', 'free'),
            'interviews_remaining': sub.get('interviews_remaining', 0),
            'monthly_limit': sub.get('monthly_limit', 3),
            'all_categories_available': (categories or []) == ['technical', 'behavioral', 'situational', 'system_design']
        }
        return jsonify(optimize_response(response)), 200

    except Exception:
        current_app.logger.exception('Unable to load question categories')
        return jsonify({
            'available_categories': ['technical', 'behavioral'],
            'tier': 'free',
            'interviews_remaining': 0,
            'monthly_limit': 3,
            'all_categories_available': False,
            'fallback': True
        }), 200


@subscription_bp.route('/analytics', methods=['GET'])
@token_required
def get_advanced_analytics():
    """Get advanced analytics dashboard for Pro tier users"""
    current_user = _get_current_user()
    user_id = current_user['_id']

    try:
        # Check if user has advanced analytics access
        if not subscription_service.has_advanced_analytics(user_id):
            return jsonify({
                'error': 'Advanced analytics is only available to Pro tier subscribers',
                'required_tier': 'pro'
            }), 403

        # Get usage stats
        usage_stats = subscription_service.get_usage_stats(user_id)
        sub = subscription_service.get_user_subscription(user_id)

        # Fetch interview data for analytics
        try:
            interviews = list(mongo.db.interviews.find({'user_id': user_id}).limit(100))
        except Exception:
            interviews = []

        # Calculate advanced metrics
        advanced_metrics = {
            'total_interviews': usage_stats['total_interviews'],
            'interviews_this_month': usage_stats['interviews_this_month'],
            'interviews_by_category': usage_stats['interviews_by_category'],
            'most_common_role': usage_stats['most_common_role'],
            'average_score': usage_stats['average_score'],
            'tier': sub['tier'],
            'plan_info': {
                'name': sub['plan_info'].get('name'),
                'price': sub['plan_info'].get('price'),
                'monthly_interviews': sub['monthly_limit'],
            },
            'performance_trend': _calculate_performance_trend(interviews),
            'detailed_breakdown': _get_detailed_breakdown(interviews),
        }

        return jsonify(advanced_metrics), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/email-support', methods=['POST'])
@token_required
def submit_email_support():
    """Submit a support email request (Basic+ tier only)"""
    current_user = _get_current_user()
    user_id = current_user['_id']

    try:
        # Check if user has email support access
        if not subscription_service.has_email_support(user_id):
            return jsonify({
                'error': 'Email support is only available in Basic and Pro plans',
                'required_tier': 'basic'
            }), 403

        data = request.get_json(silent=True) or {}
        subject = (data.get('subject') or '').strip()
        message = (data.get('message') or '').strip()

        if not subject or not message:
            return jsonify({'error': 'Subject and message are required'}), 400

        # Store support request in database
        tier = subscription_service.get_user_subscription(user_id)['tier']
        support_request = {
            'user_id': user_id,
            'email': current_user.get('email'),
            'subject': subject,
            'message': message,
            'timestamp': utc_now(),
            'status': 'open',
            'priority': 'high' if tier == 'pro' else 'normal',
            'tier': tier,
        }

        try:
            mongo.db.support_requests.insert_one(support_request)
        except Exception:
            # If MongoDB unavailable, still return success for demo
            pass

        return jsonify({
            'success': True,
            'message': 'Your support request has been submitted. Our team will respond within 24 hours.',
            'request_id': support_request.get('_id', 'pending')
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/plan-comparison', methods=['GET'])
def get_plan_comparison():
    """Get a detailed comparison of all subscription plans"""
    try:
        comparison = subscription_service.get_plan_comparison()
        return jsonify({
            'plans': comparison
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/feedback-history-limit', methods=['GET'])
@token_required
def get_feedback_history_limit():
    """Get the feedback history retention limit for the user's tier"""
    current_user = _get_current_user()
    user_id = current_user['_id']

    try:
        history_days = subscription_service.get_feedback_history_days(user_id)
        sub = subscription_service.get_user_subscription(user_id)

        return jsonify({
            'tier': sub['tier'],
            'feedback_history_days': history_days,
            'unlimited': history_days is None,
            'message': 'Unlimited feedback history' if history_days is None else f'Feedback retained for {history_days} days'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========================
# Helper Functions
# ========================

def _calculate_performance_trend(interviews):
    """Calculate performance trend over time"""
    if not interviews:
        return {'trend': 'no_data', 'average': 0}

    scores = []
    for interview in interviews:
        feedback = interview.get('feedback', [])
        for item in feedback:
            if isinstance(item, dict) and 'score' in item:
                scores.append(item['score'])

    if not scores:
        return {'trend': 'no_data', 'average': 0}

    avg = sum(scores) / len(scores)
    
    # Determine trend based on recent vs overall
    recent_scores = scores[-5:] if len(scores) >= 5 else scores
    recent_avg = sum(recent_scores) / len(recent_scores)

    if recent_avg > avg:
        trend = 'improving'
    elif recent_avg < avg:
        trend = 'declining'
    else:
        trend = 'stable'

    return {
        'trend': trend,
        'average': round(avg, 2),
        'recent_average': round(recent_avg, 2)
    }


def _get_detailed_breakdown(interviews):
    """Get detailed breakdown of interview performance by category"""
    breakdown = {}
    
    for interview in interviews:
        questions = interview.get('questions', [])
        feedback = interview.get('feedback', [])
        
        for i, question in enumerate(questions):
            category = question.get('category', 'unknown')
            
            if category not in breakdown:
                breakdown[category] = {
                    'count': 0,
                    'average_score': 0,
                    'scores': []
                }
            
            breakdown[category]['count'] += 1
            
            # Get score for this question if available
            if i < len(feedback) and isinstance(feedback[i], dict):
                score = feedback[i].get('score', 0)
                breakdown[category]['scores'].append(score)
    
    # Calculate averages
    for category in breakdown:
        if breakdown[category]['scores']:
            avg = sum(breakdown[category]['scores']) / len(breakdown[category]['scores'])
            breakdown[category]['average_score'] = round(avg, 2)
        del breakdown[category]['scores']  # Remove raw scores from response
    
    return breakdown


@subscription_bp.route('/create-coupon', methods=['POST'])
@token_required
def create_coupon():
    """Create a coupon for testing/admin use. In production restrict this to admins only."""
    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    try:
        discount = int(data.get('discount_percent', 0))
    except Exception:
        return jsonify({'error': 'Invalid discount_percent'}), 400
    if not code or discount <= 0 or discount > 100:
        return jsonify({'error': 'Invalid coupon parameters'}), 400
    expires_in_days = data.get('expires_in_days')
    max_uses = data.get('max_uses')
    from datetime import timedelta
    expires_at = None
    if isinstance(expires_in_days, (int, float)) and expires_in_days > 0:
        expires_at = utc_now() + timedelta(days=int(expires_in_days))
    try:
        coupon = subscription_service.create_coupon(code, discount, expires_at=expires_at, max_uses=max_uses)
        return jsonify({'coupon': coupon}), 201
    except Exception as e:
        current_app.logger.exception('Failed to create coupon')
        return jsonify({'error': str(e)}), 500
