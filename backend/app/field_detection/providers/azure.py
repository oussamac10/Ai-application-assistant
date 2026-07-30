"""AzureDocumentIntelligenceProvider — field detection backed by Azure's
`prebuilt-layout` (or any configured) model.

Implements the same `FieldDetectionProvider` protocol as the mock and local
providers, so `FieldDetectionService`, confidence routing, the question
bridge, ownership checks and orchestration are all completely unchanged.

Detection combines two sources, in this order:

1. Azure's `keyValuePairs` — the genuinely structural signal Azure adds:
   it has already paired a label with its input region.
2. Azure's `words` and `selectionMarks`, converted to `DetectionToken`s and
   run through the *same* text-line passes the local provider uses. That
   means every Phase 13 behaviour (Unicode dotted-leader and underscore
   blank runs, label-above-blank-line, sentence-embedded German date and
   currency blanks, party/§-section context for repeated landlord/tenant
   labels, prose/heading/footnote exclusion) applies to Azure output
   without being reimplemented.

Key-value candidates win over text-derived ones for the same normalized
name, since Azure's pairing is stronger evidence than layout inference.
The shared `deduplicate_candidates` keeps the first candidate per name, so
key-value candidates are simply emitted first.

Azure's own confidence is only ever an *input* here. Whether a field is
usable, auto-confirmed, or excluded remains the deterministic Phase 13
decision in `app/field_detection/confidence.py`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import fitz

from app.core.config import settings
from app.field_detection.azure_normalization import (
    build_detection_pages,
    build_page_geometries,
    extract_key_value_candidates,
)
from app.field_detection.errors import AzureDocumentIntelligenceError
from app.field_detection.normalization import (
    deduplicate_candidates,
    downgrade_low_confidence,
    sort_candidates_deterministically,
)
from app.field_detection.providers.azure_client import (
    AzureAnalyzeResponse,
    AzureDocumentIntelligenceClient,
)
from app.field_detection.providers.base import (
    DetectedFieldCandidate,
    DetectionDocumentInput,
    DetectionResult,
)
from app.field_detection.providers.local import LocalFieldDetectionProvider

logger = logging.getLogger(__name__)


@dataclass
class AzureCallDiagnostics:
    """Per-call facts worth persisting as usage metadata (see
    app/field_detection/usage.py). Deliberately contains no document text,
    no credentials and no raw payload."""

    model_id: str
    api_version: str
    request_id: str | None
    page_count: int
    duration_seconds: float
    succeeded: bool
    error_code: str | None = None


class AzureDocumentIntelligenceProvider:
    provider_name = "azure"
    provider_version = "1"

    def __init__(
        self,
        client: AzureDocumentIntelligenceClient | None = None,
    ) -> None:
        # Injectable so tests drive a stubbed client and never touch the
        # network; production leaves it None and builds from settings.
        self._client = client
        self.last_diagnostics: AzureCallDiagnostics | None = None

    @property
    def client(self) -> AzureDocumentIntelligenceClient:
        if self._client is None:
            self._client = _build_client_from_settings()
        return self._client

    def detect(self, document: DetectionDocumentInput) -> DetectionResult:
        if document.source_pdf_path is None:
            raise AzureDocumentIntelligenceError(
                "Azure analysis requires the original document file.",
                "azure_processing_failed",
            )

        try:
            response = self.client.analyze_document(document.source_pdf_path)
        except AzureDocumentIntelligenceError as exc:
            self.last_diagnostics = AzureCallDiagnostics(
                model_id=settings.AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID,
                api_version=settings.AZURE_DOCUMENT_INTELLIGENCE_API_VERSION,
                request_id=exc.request_id,
                page_count=document.page_count,
                duration_seconds=0.0,
                succeeded=False,
                error_code=exc.error_code,
            )
            raise

        candidates = self._candidates_from_response(response, document)

        candidates = [downgrade_low_confidence(c) for c in candidates]
        candidates = deduplicate_candidates(candidates)
        candidates = sort_candidates_deterministically(candidates)

        self.last_diagnostics = AzureCallDiagnostics(
            model_id=response.model_id,
            api_version=response.api_version,
            request_id=response.request_id,
            page_count=len(response.analyze_result.get("pages") or []),
            duration_seconds=response.duration_seconds,
            succeeded=True,
        )

        return DetectionResult(
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            fields=tuple(candidates),
        )

    def _candidates_from_response(
        self,
        response: AzureAnalyzeResponse,
        document: DetectionDocumentInput,
    ) -> list[DetectedFieldCandidate]:
        analyze_result = response.analyze_result
        geometries = build_page_geometries(analyze_result, _pdf_page_sizes(document))

        # 1. Azure's own key/value pairing — strongest evidence, emitted
        #    first so deduplication prefers it.
        candidates: list[DetectedFieldCandidate] = list(
            extract_key_value_candidates(analyze_result, geometries)
        )

        # 2. Everything the shared text-line passes can find in Azure's
        #    words/selection marks.
        pages = build_detection_pages(analyze_result, geometries)
        if pages:
            text_input = DetectionDocumentInput(
                page_count=len(pages),
                pages=pages,
                acroform_widgets=(),
                language=document.language,
            )
            # The local provider's text passes are reused wholesale;
            # dedup/sort then run once over the merged list below.
            candidates.extend(
                LocalFieldDetectionProvider().detect_from_tokens(text_input)
            )

        return candidates


def _pdf_page_sizes(
    document: DetectionDocumentInput,
) -> dict[int, tuple[float, float]]:
    """Each page's true size in PDF points, needed to convert Azure pages
    reported in pixels. Taken from the already-extracted pages when
    available, else read from the file itself."""
    sizes = {
        page.page_number: (page.width, page.height)
        for page in document.pages
        if page.width > 0 and page.height > 0
    }
    if sizes or document.source_pdf_path is None:
        return sizes

    try:
        with fitz.open(document.source_pdf_path) as pdf:
            return {
                index + 1: (
                    pdf.load_page(index).rect.width,
                    pdf.load_page(index).rect.height,
                )
                for index in range(pdf.page_count)
            }
    except Exception:
        logger.warning("Could not read PDF page sizes for Azure coordinate conversion")
        return {}


def _build_client_from_settings() -> AzureDocumentIntelligenceClient:
    endpoint = (settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or "").strip()
    api_key = (settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY or "").strip()
    if not settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED or not endpoint or not api_key:
        raise AzureDocumentIntelligenceError(
            "Azure Document Intelligence is not configured.",
            "azure_not_configured",
        )
    return AzureDocumentIntelligenceClient(
        endpoint=endpoint,
        api_key=api_key,
        model_id=settings.AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID,
        api_version=settings.AZURE_DOCUMENT_INTELLIGENCE_API_VERSION,
        timeout_seconds=settings.AZURE_DOCUMENT_INTELLIGENCE_TIMEOUT_SECONDS,
        max_retries=settings.AZURE_DOCUMENT_INTELLIGENCE_MAX_RETRIES,
    )
