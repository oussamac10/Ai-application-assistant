from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.database.session import SessionLocal
from app.forms.models import FormField, FormTemplate, FormVersion
from app.main import app
from app.organizations.models import Organization, OrganizationMember


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


def _create_test_user(db: Session, email: str = "pub_org_owner@example.com") -> User:
    norm = email.lower().strip()
    existing = db.query(User).filter(User.normalized_email == norm).first()
    if existing:
        return existing
    user = User(
        email=email,
        normalized_email=norm,
        password_hash="testpasshash123",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_public_organization_directory_and_portal(db_session: Session) -> None:
    client = TestClient(app)

    user = _create_test_user(db_session, "public_test_admin@example.com")

    # 1. Create a verified public organization
    slug = "stadt-stuttgart-amt"
    existing_org = (
        db_session.query(Organization).filter(Organization.slug == slug).first()
    )
    if existing_org:
        db_session.delete(existing_org)
        db_session.commit()

    org = Organization(
        name="Stadtverwaltung Stuttgart — Bürgeramt",
        slug=slug,
        organization_type="government",
        verification_status="verified_official",
        is_verified_government=True,
        description="Offizielles Serviceportal der Landeshauptstadt Stuttgart für Melde- und Passwesen.",
        office_address="Eberhardstraße 37, 70173 Stuttgart",
        official_website_url="https://www.stuttgart.de",
        contact_email="buergeramt@stuttgart.de",
        supported_languages=["de", "en", "tr"],
    )
    db_session.add(org)
    db_session.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role="owner",
    )
    db_session.add(member)

    # 2. Add one published form template and one draft form template
    published_tpl = FormTemplate(
        organization_id=org.id,
        key="stuttgart-anmeldung-wohnung",
        name="Anmeldung einer Wohnung (§ 17 BMG)",
        category="buergeramt",
        submission_method="print_and_sign",
        instructions="Bringen Sie Ihren Personalausweis und die Bestätigung des Wohnungsgebers mit.",
        required_documents=[
            "Personalausweis",
            "Wohnungsgeberbestätigung",
        ],
    )
    db_session.add(published_tpl)
    db_session.flush()

    published_ver = FormVersion(
        form_template_id=published_tpl.id,
        version_number=1,
        status="published",
        source_language="de",
        supported_output_languages=["de", "en"],
        origin="predefined_template",
    )
    db_session.add(published_ver)
    db_session.flush()

    # Add a field to published version
    field = FormField(
        form_version_id=published_ver.id,
        key="applicant_full_name",
        field_type="string",
        required=True,
        requiredness="required",
        position=1,
        configuration={},
        question_key="personal.first_name",
    )
    db_session.add(field)

    # Add draft form (should NOT appear in public catalog)
    draft_tpl = FormTemplate(
        organization_id=org.id,
        key="stuttgart-draft-internal",
        name="Interner Verwaltungsentwurf",
        category="general",
    )
    db_session.add(draft_tpl)
    db_session.flush()

    draft_ver = FormVersion(
        form_template_id=draft_tpl.id,
        version_number=1,
        status="needs_review",
        source_language="de",
        supported_output_languages=["de"],
        origin="predefined_template",
    )
    db_session.add(draft_ver)
    db_session.commit()

    # 3. Test public organization directory (list)
    res_list = client.get("/api/public/organizations")
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert isinstance(data_list, list)

    stuttgart_entry = next((o for o in data_list if o["slug"] == slug), None)
    assert stuttgart_entry is not None
    assert stuttgart_entry["name"] == "Stadtverwaltung Stuttgart — Bürgeramt"
    assert stuttgart_entry["is_verified_government"] is True
    assert stuttgart_entry["organization_type"] == "government"
    assert stuttgart_entry["published_forms_count"] >= 1

    # Test search query
    res_search = client.get("/api/public/organizations?search=Stuttgart")
    assert res_search.status_code == 200
    search_matches = res_search.json()
    assert any(o["slug"] == slug for o in search_matches)

    # 4. Test public portal detail by slug
    res_detail = client.get(f"/api/public/organizations/{slug}")
    assert res_detail.status_code == 200
    data_detail = res_detail.json()
    assert data_detail["slug"] == slug
    assert data_detail["name"] == "Stadtverwaltung Stuttgart — Bürgeramt"
    assert data_detail["is_verified_government"] is True
    assert data_detail["contact_email"] == "buergeramt@stuttgart.de"
    assert data_detail["office_address"] == "Eberhardstraße 37, 70173 Stuttgart"

    # Only published forms must be present
    forms = data_detail["published_forms"]
    assert len(forms) == 1
    assert forms[0]["key"] == "stuttgart-anmeldung-wohnung"
    assert forms[0]["name"] == "Anmeldung einer Wohnung (§ 17 BMG)"
    assert forms[0]["category"] == "buergeramt"
    assert forms[0]["submission_method"] == "print_and_sign"
    assert "Wohnungsgeberbestätigung" in forms[0]["required_documents"]
    assert forms[0]["fields_count"] == 1

    # Verify draft template is NOT in the public forms list
    assert not any(f["key"] == "stuttgart-draft-internal" for f in forms)

    # 5. Test non-existent slug returns 404
    res_404 = client.get("/api/public/organizations/nonexistent-municipality-xyz")
    assert res_404.status_code == 404
