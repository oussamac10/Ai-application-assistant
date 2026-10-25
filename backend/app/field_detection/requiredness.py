"""Deciding whether a detected field is required — from evidence, not habit.

Every detected field previously became `required=True` (see
`question_bridge`: `detected_field.required if ... is not None else True`).
That is an assumption, not a finding, and it is wrong in the direction that
hurts most: a user is blocked on a field the form never insisted on.

`docs/claude/domain-rules.md` forbids inventing information, so requiredness is
derived only from evidence the document actually carries, and the *absence* of
evidence is recorded as such rather than resolved to "required".

Three states, because two cannot express what we know:

- `required`   — the form says so.
- `optional`   — the form says so.
- `unknown`    — the form says nothing. Treated as optional for progress (the
  user is never blocked on a guess) but reported separately, so an admin can
  review and an export step can still warn.

Evidence sources, strongest first. Each is deterministic; none uses AI, per the
domain rule that AI decides nothing a rule can decide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

REQUIRED = "required"
OPTIONAL = "optional"
UNKNOWN = "unknown"

# Words a form uses to mark a field mandatory, in every language the product
# supports. Matched on the label and on text immediately adjacent to it.
_REQUIRED_MARKERS: tuple[str, ...] = (
    "required",
    "mandatory",
    "must be completed",
    "compulsory",
    "pflichtfeld",
    "pflichtangabe",
    "erforderlich",
    "zwingend",
    "obligatoire",
    "requis",
    "champ obligatoire",
    "إلزامي",
    "مطلوب",
)

_OPTIONAL_MARKERS: tuple[str, ...] = (
    "optional",
    "if applicable",
    "if any",
    "voluntary",
    "freiwillig",
    "falls zutreffend",
    "sofern vorhanden",
    "facultatif",
    "le cas échéant",
    "اختياري",
    "إن وجد",
)

# An asterisk adjacent to the label is the near-universal "required" marker.
# Anchored to one end or the other so a footnote reference mid-sentence ("See
# note * for details") does not count. RTL forms commonly lead with it, LTR
# forms commonly trail it (often immediately before a trailing colon, e.g.
# "Vorname *:" or "Nom (*):").
_TRAILING_ASTERISK = re.compile(r"(?:\(\s*[*∗]\s*\)|[*∗]+)\s*[:：]?\s*$")
_LEADING_ASTERISK = re.compile(r"^\s*[*∗]\s*(?=\S)")

# A form-level statement that everything is mandatory.
_ALL_REQUIRED_STATEMENTS: tuple[str, ...] = (
    "all fields are required",
    "all fields are mandatory",
    "alle felder sind pflichtfelder",
    "alle angaben sind erforderlich",
    "tous les champs sont obligatoires",
    "جميع الحقول إلزامية",
)


@dataclass(frozen=True)
class Requiredness:
    """A decision plus why it was made, so it can be reviewed and overridden."""

    state: str
    evidence: str
    confidence: float

    @property
    def is_required(self) -> bool:
        return self.state == REQUIRED

    @property
    def blocks_progress(self) -> bool:
        """Only a positive finding blocks the user. `unknown` never does."""
        return self.state == REQUIRED


def _contains(haystack: str, markers: tuple[str, ...]) -> bool:
    lowered = haystack.lower()
    return any(marker in lowered for marker in markers)


def document_requires_all(document_text: str | None) -> bool:
    """Whether the form states outright that every field is mandatory."""
    if not document_text:
        return False
    return _contains(document_text, _ALL_REQUIRED_STATEMENTS)


def detect_requiredness(
    label: str,
    *,
    acroform_required: bool | None = None,
    adjacent_text: str = "",
    all_fields_required: bool = False,
) -> Requiredness:
    """Resolves requiredness from the available evidence.

    `acroform_required` is the PDF's own flag and outranks everything: the
    document author set it explicitly. An explicit "optional" marker outranks a
    form-level "all fields required" statement, because the specific beats the
    general.
    """
    if acroform_required is True:
        return Requiredness(REQUIRED, "acroform_flag", 0.99)
    if acroform_required is False:
        return Requiredness(OPTIONAL, "acroform_flag", 0.99)

    haystack = f"{label} {adjacent_text}"

    if _contains(haystack, _OPTIONAL_MARKERS):
        return Requiredness(OPTIONAL, "optional_marker", 0.9)
    if _contains(haystack, _REQUIRED_MARKERS):
        return Requiredness(REQUIRED, "required_marker", 0.9)
    stripped = label.strip()
    if _TRAILING_ASTERISK.search(stripped) or _LEADING_ASTERISK.search(stripped):
        return Requiredness(REQUIRED, "asterisk", 0.8)
    if all_fields_required:
        return Requiredness(REQUIRED, "form_statement", 0.7)

    # Nothing said anything. Saying so is the honest answer, and it is the one
    # that does not block a user on a field the form never required.
    return Requiredness(UNKNOWN, "no_evidence", 0.0)


def strip_required_marker(label: str) -> str:
    """Removes an adjacent asterisk from a label for display.

    The marker is metadata, not part of the question; the frontend renders its
    own "Required" indicator from the resolved state.
    """
    return _LEADING_ASTERISK.sub("", _TRAILING_ASTERISK.sub("", label)).strip()


# A trailing optionality marker, in any supported language. Only in brackets
# and only at the end, so "Facultatif" used as an actual field label survives.
_TRAILING_OPTIONALITY = re.compile(
    r"[\(\[]\s*(?:optional|facultatif|facultative|freiwillig|اختياري)\s*[\)\]]\s*[:：]?\s*$",
    re.IGNORECASE,
)


def strip_requiredness_markers(label: str) -> str:
    """Removes both an asterisk and a trailing "(Optional)" from a display
    label.

    Requiredness is rendered by the frontend from the resolved three-state
    value. Leaving the marker in the text shows it twice, and worse, shows it
    in the document's language inside an interface in another one — a French
    form in an Arabic UI was rendering "(Optional)" mid-sentence.
    """
    return _TRAILING_OPTIONALITY.sub("", strip_required_marker(label)).strip()
