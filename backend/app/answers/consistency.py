"""Deterministic cross-field consistency warnings for the Verification Studio (`Phase S2-03`).

Strictly deterministic Python checks (zero AI calls, zero legal/eligibility conclusions):
surfaces factual contradictions across confirmed/draft answers so applicants can catch typos
before generating the final PDF.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

_BIRTH_KEYS = frozenset(
    {
        "person.date_of_birth",
        "personal.date_of_birth",
        "date_of_birth",
        "birth_date",
        "geburtsdatum",
        "date_de_naissance",
    }
)
_MOVE_IN_KEYS = frozenset(
    {
        "residence.move_in_date",
        "move_in_date",
        "einzugsdatum",
        "einzug_am",
        "am_einzug_datum",
        "date_emmenagement",
    }
)
_START_KEYS = frozenset(
    {
        "start_date",
        "employment.start_date",
        "lease.start_date",
        "beginn",
        "vertragsbeginn",
    }
)
_END_KEYS = frozenset(
    {
        "end_date",
        "employment.end_date",
        "lease.end_date",
        "move_out_date",
        "residence.move_out_date",
        "auszugsdatum",
        "vertragsende",
    }
)
_COUNTRY_KEYS = frozenset(
    {
        "address.country",
        "country",
        "land",
        "pays",
    }
)
_POSTAL_KEYS = frozenset(
    {
        "address.postal_code",
        "postal_code",
        "postleitzahl",
        "plz",
        "zip",
        "zip_code",
        "code_postal",
    }
)

_POSTAL_RULES_BY_COUNTRY: dict[str, re.Pattern[str]] = {
    "DE": re.compile(r"^\d{5}$"),
    "FR": re.compile(r"^\d{5}$"),
    "ES": re.compile(r"^\d{5}$"),
    "IT": re.compile(r"^\d{5}$"),
    "AT": re.compile(r"^\d{4}$"),
    "CH": re.compile(r"^\d{4}$"),
    "BE": re.compile(r"^\d{4}$"),
}

_MESSAGES: dict[str, dict[str, str]] = {
    "birth_date_in_future": {
        "en": "The date of birth is in the future. Please double-check the year.",
        "de": "Das Geburtsdatum liegt in der Zukunft. Bitte prüfen Sie die Jahreszahl.",
        "fr": "La date de naissance est dans le futur. Veuillez vérifier l'année.",
        "ar": "تاريخ الميلاد يقع في المستقبل. يرجى التحقق من السنة.",
    },
    "move_in_before_birth_date": {
        "en": "The move-in date is earlier than the date of birth. Please verify both dates.",
        "de": "Das Einzugsdatum liegt vor dem Geburtsdatum. Bitte prüfen Sie beide Daten.",
        "fr": "La date d'emménagement est antérieure à la date de naissance. Veuillez vérifier les deux dates.",
        "ar": "تاريخ الانتقال أقدم من تاريخ الميلاد. يرجى مراجعة التاريخين.",
    },
    "end_date_before_start_date": {
        "en": "The end date is earlier than the start date. Please check the date order.",
        "de": "Das Enddatum liegt vor dem Anfangsdatum. Bitte prüfen Sie die Reihenfolge der Daten.",
        "fr": "La date de fin est antérieure à la date de début. Veuillez vérifier l'ordre des dates.",
        "ar": "تاريخ الانتهاء يسبق تاريخ البدء. يرجى التحقق من ترتيب التواريخ.",
    },
    "postal_code_country_mismatch": {
        "en": "The postal code format does not match the selected country code.",
        "de": "Das Format der Postleitzahl passt nicht zum ausgewählten Land.",
        "fr": "Le format du code postal ne correspond pas au pays sélectionné.",
        "ar": "تنسيق الرمز البريدي لا يتطابق مع رمز الدولة المحدد.",
    },
}


def _msg(code: str, user_language: str) -> str:
    lang = (user_language or "en").strip().lower()[:2]
    table = _MESSAGES.get(code, {})
    return table.get(lang) or table.get("en", code)


def _extract_scalar_str(answer: Any) -> str | None:
    if answer is None:
        return None
    status = getattr(answer, "status", "unanswered")
    if status in ("unanswered", "skipped"):
        return None
    val = getattr(answer, "normalized_value", None)
    if isinstance(val, str) and val.strip():
        return val.strip()
    orig = getattr(answer, "original_answer", None)
    if isinstance(orig, str) and orig.strip():
        return orig.strip()
    return None


def _parse_iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _tokens_for_field(field: Any) -> set[str]:
    tokens: set[str] = set()
    q_key = getattr(field, "question_key", None)
    if q_key:
        tokens.add(str(q_key).strip().lower())
    f_key = getattr(field, "key", None)
    if f_key:
        cleaned = re.sub(r"_\d+$", "", str(f_key).strip().lower())
        tokens.add(str(f_key).strip().lower())
        tokens.add(cleaned)
    return tokens


def evaluate_consistency_warnings(
    version: Any,
    answers: dict[str, Any],
    user_language: str = "en",
) -> list[dict[str, Any]]:
    fields = list(getattr(version, "fields", []) or [])
    if not fields:
        return []

    today = datetime.now(UTC).date()
    warnings: list[dict[str, Any]] = []

    birth_entry: tuple[str, date] | None = None
    move_in_entry: tuple[str, date] | None = None
    start_entry: tuple[str, date] | None = None
    end_entry: tuple[str, date] | None = None
    country_entry: tuple[str, str] | None = None
    postal_entry: tuple[str, str] | None = None

    for field in fields:
        ans = answers.get(field.id)
        raw_val = _extract_scalar_str(ans)
        if not raw_val:
            continue

        tokens = _tokens_for_field(field)

        if tokens & _BIRTH_KEYS:
            parsed = _parse_iso_date(raw_val)
            if parsed is not None:
                birth_entry = (field.key, parsed)
                if parsed > today:
                    warnings.append(
                        {
                            "code": "birth_date_in_future",
                            "severity": "warning",
                            "field_keys": [field.key],
                            "message": _msg("birth_date_in_future", user_language),
                        }
                    )

        if tokens & _MOVE_IN_KEYS:
            parsed = _parse_iso_date(raw_val)
            if parsed is not None and move_in_entry is None:
                move_in_entry = (field.key, parsed)

        if tokens & _START_KEYS:
            parsed = _parse_iso_date(raw_val)
            if parsed is not None and start_entry is None:
                start_entry = (field.key, parsed)

        if tokens & _END_KEYS:
            parsed = _parse_iso_date(raw_val)
            if parsed is not None and end_entry is None:
                end_entry = (field.key, parsed)

        if tokens & _COUNTRY_KEYS and country_entry is None:
            country_code = raw_val.strip().upper()
            if country_code in ("GERMANY", "DEUTSCHLAND", "ALLEMAGNE"):
                country_code = "DE"
            elif country_code in ("FRANCE", "FRANKREICH"):
                country_code = "FR"
            elif country_code in ("AUSTRIA", "ÖSTERREICH", "OESTERREICH"):
                country_code = "AT"
            elif country_code in ("SWITZERLAND", "SCHWEIZ", "SUISSE"):
                country_code = "CH"
            country_entry = (field.key, country_code)

        if tokens & _POSTAL_KEYS and postal_entry is None:
            postal_entry = (field.key, raw_val.strip())

    if birth_entry and move_in_entry:
        dob_key, dob_val = birth_entry
        move_key, move_val = move_in_entry
        if move_val < dob_val:
            warnings.append(
                {
                    "code": "move_in_before_birth_date",
                    "severity": "warning",
                    "field_keys": [dob_key, move_key],
                    "message": _msg("move_in_before_birth_date", user_language),
                }
            )

    effective_start = start_entry or move_in_entry
    if effective_start and end_entry:
        s_key, s_val = effective_start
        e_key, e_val = end_entry
        if s_key != e_key and e_val < s_val:
            warnings.append(
                {
                    "code": "end_date_before_start_date",
                    "severity": "warning",
                    "field_keys": [s_key, e_key],
                    "message": _msg("end_date_before_start_date", user_language),
                }
            )

    if country_entry and postal_entry:
        c_key, c_code = country_entry
        p_key, p_val = postal_entry
        pattern = _POSTAL_RULES_BY_COUNTRY.get(c_code)
        if pattern is not None and not pattern.match(p_val):
            warnings.append(
                {
                    "code": "postal_code_country_mismatch",
                    "severity": "warning",
                    "field_keys": [p_key, c_key],
                    "message": _msg("postal_code_country_mismatch", user_language),
                }
            )

    return warnings
