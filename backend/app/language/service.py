"""Resolves, persists and reuses a document's source language.

One place decides what language a document is in, so nothing downstream has to
guess — and, critically, so nothing downstream can *overwrite* a real answer
with a default. The observed failure was exactly that: a German contract came
back as `en` because the local model's assumed language was recorded as if it
were a detection.

Precedence, highest first:

1. **An explicitly trusted form-definition language.** A matched template says
   what it is; nothing should second-guess it.
2. **A persisted detection on the document.** Detection runs once. Repeat
   requests reuse it, which is what keeps a retry free.
3. **The dedicated detector**, run on a filtered sample of the document's text.
4. **Azure Translator's `detectedLanguage`**, if translation happens to run and
   reports one. Lower than the dedicated detector because it only exists as a
   side effect of translating, so it is absent exactly when a document needs no
   translation.
5. **`und`.**

`und` is a real answer, not a failure: a form with eight words in it has no
determinable language, and `.agents/AGENTS.md` forbids inventing
information. Callers must handle it — Azure Translator, for instance, omits
`from` entirely rather than sending `from=en`.

Nothing here logs document text. Only the language code, the confidence, the
provider and the sample's *length* are recorded.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.documents.models import SourceDocument
from app.language.detector import (
    UNDETERMINED,
    DetectedLanguage,
    DocumentLanguageDetector,
    LocalDocumentLanguageDetector,
)
from app.language.sampling import build_language_sample, has_enough_text

logger = logging.getLogger(__name__)


def build_default_detector() -> DocumentLanguageDetector:
    return LocalDocumentLanguageDetector()


class DocumentLanguageService:
    def __init__(
        self,
        db: Session,
        detector: DocumentLanguageDetector | None = None,
    ) -> None:
        self.db = db
        self._detector = detector

    @property
    def detector(self) -> DocumentLanguageDetector:
        if self._detector is None:
            self._detector = build_default_detector()
        return self._detector

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    @staticmethod
    def persisted_language(doc: SourceDocument) -> DetectedLanguage | None:
        """The stored detection, or None if detection has never run.

        A stored `und` counts as a result: re-running the same detector over
        the same text would only produce `und` again.
        """
        if not doc.detected_source_language:
            return None
        return DetectedLanguage(
            language=doc.detected_source_language,
            confidence=doc.language_detection_confidence or 0.0,
            provider=doc.language_detection_provider or "unknown",
            version=doc.language_detection_version or "unknown",
        )

    # ------------------------------------------------------------------
    # Detecting
    # ------------------------------------------------------------------

    async def ensure_detected(
        self,
        doc: SourceDocument,
        *sources: str,
        force: bool = False,
    ) -> DetectedLanguage:
        """Detects and persists the document's language, or reuses what is
        already stored.

        `sources` are raw text in priority order (page text first, then OCR
        output, then anything else). Safe to call on every request: with a
        stored result it does no work at all.
        """
        if not force:
            stored = self.persisted_language(doc)
            if stored is not None:
                logger.info(
                    "Document language reused: document=%s language=%s "
                    "confidence=%.2f provider=%s (detector NOT called)",
                    doc.public_id,
                    stored.language,
                    stored.confidence,
                    stored.provider,
                )
                return stored

        sample = build_language_sample(*sources)
        if not has_enough_text(sample):
            logger.info(
                "Document language undetermined: document=%s sample_characters=%d "
                "(too little text)",
                doc.public_id,
                len(sample),
            )
            result = DetectedLanguage(
                UNDETERMINED, 0.0, getattr(self.detector, "provider_name", "unknown")
            )
        else:
            result = await self.detector.detect(sample)
            logger.info(
                "Document language detected: document=%s language=%s "
                "confidence=%.2f provider=%s sample_characters=%d",
                doc.public_id,
                result.language,
                result.confidence,
                result.provider,
                len(sample),
            )

        self._persist(doc, result)
        return result

    def _persist(self, doc: SourceDocument, result: DetectedLanguage) -> None:
        doc.detected_source_language = result.language
        doc.language_detection_confidence = result.confidence
        doc.language_detection_provider = result.provider
        doc.language_detection_version = result.version
        doc.language_detected_at = datetime.now(UTC)
        self.db.commit()

    # ------------------------------------------------------------------
    # Precedence
    # ------------------------------------------------------------------

    @staticmethod
    def resolve(
        template_language: str | None = None,
        persisted: DetectedLanguage | None = None,
        provider_detected: str | None = None,
    ) -> str:
        """Applies the documented precedence and returns an ISO 639-1 code or
        `und`.

        A determined answer is never replaced by a weaker one — in particular
        a real `de` or `ar` is never overwritten by a translation provider's
        assumed `en`, which is the bug this ordering exists to prevent.
        """
        if template_language and template_language != UNDETERMINED:
            return template_language
        if persisted is not None and persisted.is_determined:
            return persisted.language
        if provider_detected and provider_detected != UNDETERMINED:
            return provider_detected
        return UNDETERMINED


def dominant_language(detections: tuple[str, ...]) -> str:
    """The one language to attribute a mixed batch to.

    Policy, applied in order and fully deterministic:

    1. ignore `und` and empty entries — an item the provider could not place
       should not outvote one it could;
    2. most frequent wins;
    3. ties break alphabetically, so the same input always yields the same
       answer regardless of iteration order.

    A form version carries exactly one source language, so a choice has to be
    made; making it deterministic is what keeps it reviewable. Callers log the
    per-language *counts* (never the text) when the batch disagrees.
    """
    usable = [
        language for language in detections if language and language != UNDETERMINED
    ]
    if not usable:
        return UNDETERMINED

    counts: dict[str, int] = {}
    for language in usable:
        counts[language] = counts.get(language, 0) + 1
    return min(sorted(counts), key=lambda language: (-counts[language], language))
