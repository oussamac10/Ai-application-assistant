import logging
from typing import Any

from sqlalchemy.orm import Session

from app.ai.errors import AIProviderError
from app.ai.mock_provider import AIProvider
from app.ai.schemas import QuestionGenerationRequest, QuestionTranslationRequest
from app.core.config import settings
from app.questions.repositories import QuestionRepository
from app.questions.schemas import ResolvedQuestion

logger = logging.getLogger(__name__)


class QuestionResolver:
    def __init__(self, db: Session, ai_provider: AIProvider):
        self.db = db
        self.ai_provider = ai_provider
        self.repo = QuestionRepository(db)

    async def resolve_question(
        self,
        *,
        question_key: str | None,
        field_type: str,
        user_language: str,
        source_language: str,
        output_language: str,
        field_configuration: dict[str, Any],
        static_translations: dict[str, dict[str, str | None]],
        allow_pending: bool = False,
    ) -> ResolvedQuestion:
        """Resolve a user-facing question text using the hybrid hierarchy.

        Resolution sequence:
        1. Approved reusable question in userLanguage (DB)
        2. Approved reusable question in sourceLanguage (DB) (used to translate with AI)
        3. Approved static translation from the immutable form version
        4. AI translation of an approved source-language question
        5. AI generation from minimal field metadata
        6. Deterministic non-AI fallback
        """
        # If no question key is defined, skip DB/AI steps entirely
        if not question_key:
            return self._resolve_static_or_deterministic_fallback(
                question_key=None,
                field_type=field_type,
                user_language=user_language,
                static_translations=static_translations,
            )

        # Step 1: Check DB for approved user_language translation
        approved_user_lang = self.repo.get_approved_translation(question_key, user_language)
        if approved_user_lang:
            self.repo.log_resolution(
                question_key=question_key,
                requested_language=user_language,
                resolved_language=user_language,
                source=approved_user_lang.source,
                used_ai=False,
                result="resolved",
            )
            return ResolvedQuestion(
                text=approved_user_lang.text,
                helpText=approved_user_lang.help_text,
                placeholder=approved_user_lang.placeholder,
                source=approved_user_lang.source,
                reviewStatus=approved_user_lang.review_status,
                provider=approved_user_lang.provider,
                model=approved_user_lang.model,
                promptVersion=approved_user_lang.prompt_version,
            )

        # Optional: check DB for pending user_language translation if allowed
        if settings.QUESTION_ALLOW_PENDING_REUSE or allow_pending:
            pending_user_lang = self.repo.get_pending_translation(question_key, user_language)
            if pending_user_lang:
                self.repo.log_resolution(
                    question_key=question_key,
                    requested_language=user_language,
                    resolved_language=user_language,
                    source=pending_user_lang.source,
                    used_ai=False,
                    result="resolved",
                )
                return ResolvedQuestion(
                    text=pending_user_lang.text,
                    helpText=pending_user_lang.help_text,
                    placeholder=pending_user_lang.placeholder,
                    source=pending_user_lang.source,
                    reviewStatus=pending_user_lang.review_status,
                    provider=pending_user_lang.provider,
                    model=pending_user_lang.model,
                    promptVersion=pending_user_lang.prompt_version,
                )

        # Step 2 & 3: Check approved sourceLanguage reusable translation in DB
        # and static form translation.
        # Note: Step 3 (static translation from form version) is checked before AI.
        # Thus, we fetch the approved sourceLanguage DB translation first to see
        # if AI translation would be possible, but we check if userLanguage static
        # translation exists before making any AI call.
        source_lang_trans = self.repo.get_approved_translation(
            question_key, source_language
        )

        # Step 3: Check static form translation in userLanguage
        static_trans = static_translations.get(user_language)
        if static_trans and static_trans.get("label"):
            self.repo.log_resolution(
                question_key=question_key,
                requested_language=user_language,
                resolved_language=user_language,
                source="static_translation",
                used_ai=False,
                result="resolved",
            )
            return ResolvedQuestion(
                text=static_trans["label"] or "",
                helpText=static_trans.get("help_text"),
                placeholder=static_trans.get("placeholder"),
                source="static_translation",
                reviewStatus="approved",
            )
        # Step 4: AI translation of approved source-language question
        if settings.QUESTION_AI_TRANSLATION_ENABLED and source_lang_trans:
            try:
                ai_req = QuestionTranslationRequest(
                    questionKey=question_key,
                    fieldType=field_type,
                    text=source_lang_trans.text,
                    helpText=source_lang_trans.help_text,
                    placeholder=source_lang_trans.placeholder,
                    sourceLanguage=source_language,
                    targetLanguage=user_language,
                )
                ai_res = await self.ai_provider.translate_question(ai_req)

                # Store in DB as pending_review
                definition = self.repo.get_definition(question_key)
                if not definition:
                    raise AIProviderError("Question definition not found")

                new_trans = self.repo.create_translation(
                    definition_id=definition.id,
                    language=user_language,
                    text=ai_res.text,
                    help_text=ai_res.help_text,
                    placeholder=ai_res.placeholder,
                    source="ai_translated",
                    review_status="pending_review",
                    provider=getattr(self.ai_provider, "_model", "mock"),
                    model=getattr(self.ai_provider, "_model", "mock"),
                    prompt_version="v1",
                )

                self.repo.log_resolution(
                    question_key=question_key,
                    requested_language=user_language,
                    resolved_language=user_language,
                    source="ai_translated",
                    used_ai=True,
                    provider=new_trans.provider,
                    model=new_trans.model,
                    prompt_version=new_trans.prompt_version,
                    result="resolved",
                )

                return ResolvedQuestion(
                    text=new_trans.text,
                    helpText=new_trans.help_text,
                    placeholder=new_trans.placeholder,
                    source="ai_translated",
                    reviewStatus="pending_review",
                    provider=new_trans.provider,
                    model=new_trans.model,
                    promptVersion=new_trans.prompt_version,
                )
            except AIProviderError as e:
                logger.warning("AI translation failed for key %s: %s", question_key, e)

        # Step 5: AI generation from minimal field metadata
        if settings.QUESTION_AI_GENERATION_ENABLED:
            try:
                gen_req = QuestionGenerationRequest(
                    questionKey=question_key,
                    fieldType=field_type,
                    purpose="collect_value",
                    required=True,
                    targetLanguage=user_language,
                    fieldConfig=field_configuration,
                )
                gen_res = await self.ai_provider.generate_question(gen_req)

                definition = self.repo.get_definition(question_key)
                if not definition:
                    raise AIProviderError("Question definition not found")

                new_trans = self.repo.create_translation(
                    definition_id=definition.id,
                    language=user_language,
                    text=gen_res.text,
                    help_text=gen_res.help_text,
                    placeholder=gen_res.placeholder,
                    source="ai_generated",
                    review_status="pending_review",
                    provider=getattr(self.ai_provider, "_model", "mock"),
                    model=getattr(self.ai_provider, "_model", "mock"),
                    prompt_version="v1",
                )

                self.repo.log_resolution(
                    question_key=question_key,
                    requested_language=user_language,
                    resolved_language=user_language,
                    source="ai_generated",
                    used_ai=True,
                    provider=new_trans.provider,
                    model=new_trans.model,
                    prompt_version=new_trans.prompt_version,
                    result="resolved",
                )

                return ResolvedQuestion(
                    text=new_trans.text,
                    helpText=new_trans.help_text,
                    placeholder=new_trans.placeholder,
                    source="ai_generated",
                    reviewStatus="pending_review",
                    provider=new_trans.provider,
                    model=new_trans.model,
                    promptVersion=new_trans.prompt_version,
                )
            except AIProviderError as e:
                logger.warning("AI generation failed for key %s: %s", question_key, e)

        # Step 6: Deterministic non-AI fallback
        return self._resolve_static_or_deterministic_fallback(
            question_key=question_key,
            field_type=field_type,
            user_language=user_language,
            static_translations=static_translations,
        )

    def _resolve_static_or_deterministic_fallback(
        self,
        question_key: str | None,
        field_type: str,
        user_language: str,
        static_translations: dict[str, dict[str, str | None]],
    ) -> ResolvedQuestion:
        # Check if any static translation exists in userLanguage
        static_trans = static_translations.get(user_language)
        if static_trans and static_trans.get("label"):
            if question_key:
                self.repo.log_resolution(
                    question_key=question_key,
                    requested_language=user_language,
                    resolved_language=user_language,
                    source="static_translation",
                    used_ai=False,
                    result="resolved",
                )
            return ResolvedQuestion(
                text=static_trans["label"] or "",
                helpText=static_trans.get("help_text"),
                placeholder=static_trans.get("placeholder"),
                source="static_translation",
                reviewStatus="approved",
            )

        # Fallback to sourceLanguage static translation if available
        for lang in list(static_translations.keys()):
            s_trans = static_translations.get(lang)
            if s_trans and s_trans.get("label"):
                if question_key:
                    self.repo.log_resolution(
                        question_key=question_key,
                        requested_language=user_language,
                        resolved_language=lang,
                        source="deterministic_fallback",
                        used_ai=False,
                        result="fallback",
                    )
                return ResolvedQuestion(
                    text=s_trans["label"] or "",
                    helpText=s_trans.get("help_text"),
                    placeholder=s_trans.get("placeholder"),
                    source="deterministic_fallback",
                    reviewStatus="approved",
                )

        # Ultimate fallback
        label = (
            question_key.split(".")[-1].replace("_", " ").capitalize()
            if question_key
            else "field"
        )
        text = f"Please provide a value for “{label}”."
        if question_key:
            self.repo.log_resolution(
                question_key=question_key,
                requested_language=user_language,
                resolved_language=None,
                source="deterministic_fallback",
                used_ai=False,
                result="fallback",
            )
        return ResolvedQuestion(
            text=text,
            helpText=None,
            placeholder=None,
            source="deterministic_fallback",
            reviewStatus="approved",
        )
