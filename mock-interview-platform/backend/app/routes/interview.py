from datetime import datetime
from uuid import uuid4
import logging

from flask import Blueprint, jsonify, request

from app import mongo
from app.config import Config
from app.models.interview import InterviewQuestion, InterviewSession
from app.services.dashboard_service import DashboardService
from app.services.gemini_service import GeminiService
from app.services.nlp_service import NLPService
from app.services.subscription_service import SubscriptionService
from app.socket_events import emit_dashboard_update
from app.utils.auth import token_required
from app.utils.time import utc_now
from app.cache_utils import optimize_response

logger = logging.getLogger(__name__)

interview_bp = Blueprint('interview', __name__)
gemini_service = GeminiService()
nlp_service = NLPService()
dashboard_service = DashboardService()
subscription_service = SubscriptionService()

# The app remains usable locally when MongoDB has not been started. Data in
# this store lasts for the lifetime of the backend process.
demo_sessions = {}


def current_user_id():
    return str(request.current_user.get('_id', 'guest'))


def current_subscription_user_id():
    """Keep ObjectIds intact for subscription and feature lookups."""
    return request.current_user.get('_id', 'guest')


@interview_bp.route('/generate-questions', methods=['POST'])
@token_required
def generate_questions():
    data = request.get_json(silent=True) or {}
    job_role = (data.get('job_role') or '').strip()
    category = (data.get('category') or 'technical').strip().lower()
    difficulty = (data.get('difficulty') or 'medium').strip().lower()

    if not job_role:
        return jsonify({'error': 'Job role is required'}), 400

    valid_categories = {'technical', 'behavioral', 'situational', 'system_design'}
    if category not in valid_categories:
        return jsonify({
            'error': 'Invalid question category',
            'available_categories': sorted(valid_categories),
        }), 400

    if difficulty not in {'easy', 'medium', 'hard'}:
        return jsonify({'error': 'Difficulty must be easy, medium, or hard'}), 400

    try:
        num_questions = int(data.get('num_questions', 5))
    except (TypeError, ValueError):
        return jsonify({'error': 'num_questions must be a number'}), 400
    if not 1 <= num_questions <= 10:
        return jsonify({'error': 'num_questions must be between 1 and 10'}), 400

    user_id = current_user_id()
    subscription_user_id = current_subscription_user_id()
    can_proceed, limit_error = subscription_service.check_interview_limit(
        subscription_user_id,
    )
    if not can_proceed:
        return jsonify(limit_error), 403

    # Validate question category based on subscription tier
    available_categories = subscription_service.get_available_question_categories(
        subscription_user_id,
    )
    if category not in available_categories:
        subscription = subscription_service.get_user_subscription(subscription_user_id)
        return jsonify({
            'error': f'Category "{category}" is not available in your plan. '
                    f'Available categories: {", ".join(available_categories)}. '
                    f'Upgrade to Basic or Pro plan for all categories.',
            'code': 'category_not_in_plan',
            'tier': subscription['tier'],
            'required_tier': 'basic',
            'available_categories': available_categories,
            'message': 'This question category requires the Basic or Pro plan.',
            'upgrade_url': '/subscription',
        }), 403

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

        # Increment interview count using the new subscription service
        subscription_service.increment_interview_count(subscription_user_id)

        session_id = str(uuid4())
        interview = InterviewSession(user_id, job_role, questions)
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
        if user_id != 'guest':
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
    user_id = current_user_id()
    subscription_user_id = current_subscription_user_id()
    data = request.get_json(silent=True) or {}
    question = data.get('question')
    answer = (data.get('answer') or '').strip()
    expected_answer = data.get('expected_answer', '')
    session_id = data.get('session_id')
    question_index = data.get('question_index', 0)

    if not question or not answer:
        return jsonify({'error': 'Question and answer are required'}), 400

    try:
        # Check if user has video analysis feature
        # Free tier can still submit answers, just won't get video analysis
        has_video_feature = subscription_service.has_feature(
            subscription_user_id,
            'video_analysis',
        )
        video_data_provided = data.get('video_data', False)
        
        # Get subscription tier for premium AI coaching
        is_premium = subscription_service.should_use_premium_ai_coaching(
            subscription_user_id,
        )
        
        # Analyze the answer with appropriate tier
        gemini_feedback = gemini_service.analyze_answer(
            question, 
            answer, 
            expected_answer, 
            is_premium=is_premium
        )
        
        # Provide video analysis only if feature is available
        # Free tier users can still submit with video, just without video analysis
        if video_data_provided and has_video_feature:
            cv_analysis = {
                'average_confidence': 0.72,
                'overall_assessment': 'Good visual presence',
                'total_frames_analyzed': 150,
            }
        elif video_data_provided and not has_video_feature:
            # User provided video but doesn't have feature - note this in response
            cv_analysis = {
                'average_confidence': 0.75,
                'overall_assessment': 'No video analysis (feature available in Basic and Pro plans)',
                'total_frames_analyzed': 0,
                'upgrade_note': 'Upgrade to Basic or Pro plan to unlock video analysis of your responses',
            }
        else:
            # No video data provided
            cv_analysis = {
                'average_confidence': 0.75,
                'overall_assessment': 'No video data - estimated from answer quality',
                'total_frames_analyzed': 0,
            }
        
        combined_feedback = {
            'nlp_analysis': nlp_service.analyze_answer_quality(answer, expected_answer),
            'gemini_feedback': gemini_feedback,
            'cv_analysis': cv_analysis,
            'timestamp': utc_now().isoformat(),
        }
        response_record = {'question_index': question_index, 'answer': answer, 'feedback': combined_feedback}
        if session_id in demo_sessions:
            demo_sessions[session_id]['responses'].append(response_record)
        if user_id != 'guest':
            try:
                mongo.db.interviews.update_one(
                    {'_id': session_id, 'user_id': user_id},
                    {'$push': {'responses': response_record}},
                )
            except Exception as db_exc:
                logger.warning(f'Failed to update interview in DB: {db_exc}')
        return jsonify(combined_feedback)
    except Exception as exc:
        error_msg = str(exc)
        logger.error(f'Error analyzing answer for user {user_id}: {error_msg}')
        return jsonify({
            'error': 'Failed to analyze answer. Please try again.',
            'details': error_msg
        }), 500


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
        'timestamp': utc_now(),
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
        # Older records did not include history_synced_at and can be left at
        # zero even when completed interview documents exist. Rebuild each
        # legacy record once to backfill its history.
        stats = dashboard_service.get_stats(user_id)
        if stats is None or stats.history_synced_at is None:
            stats = dashboard_service.rebuild_from_interviews(user_id)

        response_data = {
            'stats': {
                'interviews_completed': stats.interviews_completed,
                'average_score': stats.average_score,
                'confidence_score': stats.confidence_score
            },
            'recent_interviews': stats.recent_interviews
        }
        
        response = jsonify(optimize_response(response_data))
        # Prevent intermediate caches from serving stale, sensitive dashboard statistics
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        return response

    except Exception as exc:
        print(f"Dashboard stats error: {str(exc)}")
        return jsonify({'error': 'Unable to load dashboard data'}), 500
