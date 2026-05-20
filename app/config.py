from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "HR Intelligence Platform"
    app_env: str = "development"
    database_url: str = "sqlite:///./hr_agent_engine.db"

    llm_provider: str = "groq"
    llm_api_key: str | None = None
    llm_model: str = "llama-3.1-8b-instant"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_timeout_seconds: int = 20
    llm_max_retries: int = 2

    intent_confidence_threshold: float = 0.65
    stm_limit_per_user: int = 10
    ltm_significance_threshold: float = 0.75

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()