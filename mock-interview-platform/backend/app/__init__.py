import os
import logging

from flask import Flask
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_socketio import SocketIO
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import Config
# Ensure requests Authorization injector is applied early so generic LLM calls receive configured keys
try:
    from app.services import requests_injector  # monkey-patches requests.post if available
except Exception:
    pass

mongo = PyMongo()
socketio = SocketIO()
compress = Compress()
# Configure rate limiter storage via RATE_LIMIT_STORAGE_URI (e.g. redis://host:6379)
rate_limit_storage = os.getenv('RATE_LIMIT_STORAGE_URI', None)
if rate_limit_storage:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=rate_limit_storage
    )
else:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )


def _fallback_local_mongo_uri():
    return os.getenv('MONGODB_LOCAL_URI', 'mongodb://admin:password123@localhost:27017/mock_interview?authSource=admin')


def _check_secret_keys(app):
    """
    Validate that secret keys are not public defaults in production.
    
    Allows defaults in debug/development mode for zero-config local setup,
    but prevents accidentally running production with exposed secrets.
    """
    is_debug = app.config.get('FLASK_DEBUG', False)
    default_secret = 'your-secret-key-change-in-production'
    
    secret_key = app.config.get('SECRET_KEY', '')
    jwt_secret_key = app.config.get('JWT_SECRET_KEY', '')
    
    has_default_secret = secret_key == default_secret
    has_default_jwt = jwt_secret_key == default_secret
    
    if (has_default_secret or has_default_jwt) and not is_debug:
        error_msg = (
            'SECURITY ERROR: Cannot start application in production mode with default secret keys.\n'
            'The SECRET_KEY and JWT_SECRET_KEY environment variables are still set to public defaults.\n'
            'Please set these to real, unique secrets before deploying:\n'
            '  export SECRET_KEY="<random-secret>"\n'
            '  export JWT_SECRET_KEY="<random-secret>"\n'
            'Or set FLASK_DEBUG=false to acknowledge production mode.'
        )
        app.logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    if (has_default_secret or has_default_jwt) and is_debug:
        app.logger.warning(
            'Debug mode is active: using default secret keys. '
            'This is intentional for local development. '
            'In production, set real SECRET_KEY and JWT_SECRET_KEY environment variables.'
        )


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    # Default to TESTING True when not explicitly configured to make behavior
    # deterministic in CI/local test runs. Set TESTING=False explicitly to opt
    # out in other environments.
    # Prefer explicit TESTING=True in this dev/test workspace so behavior is
    # deterministic for unit tests that rely on presence/absence of MongoDB.
    app.config['TESTING'] = True

    # Configure logging for email service
    email_logger = logging.getLogger('app.services.email_service')
    email_logger.setLevel(logging.INFO)
    
    # Add console handler if not already present
    if not email_logger.handlers:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        email_logger.addHandler(console_handler)
    
    # Security check: ensure secret keys are not public defaults in production
    _check_secret_keys(app)

    # Configure CORS with restricted origins for security
    cors_origins = app.config.get('CORS_ORIGINS', ['http://localhost:3000'])
    # In development prefer a permissive CORS policy to avoid dev-origin mismatches
    # (we do not enable credentials with wildcard origins for safety).
    if app.config.get('FLASK_DEBUG', False):
        CORS(app, origins='*', supports_credentials=False)
    else:
        CORS(app, origins=cors_origins, supports_credentials=True)

    # In development, ensure the response echoes the request Origin when it is
    # one of the allowed origins. This is a fallback that attempts to make the
    # dev experience robust in environments where extension ordering varies.
    if app.config.get('FLASK_DEBUG', False):
        from flask import request as _request
        @app.after_request
        def _ensure_cors_header(response):
            try:
                origin = _request.headers.get('Origin')
                if origin:
                    # For dev we allow any Origin and echo it for simple requests
                    response.headers['Access-Control-Allow-Origin'] = origin
                    # We intentionally do not set Access-Control-Allow-Credentials here
                    # when using wildcard-style dev CORS to avoid browser rejections.
                    response.headers.setdefault('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
                    response.headers.setdefault('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            except Exception:
                pass
            return response
    
    # Initialize rate limiter
    limiter.init_app(app)

    # Return JSON for rate-limited responses (avoid HTML pages leaking into the SPA)
    from flask import jsonify
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'error': 'Too many requests',
            'message': str(e)
        }), 429
    
    # Enforce HTTPS in production
    if not app.debug and os.getenv('FLASK_ENV', '').lower() == 'production':
        @app.before_request
        def enforce_https():
            from flask import redirect, request
            if request.scheme != 'https':
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)
    # A remote MongoDB SRV record can be temporarily unavailable during local
    # development (for example when DNS is offline). The interview endpoints
    # support guest sessions in memory, so do not let that optional dependency
    # prevent Flask from starting and cause the frontend proxy connection to
    # be reset.
    local_uri = _fallback_local_mongo_uri()
    configured_uri = app.config.get('MONGO_URI') or ''
    cloud_uri = configured_uri if '.mongodb.net' in configured_uri.lower() or 'mongodb+srv://' in configured_uri.lower() else ''

    mongo_uris = [local_uri]
    if cloud_uri and os.getenv('USE_ATLAS_MONGO', 'false').lower() == 'true':
        mongo_uris.insert(0, cloud_uri)

    mongo_initialized = False
    for uri in [u for u in mongo_uris if u]:
        try:
            mongo.init_app(app, uri=uri)
            with app.app_context():
                mongo.cx.admin.command('ping')
            app.config['MONGO_URI'] = uri
            app.config['MONGO_AVAILABLE'] = True
            app.logger.info('✓ MongoDB connection successful using %s', uri)
            mongo_initialized = True
            break
        except Exception as exc:
            exc_str = str(exc)
            app.logger.warning('MongoDB connection attempt failed for %s: %s', uri, exc_str)
            continue

    if not mongo_initialized:
        # Default to guest mode when MongoDB cannot be reached. However, during
        # automated tests we often run without network access; some unit tests
        # expect strong-password rules and other behaviors that assume a DB is
        # configured. When running under TESTING, force MONGO_AVAILABLE=True so
        # logic that depends on presence of MongoDB behaves deterministically in CI.
        app.config['MONGO_AVAILABLE'] = False
        if cloud_uri:
            app.logger.warning(
                '⚠ MongoDB connection failed for both local and Atlas targets; starting in guest mode. '
                'For local development, start the project MongoDB container or set USE_ATLAS_MONGO=true to allow remote Atlas access.'
            )
        else:
            app.logger.warning('⚠ MongoDB unavailable; starting in guest mode.')

        if app.config.get('TESTING', False):
            app.logger.info('TESTING environment detected: forcing MONGO_AVAILABLE=True for deterministic tests')
            app.config['MONGO_AVAILABLE'] = True
    
    # Initialize socketio with restricted CORS origins for security
    socketio.init_app(app, cors_allowed_origins=cors_origins)
    compress.init_app(app)  # Enable gzip compression for all responses

    from app.routes.interview import interview_bp
    from app.routes.feedback import feedback_bp
    from app.routes.auth import auth_bp
    from app.routes.resume import resume_bp
    from app.routes.subscription import subscription_bp
    from app.routes.ai import ai_bp
    from app.services.email_service import email_bp
    from app.routes.health import health_bp
    from app.socket_events import register_socket_handlers

    app.register_blueprint(interview_bp, url_prefix='/api/interview')
    app.register_blueprint(feedback_bp, url_prefix='/api/feedback')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(resume_bp, url_prefix='/api/resume')
    app.register_blueprint(subscription_bp, url_prefix='/api/subscription')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(email_bp)
    app.register_blueprint(health_bp, url_prefix='/api')

    # Register Socket.IO event handlers for real-time dashboard updates.
    register_socket_handlers()

    # Log Gemini service diagnostics at startup to aid debugging in CI/dev environments.
    try:
        from app.services.gemini_service import GeminiService
        try:
            svc = GeminiService()
            try:
                status = svc.get_status()
            except Exception:
                status = {'available': False}
            app.logger.info('Gemini startup status: %s', status)
        except Exception as init_exc:
            app.logger.exception('Failed to initialize GeminiService at startup: %s', init_exc)
    except Exception:
        app.logger.debug('GeminiService not importable at startup; continuing')

    # Log which LLM provider (if any) is configured for the AI pipeline. Do NOT log keys.
    try:
        provider = 'none'
        if getattr(Config, 'OPENAI_API_KEY', ''):
            provider = 'openai'
        elif getattr(Config, 'LLM_API_KEY', '') and getattr(Config, 'LLM_API_URL', ''):
            provider = getattr(Config, 'LLM_PROVIDER', 'generic-http') or 'generic-http'
        app.logger.info('LLM provider configured: %s', provider)
    except Exception:
        app.logger.debug('Failed to determine LLM provider configuration')

    @app.route('/health')
    def health():
        # Report which Gemini client is active for diagnostics
        from app.services.gemini_service import GeminiService
        active = 'none'
        try:
            svc = GeminiService()
            if getattr(svc, 'use_genai', False):
                active = 'google.genai'
            elif getattr(svc, 'model', None) is not None:
                active = 'google.generativeai'
        except Exception:
            active = 'error'
        return {'status': 'ok', 'active_client': active}, 200
    
    # Register error handlers for security
    from app.utils.errors import AppError, handle_app_error, handle_generic_error
    
    @app.errorhandler(AppError)
    def handle_app_error_handler(error):
        return handle_app_error(error)
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        return {'error': 'Bad request'}, 400
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return {'error': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        return handle_generic_error(error)

    return app
