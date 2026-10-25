"""Requiredness must survive the whole way from the document to the client.

Detecting three states is worthless if the pipeline stores a boolean: the
detector said "the form marked nothing", `FormField.required` said `True`
because that was its default, and the user was blocked on a question the
document never asked. These tests pin each hop.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy import text

from app.database.session import SessionLocal
from app.field_detection.question_bridge import _resolve_requiredness
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService, ValidationError, resolve_requiredness


class _Detected:
    """The two attributes `_resolve_requiredness` reads."""

    def __init__(self, label: str, required: bool | None) -> None:
        self.label = label
        self.required = required


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
        yield
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Detection -> three states
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,acroform,expected",
    [
        ("Nom de famille", None, "unknown"),
        ("Nom de famille *", None, "required"),
        ("Deuxième prénom (facultatif)", None, "optional"),
        ("Nom de famille", True, "required"),
        ("Nom de famille", False, "optional"),
    ],
)
def test_detection_resolves_three_states(
    label: str, acroform: bool | None, expected: str
) -> None:
    assert _resolve_requiredness(_Detected(label, acroform)) == expected


def test_an_unmarked_field_is_never_resolved_to_required() -> None:
    """The regression in one line: absence of evidence used to mean required."""
    assert _resolve_requiredness(_Detected("Nom de famille", None)) != "required"


# ---------------------------------------------------------------------------
# The boolean stays consistent, and never outvotes the richer value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "requiredness,required,expected",
    [
        # The richer value wins, even against the boolean's `True` default —
        # which is exactly the collapse this replaces.
        ("unknown", True, ("unknown", False)),
        ("optional", True, ("optional", False)),
        ("required", False, ("required", True)),
        # Legacy callers that only know the boolean still work.
        (None, True, ("required", True)),
        (None, False, ("optional", False)),
        (None, None, ("unknown", False)),
    ],
)
def test_resolve_requiredness_pairs(
    requiredness: str | None, required: bool | None, expected: tuple[str, bool]
) -> None:
    assert resolve_requiredness(requiredness, required) == expected


def test_an_unrecognised_state_is_rejected_rather_than_guessed() -> None:
    with pytest.raises(ValidationError):
        resolve_requiredness("maybe", True)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _add_field(**kwargs: Any) -> Any:
    db = SessionLocal()
    try:
        service = FormService(db)
        template = service.create_template(key="persist-test", name="Persist test")
        version = service.create_draft_version(
            form_template_id=template.id,
            source_language="fr",
            supported_output_languages=["fr"],
        )
        return service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="nom_de_famille",
                field_type="string",
                position=1,
                translations=[TranslationSchema(language="fr", label="Nom de famille")],
                **kwargs,
            ),
        )
    finally:
        db.close()


def test_unknown_is_stored_as_unknown_not_as_required() -> None:
    field = _add_field(requiredness="unknown")

    assert field.requiredness == "unknown"
    assert field.required is False


def test_required_keeps_the_legacy_boolean_in_sync() -> None:
    field = _add_field(requiredness="required")

    assert field.requiredness == "required"
    assert field.required is True


def test_a_template_field_declaring_only_the_boolean_stays_required() -> None:
    """Hand-authored templates say `required=True` and mean it; the default
    must not be reinterpreted as "nothing was said"."""
    field = _add_field(required=True)

    assert field.requiredness == "required"
    assert field.required is True


@pytest.mark.asyncio
async def test_question_bridge_strips_asterisk_from_display_labels_while_preserving_requiredness() -> (
    None
):
    from datetime import UTC, datetime, timedelta

    from app.ai.mock_provider import MockAIProvider
    from app.documents.models import SourceDocument
    from app.field_detection.models import DetectedField, FieldDetectionResult
    from app.field_detection.question_bridge import create_session_from_confirmed_fields
    from app.forms.models import FormVersion
    from app.sessions.security import hash_ownership_token
    from app.translation.providers.mock import MockTranslationProvider

    db = SessionLocal()
    try:
        expires = datetime.now(UTC) + timedelta(hours=2)
        doc = SourceDocument(
            ownership_token_hash=hash_ownership_token("req-strip-token"),
            original_filename="scan.pdf",
            sanitized_filename="scan.pdf",
            storage_path="uploads/scan.pdf",
            content_type="application/pdf",
            size_bytes=512,
            checksum_sha256="b" * 64,
            status="analyzed",
            page_count=1,
            detected_source_language="de",
            expires_at=expires,
        )
        db.add(doc)
        db.commit()

        fdr = FieldDetectionResult(
            source_document_id=doc.id,
            status="completed",
            provider_name="local",
            analysis_version=1,
            field_count=2,
            expires_at=expires,
        )
        db.add(fdr)
        db.commit()

        db.add_all(
            [
                DetectedField(
                    detection_result_id=fdr.id,
                    page_number=1,
                    display_order=0,
                    label="Vorname *",
                    normalized_name="vorname",
                    field_type="text",
                    required=None,
                    confidence=0.85,
                    source="ocr",
                    review_status="confirmed",
                ),
                DetectedField(
                    detection_result_id=fdr.id,
                    page_number=1,
                    display_order=1,
                    label="Geburtsdatum (TT.MM.JJJJ) *:",
                    normalized_name="geburtsdatum",
                    field_type="date",
                    required=None,
                    confidence=0.85,
                    source="ocr",
                    review_status="confirmed",
                ),
            ]
        )
        db.commit()
        db.refresh(fdr)

        session, _ = await create_session_from_confirmed_fields(
            db,
            doc,
            fdr,
            user_language="en",
            output_language="de",
            ai_provider=MockAIProvider(),
            translation_provider=MockTranslationProvider(),
            document_language="de",
        )

        version = db.get(FormVersion, session.form_version_id)
        assert version is not None
        fields = sorted(version.fields, key=lambda f: f.position)
        assert len(fields) == 2
        for created_field in fields:
            assert created_field.requiredness == "required"
            assert created_field.required is True
            for tr in created_field.translations:
                assert "*" not in tr.label
                assert not tr.label.endswith(":")
    finally:
        db.close()
