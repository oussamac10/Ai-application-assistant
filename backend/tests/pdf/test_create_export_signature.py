"""Signatures through `create_export` itself, using a committed template.

`test_signature_export_integration.py` drives `PypdfRenderer` directly with a
fixture built in-test. That proves the renderer works; it does not prove the
*service* reaches it, that a shipped mapping is well-formed, or that ownership
and cleanup behave when something fails.

These tests call the real service against `fixtures/pdf/signature-demo-v1.pdf`
and its committed mapping, then reopen whatever the service wrote.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import fitz
import pytest
from sqlalchemy import text

import app.main  # noqa: F401  registers every SQLAlchemy mapper once
from app.answers.models import FormAnswer
from app.answers.signatures import PENDING_MANUAL_SIGNATURE
from app.database.session import SessionLocal
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.pdf.services import PDFExportService
from app.pdf.signature_render import (
    SIGNATURE_INVALID,
    SIGNATURE_MAPPING_MISSING,
)
from app.sessions.services import SessionService, UnauthorizedError
from app.sessions.services import ValidationError as SessionValidationError

_TEMPLATE_KEY = "signature-demo-v1"
_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "pdf"

# The rectangle the committed mapping points at, in the top-left origin the
# renderer uses.
_RECT = (72.0, 220.0, 240.0, 70.0)

_STROKES = {
    "strokes": [[[0.0, 0.0], [150.0, 80.0], [300.0, 20.0]]],
    "width": 400.0,
    "height": 120.0,
}


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
        yield
    finally:
        db.close()


def _session_with_signature(
    signature_status: str,
    signature_value: Any = None,
    template_key: str = _TEMPLATE_KEY,
) -> dict[str, Any]:
    """A completed session ready to export: one text answer, one signature."""
    db = SessionLocal()
    try:
        forms = FormService(db)
        sessions = SessionService(db)

        template = forms.create_template(key="signature-demo", name="Signature demo")
        version = forms.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en"],
        )
        version.pdf_template_key = template_key
        db.commit()

        forms.add_field_to_draft(
            version.id,
            FieldCreate(
                key="applicant_name",
                field_type="person_name",
                requiredness="required",
                position=1,
                translations=[TranslationSchema(language="en", label="Full name")],
            ),
        )
        forms.add_field_to_draft(
            version.id,
            FieldCreate(
                key="applicant_signature",
                field_type="signature",
                requiredness="required",
                position=2,
                translations=[TranslationSchema(language="en", label="Signature")],
            ),
        )
        forms.publish_version(version.id)

        session, token = sessions.create_session(
            form_version_id=version.id, user_language="en", output_language="en"
        )
        db.commit()
        sessions.start_session(session.public_id, token)

        db.refresh(version)
        by_key = {f.key: f for f in version.fields}

        db.add(
            FormAnswer(
                session_id=session.id,
                field_id=by_key["applicant_name"].id,
                original_answer="Dupont",
                original_language="en",
                normalized_value={"fullName": "Dupont"},
                output_value="Dupont",
                status="confirmed",
                validation_status="valid",
                confirmed_by_user=True,
            )
        )
        db.add(
            FormAnswer(
                session_id=session.id,
                field_id=by_key["applicant_signature"].id,
                original_answer=None,
                original_language="en",
                normalized_value=signature_value,
                output_value=None,
                status=signature_status,
                validation_status="valid"
                if signature_status != PENDING_MANUAL_SIGNATURE
                else "not_checked",
                confirmed_by_user=signature_status == "confirmed",
            )
        )
        session.status = "ready_for_export"
        db.commit()

        return {"session_id": session.public_id, "token": token}
    finally:
        db.close()


def _export(setup: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    """Runs the real service and reads what a caller would see.

    Values are read inside the session: the ORM object detaches when it closes,
    and a test that touches it afterwards fails on refresh rather than on
    anything it meant to assert.
    """
    db = SessionLocal()
    try:
        export = PDFExportService(db).create_export(
            setup["session_id"], token if token is not None else setup["token"]
        )
        return {"status": export.status, "storage_path": export.storage_path}
    finally:
        db.close()


def _ink_in_rect(page) -> list[tuple[float, float]]:
    x, y, width, height = _RECT
    points: list[tuple[float, float]] = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            for element in item[1:]:
                if not (hasattr(element, "x") and hasattr(element, "y")):
                    continue
                if x <= element.x <= x + width and y <= element.y <= y + height:
                    points.append((element.x, element.y))
    return points


# ---------------------------------------------------------------------------
# The committed template
# ---------------------------------------------------------------------------


def test_the_committed_signature_mapping_loads_and_validates() -> None:
    """A broken mapping is a deployment mistake, and finding it when someone
    tries to download their completed form is the worst possible moment."""
    from app.pdf.registry import PDFMappingLoader, PDFTemplateRegistry

    mapping = PDFMappingLoader(PDFTemplateRegistry()).load_mapping(_TEMPLATE_KEY)

    signature = next(f for f in mapping.fields if f.field_key == "applicant_signature")
    assert signature.page == 1  # one-based
    assert signature.signature_rect == list(_RECT)


def test_the_committed_template_actually_has_that_area() -> None:
    """The mapping and the document must agree, or the signature lands
    somewhere the form did not intend."""
    document = fitz.open(_FIXTURES / f"{_TEMPLATE_KEY}.pdf")
    try:
        boxes = [
            g["rect"]
            for g in document[0].get_drawings()
            if g["rect"].width > 200 and g["rect"].height > 50
        ]
        assert boxes, "the template has no drawn signature area"
        box = boxes[0]
        assert (round(box.x0), round(box.y0)) == (72, 220)
    finally:
        document.close()


# ---------------------------------------------------------------------------
# Digital signature, full service path
# ---------------------------------------------------------------------------


def test_create_export_renders_a_digital_signature() -> None:
    setup = _session_with_signature("confirmed", _STROKES)

    export = _export(setup)

    assert export["status"] == "completed"
    document = fitz.open(export["storage_path"])
    try:
        assert _ink_in_rect(document[0]), "no signature ink in the mapped area"
        # The ordinary field is filled beside it.
        values = {w.field_name: w.field_value for w in document[0].widgets()}
        assert values.get("applicant_name") == "Dupont"
        # And the form's own content survives.
        assert "Applicant signature" in document[0].get_text()
    finally:
        document.close()
    Path(export["storage_path"]).unlink(missing_ok=True)


def test_the_signature_stays_inside_its_rectangle() -> None:
    setup = _session_with_signature("confirmed", _STROKES)

    export = _export(setup)

    document = fitz.open(export["storage_path"])
    try:
        all_points = [
            (element.x, element.y)
            for drawing in document[0].get_drawings()
            for item in drawing["items"]
            for element in item[1:]
            if hasattr(element, "x") and hasattr(element, "y")
        ]
        inside = _ink_in_rect(document[0])
        # The template draws its own box, so not every point is signature ink —
        # but every point the signature added is inside the rectangle.
        assert len(inside) >= 3
        x, y, width, height = _RECT
        stray = [
            (px, py)
            for px, py in all_points
            if not (x - 1 <= px <= x + width + 1 and y - 1 <= py <= y + height + 1)
        ]
        assert stray == [], "signature ink escaped the mapped rectangle"
    finally:
        document.close()
    Path(export["storage_path"]).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Sign after printing, full service path
# ---------------------------------------------------------------------------


def test_create_export_leaves_a_deferred_signature_blank() -> None:
    """Intentionally blank — no placeholder, no stamp. The box is left exactly
    as the form's author drew it."""
    setup = _session_with_signature(PENDING_MANUAL_SIGNATURE, None)

    export = _export(setup)

    assert export["status"] == "completed"
    document = fitz.open(export["storage_path"])
    try:
        template = fitz.open(_FIXTURES / f"{_TEMPLATE_KEY}.pdf")
        try:
            # Exactly as many drawings as the untouched template: nothing was
            # added inside the signature area, and nothing was removed.
            assert len(document[0].get_drawings()) == len(template[0].get_drawings())
        finally:
            template.close()
        # The original box is still there, and the other answers exported.
        assert "Applicant signature" in document[0].get_text()
        values = {w.field_name: w.field_value for w in document[0].widgets()}
        assert values.get("applicant_name") == "Dupont"
    finally:
        document.close()
    Path(export["storage_path"]).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Failures
# ---------------------------------------------------------------------------


def test_a_template_without_a_signature_area_refuses_to_guess() -> None:
    """`basic-registration-v1` maps no signature rectangle. Placing the
    signature somewhere plausible would be worse than declining."""
    setup = _session_with_signature(
        "confirmed", _STROKES, template_key="basic-registration-v1"
    )

    with pytest.raises(SessionValidationError) as exc:
        _export(setup)

    assert getattr(exc.value, "error_code", None) == SIGNATURE_MAPPING_MISSING


@pytest.mark.parametrize(
    "payload",
    [
        # Out of canvas, non-numeric, and structurally wrong. NaN and infinity
        # are absent on purpose: PostgreSQL will not store them in a JSON
        # column, so a row can never hold them — they are covered where they
        # *can* arrive, at the renderer boundary
        # (`test_signature_render.py`).
        {"strokes": [[[9999.0, 1.0]]], "width": 100.0, "height": 100.0},
        {"strokes": [[["x", 1.0]]], "width": 100.0, "height": 100.0},
        {"strokes": [], "width": 100.0, "height": 100.0},
        {"strokes": [[[1.0]]], "width": 100.0, "height": 100.0},
    ],
)
def test_a_malformed_signature_fails_the_export_safely(payload: Any) -> None:
    setup = _session_with_signature("confirmed", payload)

    with pytest.raises(SessionValidationError) as exc:
        _export(setup)

    assert getattr(exc.value, "error_code", None) == SIGNATURE_INVALID


def test_a_failed_export_leaves_no_downloadable_file() -> None:
    """A half-written export contains some fields and no signature. Serving it
    would hand someone a document that looks complete and is not."""
    setup = _session_with_signature(
        "confirmed", {"strokes": [[[9999.0, 1.0]]], "width": 10.0, "height": 10.0}
    )

    with pytest.raises(SessionValidationError):
        _export(setup)

    db = SessionLocal()
    try:
        from app.pdf.models import FormExport

        exports = db.query(FormExport).all()
        for export in exports:
            assert export.status == "failed"
            assert not Path(export.storage_path).exists()
    finally:
        db.close()


def test_an_export_error_never_exposes_signature_data() -> None:
    setup = _session_with_signature(
        "confirmed",
        {"strokes": [[[5150.0, 4040.0]]], "width": 10.0, "height": 10.0},
    )

    with pytest.raises(SessionValidationError) as exc:
        _export(setup)

    message = str(exc.value)
    assert "5150" not in message
    assert "4040" not in message
    # Nor an internal path.
    assert "/tmp/" not in message


def test_another_sessions_token_cannot_export() -> None:
    setup = _session_with_signature("confirmed", _STROKES)

    with pytest.raises(UnauthorizedError):
        _export(setup, token="someone-elses-token")


@pytest.mark.parametrize("env_value", ["production", "prod", " PRODUCTION "])
def test_production_refuses_to_publish_the_demo_form(env_value: str) -> None:
    from app.commands.load_signature_demo import load_signature_demo_fixture
    from app.core.config import settings

    original = settings.ENVIRONMENT
    settings.ENVIRONMENT = env_value
    try:
        with pytest.raises(SystemExit):
            load_signature_demo_fixture()
    finally:
        settings.ENVIRONMENT = original
