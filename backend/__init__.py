import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from config import config

db = SQLAlchemy()
jwt = JWTManager()

def create_app(env=None):
    if env is None:
        env = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[env])
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = app.config["JWT_SECRET_KEY"]

    CORS(app, origins=[app.config["FRONTEND_URL"]], supports_credentials=True)
    db.init_app(app)
    jwt.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.teacher import teacher_bp
    from routes.student import student_bp
    from routes.admin import admin_bp
    from routes.face import face_bp

    app.register_blueprint(auth_bp,    url_prefix="/api/auth")
    app.register_blueprint(teacher_bp, url_prefix="/api/teacher")
    app.register_blueprint(student_bp, url_prefix="/api/student")
    app.register_blueprint(admin_bp,   url_prefix="/api/admin")
    app.register_blueprint(face_bp,    url_prefix="/api/face")

    @app.route("/api/health")
    def health():
        return {"status": "ok", "service": "AttendX API"}

    return app
