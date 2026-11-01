"""Section-context tracking, so a label that repeats in different sections
of one form becomes a distinct field rather than being deduplicated away.

German contracts and administrative forms routinely reuse the same short label
under different parties or sub-sections — "Name:" under "Vermieter" and "Mieter",
"Familienname" under Applicant, "7 Ehegatte (...):" and "9 Vater (...):", or
"Grund der Strafe" under "a) In Deutschland..." and "b) Im Ausland...".
Deduplication keys on `normalized_name`, so without a section prefix the second
occurrence of each is silently dropped.

Deterministic and structural/keyword-based — no AI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# "§ 4 Mietkosten" / "§ 1 Mietraum / Mieträume" — the number is dropped from
# the slug so re-ordering the form doesn't change a field's stable key.
_SECTION_HEADING_PATTERN = re.compile(r"^§\s*(\d+)\s*(.*)$")

# Strips parenthetical remarks ("(Angaben sind auch erforderlich, ...)") and
# leading enumeration ("7 ", "8.", "II)") before checking party context.
_PARENTHETICAL_CLAUSE = re.compile(r"\([^)]*\)")
_LEADING_ENUM = re.compile(r"^\s*(?:[0-9IVXivx]{1,4}\s*[.)\-–]?\s+(?=[^\W\d_]))")
_LETTERED_SUBSECTION = re.compile(
    r"^\s*(?:\d{1,3}\s+)?([a-z])\)\s+([^?.,:;]{3,40})",
    re.IGNORECASE,
)

# Party context markers, matched against the core heading (outside parentheses).
# Specific counterparties/relatives are ordered BEFORE "antragsteller"/"mieter"
# so "Vater des Antragstellers" resolves to "Vater", not "Antragsteller".
_PARTY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("wohnungsgeber", "Wohnungsgeber"),
    ("eigentümer", "Eigentümer"),
    ("eigentuemer", "Eigentümer"),
    ("vermieter", "Vermieter"),
    ("mieter", "Mieter"),
    ("mitantragsteller", "Mitantragsteller"),
    ("ehegatte", "Ehegatte"),
    ("ehegattin", "Ehegattin"),
    ("ehepartner", "Ehepartner"),
    ("lebenspartner", "Lebenspartner"),
    ("vater", "Vater"),
    ("mutter", "Mutter"),
    ("kinder", "Kinder"),
    ("gesetzlicher vertreter", "Gesetzlicher Vertreter"),
    ("vormund", "Vormund"),
    ("arbeitgeber", "Arbeitgeber"),
    ("antragsteller", "Antragsteller"),
    # English / French party headings
    ("co-applicant", "Co-applicant"),
    ("spouse", "Spouse"),
    ("father", "Father"),
    ("mother", "Mother"),
    ("children", "Children"),
    ("guardian", "Guardian"),
    ("employer", "Employer"),
    ("landlord", "Landlord"),
    ("tenant", "Tenant"),
    ("conjoint", "Conjoint"),
    ("père", "Père"),
    ("mère", "Mère"),
    ("enfants", "Enfants"),
    ("employeur", "Employeur"),
    ("bailleur", "Bailleur"),
    ("locataire", "Locataire"),
)

# A party-context line (after stripping parenthetical instructions) is a short
# introducing heading, not a full legal paragraph that merely mentions the word.
_MAX_PARTY_CONTEXT_WORDS = 6


@dataclass(frozen=True)
class SectionContext:
    """The section a candidate was found under. `key_prefix` disambiguates
    stable keys; `label_prefix` prefixes user-visible labels when needed for
    clarity; `title` is the section's human-readable name."""

    key_prefix: str
    label_prefix: str | None = None
    title: str | None = None
    is_subsection: bool = False


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


def _strip_for_party_match(text: str) -> str:
    without_parens = _PARENTHETICAL_CLAUSE.sub(" ", text)
    without_enum = _LEADING_ENUM.sub("", without_parens)
    return " ".join(without_enum.rstrip(":：").split())


def detect_context(text: str) -> SectionContext | None:
    """Returns the section context a line establishes, or None if the line
    is ordinary content."""
    stripped = text.strip()
    if not stripped:
        return None
    # A line carrying selection markers (`[_]`, `(_)`) is an inline choice
    # question or option row, never a section/sub-section banner.
    if "[_]" in stripped or "(_)" in stripped:
        return None

    title = section_heading_title(stripped)
    if title is not None:
        return SectionContext(key_prefix=_slug(title), title=title)

    core = _strip_for_party_match(stripped)
    words = core.split()
    if 1 <= len(words) <= _MAX_PARTY_CONTEXT_WORDS:
        lowered = core.lower()
        for keyword, display in _PARTY_KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}(?:[/(\-]|$|\b)", lowered):
                return SectionContext(
                    key_prefix=_slug(keyword), label_prefix=display, title=display
                )

    # Lettered sub-section prompts ("a) In Deutschland, wann und wo?",
    # "b) Im Ausland, wann und wo?") establish context for indented follow-ups
    # ("Grund der Strafe", "Art und Höhe der Strafe") unless they are tiny
    # 1-word sub-cells ("a) jetzige").
    sub_match = _LETTERED_SUBSECTION.match(stripped)
    if sub_match is not None:
        sub_head = sub_match.group(2).strip().rstrip(",:;")
        sub_words = sub_head.split()
        if 2 <= len(sub_words) <= 5 and not re.search(
            r"\b[b-z]\)", sub_head, re.IGNORECASE
        ):
            return SectionContext(
                key_prefix=_slug(sub_head),
                label_prefix=sub_head,
                title=sub_head,
                is_subsection=True,
            )

    return None


_UNSAFE_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    lowered = text.strip().lower()
    return _UNSAFE_SLUG_CHARS.sub("_", lowered).strip("_")
