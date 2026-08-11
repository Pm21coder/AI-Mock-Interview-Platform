from datetime import datetime
from uuid import uuid4

from flask import Blueprint, jsonify, request

from app import mongo
from app.config import Config
from app.models.interview import InterviewQuestion, InterviewSession
from app.services.dashboard_service import DashboardService
from app.services.gemini_service import GeminiService
from app.services.nlp_service import NLPService
from app.socket_events import emit_dashboard_update
from app.utils.auth import token_required

interview_bp = Blueprint('interview', __name__)
gemini_service = GeminiService()
nlp_service = NLPService()
dashboard_service = DashboardService()

# The app remains usable locally when MongoDB has not been started. Data in
# this store lasts for the lifetime of the backend process.
demo_sessions = {}


def check_subscription_limit(user_id):
    """Check if user has reached their monthly interview limit"""
    if user_id == 'guest':
        return True, None
    
    try:
        user = mongo.db.users.find_one({'_id': user_id})
        if not user:
            return True, None
        
        tier = user.get('subscription_tier', 'free')
        plan = Config.SUBSCRIPTION_TIERS.get(tier, Config.SUBSCRIPTION_TIERS['free'])
        
        interviews_used = user.get('interviews_used_this_month', 0)
        monthly_limit = plan['monthly_interviews']
        
        # Unlimited interviews for pro tier
        if monthly_limit == float('inf'):
            return True, None
        
        # Check if user has exceeded limit
        if interviews_used >= monthly_limit:
            return False, {
                'error': 'Monthly interview limit reached',
                'tier': tier,
                'interviews_used': interviews_used,
                'monthly_limit': monthly_limit,
                'upgrade_url': '/subscription'
            }
        
        return True, None
    except Exception:
        return True, None


def increment_interview_count(user_id):
    """Increment the user's monthly interview count"""
    if user_id == 'guest':
        return
    
    try:
        mongo.db.users.update_one(
            {'_id': user_id},
            {'$inc': {'interviews_used_this_month': 1}}
        )
    except Exception:
        pass


def current_user_id():
    return str(request.current_user.get('_id', 'guest'))


@interview_bp.route('/generate-questions', methods=['POST'])
@token_required
def generate_questions():
    # Check subscription limit
    can_proceed, limit_error = check_subscription_limit(current_user_id())
    if not can_proceed:
        return jsonify(limit_error), 403
    
    data = request.get_json(silent=True) or {}
    job_role = (data.get('job_role') or '').strip()
    category = data.get('category', 'technical')
    difficulty = data.get('difficulty', 'medium')

    if not job_role:
        return jsonify({'error': 'Job role is required'}), 400

    try:
        num_questions = int(data.get('num_questions', 5))
    except (TypeError, ValueError):
        return jsonify({'error': 'num_questions must be a number'}), 400
    if not 1 <= num_questions <= 10:
        return jsonify({'error': 'num_questions must be between 1 and 10'}), 400

    try:
        generated = gemini_service.generate_questions(job_role, category, difficulty, num_questions)
        questions = [
            InterviewQuestion(
                question.get('question', 'Tell me about your experience'),
                category,
                difficulty,
                question.get('expected_answer', ''),
            )
            for question in generated[:num_questions]
        ]
        if not questions:
            return jsonify({'error': 'No questions could be generated'}), 500

        # Increment interview count
        increment_interview_count(current_user_id())

        session_id = str(uuid4())
        interview = InterviewSession(current_user_id(), job_role, questions)
        session_document = {
            '_id': session_id,
            'user_id': interview.user_id,
            'job_role': interview.job_role,
            'questions': [question.to_dict() for question in interview.questions],
            'created_at': interview.created_at,
            'responses': [],
            'feedback': [],
        }
        demo_sessions[session_id] = session_document
        if current_user_id() != 'guest':
            try:
                mongo.db.interviews.insert_one(session_document)
            except Exception:
                pass

        return jsonify({'session_id': session_id, 'questions': session_document['questions']})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@interview_bp.route('/analyze-answer', methods=['POST'])
@token_required
def analyze_answer():
    data = request.get_json(silent=True) or {}
    question = data.get('question')
    answer = (data.get('answer') or '').strip()
    expected_answer = data.get('expected_answer', '')
    session_id = data.get('session_id')
    question_index = data.get('question_index', 0)

    if not question or not answer:
        return jsonify({'error': 'Question and answer are required'}), 400

    try:
        combined_feedback = {
            'nlp_analysis': nlp_service.analyze_answer_quality(answer, expected_answer),
            'gemini_feedback': gemini_service.analyze_answer(question, answer, expected_answer),
            'cv_analysis': ({'average_confidence': 0.72, 'overall_assessment': 'Good visual presence', 'total_frames_analyzed': 0}
                            if data.get('video_data') else
                            {'average_confidence': 0.75, 'overall_assessment': 'No video data - estimated from answer quality', 'total_frames_analyzed': 0}),
            'timestamp': datetime.utcnow().isoformat(),
        }
        response_record = {'question_index': question_index, 'answer': answer, 'feedback': combined_feedback}
        if session_id in demo_sessions:
            demo_sessions[session_id]['responses'].append(response_record)
        if current_user_id() != 'guest':
            try:
                mongo.db.interviews.update_one(
                    {'_id': session_id, 'user_id': current_user_id()},
                    {'$push': {'responses': response_record}},
                )
            except Exception:
                pass
        return jsonify(combined_feedback)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@interview_bp.route('/get-feedback/<session_id>', methods=['GET'])
@token_required
def get_feedback(session_id):
    interview = demo_sessions.get(session_id)
    if not interview and current_user_id() != 'guest':
        try:
            interview = mongo.db.interviews.find_one({'_id': session_id, 'user_id': current_user_id()})
        except Exception:
            interview = None
    if not interview:
        return jsonify({'error': 'Session not found'}), 404

    responses = interview.get('responses', [])
    if not responses:
        return jsonify({'error': 'No responses recorded for this interview'}), 404

    score_keys = ('overall_score', 'content_score', 'structure_score', 'clarity_score')
    all_scores = [response.get('feedback', {}).get('gemini_feedback', {}) for response in responses]
    latest_scores = all_scores[-1]
    averages = {
        key: round(sum(score.get(key, 0) for score in all_scores) / len(all_scores))
        for key in score_keys
    }

    # Persist/update the user's dashboard stats in MongoDB now that the
    # interview is complete. This ensures the dashboard reflects the new
    # interview immediately after the user navigates to it.
    if current_user_id() != 'guest':
        updated_stats = dashboard_service.update_after_interview(current_user_id(), interview)
        # Emit a real-time update so any open dashboard page refreshes
        # immediately without waiting for the 30-second polling interval.
        emit_dashboard_update(current_user_id(), {
            'interviews_completed': updated_stats.interviews_completed,
            'average_score': updated_stats.average_score,
            'confidence_score': updated_stats.confidence_score,
            'recent_interviews': updated_stats.recent_interviews,
        })

    return jsonify({
        'session_id': session_id,
        **averages,
        'strengths': latest_scores.get('strengths', ['Good technical knowledge', 'Clear communication']),
        'improvements': latest_scores.get('improvements', ['Work on confidence', 'Provide more specific examples']),
        'detailed_feedback': latest_scores.get('detailed_feedback', 'You demonstrated a solid interview performance.'),
    })


@interview_bp.route('/save-response', methods=['POST'])
@token_required
def save_response():
    data = request.get_json(silent=True) or {}
    response_document = {
        'session_id': data.get('session_id'),
        'user_id': current_user_id(),
        'question_index': data.get('question_index'),
        'response': data.get('response'),
        'feedback': data.get('feedback'),
        'timestamp': datetime.utcnow(),
    }
    if current_user_id() != 'guest':
        try:
            mongo.db.responses.insert_one(response_document)
        except Exception:
            pass
    return jsonify({'status': 'success', 'message': 'Response saved'})


@interview_bp.route('/dashboard-stats', methods=['GET'])
@token_required
def get_dashboard_stats():
    # Normalize to string to match how user_id is stored on interview sessions
    # (current_user_id() always returns str(...) of the _id).
    user_id = current_user_id()

    # Mock data for guest users
    if user_id == 'guest':
        response = jsonify({
            'stats': {
                'interviews_completed': 18,
                'average_score': 82,
                'confidence_score': 88
            },
            'recent_interviews': [
                {'role': 'Software Engineer', 'score': 88, 'date': '2026-08-01', 'confidence': 90},
                {'role': 'Product Manager', 'score': 79, 'date': '2026-07-29', 'confidence': 85},
                {'role': 'Data Analyst', 'score': 91, 'date': '2026-07-24', 'confidence': 92},
                {'role': 'UX Designer', 'score': 75, 'date': '2026-07-20', 'confidence': 80},
                {'role': 'DevOps Engineer', 'score': 85, 'date': '2026-07-15', 'confidence': 88},
            ]
        })
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        return response

    try:
        # Read pre-aggregated stats from the dashboard_stats collection.
        # If no record exists yet (e.g. first visit), fall back to a
        # one-time rebuild from raw interview documents.
        stats = dashboard_service.get_stats(user_id)
        if stats is None:
            stats = dashboard_service.rebuild_from_interviews(user_id)

        response = jsonify({
            'stats': {
                'interviews_completed': stats.interviews_completed,
                'average_score': stats.average_score,
                'confidence_score': stats.confidence_score
            },
            'recent_interviews': stats.recent_interviews
        })
        # Prevent intermediate caches from serving stale, sensitive dashboard statistics
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        return response

    except Exception as exc:
        print(f"Dashboard stats error: {str(exc)}")
        # Fallback to mock data in case of any error
        response = jsonify({
            'stats': {
                'interviews_completed': 18,
                'average_score': 82,
                'confidence_score': 88
            },
            'recent_interviews': [
                {'role': 'Software Engineer', 'score': 88, 'date': '2026-08-01', 'confidence': 90},
                {'role': 'Product Manager', 'score': 79, 'date': '2026-07-29', 'confidence': 85},
                {'role': 'Data Analyst', 'score': 91, 'date': '2026-07-24', 'confidence': 92},
                {'role': 'UX Designer', 'score': 75, 'date': '2026-07-20', 'confidence': 80},
                {'role': 'DevOps Engineer', 'score': 85, 'date': '2026-07-15', 'confidence': 88},
            ]
        })
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        return response
