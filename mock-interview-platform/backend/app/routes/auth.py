from datetime import datetime
from uuid import uuid4

import bcrypt
import jwt
from flask import Blueprint, jsonify, request

from app import mongo
from app.config import Config

auth_bp = Blueprint('auth', __name__)
demo_users = {}


def create_token(user):
    return jwt.encode(
        {'user_id': str(user['_id']), 'email': user['email']},
        Config.JWT_SECRET_KEY,
        algorithm='HS256',
    )


def find_user(email):
    """Use MongoDB when available, otherwise preserve local demo accounts."""
    try:
        user = mongo.db.users.find_one({'email': email})
        if user:
            return user
    except Exception:
        pass
    return demo_users.get(email)


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
    }
    try:
        result = mongo.db.users.insert_one(user)
        user['_id'] = result.inserted_id
    except Exception:
        user['_id'] = f'demo_{uuid4()}'
        demo_users[email] = user

    return jsonify({'token': create_token(user), 'user': {'email': user['email']}}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    user = find_user(email)

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Invalid email or password'}), 401

    return jsonify({'token': create_token(user), 'user': {'email': user['email']}})
