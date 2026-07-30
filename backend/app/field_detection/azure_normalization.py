"""Converts an Azure Document Intelligence `analyzeResult` into the app's
own provider-independent detection types.

No Azure SDK object or raw response fragment ever reaches the application
workflow: everything crossing this boundary is a `DetectionToken`,
`BoundingBox`, or `DetectedFieldCandidate` — exactly what the local and
mock providers already produce.

Coordinate handling is the delicate part. Azure reports each page's own
`unit` ("inch" or "pixel"), its `width`/`height` in that unit, and every
element's position as an 8-number polygon `[x1,y1,...,x4,y4]` in the same
unit, with the origin at the page's top-left *after* the page's own
rotation has been applied (`angle` describes the *content* skew, not an
axis-swap). The rest of this codebase works in PDF point space with a
top-left origin, so inches are scaled by 72 and pixels are scaled by the
ratio of the PDF's point size to the reported pixel size. Some models also
emit already-normalized 0-1 coordinates; those are detected by range and
scaled by the page size.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.field_detection.classification import (
    classify_label,
    classify_value_pattern,
    is_blank_run,
    is_probably_prose_label,
    starts_with_blank_run,
)
from app.field_detection.normalization import normalize_field_name
from app.field_detection.providers.base import (
    BoundingBox,
    DetectedFieldCandidate,
    DetectionPageInput,
    DetectionToken,
)
from app.field_detection.sections import is_section_heading

logger = logging.getLogger(__name__)

# PostScript points per inch — the unit the rest of the pipeline uses.
_POINTS_PER_INCH = 72.0

# A polygon whose every coordinate is within [0, 1] is treated as
# already-normalized rather than as a sub-pixel/sub-inch box. Real page
# geometry is never this small, so the heuristic is unambiguous in
# practice; a degenerate zero-size box is rejected separately below.
_NORMALIZED_MAX = 1.0


@dataclass(frozen=True)
class AzurePageGeometry:
    """One page's reported size and unit, plus the scale factors needed to
    map that page's polygons into PDF point space."""

    page_number: int
    width: float
    height: float
    unit: str
    scale_x: float
    scale_y: float

    @property
    def width_points(self) -> float:
        return self.width * self.scale_x

    @property
    def height_points(self) -> float:
        return self.height * self.scale_y


def build_page_geometry(
    page: dict[str, Any],
    pdf_page_size_points: tuple[float, float] | None = None,
) -> AzurePageGeometry | None:
    """Derives the scale factors for one Azure page.

    `pdf_page_size_points` is the same page's true size from the PDF, when
    known. It is what makes "pixel" pages convertible: a pixel size is only
    meaningful relative to the page it was rendered from.
    """
    try:
        page_number = int(page.get("pageNumber", 0))
        width = float(page.get("width", 0.0))
        height = float(page.get("height", 0.0))
    except (TypeError, ValueError):
        return None

    if page_number <= 0 or width <= 0 or height <= 0:
        return None

    unit = str(page.get("unit", "")).lower()

    if unit == "inch":
        return AzurePageGeometry(
            page_number=page_number,
            width=width,
            height=height,
            unit=unit,
            scale_x=_POINTS_PER_INCH,
            scale_y=_POINTS_PER_INCH,
        )

    if unit == "pixel":
        if pdf_page_size_points is None:
            # Without the PDF's own size a pixel measurement cannot be
            # converted; assume the common 96 DPI rendering rather than
            # silently emitting wrong geometry.
            scale = _POINTS_PER_INCH / 96.0
            return AzurePageGeometry(
                page_number=page_number,
                width=width,
                height=height,
                unit=unit,
                scale_x=scale,
                scale_y=scale,
            )
        pdf_width, pdf_height = pdf_page_size_points
        return AzurePageGeometry(
            page_number=page_number,
            width=width,
            height=height,
            unit=unit,
            scale_x=pdf_width / width,
            scale_y=pdf_height / height,
        )

    # Unit absent/unknown: treat the reported width/height as already being
    # in point space (scale 1), which is what a normalized-coordinate model
    # effectively needs once its polygon is multiplied by the page size.
    return AzurePageGeometry(
        page_number=page_number,
        width=width,
        height=height,
        unit=unit or "unknown",
        scale_x=1.0,
        scale_y=1.0,
    )


def polygon_to_bounding_box(
    polygon: list[float] | None,
    geometry: AzurePageGeometry | None,
) -> BoundingBox | None:
    """Converts one Azure polygon into an axis-aligned BoundingBox in PDF
    point space.

    Returns None — never a guess — when the polygon is missing, malformed,
    or degenerate, so a caller can decide whether the candidate is still
    usable without geometry.
    """
    if not polygon or geometry is None:
        return None
    if len(polygon) < 4 or len(polygon) % 2 != 0:
        return None

    try:
        xs = [float(value) for value in polygon[0::2]]
        ys = [float(value) for value in polygon[1::2]]
    except (TypeError, ValueError):
        return None

    if not xs or not ys:
        return None

    scale_x, scale_y = geometry.scale_x, geometry.scale_y

    # Already-normalized (0-1) coordinates are scaled by the page size
    # first, then by that page's own unit scale.
    if all(0.0 <= value <= _NORMALIZED_MAX for value in xs + ys):
        xs = [value * geometry.width for value in xs]
        ys = [value * geometry.height for value in ys]

    min_x, max_x = min(xs) * scale_x, max(xs) * scale_x
    min_y, max_y = min(ys) * scale_y, max(ys) * scale_y

    width = max_x - min_x
    height = max_y - min_y
    if width <= 0 or height <= 0:
        return None
    # BoundingBox forbids negative origins; clamp rather than reject, since
    # a slightly out-of-page polygon is still useful positional evidence.
    return BoundingBox(x=max(min_x, 0.0), y=max(min_y, 0.0), width=width, height=height)


def _boxes_overlap(a: BoundingBox, b: BoundingBox, min_ratio: float = 0.5) -> bool:
    """True when two boxes cover substantially the same region.

    Used to drop a candidate that another source already found: Azure's
    `keyValuePairs` and the shared text passes frequently point at the very
    same label, and keying deduplication on `normalized_name` alone cannot
    tell that "iban" and "mietkosten_iban" (the section-prefixed variant)
    are one field — which produced two questions for the same blank.
    """
    inter_x = max(0.0, min(a.x + a.width, b.x + b.width) - max(a.x, b.x))
    inter_y = max(0.0, min(a.y + a.height, b.y + b.height) - max(a.y, b.y))
    intersection = inter_x * inter_y
    if intersection <= 0:
        return False
    smaller = min(a.width * a.height, b.width * b.height)
    if smaller <= 0:
        return False
    return (intersection / smaller) >= min_ratio


def drop_positionally_duplicate_candidates(
    preferred: list[DetectedFieldCandidate],
    extra: list[DetectedFieldCandidate],
) -> list[DetectedFieldCandidate]:
    """Returns `preferred` plus only those `extra` candidates that do not
    already occupy a region a preferred candidate covers.

    `preferred` is the section-context-aware output of the shared text
    passes ("Vermieter – Name"), which reads better in the guided flow than
    an unqualified key-value label ("Name") and keeps the landlord/tenant
    distinction. Azure's key-value pairs are then additive: they contribute
    only fields layout analysis missed, instead of duplicating it.
    """
    kept = list(preferred)
    occupied: list[tuple[int, BoundingBox]] = []
    for candidate in preferred:
        for box in (candidate.label_bounding_box, candidate.input_bounding_box):
            if box is not None:
                occupied.append((candidate.page_number, box))

    for candidate in extra:
        boxes = [
            box
            for box in (candidate.label_bounding_box, candidate.input_bounding_box)
            if box is not None
        ]
        if boxes and any(
            page == candidate.page_number and _boxes_overlap(box, taken)
            for box in boxes
            for page, taken in occupied
        ):
            continue
        kept.append(candidate)
        for box in boxes:
            occupied.append((candidate.page_number, box))

    return kept


def merge_bounding_regions(
    regions: list[dict[str, Any]] | None,
    geometries: dict[int, AzurePageGeometry],
) -> tuple[int | None, BoundingBox | None]:
    """Reduces Azure's `boundingRegions` list to one page number plus one
    box. An element spanning several regions on the *same* page is merged
    into their union; when regions span multiple pages the first page wins,
    because a single candidate cannot straddle pages in this data model."""
    if not regions:
        return None, None

    page_number: int | None = None
    boxes: list[BoundingBox] = []

    for region in regions:
        if not isinstance(region, dict):
            continue
        try:
            region_page = int(region.get("pageNumber", 0))
        except (TypeError, ValueError):
            continue
        if region_page <= 0:
            continue
        if page_number is None:
            page_number = region_page
        elif region_page != page_number:
            continue

        box = polygon_to_bounding_box(
            region.get("polygon"), geometries.get(region_page)
        )
        if box is not None:
            boxes.append(box)

    if not boxes:
        return page_number, None

    min_x = min(b.x for b in boxes)
    min_y = min(b.y for b in boxes)
    max_x = max(b.x + b.width for b in boxes)
    max_y = max(b.y + b.height for b in boxes)
    return page_number, BoundingBox(
        x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y
    )


# ---------------------------------------------------------------------------
# analyzeResult -> DetectionDocumentInput / DetectedFieldCandidate
# ---------------------------------------------------------------------------

# Azure reports a selection mark as selected/unselected; both are a
# checkbox from this app's point of view, the state only decides the
# pre-filled value.
_SELECTED_STATES = frozenset({"selected"})


def build_page_geometries(
    analyze_result: dict[str, Any],
    pdf_page_sizes: dict[int, tuple[float, float]] | None = None,
) -> dict[int, AzurePageGeometry]:
    geometries: dict[int, AzurePageGeometry] = {}
    for page in analyze_result.get("pages") or []:
        if not isinstance(page, dict):
            continue
        try:
            page_number = int(page.get("pageNumber", 0))
        except (TypeError, ValueError):
            continue
        geometry = build_page_geometry(page, (pdf_page_sizes or {}).get(page_number))
        if geometry is not None:
            geometries[geometry.page_number] = geometry
    return geometries


def build_detection_pages(
    analyze_result: dict[str, Any],
    geometries: dict[int, AzurePageGeometry],
) -> tuple[DetectionPageInput, ...]:
    """Turns Azure's per-page `words` into the same `DetectionToken` shape
    the local provider consumes, so every Phase 13 text-layout heuristic
    (blank runs, section context, sentence-embedded blanks) applies to
    Azure output unchanged.

    A word with unusable geometry is skipped individually — one malformed
    item never discards the page.
    """
    pages: list[DetectionPageInput] = []

    for page in analyze_result.get("pages") or []:
        if not isinstance(page, dict):
            continue
        try:
            page_number = int(page.get("pageNumber", 0))
        except (TypeError, ValueError):
            continue
        geometry = geometries.get(page_number)
        if geometry is None:
            continue

        tokens: list[DetectionToken] = []
        for word in page.get("words") or []:
            if not isinstance(word, dict):
                continue
            content = str(word.get("content") or "").strip()
            if not content:
                continue
            box = polygon_to_bounding_box(word.get("polygon"), geometry)
            if box is None:
                continue
            tokens.append(
                DetectionToken(
                    text=content,
                    confidence=_clamp_confidence(word.get("confidence")),
                    bounding_box=box,
                    source="native",
                )
            )

        # Selection marks become the same "[_]" marker glyphs the local
        # provider already understands, so checkbox/choice-group detection
        # behaves identically for Azure input.
        for mark in page.get("selectionMarks") or []:
            if not isinstance(mark, dict):
                continue
            box = polygon_to_bounding_box(mark.get("polygon"), geometry)
            if box is None:
                continue
            tokens.append(
                DetectionToken(
                    text="[_]",
                    confidence=_clamp_confidence(mark.get("confidence")),
                    bounding_box=box,
                    source="native",
                )
            )

        pages.append(
            DetectionPageInput(
                page_number=page_number,
                width=geometry.width_points,
                height=geometry.height_points,
                rotation=0,
                tokens=tuple(tokens),
            )
        )

    return tuple(pages)


def _clamp_confidence(value: Any, default: float = 0.8) -> float:
    """Azure omits `confidence` on some elements; a missing value must not
    become 0.0 (which would read as "certainly wrong") nor 1.0 (which would
    read as certainty we do not have)."""
    if value is None:
        return default
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, confidence))


def extract_key_value_candidates(
    analyze_result: dict[str, Any],
    geometries: dict[int, AzurePageGeometry],
) -> list[DetectedFieldCandidate]:
    """Converts Azure's `keyValuePairs` into field candidates.

    This is the one genuinely *structural* signal Azure adds over the local
    provider: it has already paired a label with its input region. Each
    pair is converted independently, and a malformed pair is skipped rather
    than aborting the document.
    """
    candidates: list[DetectedFieldCandidate] = []

    for index, pair in enumerate(analyze_result.get("keyValuePairs") or []):
        if not isinstance(pair, dict):
            continue
        key = pair.get("key")
        if not isinstance(key, dict):
            continue
        label = str(key.get("content") or "").strip().rstrip(":").strip()
        if not label:
            continue
        if is_blank_run(label) or starts_with_blank_run(label):
            continue
        if is_section_heading(label) or is_probably_prose_label(label):
            continue

        page_number, label_box = merge_bounding_regions(
            key.get("boundingRegions"), geometries
        )
        value = pair.get("value") if isinstance(pair.get("value"), dict) else None
        value_page, value_box = merge_bounding_regions(
            (value or {}).get("boundingRegions"), geometries
        )
        page_number = page_number or value_page
        if page_number is None:
            continue

        raw_value = str((value or {}).get("content") or "").strip()
        # A dotted/underscored run is a placeholder, never a real answer.
        existing_value = (
            None if (not raw_value or is_blank_run(raw_value)) else raw_value
        )

        field_type = classify_value_pattern(existing_value or "") or classify_label(
            label
        )

        try:
            candidates.append(
                DetectedFieldCandidate(
                    candidate_key=f"azure-kv-{page_number}-{index}",
                    page_number=page_number,
                    label=label,
                    normalized_name=normalize_field_name(label),
                    field_type=field_type,
                    # Azure having paired key->value is strong structural
                    # evidence, but its own confidence still caps ours.
                    confidence=min(
                        0.9, max(0.6, _clamp_confidence(pair.get("confidence")))
                    ),
                    source="native",
                    label_bounding_box=label_box,
                    input_bounding_box=value_box,
                    existing_value=existing_value,
                )
            )
        except ValueError:
            # DetectedFieldCandidate rejects an unknown field_type or an
            # out-of-range confidence; skip just this pair.
            logger.warning("Skipping one malformed Azure key-value pair")
            continue

    return candidates
