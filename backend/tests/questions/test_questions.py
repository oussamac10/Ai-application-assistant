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
    client.cookies.clear()
    client.headers.pop("X-CSRF-Token", None)
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE question_definitions CASCADE"))
        db.execute(text("TRUNCATE TABLE question_resolution_logs CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()
        client.cookies.clear()
        client.headers.pop("X-CSRF-Token", None)


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
    old_admin_emails = settings.QUESTION_ADMIN_API_ENABLED, settings.ADMIN_EMAILS
    settings.QUESTION_ADMIN_API_ENABLED = True

    try:
        # Anonymous caller must be rejected with 401 even when QUESTION_ADMIN_API_ENABLED=True
        anon_resp = client.get("/api/questions")
        assert anon_resp.status_code == 401

        # Regular authenticated user must be rejected with 403
        user_client = TestClient(app)
        reg_user = user_client.post(
            "/api/auth/register",
            json={
                "email": "regular-q@example.com",
                "password": "secure-password-123",
                "passwordConfirmation": "secure-password-123",
            },
        )
        assert reg_user.status_code == 201
        assert user_client.get("/api/questions").status_code == 403

        # Authenticate platform_admin on `client`
        settings.ADMIN_EMAILS = "q-admin@example.com"
        reg_admin = client.post(
            "/api/auth/register",
            json={
                "email": "q-admin@example.com",
                "password": "secure-password-123",
                "passwordConfirmation": "secure-password-123",
            },
        )
        assert reg_admin.status_code == 201
        csrf = client.cookies.get("csrf_token")
        assert csrf
        client.headers["X-CSRF-Token"] = csrf

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
        settings.ADMIN_EMAILS = old_admin_emails[1]
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


# ---------------------------------------------------------------------------
# "Select Manually" fix: manually-selected forms authored in only one
# language, with fields that have no reusable-catalog question_key at all
# (e.g. "last_name" in question_catalog_setup — English-only static
# translation, question_key=None) must still be translated into
# user_language, not silently served in the form's own language.
# ---------------------------------------------------------------------------


class _FakeTranslatingProvider(MockAIProvider):
    """Deterministic stand-in that prefixes translated text with the
    target language, so tests can assert exactly which language a call was
    made for without depending on Ollama."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def translate_output(self, request: Any) -> Any:
        from app.ai.schemas import TranslationResult

        self.calls.append(
            (request.text, request.source_language, request.target_language)
        )
        return TranslationResult(
            translatedText=f"[{request.target_language}] {request.text}"
        )


class _FailingTranslatingProvider(MockAIProvider):
    async def translate_output(self, request: Any) -> Any:
        from app.ai.errors import AIProviderUnavailableError

        raise AIProviderUnavailableError("Ollama is unreachable")


def _last_name_static_translations() -> dict[str, dict[str, str | None]]:
    return {"en": {"label": "Last Name Label", "help_text": None, "placeholder": None}}


@pytest.mark.asyncio
async def test_manually_selected_form_no_question_key_translates_to_german() -> None:
    """The exact reported bug: a manually selected English-only form field
    with no question_key must display in German when user_language=de,
    not remain in English."""
    db = SessionLocal()
    provider = _FakeTranslatingProvider()
    resolver = QuestionResolver(db, provider)

    res = await resolver.resolve_question(
        question_key=None,
        field_type="person_name",
        user_language="de",
        source_language="en",
        output_language="en",
        field_configuration={},
        static_translations=_last_name_static_translations(),
    )

    assert res.text == "[de] Last Name Label"
    assert res.source == "ai_translated"
    assert provider.calls == [("Last Name Label", "en", "de")]
    db.close()


@pytest.mark.asyncio
async def test_manually_selected_form_no_question_key_translates_to_arabic() -> None:
    db = SessionLocal()
    provider = _FakeTranslatingProvider()
    resolver = QuestionResolver(db, provider)

    res = await resolver.resolve_question(
        question_key=None,
        field_type="person_name",
        user_language="ar",
        source_language="en",
        output_language="en",
        field_configuration={},
        static_translations=_last_name_static_translations(),
    )

    assert res.text == "[ar] Last Name Label"
    assert provider.calls == [("Last Name Label", "en", "ar")]
    db.close()


@pytest.mark.asyncio
async def test_source_question_text_is_preserved_unchanged() -> None:
    """The original English static translation must remain retrievable
    (and untouched) even after a German translation has been resolved."""
    db = SessionLocal()
    provider = _FakeTranslatingProvider()
    resolver = QuestionResolver(db, provider)

    await resolver.resolve_question(
        question_key=None,
        field_type="person_name",
        user_language="de",
        source_language="en",
        output_language="en",
        field_configuration={},
        static_translations=_last_name_static_translations(),
    )

    res_en = await resolver.resolve_question(
        question_key=None,
        field_type="person_name",
        user_language="en",
        source_language="en",
        output_language="en",
        field_configuration={},
        static_translations=_last_name_static_translations(),
    )
    assert res_en.text == "Last Name Label"
    assert res_en.source == "static_translation"
    db.close()


@pytest.mark.asyncio
async def test_ai_failure_falls_back_to_source_text_for_manual_form() -> None:
    db = SessionLocal()
    resolver = QuestionResolver(db, _FailingTranslatingProvider())

    res = await resolver.resolve_question(
        question_key=None,
        field_type="person_name",
        user_language="de",
        source_language="en",
        output_language="en",
        field_configuration={},
        static_translations=_last_name_static_translations(),
    )

    # Falls through generation (disabled/no key) to the deterministic
    # fallback, which safely returns the English source text rather than
    # crashing or leaving the field blank.
    assert res.text == "Last Name Label"
    assert res.source == "deterministic_fallback"
    db.close()


@pytest.mark.asyncio
async def test_manually_selected_form_with_question_key_but_no_catalog_entry() -> None:
    """A field that DOES carry a question_key, but has no matching
    QuestionDefinition/catalog translation yet (e.g. a form authored
    without running the catalog seed) — must still translate via AI, and
    the result must be cached under that key for next time."""
    db = SessionLocal()
    provider = _FakeTranslatingProvider()
    resolver = QuestionResolver(db, provider)

    res = await resolver.resolve_question(
        question_key="custom.unseeded_field",
        field_type="string",
        user_language="de",
        source_language="en",
        output_language="en",
        field_configuration={},
        static_translations={
            "en": {"label": "Custom Field", "help_text": None, "placeholder": None}
        },
    )

    assert res.text == "[de] Custom Field"
    assert res.source == "ai_translated"
    assert res.review_status == "pending_review"

    # Cached: a second resolution for the same key+language hits step 1
    # (approved) once approved, or step-1-pending if allow_pending — here
    # we assert the pending translation was actually persisted.
    repo = QuestionRepository(db)
    cached = repo.get_pending_translation("custom.unseeded_field", "de")
    assert cached is not None
    assert cached.text == "[de] Custom Field"
    db.close()


@pytest.mark.asyncio
async def test_target_language_cache_separation_for_manual_form_field() -> None:
    """Prevents the exact bug scenario named in the task: an English
    question translated/cached once must never be reused for a different
    target language — German and Arabic requests for the same key must
    each get their own correctly-translated, separately cached entry."""
    db = SessionLocal()
    provider = _FakeTranslatingProvider()
    resolver = QuestionResolver(db, provider)

    res_de = await resolver.resolve_question(
        question_key="custom.shared_field",
        field_type="string",
        user_language="de",
        source_language="en",
        output_language="en",
        field_configuration={},
        static_translations={
            "en": {"label": "Shared Field", "help_text": None, "placeholder": None}
        },
    )
    res_ar = await resolver.resolve_question(
        question_key="custom.shared_field",
        field_type="string",
        user_language="ar",
        source_language="en",
        output_language="en",
        field_configuration={},
        static_translations={
            "en": {"label": "Shared Field", "help_text": None, "placeholder": None}
        },
    )

    assert res_de.text == "[de] Shared Field"
    assert res_ar.text == "[ar] Shared Field"
    assert res_de.text != res_ar.text
    assert provider.calls == [
        ("Shared Field", "en", "de"),
        ("Shared Field", "en", "ar"),
    ]

    repo = QuestionRepository(db)
    assert repo.get_pending_translation("custom.shared_field", "de") is not None
    assert repo.get_pending_translation("custom.shared_field", "ar") is not None
    # The German cache entry is never returned for an Arabic request:
    # get_pending_translation itself filters by language, so re-requesting
    # 'ar' must never surface the 'de' text.
    ar_cached = repo.get_pending_translation("custom.shared_field", "ar")
    assert ar_cached is not None
    assert ar_cached.text == "[ar] Shared Field"
    db.close()


@pytest.mark.asyncio
async def test_approved_translation_preferred_over_ai_for_manual_form() -> None:
    """Once a translation is manually approved for a key+language, it must
    be served directly — no AI call at all."""
    db = SessionLocal()
    provider = _FakeTranslatingProvider()
    catalog = QuestionCatalogService(db)

    old_admin = settings.QUESTION_ADMIN_API_ENABLED
    settings.QUESTION_ADMIN_API_ENABLED = True
    try:
        catalog.create_definition(
            question_key="custom.approved_field",
            field_type="string",
            purpose="collect_value",
            domain="custom",
        )
        catalog.create_manual_translation(
            question_key="custom.approved_field",
            language="de",
            text="Bereits genehmigt",
        )
        db.commit()
    finally:
        settings.QUESTION_ADMIN_API_ENABLED = old_admin

    resolver = QuestionResolver(db, provider)
    res = await resolver.resolve_question(
        question_key="custom.approved_field",
        field_type="string",
        user_language="de",
        source_language="en",
        output_language="en",
        field_configuration={},
        static_translations={
            "en": {"label": "Approved Field", "help_text": None, "placeholder": None}
        },
    )

    assert res.text == "Bereits genehmigt"
    assert res.review_status == "approved"
    assert (
        provider.calls == []
    )  # no AI call — the approved entry short-circuits everything
    db.close()


def test_select_manually_current_field_translates_no_question_key_field() -> None:
    """Full integration through the real /current-field endpoint — the
    exact "Select Manually" symptom: the last_name field (no question_key,
    English-only static translation) must display in German for a
    German-language session, not stay in English."""
    db = SessionLocal()
    try:
        form_service = FormService(db)
        template = form_service.create_template(
            key="manual-de-test", name="Manual DE Test"
        )
        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en"],
        )
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="last_name",
                field_type="string",
                required=True,
                position=1,
                translations=[TranslationSchema(language="en", label="Last Name")],
            ),
        )
        form_service.publish_version(version.id)

        session_service = SessionService(db)
        session, token = session_service.create_session(
            form_version_id=version.id,
            user_language="de",
            output_language="en",
        )
        db.commit()
        session_public_id = session.public_id
    finally:
        db.close()

    import app.ai.factory as ai_factory

    original_provider = ai_factory._provider
    ai_factory._provider = _FakeTranslatingProvider()
    try:
        resp = client.get(
            f"/api/form-sessions/{session_public_id}/current-field",
            headers={"X-Session-Token": token},
        )
    finally:
        ai_factory._provider = original_provider

    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "[de] Last Name"


def test_select_manually_current_field_translates_to_arabic_with_no_question_key() -> (
    None
):
    db = SessionLocal()
    try:
        form_service = FormService(db)
        template = form_service.create_template(
            key="manual-ar-test", name="Manual AR Test"
        )
        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en"],
        )
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="last_name",
                field_type="string",
                required=True,
                position=1,
                translations=[TranslationSchema(language="en", label="Last Name")],
            ),
        )
        form_service.publish_version(version.id)

        session_service = SessionService(db)
        session, token = session_service.create_session(
            form_version_id=version.id,
            user_language="ar",
            output_language="en",
        )
        db.commit()
        session_public_id = session.public_id
    finally:
        db.close()

    import app.ai.factory as ai_factory

    original_provider = ai_factory._provider
    ai_factory._provider = _FakeTranslatingProvider()
    try:
        resp = client.get(
            f"/api/form-sessions/{session_public_id}/current-field",
            headers={"X-Session-Token": token},
        )
    finally:
        ai_factory._provider = original_provider

    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "[ar] Last Name"


def test_select_manually_choice_field_translates_option_labels_stable_values_unchanged() -> (
    None
):
    """A manually selected single_choice field authored with only English
    option labels must display translated (German) labels while the
    stable option `value`s used by answer validation stay untouched —
    { value: "housing", source_label: "Housing", display_label: "Wohnen" }."""
    db = SessionLocal()
    try:
        from app.forms.schemas import OptionSchema, OptionTranslationSchema

        form_service = FormService(db)
        template = form_service.create_template(
            key="manual-choice-de-test", name="Manual Choice DE Test"
        )
        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en"],
        )
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="request_category",
                field_type="single_choice",
                required=True,
                position=1,
                translations=[
                    TranslationSchema(language="en", label="Request category")
                ],
                options=[
                    OptionSchema(
                        value="housing",
                        position=1,
                        translations=[
                            OptionTranslationSchema(language="en", label="Housing")
                        ],
                    ),
                    OptionSchema(
                        value="education",
                        position=2,
                        translations=[
                            OptionTranslationSchema(language="en", label="Education")
                        ],
                    ),
                ],
            ),
        )
        form_service.publish_version(version.id)

        session_service = SessionService(db)
        session, token = session_service.create_session(
            form_version_id=version.id,
            user_language="de",
            output_language="en",
        )
        db.commit()
        session_public_id = session.public_id
    finally:
        db.close()

    import app.ai.factory as ai_factory

    original_provider = ai_factory._provider
    ai_factory._provider = _FakeTranslatingProvider()
    try:
        resp = client.get(
            f"/api/form-sessions/{session_public_id}/current-field",
            headers={"X-Session-Token": token},
        )
    finally:
        ai_factory._provider = original_provider

    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "[de] Request category"
    assert data["options"] == [
        {"value": "housing", "label": "[de] Housing"},
        {"value": "education", "label": "[de] Education"},
    ]
    # Stable values are exactly the original English strings — unchanged.
    assert [o["value"] for o in data["options"]] == ["housing", "education"]


def test_create_translation_idempotency_prevents_unique_violation() -> None:
    """Verifies that calling create_translation multiple times for the same
    (definition, language) pair does not crash with IntegrityError.
    """
    db = SessionLocal()
    try:
        repo = QuestionRepository(db)
        defn = repo.create_definition(
            question_key="test.idempotent_key",
            field_type="string",
            purpose="collect_value",
        )
        # First creation as pending_review
        t1 = repo.create_translation(
            definition_id=defn.id,
            language="fr",
            text="Texte initial",
            review_status="pending_review",
        )
        assert t1.text == "Texte initial"
        assert t1.review_status == "pending_review"

        # Second creation should update cleanly rather than raise UniqueConstraint error
        t2 = repo.create_translation(
            definition_id=defn.id,
            language="fr",
            text="Texte mis à jour",
            review_status="pending_review",
        )
        assert t2.id == t1.id
        assert t2.text == "Texte mis à jour"

        # Mark as approved
        repo.approve_translation(t2.id)

        # Attempting to overwrite approved with pending should NOT downgrade it
        t3 = repo.create_translation(
            definition_id=defn.id,
            language="fr",
            text="Texte non approuvé",
            review_status="pending_review",
        )
        assert t3.id == t1.id
        assert t3.review_status == "approved"
        assert t3.text == "Texte mis à jour"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_repeated_resolve_question_does_not_conflict() -> None:
    """Verifies that repeatedly resolving a question that requires AI translation
    does not hit unique constraint collisions.
    """
    db = SessionLocal()
    try:
        provider = _FakeTranslatingProvider()
        resolver = QuestionResolver(db, provider)

        # First resolution generates pending AI translation
        res1 = await resolver.resolve_question(
            question_key="test.repeated_resolve",
            field_type="string",
            user_language="fr",
            source_language="de",
            output_language="de",
            field_configuration={},
            static_translations={
                "de": {
                    "label": "Wiederholtes Feld",
                    "help_text": None,
                    "placeholder": None,
                }
            },
            allow_pending=True,
        )
        assert res1.text == "[fr] Wiederholtes Feld"

        # Second resolution should seamlessly return the pending translation
        res2 = await resolver.resolve_question(
            question_key="test.repeated_resolve",
            field_type="string",
            user_language="fr",
            source_language="de",
            output_language="de",
            field_configuration={},
            static_translations={
                "de": {
                    "label": "Wiederholtes Feld",
                    "help_text": None,
                    "placeholder": None,
                }
            },
            allow_pending=True,
        )
        assert res2.text == "[fr] Wiederholtes Feld"
    finally:
        db.close()
