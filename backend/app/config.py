import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "postgresql://purchasing_agent:purchasing_agent_dev@localhost:5432/purchasing_agent"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Fallback to os.environ if not populated by pydantic BaseSettings
    if not settings.gemini_api_key:
        settings.gemini_api_key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    if os.getenv("GEMINI_MODEL"):
        settings.gemini_model = os.getenv("GEMINI_MODEL")
    return settings
