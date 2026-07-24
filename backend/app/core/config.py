from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @model_validator(mode="after")
    def validate_session_secret(self) -> "Settings":
        if not self.SESSION_TOKEN_SECRET:
            self.SESSION_TOKEN_SECRET = "unsafe-dev-fallback-secret-key-12345678"
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
