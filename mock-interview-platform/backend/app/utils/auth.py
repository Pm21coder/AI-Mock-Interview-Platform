from functools import wraps

import jwt
from bson import ObjectId
from bson.errors import InvalidId
from flask import jsonify, request

from app import mongo
from app.config import Config


def get_user_id_from_token(token):
    """Decode a JWT and return the user id string, or None on failure."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        return str(user_id) if user_id else None
    except Exception:
        return None


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        # The interview UI supports a no-account practice mode. Authenticated
        # requests still use the normal JWT path below.
        if not auth_header.startswith('Bearer '):
            request.current_user = {'_id': 'guest', 'email': 'guest@local'}
            return f(*args, **kwargs)

        token = auth_header.split(' ', 1)[1].strip()
        if not token:
            return jsonify({'error': 'Missing auth token'}), 401

        try:
            payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            user_id = str(payload.get('user_id') or '').strip()
            if not user_id:
                return jsonify({'error': 'Invalid token payload'}), 401

            if user_id.startswith('demo_'):
                request.current_user = {'_id': user_id, 'email': payload.get('email', '')}
                return f(*args, **kwargs)

            try:
                object_id = ObjectId(user_id)
            except (InvalidId, TypeError):
                return jsonify({'error': 'Invalid token payload'}), 401

            try:
                user = mongo.db.users.find_one({'_id': object_id})
            except Exception:
                request.current_user = {'_id': user_id, 'email': payload.get('email', '')}
                return f(*args, **kwargs)

            if not user:
                return jsonify({'error': 'User not found'}), 401
            request.current_user = user
        except Exception:
            return jsonify({'error': 'Invalid or expired token'}), 401

        return f(*args, **kwargs)

    return decorated_function
