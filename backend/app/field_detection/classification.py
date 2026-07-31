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
    ("sign here", "signature"),
    ("signed by", "signature"),
    # Arabic. Matched as substrings because Arabic attaches the definite
    # article and prepositions directly to the noun ("التوقيع" is "the
    # signature"), so a word-boundary rule would miss every real occurrence.
    ("التوقيع", "signature"),
    ("توقيع", "signature"),
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
    # German keyword rules (deterministic — see docs/field-detection.md).
    # Ordered before the generic fallbacks below so e.g. "unterschrift"
    # (signature) is never mistaken for "schrift"-adjacent text matches.
    ("unterschrift", "signature"),
    ("unterzeichnung", "signature"),
    ("e-mail-adresse", "email"),
    ("telefon", "phone"),
    ("handynummer", "phone"),
    ("geburtsdatum", "date"),
    ("datum", "date"),
    ("beginn", "date"),
    ("beginnt", "date"),
    ("endet", "date"),
    ("ablauf", "date"),
    ("straße", "address"),
    ("strasse", "address"),
    ("hausnummer", "address"),
    ("plz", "address"),
    ("postleitzahl", "address"),
    ("wohnort", "address"),
    ("anschrift", "address"),
    ("miete", "currency"),
    ("kaution", "currency"),
    ("nebenkosten", "currency"),
    ("betriebskosten", "currency"),
    ("heizkosten", "currency"),
    ("vorauszahlung", "currency"),
    ("euro", "currency"),
    ("gesamtmiete", "currency"),
    ("anzahl", "number"),
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

# A "blank run" is a fillable-input placeholder rendered as repeated
# punctuation rather than an AcroForm widget or a drawn line: a run of
# dots, the Unicode ellipsis character, middle dots, underscores, or
# hyphens (optionally separated by plain spaces, since some exporters emit
# "word"-tokenized runs like ". . . . ."). Deliberately character-based
# (not tied to any one document's exact glyph) and requires a minimum
# length so ordinary punctuation ("...", a single "-", an em dash in prose)
# is never mistaken for a blank input area.
_BLANK_RUN_CHARS = frozenset(".…·_-")
_MIN_BLANK_RUN_LENGTH = 3


def is_blank_run(text: str) -> bool:
    """True if `text` is (once spaces are removed) entirely made of blank-
    marker characters and at least `_MIN_BLANK_RUN_LENGTH` characters long."""
    stripped = text.strip()
    if not stripped:
        return False
    non_space = stripped.replace(" ", "")
    if len(non_space) < _MIN_BLANK_RUN_LENGTH:
        return False
    return all(ch in _BLANK_RUN_CHARS for ch in non_space)


def starts_with_blank_run(text: str) -> bool:
    """True if `text` *begins* with a blank-marker run, i.e. the input area
    comes first and any trailing words are a suffix of the blank rather
    than a label (e.g. a signature line rendered "…………………, den"). Such a
    segment carries no usable label and must not become a question."""
    stripped = text.strip()
    leading = 0
    for ch in stripped:
        if ch in _BLANK_RUN_CHARS:
            leading += 1
        else:
            break
    return leading >= _MIN_BLANK_RUN_LENGTH


# A colon-terminated segment with more words than this reads as a prose
# sentence that merely happens to end in a colon (e.g. "...bindend sind und
# keiner weiteren Form bedürfen als der Schriftform:" introducing a list)
# rather than a short field label ("IBAN:", "Straße, Nr.:") — never treated
# as a field regardless of confidence.
_MAX_LABEL_WORD_COUNT = 6


def is_probably_prose_label(label_text: str) -> bool:
    return len(label_text.split()) > _MAX_LABEL_WORD_COUNT


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


_KEYWORD_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _keyword_matches(keyword: str, lowered_label: str) -> bool:
    """Matches `keyword` as a whole word, with an optional trailing "s"
    for simple English plurals ("comment"/"comments",
    "amount"/"amounts") — but never mid-word or as a bare prefix.
    German's heavy compounding otherwise produces false positives: the
    substring "miete" is both inside "Vermieter" (no boundary before it —
    correctly rejected) *and* is a literal prefix of "Mieter" ("miete" +
    "r") — a prefix-only match would misclassify a tenant *name* field as
    a currency field, so the end of the match must also land on a real
    word boundary (whole word, or whole word + "s"), not merely "keyword
    optionally followed by more letters". `\\b` correctly respects
    Unicode letters (umlauts, ß) for `str` patterns."""
    pattern = _KEYWORD_PATTERN_CACHE.get(keyword)
    if pattern is None:
        pattern = re.compile(rf"\b{re.escape(keyword)}s?\b")
        _KEYWORD_PATTERN_CACHE[keyword] = pattern
    return pattern.search(lowered_label) is not None


# Concept groups for compound-label detection. A label naming two of these is
# asking for two different things in one box, and no single subtype can
# validate it correctly.
_CONCEPT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "postal_code",
        (
            "postal code",
            "post code",
            "postcode",
            "zip",
            "plz",
            "code postal",
            "الرمز البريدي",
        ),
    ),
    ("city", ("city", "town", "ort", "stadt", "ville", "المدينة")),
    ("place", ("place", "lieu", "ort", "مكان")),
    ("date", ("date", "datum", "تاريخ")),
    ("first_name", ("first name", "given name", "vorname", "prénom", "الاسم الأول")),
    (
        "last_name",
        (
            "last name",
            "surname",
            "family name",
            "nachname",
            "familienname",
            "nom de famille",
            "اسم العائلة",
        ),
    ),
    ("street", ("street", "straße", "strasse", "rue", "شارع")),
    (
        "house_number",
        ("house number", "hausnummer", "nr.", "no.", "numéro", "رقم المنزل"),
    ),
    ("iban", ("iban",)),
    (
        "account_number",
        ("account number", "kontonummer", "numéro de compte", "رقم الحساب"),
    ),
    ("bic", ("bic", "swift")),
)


# Parts of one postal address. A label naming several of these is not two
# questions crammed together — it is an address, and `address` accepts free
# text. "Im Haus (Ort, Straße, Haus-Nr., Etage)" and "Code postal, ville" are
# both this shape.
_ADDRESS_CONCEPTS = frozenset(
    {"postal_code", "city", "street", "house_number", "place"}
)


def compound_concepts(label_text: str) -> tuple[str, ...]:
    """The distinct concepts a label names, when it names more than one.

    "Code postal, ville" names a postal code *and* a city; "Lieu et date" a
    place *and* a date. Returns an empty tuple for an ordinary single-concept
    label.
    """
    lowered = label_text.strip().lower()
    if not lowered:
        return ()
    found: list[str] = []
    for concept, keywords in _CONCEPT_KEYWORDS:
        if concept in found:
            continue
        if any(_keyword_matches(keyword, lowered) for keyword in keywords):
            found.append(concept)
    # "place" and "city" overlap by design (German "Ort" is both); collapsing
    # them prevents a single word looking like two concepts.
    if "place" in found and "city" in found:
        found.remove("place")
    return tuple(found) if len(found) > 1 else ()


def is_compound_label(label_text: str) -> bool:
    return bool(compound_concepts(label_text))


def classify_label(label_text: str) -> str:
    """Guesses a field_type from label wording alone. Returns "text" when
    nothing matches — never invents a more specific type from weak evidence.
    """
    lowered = label_text.strip().lower()
    if not lowered:
        return "text"

    # A label naming two concepts usually gets no subtype at all: no single
    # validator is correct for "Lieu et date" or "Prénom Nom de famille".
    #
    # The exception is a combination that genuinely composes into one known
    # type — a postal code with a city, or a street with a house number, is an
    # address. Those keep `address`, which accepts free text; the reason
    # "70188, Stuttgart" was rejected was not the type but an over-strict
    # address validator demanding a street, fixed in
    # app/answers/validation/validation.py.
    concepts = compound_concepts(lowered)
    if concepts and not set(concepts) <= _ADDRESS_CONCEPTS:
        return "text"

    for keyword, field_type in _LABEL_KEYWORD_RULES:
        if _keyword_matches(keyword, lowered):
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
