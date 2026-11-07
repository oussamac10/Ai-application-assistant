from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.orm.session import Session

from app.core.config import settings

# In SQLAlchemy 2.0 database URL must be a string.
# We assert settings.DATABASE_URL is not None.
assert (
    settings.DATABASE_URL is not None
), "DATABASE_URL environment variable is not set."

engine_kwargs: dict[str, Any] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
        }
    )

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
