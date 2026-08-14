from flask import Flask
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_socketio import SocketIO

from app.config import Config

mongo = PyMongo()
socketio = SocketIO(cors_allowed_origins='*')


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
    try:
        mongo.init_app(app)
        try:
            with app.app_context():
                mongo.cx.admin.command('ping')
            app.config['MONGO_AVAILABLE'] = True
            app.logger.info('✓ MongoDB connection successful')
        except Exception as exc:
            app.config['MONGO_AVAILABLE'] = False
            exc_str = str(exc)
            if 'timed out' in exc_str.lower() or 'timeout' in exc_str.lower():
                app.logger.warning(
                    '⚠ MongoDB SRV connection timeout (DNS/network issue). '
                    'Running in guest mode. Increase MONGO_CONNECT_TIMEOUT_MS if needed.'
                )
            else:
                app.logger.warning(
                    '⚠ MongoDB unavailable; starting in guest mode. Error: %s', exc
                )
    except Exception as exc:
        app.config['MONGO_AVAILABLE'] = False
        app.logger.warning('⚠ MongoDB initialization failed; starting in guest mode: %s', exc)
    socketio.init_app(app)

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
