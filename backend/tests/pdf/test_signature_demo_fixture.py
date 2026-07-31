"""The signature demo form: reachable in development, absent in production.

The committed signature template and mapping were reachable only from tests, so
the flow they exist to prove — fill a field, sign or defer, export a PDF with
the signature in the right place — could not be walked in a browser.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import text

import app.main  # noqa: F401  registers every SQLAlchemy mapper once
from app.commands.load_signature_demo import (
    PDF_TEMPLATE_KEY,
    TEMPLATE_KEY,
    load_signature_demo_fixture,
)
from app.core.config import settings
from app.database.session import SessionLocal
from app.forms.models import FormTemplate


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
        yield
    finally:
        db.close()


@pytest.fixture(autouse=True)
def development_environment() -> Generator[None, None, None]:
    original = settings.ENVIRONMENT
    settings.ENVIRONMENT = "development"
    yield
    settings.ENVIRONMENT = original


def _template() -> FormTemplate | None:
    db = SessionLocal()
    try:
        return db.query(FormTemplate).filter_by(key=TEMPLATE_KEY).first()
    finally:
        db.close()


def test_the_demo_form_is_published_with_a_signature_field() -> None:
    load_signature_demo_fixture()

    db = SessionLocal()
    try:
        template = db.query(FormTemplate).filter_by(key=TEMPLATE_KEY).first()
        assert template is not None
        version = template.versions[0]
        assert version.status == "published"
        # Bound to the committed PDF, which is what gives the export a
        # signature rectangle to draw into.
        assert version.pdf_template_key == PDF_TEMPLATE_KEY

        by_key = {f.key: f for f in version.fields}
        assert by_key["applicant_name"].field_type == "person_name"
        assert by_key["applicant_signature"].field_type == "signature"
        # Required on purpose: a required signature is the case worth
        # demonstrating, because it still allows signing on paper.
        assert by_key["applicant_signature"].requiredness == "required"
    finally:
        db.close()


def test_running_the_command_twice_leaves_one_form() -> None:
    """Repeated fixture commands must not fill the form list with duplicates."""
    load_signature_demo_fixture()
    load_signature_demo_fixture()

    db = SessionLocal()
    try:
        templates = db.query(FormTemplate).filter_by(key=TEMPLATE_KEY).all()
        assert len(templates) == 1
        assert len(templates[0].versions) == 1
    finally:
        db.close()


def test_production_refuses_to_publish_the_demo_form() -> None:
    """A demo form in a public list is not cosmetic: someone would fill it in
    and export a document that means nothing."""
    settings.ENVIRONMENT = "production"

    with pytest.raises(SystemExit) as exc:
        load_signature_demo_fixture()

    assert exc.value.code == 1
    assert _template() is None


@pytest.mark.parametrize("value", ["prod", "PRODUCTION", " Production "])
def test_production_is_recognised_however_it_is_spelled(value: str) -> None:
    settings.ENVIRONMENT = value

    with pytest.raises(SystemExit):
        load_signature_demo_fixture()


def test_the_demo_form_maps_a_signature_rectangle() -> None:
    """Without one the export refuses to place the signature, which would make
    the demo prove the opposite of what it exists for."""
    from app.pdf.registry import PDFMappingLoader, PDFTemplateRegistry

    mapping = PDFMappingLoader(PDFTemplateRegistry()).load_mapping(PDF_TEMPLATE_KEY)

    signature = next(f for f in mapping.fields if f.field_key == "applicant_signature")
    assert signature.signature_rect is not None
    assert signature.page == 1
    # And the ordinary field is mapped beside it, so the demo exercises both
    # export paths at once.
    assert any(f.field_key == "applicant_name" for f in mapping.fields)
