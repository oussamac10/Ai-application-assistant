from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.database.session import SessionLocal
from app.forms.models import FormField, FormTemplate, FormVersion
from app.main import app
from app.organizations.models import (
    Organization,
    OrganizationCategory,
    OrganizationMember,
)

PASSWORD = "AgencySecretPassword123!"


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE organizations CASCADE"))
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
        yield db
    finally:
        db.close()


def _create_user(db: Session, email: str) -> User:
    norm = email.lower().strip()
    user = User(
        email=email,
        normalized_email=norm,
        password_hash="testhash123",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _register_user(c: TestClient, email: str) -> None:
    res = c.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "passwordConfirmation": PASSWORD,
        },
    )
    assert res.status_code == 201


def _csrf(c: TestClient) -> str:
    token = c.cookies.get("csrf_token")
    assert token
    return token


def test_organization_categories_crud_and_seeding(db_session: Session) -> None:
    client = TestClient(app)
    _register_user(client, "cat_owner@example.com")
    csrf_token = _csrf(client)
    headers = {"x-csrf-token": csrf_token}

    # 1. Fetching categories when empty auto-seeds standard municipal categories
    res = client.get("/api/organizations/current/categories")
    assert res.status_code == 200
    categories = res.json()
    assert len(categories) >= 6
    housing_cat = next(
        (c for c in categories if c["slug"] == "housing-residence"), None
    )
    assert housing_cat is not None
    assert housing_cat["name"] == "Wohnen & Meldewesen"
    assert housing_cat["icon"] == "Home"
    assert "en" in housing_cat["translations"]
    assert housing_cat["translations"]["en"]["name"] == "Housing & Residence"
    assert "ar" in housing_cat["translations"]
    assert housing_cat["translations"]["ar"]["name"] == "السكن وتسجيل الإقامة"

    # 2. Create a new custom category
    create_payload = {
        "name": "Umwelt & Abfallwirtschaft",
        "slug": "waste-environment",
        "icon": "Sparkles",
        "description": "Waste disposal, recycling, and environmental services.",
        "translations": {
            "en": {
                "name": "Environment & Waste Management",
                "description": "Recycling and waste disposal.",
            },
            "de": {
                "name": "Umwelt & Abfallwirtschaft",
                "description": "Müllabfuhr und Recycling.",
            },
        },
        "sort_order": 90,
        "is_active": True,
    }
    create_res = client.post(
        "/api/organizations/current/categories",
        json=create_payload,
        headers=headers,
    )
    assert create_res.status_code == 201
    new_cat = create_res.json()
    assert new_cat["name"] == "Umwelt & Abfallwirtschaft"
    assert new_cat["slug"] == "waste-environment"
    new_cat_id = new_cat["id"]

    # 3. Update the category
    update_res = client.put(
        f"/api/organizations/current/categories/{new_cat_id}",
        json={"name": "Klima, Umwelt & Abfall", "sort_order": 95},
        headers=headers,
    )
    assert update_res.status_code == 200
    updated_cat = update_res.json()
    assert updated_cat["name"] == "Klima, Umwelt & Abfall"
    assert updated_cat["sort_order"] == 95

    # 4. Delete the category
    del_res = client.delete(
        f"/api/organizations/current/categories/{new_cat_id}",
        headers=headers,
    )
    assert del_res.status_code == 204

    # Verify category is gone
    list_res = client.get("/api/organizations/current/categories")
    assert not any(c["id"] == new_cat_id for c in list_res.json())


def test_public_organization_portal_category_filtering(db_session: Session) -> None:
    client = TestClient(app)
    admin = _create_user(db_session, "pub_cat_admin@example.com")

    # Create Organization
    org = Organization(
        name="Stadtverwaltung Stuttgart",
        slug="stadt-stuttgart-cat-test",
        is_verified_government=True,
        verification_status="verified_official",
        supported_languages=["de", "en", "ar"],
    )
    db_session.add(org)
    db_session.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=admin.id,
        role="owner",
    )
    db_session.add(member)

    # Create Categories
    cat_housing = OrganizationCategory(
        organization_id=org.id,
        name="Wohnen & Meldewesen",
        slug="housing-residence",
        icon="Home",
        sort_order=10,
        translations={
            "en": {"name": "Housing & Residence"},
            "ar": {"name": "السكن وتسجيل الإقامة"},
        },
    )
    cat_family = OrganizationCategory(
        organization_id=org.id,
        name="Familie & Kinder",
        slug="family-children",
        icon="Users",
        sort_order=20,
        translations={
            "en": {"name": "Family & Children"},
            "ar": {"name": "الأسرة والأطفال"},
        },
    )
    db_session.add_all([cat_housing, cat_family])
    db_session.flush()

    # Create Form 1 in Housing
    tmpl1 = FormTemplate(
        organization_id=org.id,
        category_id=cat_housing.id,
        key="anmeldung-wohnung",
        name="Anmeldung einer Wohnung",
        category="housing-residence",
        submission_method="print_and_sign",
    )
    db_session.add(tmpl1)
    db_session.flush()

    ver1 = FormVersion(
        form_template_id=tmpl1.id,
        version_number=1,
        status="published",
        source_language="de",
        supported_output_languages=["de", "en"],
    )
    db_session.add(ver1)
    db_session.flush()

    field1 = FormField(
        form_version_id=ver1.id,
        key="applicant.first_name",
        field_type="string",
        requiredness="required",
        position=1,
        configuration={},
    )
    db_session.add(field1)

    # Create Form 2 in Family
    tmpl2 = FormTemplate(
        organization_id=org.id,
        category_id=cat_family.id,
        key="geburtsurkunde",
        name="Geburtsurkunde",
        category="family-children",
        submission_method="print_and_sign",
    )
    db_session.add(tmpl2)
    db_session.flush()

    ver2 = FormVersion(
        form_template_id=tmpl2.id,
        version_number=1,
        status="published",
        source_language="de",
        supported_output_languages=["de", "en"],
    )
    db_session.add(ver2)
    db_session.flush()

    field2 = FormField(
        form_version_id=ver2.id,
        key="child.name",
        field_type="string",
        requiredness="required",
        position=1,
        configuration={},
    )
    db_session.add(field2)
    db_session.commit()

    # Call Public Organization Portal endpoint
    res = client.get(f"/api/public/organizations/{org.slug}")
    assert res.status_code == 200
    data = res.json()

    # Check categories
    assert "categories" in data
    cats = data["categories"]
    assert len(cats) >= 2
    housing = next((c for c in cats if c["slug"] == "housing-residence"), None)
    assert housing is not None
    assert housing["name"] == "Wohnen & Meldewesen"
    assert housing["forms_count"] == 1
    assert housing["translations"]["en"]["name"] == "Housing & Residence"

    family = next((c for c in cats if c["slug"] == "family-children"), None)
    assert family is not None
    assert family["forms_count"] == 1
    assert family["translations"]["en"]["name"] == "Family & Children"

    # Check published forms
    forms = data["published_forms"]
    assert len(forms) == 2
    f1 = next((f for f in forms if f["key"] == "anmeldung-wohnung"), None)
    assert f1 is not None
    assert f1["category_id"] == cat_housing.id
    assert f1["category_slug"] == "housing-residence"
    assert f1["category_name"] == "Wohnen & Meldewesen"

    f2 = next((f for f in forms if f["key"] == "geburtsurkunde"), None)
    assert f2 is not None
    assert f2["category_id"] == cat_family.id
    assert f2["category_slug"] == "family-children"
