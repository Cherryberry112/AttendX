import os
import json
import flask_jwt_extended
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from config import config

# Monkey-patch flask_jwt_extended.get_jwt_identity to auto-decode JSON string identities
original_get_jwt_identity = flask_jwt_extended.get_jwt_identity

def patched_get_jwt_identity():
    identity = original_get_jwt_identity()
    if isinstance(identity, str):
        try:
            return json.loads(identity)
        except json.JSONDecodeError:
            return identity
    return identity

flask_jwt_extended.get_jwt_identity = patched_get_jwt_identity

db = SQLAlchemy()
jwt = JWTManager()

@jwt.user_identity_loader
def user_identity_lookup(identity):
    if isinstance(identity, (dict, list)):
        return json.dumps(identity)
    return str(identity)

def create_app(env=None):
    if env is None:
        env = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[env])
    
    # Check if database host is resolvable (supports offline / IPv4-only local development fallback)
    db_url = app.config.get("DATABASE_URL")
    fallback_to_sqlite = False
    if not db_url:
        fallback_to_sqlite = True
    else:
        import urllib.parse
        import socket
        try:
            parsed = urllib.parse.urlparse(db_url)
            if parsed.hostname:
                socket.gethostbyname(parsed.hostname)
        except Exception:
            fallback_to_sqlite = True

    if fallback_to_sqlite:
        print("[WARNING] Supabase database host is unreachable (possibly due to local IPv4-only network constraints). Falling back to local SQLite database (attendx_dev.db).")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///attendx_dev.db"
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = app.config["JWT_SECRET_KEY"]

    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    db.init_app(app)
    jwt.init_app(app)

    # Auto-create tables (required for SQLite local setup)
    with app.app_context():
        import models
        db.create_all()
        # Seed default admin if it doesn't exist
        from models import User
        admin_email = "admin@attendx.com"
        if not User.query.filter_by(email=admin_email).first():
            import bcrypt
            hashed = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt()).decode()
            admin = User(
                type="admin",
                email=admin_email,
                username="System Admin",
                password=hashed,
            )
            db.session.add(admin)
            db.session.commit()
            print("[INFO] Seeded default system admin (admin@attendx.com / Admin@1234) in local database.")

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
