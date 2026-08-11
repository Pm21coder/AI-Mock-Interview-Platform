from flask import Blueprint, jsonify

feedback_bp = Blueprint('feedback', __name__)


@feedback_bp.route('/summary', methods=['GET'])
def summary():
    return jsonify({
        'summary': 'Interview feedback is ready.',
        'overall_score': 82,
        'key_strengths': ['Clear communication', 'Technical depth'],
        'areas_to_improve': ['Be more concise', 'Add more examples'],
    })
