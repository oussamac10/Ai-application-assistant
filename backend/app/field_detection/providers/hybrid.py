"""Local-first field detection, escalating to Azure only when it has to.

Phases 11-15 forced a choice: `FIELD_DETECTION_PROVIDER=local` was free but
missed structure on hard documents, and `=azure` read them well but billed
every upload, including the digital PDFs the local pass already handled
perfectly. Neither is the right default, because the right answer depends on
the document.

So the local pass runs first, its output is scored deterministically
(`app/field_detection/quality.py`), and Azure is called only when that score
says the document was not read. An ordinary digital form costs nothing; a
scanned or densely laid-out one still works.

Three rules the routing never breaks:

- **The decision is arithmetic.** No model, no heuristic prompt, nothing that
  could learn to spend money. `domain-rules.md` forbids letting AI decide
  provider spending, and a hosted call is spending.
- **Escalation can only improve the answer.** If Azure fails, is unavailable,
  is not configured, or comes back *worse* than the local result, the local
  result is what the caller gets. A hybrid provider that can fail where the
  local provider would have succeeded is a downgrade.
- **Limits are hard.** A document over the page limit is never escalated,
  whatever it scores — a 200-page upload is exactly the case where an
  automatic hosted call is most expensive and least likely to be wanted.

Caching lives a layer up in `FieldDetectionService`, keyed on a fingerprint
that includes the provider and model, so an escalated result is stored and
reused like any other: escalation is paid for once per document, not once per
request.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from app.core.config import settings
from app.field_detection.providers.base import (
    DetectionDocumentInput,
    DetectionResult,
    FieldDetectionProvider,
)
from app.field_detection.quality import ExtractionQuality, score_extraction

logger = logging.getLogger(__name__)

# Why the hybrid provider did what it did. Stable codes — they appear in logs
# and usage metadata, never a document's content.
REASON_LOCAL_SUFFICIENT = "local_sufficient"
REASON_AZURE_NOT_CONFIGURED = "azure_not_configured"
REASON_PAGE_LIMIT = "page_limit_exceeded"
REASON_AZURE_FAILED = "azure_failed"
REASON_AZURE_NOT_BETTER = "azure_not_better"
REASON_ESCALATED = "escalated_to_azure"


@dataclass(frozen=True)
class HybridDecision:
    """What the router decided, and on what evidence. Counts and scores only."""

    used_provider: str
    reason: str
    local_quality: ExtractionQuality
    azure_quality: ExtractionQuality | None = None
    local_duration: float = 0.0
    azure_duration: float = 0.0
    page_count: int = 0

    @property
    def escalated(self) -> bool:
        return self.used_provider == "azure"


class HybridFieldDetectionProvider:
    """Runs the local provider, and Azure only when the local result is poor.

    Satisfies `FieldDetectionProvider`; callers see one provider and never know
    which engine answered, except through `last_decision` and the log line.
    """

    provider_name = "hybrid"
    provider_version = "1"

    def __init__(
        self,
        local_provider: FieldDetectionProvider | None = None,
        azure_provider: FieldDetectionProvider | None = None,
    ) -> None:
        if local_provider is None:
            from app.field_detection.providers.local import LocalFieldDetectionProvider

            local_provider = LocalFieldDetectionProvider()
        self._local = local_provider
        # Injected in tests. In production it is built lazily and only when an
        # escalation is actually going to happen, so a deployment that never
        # escalates never imports or constructs the Azure client.
        self._azure = azure_provider
        self.last_decision: HybridDecision | None = None

    # -- Azure availability -------------------------------------------------

    def _azure_is_configured(self) -> bool:
        """Whether escalation is possible at all.

        Deliberately checks configuration rather than trying and catching: an
        unconfigured deployment must not pay the cost of constructing a client
        and failing on every document.
        """
        if self._azure is not None:
            return True
        return bool(
            settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED
            and (settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or "").strip()
            and (settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY or "").strip()
        )

    def _get_azure(self) -> FieldDetectionProvider:
        if self._azure is None:
            from app.field_detection.providers.azure import (
                AzureDocumentIntelligenceProvider,
            )

            self._azure = AzureDocumentIntelligenceProvider()
        return self._azure

    # -- Routing ------------------------------------------------------------

    def detect(self, document: DetectionDocumentInput) -> DetectionResult:
        started = time.monotonic()
        local_result = self._local.detect(document)
        local_duration = time.monotonic() - started
        local_quality = score_extraction(local_result.fields)
        page_count = document.page_count

        blocked = self._escalation_blocked(local_quality, page_count)
        if blocked is not None:
            self._record(
                HybridDecision(
                    used_provider="local",
                    reason=blocked,
                    local_quality=local_quality,
                    local_duration=local_duration,
                    page_count=page_count,
                )
            )
            return local_result

        azure_started = time.monotonic()
        try:
            azure_result = self._get_azure().detect(document)
        except Exception as exc:
            # Local-first means local-safe: an escalation that fails costs the
            # caller nothing but time. The error type only — never a message,
            # which can carry the endpoint or echoed document content.
            azure_duration = time.monotonic() - azure_started
            logger.warning(
                "Hybrid escalation failed (%s); serving the local result",
                type(exc).__name__,
            )
            self._record(
                HybridDecision(
                    used_provider="local",
                    reason=REASON_AZURE_FAILED,
                    local_quality=local_quality,
                    local_duration=local_duration,
                    azure_duration=azure_duration,
                    page_count=page_count,
                )
            )
            return local_result

        azure_duration = time.monotonic() - azure_started
        azure_quality = score_extraction(azure_result.fields)

        # Paying for a worse answer is the one outcome with no upside. This is
        # measured, not assumed: Azure is usually better on the documents that
        # reach here, and "usually" is not "always".
        if azure_quality.score <= local_quality.score:
            self._record(
                HybridDecision(
                    used_provider="local",
                    reason=REASON_AZURE_NOT_BETTER,
                    local_quality=local_quality,
                    azure_quality=azure_quality,
                    local_duration=local_duration,
                    azure_duration=azure_duration,
                    page_count=page_count,
                )
            )
            return local_result

        self._record(
            HybridDecision(
                used_provider="azure",
                reason=REASON_ESCALATED,
                local_quality=local_quality,
                azure_quality=azure_quality,
                local_duration=local_duration,
                azure_duration=azure_duration,
                page_count=page_count,
            )
        )
        # The result keeps Azure's own provider/version so the persisted row
        # records which engine actually produced these fields.
        return azure_result

    def _escalation_blocked(
        self, quality: ExtractionQuality, page_count: int
    ) -> str | None:
        """The reason not to escalate, or None to go ahead.

        Order matters: a hard limit is checked before quality, so a document
        that is both over the limit and poorly read is reported as
        limit-blocked — that is the fact an operator needs.
        """
        if quality.score >= settings.HYBRID_LOCAL_QUALITY_THRESHOLD:
            return REASON_LOCAL_SUFFICIENT
        if page_count > settings.HYBRID_MAX_ESCALATION_PAGES:
            return REASON_PAGE_LIMIT
        if not self._azure_is_configured():
            return REASON_AZURE_NOT_CONFIGURED
        return None

    # -- Diagnostics --------------------------------------------------------

    @property
    def last_diagnostics(self) -> object | None:
        """The escalated call's own diagnostics, when there was one.

        `FieldDetectionService` reads this to record model id, api version and
        request id against the usage row. It is deliberately None when the
        local pass answered — there was no metered call to describe, and
        reporting stale Azure diagnostics would overstate cost.
        """
        if self.last_decision is None or not self.last_decision.escalated:
            return None
        return getattr(self._azure, "last_diagnostics", None)

    def _record(self, decision: HybridDecision) -> None:
        self.last_decision = decision
        # Scores, counts and durations only. No label, no coordinate, no page
        # text, no credential — `docs/claude/working-rules.md`. The document id
        # is logged by FieldDetectionService around this call.
        logger.info(
            "Hybrid detection: used=%s reason=%s pages=%d "
            "local_score=%.3f local_fields=%d local_labels=%.2f "
            "local_inputs=%.2f local_duration=%.2fs "
            "azure_score=%s azure_fields=%s azure_duration=%.2fs "
            "threshold=%.2f",
            decision.used_provider,
            decision.reason,
            decision.page_count,
            decision.local_quality.score,
            decision.local_quality.field_count,
            decision.local_quality.label_quality,
            decision.local_quality.input_evidence,
            decision.local_duration,
            f"{decision.azure_quality.score:.3f}" if decision.azure_quality else "-",
            decision.azure_quality.field_count if decision.azure_quality else "-",
            decision.azure_duration,
            settings.HYBRID_LOCAL_QUALITY_THRESHOLD,
        )
