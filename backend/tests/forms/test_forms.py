import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.session import SessionLocal
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> None:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


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
