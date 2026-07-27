import os
from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SUPPORTED_PROVIDERS = frozenset({"mock", "ollama"})
_SUPPORTED_OCR_PROVIDERS = frozenset({"mock", "local"})
_SUPPORTED_FIELD_DETECTION_PROVIDERS = frozenset({"mock", "local"})


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

    # Document Upload & Analysis
    DOCUMENT_UPLOAD_MAX_BYTES: int = 10485760
    DOCUMENT_UPLOAD_MAX_PAGES: int = 20
    DOCUMENT_EXPIRATION_HOURS: int = 24
    DOCUMENT_STORAGE_PATH: str = "/tmp/ai-form-assistant/documents"
    DOCUMENT_ANALYSIS_VERSION: int = 1
    DOCUMENT_TEXT_SAMPLE_LIMIT: int = 5000

    # OCR
    OCR_PROVIDER: str = "mock"
    OCR_EXPIRATION_HOURS: int = 24
    OCR_RENDER_STORAGE_PATH: str = "/tmp/ai-form-assistant/ocr-render"
    OCR_RENDER_DPI: int = 300
    OCR_TIMEOUT_SECONDS: int = 120

    # Dynamic Field Detection
    FIELD_DETECTION_PROVIDER: str = "mock"
    FIELD_DETECTION_ANALYSIS_VERSION: int = 1

    # AI Provider
    AI_PROVIDER: str = "mock"
    AI_ALLOW_MOCK_FALLBACK: bool = False

    # Ollama
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "qwen3:4b"
    # 120s gives a local CPU-bound Ollama instance enough headroom for a
    # cold model load plus generation; a warm qwen3:4b call with thinking
    # disabled typically completes in a few seconds.
    OLLAMA_REQUEST_TIMEOUT_SECONDS: int = 120
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

    @model_validator(mode="after")
    def validate_document_settings(self) -> "Settings":
        if self.DOCUMENT_UPLOAD_MAX_BYTES <= 0:
            raise ValueError("DOCUMENT_UPLOAD_MAX_BYTES must be a positive integer.")
        if self.DOCUMENT_UPLOAD_MAX_PAGES <= 0:
            raise ValueError("DOCUMENT_UPLOAD_MAX_PAGES must be a positive integer.")
        if self.DOCUMENT_EXPIRATION_HOURS <= 0:
            raise ValueError("DOCUMENT_EXPIRATION_HOURS must be a positive integer.")
        if not self.DOCUMENT_STORAGE_PATH:
            raise ValueError("DOCUMENT_STORAGE_PATH must not be empty.")
        try:
            os.makedirs(self.DOCUMENT_STORAGE_PATH, exist_ok=True)
        except Exception as e:
            raise ValueError(
                f"DOCUMENT_STORAGE_PATH '{self.DOCUMENT_STORAGE_PATH}' is not writable: {str(e)}"
            ) from e
        return self

    @model_validator(mode="after")
    def validate_ocr_settings(self) -> "Settings":
        if self.OCR_PROVIDER not in _SUPPORTED_OCR_PROVIDERS:
            raise ValueError(
                f"Unknown OCR_PROVIDER '{self.OCR_PROVIDER}'. "
                f"Supported values: {sorted(_SUPPORTED_OCR_PROVIDERS)}"
            )
        if self.OCR_EXPIRATION_HOURS <= 0:
            raise ValueError("OCR_EXPIRATION_HOURS must be a positive integer.")
        if self.OCR_RENDER_DPI <= 0:
            raise ValueError("OCR_RENDER_DPI must be a positive integer.")
        if self.OCR_TIMEOUT_SECONDS <= 0:
            raise ValueError("OCR_TIMEOUT_SECONDS must be a positive integer.")
        if not self.OCR_RENDER_STORAGE_PATH:
            raise ValueError("OCR_RENDER_STORAGE_PATH must not be empty.")
        try:
            os.makedirs(self.OCR_RENDER_STORAGE_PATH, exist_ok=True)
        except Exception as e:
            raise ValueError(
                f"OCR_RENDER_STORAGE_PATH '{self.OCR_RENDER_STORAGE_PATH}' is not writable: {str(e)}"
            ) from e
        return self

    @model_validator(mode="after")
    def validate_field_detection_settings(self) -> "Settings":
        if self.FIELD_DETECTION_PROVIDER not in _SUPPORTED_FIELD_DETECTION_PROVIDERS:
            raise ValueError(
                f"Unknown FIELD_DETECTION_PROVIDER '{self.FIELD_DETECTION_PROVIDER}'. "
                f"Supported values: {sorted(_SUPPORTED_FIELD_DETECTION_PROVIDERS)}"
            )
        if self.FIELD_DETECTION_ANALYSIS_VERSION <= 0:
            raise ValueError(
                "FIELD_DETECTION_ANALYSIS_VERSION must be a positive integer."
            )
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
