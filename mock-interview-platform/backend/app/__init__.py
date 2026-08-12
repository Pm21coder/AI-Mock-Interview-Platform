from flask import Flask
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_socketio import SocketIO

from app.config import Config

mongo = PyMongo()
socketio = SocketIO(cors_allowed_origins='*')


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

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
        except Exception as exc:
            app.config['MONGO_AVAILABLE'] = False
            app.logger.warning('MongoDB is unavailable after init; starting in guest mode: %s', exc)
    except Exception as exc:
        app.config['MONGO_AVAILABLE'] = False
        app.logger.warning('MongoDB init failed; starting in guest mode: %s', exc)
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
