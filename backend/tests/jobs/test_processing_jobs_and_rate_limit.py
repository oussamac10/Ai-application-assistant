"""Tests for async prepare-questions ProcessingJob queue, ARQ worker, and rate limiting (S1-03)."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.database.session import SessionLocal
from app.main import app


def _make_digital_form_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 120), "Anmeldung einer Wohnung", fontsize=14)
    page.insert_text((72, 170), "Vorname: ____________________________", fontsize=11)
    page.insert_text((72, 210), "Nachname: ___________________________", fontsize=11)
    page.insert_text((72, 250), "Geburtsdatum: _______________________", fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def test_async_prepare_questions_returns_202_and_completes_with_ownership_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "JOB_EXECUTION_MODE", "background")

    client = TestClient(app)
    upload_resp = client.post(
        "/api/source-documents",
        files={"file": ("anmeldung.pdf", _make_digital_form_pdf(), "application/pdf")},
        data={"language": "ar", "privacyAccepted": "true"},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    doc_id = upload_resp.json()["documentId"]
    doc_token = upload_resp.json()["ownershipToken"]

    # 1. Slow dynamic detection path returns 202 Accepted with jobId
    prep_resp = client.post(
        f"/api/source-documents/{doc_id}/prepare-questions",
        headers={"X-Document-Token": doc_token},
        json={"language": "ar"},
    )
    assert prep_resp.status_code == 202, prep_resp.text
    queued_body = prep_resp.json()
    assert queued_body["documentId"] == doc_id
    assert queued_body["status"] in ("queued", "running")
    job_id = queued_body["jobId"]
    assert job_id

    # 2. Polling /api/jobs/{jobId} WITHOUT valid document ownership token is rejected (401)
    unauth_poll = client.get(f"/api/jobs/{job_id}")
    assert unauth_poll.status_code == 401
    wrong_poll = client.get(
        f"/api/jobs/{job_id}",
        headers={"X-Document-Token": "wrong-token"},
    )
    assert wrong_poll.status_code == 401

    # 3. Polling WITH valid X-Document-Token returns completed job + usable session credentials
    ok_poll = client.get(
        f"/api/jobs/{job_id}",
        headers={"X-Document-Token": doc_token},
    )
    assert ok_poll.status_code == 200, ok_poll.text
    job_body = ok_poll.json()
    assert job_body["jobId"] == job_id
    assert job_body["status"] == "completed"
    result = job_body["result"]
    assert result["status"] == "ready"
    assert result["sessionId"]
    assert result["ownershipToken"]

    # Verify the returned session token actually unlocks the created session
    sess_resp = client.get(
        f"/api/form-sessions/{result['sessionId']}",
        headers={"X-Session-Token": result["ownershipToken"]},
    )
    assert sess_resp.status_code == 200

    # Verify zero plaintext token is stored in ProcessingJob JSON columns
    from app.jobs.models import ProcessingJob

    db = SessionLocal()
    try:
        row = db.query(ProcessingJob).filter(ProcessingJob.public_id == job_id).one()
        assert result["ownershipToken"] not in str(row.payload or {})
        assert result["ownershipToken"] not in str(row.result_payload or {})
        assert doc_token not in str(row.payload or {})
    finally:
        db.close()


@pytest.mark.asyncio
async def test_arq_worker_function_executes_queued_job_idempotently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "OCR_PROVIDER", "mock")
    # Simulate ARQ mode where HTTP route only enqueues to DB (mocking Redis enqueue)
    monkeypatch.setattr(settings, "JOB_EXECUTION_MODE", "arq")

    from app.jobs import worker as jobs_worker

    enqueued_ids: list[str] = []

    async def _fake_enqueue(job_public_id: str) -> None:
        enqueued_ids.append(job_public_id)

    monkeypatch.setattr(jobs_worker, "enqueue_prepare_questions_job", _fake_enqueue)

    img = Image.new("RGB", (500, 700), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    client = TestClient(app)
    up = client.post(
        "/api/source-documents",
        files={"file": ("scan.png", buf.getvalue(), "image/png")},
        data={"language": "fr", "privacyAccepted": "true"},
    )
    assert up.status_code == 201
    doc_id = up.json()["documentId"]
    doc_token = up.json()["ownershipToken"]

    prep = client.post(
        f"/api/source-documents/{doc_id}/prepare-questions",
        headers={"X-Document-Token": doc_token},
        json={"language": "fr"},
    )
    assert prep.status_code == 202
    job_id = prep.json()["jobId"]
    assert enqueued_ids == [job_id]

    # Before worker runs, job is still "queued"
    poll_before = client.get(
        f"/api/jobs/{job_id}", headers={"X-Document-Token": doc_token}
    )
    assert poll_before.status_code == 200
    assert poll_before.json()["status"] == "queued"

    # Run ARQ worker function directly (and run twice to prove idempotency)
    await jobs_worker.process_prepare_questions_job({}, job_id)
    await jobs_worker.process_prepare_questions_job({}, job_id)

    poll_after = client.get(
        f"/api/jobs/{job_id}", headers={"X-Document-Token": doc_token}
    )
    assert poll_after.status_code == 200
    assert poll_after.json()["status"] == "completed"


def test_sliding_window_rate_limiter_enforces_429_and_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.rate_limit import reset_rate_limiter_state

    reset_rate_limiter_state()
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 2)

    client = TestClient(app)
    for _ in range(2):
        r = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "wrongpassword123"},
        )
        assert r.status_code == 401

    third = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "wrongpassword123"},
    )
    assert third.status_code == 429
    assert third.headers.get("Retry-After") is not None
    assert third.json()["error_code"] == "rate_limit_exceeded"
    reset_rate_limiter_state()


def test_standalone_worker_subprocess_resolves_all_orm_foreign_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression test: a cold `arq app.jobs.worker.WorkerSettings` process that
    has NOT imported `app.main` must still resolve every SQLAlchemy FK (`users.id`,
    `source_documents.id`, `form_sessions.id`, etc.) without `NoReferencedTableError`.
    """
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(storage_dir))
    monkeypatch.setattr(settings, "JOB_EXECUTION_MODE", "arq")

    from app.jobs import worker as jobs_worker

    async def _noop_enqueue(job_public_id: str) -> None:
        return None

    monkeypatch.setattr(jobs_worker, "enqueue_prepare_questions_job", _noop_enqueue)

    client = TestClient(app)
    up = client.post(
        "/api/source-documents",
        files={"file": ("anmeldung.pdf", _make_digital_form_pdf(), "application/pdf")},
        data={"language": "en", "privacyAccepted": "true"},
    )
    assert up.status_code == 201
    doc_id = up.json()["documentId"]
    doc_token = up.json()["ownershipToken"]

    prep = client.post(
        f"/api/source-documents/{doc_id}/prepare-questions",
        headers={"X-Document-Token": doc_token},
        json={"language": "en"},
    )
    assert prep.status_code == 202
    job_id = prep.json()["jobId"]

    env = dict(os.environ)
    env.update(
        {
            "STORAGE_PROVIDER": "local",
            "DOCUMENT_STORAGE_PATH": str(storage_dir),
            "AI_PROVIDER": "mock",
            "OCR_PROVIDER": "mock",
            "FIELD_DETECTION_PROVIDER": "local",
            "TRANSLATION_PROVIDER": "mock",
            "TRANSLATION_FALLBACK_PROVIDER": "none",
        }
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import asyncio\n"
                "from app.jobs.worker import process_prepare_questions_job\n"
                f"asyncio.run(process_prepare_questions_job({{}}, {job_id!r}))\n"
            ),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Worker subprocess crashed:\n{proc.stderr}"

    poll = client.get(f"/api/jobs/{job_id}", headers={"X-Document-Token": doc_token})
    assert poll.status_code == 200
    assert poll.json()["status"] == "completed"
