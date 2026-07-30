"""Filtering document content that is not a field.

A form contains a lot of text that looks structurally like a label but asks the
user for nothing: notices, section titles, instructions, footers, page numbers.
The French test form opens with

    Attention : exemple non officiel. Utilisez uniquement des données fictives.

which the label passes read as a colon-terminated label ("Attention") with
trailing text — the same shape as a real field — and it became question 1.

The filter deliberately does **not** decide on wording alone. "Attention" can
legitimately head a field ("Attention à porter :" with a line to write on), and
rejecting a real field is worse than keeping a spurious one: the user can skip
a bad question, but cannot answer one that was removed. So a candidate is only
dropped when the wording says "notice" **and** the layout offers no evidence
that anything can be entered:

- no input region (`input_bounding_box`),
- no options (it is not a choice group),
- no existing value,
- a short label, so a long sentence that merely contains the word is untouched.

Every one of those is already carried on `DetectedFieldCandidate`, so the same
rule applies to every provider — the local text passes and Azure's key-value
pairs alike.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.field_detection.providers.base import DetectedFieldCandidate

logger = logging.getLogger(__name__)

# Words that introduce a notice rather than name a field, in every language the
# product supports.
_NOTICE_WORDS: frozenset[str] = frozenset(
    {
        # English
        "attention",
        "warning",
        "notice",
        "important",
        "note",
        "caution",
        "disclaimer",
        "please note",
        # German
        "achtung",
        "hinweis",
        "wichtig",
        "warnung",
        "anmerkung",
        "bitte beachten",
        # French
        "avertissement",
        "remarque",
        "avis",
        "veuillez noter",
        # Arabic
        "تنبيه",
        "تحذير",
        "ملاحظة",
        "مهم",
        "إشعار",
    }
)

# Instruction openings: a sentence telling the user what to do, not asking for
# a value.
_INSTRUCTION_PREFIXES: tuple[str, ...] = (
    "please ",
    "fill in",
    "complete the",
    "use only",
    "do not ",
    "bitte ",
    "füllen sie",
    "verwenden sie",
    "beachten sie",
    "veuillez ",
    "utilisez ",
    "remplissez",
    "merci de ",
    "يرجى ",
    "الرجاء ",
    "استخدم ",
)

# A page footer: "Page 1 of 2", "Seite 1 von 2", "page 1 sur 2", "1 / 2".
_FOOTER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bpage\s*\d+\s*(of|/|sur|von|aus|من)\s*\d+\b", re.IGNORECASE),
    re.compile(r"\bseite\s*\d+\b", re.IGNORECASE),
    re.compile(r"^\s*[-–—]?\s*\d+\s*[/|]\s*\d+\s*[-–—]?\s*$"),
)

# A notice heading is short. Beyond this it is prose, and prose is filtered by
# its own rule (or left alone).
_MAX_NOTICE_WORDS = 3


@dataclass(frozen=True)
class FilterCounts:
    """Why candidates were dropped. Counts only — never a label."""

    non_field_heading: int = 0
    warning: int = 0
    instruction: int = 0
    footer: int = 0

    @property
    def total(self) -> int:
        return self.non_field_heading + self.warning + self.instruction + self.footer


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().rstrip(":：.،,").split())


def is_notice_word(label: str) -> bool:
    """Whether the label is (essentially) just a notice word."""
    normalized = _normalize(label)
    if not normalized or len(normalized.split()) > _MAX_NOTICE_WORDS:
        return False
    return normalized in _NOTICE_WORDS


def is_instruction(label: str) -> bool:
    normalized = _normalize(label)
    return any(normalized.startswith(prefix) for prefix in _INSTRUCTION_PREFIXES)


def is_footer(label: str) -> bool:
    text = label.strip()
    return any(pattern.search(text) for pattern in _FOOTER_PATTERNS)


# A pre-filled value is short and is not a sentence. The body of a notice is
# neither — "exemple non officiel. Utilisez uniquement des données fictives."
# was being read as this field's existing value, which made a notice look like
# a filled-in field.
_MAX_VALUE_WORDS = 8


def is_prose_value(text: str | None) -> bool:
    """Whether an "existing value" is really a paragraph of prose."""
    if not text:
        return False
    stripped = text.strip()
    return stripped.endswith(".") or len(stripped.split()) > _MAX_VALUE_WORDS


def has_input_evidence(candidate: DetectedFieldCandidate) -> bool:
    """Whether anything about this candidate says a value can be entered.

    This is what keeps a *real* field whose label happens to be a notice word
    from being filtered: if the form drew somewhere to write, it is a field
    regardless of what it is called.

    Prose sitting after the label is explicitly *not* evidence — that is the
    notice's own body text, which is exactly what a notice looks like.
    """
    if candidate.input_bounding_box is not None or candidate.options:
        return True
    return bool(candidate.existing_value) and not is_prose_value(
        candidate.existing_value
    )


def classify_non_field(candidate: DetectedFieldCandidate) -> str | None:
    """Why this candidate is not a field, or None if it is one.

    Layout evidence wins: a candidate with an input region is always a field.
    """
    if has_input_evidence(candidate):
        return None

    label = candidate.label or ""
    if is_footer(label):
        return "footer"
    if is_notice_word(label):
        # "warning" and "notice" are reported separately from generic
        # headings because they are the ones users noticed as bogus questions.
        return "warning"
    if is_instruction(label):
        return "instruction"
    return None


def filter_non_field_candidates(
    candidates: list[DetectedFieldCandidate],
) -> tuple[list[DetectedFieldCandidate], FilterCounts]:
    """Drops candidates that are document furniture rather than fields."""
    kept: list[DetectedFieldCandidate] = []
    warning = instruction = footer = heading = 0

    for candidate in candidates:
        reason = classify_non_field(candidate)
        if reason is None:
            kept.append(candidate)
            continue
        if reason == "warning":
            warning += 1
        elif reason == "instruction":
            instruction += 1
        elif reason == "footer":
            footer += 1
        else:
            heading += 1

    counts = FilterCounts(
        non_field_heading=heading,
        warning=warning,
        instruction=instruction,
        footer=footer,
    )
    if counts.total:
        logger.info(
            "Non-field content filtered: non_field_heading_filtered=%d "
            "warning_filtered=%d instruction_filtered=%d footer_filtered=%d",
            counts.non_field_heading,
            counts.warning,
            counts.instruction,
            counts.footer,
        )
    return kept, counts
