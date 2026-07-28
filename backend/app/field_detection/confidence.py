"""Deterministic confidence routing for the automatic upload-to-questions
flow (Phase 13).

Decides, from a detected field candidate alone, which `review_status` it
should be assigned when `FIELD_DETECTION_REVIEW_MODE="auto"`. Thresholds are
plain configuration (`app/core/config.py`) — Ollama/AI is never consulted
for this decision, so the outcome is fully testable and reproducible.

Three outcomes, in order of increasing caution:

- "confirmed": high confidence and a safely usable type/configuration.
  Auto-confirmed; a question is generated from it without any user review.
- "pending_review": medium confidence, still usable and safe. A question is
  generated automatically (the normal user is never blocked), but the field
  is left non-"confirmed" so it surfaces later for admin review (Phase 14).
- "needs_clarification": confidence too low, an unclassifiable type, or a
  choice field missing its options. Never used to generate a question
  automatically — surfaced only as a plain-language uncertainty flag.
"""

from __future__ import annotations

from app.core.config import settings
from app.field_detection.providers.base import DetectedFieldCandidate

# Detected field_type values that can never be auto-confirmed/auto-used
# regardless of confidence: no safe guided-question equivalent is known.
_UNSAFE_TYPES = frozenset({"unknown"})

# Choice-shaped types that require at least one option to be usable at all.
_CHOICE_TYPES = frozenset({"radio", "select", "multiple_choice"})


def decide_auto_review_status(candidate: DetectedFieldCandidate) -> str:
    """Returns one of "confirmed", "pending_review", "needs_clarification"."""
    if candidate.field_type in _UNSAFE_TYPES:
        return "needs_clarification"

    if candidate.field_type in _CHOICE_TYPES and not candidate.options:
        return "needs_clarification"

    if candidate.confidence >= settings.FIELD_AUTO_CONFIRM_THRESHOLD:
        return "confirmed"

    if candidate.confidence >= settings.FIELD_CLARIFICATION_THRESHOLD:
        return "pending_review"

    return "needs_clarification"


# review_status values that the automatic flow treats as "usable" for
# question generation, in addition to an explicitly "confirmed" or manually
# "edited" (and thereby human-reviewed) field. "needs_clarification" and
# "rejected" are always excluded.
AUTO_USABLE_REVIEW_STATUSES = frozenset({"confirmed", "edited", "pending_review"})
