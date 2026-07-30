"""Provider-level and end-to-end tests for the Azure Document Intelligence
provider. Azure HTTP is always stubbed — no test calls the real service.

The `azure_rental_contract_layout.json` fixture is a real
`prebuilt-layout`-shaped response generated from the actual
Jobcenter-LK-SM-Muster-Mietvertrag-Zimmer.pdf: every word's content and
polygon comes from that document's own text layer (PDF points converted to
inches), so the geometry exercised here is genuine rather than invented.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text as sa_text

import app.main  # noqa: F401  registers every SQLAlchemy mapper once
from app.ai.mock_provider import MockAIProvider
from app.core.config import settings
from app.database.session import SessionLocal
from app.documents.errors import DocumentUnauthorizedError
from app.documents.service import SourceDocumentService
from app.field_detection.confidence import decide_auto_review_status
from app.field_detection.errors import AzureDocumentIntelligenceError
from app.field_detection.orchestration import PrepareQuestionsService
from app.field_detection.providers.azure import AzureDocumentIntelligenceProvider
from app.field_detection.providers.azure_client import AzureAnalyzeResponse
from app.field_detection.providers.base import DetectionDocumentInput
from app.field_detection.repository import FieldDetectionRepository
from app.field_detection.service import (
    FieldDetectionService,
    build_default_provider,
    build_detection_fingerprint,
)
from app.field_detection.usage import ProviderUsageRecord
from app.forms.repositories import FormRepository

_FIXTURE = Path(__file__).parent / "fixtures" / "azure_rental_contract_layout.json"


@pytest.fixture(scope="module")
def rental_layout() -> dict[str, Any]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


class StubAzureClient:
    """Stands in for AzureDocumentIntelligenceClient, counting calls so a
    test can prove the real provider was (or was not) invoked."""

    def __init__(
        self,
        analyze_result: dict[str, Any] | None = None,
        error: AzureDocumentIntelligenceError | None = None,
    ) -> None:
        self.analyze_result = analyze_result or {"pages": []}
        self.error = error
        self.call_count = 0

    def analyze_document(self, pdf_path: Path) -> AzureAnalyzeResponse:
        self.call_count += 1
        if self.error is not None:
            raise self.error
        return AzureAnalyzeResponse(
            analyze_result=self.analyze_result,
            request_id="req-test-1",
            model_id="prebuilt-layout",
            api_version="2024-11-30",
            duration_seconds=1.25,
        )


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(sa_text("TRUNCATE TABLE provider_usage_records CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE form_sessions CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture
def azure_settings() -> Generator[None, None, None]:
    """Selects the Azure provider for the duration of a test, restoring
    whatever was configured before."""
    original = (
        settings.FIELD_DETECTION_PROVIDER,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY,
    )
    settings.FIELD_DETECTION_PROVIDER = "azure"
    settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED = True
    settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = (
        "https://example.cognitiveservices.azure.com"
    )
    settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY = "test-key"
    yield
    (
        settings.FIELD_DETECTION_PROVIDER,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY,
    ) = original


def _create_digital_pdf(path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 10)
    c.drawString(40, 700, "Platzhalter für Azure-Analyse")
    c.showPage()
    c.save()


def _upload(tmp_path: Path) -> tuple[Any, Any, str]:
    pdf_path = tmp_path / "azure-doc.pdf"
    _create_digital_pdf(pdf_path)
    db = SessionLocal()
    with open(pdf_path, "rb") as handle:
        content = handle.read()
    doc, token = SourceDocumentService(db).upload_and_analyze(
        filename="azure-doc.pdf",
        content_type="application/pdf",
        file_chunks=[content],
        privacy_accepted=True,
        user_language="de",
        output_language="de",
    )
    return db, doc, token


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------


def test_factory_selects_the_azure_provider(azure_settings: None) -> None:
    provider = build_default_provider()
    assert isinstance(provider, AzureDocumentIntelligenceProvider)
    assert provider.provider_name == "azure"


def test_factory_still_selects_local_and_mock() -> None:
    from app.field_detection.providers.local import LocalFieldDetectionProvider
    from app.field_detection.providers.mock import MockFieldDetectionProvider

    original = settings.FIELD_DETECTION_PROVIDER
    try:
        settings.FIELD_DETECTION_PROVIDER = "local"
        assert isinstance(build_default_provider(), LocalFieldDetectionProvider)
        settings.FIELD_DETECTION_PROVIDER = "mock"
        assert isinstance(build_default_provider(), MockFieldDetectionProvider)
    finally:
        settings.FIELD_DETECTION_PROVIDER = original


def test_provider_without_configuration_reports_not_configured() -> None:
    original = (
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY,
    )
    settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED = False
    settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = None
    settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY = None
    try:
        provider = AzureDocumentIntelligenceProvider()
        with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
            provider.detect(
                DetectionDocumentInput(page_count=1, source_pdf_path=Path("/tmp/x.pdf"))
            )
        assert exc_info.value.error_code == "azure_not_configured"
    finally:
        (
            settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED,
            settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY,
        ) = original


def test_provider_requires_the_original_file() -> None:
    provider = AzureDocumentIntelligenceProvider(client=StubAzureClient())
    with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
        provider.detect(DetectionDocumentInput(page_count=1, source_pdf_path=None))
    assert exc_info.value.error_code == "azure_processing_failed"


# ---------------------------------------------------------------------------
# Normalization of the real rental-contract layout
# ---------------------------------------------------------------------------


def test_rental_contract_layout_produces_usable_german_candidates(
    rental_layout: dict[str, Any], tmp_path: Path
) -> None:
    """The core Phase 14 claim: an Azure layout response converts into the
    app's own detected-field format, and yields the same kind of usable
    German candidates the local provider finds."""
    pdf_path = tmp_path / "doc.pdf"
    _create_digital_pdf(pdf_path)

    provider = AzureDocumentIntelligenceProvider(client=StubAzureClient(rental_layout))
    result = provider.detect(
        DetectionDocumentInput(page_count=3, source_pdf_path=pdf_path)
    )

    assert result.provider_name == "azure"
    usable = [
        f
        for f in result.fields
        if decide_auto_review_status(f) != "needs_clarification"
    ]
    assert len(usable) >= 5

    keys = {f.normalized_name for f in usable}
    # Landlord and tenant stay distinct (Phase 13 section context applies
    # to Azure-derived tokens too).
    assert "vermieter_name" in keys
    assert "mieter_name" in keys
    # Bank block and the sentence-embedded date/amount blanks.
    assert any("iban" in k for k in keys)
    assert any("bic" in k for k in keys)
    assert any("beginnt_am" in k for k in keys)
    assert any("grundmiete" in k for k in keys)

    # Every candidate carries page and geometry, and no heading/prose leaks.
    for field in usable:
        assert field.page_number >= 1
        assert not field.label.startswith("§")


def test_key_value_pairs_take_precedence_over_text_derived_candidates(
    tmp_path: Path,
) -> None:
    """Azure's own key/value pairing is stronger evidence than layout
    inference, so it wins for the same normalized name."""
    pdf_path = tmp_path / "doc.pdf"
    _create_digital_pdf(pdf_path)
    poly = [1.0, 1.0, 2.0, 1.0, 2.0, 1.2, 1.0, 1.2]
    layout = {
        "pages": [
            {
                "pageNumber": 1,
                "unit": "inch",
                "width": 8.5,
                "height": 11.0,
                "words": [
                    {"content": "IBAN:", "polygon": poly, "confidence": 0.99},
                    {
                        "content": "_" * 30,
                        "polygon": [2.5, 1.0, 6.0, 1.0, 6.0, 1.2, 2.5, 1.2],
                        "confidence": 0.99,
                    },
                ],
            }
        ],
        "keyValuePairs": [
            {
                "key": {
                    "content": "IBAN",
                    "boundingRegions": [{"pageNumber": 1, "polygon": poly}],
                },
                "confidence": 0.95,
            }
        ],
    }

    provider = AzureDocumentIntelligenceProvider(client=StubAzureClient(layout))
    result = provider.detect(
        DetectionDocumentInput(page_count=1, source_pdf_path=pdf_path)
    )

    iban = [f for f in result.fields if f.normalized_name == "iban"]
    assert len(iban) == 1, "duplicate IBAN candidates were not deduplicated"
    # The key-value candidate's confidence band (>=0.6) distinguishes it
    # from the text-derived one (0.6 exactly is shared, so assert the
    # structural evidence carried through instead).
    assert iban[0].label == "IBAN"


def test_malformed_pages_do_not_fail_the_whole_document(tmp_path: Path) -> None:
    pdf_path = tmp_path / "doc.pdf"
    _create_digital_pdf(pdf_path)
    layout = {
        "pages": [
            "not-a-dict",
            {"pageNumber": 0},
            {
                "pageNumber": 1,
                "unit": "inch",
                "width": 8.5,
                "height": 11.0,
                "words": [
                    {
                        "content": "IBAN:",
                        "polygon": [1.0, 1.0, 2.0, 1.0, 2.0, 1.2, 1.0, 1.2],
                    },
                    {
                        "content": "_" * 30,
                        "polygon": [2.5, 1.0, 6.0, 1.0, 6.0, 1.2, 2.5, 1.2],
                    },
                ],
            },
        ],
        "keyValuePairs": ["not-a-dict"],
    }

    provider = AzureDocumentIntelligenceProvider(client=StubAzureClient(layout))
    result = provider.detect(
        DetectionDocumentInput(page_count=1, source_pdf_path=pdf_path)
    )
    assert any(f.normalized_name == "iban" for f in result.fields)


def test_empty_analyze_result_yields_no_candidates_without_raising(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "doc.pdf"
    _create_digital_pdf(pdf_path)
    provider = AzureDocumentIntelligenceProvider(client=StubAzureClient({"pages": []}))
    result = provider.detect(
        DetectionDocumentInput(page_count=1, source_pdf_path=pdf_path)
    )
    assert result.fields == ()


# ---------------------------------------------------------------------------
# Service integration: caching, usage metadata, ownership
# ---------------------------------------------------------------------------


def test_second_detection_reuses_the_cache_and_never_calls_azure_twice(
    azure_settings: None, rental_layout: dict[str, Any], tmp_path: Path
) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        stub = StubAzureClient(rental_layout)
        provider = AzureDocumentIntelligenceProvider(client=stub)

        FieldDetectionService(db, provider=provider).request_detection(
            doc.public_id, token
        )
        assert stub.call_count == 1

        # A repeated request for the same document/provider/model must be
        # served from the stored result — a paid provider is never billed
        # twice for an unchanged configuration.
        FieldDetectionService(db, provider=provider).request_detection(
            doc.public_id, token
        )
        assert stub.call_count == 1

        usage = (
            db.query(ProviderUsageRecord).order_by(ProviderUsageRecord.created_at).all()
        )
        assert len(usage) == 2
        assert usage[0].served_from_cache is False
        assert usage[0].succeeded is True
        assert usage[0].provider == "azure"
        assert usage[0].model_id == "prebuilt-layout"
        assert usage[0].provider_request_id == "req-test-1"
        assert usage[0].page_count == 3
        assert usage[1].served_from_cache is True
    finally:
        db.close()


def test_changing_the_model_invalidates_the_cache_and_recomputes(
    azure_settings: None, rental_layout: dict[str, Any], tmp_path: Path
) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        stub = StubAzureClient(rental_layout)
        provider = AzureDocumentIntelligenceProvider(client=stub)
        FieldDetectionService(db, provider=provider).request_detection(
            doc.public_id, token
        )
        assert stub.call_count == 1

        settings.AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID = "prebuilt-document"
        try:
            FieldDetectionService(db, provider=provider).request_detection(
                doc.public_id, token
            )
        finally:
            settings.AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID = "prebuilt-layout"

        # A different model is a different result; reusing the old one
        # would silently serve the previous model's fields.
        assert stub.call_count == 2
    finally:
        db.close()


def test_fingerprint_changes_with_provider_model_and_document() -> None:
    base = {
        "checksum": "abc",
        "provider": "azure",
        "model_id": "prebuilt-layout",
        "analysis_version": 1,
    }
    baseline = build_detection_fingerprint(**base)  # type: ignore[arg-type]
    assert baseline == build_detection_fingerprint(**base)  # type: ignore[arg-type]
    assert baseline != build_detection_fingerprint(**{**base, "provider": "local"})  # type: ignore[arg-type]
    assert baseline != build_detection_fingerprint(**{**base, "checksum": "def"})  # type: ignore[arg-type]
    assert baseline != build_detection_fingerprint(**{**base, "model_id": "other"})  # type: ignore[arg-type]
    assert baseline != build_detection_fingerprint(**{**base, "analysis_version": 2})  # type: ignore[arg-type]


def test_azure_failure_is_recorded_and_surfaces_a_generic_error(
    azure_settings: None, tmp_path: Path
) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        stub = StubAzureClient(
            error=AzureDocumentIntelligenceError(
                "Azure rate limit reached.", "azure_rate_limited", "req-fail-1"
            )
        )
        provider = AzureDocumentIntelligenceProvider(client=stub)
        service = FieldDetectionService(db, provider=provider)

        from app.field_detection.errors import FieldDetectionValidationError

        with pytest.raises(FieldDetectionValidationError) as exc_info:
            service.request_detection(doc.public_id, token)

        # The user-facing failure never mentions Azure.
        assert exc_info.value.error_code == "field_detection_failed"
        assert "azure" not in str(exc_info.value).lower()

        usage = db.query(ProviderUsageRecord).all()
        assert len(usage) == 1
        assert usage[0].succeeded is False
        assert usage[0].error_code == "azure_rate_limited"
        assert usage[0].provider_request_id == "req-fail-1"
    finally:
        db.close()


def test_ownership_is_still_enforced_for_azure_detection(
    azure_settings: None, rental_layout: dict[str, Any], tmp_path: Path
) -> None:
    db, doc, _token = _upload(tmp_path)
    try:
        stub = StubAzureClient(rental_layout)
        service = FieldDetectionService(
            db, provider=AzureDocumentIntelligenceProvider(client=stub)
        )
        with pytest.raises(DocumentUnauthorizedError):
            service.request_detection(doc.public_id, "wrong-token")
        # Azure is never called for a request that fails authorization.
        assert stub.call_count == 0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Full orchestration through the Azure provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prepare_questions_end_to_end_with_azure(
    azure_settings: None, rental_layout: dict[str, Any], tmp_path: Path
) -> None:
    """upload -> analyze -> detect(azure) -> route -> generate questions ->
    session, with the frontend-facing flow completely unchanged."""
    db, doc, token = _upload(tmp_path)
    try:
        stub = StubAzureClient(rental_layout)
        service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=AzureDocumentIntelligenceProvider(client=stub),
        )
        result = await service.prepare(doc.public_id, token, "de", "de")

        assert result.status == "ready"
        assert result.error_code is None
        assert result.session is not None

        version = FormRepository(db).get_version(result.session.form_version_id)
        assert version is not None
        assert len(version.fields) >= 5

        keys = {f.key for f in version.fields}
        assert "vermieter_name" in keys
        assert "mieter_name" in keys

        detection = FieldDetectionRepository().get_by_source_document_and_version(
            db, doc.id, settings.FIELD_DETECTION_ANALYSIS_VERSION
        )
        assert detection is not None
        assert detection.provider_name == "azure"
        assert detection.detection_fingerprint is not None
        assert detection.review_metadata is not None
        assert stub.call_count == 1
    finally:
        db.close()


@pytest.mark.asyncio
async def test_repeated_prepare_questions_is_idempotent_and_does_not_recall_azure(
    azure_settings: None, rental_layout: dict[str, Any], tmp_path: Path
) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        stub = StubAzureClient(rental_layout)
        service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=AzureDocumentIntelligenceProvider(client=stub),
        )
        first = await service.prepare(doc.public_id, token, "de", "de")
        second = await service.prepare(doc.public_id, token, "de", "de")

        assert first.session is not None and second.session is not None
        assert first.session.public_id == second.session.public_id
        assert second.reused_existing_session is True
        # The second call reuses the session outright, so Azure is not
        # consulted again.
        assert stub.call_count == 1
    finally:
        db.close()


@pytest.mark.asyncio
async def test_azure_prepare_questions_rejects_a_non_owner(
    azure_settings: None, rental_layout: dict[str, Any], tmp_path: Path
) -> None:
    db, doc, _token = _upload(tmp_path)
    try:
        stub = StubAzureClient(rental_layout)
        service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=AzureDocumentIntelligenceProvider(client=stub),
        )
        with pytest.raises(DocumentUnauthorizedError):
            await service.prepare(doc.public_id, "wrong-token", "de", "de")
        assert stub.call_count == 0
    finally:
        db.close()
