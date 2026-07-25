import os
from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SUPPORTED_PROVIDERS = frozenset({"mock", "ollama"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str | None = None

    FORM_SESSION_TTL_HOURS: int = 24
    SESSION_TOKEN_SECRET: str | None = None

    PDF_EXPORT_DIRECTORY: str = "/tmp/ai-form-assistant/exports"
    PDF_EXPORT_TTL_HOURS: int = 24
    PDF_TEMPLATE_KEY: str = "basic-registration-v1"

    # AI Provider
    AI_PROVIDER: str = "mock"
    AI_ALLOW_MOCK_FALLBACK: bool = False

    # Ollama
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "qwen3:4b"
    OLLAMA_REQUEST_TIMEOUT_SECONDS: int = 60
    OLLAMA_MAX_RETRIES: int = 1
    OLLAMA_CACHE_ENABLED: bool = False

    # Question Catalog
    QUESTION_ALLOW_PENDING_REUSE: bool = False
    QUESTION_AI_TRANSLATION_ENABLED: bool = True
    QUESTION_AI_GENERATION_ENABLED: bool = True
    QUESTION_ADMIN_API_ENABLED: bool = False

    @model_validator(mode="after")
    def validate_session_secret(self) -> "Settings":
        if not self.SESSION_TOKEN_SECRET:
            self.SESSION_TOKEN_SECRET = "unsafe-dev-fallback-secret-key-12345678"
        return self

    @model_validator(mode="after")
    def validate_ai_provider(self) -> "Settings":
        if self.AI_PROVIDER not in _SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unknown AI_PROVIDER '{self.AI_PROVIDER}'. "
                f"Supported values: {sorted(_SUPPORTED_PROVIDERS)}"
            )
        return self

    @model_validator(mode="after")
    def validate_pdf_settings(self) -> "Settings":
        if self.PDF_EXPORT_TTL_HOURS <= 0:
            raise ValueError("PDF_EXPORT_TTL_HOURS must be a positive integer.")
        if not self.PDF_EXPORT_DIRECTORY:
            raise ValueError("PDF_EXPORT_DIRECTORY must not be empty.")
        try:
            os.makedirs(self.PDF_EXPORT_DIRECTORY, exist_ok=True)
        except Exception as e:
            raise ValueError(
                f"PDF_EXPORT_DIRECTORY '{self.PDF_EXPORT_DIRECTORY}' is not writable: {str(e)}"
            ) from e
        return self

    @model_validator(mode="before")
    @classmethod
    def assemble_db_connection(cls, data: Any) -> Any:
        if isinstance(data, dict):
            db_url = data.get("DATABASE_URL")
            if not db_url:
                user = data.get("POSTGRES_USER", "postgres")
                password = data.get("POSTGRES_PASSWORD", "postgres")
                host = data.get("POSTGRES_HOST", "localhost")
                port = data.get("POSTGRES_PORT", 5432)
                db = data.get("POSTGRES_DB", "postgres")
                data["DATABASE_URL"] = (
                    f"postgresql://{user}:{password}@{host}:{port}/{db}"
                )
        return data


settings = Settings()
