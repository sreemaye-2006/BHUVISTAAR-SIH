import os
from pydantic_settings import BaseSettings

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_BASE_DIR, ".env")


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test_temp.db"
    SECRET_KEY: str = "bhuvistaar-super-secret-key-development-2026"

    UPLOAD_DIR: str = os.path.join(_BASE_DIR, "uploads")
    PROCESSED_DIR: str = os.path.join(_BASE_DIR, "processed")
    EXPORT_DIR: str = os.path.join(_BASE_DIR, "exports")

    # Redis/Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = [_ENV_PATH, ".env"]


settings = Settings()