"""Tests for Translation Memory caching and Organization template publishing slot limits."""

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.auth.models import User
from app.database.session import SessionLocal
from app.forms.models import FormField, FormTemplate, FormVersion
from app.forms.organization_service import OrganizationFormService
from app.main import app  # noqa: F401
from app.organizations.models import Organization, OrganizationMember
from app.translation.memory import TranslationMemoryService
from app.translation.models import hash_text


@pytest.fixture(autouse=True)
def clean_db() -> None:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE translation_memories CASCADE"))
        db.execute(text("TRUNCATE TABLE form_fields CASCADE"))
        db.execute(text("TRUNCATE TABLE form_versions CASCADE"))
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE organization_members CASCADE"))
        db.execute(text("TRUNCATE TABLE organizations CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_translation_memory_service_crud() -> None:
    """Verifies that TranslationMemoryService accurately saves, updates, and retrieves cached translations."""
    db = SessionLocal()
    try:
        service = TranslationMemoryService(db)

        # 1. Initially empty
        res = service.get_translations("Vorname", "de", ["en", "ar", "fr"])
        assert res == {}

        # 2. Save translation
        entry = service.save_translation(
            text="Vorname",
            source_language="de",
            target_language="en",
            translated_text="First Name",
            provider="gemini",
        )
        assert entry.id is not None
        assert entry.source_text_hash == hash_text("Vorname")

        # 3. Retrieve single cached translation
        res = service.get_translations("Vorname", "de", ["en", "ar"])
        assert res == {"en": "First Name"}

        # 4. Bulk save
        service.bulk_save_translations(
            text="Vorname",
            source_language="de",
            translations={"ar": "الاسم الأول", "fr": "Prénom"},
            provider="gemini",
        )

        # 5. Retrieve all 3
        res_all = service.get_translations("Vorname", "de", ["en", "ar", "fr"])
        assert res_all == {
            "en": "First Name",
            "ar": "الاسم الأول",
            "fr": "Prénom",
        }
    finally:
        db.close()


@pytest.mark.asyncio
async def test_translate_field_label_uses_translation_memory() -> None:
    """Verifies that OrganizationFormService.translate_field_label reads from TranslationMemory."""
    db = SessionLocal()
    try:
        # Pre-seed TranslationMemory
        tm_service = TranslationMemoryService(db)
        tm_service.save_translation(
            text="Wohnungsgeberbestätigung",
            source_language="de",
            target_language="en",
            translated_text="Landlord Move-in Confirmation",
            provider="human_verified",
        )
        db.commit()

        user = User(
            id="u-tm-test",
            email="staff@example.de",
            normalized_email="staff@example.de",
            password_hash="pw",
            role="user",
            status="active",
        )
        org = Organization(
            id="org-tm-test",
            name="Stadt Stuttgart",
            slug="stadt-stuttgart-tm",
            billing_plan="pro",
        )
        member = OrganizationMember(
            id="m-tm-test",
            organization_id=org.id,
            user_id=user.id,
            role="owner",
        )
        db.add_all([user, org, member])
        db.commit()

        form_service = OrganizationFormService(db)
        result = await form_service.translate_field_label(
            user=user,
            text="Wohnungsgeberbestätigung",
            source_language="de",
            target_languages=["en", "de"],
        )

        assert result["en"] == "Landlord Move-in Confirmation"
        assert result["de"] == "Wohnungsgeberbestätigung"
    finally:
        db.close()


def test_publish_slot_limit_enforcement() -> None:
    """Verifies that publishing is blocked with 402 Payment Required once active template slot limit is reached."""
    db = SessionLocal()
    try:
        user = User(
            id="u-slot-test",
            email="limit@example.de",
            normalized_email="limit@example.de",
            password_hash="pw",
            role="user",
            status="active",
        )
        # Free plan has limit = 5
        org = Organization(
            id="org-slot-test",
            name="Kleinstadt Amt",
            slug="kleinstadt-amt",
            billing_plan="free",
        )
        member = OrganizationMember(
            id="m-slot-test",
            organization_id=org.id,
            user_id=user.id,
            role="owner",
        )
        db.add_all([user, org, member])
        db.commit()

        # Seed 5 already-published templates
        for i in range(5):
            t = FormTemplate(
                id=f"tmpl-{i}",
                organization_id=org.id,
                name=f"Template {i}",
                key=f"template-{i}",
            )
            v = FormVersion(
                id=f"ver-{i}",
                form_template_id=t.id,
                version_number=1,
                source_language="de",
                supported_output_languages=["de"],
                status="published",
            )
            f = FormField(
                id=f"fld-{i}",
                form_version_id=v.id,
                key="name",
                field_type="string",
                position=1,
            )
            db.add_all([t, v, f])
        db.commit()

        # Create a 6th draft template
        t6 = FormTemplate(
            id="tmpl-6",
            organization_id=org.id,
            name="Template 6",
            key="template-6",
        )
        v6 = FormVersion(
            id="ver-6",
            form_template_id=t6.id,
            version_number=1,
            source_language="de",
            supported_output_languages=["de"],
            status="draft",
        )
        f6 = FormField(
            id="fld-6",
            form_version_id=v6.id,
            key="name",
            field_type="string",
            position=1,
        )
        db.add_all([t6, v6, f6])
        db.commit()

        form_service = OrganizationFormService(db)

        # Attempt to publish the 6th template -> Should raise 402
        with pytest.raises(HTTPException) as exc_info:
            form_service.publish_form(user, "tmpl-6")

        assert exc_info.value.status_code == 402
        assert "Publishing slot limit reached" in exc_info.value.detail
    finally:
        db.close()
