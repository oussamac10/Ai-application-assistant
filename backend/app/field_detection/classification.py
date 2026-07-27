"""Field-type classification from label text and known value patterns.

Deterministic keyword/regex matching only — no AI involved, per the
project's "deterministic validation over AI" rule.
"""

from __future__ import annotations

import re

# Ordered: first matching pattern wins. Keys are matched case-insensitively
# as substrings of the label text.
_LABEL_KEYWORD_RULES: tuple[tuple[str, str], ...] = (
    ("email", "email"),
    ("e-mail", "email"),
    ("phone", "phone"),
    ("mobile", "phone"),
    ("tel", "phone"),
    ("fax", "phone"),
    ("date of birth", "date"),
    ("birth date", "date"),
    ("date", "date"),
    ("signature", "signature"),
    ("address", "address"),
    ("street", "address"),
    ("city", "address"),
    ("postal", "address"),
    ("zip", "address"),
    ("amount", "currency"),
    ("price", "currency"),
    ("total", "currency"),
    ("salary", "currency"),
    ("fee", "currency"),
    ("quantity", "number"),
    ("count", "number"),
    ("age", "number"),
    ("number", "number"),
    ("comment", "multiline_text"),
    ("message", "multiline_text"),
    ("description", "multiline_text"),
    ("describe", "multiline_text"),
    ("situation", "multiline_text"),
    ("notes", "multiline_text"),
    ("remarks", "multiline_text"),
    ("explain", "multiline_text"),
)

_EMAIL_VALUE_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_VALUE_PATTERN = re.compile(r"^\+?[0-9()\-.\s]{6,}$")
_CURRENCY_VALUE_PATTERN = re.compile(r"^[€$£]?\s?\d+([.,]\d+)?$")

# Generic marker glyphs: a checkbox is a bracket pair with 0-1 char inside
# (e.g. "[ ]", "[x]", "[_]"); a radio button is the same shape in parens
# (e.g. "( )", "(x)"). Deliberately not tied to any specific document's
# exact marker characters.
_CHECKBOX_MARKER_PATTERN = re.compile(r"^\[.{0,2}\]$")
_RADIO_MARKER_PATTERN = re.compile(r"^\(.{0,2}\)$")

# First-person confirmation/consent phrasing — generic legal/consent
# boilerplate wording, not any one document's exact sentence.
_CONFIRMATION_KEYWORDS = (
    "i confirm",
    "i agree",
    "i certify",
    "i declare",
    "i acknowledge",
    "i understand and accept",
    "i consent",
    "i attest",
)

# Footer / document-identifier boilerplate keywords. Combined with a
# page-bottom position check in is_footer_metadata so a legitimate field
# elsewhere on the page (e.g. "ID Number:" near the top) is never excluded
# by keyword alone.
_METADATA_KEYWORDS = (
    "document id",
    "doc id",
    "doc. id",
    "reference number",
    "reference no",
    "ref no",
    "ref.",
    "form id",
    "internal use only",
    "page ",
)

# Fraction of page height (from the top) beyond which content is
# considered to be in the footer/margin region.
_FOOTER_POSITION_RATIO = 0.9


def classify_label(label_text: str) -> str:
    """Guesses a field_type from label wording alone. Returns "text" when
    nothing matches — never invents a more specific type from weak evidence.
    """
    lowered = label_text.strip().lower()
    if not lowered:
        return "text"

    for keyword, field_type in _LABEL_KEYWORD_RULES:
        if keyword in lowered:
            return field_type

    return "text"


def classify_value_pattern(value_text: str) -> str | None:
    """Classifies a candidate's known existing value text, if it
    unambiguously matches a recognized pattern. Returns None otherwise."""
    stripped = value_text.strip()
    if not stripped:
        return None
    if _EMAIL_VALUE_PATTERN.match(stripped):
        return "email"
    if _CURRENCY_VALUE_PATTERN.match(stripped):
        return "currency"
    if _PHONE_VALUE_PATTERN.match(stripped) and any(ch.isdigit() for ch in stripped):
        return "phone"
    return None


def marker_type(token_text: str) -> str | None:
    """Classifies a single token as a checkbox marker, a radio marker, or
    neither (a normal word)."""
    stripped = token_text.strip()
    if _CHECKBOX_MARKER_PATTERN.match(stripped):
        return "checkbox"
    if _RADIO_MARKER_PATTERN.match(stripped):
        return "radio"
    return None


def is_confirmation_sentence(text: str) -> bool:
    """True if the text reads as first-person consent/confirmation
    boilerplate (e.g. "I confirm that ...", "I agree to ..."). Keyword-based
    and independent of any single document's exact wording."""
    lowered = text.strip().lower()
    if not lowered:
        return False
    return any(keyword in lowered for keyword in _CONFIRMATION_KEYWORDS)


def is_footer_metadata(text: str, top_y: float, page_height: float) -> bool:
    """True only when text matches a metadata/footer keyword AND sits in the
    bottom margin of the page — both signals are required so a legitimate
    field elsewhere on the page is never excluded by keyword alone."""
    if page_height <= 0:
        return False
    in_footer_region = (top_y / page_height) >= _FOOTER_POSITION_RATIO
    if not in_footer_region:
        return False
    lowered = text.strip().lower()
    return any(keyword in lowered for keyword in _METADATA_KEYWORDS)


_ACROFORM_TYPE_CONFIDENCE = {
    "checkbox": 0.97,
    "radio": 0.97,
    "select": 0.9,
    "signature": 0.95,
}


def acroform_widget_confidence(field_type: str, label_found: bool) -> float:
    base = _ACROFORM_TYPE_CONFIDENCE.get(
        field_type, 0.9 if field_type == "text" else 0.85
    )
    return base if label_found else max(0.6, base - 0.15)


_CHOICE_GROUP_CONFIDENCE = {
    "checkbox": 0.85,  # marker-based multiple_choice (checkbox group)
    "radio": 0.85,  # marker-based single-choice (radio group)
    None: 0.6,  # no markers — inferred from layout alone
}


def choice_group_confidence(marker_kind: str | None) -> float:
    return _CHOICE_GROUP_CONFIDENCE.get(marker_kind, 0.6)
