"""Drawing a captured signature into an exported PDF.

Two paths, and the second is as important as the first.

**Drawn signature.** The stored strokes are scaled to fit the form's signature
rectangle, centred, and drawn as vector polylines. Vectors rather than a
rasterised image because the data already *is* vectors: rendering a PNG to
paste in would lose resolution, add a temporary file to create and delete, and
require decoding user-supplied image bytes — a step this avoids entirely by
never producing any. Nothing here writes to disk beyond the output document.

**Sign after printing.** The rectangle is left exactly as the form's author drew
it. No placeholder, no "signed later" stamp, no faint line: this is a document
someone is about to hand to an authority, and writing anything into its
signature box would deface it. The reminder belongs in the interface, not in the
PDF.

Validation runs again here even though capture already validated. Export reads
from the database, and between capture and export sits storage — the cheapest
possible place to catch a corrupted or tampered row is immediately before it
reaches a renderer. `parse_signature` rejects NaN and infinity, which survive an
`isinstance` check and would otherwise become PDF drawing operators.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.answers.signatures import SignatureValidationError, parse_signature

logger = logging.getLogger(__name__)

# Error codes for the export layer. Structural only: a signature payload is
# biometric data and never appears in an error, a log line or a response.
SIGNATURE_INVALID = "signature_invalid"
SIGNATURE_TOO_LARGE = "signature_too_large"
SIGNATURE_EXPORT_FAILED = "signature_export_failed"
SIGNATURE_MAPPING_MISSING = "signature_mapping_missing"

# Ink width in points. Thin enough to look like a pen at signature scale,
# thick enough to survive printing.
_STROKE_WIDTH = 1.2

# Leave the signature clear of the box's own border.
_PADDING_RATIO = 0.06


class SignatureRenderError(Exception):
    """A signature that cannot be rendered. Carries a code, never a payload."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True)
class SignatureBox:
    """Where on the page the signature goes, in PDF points."""

    page_number: int
    x: float
    y: float
    width: float
    height: float


def _ink_bounds(
    strokes: tuple[tuple[tuple[float, float], ...], ...],
) -> tuple[float, float, float, float]:
    """The extent of the ink itself, not of the canvas it was drawn on.

    Someone signing in the left half of the pad leaves the right half empty.
    Fitting the *canvas* would centre that emptiness and push the signature to
    one side of the box; fitting the ink puts the signature where it looks
    centred.
    """
    xs = [x for stroke in strokes for x, _ in stroke]
    ys = [y for stroke in strokes for _, y in stroke]
    return min(xs), min(ys), max(xs), max(ys)


def _fit(
    signature_width: float,
    signature_height: float,
    box: SignatureBox,
) -> tuple[float, float, float]:
    """Returns `(scale, offset_x, offset_y)` fitting a size into the box.

    One scale for both axes, so the signature is never stretched — a stretched
    signature is not the one the person drew. The smaller ratio wins, which
    guarantees the result stays inside the box on both axes, and the leftover
    space is split evenly to centre it.
    """
    padding_x = box.width * _PADDING_RATIO
    padding_y = box.height * _PADDING_RATIO
    available_width = max(box.width - 2 * padding_x, 1.0)
    available_height = max(box.height - 2 * padding_y, 1.0)

    scale = min(
        available_width / max(signature_width, 1e-6),
        available_height / max(signature_height, 1e-6),
    )
    drawn_width = signature_width * scale
    drawn_height = signature_height * scale
    offset_x = box.x + (box.width - drawn_width) / 2
    offset_y = box.y + (box.height - drawn_height) / 2
    return scale, offset_x, offset_y


def render_signature(page: Any, box: SignatureBox, payload: Any) -> int:
    """Draws a stored signature into `box` on `page`. Returns stroke count.

    `page` is a PyMuPDF page. Coordinates are page space, top-left origin,
    which is the same convention the capture canvas uses — so no vertical flip
    is needed and none is applied.
    """
    try:
        signature = parse_signature(payload)
    except SignatureValidationError as exc:
        # The structural problem only. Never the payload, and never how much of
        # it parsed.
        raise SignatureRenderError(SIGNATURE_INVALID, str(exc)) from exc

    ink_x0, ink_y0, ink_x1, ink_y1 = _ink_bounds(signature.strokes)
    scale, offset_x, offset_y = _fit(ink_x1 - ink_x0, ink_y1 - ink_y0, box)

    drawn = 0
    for stroke in signature.strokes:
        # Ink coordinates are made relative to the ink's own origin before
        # scaling, so an unused corner of the pad never shifts the result.
        points = [
            (offset_x + (x - ink_x0) * scale, offset_y + (y - ink_y0) * scale)
            for x, y in stroke
        ]
        if len(points) == 1:
            # A deliberate dot. Without this a single tap would vanish.
            x, y = points[0]
            points = [(x, y), (x + 0.4, y + 0.4)]
        try:
            shape = page.new_shape()
            shape.draw_polyline(points)
            # No fill: the background stays whatever the form already had, so
            # nothing behind the signature is covered up.
            shape.finish(width=_STROKE_WIDTH, color=(0, 0, 0), fill=None)
            shape.commit()
        except Exception as exc:
            logger.warning(
                "Signature stroke could not be drawn (%s)", type(exc).__name__
            )
            raise SignatureRenderError(
                SIGNATURE_EXPORT_FAILED, "The signature could not be rendered."
            ) from exc
        drawn += 1

    # Counts only — a signature is biometric personal data.
    logger.info(
        "Signature rendered: page=%d strokes=%d points=%d",
        box.page_number,
        drawn,
        signature.point_count,
    )
    return drawn


def should_render_signature(answer_status: str | None) -> bool:
    """Whether an answer in this state puts ink on the page.

    `pending_manual_signature` deliberately returns False: the box is left
    exactly as the form's author drew it, with no placeholder of any kind.
    """
    from app.answers.signatures import PENDING_MANUAL_SIGNATURE

    if answer_status == PENDING_MANUAL_SIGNATURE:
        return False
    return answer_status in ("confirmed", "awaiting_confirmation")
