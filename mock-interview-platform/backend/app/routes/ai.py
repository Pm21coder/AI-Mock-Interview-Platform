from flask import Blueprint, request, jsonify
import logging

from app.services.ai_pipeline import AnswerGenerator, AnswerAnalyzer, ExpressionAnalyzer

logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__)

# Initialize shared service instances
_answer_generator = AnswerGenerator()
_answer_analyzer = AnswerAnalyzer()
_expression_analyzer = ExpressionAnalyzer()


@ai_bp.route('/generate-answer', methods=['POST'])
def generate_answer():
    """Generate a model answer for a given question.
    Expects JSON: { question: string }
    Returns: { model_answer: string }
    """
    data = request.get_json(silent=True) or {}
    question = data.get('question')
    if not question:
        return jsonify({'error': 'Missing question'}), 400

    try:
        answer = _answer_generator.generate_answer(question)
        return jsonify({'model_answer': answer}), 200
    except Exception as exc:
        logger.exception('generate-answer failed: %s', exc)
        return jsonify({'error': 'Failed to generate answer', 'detail': str(exc)}), 500


@ai_bp.route('/analyze-answer', methods=['POST'])
def analyze_answer():
    """Analyze a user's answer compared to the model answer.
    Expects JSON: { question, user_answer, model_answer }
    Returns: { similarity_score, feedback }
    """
    data = request.get_json(silent=True) or {}
    question = data.get('question')
    user_answer = data.get('user_answer')
    model_answer = data.get('model_answer')

    if not question or user_answer is None or model_answer is None:
        return jsonify({'error': 'Missing fields; require question, user_answer, model_answer'}), 400

    try:
        out = _answer_analyzer.analyze(question, user_answer, model_answer)
        return jsonify(out), 200
    except Exception as exc:
        logger.exception('analyze-answer failed: %s', exc)
        return jsonify({'error': 'Failed to analyze answer', 'detail': str(exc)}), 500


@ai_bp.route('/analyze-expression', methods=['POST'])
def analyze_expression():
    """Analyze emotion from an uploaded image.
    Accepts multipart/form-data with field 'image' (file upload).
    Returns: { dominant_emotion, emotions }
    """
    if 'image' not in request.files:
        return jsonify({'error': 'image file is required (multipart/form-data with "image" field)'}), 400

    f = request.files['image']
    try:
        data = f.read()
        res = _expression_analyzer.analyze_image_bytes(data)
        return jsonify(res), 200
    except Exception as exc:
        logger.exception('analyze-expression failed: %s', exc)
        return jsonify({'error': 'Failed to analyze image', 'detail': str(exc)}), 500
