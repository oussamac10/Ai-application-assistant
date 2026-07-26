"""LocalFieldDetectionProvider — deterministic, rules-based field detection.

No AI or cloud dependency. Two mutually exclusive strategies:

- If the document has AcroForm widgets, they are authoritative: each widget
  already carries a structural field_type, so detection here is about
  finding its nearby label and refining "text" widgets via label wording.
- Otherwise (plain digital text or OCR output), lines ending in a colon are
  treated as label candidates; the field_type is guessed from the label
  text and, when present, from the value pattern trailing the colon.

Confidence always reflects how much of this evidence was actually found —
a label-less AcroForm widget or a bare colon-line both score lower than a
fully corroborated candidate, and normalization.py downgrades anything
below the low-confidence threshold to "unknown" rather than guessing.
"""

from __future__ import annotations

from app.field_detection.classification import (
    acroform_widget_confidence,
    classify_label,
    classify_value_pattern,
)
from app.field_detection.labeling import (
    LinePhrase,
    build_line_phrases,
    find_nearest_label_for_box,
)
from app.field_detection.normalization import (
    deduplicate_candidates,
    downgrade_low_confidence,
    normalize_field_name,
    sort_candidates_deterministically,
)
from app.field_detection.providers.base import (
    DetectedFieldCandidate,
    DetectionDocumentInput,
    DetectionResult,
)

_ACROFORM_TYPE_MAP = {
    "checkbox": "checkbox",
    "radio": "radio",
    "choice": "select",
    "signature": "signature",
    "text": "text",
}

_HUMANIZE_UNDERSCORE = str.maketrans("_-", "  ")


def _humanize_field_name(field_name: str) -> str:
    spaced = field_name.translate(_HUMANIZE_UNDERSCORE).strip()
    return spaced.title() if spaced else field_name


class LocalFieldDetectionProvider:
    provider_name = "local"
    provider_version = "1"

    def detect(self, document: DetectionDocumentInput) -> DetectionResult:
        if document.acroform_widgets:
            candidates = self._detect_from_acroform(document)
        else:
            candidates = self._detect_from_text_lines(document)

        candidates = [downgrade_low_confidence(c) for c in candidates]
        candidates = deduplicate_candidates(candidates)
        candidates = sort_candidates_deterministically(candidates)

        return DetectionResult(
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            fields=tuple(candidates),
        )

    def _phrases_by_page(
        self, document: DetectionDocumentInput
    ) -> dict[int, list[LinePhrase]]:
        return {
            page.page_number: build_line_phrases(page.page_number, page.tokens)
            for page in document.pages
        }

    def _detect_from_acroform(
        self, document: DetectionDocumentInput
    ) -> list[DetectedFieldCandidate]:
        phrases_by_page = self._phrases_by_page(document)
        candidates: list[DetectedFieldCandidate] = []

        for index, widget in enumerate(document.acroform_widgets):
            page_phrases = phrases_by_page.get(widget.page_number, [])
            nearest_label = find_nearest_label_for_box(widget.rect, page_phrases)

            mapped_type = _ACROFORM_TYPE_MAP.get(widget.field_type, "text")
            if nearest_label and nearest_label.text:
                label = nearest_label.text
            else:
                label = _humanize_field_name(widget.field_name)

            if mapped_type == "text":
                mapped_type = classify_label(label)

            confidence = acroform_widget_confidence(
                mapped_type, label_found=nearest_label is not None
            )

            candidates.append(
                DetectedFieldCandidate(
                    candidate_key=f"acroform-{widget.page_number}-{index}",
                    page_number=widget.page_number,
                    label=label,
                    normalized_name=normalize_field_name(widget.field_name or label),
                    field_type=mapped_type,
                    confidence=confidence,
                    source="acroform",
                    required=widget.required,
                    label_bounding_box=nearest_label.bounding_box
                    if nearest_label
                    else None,
                    input_bounding_box=widget.rect,
                )
            )

        return candidates

    def _detect_from_text_lines(
        self, document: DetectionDocumentInput
    ) -> list[DetectedFieldCandidate]:
        candidates: list[DetectedFieldCandidate] = []

        for page in document.pages:
            phrases = build_line_phrases(page.page_number, page.tokens)
            for line_index, phrase in enumerate(phrases):
                if not phrase.has_colon or not phrase.text:
                    continue

                value_type = (
                    classify_value_pattern(phrase.trailing_text)
                    if phrase.trailing_text
                    else None
                )
                label_type = classify_label(phrase.text)

                if value_type is not None:
                    field_type = value_type
                    confidence = 0.8
                elif label_type != "text":
                    field_type = label_type
                    confidence = 0.65
                else:
                    field_type = "text"
                    confidence = 0.55

                candidates.append(
                    DetectedFieldCandidate(
                        candidate_key=f"page{page.page_number}-line{line_index}",
                        page_number=page.page_number,
                        label=phrase.text,
                        normalized_name=normalize_field_name(phrase.text),
                        field_type=field_type,
                        confidence=confidence,
                        source=phrase.source,
                        label_bounding_box=phrase.bounding_box,
                        existing_value=phrase.trailing_text or None,
                    )
                )

        return candidates
