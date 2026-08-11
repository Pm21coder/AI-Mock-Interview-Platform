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
    mongo.init_app(app)
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
        return {'status': 'ok'}, 200

    return app
