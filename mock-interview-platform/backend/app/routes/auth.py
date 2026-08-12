from datetime import datetime
from uuid import uuid4

import bcrypt
import jwt
from flask import Blueprint, jsonify, request, current_app

from app import mongo
from app.config import Config

auth_bp = Blueprint('auth', __name__)
DEMO_EMAIL = 'demo@mockinterview.app'
DEMO_PASSWORD = 'demo12345'
local_auth_users = {
    DEMO_EMAIL: {
        '_id': 'demo_default',
        'email': DEMO_EMAIL,
        'password_hash': bcrypt.hashpw(
            DEMO_PASSWORD.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8'),
        'created_at': datetime.utcnow(),
        'subscription_tier': 'free',
        'subscription_status': 'active',
    }
}


def _mongo_available():
    return current_app.config.get('MONGO_AVAILABLE', False)


def _disable_mongo():
    current_app.config['MONGO_AVAILABLE'] = False
    current_app.logger.warning('Disabling MongoDB access due to repeated errors.')


def find_user(email):
    """Use MongoDB when available, otherwise preserve local fallback accounts."""
    email = (email or '').strip().lower()
    if not email:
        return None

    if email in local_auth_users:
        return local_auth_users[email]

    if not _mongo_available():
        return local_auth_users.get(email)

    try:
        user = mongo.db.users.find_one({'email': email})
        if user:
            return user
    except Exception as exc:
        current_app.logger.warning(
            'MongoDB read failed during auth lookup; falling back to local auth: %s',
            exc,
        )
        _disable_mongo()
        return local_auth_users.get(email)

    return None


def create_token(user):
    token = jwt.encode(
        {'user_id': str(user['_id']), 'email': user['email']},
        Config.JWT_SECRET_KEY,
        algorithm='HS256',
    )
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or '@' not in email or not password:
        return jsonify({'error': 'A valid email and password are required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must contain at least 8 characters'}), 400
    if find_user(email):
        return jsonify({'error': 'User already exists'}), 409

    user = {
        'email': email,
        'password_hash': bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        'created_at': datetime.utcnow(),
        'subscription_tier': 'free',
        'subscription_status': 'active',
    }

    if _mongo_available():
        try:
            result = mongo.db.users.insert_one(user)
            user['_id'] = result.inserted_id
        except Exception as exc:
            current_app.logger.warning(
                'MongoDB write failed during register; using local fallback: %s',
                exc,
            )
            _disable_mongo()
            user['_id'] = f'demo_{uuid4()}'
            local_auth_users[email] = user
    else:
        user['_id'] = f'demo_{uuid4()}'
        local_auth_users[email] = user

    return jsonify({
        'token': create_token(user),
        'user': {
            'email': user['email'],
            'subscription_tier': user.get('subscription_tier', 'free'),
            'subscription_status': user.get('subscription_status', 'active'),
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    user = find_user(email)

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Invalid email or password'}), 401

    return jsonify({
        'token': create_token(user), 
        'user': {
            'email': user['email'],
            'subscription_tier': user.get('subscription_tier', 'free'),
            'subscription_status': user.get('subscription_status', 'active')
        }
    })
