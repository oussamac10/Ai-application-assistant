import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings
from app.database.session import SessionLocal
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.main import app

client = TestClient(app)
ADMIN_PASSWORD = "admin-secure-password-123"


def _authenticate_admin(c: TestClient, email: str = "forms-admin@example.com") -> None:
    old_admins = settings.ADMIN_EMAILS
    settings.ADMIN_EMAILS = email
    try:
        res = c.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": ADMIN_PASSWORD,
                "passwordConfirmation": ADMIN_PASSWORD,
            },
        )
        assert res.status_code == 201
        csrf = c.cookies.get("csrf_token")
        assert csrf
        c.headers["X-CSRF-Token"] = csrf
    finally:
        settings.ADMIN_EMAILS = old_admins


@pytest.fixture(autouse=True)
def clean_db() -> None:
    client.cookies.clear()
    client.headers.pop("X-CSRF-Token", None)
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    _authenticate_admin(client)


def test_create_template() -> None:
    # Creating a form template
    response = client.post(
        "/api/forms",
        json={
            "key": "test-form",
            "name": "Test Form",
            "description": "A test form",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "test-form"
    assert data["name"] == "Test Form"
    assert "id" in data


def test_reject_duplicate_template_key() -> None:
    # Rejecting duplicate template keys
    client.post(
        "/api/forms",
        json={"key": "dup-key", "name": "First"},
    )
    response = client.post(
        "/api/forms",
        json={"key": "dup-key", "name": "Second"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_list_templates() -> None:
    client.post(
        "/api/forms",
        json={"key": "form1", "name": "Form 1"},
    )
    client.post(
        "/api/forms",
        json={"key": "form2", "name": "Form 2"},
    )
    response = client.get("/api/forms")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_template() -> None:
    res = client.post(
        "/api/forms",
        json={"key": "form1", "name": "Form 1"},
    )
    form_id = res.json()["id"]

    response = client.get(f"/api/forms/{form_id}")
    assert response.status_code == 200
    assert response.json()["key"] == "form1"

    # API 404 response
    response_404 = client.get("/api/forms/non-existent-id")
    assert response_404.status_code == 404


def test_create_first_draft_version() -> None:
    res = client.post(
        "/api/forms",
        json={"key": "test-form", "name": "Test Form"},
    )
    form_id = res.json()["id"]

    response = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en", "de"]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["versionNumber"] == 1
    assert data["status"] == "draft"


def test_increment_version_numbers() -> None:
    res = client.post(
        "/api/forms",
        json={"key": "test-form", "name": "Test Form"},
    )
    form_id = res.json()["id"]

    res_v1 = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en"]},
    )
    assert res_v1.json()["versionNumber"] == 1

    res_v2 = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en"]},
    )
    assert res_v2.json()["versionNumber"] == 2


def test_add_fields_and_deterministic_ordering() -> None:
    res = client.post(
        "/api/forms",
        json={"key": "test-form", "name": "Test Form"},
    )
    form_id = res.json()["id"]
    res_v = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en"]},
    )
    version_id = res_v.json()["id"]

    # Add field with position 2
    res_f2 = client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "last_name",
            "fieldType": "person_name",
            "required": True,
            "position": 2,
            "configuration": {"maxLength": 50},
            "translations": [{"language": "en", "label": "Last Name"}],
        },
    )
    assert res_f2.status_code == 201

    # Add field with position 1
    res_f1 = client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "first_name",
            "fieldType": "person_name",
            "required": True,
            "position": 1,
            "configuration": {"maxLength": 50},
            "translations": [{"language": "en", "label": "First Name"}],
        },
    )
    assert res_f1.status_code == 201

    # Get version and assert fields are returned in deterministic order
    # (sorted by position)
    res_get = client.get(f"/api/form-versions/{version_id}")
    fields = res_get.json()["fields"]
    assert len(fields) == 2
    assert fields[0]["key"] == "first_name"
    assert fields[1]["key"] == "last_name"


def test_reject_duplicate_field_keys() -> None:
    res = client.post(
        "/api/forms",
        json={"key": "test-form", "name": "Test Form"},
    )
    form_id = res.json()["id"]
    res_v = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en"]},
    )
    version_id = res_v.json()["id"]

    client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "email",
            "fieldType": "email",
            "required": True,
            "position": 1,
            "translations": [{"language": "en", "label": "Email"}],
        },
    )
    # Adding duplicate key should fail with 409
    response = client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "email",
            "fieldType": "email",
            "required": True,
            "position": 2,
            "translations": [{"language": "en", "label": "Second Email"}],
        },
    )
    assert response.status_code == 409


def test_translation_uniqueness() -> None:
    res = client.post(
        "/api/forms",
        json={"key": "test-form", "name": "Test Form"},
    )
    form_id = res.json()["id"]
    res_v = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en"]},
    )
    version_id = res_v.json()["id"]

    # Provide duplicate translations for the same language 'en'
    response = client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "first_name",
            "fieldType": "person_name",
            "required": True,
            "position": 1,
            "translations": [
                {"language": "en", "label": "First Name"},
                {"language": "en", "label": "Duplicate First Name"},
            ],
        },
    )
    assert response.status_code == 409 or response.status_code == 422
    # Our DB unique constraint uq_field_translation_language will reject
    # this inside transaction. Since we run inside a transaction, the DB
    # raises IntegrityError (which is intercepted and returned as 409).


def test_choice_option_uniqueness_and_non_choice_rejection() -> None:
    res = client.post(
        "/api/forms",
        json={"key": "test-form", "name": "Test Form"},
    )
    form_id = res.json()["id"]
    res_v = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en"]},
    )
    version_id = res_v.json()["id"]

    # 1. Rejecting options on non-choice fields
    response_non_choice = client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "first_name",
            "fieldType": "person_name",
            "required": True,
            "position": 1,
            "options": [{"value": "opt1", "position": 1}],
        },
    )
    assert response_non_choice.status_code == 422

    # 2. Rejecting choice field with duplicate options
    response_dup_options = client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "color",
            "fieldType": "single_choice",
            "required": True,
            "position": 2,
            "options": [
                {"value": "red", "position": 1},
                {"value": "red", "position": 2},
            ],
        },
    )
    assert response_dup_options.status_code == 422


def test_field_configuration_validation() -> None:
    res = client.post(
        "/api/forms",
        json={"key": "test-form", "name": "Test Form"},
    )
    form_id = res.json()["id"]
    res_v = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en"]},
    )
    version_id = res_v.json()["id"]

    # Invalid string configuration (maxLength < minLength)
    response = client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "bio",
            "fieldType": "string",
            "required": False,
            "position": 1,
            "configuration": {"minLength": 10, "maxLength": 5},
        },
    )
    assert response.status_code == 422
    assert "greater than or equal to minLength" in response.json()["detail"]

    # Invalid key for type
    response2 = client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "bio",
            "fieldType": "string",
            "required": False,
            "position": 1,
            "configuration": {"minimum": 5},
        },
    )
    assert response2.status_code == 422


def test_version_publication_flow() -> None:
    res = client.post(
        "/api/forms",
        json={"key": "test-form", "name": "Test Form"},
    )
    form_id = res.json()["id"]
    res_v = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en", "de"]},
    )
    version_id = res_v.json()["id"]

    # 1. Publication fails with no fields
    response_no_fields = client.post(f"/api/form-versions/{version_id}/publish")
    assert response_no_fields.status_code == 422
    assert "no fields" in response_no_fields.json()["detail"]

    # Add choice field but missing options
    client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "color",
            "fieldType": "single_choice",
            "required": True,
            "position": 1,
            "translations": [{"language": "en", "label": "Color"}],
        },
    )
    # 2. Publication fails for invalid choice fields (no options)
    response_choice_invalid = client.post(f"/api/form-versions/{version_id}/publish")
    assert response_choice_invalid.status_code == 422

    # Update field to delete it (or create new version to start clean)
    res_v2 = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en", "de"]},
    )
    v2_id = res_v2.json()["id"]

    # Add correct field but missing source-language label
    client.post(
        f"/api/form-versions/{v2_id}/fields",
        json={
            "key": "first_name",
            "fieldType": "person_name",
            "required": True,
            "position": 1,
            "translations": [{"language": "de", "label": "Vorname"}],
        },
    )
    # 3. Publication fails with missing source-language (en) label
    response_missing_src = client.post(f"/api/form-versions/{v2_id}/publish")
    assert response_missing_src.status_code == 422

    # Clear/create v3
    res_v3 = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en"]},
    )
    v3_id = res_v3.json()["id"]

    # Add valid field with source translation
    client.post(
        f"/api/form-versions/{v3_id}/fields",
        json={
            "key": "first_name",
            "fieldType": "person_name",
            "required": True,
            "position": 1,
            "translations": [{"language": "en", "label": "First Name"}],
        },
    )

    # 4. Successful publication
    res_pub = client.post(f"/api/form-versions/{v3_id}/publish")
    assert res_pub.status_code == 200
    assert res_pub.json()["status"] == "published"
    assert res_pub.json()["publishedAt"] is not None

    # 5. Published-version immutability
    res_add_f = client.post(
        f"/api/form-versions/{v3_id}/fields",
        json={
            "key": "last_name",
            "fieldType": "person_name",
            "required": True,
            "position": 2,
            "translations": [{"language": "en", "label": "Last Name"}],
        },
    )
    assert res_add_f.status_code == 409


def test_cloning_and_independence() -> None:
    res = client.post(
        "/api/forms",
        json={"key": "test-form", "name": "Test Form"},
    )
    form_id = res.json()["id"]
    res_v = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en", "de"]},
    )
    version_id = res_v.json()["id"]

    # Add choice field with option and option translation
    client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "gender",
            "fieldType": "single_choice",
            "required": True,
            "position": 1,
            "translations": [{"language": "en", "label": "Gender"}],
            "options": [
                {
                    "value": "male",
                    "position": 1,
                    "translations": [{"language": "en", "label": "Male"}],
                }
            ],
        },
    )

    # Clone the version
    res_clone = client.post(f"/api/form-versions/{version_id}/clone")
    assert res_clone.status_code == 201
    clone_data = res_clone.json()
    assert clone_data["versionNumber"] == 2
    assert clone_data["status"] == "draft"

    # Assert fields are independent database records
    assert len(clone_data["fields"]) == 1
    clone_field = clone_data["fields"][0]
    assert clone_field["key"] == "gender"

    # Fetch original field
    orig_ver = client.get(f"/api/form-versions/{version_id}").json()
    orig_field = orig_ver["fields"][0]

    assert clone_field["id"] != orig_field["id"]
    clone_lang = clone_field["translations"][0]["language"]
    orig_lang = orig_field["translations"][0]["language"]
    assert clone_lang == orig_lang
    assert clone_field["options"][0]["id"] != orig_field["options"][0]["id"]


def test_list_published_forms() -> None:
    # 1. Create and publish a version
    res = client.post(
        "/api/forms",
        json={
            "key": "published-list-form",
            "name": "Published List Form",
            "description": "Form for test",
        },
    )
    form_id = res.json()["id"]
    res_v = client.post(
        f"/api/forms/{form_id}/versions",
        json={"sourceLanguage": "en", "supportedOutputLanguages": ["en", "de"]},
    )
    version_id = res_v.json()["id"]

    # At this point, it is a draft, so it shouldn't show in the published list
    res_list_1 = client.get("/api/published-forms")
    assert res_list_1.status_code == 200
    assert not any(f["id"] == version_id for f in res_list_1.json())

    # Add a field to the draft
    res_field = client.post(
        f"/api/form-versions/{version_id}/fields",
        json={
            "key": "first_name",
            "fieldType": "person_name",
            "required": True,
            "position": 1,
            "translations": [
                {"language": "en", "label": "First Name"},
            ],
        },
    )
    assert res_field.status_code == 201

    # Publish the version
    res_pub = client.post(f"/api/form-versions/{version_id}/publish")
    assert res_pub.status_code == 200

    # Now it should show up in the published forms list
    res_list_2 = client.get("/api/published-forms")
    assert res_list_2.status_code == 200
    published_forms = res_list_2.json()
    assert any(f["id"] == version_id for f in published_forms)

    # Verify response schema fields
    target_form = next(f for f in published_forms if f["id"] == version_id)
    assert target_form["templateKey"] == "published-list-form"
    assert target_form["name"] == "Published List Form"
    assert target_form["description"] == "Form for test"
    assert target_form["versionNumber"] == 1
    assert target_form["sourceLanguage"] == "en"
    assert target_form["supportedOutputLanguages"] == ["en", "de"]


def test_admin_form_endpoints_reject_anonymous_and_regular_users() -> None:
    anon_client = TestClient(app)
    assert anon_client.get("/api/forms").status_code == 401
    assert (
        anon_client.post("/api/forms", json={"key": "k1", "name": "N1"}).status_code
        == 401
    )

    user_client = TestClient(app)
    reg = user_client.post(
        "/api/auth/register",
        json={
            "email": "regular-user@example.com",
            "password": ADMIN_PASSWORD,
            "passwordConfirmation": ADMIN_PASSWORD,
        },
    )
    assert reg.status_code == 201
    csrf = user_client.cookies.get("csrf_token")
    assert csrf

    assert user_client.get("/api/forms").status_code == 403
    assert (
        user_client.post(
            "/api/forms",
            json={"key": "k2", "name": "N2"},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 403
    )

    # Admin mutation without CSRF header must fail with 401
    no_csrf_headers = {
        k: v for k, v in client.headers.items() if k.lower() != "x-csrf-token"
    }
    res_no_csrf = client.post(
        "/api/forms",
        json={"key": "k3", "name": "N3"},
        headers={"X-CSRF-Token": ""},
    )
    assert res_no_csrf.status_code == 401
    _ = no_csrf_headers


def test_published_forms_excludes_dynamic_detection_and_prod_demo() -> None:
    db = SessionLocal()
    try:
        svc = FormService(db)
        # 1. Dynamic detection form (from uploaded user PDF) must NEVER appear publicly
        dyn_tpl = svc.create_template(
            key="uploaded-user-pdf", name="Private Uploaded PDF"
        )
        dyn_ver = svc.create_draft_version(
            form_template_id=dyn_tpl.id,
            source_language="de",
            supported_output_languages=["de"],
            origin="dynamic_detection",
        )
        svc.add_field_to_draft(
            dyn_ver.id,
            FieldCreate(
                key="secret_field",
                field_type="string",
                required=True,
                position=1,
                translations=[TranslationSchema(language="de", label="Geheim")],
            ),
        )
        svc.publish_version(dyn_ver.id)

        # 2. Signature demo form
        demo_tpl = svc.create_template(key="signature-demo", name="Signature Demo")
        demo_ver = svc.create_draft_version(
            form_template_id=demo_tpl.id,
            source_language="en",
            supported_output_languages=["en"],
            origin="predefined_template",
        )
        svc.add_field_to_draft(
            demo_ver.id,
            FieldCreate(
                key="sig",
                field_type="signature",
                required=False,
                position=1,
                translations=[TranslationSchema(language="en", label="Signature")],
            ),
        )
        svc.publish_version(demo_ver.id)
        dyn_ver_id = dyn_ver.id
        demo_ver_id = demo_ver.id
    finally:
        db.close()

    anon_client = TestClient(app)
    pub_list = anon_client.get("/api/published-forms")
    assert pub_list.status_code == 200
    ids = {f["id"] for f in pub_list.json()}
    assert dyn_ver_id not in ids
    assert demo_ver_id in ids

    # Public session endpoint must also refuse dynamic_detection versions directly
    dyn_session_attempt = anon_client.post(
        f"/api/form-versions/{dyn_ver_id}/sessions",
        json={"userLanguage": "de", "outputLanguage": "de"},
    )
    assert dyn_session_attempt.status_code == 404

    # In production mode, signature-demo is hidden from /api/published-forms
    old_env = settings.ENVIRONMENT
    settings.ENVIRONMENT = "production"
    try:
        prod_list = anon_client.get("/api/published-forms")
        assert prod_list.status_code == 200
        prod_ids = {f["id"] for f in prod_list.json()}
        assert demo_ver_id not in prod_ids
    finally:
        settings.ENVIRONMENT = old_env
