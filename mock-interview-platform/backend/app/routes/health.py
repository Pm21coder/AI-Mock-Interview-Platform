from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health endpoint used by the frontend and load balancers.

    Returns 200 OK and a short JSON payload to indicate the backend is alive.
    """
    return jsonify({'status': 'ok', 'time': None}), 200
