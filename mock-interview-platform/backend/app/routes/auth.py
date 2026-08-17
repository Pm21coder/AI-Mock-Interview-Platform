import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import bcrypt
import jwt
from flask import Blueprint, jsonify, request, current_app

from app import mongo, limiter
from app.config import Config
from app.utils.time import utc_now
from app.utils.validation import validate_string, validate_email

auth_bp = Blueprint('auth', __name__)
DEMO_EMAIL = 'demo@mockinterview.app'
DEMO_PASSWORD = 'demo12345'
AUTH_USERS_FILE = Path(__file__).resolve().parents[2] / 'data' / 'local_auth_users.json'


def _default_demo_user():
    now = utc_now()
    return {
        '_id': 'demo_default',
        'email': DEMO_EMAIL,
        'password_hash': bcrypt.hashpw(
            DEMO_PASSWORD.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8'),
        'created_at': now,
        'subscription_tier': 'free',
        'subscription_status': 'active',
        'subscription_start_date': now,
        'subscription_end_date': now + timedelta(days=30),
        'interviews_used_this_month': 0,
    }


def load_local_auth_users():
    try:
        AUTH_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not AUTH_USERS_FILE.exists():
            payload = {DEMO_EMAIL: _default_demo_user()}
            save_local_auth_users(payload)
            return payload

        raw_data = AUTH_USERS_FILE.read_text(encoding='utf-8').strip()
        if not raw_data:
            payload = {DEMO_EMAIL: _default_demo_user()}
            save_local_auth_users(payload)
            return payload

        data = json.loads(raw_data)
        if not isinstance(data, dict):
            return {DEMO_EMAIL: _default_demo_user()}

        normalized = {}
        for email, user in data.items():
            if not email:
                continue
            normalized[str(email).strip().lower()] = user
        if DEMO_EMAIL not in normalized:
            normalized[DEMO_EMAIL] = _default_demo_user()
        save_local_auth_users(normalized)
        return normalized
    except Exception:
        fallback = {DEMO_EMAIL: _default_demo_user()}
        save_local_auth_users(fallback)
        return fallback


def save_local_auth_users(users):
    try:
        AUTH_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        normalized = {}
        for email, user in (users or {}).items():
            if not email:
                continue
            normalized[str(email).strip().lower()] = user
        AUTH_USERS_FILE.write_text(json.dumps(normalized, default=str, indent=2), encoding='utf-8')
        return normalized
    except Exception:
        return users or {}


local_auth_users = load_local_auth_users()


def validate_password(password):
    if not isinstance(password, str):
        return False
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[^A-Za-z0-9]', password):
        return False
    return True


def _mongo_available():
    return current_app.config.get('MONGO_AVAILABLE', False)


def _disable_mongo():
    current_app.config['MONGO_AVAILABLE'] = False
    current_app.logger.warning('Disabling MongoDB access due to repeated errors.')


def find_user(email):
    """Use MongoDB when available, otherwise preserve local fallback accounts."""
    global local_auth_users
    email = (email or '').strip().lower()
    if not email:
        return None

    local_auth_users = load_local_auth_users()
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
    from datetime import datetime, timedelta
    token = jwt.encode(
        {
            'user_id': str(user['_id']),
            'email': user['email'],
            'exp': utc_now() + timedelta(days=30)
        },
        Config.JWT_SECRET_KEY,
        algorithm='HS256',
    )
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")  # Prevent spam and brute force attacks
def register():
    global local_auth_users
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    # Validate email
    is_valid, error = validate_email(email)
    if not is_valid:
        return jsonify({'error': error}), 400
    
    # Validate password exists
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    
    # Validate password length
    is_valid, error = validate_string(password, min_length=8, max_length=128, field_name="Password")
    if not is_valid:
        return jsonify({'error': error}), 400
    
    # Validate password strength
    if not validate_password(password):
        return jsonify({
            'error': 'Password must be at least 8 characters and include uppercase, lowercase, a number, and a symbol.'
        }), 400
    
    if find_user(email):
        return jsonify({'error': 'User already exists'}), 409

    now = utc_now()
    user = {
        'email': email,
        'password_hash': bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        'created_at': now,
        'subscription_tier': 'free',
        'subscription_status': 'active',
        'subscription_start_date': now,
        'subscription_end_date': now + timedelta(days=30),
        'interviews_used_this_month': 0,
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
            local_auth_users = load_local_auth_users()
            local_auth_users[email] = user
            save_local_auth_users(local_auth_users)
    else:
        user['_id'] = f'demo_{uuid4()}'
        local_auth_users = load_local_auth_users()
        local_auth_users[email] = user
        save_local_auth_users(local_auth_users)

    return jsonify({
        'token': create_token(user),
        'user': {
            'email': user['email'],
            'subscription_tier': user.get('subscription_tier', 'free'),
            'subscription_status': user.get('subscription_status', 'active'),
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Protect against brute force attacks
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    
    # Validate email format
    is_valid, error = validate_email(email)
    if not is_valid:
        return jsonify({'error': 'Invalid email address'}), 400
    
    # Validate password exists
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    
    # Validate password length
    is_valid, error = validate_string(password, min_length=1, max_length=128, field_name="Password")
    if not is_valid:
        return jsonify({'error': error}), 400
    
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
