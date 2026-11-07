import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.session import SessionLocal
from app.forms.organization_service import OrganizationFormService
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> None:
    client.cookies.clear()
    client.headers.pop("X-CSRF-Token", None)
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE organizations CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_acroform_widget_label_extraction() -> None:
    """Verifies that PDF AcroForm checkboxes and text widgets extract authentic German labels

    instead of technical variable names like 'chkEinzug'.
    """
    pdf_path = "/fixtures/pdf/de-stuttgart-wohnungsgeberbestaetigung.pdf"
    if not os.path.exists(pdf_path):
        pdf_path = "fixtures/pdf/de-stuttgart-wohnungsgeberbestaetigung.pdf"
    assert os.path.exists(pdf_path), f"Fixture {pdf_path} not found"

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    db = SessionLocal()
    try:
        service = OrganizationFormService(db)
        fields = service._extract_fields_from_pdf_bytes(pdf_bytes)

        # 1. Verify pushbuttons (Print, Reset) were filtered out
        keys = [f["key"] for f in fields]
        assert "btdrucken" not in keys
        assert "zurucksetzen" not in keys

        # 2. Verify chkEinzug is boolean with authentic German label
        einzug_field = next(
            (
                f
                for f in fields
                if "einzug" in f["key"].lower() and f["field_type"] == "boolean"
            ),
            None,
        )
        assert einzug_field is not None
        assert "Einzugsbestätigung" in einzug_field["label"]
        assert "Bundesmeldegesetz" in einzug_field["label"]
        assert einzug_field["field_type"] == "boolean"

        # 3. Verify chkAuszug is boolean with authentic German label
        auszug_field = next(
            (
                f
                for f in fields
                if "auszug" in f["key"].lower() and f["field_type"] == "boolean"
            ),
            None,
        )
        assert auszug_field is not None
        assert "Auszugsbestätigung" in auszug_field["label"]
        assert auszug_field["field_type"] == "boolean"

        # 4. Verify address and name fields
        anschrift = next((f for f in fields if "anschrift1" in f["key"].lower()), None)
        assert anschrift is not None
        assert "Straße" in anschrift["label"] or "Anschrift" in anschrift["label"]
    finally:
        db.close()


def test_translate_field_api() -> None:
    """Verifies that the /translate-field endpoint translates field labels into citizen languages."""
    # Register/login user
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "field-translator@example.com",
            "password": "Password123!",
            "passwordConfirmation": "Password123!",
        },
    )
    assert reg.status_code == 201
    csrf = client.cookies.get("csrf_token")
    assert csrf

    # Translate label from German to Arabic and English
    res = client.post(
        "/api/organizations/current/forms/translate-field",
        headers={"X-CSRF-Token": csrf},
        json={
            "text": "Einzugsbestätigung des Wohnungsgebers nach § 19 Bundesmeldegesetz (BMG)",
            "source_language": "de",
            "target_languages": ["en", "ar"],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "translations" in data
    assert "en" in data["translations"]
    assert "ar" in data["translations"]
    assert len(data["translations"]["en"]) > 0
    assert len(data["translations"]["ar"]) > 0
