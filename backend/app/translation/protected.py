"""Deterministic detection of text that must never be translated.

Per `.agents/AGENTS.md`, deterministic code decides this — not the
AI, and not the translation provider. Sending an IBAN, an email address or an
ISO date to a translator risks it being "helpfully" reformatted, localized or
transliterated, and a mangled identifier is far worse than an untranslated
label. Skipping them also removes them from the request, which costs nothing
and saves characters.

The rule is intentionally conservative: text is protected only when it is
*entirely* an identifier. A label that merely mentions one ("IBAN des
Vermieters", "Date of birth") is ordinary translatable text and must still be
translated — over-matching here would silently leave real labels in the source
language, which is exactly the bug this phase exists to remove.

Names are **not** pattern-matched. There is no reliable way to tell a personal
name from a common noun, and `domain-rules.md` forbids transliterating a name
automatically. Protection for names comes from the layer above: a *value* the
user entered is never sent here at all, only field labels and choice-option
display labels are. Stable choice `value`s are likewise never translated —
`question_bridge` translates the label and keeps the value verbatim.
"""

from __future__ import annotations

import re

# An email address, whole-string.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

# A URL or bare domain.
_URL = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)

# IBAN, matched against the text with spaces removed because forms print it
# grouped ("DE89 3704 0044 ..."). Case-sensitive and anchored on the country
# code plus check digits, so a label that merely says "IBAN des Vermieters"
# (compacted: "IBANdesVermieters") does not match.
_IBAN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")

# BIC/SWIFT.
_BIC = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")

# ISO 8601 dates and the common European/US numeric forms.
_DATE = re.compile(
    r"^("
    r"\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?"
    r"|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
    r")$"
)

# A number, optionally signed, with , or . grouping/decimals, optionally
# carrying a currency symbol or a 3-letter code.
_NUMERIC = re.compile(
    r"^[-+]?[€$£¥]?\s?\d+([ .,]\d+)*\s?([€$£¥]|[A-Z]{3})?$",
    re.IGNORECASE,
)

# A phone number: digits, spaces, and the usual separators, at least 6 digits.
_PHONE = re.compile(r"^\+?[\d][\d\s()./-]{5,}$")

# A UUID.
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# A machine token: an internal key, slug or path such as
# "personal.first_name". The hyphen is deliberately *not* a separator here —
# hyphenated words are ordinary language ("E-Mail-Adresse", "Wohn-Adresse"),
# and treating them as tokens left real German labels untranslated.
_MACHINE_TOKEN = re.compile(r"^[A-Za-z0-9]+([_.:/][A-Za-z0-9]+)+$")

_PATTERNS = (
    ("email", _EMAIL),
    ("url", _URL),
    ("bic", _BIC),
    ("date", _DATE),
    ("uuid", _UUID),
    # Phone before numeric: a phone number also looks numeric, and the more
    # specific reason is the more useful one in a log line.
    ("phone", _PHONE),
    ("numeric", _NUMERIC),
    ("machine_token", _MACHINE_TOKEN),
)


def protected_reason(text: str) -> str | None:
    """Returns why `text` must not be translated, or None if it is ordinary
    translatable text. The reason is a stable slug, safe to log."""
    candidate = text.strip()
    if not candidate:
        return "empty"

    # An IBAN is printed in groups, so it is matched without its spaces.
    if _IBAN.match(candidate.replace(" ", "")):
        return "iban"

    # Specific reasons before the generic one: "date" and "phone" are more
    # useful in a log line than "no_letters", and both would otherwise be
    # swallowed by it.
    for reason, pattern in _PATTERNS:
        if pattern.match(candidate):
            return reason

    # Nothing to translate: no letter anywhere means no language.
    if not any(character.isalpha() for character in candidate):
        return "no_letters"
    return None


def is_protected(text: str) -> bool:
    return protected_reason(text) is not None


def partition_protected(texts: list[str]) -> tuple[list[str], dict[str, str]]:
    """Splits `texts` into (translatable, {protected_text: reason}), preserving
    order and without deduplicating — the caller owns dedup."""
    translatable: list[str] = []
    protected: dict[str, str] = {}
    for text in texts:
        reason = protected_reason(text)
        if reason is None:
            translatable.append(text)
        else:
            protected[text] = reason
    return translatable, protected
