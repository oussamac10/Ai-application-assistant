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
    ("notes", "multiline_text"),
    ("remarks", "multiline_text"),
    ("signature", "signature"),
)

_EMAIL_VALUE_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_VALUE_PATTERN = re.compile(r"^\+?[0-9()\-.\s]{6,}$")
_CURRENCY_VALUE_PATTERN = re.compile(r"^[€$£]?\s?\d+([.,]\d+)?$")


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
