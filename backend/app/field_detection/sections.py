"""Section-context tracking, so a label that repeats in different sections
of one form becomes a distinct field rather than being deduplicated away.

German contracts routinely reuse the same short label under different
parties — "Name:", "Straße, Nr.", "PLZ, Ort" appear once under
"Zwischen dem Vermieter" (landlord) and again under "und dem Mieter"
(tenant). Deduplication keys on `normalized_name`, so without a section
prefix the second occurrence of each is silently dropped and the user is
only ever asked for one of the two parties.

Deterministic and keyword-based — no AI. Two kinds of context line are
recognized:

- a *party* context ("... Vermieter", "... Mieter"), which is also used to
  prefix the user-visible label, since "Name" alone would otherwise be
  ambiguous in the guided flow; and
- a *numbered section* heading ("§ 4 Mietkosten"), used only for the
  stable key, never for the label — "Mietkosten – IBAN" adds nothing for
  the user over plain "IBAN".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# "§ 4 Mietkosten" / "§ 1 Mietraum / Mieträume" — the number is dropped from
# the slug so re-ordering the form doesn't change a field's stable key.
_SECTION_HEADING_PATTERN = re.compile(r"^§\s*(\d+)\s*(.*)$")

# Party context markers, matched as whole words against the *whole* line.
# Ordered so the more specific "vermieter" is tried before "mieter";
# whole-word matching also keeps "Untermieter" from matching "mieter".
_PARTY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("wohnungsgeber", "Wohnungsgeber"),
    ("eigentümer", "Eigentümer"),
    ("eigentuemer", "Eigentümer"),
    ("vermieter", "Vermieter"),
    ("mieter", "Mieter"),
    ("antragsteller", "Antragsteller"),
    ("arbeitgeber", "Arbeitgeber"),
)

# A party-context line is a short introducing line, not a full paragraph
# that merely mentions the word — "Zwischen dem Vermieter" (3 words) is
# context; a legal clause discussing the Vermieter is not.
_MAX_PARTY_CONTEXT_WORDS = 5


@dataclass(frozen=True)
class SectionContext:
    """The section a candidate was found under. `key_prefix` disambiguates
    stable keys; `label_prefix` is only set for party contexts, where the
    user-visible label genuinely needs it; `title` is the section's own
    human-readable name, used as a fallback label when a candidate's own
    nearby text reads as prose."""

    key_prefix: str
    label_prefix: str | None = None
    title: str | None = None


def is_section_heading(text: str) -> bool:
    """True for a numbered "§ N ..." heading line — never a field itself."""
    return _SECTION_HEADING_PATTERN.match(text.strip()) is not None


def section_heading_title(text: str) -> str | None:
    """The title part of a "§ N Title" heading, without the number."""
    match = _SECTION_HEADING_PATTERN.match(text.strip())
    if match is None:
        return None
    title = match.group(2).strip()
    return title or None


def detect_context(text: str) -> SectionContext | None:
    """Returns the section context a line establishes, or None if the line
    is ordinary content. Only called for lines that were not consumed as
    fields, so a real field line never overwrites the active context."""
    stripped = text.strip()
    if not stripped:
        return None

    title = section_heading_title(stripped)
    if title is not None:
        return SectionContext(key_prefix=_slug(title), title=title)

    words = stripped.split()
    if len(words) <= _MAX_PARTY_CONTEXT_WORDS:
        lowered = stripped.lower()
        for keyword, display in _PARTY_KEYWORDS:
            if re.search(rf"\b{keyword}\b", lowered):
                return SectionContext(
                    key_prefix=_slug(keyword), label_prefix=display, title=display
                )

    return None


_UNSAFE_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    lowered = text.strip().lower()
    return _UNSAFE_SLUG_CHARS.sub("_", lowered).strip("_")
