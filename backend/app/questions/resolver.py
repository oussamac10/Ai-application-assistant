import logging
from typing import Any

from sqlalchemy.orm import Session

from app.ai.errors import AIProviderError
from app.ai.mock_provider import AIProvider
from app.ai.schemas import QuestionGenerationRequest, QuestionTranslationRequest
from app.ai.text_translation import translate_text
from app.core.config import settings
from app.questions.repositories import QuestionRepository
from app.questions.schemas import ResolvedQuestion

logger = logging.getLogger(__name__)

# Placeholder used only for the resolution-log row (question_key is
# NOT NULL there) when a field has no stable catalog key at all — never
# used as a real lookup/cache key.
_UNKEYED_LOG_PLACEHOLDER = "(unkeyed)"


class QuestionResolver:
    """Resolves a field's user-facing question text — the single shared
    presentation/translation service used by every guided-session flow
    (manually-selected predefined forms and dynamically-detected ones
    alike). Callers differ only in what evidence they can supply
    (`question_key`, `static_translations`); the resolution order and AI
    fallback/caching behavior below are identical for all of them.
    """

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

        Resolution sequence (steps 1-2 and 5 only apply when a stable
        `question_key` is available — a reusable catalog entry needs a
        stable key to look up or persist under):
        1. Approved reusable question in userLanguage (DB)
        2. Approved reusable question in sourceLanguage (DB) (used to translate with AI)
        3. Approved static translation from the immutable form version
        4. AI translation — of an approved source-language catalog entry
           when one exists, otherwise of the best available static
           translation (this is what makes translation work for manually
           selected forms with no catalog coverage for the requested
           language, and never assumes form_language == user_language)
        5. AI generation from minimal field metadata
        6. Deterministic non-AI fallback
        """
        # Step 1: approved reusable translation in user_language
        if question_key:
            approved_user_lang = self.repo.get_approved_translation(
                question_key, user_language
            )
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
                pending_user_lang = self.repo.get_pending_translation(
                    question_key, user_language
                )
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

        # Step 2: approved sourceLanguage reusable translation, fetched now
        # so step 4 can use it as AI-translation input if no static
        # user_language translation is found below.
        source_lang_trans = (
            self.repo.get_approved_translation(question_key, source_language)
            if question_key
            else None
        )

        # Step 3: static translation from the immutable form version, in
        # user_language — never assumes form_language == user_language;
        # this only matches when the form was actually authored (or, for
        # dynamically-detected fields, previously translated) in that
        # specific language.
        static_trans = static_translations.get(user_language)
        if static_trans and static_trans.get("label"):
            self.repo.log_resolution(
                question_key=question_key or _UNKEYED_LOG_PLACEHOLDER,
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

        # Step 4a: AI translation of an approved source-language catalog
        # entry (preserves help_text/placeholder from the catalog).
        if settings.QUESTION_AI_TRANSLATION_ENABLED and source_lang_trans:
            resolved = await self._try_translate_from_catalog(
                question_key=question_key,  # type: ignore[arg-type]
                field_type=field_type,
                source_language=source_language,
                user_language=user_language,
                source_lang_trans=source_lang_trans,
            )
            if resolved is not None:
                return resolved

        # Step 4b: AI translation of the best available static translation
        # — the fallback that makes a manually selected form (authored in
        # only one language, with or without a catalog question_key) still
        # display in user_language rather than silently staying in
        # whatever language it happens to be stored in.
        elif settings.QUESTION_AI_TRANSLATION_ENABLED:
            resolved = await self._try_translate_from_static(
                question_key=question_key,
                field_type=field_type,
                source_language=source_language,
                user_language=user_language,
                static_translations=static_translations,
            )
            if resolved is not None:
                return resolved

        # Step 5: AI generation from minimal field metadata (needs a
        # stable key — there is no reusable definition to generate under
        # otherwise).
        if question_key and settings.QUESTION_AI_GENERATION_ENABLED:
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

                definition = self.repo.get_definition(
                    question_key
                ) or self.repo.create_definition(
                    question_key=question_key,
                    field_type=field_type,
                    purpose="collect_value",
                    domain="auto",
                )

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

    async def _try_translate_from_catalog(
        self,
        *,
        question_key: str,
        field_type: str,
        source_language: str,
        user_language: str,
        source_lang_trans: Any,
    ) -> ResolvedQuestion | None:
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

            definition = self.repo.get_definition(
                question_key
            ) or self.repo.create_definition(
                question_key=question_key,
                field_type=field_type,
                purpose="collect_value",
                domain="auto",
            )

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
            return None

    async def _try_translate_from_static(
        self,
        *,
        question_key: str | None,
        field_type: str,
        source_language: str,
        user_language: str,
        static_translations: dict[str, dict[str, str | None]],
    ) -> ResolvedQuestion | None:
        """Translates the best available static translation into
        user_language via the shared text-translation helper — used when
        there is no reusable-catalog entry to translate from (no
        question_key, or the catalog simply has no source_language
        translation for it). Never assumes the form's own language equals
        user_language: it only ever uses this as the *input* to a real
        translation call.
        """
        source_static = static_translations.get(source_language)
        if not (source_static and source_static.get("label")):
            source_static = next(
                (s for s in static_translations.values() if s and s.get("label")),
                None,
            )
        if not source_static:
            return None

        translation = await translate_text(
            self.ai_provider,
            source_static["label"] or "",
            source_language,
            user_language,
        )
        if translation.translated_text == translation.source_text:
            # Translation unavailable (AI failure) — let the caller fall
            # through to generation/deterministic fallback instead of
            # silently caching a non-translation.
            return None

        help_text = source_static.get("help_text")
        placeholder = source_static.get("placeholder")

        if not question_key:
            self.repo.log_resolution(
                question_key=_UNKEYED_LOG_PLACEHOLDER,
                requested_language=user_language,
                resolved_language=user_language,
                source="ai_translated",
                used_ai=True,
                result="resolved",
            )
            return ResolvedQuestion(
                text=translation.translated_text,
                helpText=help_text,
                placeholder=placeholder,
                source="ai_translated",
                reviewStatus="pending_review",
            )

        definition = self.repo.get_definition(
            question_key
        ) or self.repo.create_definition(
            question_key=question_key,
            field_type=field_type,
            purpose="collect_value",
            domain="auto",
        )
        new_trans = self.repo.create_translation(
            definition_id=definition.id,
            language=user_language,
            text=translation.translated_text,
            help_text=help_text,
            placeholder=placeholder,
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
