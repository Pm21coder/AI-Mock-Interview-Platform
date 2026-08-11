from datetime import datetime, timedelta
from uuid import uuid4

import stripe
from flask import Blueprint, jsonify, request

from app import mongo
from app.config import Config
from app.utils.auth import token_required

subscription_bp = Blueprint('subscription', __name__)

# Initialize Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY


@subscription_bp.route('/plans', methods=['GET'])
def get_plans():
    """Get all available subscription plans"""
    return jsonify({
        'plans': Config.SUBSCRIPTION_TIERS
    }), 200


@subscription_bp.route('/status', methods=['GET'])
@token_required
def get_subscription_status(current_user):
    """Get current user's subscription status"""
    user_data = mongo.db.users.find_one({'_id': current_user['_id']})
    
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
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
            {'_id': current_user['_id']},
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


@subscription_bp.route('/create-checkout-session', methods=['POST'])
@token_required
def create_checkout_session(current_user):
    """Create Stripe checkout session for subscription"""
    data = request.get_json(silent=True) or {}
    tier = data.get('tier', '').lower()
    
    if tier not in ['basic', 'pro']:
        return jsonify({'error': 'Invalid subscription tier'}), 400
    
    price_id = Config.STRIPE_PRICE_IDS.get(tier)
    if not price_id:
        return jsonify({'error': 'Price ID not configured for this tier'}), 500
    
    try:
        # Get or create Stripe customer
        user_data = mongo.db.users.find_one({'_id': current_user['_id']})
        stripe_customer_id = user_data.get('stripe_customer_id')
        
        if not stripe_customer_id:
            customer = stripe.Customer.create(
                email=user_data['email'],
                metadata={'user_id': str(current_user['_id'])}
            )
            stripe_customer_id = customer.id
            
            # Save customer ID to database
            mongo.db.users.update_one(
                {'_id': current_user['_id']},
                {'$set': {'stripe_customer_id': stripe_customer_id}}
            )
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{Config.FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{Config.FRONTEND_URL}/subscription?canceled=true",
            metadata={
                'user_id': str(current_user['_id']),
                'tier': tier
            }
        )
        
        return jsonify({
            'sessionId': checkout_session.id,
            'url': checkout_session.url
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    event_type = event['type']
    event_data = event['data']['object']
    
    if event_type == 'checkout.session.completed':
        # Subscription created
        session = event_data
        user_id = session['metadata']['user_id']
        tier = session['metadata']['tier']
        stripe_customer_id = session['customer']
        stripe_subscription_id = session['subscription']
        
        # Get subscription details
        subscription = stripe.Subscription.retrieve(stripe_subscription_id)
        
        # Update user subscription
        mongo.db.users.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'subscription_tier': tier,
                    'subscription_status': 'active',
                    'subscription_start_date': datetime.utcnow(),
                    'subscription_end_date': datetime.fromtimestamp(subscription.current_period_end),
                    'stripe_customer_id': stripe_customer_id,
                    'stripe_subscription_id': stripe_subscription_id,
                    'interviews_used_this_month': 0
                }
            }
        )
    
    elif event_type == 'customer.subscription.updated':
        # Subscription updated (upgrade/downgrade)
        subscription = event_data
        stripe_customer_id = subscription['customer']
        
        # Find user by Stripe customer ID
        user = mongo.db.users.find_one({'stripe_customer_id': stripe_customer_id})
        if user:
            # Update subscription status
            status = subscription['status']
            mongo.db.users.update_one(
                {'_id': user['_id']},
                {
                    '$set': {
                        'subscription_status': status,
                        'subscription_end_date': datetime.fromtimestamp(subscription['current_period_end'])
                    }
                }
            )
    
    elif event_type == 'customer.subscription.deleted':
        # Subscription canceled
        subscription = event_data
        stripe_customer_id = subscription['customer']
        
        # Find user and downgrade to free
        user = mongo.db.users.find_one({'stripe_customer_id': stripe_customer_id})
        if user:
            mongo.db.users.update_one(
                {'_id': user['_id']},
                {
                    '$set': {
                        'subscription_tier': 'free',
                        'subscription_status': 'canceled',
                        'subscription_end_date': datetime.utcnow(),
                        'stripe_subscription_id': None
                    }
                }
            )
    
    return jsonify({'status': 'success'}), 200


@subscription_bp.route('/cancel', methods=['POST'])
@token_required
def cancel_subscription(current_user):
    """Cancel user's subscription"""
    user_data = mongo.db.users.find_one({'_id': current_user['_id']})
    
    if not user_data or not user_data.get('stripe_subscription_id'):
        return jsonify({'error': 'No active subscription found'}), 404
    
    try:
        # Cancel at period end (user keeps access until end of billing period)
        stripe.Subscription.modify(
            user_data['stripe_subscription_id'],
            cancel_at_period_end=True
        )
        
        # Update subscription status
        mongo.db.users.update_one(
            {'_id': current_user['_id']},
            {'$set': {'subscription_status': 'canceled'}}
        )
        
        return jsonify({'message': 'Subscription will be canceled at the end of billing period'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/reactivate', methods=['POST'])
@token_required
def reactivate_subscription(current_user):
    """Reactivate a canceled subscription"""
    user_data = mongo.db.users.find_one({'_id': current_user['_id']})
    
    if not user_data or not user_data.get('stripe_subscription_id'):
        return jsonify({'error': 'No subscription found'}), 404
    
    try:
        # Remove cancel_at_period_end
        stripe.Subscription.modify(
            user_data['stripe_subscription_id'],
            cancel_at_period_end=False
        )
        
        # Update subscription status
        mongo.db.users.update_one(
            {'_id': current_user['_id']},
            {'$set': {'subscription_status': 'active'}}
        )
        
        return jsonify({'message': 'Subscription reactivated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/portal', methods=['POST'])
@token_required
def create_customer_portal(current_user):
    """Create Stripe customer portal session for managing subscription"""
    user_data = mongo.db.users.find_one({'_id': current_user['_id']})
    
    if not user_data or not user_data.get('stripe_customer_id'):
        return jsonify({'error': 'No subscription found'}), 404
    
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=user_data['stripe_customer_id'],
            return_url=f"{Config.FRONTEND_URL}/subscription",
        )
        
        return jsonify({'url': portal_session.url}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500