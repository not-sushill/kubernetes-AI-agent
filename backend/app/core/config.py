from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "AI Kubernetes Troubleshooting Agent"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = (
        "AI-powered Kubernetes Investigation and Troubleshooting Platform"
    )

    ENVIRONMENT: str = Field(default="development")

    DEBUG: bool = True

    HOST: str = "127.0.0.1"

    PORT: int = 8000

    API_PREFIX: str = "/api"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    LOG_LEVEL: str = "INFO"

    LOG_DIRECTORY: str = "logs"

    LOG_ROTATION: str = "10 MB"

    LOG_RETENTION: str = "30 days"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    DATABASE_URL: str = (
        f"sqlite:///{(BASE_DIR / 'ai_kubernetes_agent.db').as_posix()}"
    )

    # ------------------------------------------------------------------
    # Docker
    # ------------------------------------------------------------------

    PROJECT_NAME: str = "ai-kubernetes-agent"

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------

    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    # ------------------------------------------------------------------
    # AI / Ollama
    # ------------------------------------------------------------------

    AI_DIAGNOSIS_ENABLED: bool = False

    AI_PROVIDER: str = "ollama"

    OLLAMA_BASE_URL: str = "http://localhost:11434"

    OLLAMA_MODEL: str = "gemma3:4b"
    # ------------------------------------------------------------------
    # Pydantic Configuration
    # ------------------------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in {"debug", "development"}:
                return True

            if normalized in {"release", "production", "prod"}:
                return False

        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
