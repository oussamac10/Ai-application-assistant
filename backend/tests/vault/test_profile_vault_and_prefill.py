from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.answers.models import FormAnswer
from app.database.session import SessionLocal
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.main import app
from app.sessions.models import FormSession
from app.vault.models import UserProfileEntry

PASSWORD = "correct-horse-battery"

client = TestClient(app)
other_client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    client.cookies.clear()
    other_client.cookies.clear()
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()
        client.cookies.clear()
        other_client.cookies.clear()


def _register(c: TestClient, email: str = "vault-owner@example.com") -> str:
    res = c.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "passwordConfirmation": PASSWORD,
        },
    )
    assert res.status_code == 201
    return str(res.json()["id"])


def _csrf(c: TestClient) -> str:
    token = c.cookies.get("csrf_token")
    assert token
    return token


def _seed_multifield_form(
    supported_langs: list[str] | None = None,
) -> tuple[str, dict[str, str]]:
    langs = supported_langs or ["en", "de"]
    db = SessionLocal()
    try:
        service = FormService(db)
        template = service.create_template(
            key=f"vault-form-{uuid.uuid4().hex[:8]}", name="Vault Test Form"
        )
        version = service.create_draft_version(
            form_template_id=template.id,
            source_language="de",
            supported_output_languages=langs,
        )
        f_first = service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="vorname",
                field_type="person_name",
                required=True,
                position=1,
                question_key="personal.first_name",
                translations=[
                    TranslationSchema(language="de", label="Vorname"),
                    TranslationSchema(language="en", label="First name"),
                ],
            ),
        )
        f_email = service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="email",
                field_type="email",
                required=True,
                position=2,
                question_key="contact.email",
                translations=[
                    TranslationSchema(language="de", label="E-Mail"),
                    TranslationSchema(language="en", label="Email"),
                ],
            ),
        )
        f_dob = service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="geburtsdatum",
                field_type="date",
                required=True,
                position=3,
                question_key="person.date_of_birth",
                translations=[
                    TranslationSchema(language="de", label="Geburtsdatum"),
                    TranslationSchema(language="en", label="Date of birth"),
                ],
            ),
        )
        f_city = service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="wohnort",
                field_type="string",
                required=False,
                position=4,
                question_key="address.city",
                translations=[
                    TranslationSchema(language="de", label="Wohnort"),
                    TranslationSchema(language="en", label="City"),
                ],
            ),
        )
        f_sig = service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="unterschrift",
                field_type="signature",
                required=False,
                position=5,
                question_key="declaration.signature",
                translations=[
                    TranslationSchema(language="de", label="Unterschrift"),
                    TranslationSchema(language="en", label="Signature"),
                ],
            ),
        )
        service.publish_version(version.id)
        return version.id, {
            "vorname": f_first.id,
            "email": f_email.id,
            "geburtsdatum": f_dob.id,
            "wohnort": f_city.id,
            "unterschrift": f_sig.id,
        }
    finally:
        db.close()


def test_vault_crud_encrypts_at_rest_and_enforces_csrf_and_ownership() -> None:
    user_id = _register(client)
    csrf = _csrf(client)

    # Missing CSRF is rejected
    no_csrf = client.put(
        "/api/profile-vault/personal.first_name",
        json={"value": "Oussama", "fieldType": "person_name", "valueLanguage": "en"},
    )
    assert no_csrf.status_code == 401

    put_res = client.put(
        "/api/profile-vault/personal.first_name",
        json={"value": "Oussama", "fieldType": "person_name", "valueLanguage": "en"},
        headers={"X-CSRF-Token": csrf},
    )
    assert put_res.status_code == 200
    body = put_res.json()
    assert body["questionKey"] == "personal.first_name"
    assert body["value"] == "Oussama"
    assert body["fieldType"] == "person_name"

    # Verify raw DB column is Fernet-encrypted and never stores plaintext PII
    db = SessionLocal()
    try:
        row = db.scalars(
            select(UserProfileEntry).where(UserProfileEntry.user_id == user_id)
        ).first()
        assert row is not None
        assert "Oussama" not in row.encrypted_payload
        assert row.encrypted_payload.startswith("gAAAAA")
    finally:
        db.close()

    # Cross-user isolation
    _register(other_client, email="other-user@example.com")
    assert other_client.get("/api/profile-vault").json() == []

    # Owner sees decrypted entry
    listed = client.get("/api/profile-vault")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["value"] == "Oussama"

    # Delete single key + delete all
    client.put(
        "/api/profile-vault/address.city",
        json={"value": "Berlin", "fieldType": "string", "valueLanguage": "de"},
        headers={"X-CSRF-Token": csrf},
    )
    assert len(client.get("/api/profile-vault").json()) == 2

    del_one = client.delete(
        "/api/profile-vault/personal.first_name",
        headers={"X-CSRF-Token": csrf},
    )
    assert del_one.status_code == 204
    remaining = client.get("/api/profile-vault").json()
    assert [r["questionKey"] for r in remaining] == ["address.city"]

    del_all = client.delete("/api/profile-vault", headers={"X-CSRF-Token": csrf})
    assert del_all.status_code == 204
    assert client.get("/api/profile-vault").json() == []


def test_vault_deterministic_validation_and_rejects_signatures() -> None:
    _register(client)
    csrf = _csrf(client)

    bad_email = client.put(
        "/api/profile-vault/contact.email",
        json={"value": "not-an-email", "fieldType": "email", "valueLanguage": "en"},
        headers={"X-CSRF-Token": csrf},
    )
    assert bad_email.status_code == 422
    assert bad_email.json()["error_code"] == "invalid_vault_value"

    bad_date = client.put(
        "/api/profile-vault/person.date_of_birth",
        json={"value": "31-02-2020", "fieldType": "date", "valueLanguage": "en"},
        headers={"X-CSRF-Token": csrf},
    )
    assert bad_date.status_code == 422
    assert bad_date.json()["error_code"] == "invalid_vault_value"

    sig = client.put(
        "/api/profile-vault/declaration.signature",
        json={"value": "drawn", "fieldType": "signature", "valueLanguage": "en"},
        headers={"X-CSRF-Token": csrf},
    )
    assert sig.status_code == 422
    assert sig.json()["error_code"] == "unsupported_vault_field_type"


def test_save_session_to_vault_and_one_click_prefill_on_second_form() -> None:
    user_id = _register(client)
    csrf = _csrf(client)
    version1_id, fields1 = _seed_multifield_form()
    version2_id, fields2 = _seed_multifield_form()

    now = datetime.now(UTC)
    db = SessionLocal()
    try:
        s1 = FormSession(
            user_id=user_id,
            form_version_id=version1_id,
            user_language="en",
            source_language="de",
            output_language="de",
            status="completed",
            total_required_fields=3,
            expires_at=now + timedelta(hours=24),
        )
        db.add(s1)
        db.flush()
        s1_public_id = s1.public_id

        db.add_all(
            [
                FormAnswer(
                    session_id=s1.id,
                    field_id=fields1["vorname"],
                    original_answer="Nadia",
                    original_language="en",
                    normalized_value={"fullName": "Nadia"},
                    output_value="Nadia",
                    status="confirmed",
                    validation_status="valid",
                    confirmed_by_user=True,
                ),
                FormAnswer(
                    session_id=s1.id,
                    field_id=fields1["email"],
                    original_answer="nadia@example.com",
                    original_language="en",
                    normalized_value="nadia@example.com",
                    output_value="nadia@example.com",
                    status="confirmed",
                    validation_status="valid",
                    confirmed_by_user=True,
                ),
                FormAnswer(
                    session_id=s1.id,
                    field_id=fields1["geburtsdatum"],
                    original_answer="1994-08-21",
                    original_language="en",
                    normalized_value="1994-08-21",
                    output_value="1994-08-21",
                    status="confirmed",
                    validation_status="valid",
                    confirmed_by_user=True,
                ),
                FormAnswer(
                    session_id=s1.id,
                    field_id=fields1["wohnort"],
                    original_answer="Hamburg",
                    original_language="en",
                    normalized_value="Hamburg",
                    output_value="Hamburg",
                    status="confirmed",
                    validation_status="valid",
                    confirmed_by_user=True,
                ),
                FormAnswer(
                    session_id=s1.id,
                    field_id=fields1["unterschrift"],
                    original_answer=None,
                    original_language="en",
                    normalized_value={
                        "strokes": [[[0.1, 0.2], [0.4, 0.5]]],
                        "width": 200,
                        "height": 80,
                    },
                    output_value=None,
                    status="confirmed",
                    validation_status="valid",
                    confirmed_by_user=True,
                ),
            ]
        )

        # Second session already has `wohnort` confirmed as "Berlin" — prefill must NOT overwrite it!
        s2 = FormSession(
            user_id=user_id,
            form_version_id=version2_id,
            user_language="en",
            source_language="de",
            output_language="de",
            status="in_progress",
            total_required_fields=3,
            expires_at=now + timedelta(hours=24),
        )
        db.add(s2)
        db.flush()
        s2_public_id = s2.public_id
        s2_internal_id = s2.id

        db.add(
            FormAnswer(
                session_id=s2.id,
                field_id=fields2["wohnort"],
                original_answer="Berlin",
                original_language="en",
                normalized_value="Berlin",
                output_value="Berlin",
                status="confirmed",
                validation_status="valid",
                confirmed_by_user=True,
            )
        )
        db.commit()
    finally:
        db.close()

    # 1. Opt-in save confirmed reusable answers from Form #1 to Vault (skipping signature!)
    saved = client.post(
        f"/api/form-sessions/{s1_public_id}/save-to-vault",
        headers={"X-CSRF-Token": csrf},
    )
    assert saved.status_code == 200
    assert saved.json()["savedCount"] == 4

    # GDPR export includes the decrypted vault entries
    gdpr = client.get("/api/auth/me/export")
    assert gdpr.status_code == 200
    assert len(gdpr.json()["profileVault"]) == 4

    # 2. 1-click pre-fill onto Form #2
    prefilled = client.post(
        f"/api/form-sessions/{s2_public_id}/prefill-from-vault",
        headers={"X-CSRF-Token": csrf},
    )
    assert prefilled.status_code == 200
    pdata = prefilled.json()
    assert pdata["prefilledCount"] == 3
    assert set(pdata["prefilledFieldKeys"]) == {"vorname", "email", "geburtsdatum"}

    db = SessionLocal()
    try:
        s2_answers = {
            a.field_id: a
            for a in db.scalars(
                select(FormAnswer).where(FormAnswer.session_id == s2_internal_id)
            ).all()
        }
        # Pre-filled answers MUST be awaiting_confirmation (confirmed_by_user=False)
        for key in ("vorname", "email", "geburtsdatum"):
            ans = s2_answers[fields2[key]]
            assert ans.status == "awaiting_confirmation"
            assert ans.confirmed_by_user is False
            assert ans.validation_status == "valid"

        # Already-confirmed answer (`wohnort == "Berlin"`) must NOT be mutated!
        city_ans = s2_answers[fields2["wohnort"]]
        assert city_ans.original_answer == "Berlin"
        assert city_ans.status == "confirmed"
        assert city_ans.confirmed_by_user is True
    finally:
        db.close()


def test_prefill_preserves_original_script_without_silent_transliteration() -> None:
    user_id = _register(client, email="arabic-name@example.com")
    csrf = _csrf(client)
    version_id, fields = _seed_multifield_form(supported_langs=["de", "en", "ar"])

    put_res = client.put(
        "/api/profile-vault/personal.first_name",
        json={"value": "أمينة", "fieldType": "person_name", "valueLanguage": "ar"},
        headers={"X-CSRF-Token": csrf},
    )
    assert put_res.status_code == 200

    now = datetime.now(UTC)
    db = SessionLocal()
    try:
        s = FormSession(
            user_id=user_id,
            form_version_id=version_id,
            user_language="ar",
            source_language="de",
            output_language="de",
            status="in_progress",
            total_required_fields=3,
            expires_at=now + timedelta(hours=24),
        )
        db.add(s)
        db.commit()
        s_public_id = s.public_id
        s_internal_id = s.id
    finally:
        db.close()

    prefilled = client.post(
        f"/api/form-sessions/{s_public_id}/prefill-from-vault",
        headers={"X-CSRF-Token": csrf},
    )
    assert prefilled.status_code == 200
    assert prefilled.json()["prefilledCount"] == 1

    db = SessionLocal()
    try:
        ans = db.scalars(
            select(FormAnswer).where(
                FormAnswer.session_id == s_internal_id,
                FormAnswer.field_id == fields["vorname"],
            )
        ).first()
        assert ans is not None
        assert ans.original_answer == "أمينة"
        assert ans.output_value == "أمينة"
        assert ans.status == "awaiting_confirmation"
        assert ans.confirmed_by_user is False
    finally:
        db.close()
