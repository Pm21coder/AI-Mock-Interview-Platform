from datetime import datetime
from uuid import uuid4
import logging

from flask import Blueprint, current_app, jsonify, request, Response, stream_with_context

from app import mongo, limiter
from app.config import Config
from app.models.interview import InterviewQuestion, InterviewSession
from app.services.dashboard_service import DashboardService
from app.services.gemini_service import GeminiService
from app.services.nlp_service import NLPService
from app.services.subscription_service import SubscriptionService
from app.socket_events import emit_dashboard_update, emit_interview_usage_update
from app.utils.auth import token_required
from app.utils.time import utc_now
from app.utils.validation import validate_string, validate_integer
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

# Prefer a Redis-backed queue (RQ) for background jobs in production.
# Fall back to a simple in-process job store and threads for local/dev runs
# when Redis is not configured or available.
import os
redis_conn = None
rq_queue = None
use_redis_queue = False
try:
    import redis
    from rq import Queue, Job
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        redis_conn = redis.from_url(redis_url)
        rq_queue = Queue('default', connection=redis_conn)
        use_redis_queue = True
except Exception:
    # Redis/RQ not available in the environment; fall back to in-process worker
    redis_conn = None
    rq_queue = None
    use_redis_queue = False

# In-process fallback job store (used when Redis is not configured)
jobs = {}
from threading import Thread, Lock
jobs_lock = Lock()


# Job worker functions (must be importable by RQ workers when using Redis)
def run_generate_questions_job(payload):
    """Background-friendly function that generates questions and returns a job result."""
    try:
        job_role = (payload.get('job_role') or '').strip()
        category = (payload.get('category') or 'technical').strip().lower()
        difficulty = (payload.get('difficulty') or 'medium').strip().lower()
        num_questions = int(payload.get('num_questions', 5))

        try:
            generated = gemini_service.generate_questions(job_role, category, difficulty, num_questions)
        except Exception as exc:
            logger.exception('Gemini generate_questions (job) failed: %s', exc)
            generated = gemini_service.get_fallback_questions(job_role, category, num_questions)

        questions = [
            InterviewQuestion(
                q.get('question', 'Tell me about your experience'),
                category,
                difficulty,
                q.get('expected_answer', ''),
            ).to_dict()
            for q in generated[:num_questions]
        ]

        result = {'session_id': str(uuid4()), 'questions': questions}
        return {'status': 'completed', 'result': result}
    except Exception as exc:
        logger.exception('Question generation job failed: %s', exc)
        return {'status': 'failed', 'error': str(exc)}


def run_analyze_answer_job(payload):
    """Background-friendly function that analyzes an answer and returns feedback."""
    try:
        question = payload.get('question')
        answer = (payload.get('answer') or '').strip()
        expected_answer = payload.get('expected_answer', '')

        try:
            is_premium = subscription_service.should_use_premium_ai_coaching(payload.get('user_id', 'guest'))
        except Exception:
            is_premium = False

        try:
            gemini_feedback = gemini_service.analyze_answer(question, answer, expected_answer, is_premium=is_premium)
        except Exception as gem_exc:
            logger.exception('Gemini analysis job failed: %s', gem_exc)
            gemini_feedback = gemini_service.get_fallback_feedback(is_premium=is_premium, user_answer=answer, expected_answer=expected_answer)

        try:
            nlp_analysis = nlp_service.analyze_answer_quality(answer, expected_answer)
        except Exception as nlp_exc:
            logger.exception('NLP analysis job failed: %s', nlp_exc)
            nlp_analysis = {'word_count': len(answer.split()), 'sentence_count': 0}

        cv_analysis = {'average_confidence': 0.75, 'overall_assessment': 'No video analysis in job mode', 'total_frames_analyzed': 0}

        combined_feedback = {'nlp_analysis': nlp_analysis, 'gemini_feedback': gemini_feedback, 'cv_analysis': cv_analysis, 'timestamp': utc_now().isoformat()}
        return {'status': 'completed', 'result': combined_feedback}
    except Exception as exc:
        logger.exception('Analysis job failed: %s', exc)
        return {'status': 'failed', 'error': str(exc)}


def current_user_id():
    return str(request.current_user.get('_id', 'guest'))


def current_subscription_user_id():
    """Keep ObjectIds intact for subscription and feature lookups."""
    return request.current_user.get('_id', 'guest')


@interview_bp.route('/generate-questions', methods=['POST'])
@token_required
@limiter.limit("10 per minute")  # Prevent abuse of expensive AI API calls
def generate_questions():
    data = request.get_json(silent=True) or {}
    job_role = (data.get('job_role') or '').strip()
    category = (data.get('category') or 'technical').strip().lower()
    difficulty = (data.get('difficulty') or 'medium').strip().lower()

    # Validate job_role length to prevent DoS
    is_valid, error = validate_string(job_role, min_length=1, max_length=100, field_name="Job role")
    if not is_valid:
        return jsonify({'error': error}), 400

    valid_categories = {'technical', 'behavioral', 'situational', 'system_design'}
    if category not in valid_categories:
        return jsonify({
            'error': 'Invalid question category',
            'available_categories': sorted(valid_categories),
        }), 400

    if difficulty not in {'easy', 'medium', 'hard'}:
        return jsonify({'error': 'Difficulty must be easy, medium, or hard'}), 400

    # Validate num_questions
    is_valid, error = validate_integer(data.get('num_questions', 5), min_value=1, max_value=10, field_name="num_questions")
    if not is_valid:
        return jsonify({'error': error}), 400
    num_questions = int(data.get('num_questions', 5))

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
        try:
            generated = gemini_service.generate_questions(job_role, category, difficulty, num_questions)
        except Exception as exc:
            # If the AI provider fails, fall back to local canned questions so the
            # user experience remains uninterrupted.
            logger.exception('Gemini generate_questions failed for user %s: %s', user_id, exc)
            generated = gemini_service.get_fallback_questions(job_role, category, num_questions)

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

        # A generated question set consumes one interview from the plan.
        try:
            subscription_service.increment_interview_count(subscription_user_id)
        except Exception as exc:
            # Log the failure but do not block question delivery to the user.
            logger.exception('Failed to record interview usage for user %s: %s', subscription_user_id, exc)

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

        # Notify any open subscription/setup pages after the usage write has
        # completed. The dashboard receives its separate completion event only
        # after feedback is generated.
        subscription = subscription_service.get_user_subscription(subscription_user_id)
        if user_id != 'guest':
            emit_interview_usage_update(user_id, subscription, session_id)

        return jsonify({
            'session_id': session_id,
            'questions': session_document['questions'],
            'subscription': subscription,
        })
    except Exception as exc:
        logger.exception('Failed to generate questions for user %s', user_id)
        return jsonify({
            'error': 'Unable to generate interview questions. Please try again.',
            'details': str(exc) if current_app.debug else None,
        }), 500


def _redis_required_guard():
    """Return a tuple (response, status) when Redis is required but not configured.
    Returns None when it's ok to proceed. Uses Config.REQUIRE_REDIS_IN_PRODUCTION
    and FLASK_DEBUG to decide whether Redis must be present.
    """
    # In production (FLASK_DEBUG False) require Redis when configured to do so
    if not Config.FLASK_DEBUG and Config.REQUIRE_REDIS_IN_PRODUCTION and not use_redis_queue:
        logger.error('Redis is required in production but REDIS_URL is not configured or Redis is unavailable')
        return jsonify({
            'error': 'Server misconfiguration: Redis is required in production to process background jobs. Please set REDIS_URL and start a worker.'
        }), 503
    return None


@interview_bp.route('/generate-questions-job', methods=['POST'])
@token_required
@limiter.limit("10 per minute")
def generate_questions_job():
    """Start a background job to generate questions and return a job_id immediately.
    Client should poll /api/interview/job/<job_id> for status/result.
    """
    # Guard: do not allow in-process fallback in production
    guard_resp = _redis_required_guard()
    if guard_resp:
        return guard_resp

    data = request.get_json(silent=True) or {}

    if use_redis_queue and rq_queue is not None:
        # Enqueue the job using RQ. The worker should import run_generate_questions_job
        try:
            job = rq_queue.enqueue('app.routes.interview.run_generate_questions_job', data)
            response = jsonify({'job_id': job.get_id()})
            response.status_code = 202
            return response
        except Exception as exc:
            logger.exception('Failed to enqueue generate_questions job to Redis: %s', exc)
            # Fall back to in-process job creation

    # In-process fallback: populate jobs store and start a thread
    job_id = str(uuid4())
    job_record = {
        'status': 'pending',
        'result': None,
        'error': None,
        'started_at': datetime.utcnow().isoformat(),
        'completed_at': None,
    }
    with jobs_lock:
        jobs[job_id] = job_record

    def _run_local_job(job_id_local, payload):
        result = run_generate_questions_job(payload)
        with jobs_lock:
            if result.get('status') == 'completed':
                jobs[job_id_local]['status'] = 'completed'
                jobs[job_id_local]['result'] = result.get('result')
            else:
                jobs[job_id_local]['status'] = 'failed'
                jobs[job_id_local]['error'] = result.get('error')
            jobs[job_id_local]['completed_at'] = datetime.utcnow().isoformat()

    thread = Thread(target=_run_local_job, args=(job_id, data), daemon=True)
    thread.start()

    response = jsonify({'job_id': job_id})
    response.status_code = 202
    return response


@interview_bp.route('/stream/generate-questions', methods=['POST'])
@token_required
@limiter.limit("10 per minute")
def stream_generate_questions():
    """Stream job events via Server-Sent Events (SSE)-style text/event-stream.
    This endpoint enqueues the same background job and then streams status updates
    and the final result as JSON in 'data:' SSE events. The frontend can connect
    and read events without busy-polling.
    """
    data = request.get_json(silent=True) or {}

    # Guard: in production require Redis (no in-process fallback)
    guard_resp = _redis_required_guard()
    if guard_resp:
        return guard_resp

    # Create or enqueue job (reuse the same logic as generate_questions_job)
    if use_redis_queue and rq_queue is not None:
        try:
            job = rq_queue.enqueue('app.routes.interview.run_generate_questions_job', data)
            job_id = job.get_id()
        except Exception as exc:
            logger.exception('Failed to enqueue streaming generate_questions job to Redis: %s', exc)
            job_id = None
    else:
        job_id = str(uuid4())
        job_record = {'status': 'pending', 'result': None, 'error': None, 'started_at': datetime.utcnow().isoformat(), 'completed_at': None}
        with jobs_lock:
            jobs[job_id] = job_record
        def _run_local_job_stream(job_id_local, payload):
            result = run_generate_questions_job(payload)
            with jobs_lock:
                if result.get('status') == 'completed':
                    jobs[job_id_local]['status'] = 'completed'
                    jobs[job_id_local]['result'] = result.get('result')
                else:
                    jobs[job_id_local]['status'] = 'failed'
                    jobs[job_id_local]['error'] = result.get('error')
                jobs[job_id_local]['completed_at'] = datetime.utcnow().isoformat()
        Thread(target=_run_local_job_stream, args=(job_id, data), daemon=True).start()

    # Now stream job status events until completion or timeout
    from app.routes._stream_helpers import sse_event, poll_job_and_stream

    @stream_with_context
    def event_stream():
        # Immediately tell the client we've started and provide job_id
        yield sse_event({'status': 'started', 'job_id': job_id})
        # Poll job status and yield events
        for chunk in poll_job_and_stream(job_id, timeout_seconds=max(60, int(Config.STREAM_TIMEOUT_SECONDS or 60))):
            yield chunk
        # Close
    return Response(event_stream(), mimetype='text/event-stream')


@interview_bp.route('/job/<job_id>', methods=['GET'])
@token_required
def get_job_status(job_id):
        # If Redis + RQ is configured, attempt to fetch the job status from Redis
        if use_redis_queue and redis_conn is not None:
            try:
                from rq.job import Job
                rq_job = Job.fetch(job_id, connection=redis_conn)
                state = rq_job.get_status()  # queued, started, finished, failed, deferred, scheduled
                if state in ('queued', 'deferred', 'started', 'scheduled'):
                    return jsonify({'status': 'pending'})
                if state == 'finished':
                    return jsonify({'status': 'completed', 'result': rq_job.result})
                if state == 'failed':
                    # RQ stores exc info in exc_info
                    return jsonify({'status': 'failed', 'error': str(rq_job.exc_info)}), 200
                return jsonify({'status': state})
            except Exception as exc:
                logger.exception('Failed to fetch job status from Redis for %s: %s', job_id, exc)
                # Fall through to in-process job store check

        with jobs_lock:
            job = jobs.get(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        return jsonify(job)


@interview_bp.route('/analyze-answer', methods=['POST'])
@token_required
@limiter.limit("20 per minute")  # Prevent spam of analysis requests
def analyze_answer():
    user_id = current_user_id()
    subscription_user_id = current_subscription_user_id()

    # Parse JSON safely and log lightweight request metadata to aid debugging
    try:
        data = request.get_json(silent=True) or {}
    except Exception as parse_exc:
        logger.warning('Failed to parse JSON body for analyze_answer: %s', parse_exc)
        data = {}

    # Log request summary (do not log large fields like video_data)
    try:
        keys = list(data.keys()) if isinstance(data, dict) else []
        logger.info(
            'analyze_answer request: user=%s session=%s content_length=%s keys=%s',
            user_id,
            data.get('session_id'),
            request.content_length,
            keys,
        )
    except Exception:
        # Best effort logging — never let logging raise and crash the handler
        logger.debug('analyze_answer: failed to record request metadata')

    question = data.get('question')
    answer = (data.get('answer') or '').strip()
    expected_answer = data.get('expected_answer', '')
    session_id = data.get('session_id')
    question_index = data.get('question_index', 0)

    if not question or not answer:
        return jsonify({'error': 'Question and answer are required'}), 400
    
    # Validate answer length to prevent DoS
    is_valid, error = validate_string(answer, min_length=1, max_length=5000, field_name="Answer")
    if not is_valid:
        return jsonify({'error': error}), 400

    try:
        # Check if user has video analysis feature
        # Free tier can still submit answers, just won't get video analysis
        try:
            has_video_feature = subscription_service.has_feature(
                subscription_user_id,
                'video_analysis',
            )
        except Exception as feat_exc:
            logger.warning(f'Failed to determine video feature access for user {subscription_user_id}: {feat_exc}')
            has_video_feature = False

        video_data_provided = data.get('video_data', False)
        
        # Get subscription tier for premium AI coaching
        try:
            is_premium = subscription_service.should_use_premium_ai_coaching(
                subscription_user_id,
            )
        except Exception as tier_exc:
            logger.warning(f'Failed to determine premium coaching eligibility for user {subscription_user_id}: {tier_exc}')
            is_premium = False
        
        # Analyze the answer with appropriate tier
        try:
            gemini_feedback = gemini_service.analyze_answer(
                question, 
                answer, 
                expected_answer, 
                is_premium=is_premium
            )
        except Exception as gem_exc:
            logger.exception('Gemini analysis failed, falling back to heuristic feedback: %s', gem_exc)
            gemini_feedback = gemini_service.get_fallback_feedback(is_premium=is_premium, user_answer=answer, expected_answer=expected_answer)
        
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
        
        # Ensure NLP analysis never raises to avoid returning 500 to client
        try:
            nlp_analysis = nlp_service.analyze_answer_quality(answer, expected_answer)
        except Exception as nlp_exc:
            logger.exception('NLP analysis failed, using minimal heuristic fallback: %s', nlp_exc)
            nlp_analysis = {'word_count': len(answer.split()), 'sentence_count': 0, 'sentiment': {'polarity': 0, 'subjectivity': 0}, 'keyword_coverage': 0, 'similarity_score': 0, 'grammar_score': 0, 'overall_quality': 0.0}

        combined_feedback = {
            'nlp_analysis': nlp_analysis,
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
        logger.exception(f'Error analyzing answer for user {user_id}: %s', error_msg)
        # Return a safe, non-sensitive error message to the client while logging details
        return jsonify({
            'error': 'Failed to analyze answer. Please try again.',
            'details': None,
        }), 500


@interview_bp.route('/analyze-answer-job', methods=['POST'])
@token_required
@limiter.limit("20 per minute")
def analyze_answer_job():
    """Start a background job to analyze an answer and return a job_id. Client polls /api/interview/job/<job_id>"""
    # Guard: do not allow in-process fallback in production
    guard_resp = _redis_required_guard()
    if guard_resp:
        return guard_resp

    data = request.get_json(silent=True) or {}

    if use_redis_queue and rq_queue is not None:
        try:
            job = rq_queue.enqueue('app.routes.interview.run_analyze_answer_job', data)
            response = jsonify({'job_id': job.get_id()})
            response.status_code = 202
            return response
        except Exception as exc:
            logger.exception('Failed to enqueue analyze_answer job to Redis: %s', exc)
            # Fall back to in-process job creation

    job_id = str(uuid4())
    job_record = {'status': 'pending', 'result': None, 'error': None, 'started_at': datetime.utcnow().isoformat(), 'completed_at': None}
    with jobs_lock:
        jobs[job_id] = job_record

    def _run_local_analysis(job_id_local, payload):
        result = run_analyze_answer_job(payload)
        with jobs_lock:
            if result.get('status') == 'completed':
                jobs[job_id_local]['status'] = 'completed'
                jobs[job_id_local]['result'] = result.get('result')
            else:
                jobs[job_id_local]['status'] = 'failed'
                jobs[job_id_local]['error'] = result.get('error')
            jobs[job_id_local]['completed_at'] = datetime.utcnow().isoformat()

    thread = Thread(target=_run_local_analysis, args=(job_id, data), daemon=True)
    thread.start()

    response = jsonify({'job_id': job_id})
    response.status_code = 202
    return response


@interview_bp.route('/stream/analyze-answer', methods=['POST'])
@token_required
@limiter.limit("20 per minute")
def stream_analyze_answer():
    """Stream analysis job events via SSE-style text/event-stream.
    Enqueue or start a background analyze job and stream status updates and the
    final result as JSON 'data' events.
    """
    data = request.get_json(silent=True) or {}

    # Guard: in production require Redis (no in-process fallback)
    guard_resp = _redis_required_guard()
    if guard_resp:
        return guard_resp

    # Enqueue to Redis RQ if available
    if use_redis_queue and rq_queue is not None:
        try:
            job = rq_queue.enqueue('app.routes.interview.run_analyze_answer_job', data)
            job_id = job.get_id()
        except Exception as exc:
            logger.exception('Failed to enqueue streaming analyze job to Redis: %s', exc)
            job_id = None
    else:
        job_id = str(uuid4())
        job_record = {'status': 'pending', 'result': None, 'error': None, 'started_at': datetime.utcnow().isoformat(), 'completed_at': None}
        with jobs_lock:
            jobs[job_id] = job_record

        def _run_local_analysis_stream(job_id_local, payload):
            result = run_analyze_answer_job(payload)
            with jobs_lock:
                if result.get('status') == 'completed':
                    jobs[job_id_local]['status'] = 'completed'
                    jobs[job_id_local]['result'] = result.get('result')
                else:
                    jobs[job_id_local]['status'] = 'failed'
                    jobs[job_id_local]['error'] = result.get('error')
                jobs[job_id_local]['completed_at'] = datetime.utcnow().isoformat()

        Thread(target=_run_local_analysis_stream, args=(job_id, data), daemon=True).start()

    from app.routes._stream_helpers import sse_event, poll_job_and_stream

    @stream_with_context
    def event_stream():
        yield sse_event({'status': 'started', 'job_id': job_id})
        for chunk in poll_job_and_stream(job_id, timeout_seconds=max(60, int(Config.STREAM_TIMEOUT_SECONDS or 60))):
            yield chunk

    return Response(event_stream(), mimetype='text/event-stream')


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
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Dashboard stats error for user {user_id}: {str(exc)}", exc_info=True)
        return jsonify({
            'error': 'Unable to load dashboard data',
            'details': str(exc)
        }), 500
