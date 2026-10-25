"""ARQ Redis worker & background task dispatcher for ProcessingJob (Phase S1-03)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

# Register all SQLAlchemy ORM mappers so standalone `arq app.jobs.worker.WorkerSettings`
# processes resolve every cross-module ForeignKey (`users.id`, `source_documents.id`, etc.).
import app.answers.models  # noqa: F401
import app.auth.models  # noqa: F401
import app.documents.models  # noqa: F401
import app.field_detection.models  # noqa: F401
import app.forms.models  # noqa: F401
import app.jobs.models  # noqa: F401
import app.ocr.models  # noqa: F401
import app.pdf.models  # noqa: F401
import app.questions.models  # noqa: F401
import app.sessions.models  # noqa: F401
from app.core.config import settings
from app.database.session import SessionLocal
from app.jobs.repository import ProcessingJobRepository
from app.jobs.service import ProcessingJobService

logger = logging.getLogger(__name__)


async def process_prepare_questions_job(
    ctx: dict[str, Any], job_public_id: str
) -> None:
    """Idempotent ARQ worker task executing document OCR/detection/question preparation."""
    db = SessionLocal()
    try:
        service = ProcessingJobService(db)
        await service.execute_prepare_job_by_public_id(job_public_id)
    except Exception:
        logger.exception(
            "Unhandled error in prepare_questions worker job %s", job_public_id
        )
        db.rollback()
        repo = ProcessingJobRepository()
        job = repo.get_by_public_id(db, job_public_id)
        if job is not None and job.status not in ("completed", "failed"):
            job.status = "failed"
            job.stage = "worker"
            job.error_code = "document_processing_failed"
            job.completed_at = datetime.now(UTC)
            repo.update(db, job)
    finally:
        db.close()


def run_prepare_questions_job_sync(job_public_id: str) -> None:
    """Synchronous runner invoked by FastAPI BackgroundTasks in `background` mode."""
    import asyncio

    asyncio.run(process_prepare_questions_job({}, job_public_id))


async def enqueue_prepare_questions_job(job_public_id: str) -> None:
    """Enqueues `job_public_id` onto Redis via ARQ."""
    from arq import create_pool
    from arq.connections import RedisSettings

    if not settings.REDIS_URL:
        raise RuntimeError("REDIS_URL is required when JOB_EXECUTION_MODE='arq'.")

    pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    try:
        await pool.enqueue_job(
            "process_prepare_questions_job",
            job_public_id,
        )
    finally:
        await pool.aclose()


def _worker_redis_settings() -> Any:
    from arq.connections import RedisSettings

    dsn = settings.REDIS_URL or "redis://redis:6379/0"
    return RedisSettings.from_dsn(dsn)


class WorkerSettings:
    """ARQ CLI entrypoint (`arq app.jobs.worker.WorkerSettings`)."""

    functions = [process_prepare_questions_job]
    redis_settings = _worker_redis_settings() if settings.REDIS_URL else None
    job_timeout = 300
    max_jobs = 8
