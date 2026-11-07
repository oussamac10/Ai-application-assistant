from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.database.session import SessionLocal
from app.forms.models import FormField, FormTemplate, FormVersion
from app.forms.public_qr_service import (
    generate_counter_poster_pdf,
    generate_qr_png,
    generate_qr_svg,
)
from app.main import app
from app.organizations.models import Organization


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE organizations CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
        yield db
    finally:
        db.close()


def _create_test_data(db: Session) -> tuple[Organization, FormTemplate, FormVersion]:
    norm = "qr_test_admin@example.com"
    user = User(
        email=norm,
        normalized_email=norm,
        password_hash="testpasshash123",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    org = Organization(
        name="Stadtverwaltung Stuttgart",
        slug="stadt-stuttgart",
        organization_type="government",
        verification_status="verified_official",
        is_verified_government=True,
        office_address="Marktplatz 1, 70173 Stuttgart",
        official_website_url="https://www.stuttgart.de",
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    template = FormTemplate(
        organization_id=org.id,
        key="anmeldung-stuttgart",
        name="Anmeldung einer Wohnung (§ 17 BMG)",
        description="Official apartment registration form for Stuttgart residents.",
        category="residence",
        submission_method="print_and_sign",
        instructions="Please bring your landlord confirmation (Wohnungsgeberbestätigung).",
        required_documents=[
            "Wohnungsgeberbestätigung",
            "Personalausweis oder Reisepass",
        ],
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    version = FormVersion(
        form_template_id=template.id,
        version_number=1,
        status="published",
        source_language="de",
        supported_output_languages=["de", "en", "fr"],
        origin="predefined_template",
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    field = FormField(
        form_version_id=version.id,
        key="personal.first_name",
        field_type="text",
        required=True,
        position=1,
    )
    db.add(field)
    db.commit()

    return org, template, version


def test_qr_service_primitives() -> None:
    test_url = "http://localhost:3000/f/test-form"
    svg = generate_qr_svg(test_url, size=200)
    assert "<svg" in svg
    assert "</svg>" in svg

    png = generate_qr_png(test_url, size=200)
    assert isinstance(png, bytes)
    assert len(png) > 500
    assert png[:8] == b"\x89PNG\r\n\x1a\n"

    pdf = generate_counter_poster_pdf(
        form_name="Anmeldung einer Wohnung",
        target_url=test_url,
        org_name="Stadtverwaltung Stuttgart",
        is_verified_government=True,
    )
    assert isinstance(pdf, bytes)
    assert len(pdf) > 2000
    assert pdf.startswith(b"%PDF-")


def test_public_form_detail_endpoint(db_session: Session) -> None:
    client = TestClient(app)
    org, template, version = _create_test_data(db_session)

    # 1. Fetch by key
    res = client.get(f"/api/public/forms/{template.key}")
    assert res.status_code == 200
    data = res.json()
    assert data["key"] == "anmeldung-stuttgart"
    assert data["name"] == "Anmeldung einer Wohnung (§ 17 BMG)"
    assert data["active_version_id"] == version.id
    assert data["fields_count"] == 1
    assert data["organization"]["slug"] == "stadt-stuttgart"
    assert data["organization"]["is_verified_government"] is True
    assert data["share_url"] == "http://localhost:3000/f/anmeldung-stuttgart"
    assert "/qr?format=svg" in data["qr_svg_url"]
    assert "/qr?format=png" in data["qr_png_url"]
    assert "/counter-poster.pdf" in data["counter_poster_pdf_url"]

    # 2. Fetch by ID
    res_id = client.get(f"/api/public/forms/{template.id}")
    assert res_id.status_code == 200
    assert res_id.json()["key"] == template.key

    # 3. Fetch by org_slug/form_key
    res_composite = client.get(f"/api/public/forms/{org.slug}/{template.key}")
    assert res_composite.status_code == 200
    assert res_composite.json()["id"] == template.id

    # 4. 404 for nonexistent form
    res_404 = client.get("/api/public/forms/nonexistent-form-xyz")
    assert res_404.status_code == 404


def test_public_form_qr_endpoint(db_session: Session) -> None:
    client = TestClient(app)
    _, template, _ = _create_test_data(db_session)

    # 1. Request PNG QR code (default)
    res_png = client.get(f"/api/public/forms/{template.key}/qr")
    assert res_png.status_code == 200
    assert res_png.headers["content-type"] == "image/png"
    assert res_png.content[:8] == b"\x89PNG\r\n\x1a\n"

    # 2. Request SVG QR code
    res_svg = client.get(f"/api/public/forms/{template.key}/qr?format=svg")
    assert res_svg.status_code == 200
    assert "image/svg+xml" in res_svg.headers["content-type"]
    assert b"<svg" in res_svg.content


def test_public_form_counter_poster_pdf(db_session: Session) -> None:
    client = TestClient(app)
    org, template, _ = _create_test_data(db_session)

    res = client.get(f"/api/public/forms/{template.key}/counter-poster.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "inline; filename=" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")

    # Composite route
    res_comp = client.get(
        f"/api/public/forms/{org.slug}/{template.key}/counter-poster.pdf"
    )
    assert res_comp.status_code == 200
    assert res_comp.content.startswith(b"%PDF-")
