"""Regression tests for the language combinations the question bridge must
support.

Root cause captured here: Phase 13 added `output_language` to the generated
version's `supported_output_languages`, but the bridge only produced
translations for `user_language`. `FormService.publish_version` requires an
option translation for *every* supported output language, so any document
containing a choice field failed to publish whenever
`user_language != output_language`. The orchestration reported that as
`field_detection_invalid_result` -> "We found no usable questions in this
document", even though detection had found plenty.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import text as sa_text

import app.main  # noqa: F401  registers every SQLAlchemy mapper once
from app.ai.mock_provider import MockAIProvider
from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.field_detection.providers.base import DetectedFieldCandidate
from app.field_detection.providers.mock import MockFieldDetectionProvider
from app.field_detection.question_bridge import _supported_languages
from app.field_detection.service import FieldDetectionService


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(sa_text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE form_sessions CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


def _upload(tmp_path: Path) -> tuple[Any, Any, str]:
    pdf_path = tmp_path / "doc.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.setFont("Helvetica", 10)
    c.drawString(40, 700, "Unmatched content for detection")
    c.showPage()
    c.save()

    db = SessionLocal()
    with open(pdf_path, "rb") as handle:
        content = handle.read()
    doc, token = SourceDocumentService(db).upload_and_analyze(
        filename="doc.pdf",
        content_type="application/pdf",
        file_chunks=[content],
        privacy_accepted=True,
        user_language="en",
        output_language="en",
    )
    return db, doc, token


def _choice_and_text_candidates() -> list[DetectedFieldCandidate]:
    """A document containing at least one choice field — the shape that
    exposed the bug (plain fields alone never hit the option check)."""
    return [
        DetectedFieldCandidate(
            candidate_key="c1",
            page_number=1,
            label="Full Name",
            normalized_name="full_name",
            field_type="text",
            confidence=0.9,
            source="native",
        ),
        DetectedFieldCandidate(
            candidate_key="c2",
            page_number=1,
            label="Rooms",
            normalized_name="rooms",
            field_type="multiple_choice",
            confidence=0.9,
            source="native",
            options=("Kitchen", "Bathroom", "Cellar"),
        ),
    ]


def test_supported_languages_covers_source_user_and_output() -> None:
    """publish_version demands an option translation for each of these, and
    create_session rejects a version that omits the output language."""
    assert _supported_languages("de", "de", "de") == ["de"]
    assert _supported_languages("en", "en", "de") == ["de", "en"]
    assert _supported_languages("de", "en", "de") == ["de", "en"]
    assert _supported_languages("en", "fr", "ar") == ["ar", "en", "fr"]


@pytest.mark.parametrize(
    "user_language,output_language",
    [
        ("en", "de"),  # the exact failing combination reported from the UI
        ("de", "en"),
        ("de", "de"),
        ("fr", "ar"),
        ("en", "en"),
        ("ar", "de"),
    ],
)
@pytest.mark.asyncio
async def test_choice_field_publishes_for_every_language_combination(
    tmp_path: Path, user_language: str, output_language: str
) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        provider = MockFieldDetectionProvider(candidates=_choice_and_text_candidates())
        service = FieldDetectionService(
            db, provider=provider, ai_provider=MockAIProvider()
        )
        service.request_detection(doc.public_id, token)

        session, session_token = await service.create_session_from_confirmed_fields(
            doc.public_id,
            token,
            user_language,
            output_language,
            include_auto_usable=True,
        )

        assert session_token
        version = session.version
        assert version.status == "published", (
            f"{user_language}->{output_language} left the version unpublished, "
            "which surfaces to the user as 'no usable questions'"
        )
        assert len(version.fields) == 2
        assert session.output_language == output_language

        # Every supported output language must actually have option text —
        # this is precisely what publish_version enforces.
        choice = next(f for f in version.fields if f.field_type == "multiple_choice")
        for option in choice.options:
            languages = {t.language for t in option.translations}
            missing = set(version.supported_output_languages) - languages
            assert not missing, f"option {option.value!r} missing {missing}"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_stable_option_values_are_never_translated(tmp_path: Path) -> None:
    """The display label is translated; the value used for validation and
    export must stay the original source text."""
    db, doc, token = _upload(tmp_path)
    try:
        provider = MockFieldDetectionProvider(candidates=_choice_and_text_candidates())
        service = FieldDetectionService(
            db, provider=provider, ai_provider=MockAIProvider()
        )
        service.request_detection(doc.public_id, token)

        session, _ = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "de", "fr", include_auto_usable=True
        )
        choice = next(
            f for f in session.version.fields if f.field_type == "multiple_choice"
        )
        assert {o.value for o in choice.options} == {"Kitchen", "Bathroom", "Cellar"}
    finally:
        db.close()
