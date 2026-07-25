from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.ai.mock_provider import MockAIProvider
from app.ai.schemas import QuestionGenerationResult, QuestionTranslationResult
from app.core.config import settings
from app.database.session import SessionLocal
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.main import app
from app.questions.repositories import QuestionRepository
from app.questions.resolver import QuestionResolver
from app.questions.services import QuestionCatalogService
from app.sessions.services import SessionService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE question_definitions CASCADE"))
        db.execute(text("TRUNCATE TABLE question_resolution_logs CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture
def question_catalog_setup() -> dict[str, Any]:
    db = SessionLocal()
    service = QuestionCatalogService(db)
    form_service = FormService(db)

    # Enable Admin API during setup
    old_admin = settings.QUESTION_ADMIN_API_ENABLED
    settings.QUESTION_ADMIN_API_ENABLED = True

    try:
        # Create form template and version
        template = form_service.create_template(key="test-form", name="Test Form")
        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en", "de", "ar"],
        )

        # Create fields
        f1 = form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="first_name",
                field_type="person_name",
                required=True,
                position=1,
                question_key="personal.first_name",
                translations=[
                    TranslationSchema(language="en", label="First Name Label"),
                    TranslationSchema(language="de", label="Vorname Label"),
                ],
            ),
        )

        f2 = form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="last_name",
                field_type="person_name",
                required=True,
                position=2,
                translations=[
                    TranslationSchema(language="en", label="Last Name Label"),
                ],
            ),
        )

        form_service.publish_version(version.id)

        # Create question definitions in DB
        def1 = service.create_definition(
            question_key="personal.first_name",
            field_type="person_name",
            purpose="collect_value",
            domain="personal",
        )

        # Create approved translation for en
        service.create_manual_translation(
            question_key="personal.first_name",
            language="en",
            text="What is your first name?",
            help_text="Provide first name.",
            placeholder="First Name",
        )

        # Create approved translation for de
        service.create_manual_translation(
            question_key="personal.first_name",
            language="de",
            text="Wie lautet Ihr Vorname?",
            help_text="Geben Sie Ihren Vornamen an.",
            placeholder="Vorname",
        )

        db.commit()

        return {
            "version_id": version.id,
            "field_first_name_id": f1.id,
            "field_last_name_id": f2.id,
            "definition_id": def1.id,
        }
    finally:
        settings.QUESTION_ADMIN_API_ENABLED = old_admin
        db.close()


@pytest.mark.asyncio
async def test_resolver_step_1_db_lookup_approved(
    question_catalog_setup: dict[str, Any],
) -> None:
    db = SessionLocal()
    ai = MockAIProvider()
    resolver = QuestionResolver(db, ai)

    # Should find approved 'en' translation in DB
    res = await resolver.resolve_question(
        question_key="personal.first_name",
        field_type="person_name",
        user_language="en",
        source_language="en",
        output_language="en",
        field_configuration={},
        static_translations={},
    )
    assert res.text == "What is your first name?"
    assert res.help_text == "Provide first name."
    assert res.placeholder == "First Name"
    assert res.source == "manual"
    assert res.review_status == "approved"
    db.close()


@pytest.mark.asyncio
async def test_resolver_step_3_static_form_fallback(
    question_catalog_setup: dict[str, Any],
) -> None:
    db = SessionLocal()
    ai = MockAIProvider()
    resolver = QuestionResolver(db, ai)

    # We look for userLanguage 'de'. Wait, de has approved translation in DB, so let's test a language
    # not in DB: 'ar'.
    # For 'ar', DB has no translations.
    # Static translations dict has labels.
    static_translations = {
        "ar": {
            "label": "الاسم الأول",
            "help_text": "الرجاء الإدخال",
            "placeholder": None,
        }
    }

    # Disable AI Translation and AI Generation to force static/fallback check
    old_trans = settings.QUESTION_AI_TRANSLATION_ENABLED
    old_gen = settings.QUESTION_AI_GENERATION_ENABLED
    settings.QUESTION_AI_TRANSLATION_ENABLED = False
    settings.QUESTION_AI_GENERATION_ENABLED = False

    try:
        res = await resolver.resolve_question(
            question_key="personal.first_name",
            field_type="person_name",
            user_language="ar",
            source_language="en",
            output_language="en",
            field_configuration={},
            static_translations=static_translations,
        )
        assert res.text == "الاسم الأول"
        assert res.help_text == "الرجاء الإدخال"
        assert res.source == "static_translation"
    finally:
        settings.QUESTION_AI_TRANSLATION_ENABLED = old_trans
        settings.QUESTION_AI_GENERATION_ENABLED = old_gen
        db.close()


@pytest.mark.asyncio
async def test_resolver_step_4_ai_translation(
    question_catalog_setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    db = SessionLocal()
    ai = MockAIProvider()

    from app.ai.schemas import QuestionTranslationRequest

    # Mock the AI translate_question method
    async def mock_translate_question(
        request: QuestionTranslationRequest,
    ) -> QuestionTranslationResult:
        return QuestionTranslationResult(
            text="[Mocked Translation] " + request.text,
            helpText="[Mocked Translation] " + request.help_text
            if request.help_text
            else None,
            placeholder=request.placeholder,
        )

    monkeypatch.setattr(ai, "translate_question", mock_translate_question)

    resolver = QuestionResolver(db, ai)

    # We request French 'fr'.
    # DB has approved 'en' (source_language).
    # AI Translation is enabled.
    old_trans = settings.QUESTION_AI_TRANSLATION_ENABLED
    settings.QUESTION_AI_TRANSLATION_ENABLED = True

    try:
        res = await resolver.resolve_question(
            question_key="personal.first_name",
            field_type="person_name",
            user_language="fr",
            source_language="en",
            output_language="en",
            field_configuration={},
            static_translations={},
        )
        assert res.text == "[Mocked Translation] What is your first name?"
        assert res.source == "ai_translated"
        assert res.review_status == "pending_review"

        # Verify it was saved in DB as pending_review
        repo = QuestionRepository(db)
        saved = repo.get_pending_translation("personal.first_name", "fr")
        assert saved is not None
        assert saved.text == "[Mocked Translation] What is your first name?"
        assert saved.review_status == "pending_review"
    finally:
        settings.QUESTION_AI_TRANSLATION_ENABLED = old_trans
        db.close()


@pytest.mark.asyncio
async def test_resolver_step_5_ai_generation(
    question_catalog_setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    db = SessionLocal()
    ai = MockAIProvider()

    from app.ai.schemas import QuestionGenerationRequest

    # Mock AI generate_question method
    async def mock_generate_question(
        request: QuestionGenerationRequest,
    ) -> QuestionGenerationResult:
        return QuestionGenerationResult(
            text="Generated Question?",
            helpText="Generated Help.",
            placeholder="Generated Place.",
        )

    monkeypatch.setattr(ai, "generate_question", mock_generate_question)

    resolver = QuestionResolver(db, ai)

    # We request 'fr' but we disable AI translation to force AI generation.
    old_trans = settings.QUESTION_AI_TRANSLATION_ENABLED
    old_gen = settings.QUESTION_AI_GENERATION_ENABLED
    settings.QUESTION_AI_TRANSLATION_ENABLED = False
    settings.QUESTION_AI_GENERATION_ENABLED = True

    try:
        res = await resolver.resolve_question(
            question_key="personal.first_name",
            field_type="person_name",
            user_language="fr",
            source_language="en",
            output_language="en",
            field_configuration={},
            static_translations={},
        )
        assert res.text == "Generated Question?"
        assert res.source == "ai_generated"
        assert res.review_status == "pending_review"

        # Verify it was saved as pending
        repo = QuestionRepository(db)
        saved = repo.get_pending_translation("personal.first_name", "fr")
        assert saved is not None
        assert saved.text == "Generated Question?"
        assert saved.source == "ai_generated"
    finally:
        settings.QUESTION_AI_TRANSLATION_ENABLED = old_trans
        settings.QUESTION_AI_GENERATION_ENABLED = old_gen
        db.close()


@pytest.mark.asyncio
async def test_resolver_step_6_deterministic_fallback(
    question_catalog_setup: dict[str, Any],
) -> None:
    db = SessionLocal()
    ai = MockAIProvider()
    resolver = QuestionResolver(db, ai)

    # Disable AI and static translation
    old_trans = settings.QUESTION_AI_TRANSLATION_ENABLED
    old_gen = settings.QUESTION_AI_GENERATION_ENABLED
    settings.QUESTION_AI_TRANSLATION_ENABLED = False
    settings.QUESTION_AI_GENERATION_ENABLED = False

    try:
        res = await resolver.resolve_question(
            question_key="personal.first_name",
            field_type="person_name",
            user_language="it",
            source_language="en",
            output_language="en",
            field_configuration={},
            static_translations={},
        )
        # Should fallback to ultimate fallback
        assert res.text == "Please provide a value for “First name”."
        assert res.source == "deterministic_fallback"
    finally:
        settings.QUESTION_AI_TRANSLATION_ENABLED = old_trans
        settings.QUESTION_AI_GENERATION_ENABLED = old_gen
        db.close()


def test_admin_api_disabled_by_default(question_catalog_setup: dict[str, Any]) -> None:
    # Ensure admin routes return 403 Forbidden when disabled
    old_admin = settings.QUESTION_ADMIN_API_ENABLED
    settings.QUESTION_ADMIN_API_ENABLED = False

    try:
        # GET list questions
        resp = client.get("/api/questions")
        assert resp.status_code == 403

        # POST manual translation
        resp = client.post(
            "/api/questions/personal.first_name/translations?language=en",
            json={"text": "Hello"},
        )
        assert resp.status_code == 403
    finally:
        settings.QUESTION_ADMIN_API_ENABLED = old_admin


def test_admin_api_workflow(question_catalog_setup: dict[str, Any]) -> None:
    old_admin = settings.QUESTION_ADMIN_API_ENABLED
    settings.QUESTION_ADMIN_API_ENABLED = True

    try:
        db = SessionLocal()
        # 1. Create a pending translation manually in DB to test review workflow
        repo = QuestionRepository(db)
        definition = repo.get_definition("personal.first_name")
        assert definition is not None
        repo.create_translation(
            definition_id=definition.id,
            language="fr",
            text="Quel est votre prénom ?",
            source="ai_translated",
            review_status="pending_review",
        )
        db.commit()

        # 2. Approve translation via endpoint
        resp = client.post("/api/questions/personal.first_name/translations/fr/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reviewStatus"] == "approved"

        # 3. Reject a new pending translation
        assert definition is not None
        repo.create_translation(
            definition_id=definition.id,
            language="it",
            text="Qual è il tuo nome?",
            source="ai_translated",
            review_status="pending_review",
        )
        db.commit()

        resp = client.post("/api/questions/personal.first_name/translations/it/reject")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reviewStatus"] == "rejected"

        # 4. Filter questions list
        resp = client.get("/api/questions?language=fr&reviewStatus=approved")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["text"] == "Quel est votre prénom ?"
    finally:
        settings.QUESTION_ADMIN_API_ENABLED = old_admin
        db.close()


def test_session_current_field_integration(
    question_catalog_setup: dict[str, Any],
) -> None:
    db = SessionLocal()
    session_service = SessionService(db)
    session, token = session_service.create_session(
        form_version_id=question_catalog_setup["version_id"],
        user_language="de",
        output_language="en",
    )
    db.commit()

    # Call current-field endpoint
    resp = client.get(
        f"/api/form-sessions/{session.public_id}/current-field",
        headers={"X-Session-Token": token},
    )
    assert resp.status_code == 200
    data = resp.json()
    # The resolved question text for first_name in 'de' is 'Wie lautet Ihr Vorname?' from seed/catalog DB
    assert data["label"] == "Wie lautet Ihr Vorname?"
    db.close()
