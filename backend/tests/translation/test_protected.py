"""Which text is withheld from the translator, and which is not.

Both directions matter and the failure modes are asymmetric: sending an IBAN
risks a silently mangled identifier, while withholding a real label leaves the
user reading a language they did not choose. The second is the bug this phase
exists to remove, so the false-positive cases below are the important ones.
"""

from __future__ import annotations

import pytest

from app.translation.protected import (
    is_protected,
    partition_protected,
    protected_reason,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("user@example.com", "email"),
        ("Max.Mustermann@sub.example.co.uk", "email"),
        ("https://example.com/form?a=1", "url"),
        ("www.example.com", "url"),
        ("DE89370400440532013000", "iban"),
        ("DE89 3704 0044 0532 0130 00", "iban"),
        ("COBADEFFXXX", "bic"),
        ("2026-07-30", "date"),
        ("2026-07-30T12:00", "date"),
        ("30.07.2026", "date"),
        ("07/30/2026", "date"),
        ("550e8400-e29b-41d4-a716-446655440000", "uuid"),
        ("personal.first_name", "machine_token"),
        ("form/section/field", "machine_token"),
        ("+49 30 12345678", "phone"),
        ("1.234,56 EUR", "numeric"),
        ("€ 850", "numeric"),
        ("   ", "empty"),
        ("12345", "numeric"),
        ("—", "no_letters"),
    ],
)
def test_identifiers_are_protected(text: str, expected: str) -> None:
    assert protected_reason(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "First name",
        "Vorname",
        "IBAN des Vermieters",
        "IBAN",
        "E-Mail-Adresse",
        "Wohn-Adresse",
        "Date of birth",
        "Geburtsdatum",
        "Telefonnummer",
        "Miete pro Monat in Euro",
        "الاسم الكامل",
        "تاريخ الميلاد",
        "Küche",
        "Badezimmer mit WC (abschließbar)",
        "Vermieter – Name",
        "PLZ, Ort",
        "Kaution (3 Monatsmieten)",
    ],
)
def test_real_labels_are_translatable(text: str) -> None:
    """Every one of these must reach the provider. A false positive here is
    how a user ends up reading the wrong language."""
    assert not is_protected(text), f"{text!r} was wrongly withheld from translation"


def test_partition_preserves_order_and_reports_reasons() -> None:
    translatable, protected = partition_protected(
        ["First name", "user@example.com", "Last name", "2026-01-01"]
    )

    assert translatable == ["First name", "Last name"]
    assert protected == {"user@example.com": "email", "2026-01-01": "date"}


def test_partition_does_not_deduplicate() -> None:
    """Dedup belongs to the service, which counts it; doing it here too would
    make those counts wrong."""
    translatable, _ = partition_protected(["Name", "Name"])
    assert translatable == ["Name", "Name"]
