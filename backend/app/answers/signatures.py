"""Signatures: sensitive, structured, and never electronically mandatory.

Two product rules shape this module, and both are easy to get wrong in the
obvious direction.

**A required signature field does not mean a required *digital* signature.**
When a PDF marks its signature box required, the form is saying "this must be
signed before it counts" — about the printed document, not about this
application. Forcing an electronic signature would invent a requirement the
document never made, and would lock out anyone who cannot draw one on the
device they happen to be using. So `digital_signature_required` is `False`,
always, and "sign after printing" is a first-class completion, not a skip:
`pending_manual_signature` is a decision the user made, and the summary says
"Will be signed after printing" rather than "Skipped".

**A signature is biometric personal data.** It never goes to a translation
provider, an AI provider or an analytics sink; it is never logged, never echoed
in an error, and never normalized. Everything below stores geometry and nothing
else — no pressure, no tilt, no device identity, no timing. Those add nothing
to a rendered signature and everything to what a leak would expose.

Strokes are stored as vectors rather than a bitmap: they render crisply at any
export size, they are far smaller, and they are trivial to validate. A PNG is
generated only when export actually needs one, from data that has already been
bounds-checked — which also means no user-supplied image bytes are ever
persisted or decoded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# How a document's own metadata describes the need for a signature. Distinct
# from *how* it will be produced, which is always the user's choice.
SIGNATURE_REQUIRED_BEFORE_SUBMISSION = "required_before_submission"
SIGNATURE_OPTIONAL = "optional"
SIGNATURE_UNKNOWN = "unknown"

SIGNATURE_REQUIREMENTS = (
    SIGNATURE_REQUIRED_BEFORE_SUBMISSION,
    SIGNATURE_OPTIONAL,
    SIGNATURE_UNKNOWN,
)

# The answer status for "I will sign the printed form". Its own state on
# purpose: it is neither an answer (there is no value) nor a skip (the question
# was dealt with, deliberately, and the summary must say so).
PENDING_MANUAL_SIGNATURE = "pending_manual_signature"

# Bounds. Generous enough for a real signature on a large tablet, small enough
# that no request can be used to store bulk data or exhaust memory. A rejection
# here is a client bug or an attack; either way the payload is refused whole
# rather than truncated, so a partial signature can never be rendered as if it
# were complete.
MAX_STROKES = 200
MAX_POINTS_PER_STROKE = 2000
MAX_TOTAL_POINTS = 20_000
MAX_CANVAS_DIMENSION = 4000
MIN_CANVAS_DIMENSION = 1


class SignatureValidationError(ValueError):
    """A signature payload that cannot be accepted.

    The message names the structural problem only — never a coordinate, never
    the payload, never how much of it was parsed.
    """


@dataclass(frozen=True)
class SignatureData:
    """One captured signature, as vectors.

    `width`/`height` are the canvas the strokes were drawn on, so export can
    scale into the PDF's signature box while preserving aspect ratio.
    """

    strokes: tuple[tuple[tuple[float, float], ...], ...]
    width: float
    height: float

    @property
    def point_count(self) -> int:
        return sum(len(stroke) for stroke in self.strokes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "strokes": [[list(point) for point in stroke] for stroke in self.strokes],
            "width": self.width,
            "height": self.height,
        }


def _coerce_dimension(raw: Any, name: str) -> float:
    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        raise SignatureValidationError(f"Signature {name} must be a number.")
    value = float(raw)
    if not (MIN_CANVAS_DIMENSION <= value <= MAX_CANVAS_DIMENSION):
        raise SignatureValidationError(f"Signature {name} is out of range.")
    return value


def parse_signature(payload: Any) -> SignatureData:
    """Validates a client signature payload and returns it as vectors.

    Strict by construction: every value must be a finite number inside the
    declared canvas, and anything else is refused. Nothing here interprets
    strings, so a payload cannot carry markup, a data URI or a script — the
    class of injection that an SVG or HTML signature format invites simply has
    no surface here.
    """
    if not isinstance(payload, dict):
        raise SignatureValidationError("Signature payload must be an object.")

    width = _coerce_dimension(payload.get("width"), "width")
    height = _coerce_dimension(payload.get("height"), "height")

    raw_strokes = payload.get("strokes")
    if not isinstance(raw_strokes, list) or not raw_strokes:
        raise SignatureValidationError("Signature must contain at least one stroke.")
    if len(raw_strokes) > MAX_STROKES:
        raise SignatureValidationError("Signature contains too many strokes.")

    strokes: list[tuple[tuple[float, float], ...]] = []
    total_points = 0

    for raw_stroke in raw_strokes:
        if not isinstance(raw_stroke, list) or not raw_stroke:
            raise SignatureValidationError(
                "Each signature stroke must be a point list."
            )
        if len(raw_stroke) > MAX_POINTS_PER_STROKE:
            raise SignatureValidationError("A signature stroke has too many points.")

        points: list[tuple[float, float]] = []
        for raw_point in raw_stroke:
            if not isinstance(raw_point, (list, tuple)) or len(raw_point) != 2:
                raise SignatureValidationError(
                    "Each signature point must be an [x, y] pair."
                )
            x, y = raw_point
            for value in (x, y):
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise SignatureValidationError(
                        "Signature coordinates must be numbers."
                    )
                # Rejects NaN and infinity, which survive an isinstance check
                # and would otherwise reach the PDF renderer.
                if value != value or value in (float("inf"), float("-inf")):
                    raise SignatureValidationError(
                        "Signature coordinates must be finite."
                    )
            if not (0 <= float(x) <= width and 0 <= float(y) <= height):
                raise SignatureValidationError(
                    "Signature coordinates fall outside the canvas."
                )
            points.append((float(x), float(y)))

        total_points += len(points)
        if total_points > MAX_TOTAL_POINTS:
            raise SignatureValidationError("Signature contains too many points.")
        # Stroke order is preserved — it is what makes the rendered signature
        # look like the one that was drawn.
        strokes.append(tuple(points))

    return SignatureData(strokes=tuple(strokes), width=width, height=height)


def signature_requirement_from_field(field: Any) -> str:
    """What the *document* said about needing a signature.

    Mapped from the field's three-state requiredness, so a signature field
    inherits the same evidence rules as every other field and `unknown` stays
    unknown.
    """
    from app.answers.states import OPTIONAL, REQUIRED, field_requiredness

    state = field_requiredness(field)
    if state == REQUIRED:
        return SIGNATURE_REQUIRED_BEFORE_SUBMISSION
    if state == OPTIONAL:
        return SIGNATURE_OPTIONAL
    return SIGNATURE_UNKNOWN


def digital_signature_required() -> bool:
    """Always False.

    A function rather than a constant so the rule is greppable and so any
    future caller that wants to make electronic signing mandatory has to change
    this one place, where the reason is written down.
    """
    return False
