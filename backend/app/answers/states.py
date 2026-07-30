"""The two state questions every answer check needs, answered in one place.

`confirm_summary` used to ask them inline, and got both wrong:

    if ans:
        if ans.validation_status != "valid":
            raise StateConflictError(f"Field '{field.key}' contains invalid value.")

That fires for *any* answer record that exists, whatever it holds. A skipped
question stores `validation_status="not_checked"` by design, so deliberately
skipping an optional field made the summary permanently unconfirmable with
"contains invalid value" — about a field that had no value at all.

Two independent dimensions, kept independent:

- **requiredness** — what the *document* said: `required`, `optional`, or
  `unknown`. Never inferred from whether an answer exists.
- **answer state** — what the *user* did: `unreached`, `unanswered`,
  `skipped`, `answered`, `invalid`. Never inferred from requiredness.

Only the cross-product decides anything. An unanswered field blocks confirmation
when it is `required` and never otherwise; a value is validated because it is a
value, not because its field is important.
"""

from __future__ import annotations

from typing import Any

from app.field_detection.requiredness import OPTIONAL, REQUIRED, UNKNOWN

__all__ = [
    "ANSWERED",
    "INVALID",
    "OPTIONAL",
    "REQUIRED",
    "SKIPPED",
    "UNANSWERED",
    "UNKNOWN",
    "UNREACHED",
    "answer_state",
    "field_requiredness",
    "has_submitted_value",
    "is_declaration",
    "is_skippable",
]

# Answer states. Distinct on purpose — "no record at all" and "opened it and
# typed nothing" and "chose to leave it blank" are three different facts, and
# collapsing them is what made a skip look like a validation failure.
UNREACHED = "unreached"
UNANSWERED = "unanswered"
SKIPPED = "skipped"
ANSWERED = "answered"
INVALID = "invalid"


def field_requiredness(field: Any) -> str:
    """The field's three-state requiredness.

    Falls back to the legacy boolean for rows written before the column
    existed, where it is the only evidence available.
    """
    state = getattr(field, "requiredness", None)
    if state in (REQUIRED, OPTIONAL, UNKNOWN):
        return str(state)
    return REQUIRED if getattr(field, "required", False) else UNKNOWN


def is_skippable(field: Any) -> bool:
    """Whether the user may leave this question unanswered.

    `unknown` is skippable. The form never said the field was mandatory, and
    treating silence as a demand blocks people on questions the document does
    not ask them to answer.
    """
    return field_requiredness(field) != REQUIRED


def has_submitted_value(answer: Any) -> bool:
    """Whether the user actually put something in.

    An empty string is not a value — but it is not a skip either, so it is
    never stored (`submit_answer` refuses it). This exists so that no validator,
    normalizer or AI call ever receives a blank.
    """
    if answer is None:
        return False
    if getattr(answer, "status", None) == SKIPPED:
        return False
    raw = getattr(answer, "original_answer", None)
    if raw is None:
        return False
    return bool(str(raw).strip())


def answer_state(answer: Any) -> str:
    """What the user did with this question."""
    if answer is None:
        return UNREACHED
    if getattr(answer, "status", None) == SKIPPED:
        return SKIPPED
    if not has_submitted_value(answer):
        return UNANSWERED
    if getattr(answer, "requires_clarification", False):
        return INVALID
    if getattr(answer, "validation_status", None) == "invalid":
        return INVALID
    return ANSWERED


def is_declaration(field: Any) -> bool:
    """Whether the field is a consent/declaration the user must *accept*.

    A required boolean is not answered by saying "no" — an unticked mandatory
    declaration is a missing acceptance, and it needs its own reason so the
    frontend can say so rather than reporting an invalid value.
    """
    return getattr(field, "field_type", None) == "boolean"
