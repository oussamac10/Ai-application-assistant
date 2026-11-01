import json
from collections.abc import Generator
from io import BytesIO

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.main import app


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


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _register_and_auth(client: TestClient, email: str) -> None:
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "passwordConfirmation": "SecurePassword123!",
        },
    )
    assert res.status_code == 201
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


def _login_existing_user(client: TestClient, email: str, db: Session) -> None:
    from app.auth.models import User
    from app.auth.security import hash_password

    user = db.query(User).filter_by(email=email).first()
    assert user is not None
    user.password_hash = hash_password("SecurePassword123!")
    db.commit()

    res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert res.status_code == 200
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


def _create_sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()

    # Add interactive AcroForm text widgets
    w1 = fitz.Widget()
    w1.rect = fitz.Rect(50, 100, 200, 120)
    w1.field_name = "Vorname"
    w1.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    page.add_widget(w1)

    w2 = fitz.Widget()
    w2.rect = fitz.Rect(50, 140, 200, 160)
    w2.field_name = "Nachname"
    w2.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    page.add_widget(w2)

    w3 = fitz.Widget()
    w3.rect = fitz.Rect(50, 180, 200, 200)
    w3.field_name = "Geburtsdatum"
    w3.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    page.add_widget(w3)

    return doc.tobytes()


def test_organization_form_upload_review_and_publish_flow(
    client: TestClient, db_session: Session
) -> None:
    # 1. Register owner of Stuttgart workspace
    _register_and_auth(client, "rathaus@stuttgart.de")

    # Initial list is empty
    list_res = client.get("/api/organizations/current/forms")
    assert list_res.status_code == 200
    assert list_res.json() == []

    # 2. Upload official form PDF
    sample_pdf = _create_sample_pdf()
    files = {"file": ("anmeldung.pdf", BytesIO(sample_pdf), "application/pdf")}
    data = {
        "name": "Wohnsitz Anmeldung",
        "category": "buergeramt",
        "submission_method": "in_person_counter",
        "instructions": "Bitte bringen Sie alle Originaldokumente zum Bürgeramt mit.",
        "required_documents": json.dumps(
            ["Personalausweis oder Reisepass", "Wohnungsgeberbestätigung"]
        ),
    }

    upload_res = client.post(
        "/api/organizations/current/forms/upload", files=files, data=data
    )
    assert upload_res.status_code == 201
    form_detail = upload_res.json()
    assert form_detail["name"] == "Wohnsitz Anmeldung"
    assert form_detail["category"] == "buergeramt"
    assert form_detail["status"] == "needs_review"
    assert len(form_detail["fields"]) >= 3
    assert form_detail["requiredDocuments"] == [
        "Personalausweis oder Reisepass",
        "Wohnungsgeberbestätigung",
    ]

    template_id = form_detail["templateId"]

    # 3. Check list shows the new form
    list_res = client.get("/api/organizations/current/forms")
    assert list_res.status_code == 200
    forms = list_res.json()
    assert len(forms) == 1
    assert forms[0]["id"] == template_id
    assert forms[0]["status"] == "needs_review"
    assert forms[0]["fieldsCount"] >= 3
    assert forms[0]["hasPdf"] is True

    # 4. Get Review Details
    review_res = client.get(f"/api/organizations/current/forms/{template_id}/review")
    assert review_res.status_code == 200
    detail = review_res.json()
    first_field = detail["fields"][0]
    field_id = first_field["id"]

    # 5. Update Field (e.g. rename or mark optional)
    field_patch = client.patch(
        f"/api/organizations/current/forms/{template_id}/fields/{field_id}",
        json={
            "requiredness": "optional",
            "translations": [
                {
                    "language": "de",
                    "label": "Rufname / Vorname",
                    "help_text": "Geben Sie alle Vornamen laut Pass an.",
                }
            ],
        },
    )
    assert field_patch.status_code == 200
    updated_field = field_patch.json()
    assert updated_field["requiredness"] == "optional"
    assert updated_field["translations"][0]["label"] == "Rufname / Vorname"

    # 6. Add a custom field to the schema
    new_field_res = client.post(
        f"/api/organizations/current/forms/{template_id}/fields",
        json={
            "key": "contact_phone",
            "fieldType": "phone",
            "requiredness": "optional",
            "position": 10,
            "questionKey": "contact.phone",
            "translations": [
                {"language": "de", "label": "Telefonnummer für Rückfragen"}
            ],
        },
    )
    assert new_field_res.status_code == 201
    custom_field_id = new_field_res.json()["id"]

    # 7. Reorder fields
    all_fids = [f["id"] for f in detail["fields"]] + [custom_field_id]
    reversed_fids = list(reversed(all_fids))
    reorder_res = client.post(
        f"/api/organizations/current/forms/{template_id}/reorder",
        json=reversed_fids,
    )
    assert reorder_res.status_code == 200

    # 8. Update Form Metadata
    meta_patch = client.patch(
        f"/api/organizations/current/forms/{template_id}/review",
        json={
            "description": "Offizielles Anmeldeformular der Landeshauptstadt Stuttgart.",
            "instructions": "Vollständig ausgefüllt vorlegen.",
            "reviewNotes": "Geprüft durch Bürgeramt Teamleitung.",
        },
    )
    assert meta_patch.status_code == 200
    assert (
        meta_patch.json()["description"]
        == "Offizielles Anmeldeformular der Landeshauptstadt Stuttgart."
    )
    assert meta_patch.json()["reviewNotes"] == "Geprüft durch Bürgeramt Teamleitung."

    # 9. Stream source PDF
    pdf_res = client.get(f"/api/organizations/current/forms/{template_id}/source-pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")

    # 10. Approve and Publish Form
    publish_res = client.post(f"/api/organizations/current/forms/{template_id}/publish")
    assert publish_res.status_code == 200
    assert publish_res.json()["status"] == "published"

    # Check that list reflects published status
    list_res2 = client.get("/api/organizations/current/forms")
    assert list_res2.json()[0]["status"] == "published"

    # 11. Archive Form
    archive_res = client.post(f"/api/organizations/current/forms/{template_id}/archive")
    assert archive_res.status_code == 200
    assert archive_res.json()["status"] == "archived"


def test_organization_form_rbac_and_tenant_isolation(
    client: TestClient, db_session: Session
) -> None:
    # 1. Stuttgart Owner
    _register_and_auth(client, "owner@stuttgart.de")
    sample_pdf = _create_sample_pdf()
    upload_res = client.post(
        "/api/organizations/current/forms/upload",
        files={"file": ("stuttgart.pdf", BytesIO(sample_pdf), "application/pdf")},
        data={"name": "Stuttgart Meldeschein"},
    )
    assert upload_res.status_code == 201
    stuttgart_form_id = upload_res.json()["templateId"]

    # 2. Invite a Viewer colleague to Stuttgart
    invite_res = client.post(
        "/api/organizations/current/members",
        json={"email": "viewer@stuttgart.de", "role": "viewer"},
    )
    assert invite_res.status_code == 201

    # 3. Create Berlin workspace
    client_berlin = TestClient(app)
    _register_and_auth(client_berlin, "rathaus@berlin.de")

    # Berlin cannot see Stuttgart's forms
    berlin_list = client_berlin.get("/api/organizations/current/forms")
    assert berlin_list.status_code == 200
    assert berlin_list.json() == []

    # Berlin cannot access Stuttgart's review endpoint
    berlin_access = client_berlin.get(
        f"/api/organizations/current/forms/{stuttgart_form_id}/review"
    )
    assert berlin_access.status_code == 404

    # 4. Log in as Viewer in Stuttgart
    client_viewer = TestClient(app)
    _login_existing_user(client_viewer, "viewer@stuttgart.de", db_session)

    # Viewer CAN view form list and review
    v_list = client_viewer.get("/api/organizations/current/forms")
    assert v_list.status_code == 200
    assert len(v_list.json()) == 1

    v_review = client_viewer.get(
        f"/api/organizations/current/forms/{stuttgart_form_id}/review"
    )
    assert v_review.status_code == 200

    # Viewer CANNOT upload a form (403 Forbidden)
    v_upload = client_viewer.post(
        "/api/organizations/current/forms/upload",
        files={"file": ("viewer.pdf", BytesIO(sample_pdf), "application/pdf")},
        data={"name": "Viewer Attempt"},
    )
    assert v_upload.status_code == 403

    # Viewer CANNOT publish a form (403 Forbidden)
    v_publish = client_viewer.post(
        f"/api/organizations/current/forms/{stuttgart_form_id}/publish"
    )
    assert v_publish.status_code == 403

    # Viewer CAN fetch page 1 preview PNG
    v_preview = client_viewer.get(
        f"/api/organizations/current/forms/{stuttgart_form_id}/pages/1/preview"
    )
    assert v_preview.status_code == 200
    assert v_preview.headers["content-type"] == "image/png"
    assert len(v_preview.content) > 100
    assert v_preview.content[:8] == b"\x89PNG\r\n\x1a\n"
