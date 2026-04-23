from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_socketio import SocketIO, join_room
from config import Config

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    socketio.init_app(app, cors_allowed_origins='*', async_mode='threading', logger=False, engineio_logger=False)
    
    from app.routes import auth, users, workers, categories, jobs, payments, reviews, sync, sms, ussd, verification, notifications, job_updates, tracking, africastalking, escrow
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(workers.bp)
    app.register_blueprint(categories.bp)
    app.register_blueprint(jobs.bp)
    app.register_blueprint(payments.bp)
    app.register_blueprint(reviews.bp)
    app.register_blueprint(sync.bp)
    app.register_blueprint(sms.bp)
    app.register_blueprint(ussd.bp)
    app.register_blueprint(verification.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(job_updates.bp)
    app.register_blueprint(tracking.bp)
    app.register_blueprint(africastalking.bp)
    app.register_blueprint(escrow.bp)

    @socketio.on('join')
    def on_join(data):
        """Client emits {token} → server validates and joins room = user_id."""
        from flask_jwt_extended import decode_token
        try:
            token_data = decode_token(data.get('token', ''))
            user_id = token_data['sub']
            join_room(user_id)
        except Exception:
            pass  # invalid token — silently ignore

    return app
