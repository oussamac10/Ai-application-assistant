"""AzureDocumentIntelligenceProvider — field detection backed by Azure's
`prebuilt-layout` (or any configured) model.

Implements the same `FieldDetectionProvider` protocol as the mock and local
providers, so `FieldDetectionService`, confidence routing, the question
bridge, ownership checks and orchestration are all completely unchanged.

Detection combines two sources, in this order:

1. Azure's `words` and `selectionMarks`, converted to `DetectionToken`s and
   run through the *same* text-line passes the local provider uses. That
   means every Phase 13 behaviour (Unicode dotted-leader and underscore
   blank runs, label-above-blank-line, sentence-embedded German date and
   currency blanks, party/§-section context for repeated landlord/tenant
   labels, prose/heading/footnote exclusion) applies to Azure output
   without being reimplemented.
2. Azure's `keyValuePairs`, added **only** for regions the text passes did
   not already cover.

Order matters and was chosen from measured behaviour. The text passes carry
section context ("Vermieter – Name"), which reads unambiguously in the
guided flow and keeps the landlord's and tenant's identically-labelled
fields distinct; a bare key-value label ("Name") does neither. And because
name-based deduplication cannot tell that "iban" and "mietkosten_iban" are
the same blank, letting both sources through unfiltered asked the user for
the same value twice — and additionally turned checkbox *option* labels
("Küche", "Hausschlüssel") into standalone questions. Key-value pairs are
therefore filtered positionally (see
`azure_normalization.drop_positionally_duplicate_candidates`) and are
purely additive.

Azure's own confidence is only ever an *input* here. Whether a field is
usable, auto-confirmed, or excluded remains the deterministic Phase 13
decision in `app/field_detection/confidence.py`.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import fitz

from app.core.config import settings
from app.field_detection.azure_normalization import (
    build_detection_pages,
    build_page_geometries,
    drop_positionally_duplicate_candidates,
    extract_key_value_candidates,
    extract_table_candidates,
)
from app.field_detection.errors import AzureDocumentIntelligenceError
from app.field_detection.normalization import (
    deduplicate_candidates,
    downgrade_low_confidence,
    sort_candidates_deterministically,
)
from app.field_detection.notices import filter_non_field_candidates
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
        # Per-call counts of what Azure returned and what normalization made
        # of it; read by FieldDetectionService for its own summary log.
        self.last_azure_counts: dict[str, int] = {}

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

        normalization_started = time.perf_counter()
        candidates = self._candidates_from_response(response, document)

        candidates = [downgrade_low_confidence(c) for c in candidates]
        # Document furniture — notices, instructions, footers — looks like a
        # label but asks for nothing. Filtered before dedup so it cannot
        # occupy a normalized name a real field needs.
        candidates, _filtered = filter_non_field_candidates(candidates)
        from app.field_detection.direction import is_rtl_language

        candidates = deduplicate_candidates(candidates)
        candidates = sort_candidates_deterministically(
            candidates, rtl=is_rtl_language(document.language)
        )
        normalization_duration = time.perf_counter() - normalization_started

        # Split so a slow request is attributable to the remote service
        # rather than to our own conversion (or the reverse).
        logger.info(
            "Azure detect timing: azure_duration=%.2fs normalization_duration=%.2fs "
            "candidates=%d",
            response.duration_seconds,
            normalization_duration,
            len(candidates),
        )

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

        # What Azure actually returned. Counts only — never content — so
        # this is safe to log and answers "did the model give us key-value
        # pairs at all, or only layout?" without a debugger.
        raw_pages = analyze_result.get("pages") or []
        azure_counts = {
            "pages": len(raw_pages),
            "lines": sum(
                len(p.get("lines") or []) for p in raw_pages if isinstance(p, dict)
            ),
            "words": sum(
                len(p.get("words") or []) for p in raw_pages if isinstance(p, dict)
            ),
            "selection_marks": sum(
                len(p.get("selectionMarks") or [])
                for p in raw_pages
                if isinstance(p, dict)
            ),
            "paragraphs": len(analyze_result.get("paragraphs") or []),
            "tables": len(analyze_result.get("tables") or []),
            "key_value_pairs": len(analyze_result.get("keyValuePairs") or []),
        }

        # 1. The shared text-line passes over Azure's words/selection marks.
        #    These carry party/§-section context ("Vermieter – Name"), which
        #    both reads better in the guided flow and keeps the landlord and
        #    tenant fields distinct, so they take precedence.
        pages = build_detection_pages(analyze_result, geometries)
        text_candidates: list[DetectedFieldCandidate] = []
        if pages:
            text_input = DetectionDocumentInput(
                page_count=len(pages),
                pages=pages,
                acroform_widgets=(),
                language=document.language,
            )
            text_candidates = LocalFieldDetectionProvider().detect_from_tokens(
                text_input
            )

        # 2. Azure's table cells (grid table form fields)
        table_candidates = extract_table_candidates(analyze_result, geometries)
        after_tables = drop_positionally_duplicate_candidates(
            text_candidates, table_candidates
        )

        # 3. Azure's own key/value pairing, added only where it found a
        #    region layout analysis did not. Without this positional check
        #    the same blank yields two questions, because name-based
        #    deduplication cannot equate "iban" with "mietkosten_iban".
        kv_candidates = extract_key_value_candidates(analyze_result, geometries)
        candidates = drop_positionally_duplicate_candidates(after_tables, kv_candidates)
        table_kept = len(after_tables) - len(text_candidates)
        kv_kept = len(candidates) - len(after_tables)

        self.last_azure_counts = {
            **azure_counts,
            "tokens_built": sum(len(p.tokens) for p in pages),
            "text_candidates": len(text_candidates),
            "table_candidates": len(table_candidates),
            "table_kept_after_position_dedup": table_kept,
            "kv_candidates": len(kv_candidates),
            "kv_kept_after_position_dedup": kv_kept,
            "raw_candidates": len(candidates),
        }
        logger.info(
            "Azure normalization: model=%s request_id=%s pages=%d lines=%d words=%d "
            "selection_marks=%d paragraphs=%d tables=%d key_value_pairs=%d "
            "-> tokens=%d text_candidates=%d kv_candidates=%d kv_kept=%d "
            "raw_candidates=%d",
            response.model_id,
            response.request_id,
            azure_counts["pages"],
            azure_counts["lines"],
            azure_counts["words"],
            azure_counts["selection_marks"],
            azure_counts["paragraphs"],
            azure_counts["tables"],
            azure_counts["key_value_pairs"],
            self.last_azure_counts["tokens_built"],
            len(text_candidates),
            len(kv_candidates),
            kv_kept,
            len(candidates),
        )
        if azure_counts["key_value_pairs"] == 0:
            logger.info(
                "Azure returned no keyValuePairs (model=%s); detection relies on the "
                "shared layout/text passes. Request the 'keyValuePairs' add-on "
                "feature if the model supports it.",
                response.model_id,
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
