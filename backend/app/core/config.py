import os
from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SUPPORTED_PROVIDERS = frozenset({"mock", "ollama", "gemini"})
_SUPPORTED_OCR_PROVIDERS = frozenset({"mock", "local"})
_SUPPORTED_FIELD_DETECTION_PROVIDERS = frozenset({"mock", "local", "azure", "hybrid"})
_SUPPORTED_TRANSLATION_PROVIDERS = frozenset({"mock", "ollama", "azure", "gemini"})
_SUPPORTED_STORAGE_PROVIDERS = frozenset({"local", "s3"})
_SUPPORTED_EMAIL_PROVIDERS = frozenset({"mock", "postmark"})


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

    # Which environment this process is running in. Used to keep
    # development-only fixtures (the signature demo form) out of production,
    # where a test form appearing in a public list would be a real problem.
    ENVIRONMENT: str = "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("production", "prod")

    # Application log level. Uvicorn does not configure our loggers, so
    # app/main.py sets this up explicitly (see the basicConfig call there).
    LOG_LEVEL: str = "INFO"

    # How many texts go into one batched AI translation request. Small local
    # models follow a long multi-item instruction less reliably, so the work
    # is chunked rather than sent as a single request; 12 kept every item
    # correctly mapped on the reference document while cutting a 28-call
    # sequence to 3 calls. Raise only with measurement.
    AI_TRANSLATION_BATCH_SIZE: int = 12

    # How many batched translation requests may be in flight at once. Bounded
    # on purpose: a single local Ollama instance serializes work beyond its
    # own parallelism, so an unbounded fan-out would convert latency into
    # timeouts rather than speed. 3 covers the reference document's chunks in
    # one wave.
    AI_TRANSLATION_CONCURRENCY: int = 3

    # Which provider translates display text (field labels, choice option
    # labels). Separate from AI_PROVIDER on purpose: translation is a
    # different capability from language understanding, and a dedicated
    # service does it faster and more predictably than a local LLM.
    TRANSLATION_PROVIDER: str = "ollama"
    # Used only when the primary provider fails, and must differ from it.
    # Defaults to "none" because the default primary is already Ollama; the
    # intended production pairing is azure + ollama. Source text remains the
    # final fallback either way, so a document is never blocked.
    TRANSLATION_FALLBACK_PROVIDER: str = "none"

    # Azure Translator. Backend-only; never exposed to the frontend.
    # Validated (fail fast) only when Azure is actually selected — the
    # mock/ollama providers must keep working with none of this set.
    AZURE_TRANSLATOR_ENABLED: bool = False
    AZURE_TRANSLATOR_ENDPOINT: str = "https://api.cognitive.microsofttranslator.com"
    AZURE_TRANSLATOR_API_KEY: str | None = None
    # Required for a regional (non-global) resource; Azure rejects the
    # request without it.
    AZURE_TRANSLATOR_REGION: str | None = None
    AZURE_TRANSLATOR_API_VERSION: str = "3.0"
    AZURE_TRANSLATOR_TIMEOUT_SECONDS: int = 30
    AZURE_TRANSLATOR_MAX_RETRIES: int = 1
    # Azure's documented per-request limit is 1000 elements / 50,000 chars;
    # 50 keeps a single request well inside both while still collapsing a
    # whole document into one call.
    AZURE_TRANSLATOR_MAX_BATCH_SIZE: int = 50

    FORM_SESSION_TTL_HOURS: int = 24
    SESSION_TOKEN_SECRET: str | None = None

    PDF_EXPORT_DIRECTORY: str = "/tmp/ai-form-assistant/exports"
    PDF_EXPORT_TTL_HOURS: int = 24
    PDF_TEMPLATE_KEY: str = "basic-registration-v1"

    # Document Upload & Analysis
    DOCUMENT_UPLOAD_MAX_BYTES: int = 10485760
    DOCUMENT_UPLOAD_MAX_PAGES: int = 20
    DOCUMENT_UPLOAD_MAX_IMAGE_PIXELS: int = 40_000_000
    DOCUMENT_EXPIRATION_HOURS: int = 24
    DOCUMENT_STORAGE_PATH: str = "/tmp/ai-form-assistant/documents"
    DOCUMENT_ANALYSIS_VERSION: int = 1
    DOCUMENT_TEXT_SAMPLE_LIMIT: int = 5000

    # Private Object & File Storage (Phase S1-01)
    STORAGE_PROVIDER: str = "local"
    S3_ENDPOINT_URL: str | None = None
    S3_REGION: str = "eu-central-1"
    S3_BUCKET: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_KEY_PREFIX: str = ""
    S3_TIMEOUT_SECONDS: float = 30.0

    # OCR
    OCR_PROVIDER: str = "mock"
    OCR_EXPIRATION_HOURS: int = 24
    OCR_RENDER_STORAGE_PATH: str = "/tmp/ai-form-assistant/ocr-render"
    OCR_RENDER_DPI: int = 300
    OCR_TIMEOUT_SECONDS: int = 120

    # Background Jobs & Rate Limiting (Phase S1-03)
    REDIS_URL: str | None = None
    JOB_EXECUTION_MODE: str = "inline"
    JOB_EXPIRATION_HOURS: int = 24
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = 30
    RATE_LIMIT_PREPARE_PER_MINUTE: int = 30
    RATE_LIMIT_AUTH_PER_MINUTE: int = 15

    # Dynamic Field Detection
    FIELD_DETECTION_PROVIDER: str = "mock"
    FIELD_DETECTION_ANALYSIS_VERSION: int = 1

    # Automatic upload-to-questions confidence routing (Phase 13). Deterministic
    # thresholds only — Ollama is never allowed to decide auto-confirmation.
    # A candidate's confidence >= FIELD_AUTO_CONFIRM_THRESHOLD is auto-confirmed
    # (high confidence). Between FIELD_CLARIFICATION_THRESHOLD (inclusive) and
    # FIELD_AUTO_CONFIRM_THRESHOLD (exclusive) is "medium" confidence: still
    # usable for automatic question generation, but flagged for later admin
    # review rather than silently marked confirmed. Below
    # FIELD_CLARIFICATION_THRESHOLD is "low" confidence and is never used to
    # generate a question automatically.
    FIELD_AUTO_CONFIRM_THRESHOLD: float = 0.75
    FIELD_CLARIFICATION_THRESHOLD: float = 0.4
    # Azure Document Intelligence (Phase 14) — a second, opt-in
    # field-detection provider. Backend-only: the API key must never be
    # exposed to the frontend, never logged, and never returned in an API
    # response. Credentials are only required when
    # FIELD_DETECTION_PROVIDER=azure; the local/mock providers must keep
    # working with all of these unset.
    AZURE_DOCUMENT_INTELLIGENCE_ENABLED: bool = False
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str | None = None
    AZURE_DOCUMENT_INTELLIGENCE_API_KEY: str | None = None
    AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID: str = "prebuilt-layout"
    AZURE_DOCUMENT_INTELLIGENCE_API_VERSION: str = "2024-11-30"
    AZURE_DOCUMENT_INTELLIGENCE_TIMEOUT_SECONDS: int = 120
    AZURE_DOCUMENT_INTELLIGENCE_MAX_RETRIES: int = 1

    # Hybrid local-first routing (Phase 16). The local pass always runs; Azure
    # is called only when the local result scores below the threshold. Both
    # limits are deterministic — no model participates in a spending decision.
    #
    # The threshold is a weighted quality score in 0-1 (see
    # app/field_detection/quality.py). 0.55 sits between the reference
    # documents: the German rental contract and the French employment form
    # score well above it locally, the Arabic form that collapsed to two
    # candidates scores far below.
    HYBRID_LOCAL_QUALITY_THRESHOLD: float = 0.55
    # A hard ceiling on what may be escalated. A long document is where an
    # automatic hosted call is most expensive and least likely to be intended,
    # so it is never escalated regardless of quality.
    HYBRID_MAX_ESCALATION_PAGES: int = 10
    # Coverage floors — how much of what the *document* offered has to be
    # accounted for. Separate from the quality score, which only sees the
    # output: five flawless candidates on a thirty-field form scored 0.83 and
    # were never escalated, because nothing in the score could see the
    # twenty-five that were missed. See app/field_detection/coverage.py.
    #
    # Each is compared on its own so the reported reason names the real gap:
    # unread labels and leaked checkboxes are different problems.
    HYBRID_MIN_LABEL_COVERAGE: float = 0.6
    HYBRID_MIN_MARK_COVERAGE: float = 0.75
    HYBRID_MIN_PAGE_COVERAGE: float = 0.75

    # "auto": review_status is assigned automatically per the thresholds above
    # and the normal-user upload flow generates questions without a manual
    # review step. "manual": preserves the exact Phase 11 behavior — every
    # detected field starts as pending_review and only an explicit reviewer
    # action (PATCH .../fields/{id}) can mark it confirmed. Debug/admin
    # tooling can always reach the Phase 11 review screen regardless of this
    # setting; this only controls the *normal-user* upload path's default.
    FIELD_DETECTION_REVIEW_MODE: str = "auto"

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

    # Google Gemini
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_REQUEST_TIMEOUT_SECONDS: int = 30
    GEMINI_MAX_RETRIES: int = 2

    # Question Catalog
    QUESTION_ALLOW_PENDING_REUSE: bool = False
    QUESTION_AI_TRANSLATION_ENABLED: bool = True
    QUESTION_AI_GENERATION_ENABLED: bool = True
    QUESTION_ADMIN_API_ENABLED: bool = False

    # User Accounts & Auth Sessions (Phase 12)
    AUTH_SECRET: str | None = None
    AUTH_SESSION_TTL_HOURS: int = 336  # 14 days
    AUTH_COOKIE_NAME: str = "auth_session"
    AUTH_COOKIE_SECURE: bool = False  # must be true in production (HTTPS)
    AUTH_COOKIE_SAMESITE: str = "lax"
    AUTH_CSRF_COOKIE_NAME: str = "csrf_token"
    AUTH_CSRF_HEADER_NAME: str = "X-CSRF-Token"
    PASSWORD_MIN_LENGTH: int = 10
    ADMIN_EMAILS: str = ""

    # Account Lifecycle Email & Profile Vault Encryption (Phase S2)
    EMAIL_PROVIDER: str = "mock"
    FRONTEND_PUBLIC_URL: str = "http://localhost:3003"
    POSTMARK_SERVER_TOKEN: str | None = None
    EMAIL_FROM_ADDRESS: str = "no-reply@formassistant.local"
    EMAIL_VERIFICATION_TTL_HOURS: int = 24
    PASSWORD_RESET_TTL_MINUTES: int = 60
    VAULT_ENCRYPTION_KEY: str | None = None

    # Stripe B2B/B2G Billing
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_PUBLISHABLE_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_AGENCY_PRO: str | None = None
    STRIPE_PRICE_ENTERPRISE: str | None = None
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    @property
    def admin_emails_set(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.ADMIN_EMAILS.split(",")
            if email.strip()
        }

    # Comma-separated list of frontend origins allowed to send credentialed
    # (cookie-bearing) requests. A wildcard cannot be combined with
    # credentials per the CORS spec, so this must be an explicit list now
    # that auth relies on cookies.
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3003"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_session_secret(self) -> "Settings":
        dev_fallback = "unsafe-dev-fallback-secret-key-12345678"
        if self.is_production:
            secret = (self.SESSION_TOKEN_SECRET or "").strip()
            if not secret or secret == dev_fallback or len(secret) < 32:
                raise ValueError(
                    "SESSION_TOKEN_SECRET must be explicitly set to a strong "
                    "secret (>= 32 characters) in production."
                )
        elif not self.SESSION_TOKEN_SECRET:
            self.SESSION_TOKEN_SECRET = dev_fallback
        return self

    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
        dev_auth_fallback = "unsafe-dev-fallback-auth-secret-key-12345678"
        if self.is_production:
            auth_secret = (self.AUTH_SECRET or "").strip()
            if (
                not auth_secret
                or auth_secret == dev_auth_fallback
                or len(auth_secret) < 32
            ):
                raise ValueError(
                    "AUTH_SECRET must be explicitly set to a strong secret "
                    "(>= 32 characters) in production."
                )
            if not self.AUTH_COOKIE_SECURE:
                raise ValueError("AUTH_COOKIE_SECURE must be true in production.")
        elif not self.AUTH_SECRET:
            self.AUTH_SECRET = dev_auth_fallback
        if self.AUTH_SESSION_TTL_HOURS <= 0:
            raise ValueError("AUTH_SESSION_TTL_HOURS must be a positive integer.")
        if self.AUTH_COOKIE_SAMESITE.lower() not in ("lax", "strict", "none"):
            raise ValueError("AUTH_COOKIE_SAMESITE must be one of: lax, strict, none.")
        if self.PASSWORD_MIN_LENGTH < 8:
            raise ValueError("PASSWORD_MIN_LENGTH must be at least 8.")
        email_provider = self.EMAIL_PROVIDER.strip().lower()
        if email_provider not in _SUPPORTED_EMAIL_PROVIDERS:
            raise ValueError(
                f"Unknown EMAIL_PROVIDER '{self.EMAIL_PROVIDER}'. "
                f"Supported values: {sorted(_SUPPORTED_EMAIL_PROVIDERS)}"
            )
        self.EMAIL_PROVIDER = email_provider
        if (
            email_provider == "postmark"
            and not (self.POSTMARK_SERVER_TOKEN or "").strip()
        ):
            raise ValueError(
                "POSTMARK_SERVER_TOKEN must be set when EMAIL_PROVIDER='postmark'."
            )
        if self.EMAIL_VERIFICATION_TTL_HOURS <= 0:
            raise ValueError("EMAIL_VERIFICATION_TTL_HOURS must be positive.")
        if self.PASSWORD_RESET_TTL_MINUTES <= 0:
            raise ValueError("PASSWORD_RESET_TTL_MINUTES must be positive.")
        if (
            self.is_production
            and self.VAULT_ENCRYPTION_KEY is not None
            and len(self.VAULT_ENCRYPTION_KEY.strip()) < 32
        ):
            raise ValueError(
                "VAULT_ENCRYPTION_KEY must be at least 32 characters when set in production."
            )
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
    def validate_translation_provider(self) -> "Settings":
        if self.TRANSLATION_PROVIDER not in _SUPPORTED_TRANSLATION_PROVIDERS:
            raise ValueError(
                f"Unknown TRANSLATION_PROVIDER '{self.TRANSLATION_PROVIDER}'. "
                f"Supported values: {sorted(_SUPPORTED_TRANSLATION_PROVIDERS)}"
            )
        fallback = self.TRANSLATION_FALLBACK_PROVIDER
        if fallback not in _SUPPORTED_TRANSLATION_PROVIDERS | {"none", ""}:
            raise ValueError(
                f"Unknown TRANSLATION_FALLBACK_PROVIDER '{fallback}'. Supported "
                f"values: {sorted(_SUPPORTED_TRANSLATION_PROVIDERS)} or 'none'."
            )
        if fallback == self.TRANSLATION_PROVIDER:
            raise ValueError(
                "TRANSLATION_FALLBACK_PROVIDER must differ from "
                "TRANSLATION_PROVIDER; falling back to the provider that just "
                "failed only doubles the latency of a failure."
            )

        if self.AZURE_TRANSLATOR_MAX_BATCH_SIZE < 1:
            raise ValueError("AZURE_TRANSLATOR_MAX_BATCH_SIZE must be at least 1.")
        if self.AZURE_TRANSLATOR_TIMEOUT_SECONDS < 1:
            raise ValueError("AZURE_TRANSLATOR_TIMEOUT_SECONDS must be at least 1.")
        if self.AZURE_TRANSLATOR_MAX_RETRIES < 0:
            raise ValueError("AZURE_TRANSLATOR_MAX_RETRIES must not be negative.")

        # Fail fast only when Azure is reachable from configuration — either
        # as the primary provider or as the configured fallback.
        azure_selected = "azure" in (
            self.TRANSLATION_PROVIDER,
            self.TRANSLATION_FALLBACK_PROVIDER,
        )
        if azure_selected:
            if not self.AZURE_TRANSLATOR_ENABLED:
                raise ValueError(
                    "Selecting the azure translation provider requires "
                    "AZURE_TRANSLATOR_ENABLED=true."
                )
            if not (self.AZURE_TRANSLATOR_ENDPOINT or "").strip():
                raise ValueError(
                    "AZURE_TRANSLATOR_ENDPOINT must be set when the azure "
                    "translation provider is selected."
                )
            if not (self.AZURE_TRANSLATOR_API_KEY or "").strip():
                raise ValueError(
                    "AZURE_TRANSLATOR_API_KEY must be set when the azure "
                    "translation provider is selected."
                )
        return self

    @model_validator(mode="after")
    def validate_gemini_settings(self) -> "Settings":
        gemini_selected = "gemini" in (
            self.AI_PROVIDER,
            self.TRANSLATION_PROVIDER,
            self.TRANSLATION_FALLBACK_PROVIDER,
        )
        if gemini_selected:
            if not (self.GEMINI_API_KEY or "").strip():
                raise ValueError(
                    "GEMINI_API_KEY must be set when gemini is selected as "
                    "AI_PROVIDER or TRANSLATION_PROVIDER."
                )
            if not (self.GEMINI_MODEL or "").strip():
                raise ValueError("GEMINI_MODEL must not be empty.")
            if self.GEMINI_REQUEST_TIMEOUT_SECONDS < 1:
                raise ValueError("GEMINI_REQUEST_TIMEOUT_SECONDS must be at least 1.")
            if self.GEMINI_MAX_RETRIES < 0:
                raise ValueError("GEMINI_MAX_RETRIES must not be negative.")
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
        if not (0.0 <= self.FIELD_CLARIFICATION_THRESHOLD <= 1.0):
            raise ValueError(
                "FIELD_CLARIFICATION_THRESHOLD must be between 0.0 and 1.0."
            )
        if not (0.0 <= self.FIELD_AUTO_CONFIRM_THRESHOLD <= 1.0):
            raise ValueError(
                "FIELD_AUTO_CONFIRM_THRESHOLD must be between 0.0 and 1.0."
            )
        if self.FIELD_CLARIFICATION_THRESHOLD > self.FIELD_AUTO_CONFIRM_THRESHOLD:
            raise ValueError(
                "FIELD_CLARIFICATION_THRESHOLD must not exceed "
                "FIELD_AUTO_CONFIRM_THRESHOLD."
            )
        if self.FIELD_DETECTION_REVIEW_MODE not in ("auto", "manual"):
            raise ValueError(
                "FIELD_DETECTION_REVIEW_MODE must be one of: auto, manual."
            )
        if not (0.0 <= self.HYBRID_LOCAL_QUALITY_THRESHOLD <= 1.0):
            raise ValueError(
                "HYBRID_LOCAL_QUALITY_THRESHOLD must be between 0.0 and 1.0."
            )
        if self.HYBRID_MAX_ESCALATION_PAGES <= 0:
            raise ValueError("HYBRID_MAX_ESCALATION_PAGES must be a positive integer.")
        for name in (
            "HYBRID_MIN_LABEL_COVERAGE",
            "HYBRID_MIN_MARK_COVERAGE",
            "HYBRID_MIN_PAGE_COVERAGE",
        ):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be between 0.0 and 1.0.")
        # Azure credentials are validated only when Azure is actually the
        # selected provider — the local/mock providers must keep working
        # with every AZURE_* setting unset. Error messages never echo the
        # key back, only the name of the missing/invalid setting.
        #
        # `hybrid` is deliberately *not* included: it runs the local pass
        # first and treats an unconfigured Azure as "cannot escalate", which
        # is a documented, working mode. Failing startup there would make the
        # cheap default impossible to deploy without a paid account.
        if self.FIELD_DETECTION_PROVIDER == "azure":
            if not self.AZURE_DOCUMENT_INTELLIGENCE_ENABLED:
                raise ValueError(
                    "FIELD_DETECTION_PROVIDER=azure requires "
                    "AZURE_DOCUMENT_INTELLIGENCE_ENABLED=true."
                )
            if not (self.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or "").strip():
                raise ValueError(
                    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT must be set when "
                    "FIELD_DETECTION_PROVIDER=azure."
                )
            endpoint = self.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or ""
            if not endpoint.startswith("https://"):
                raise ValueError(
                    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT must be an https:// URL."
                )
            if not (self.AZURE_DOCUMENT_INTELLIGENCE_API_KEY or "").strip():
                raise ValueError(
                    "AZURE_DOCUMENT_INTELLIGENCE_API_KEY must be set when "
                    "FIELD_DETECTION_PROVIDER=azure."
                )
            if not self.AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID.strip():
                raise ValueError(
                    "AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID must not be empty."
                )
            if not self.AZURE_DOCUMENT_INTELLIGENCE_API_VERSION.strip():
                raise ValueError(
                    "AZURE_DOCUMENT_INTELLIGENCE_API_VERSION must not be empty."
                )
        if self.AZURE_DOCUMENT_INTELLIGENCE_TIMEOUT_SECONDS <= 0:
            raise ValueError(
                "AZURE_DOCUMENT_INTELLIGENCE_TIMEOUT_SECONDS must be a "
                "positive integer."
            )
        if self.AZURE_DOCUMENT_INTELLIGENCE_MAX_RETRIES < 0:
            raise ValueError(
                "AZURE_DOCUMENT_INTELLIGENCE_MAX_RETRIES must not be negative."
            )
        return self

    @model_validator(mode="after")
    def validate_storage_settings(self) -> "Settings":
        provider = self.STORAGE_PROVIDER.strip().lower()
        if provider not in _SUPPORTED_STORAGE_PROVIDERS:
            raise ValueError(
                f"Unknown STORAGE_PROVIDER '{self.STORAGE_PROVIDER}'. "
                f"Supported values: {sorted(_SUPPORTED_STORAGE_PROVIDERS)}"
            )
        self.STORAGE_PROVIDER = provider
        if provider == "s3":
            endpoint = (self.S3_ENDPOINT_URL or "").strip()
            if not endpoint.startswith(("https://", "http://")):
                raise ValueError(
                    "S3_ENDPOINT_URL must be a valid http(s):// URL when STORAGE_PROVIDER='s3'."
                )
            if not (self.S3_BUCKET or "").strip():
                raise ValueError(
                    "S3_BUCKET must not be empty when STORAGE_PROVIDER='s3'."
                )
            if not (self.S3_ACCESS_KEY_ID or "").strip():
                raise ValueError(
                    "S3_ACCESS_KEY_ID must not be empty when STORAGE_PROVIDER='s3'."
                )
            if not (self.S3_SECRET_ACCESS_KEY or "").strip():
                raise ValueError(
                    "S3_SECRET_ACCESS_KEY must not be empty when STORAGE_PROVIDER='s3'."
                )
            if self.S3_TIMEOUT_SECONDS <= 0:
                raise ValueError("S3_TIMEOUT_SECONDS must be positive.")
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
