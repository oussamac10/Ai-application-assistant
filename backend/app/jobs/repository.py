from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.jobs.models import ProcessingJob


class ProcessingJobRepository:
    def create(self, db: Session, job: ProcessingJob) -> ProcessingJob:
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def update(self, db: Session, job: ProcessingJob) -> ProcessingJob:
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def get_by_public_id(self, db: Session, public_id: str) -> ProcessingJob | None:
        stmt = select(ProcessingJob).where(ProcessingJob.public_id == public_id)
        return db.scalars(stmt).first()

    def get_active_or_completed_by_idempotency_key(
        self, db: Session, idempotency_key: str
    ) -> ProcessingJob | None:
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.idempotency_key == idempotency_key)
            .where(ProcessingJob.status.in_(("queued", "running", "completed")))
            .order_by(ProcessingJob.created_at.desc())
        )
        return db.scalars(stmt).first()
