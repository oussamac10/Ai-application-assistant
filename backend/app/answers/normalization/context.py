"""Deterministic field context: what a label tells us about its answer.

Two live defects motivated this, both caused by the AI being asked to normalize
an answer without being told anything about the field:

- A user typed `stuttgart` into "Code postal, ville" and the model returned it
  transliterated into Arabic. `.agents/AGENTS.md` forbids
  transliterating a name automatically — and a city, an employer and a bank are
  proper nouns exactly like a person's name.
- A user typed `2000` into "Revenu net mensuel en euros" and the model returned
  `USD 2000`. The label says euros. Nothing should have had to guess.

Both are answered from the label with plain code, per the domain rule that
deterministic logic beats AI wherever language understanding is not genuinely
required. Reading the word "euros" is not language understanding.

Nothing here inspects the user's answer — only the field's own label — so no
answer content influences the decision, and the same field always behaves the
same way.
"""

from __future__ import annotations

import re

# ISO 4217 codes we can name from a label. Symbols and words in every UI
# language, plus the Arabic and German forms real documents actually use.
_CURRENCY_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "EUR",
        (
            "€",
            "eur",
            "euro",
            "euros",
            "in euro",
            "in euros",
            "en euros",
            "en euro",
            "باليورو",
            "اليورو",
            "يورو",
        ),
    ),
    (
        "USD",
        ("$", "usd", "dollar", "dollars", "us-dollar", "دولار"),
    ),
    ("GBP", ("£", "gbp", "pound", "pounds", "sterling")),
    ("CHF", ("chf", "franken", "franc suisse")),
)

_PERIOD_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "monthly",
        (
            "monthly",
            "per month",
            "mensuel",
            "mensuelle",
            "mensuels",
            "mensuelles",
            "par mois",
            "monatlich",
            "monatliche",
            "monatlichen",
            "monatliches",
            "pro monat",
            "شهري",
            "شهريا",
            "شهرياً",
        ),
    ),
    (
        "yearly",
        (
            "yearly",
            "annual",
            "annually",
            "per year",
            "annuel",
            "annuelle",
            "annuels",
            "annuelles",
            "par an",
            "jährlich",
            "jährliche",
            "jährlichen",
            "jährliches",
            "pro jahr",
            "سنوي",
            "سنويا",
            "سنوياً",
        ),
    ),
    (
        "weekly",
        (
            "weekly",
            "per week",
            "hebdomadaire",
            "par semaine",
            "wöchentlich",
            "pro woche",
            "أسبوعي",
            "أسبوعيا",
            "أسبوعياً",
        ),
    ),
)

# Labels whose answer is a proper noun: a person, a place, or an organisation.
# Translating or transliterating any of these corrupts the answer — "Stuttgart"
# is "Stuttgart" on a German form regardless of the interface language.
_PROPER_NOUN_KEYWORDS: tuple[str, ...] = (
    # person
    "name",
    "vorname",
    "nachname",
    "familienname",
    "prénom",
    "nom",
    "الاسم",
    "اسم",
    "العائلة",
    # place
    "city",
    "town",
    "place",
    "ort",
    "stadt",
    "wohnort",
    "ville",
    "lieu",
    "geburtsort",
    "lieu de naissance",
    "المدينة",
    "مكان",
    "العنوان",
    "address",
    "adresse",
    "straße",
    "strasse",
    "street",
    "rue",
    # organisation
    "employer",
    "arbeitgeber",
    "employeur",
    "organisme",
    "organisation",
    "company",
    "firma",
    "unternehmen",
    "société",
    "bank",
    "banque",
    "titulaire",
    "kontoinhaber",
    "account holder",
    "المالك",
    "البنك",
    "شركة",
    "جهة",
    # signature
    "signature",
    "unterschrift",
    "توقيع",
)

# Field types whose value is never a translatable phrase.
_NEVER_TRANSLATED_TYPES = frozenset(
    {
        "email",
        "phone",
        "iban",
        "number",
        "integer",
        "decimal",
        "currency",
        "money",
        "date",
        "boolean",
        "single_choice",
        "multiple_choice",
        "radio",
        "select",
        "country",
        "signature",
        "file",
    }
)

_WORD_BOUNDARY_CACHE: dict[str, re.Pattern[str]] = {}


def _matches_word(haystack: str, needle: str) -> bool:
    """Whole-word match, so "name" does not fire inside "Nachname" by accident
    while still matching "Nachname" through its own entry. Non-ASCII needles
    (Arabic) fall back to substring matching, where word boundaries are not
    meaningful in the same way."""
    if not needle.isascii():
        return needle in haystack
    pattern = _WORD_BOUNDARY_CACHE.get(needle)
    if pattern is None:
        pattern = re.compile(rf"\b{re.escape(needle)}\b", re.IGNORECASE)
        _WORD_BOUNDARY_CACHE[needle] = pattern
    return bool(pattern.search(haystack))


def currency_from_label(label: str | None) -> str | None:
    """The ISO 4217 code a label names, or None.

    None is a real answer: an amount field that names no currency keeps its
    number and gets no currency at all. Inventing one is how `2000` became
    `USD 2000` on a form that said euros.
    """
    if not label:
        return None
    lowered = label.lower()
    for code, markers in _CURRENCY_MARKERS:
        for marker in markers:
            if not marker.isalpha() and marker in lowered:
                return code
            if marker.isalpha() and _matches_word(lowered, marker):
                return code
        # Multi-word markers ("in euros") contain spaces and are not
        # `isalpha()`; the substring branch above already covered them.
    return None


def period_from_label(label: str | None) -> str | None:
    """The recurring frequency (`monthly`, `yearly`, `weekly`) a label names, or None."""
    if not label:
        return None
    lowered = label.lower()
    for period, markers in _PERIOD_MARKERS:
        for marker in markers:
            if not marker.isalpha() and marker in lowered:
                return period
            if marker.isalpha() and _matches_word(lowered, marker):
                return period
    return None


def is_proper_noun_field(label: str | None, field_type: str | None = None) -> bool:
    """Whether this field's answer must be preserved verbatim.

    Deliberately keyword-based rather than value-based: a name is not
    recognisable from its spelling, and `domain-rules.md` forbids guessing.
    The *label* is what tells us the answer will be a proper noun.
    """
    if field_type and field_type.lower() in _NEVER_TRANSLATED_TYPES:
        return False
    if not label:
        return False
    lowered = label.lower()
    return any(_matches_word(lowered, keyword) for keyword in _PROPER_NOUN_KEYWORDS)


def apply_currency_context(
    normalized: object,
    label: str | None,
    original_answer: str | None = None,
) -> tuple[object, bool]:
    """Reconciles a money value's currency (and label-stated period) with the
    evidence that exists.

    Returns `(value, changed)`.

    - **The label names a currency** -> it wins. A provider that answered
      `USD` for a field reading "en euros" is simply wrong, and correcting it
      deterministically is more reliable than prompting harder.
    - **Neither the label nor the user's answer names one** -> a currency in
      the result was invented, and is removed. `2000` on a field that says
      nothing about currency must not silently become dollars.
    - **The answer names one but the label does not** -> left alone. The user
      wrote "1800 EUR"; that is real evidence, not an invention.
    - **The label names a recurring period (`mensuel`/`monthly`/`annuel`)** ->
      if `period` is present on the money dict and the user's answer did not
      name a different period, the label's period overrides an AI-guessed
      `"once"`.
    """
    if not isinstance(normalized, dict) or "amount" not in normalized:
        return normalized, False

    corrected = dict(normalized)
    changed = False

    expected = currency_from_label(label)
    current = corrected.get("currency")

    if expected is not None:
        if current != expected:
            corrected["currency"] = expected
            changed = True
    elif current and currency_from_label(original_answer) is None:
        corrected.pop("currency", None)
        changed = True

    if "period" in corrected:
        expected_period = period_from_label(label)
        if expected_period is not None and period_from_label(original_answer) is None:
            if corrected.get("period") != expected_period:
                corrected["period"] = expected_period
                changed = True

    if not changed:
        return normalized, False
    return corrected, True


def format_money_output(value: dict[str, object]) -> str:
    """Formats a normalized money dict for display/output without float `.0` or
    invented `once` period."""
    amt = value.get("amount")
    if isinstance(amt, float) and amt.is_integer():
        amt = int(amt)
    cur = value.get("currency")
    per = value.get("period")
    parts: list[str] = []
    if amt is not None and amt != "":
        parts.append(str(amt))
    if isinstance(cur, str) and cur.strip():
        parts.append(cur.strip())
    if isinstance(per, str) and per.strip() and per.strip().lower() != "once":
        parts.append(per.strip())
    return " ".join(parts)


def format_boolean_output(value: bool, language: str | None = None) -> str:
    """Formats a boolean value into localized Yes/No in the target language."""
    lang = (language or "en").lower()
    if value is True:
        if lang == "de":
            return "Ja"
        if lang == "fr":
            return "Oui"
        if lang == "ar":
            return "نعم"
        return "Yes"
    if lang == "de":
        return "Nein"
    if lang == "fr":
        return "Non"
    if lang == "ar":
        return "لا"
    return "No"
