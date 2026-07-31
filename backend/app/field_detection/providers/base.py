"""FieldDetectionProvider protocol and provider-independent normalized types.

Every detection engine implementation (mock, local rules-based, future ones)
consumes a `DetectionDocumentInput` and returns a `DetectionResult`. Input
tokens carry their own coordinate space via `source` — "native"/"acroform"
tokens are in PDF point space, "ocr" tokens are in the rendered-image pixel
space Phase 10 produced (see ADR 0009) — the two are never silently mixed.
These types describe text, geometry, and a classification guess only; the
review workflow (not the provider) is the only place a candidate becomes an
authoritative field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.field_detection.constants import FIELD_TYPES, SOURCE_TYPES


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("Bounding box width and height must be non-negative.")
        if self.x < 0 or self.y < 0:
            raise ValueError("Bounding box x and y must be non-negative.")


@dataclass(frozen=True)
class DetectionToken:
    """A single unit of evidence (a word, a widget, a text run) on a page."""

    text: str
    confidence: float
    bounding_box: BoundingBox
    source: str  # one of SOURCE_TYPES

    def __post_init__(self) -> None:
        if self.source not in SOURCE_TYPES:
            raise ValueError(f"Unknown token source '{self.source}'.")


@dataclass(frozen=True)
class AcroFormWidgetInput:
    """A single AcroForm interactive-field widget on a page."""

    field_name: str
    field_type: str  # raw PDF field type: text | checkbox | radio | choice | signature
    rect: BoundingBox
    page_number: int
    required: bool = False
    # The widget's tooltip (/TU, "alternate field name"). On real government
    # forms this is the human text — "Ausbildung", "ledig" — while
    # `field_name` is a machine identifier ("chkLedigS1"). Preferred for
    # display; the name is kept because export writes back to it.
    field_label: str | None = None
    # The /AP "on" state a checkbox writes when ticked. Needed to fill the
    # form correctly and never shown to a user.
    export_value: str | None = None
    # The parent field name when the widget is a kid of a shared field, which
    # is how a *native* radio group is expressed.
    parent_name: str | None = None


@dataclass(frozen=True)
class DetectionPageInput:
    page_number: int
    width: float
    height: float
    rotation: int = 0
    tokens: tuple[DetectionToken, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DetectionDocumentInput:
    """Provider-independent input: everything a detection provider needs,
    with no knowledge of SourceDocument or ownership.

    `source_pdf_path` is the one exception to "no storage paths": a remote
    provider (Azure, Phase 14) must upload the original file itself, since
    already-extracted tokens cannot be re-submitted for layout analysis.
    It is server-side only — never serialized into an API response, never
    logged, and left None for providers that work purely from `pages`.
    """

    page_count: int
    pages: tuple[DetectionPageInput, ...] = field(default_factory=tuple)
    acroform_widgets: tuple[AcroFormWidgetInput, ...] = field(default_factory=tuple)
    language: str | None = None
    source_pdf_path: Path | None = None


@dataclass(frozen=True)
class DetectedFieldCandidate:
    """One candidate field, as returned directly by a provider.

    `candidate_key` is a deterministic, provider-generated string used for
    stable ordering/deduplication before persistence — it is not a database
    public_id (the repository layer generates those when persisting).
    """

    candidate_key: str
    page_number: int
    label: str
    normalized_name: str
    field_type: str
    confidence: float
    source: str  # one of SOURCE_TYPES
    required: bool | None = None
    multiple: bool = False
    label_bounding_box: BoundingBox | None = None
    input_bounding_box: BoundingBox | None = None
    options: tuple[str, ...] = field(default_factory=tuple)
    existing_value: str | None = None

    def __post_init__(self) -> None:
        if self.field_type not in FIELD_TYPES:
            raise ValueError(f"Unknown field_type '{self.field_type}'.")
        if self.source not in SOURCE_TYPES:
            raise ValueError(f"Unknown candidate source '{self.source}'.")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be normalized to the 0-1 range.")


@dataclass(frozen=True)
class DetectionResult:
    provider_name: str
    provider_version: str
    fields: tuple[DetectedFieldCandidate, ...] = field(default_factory=tuple)


@runtime_checkable
class FieldDetectionProvider(Protocol):
    """Provider-independent interface for all field-detection operations.

    Business services must depend only on this Protocol, never a concrete
    provider class.
    """

    provider_name: str
    provider_version: str

    def detect(self, document: DetectionDocumentInput) -> DetectionResult: ...
