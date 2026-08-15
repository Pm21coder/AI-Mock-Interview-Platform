import os

from flask import Flask
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_socketio import SocketIO
from flask_compress import Compress

from app.config import Config

mongo = PyMongo()
socketio = SocketIO(cors_allowed_origins='*')
compress = Compress()


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

    # Security check: ensure secret keys are not public defaults in production
    _check_secret_keys(app)

    CORS(app)
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
        app.config['MONGO_AVAILABLE'] = False
        if cloud_uri:
            app.logger.warning(
                '⚠ MongoDB connection failed for both local and Atlas targets; starting in guest mode. '
                'For local development, start the project MongoDB container or set USE_ATLAS_MONGO=true to allow remote Atlas access.'
            )
        else:
            app.logger.warning('⚠ MongoDB unavailable; starting in guest mode.')
    socketio.init_app(app)
    compress.init_app(app)  # Enable gzip compression for all responses

    from app.routes.interview import interview_bp
    from app.routes.feedback import feedback_bp
    from app.routes.auth import auth_bp
    from app.routes.resume import resume_bp
    from app.routes.subscription import subscription_bp
    from app.socket_events import register_socket_handlers

    app.register_blueprint(interview_bp, url_prefix='/api/interview')
    app.register_blueprint(feedback_bp, url_prefix='/api/feedback')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(resume_bp, url_prefix='/api/resume')
    app.register_blueprint(subscription_bp, url_prefix='/api/subscription')

    # Register Socket.IO event handlers for real-time dashboard updates.
    register_socket_handlers()

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

    return app
