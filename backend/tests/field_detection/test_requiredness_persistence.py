"""Requiredness must survive the whole way from the document to the client.

Detecting three states is worthless if the pipeline stores a boolean: the
detector said "the form marked nothing", `FormField.required` said `True`
because that was its default, and the user was blocked on a question the
document never asked. These tests pin each hop.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy import text

from app.database.session import SessionLocal
from app.field_detection.question_bridge import _resolve_requiredness
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService, ValidationError, resolve_requiredness


class _Detected:
    """The two attributes `_resolve_requiredness` reads."""

    def __init__(self, label: str, required: bool | None) -> None:
        self.label = label
        self.required = required


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
        yield
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Detection -> three states
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,acroform,expected",
    [
        ("Nom de famille", None, "unknown"),
        ("Nom de famille *", None, "required"),
        ("Deuxième prénom (facultatif)", None, "optional"),
        ("Nom de famille", True, "required"),
        ("Nom de famille", False, "optional"),
    ],
)
def test_detection_resolves_three_states(
    label: str, acroform: bool | None, expected: str
) -> None:
    assert _resolve_requiredness(_Detected(label, acroform)) == expected


def test_an_unmarked_field_is_never_resolved_to_required() -> None:
    """The regression in one line: absence of evidence used to mean required."""
    assert _resolve_requiredness(_Detected("Nom de famille", None)) != "required"


# ---------------------------------------------------------------------------
# The boolean stays consistent, and never outvotes the richer value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "requiredness,required,expected",
    [
        # The richer value wins, even against the boolean's `True` default —
        # which is exactly the collapse this replaces.
        ("unknown", True, ("unknown", False)),
        ("optional", True, ("optional", False)),
        ("required", False, ("required", True)),
        # Legacy callers that only know the boolean still work.
        (None, True, ("required", True)),
        (None, False, ("optional", False)),
        (None, None, ("unknown", False)),
    ],
)
def test_resolve_requiredness_pairs(
    requiredness: str | None, required: bool | None, expected: tuple[str, bool]
) -> None:
    assert resolve_requiredness(requiredness, required) == expected


def test_an_unrecognised_state_is_rejected_rather_than_guessed() -> None:
    with pytest.raises(ValidationError):
        resolve_requiredness("maybe", True)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _add_field(**kwargs: Any) -> Any:
    db = SessionLocal()
    try:
        service = FormService(db)
        template = service.create_template(key="persist-test", name="Persist test")
        version = service.create_draft_version(
            form_template_id=template.id,
            source_language="fr",
            supported_output_languages=["fr"],
        )
        return service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="nom_de_famille",
                field_type="string",
                position=1,
                translations=[TranslationSchema(language="fr", label="Nom de famille")],
                **kwargs,
            ),
        )
    finally:
        db.close()


def test_unknown_is_stored_as_unknown_not_as_required() -> None:
    field = _add_field(requiredness="unknown")

    assert field.requiredness == "unknown"
    assert field.required is False


def test_required_keeps_the_legacy_boolean_in_sync() -> None:
    field = _add_field(requiredness="required")

    assert field.requiredness == "required"
    assert field.required is True


def test_a_template_field_declaring_only_the_boolean_stays_required() -> None:
    """Hand-authored templates say `required=True` and mean it; the default
    must not be reinterpreted as "nothing was said"."""
    field = _add_field(required=True)

    assert field.requiredness == "required"
    assert field.required is True
