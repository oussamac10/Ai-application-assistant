"""Deterministic field context: currency from the label, proper nouns kept.

Both guard reported live defects — `stuttgart` returned transliterated into
Arabic, and `2000` on a field reading "en euros" returned as `USD 2000`.
"""

from __future__ import annotations

import pytest

from app.answers.normalization.context import (
    apply_currency_context,
    currency_from_label,
    is_proper_noun_field,
)

# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label",
    [
        "Revenu net mensuel en euros",
        "Coût total en euros",
        "Monatliche Grundmiete in Euro",
        "Amount in EUR",
        "Betrag (€)",
        "المبلغ باليورو",
    ],
)
def test_euro_labels_resolve_to_eur(label: str) -> None:
    assert currency_from_label(label) == "EUR"


def test_dollar_labels_resolve_to_usd() -> None:
    assert currency_from_label("Amount in USD") == "USD"
    assert currency_from_label("Total ($)") == "USD"


def test_a_label_naming_no_currency_returns_none() -> None:
    assert currency_from_label("Monthly Income") is None
    assert currency_from_label("") is None
    assert currency_from_label(None) is None


def test_a_euro_label_overrides_an_invented_usd() -> None:
    """The exact reported bug."""
    value, changed = apply_currency_context(
        {"amount": 2000, "currency": "USD"}, "Montant demandé en euros"
    )
    assert value == {"amount": 2000, "currency": "EUR"}
    assert changed is True


def test_a_matching_currency_is_left_alone() -> None:
    value, changed = apply_currency_context(
        {"amount": 2000, "currency": "EUR"}, "Montant en euros"
    )
    assert changed is False
    assert value == {"amount": 2000, "currency": "EUR"}


def test_no_context_anywhere_removes_an_invented_currency() -> None:
    """`2000` on a field that says nothing about currency must not become
    dollars."""
    value, changed = apply_currency_context(
        {"amount": 2000, "currency": "USD"}, "Monthly Income", "2000"
    )
    assert value == {"amount": 2000}
    assert changed is True


def test_a_currency_the_user_typed_is_kept() -> None:
    """The label names none, but the answer does — that is evidence, not an
    invention."""
    value, changed = apply_currency_context(
        {"amount": 1800, "currency": "EUR"}, "Monthly Income", "1800 EUR monthly"
    )
    assert value == {"amount": 1800, "currency": "EUR"}
    assert changed is False


def test_non_money_values_pass_through() -> None:
    assert apply_currency_context("Stuttgart", "City") == ("Stuttgart", False)
    assert apply_currency_context(None, "City") == (None, False)


# ---------------------------------------------------------------------------
# Proper nouns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label",
    [
        "Code postal, ville",
        "Ville",
        "Lieu de naissance",
        "Wohnort",
        "PLZ, Ort",
        "Full name",
        "Nom de l'employeur ou organisme",
        "Nom de la banque",
        "Kontoinhaber",
        "Adresse complète",
        "Signature du demandeur",
        "اسم العائلة",
        "المدينة",
    ],
)
def test_proper_noun_labels_are_protected(label: str) -> None:
    assert is_proper_noun_field(label) is True


@pytest.mark.parametrize(
    "label",
    [
        "Monthly income",
        "Date de naissance",
        "Pourquoi souhaitez-vous suivre cette formation ?",
        "Nombre de personnes",
    ],
)
def test_ordinary_labels_are_not_protected(label: str) -> None:
    assert is_proper_noun_field(label) is False


def test_typed_fields_are_never_treated_as_proper_nouns() -> None:
    """An email or a date has its own normalization; the label wording is
    irrelevant."""
    assert is_proper_noun_field("Name email", "email") is False
    assert is_proper_noun_field("Ort date", "date") is False
    assert is_proper_noun_field("City", "single_choice") is False


def test_missing_label_is_not_protected() -> None:
    assert is_proper_noun_field(None) is False
    assert is_proper_noun_field("") is False


# ---------------------------------------------------------------------------
# Reported regression: "2000" in a euro field proposed as "2000 USD"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label",
    [
        "Revenu net mensuel en euros",
        "Montant demande en euros *",
        "Cout total en euros",
        "Betrag in Euro",
        "Monatliches Nettoeinkommen in Euro",
        "Monthly income in euros",
        "Amount (EUR)",
        "Montant (€)",
        "المبلغ باليورو",
    ],
)
def test_a_euro_label_overrides_a_provider_that_answered_usd(label: str) -> None:
    """The reported failure: the label says euros, the user typed 2000, and the
    proposal came back "2000 USD".

    The label is authoritative. Correcting deterministically is more reliable
    than prompting harder, and `docs/claude/domain-rules.md` puts deterministic
    logic ahead of AI wherever language understanding is not genuinely
    required — reading the word "euros" is not language understanding.
    """
    corrected, changed = apply_currency_context(
        {"amount": 2000, "currency": "USD"}, label, "2000"
    )

    assert corrected["currency"] == "EUR"
    assert changed is True
    # The user's number is never touched.
    assert corrected["amount"] == 2000


def test_an_unknown_currency_context_never_defaults_to_usd() -> None:
    """No reliable currency means no currency. Inventing one is how "2000"
    became dollars on a form that said nothing about dollars."""
    corrected, changed = apply_currency_context(
        {"amount": 2000, "currency": "USD"}, "Monthly income", "2000"
    )

    assert "currency" not in corrected
    assert corrected["amount"] == 2000
    assert changed is True


def test_an_explicit_usd_label_is_preserved() -> None:
    corrected, changed = apply_currency_context(
        {"amount": 2000, "currency": "USD"}, "Monthly income in USD", "2000"
    )

    assert corrected["currency"] == "USD"
    assert changed is False


def test_a_currency_the_user_typed_is_preserved() -> None:
    """Real evidence from the user outranks the absence of a label hint."""
    corrected, changed = apply_currency_context(
        {"amount": 1800, "currency": "EUR"}, "Monthly income", "1800 EUR"
    )

    assert corrected["currency"] == "EUR"
    assert changed is False
