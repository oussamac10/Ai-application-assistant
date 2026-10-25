from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.field_detection.schemas import PrepareQuestionsResponse


class PrepareQuestionsAcceptedResponse(BaseModel):
    documentId: str
    status: Literal["queued", "running"]
    jobId: str
    pollUrl: str


class JobStatusResponse(BaseModel):
    jobId: str
    documentId: str
    jobType: str
    status: Literal["queued", "running", "completed", "failed"]
    stage: str | None = None
    result: PrepareQuestionsResponse | None = None
    errorCode: str | None = None
