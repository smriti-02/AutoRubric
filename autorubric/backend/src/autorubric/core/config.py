import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(_ENV_PATH)

class Config:
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/autorubric")
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    SECRET_KEY = os.environ.get("SECRET_KEY", "supersecret")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "$2b$12$XnPs0wsVFTB9pj5EANy8wuW7NGlE2TyUPfqMsLotDLj7M6KBevWsi") # default 'admin'
    JWT_SECRET = os.environ.get("JWT_SECRET", "jwtsecret")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    STAGE_EXTRACTION_MODE = os.environ.get("STAGE_EXTRACTION_MODE", "real")
    STAGE_SEGMENTATION_MODE = os.environ.get("STAGE_SEGMENTATION_MODE", "real")
    STAGE_RETRIEVAL_MODE = os.environ.get("STAGE_RETRIEVAL_MODE", "real")
    STAGE_EVALUATION_MODE = os.environ.get("STAGE_EVALUATION_MODE", "real")
    STAGE_AUDIT_MODE = os.environ.get("STAGE_AUDIT_MODE", "real")
    STAGE_ANNOTATION_MODE = os.environ.get("STAGE_ANNOTATION_MODE", "real")
    
    EVALUATOR_BACKEND = os.environ.get("EVALUATOR_BACKEND", "cpu") # mock, cpu, gpu
    UPLOADS_DIR = os.environ.get("UPLOADS_DIR", "/app/uploads")


config = Config()
