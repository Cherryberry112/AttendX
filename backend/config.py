import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend dir first, then fall back to repo root
_here = Path(__file__).parent          # …/backend/
load_dotenv(_here / ".env")            # …/backend/.env  (Render / explicit)
load_dotenv(_here.parent / ".env")     # …/.env          (local root)

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
