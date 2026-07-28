import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.ai.errors import AIProviderMalformedResponseError, AIProviderValidationError
from app.ai.mock_provider import AIProvider, MockAIProvider
from app.ai.schemas import ExtractionRequest, ExtractionResult
from app.ai.text_translation import translate_text
from app.answers.models import FormAnswer
from app.answers.normalization.normalization import normalize_value
from app.answers.repositories import AnswerRepository
from app.answers.validation.validation import validate_value
from app.forms.models import FormField
from app.forms.repositories import FormRepository
from app.questions.resolver import QuestionResolver
from app.sessions.services import (
    ResourceNotFoundError,
    SessionService,
    StateConflictError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Choice fields are rendered by the frontend as a <select>/checkbox group
# bound directly to each option's canonical value — the submitted answer is
# already the exact canonical value(s), never free text needing AI
# interpretation. Per the "deterministic validation over AI" domain rule,
# these are validated deterministically against the field's own configured
# options and never routed through the AI provider: an AI call would need
# the option set repeated in its prompt context (which submit_answer never
# populated) just to reproduce a membership check plain code already does
# reliably, and — for a dynamically detected field with no other AI-visible
# description of its options — could not answer at all.
_DETERMINISTIC_CHOICE_TYPES = ("single_choice", "multiple_choice")


class AnswerService:
    def __init__(
        self,
        db: Session,
        ai_provider: AIProvider | None = None,
        current_user_id: str | None = None,
    ):
        self.db = db
        self.repo = AnswerRepository(db)
        self.form_repo = FormRepository(db)
        self.session_service = SessionService(db)
        self.ai_provider: AIProvider = (
            ai_provider if ai_provider is not None else MockAIProvider()
        )
        self.resolver = QuestionResolver(db, self.ai_provider)
        # Resolved from the auth cookie, never trusted from the client body
        # — every session lookup below authorizes against this (or, for
        # anonymous callers, the ownership token) via SessionService.
        self.current_user_id = current_user_id

    def get_progress(self, session: Any) -> dict[str, int]:
        """Calculate progress based on confirmed required fields."""
        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            return {
                "confirmedRequiredFields": 0,
                "totalRequiredFields": 0,
                "percentage": 0,
            }

        required_field_ids = {f.id for f in version.fields if f.required}
        total_required = len(required_field_ids)

        if total_required == 0:
            return {
                "confirmedRequiredFields": 0,
                "totalRequiredFields": 0,
                "percentage": 100,
            }

        answers = self.repo.get_answers_for_session(session.id)
        confirmed_required = sum(
            1
            for a in answers
            if a.field_id in required_field_ids and a.status == "confirmed"
        )

        percentage = int((confirmed_required / total_required) * 100)
        return {
            "confirmedRequiredFields": confirmed_required,
            "totalRequiredFields": total_required,
            "percentage": percentage,
        }

    async def _get_translated_field(
        self, field: FormField, user_lang: str, source_lang: str, output_lang: str
    ) -> dict[str, Any]:
        # Build dictionary of static translations
        static_translations = {}
        for t in field.translations:
            static_translations[t.language] = {
                "label": t.label,
                "help_text": t.help_text,
                "placeholder": t.placeholder,
            }

        resolved = await self.resolver.resolve_question(
            question_key=field.question_key,
            field_type=field.field_type,
            user_language=user_lang,
            source_language=source_lang,
            output_language=output_lang,
            field_configuration=field.configuration,
            static_translations=static_translations,
        )

        label = resolved.text
        help_text = resolved.help_text
        placeholder = resolved.placeholder

        # Translate options. The stable `value` is never touched — only
        # the display label. If no translation exists yet for user_lang,
        # translate the best available label via AI rather than silently
        # showing it in whatever language happens to be stored (the same
        # "manually selected forms must not assume form_language ==
        # user_language" guarantee as the question text above).
        translated_options = []
        if field.options:
            for opt in field.options:
                opt_trans = {ot.language: ot for ot in opt.translations}
                ot = opt_trans.get(user_lang)
                if ot:
                    translated_options.append({"value": opt.value, "label": ot.label})
                    continue

                source_ot = opt_trans.get(source_lang) or (
                    opt.translations[0] if opt.translations else None
                )
                if source_ot and source_ot.label:
                    translation = await translate_text(
                        self.ai_provider, source_ot.label, source_lang, user_lang
                    )
                    translated_options.append(
                        {"value": opt.value, "label": translation.translated_text}
                    )
                else:
                    translated_options.append({"value": opt.value, "label": opt.value})

        return {
            "id": field.id,
            "key": field.key,
            "field_type": field.field_type,
            "required": field.required,
            "position": field.position,
            "label": label,
            "help_text": help_text,
            "placeholder": placeholder,
            "options": translated_options if field.options else None,
        }

    async def get_current_field(
        self, session_id: str, raw_token: str | None
    ) -> dict[str, Any]:
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        version = self.form_repo.get_version(session.form_version_id)
        if not version or not version.fields:
            raise ResourceNotFoundError("No fields found for this form version.")

        # First incomplete required field
        # (unanswered, draft, needs_clarification, awaiting_confirmation),
        # otherwise next position.
        answers = {a.field_id: a for a in self.repo.get_answers_for_session(session.id)}
        current_field = None

        for field in version.fields:
            ans = answers.get(field.id)
            if field.required and (not ans or ans.status != "confirmed"):
                current_field = field
                break

        # Fallback to the session's stored position if all required fields are confirmed
        if not current_field:
            stored_pos = session.current_field_position
            fields_by_pos = {f.position: f for f in version.fields}
            current_field = fields_by_pos.get(stored_pos) or version.fields[0]

        # Update session position
        session.current_field_position = current_field.position
        self.db.commit()

        # Build response
        ans = answers.get(current_field.id)
        field_data = await self._get_translated_field(
            current_field,
            session.user_language,
            session.source_language,
            session.output_language,
        )
        field_data["current_answer_status"] = ans.status if ans else None
        field_data["progress"] = self.get_progress(session)

        return field_data

    async def previous_field(
        self, session_id: str, raw_token: str | None
    ) -> dict[str, Any]:
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        if session.status != "in_progress":
            raise StateConflictError("Session is not in progress.")

        version = self.form_repo.get_version(session.form_version_id)
        if not version or not version.fields:
            raise ResourceNotFoundError("No fields found for this form version.")

        # Find field at position before current
        fields = sorted(version.fields, key=lambda f: f.position)
        current_pos = session.current_field_position

        prev_field = None
        for f in reversed(fields):
            if f.position < current_pos:
                prev_field = f
                break

        if not prev_field:
            raise StateConflictError("Already at the first field.")

        session.current_field_position = prev_field.position
        self.db.commit()

        ans = self.repo.get_answer(session.id, prev_field.id)
        field_data = await self._get_translated_field(
            prev_field,
            session.user_language,
            session.source_language,
            session.output_language,
        )
        field_data["current_answer_status"] = ans.status if ans else None
        field_data["progress"] = self.get_progress(session)

        return field_data

    async def submit_answer(
        self,
        session_id: str,
        field_id: str,
        original_answer: str,
        raw_token: str | None,
    ) -> FormAnswer:
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        if session.status != "in_progress":
            raise StateConflictError("Session is not in progress.")

        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            raise ResourceNotFoundError("Form version not found.")

        # Find field
        field = next((f for f in version.fields if f.id == field_id), None)
        if not field:
            raise ValidationError(
                "Field does not belong to the session's form version."
            )

        # Get or create answer
        answer = self.repo.get_answer(session.id, field_id)
        if not answer:
            answer = FormAnswer(
                session_id=session.id,
                field_id=field_id,
                original_answer=original_answer,
                original_language=session.user_language,
            )

        # Update original properties
        answer.original_answer = original_answer
        answer.original_language = session.user_language
        answer.confirmed_by_user = False
        answer.confirmed_at = None

        if field.field_type in _DETERMINISTIC_CHOICE_TYPES:
            self._apply_choice_answer(answer, field, original_answer)
            self.repo.save_answer(answer)
            return answer

        # Call MockAIProvider
        req = ExtractionRequest(
            fieldType=field.field_type,
            answer=original_answer,
            userLanguage=session.user_language,
            sourceLanguage=session.source_language,
            outputLanguage=session.output_language,
        )
        try:
            result = await self.ai_provider.extract_value(req)
        except (AIProviderMalformedResponseError, AIProviderValidationError) as exc:
            # The provider *did* respond (and already spent its one bounded
            # repair attempt — see OllamaAIProvider._call_ollama_structured)
            # but never produced a response matching the required schema.
            # Never surface that raw/malformed content, and never lose the
            # user's answer over it: fall back to the same deterministic
            # normalize_value()/validate_value() pipeline used for the
            # AI-success path, seeded with the original, untranslated
            # answer. This never forces a clarification purely because
            # parsing failed — a field that deterministically validates
            # (e.g. free-form text) proceeds normally; a field that doesn't
            # (e.g. an unparseable date) is marked invalid, same as any
            # other invalid answer, letting the user retry.
            #
            # A genuine transport failure (AIProviderTimeoutError,
            # AIProviderUnavailableError — Ollama unreachable/timed out, no
            # response received at all) is deliberately NOT caught here: it
            # propagates as the existing 504/503 error, since there is no
            # response to fall back on and retrying the whole request is
            # the correct recovery, not silently accepting an unverified
            # answer.
            logger.warning(
                "AI extraction returned a malformed/invalid response for "
                "field_type=%s; falling back to deterministic normalization "
                "of the original answer: %s",
                field.field_type,
                type(exc).__name__,
            )
            result = ExtractionResult(
                normalizedValue=original_answer,
                outputValue=None,
                requiresClarification=False,
                uncertainties=[],
            )

        if result.requires_clarification:
            answer.normalized_value = result.normalized_value
            answer.output_value = None
            answer.requires_clarification = True
            answer.status = "needs_clarification"
            answer.validation_status = "not_checked"
            # Attach dynamic property for JSON serializer
            answer._uncertainties = result.uncertainties  # type: ignore[attr-defined]
        else:
            norm_val = normalize_value(field.field_type, result.normalized_value)
            is_valid, err = validate_value(
                field.field_type,
                norm_val,
                field.required,
                field.configuration,
                options=field.options,
            )

            answer.normalized_value = norm_val
            answer.output_value = result.output_value
            answer.requires_clarification = False

            if is_valid:
                answer.validation_status = "valid"
                answer.status = "awaiting_confirmation"
            else:
                answer.validation_status = "invalid"
                answer.status = "draft"

        # Save
        self.repo.save_answer(answer)
        return answer

    @staticmethod
    def _apply_choice_answer(
        answer: FormAnswer, field: FormField, original_answer: str
    ) -> None:
        """Deterministically normalizes and validates a single_choice/
        multiple_choice answer against the field's own configured options
        — no AI call, no clarification. The submitted value(s) either match
        a configured option or they don't; there is nothing for an AI
        provider to interpret or clarify.
        """
        norm_val = normalize_value(field.field_type, original_answer)
        is_valid, _err = validate_value(
            field.field_type,
            norm_val,
            field.required,
            field.configuration,
            options=field.options,
        )

        answer.normalized_value = norm_val
        answer.requires_clarification = False

        if is_valid:
            answer.output_value = (
                ", ".join(norm_val)
                if field.field_type == "multiple_choice"
                else norm_val
            )
            answer.validation_status = "valid"
            answer.status = "awaiting_confirmation"
        else:
            answer.output_value = None
            answer.validation_status = "invalid"
            answer.status = "draft"

    def submit_clarification(
        self,
        session_id: str,
        answer_id: str,
        values: dict[str, Any],
        raw_token: str | None,
    ) -> FormAnswer:
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        if session.status != "in_progress":
            raise StateConflictError("Session is not in progress.")

        answer = self.repo.get_answer_by_id(answer_id)
        if not answer or answer.session_id != session.id:
            raise ResourceNotFoundError("Answer not found.")

        field = answer.field
        # Merge values
        existing = answer.normalized_value or {}
        if isinstance(existing, dict):
            merged = {**existing, **values}
        else:
            merged = values

        # Re-evaluate money clarification
        requires_clar = False
        uncertainties = []
        if field.field_type == "money":
            if "currency" not in merged or not merged["currency"]:
                requires_clar = True
                uncertainties.append("currency")
            if "period" not in merged or not merged["period"]:
                requires_clar = True
                uncertainties.append("period")

        answer.confirmed_by_user = False
        answer.confirmed_at = None

        if requires_clar:
            answer.normalized_value = merged
            answer.output_value = None
            answer.requires_clarification = True
            answer.status = "needs_clarification"
            answer.validation_status = "not_checked"
            answer._uncertainties = uncertainties  # type: ignore[attr-defined]
        else:
            norm_val = normalize_value(field.field_type, merged)
            is_valid, err = validate_value(
                field.field_type,
                norm_val,
                field.required,
                field.configuration,
                options=field.options,
            )

            answer.normalized_value = norm_val
            answer.requires_clarification = False

            if is_valid:
                answer.validation_status = "valid"
                answer.status = "awaiting_confirmation"
                # Construct output value
                if field.field_type == "money":
                    amt = norm_val.get("amount")
                    cur = norm_val.get("currency")
                    per = norm_val.get("period")
                    answer.output_value = f"{amt} {cur} {per}"
                else:
                    answer.output_value = str(norm_val)
            else:
                answer.validation_status = "invalid"
                answer.status = "draft"

        self.repo.save_answer(answer)
        return answer

    def confirm_answer(
        self, session_id: str, answer_id: str, raw_token: str | None
    ) -> FormAnswer:
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        if session.status != "in_progress":
            raise StateConflictError("Session is not in progress.")

        answer = self.repo.get_answer_by_id(answer_id)
        if not answer or answer.session_id != session.id:
            raise ResourceNotFoundError("Answer not found.")

        if (
            answer.status != "awaiting_confirmation"
            or answer.validation_status != "valid"
            or answer.requires_clarification
        ):
            raise StateConflictError("Cannot confirm an incomplete or invalid answer.")

        answer.status = "confirmed"
        answer.confirmed_by_user = True
        answer.confirmed_at = datetime.now(UTC)
        self.db.commit()

        # Advance to next field in position order
        version = self.form_repo.get_version(session.form_version_id)
        if version:
            fields = sorted(version.fields, key=lambda f: f.position)
            current_pos = session.current_field_position
            next_field = next((f for f in fields if f.position > current_pos), None)
            if next_field:
                session.current_field_position = next_field.position
                self.db.commit()

        return answer

    async def get_summary(
        self, session_id: str, raw_token: str | None
    ) -> list[dict[str, Any]]:
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            raise ResourceNotFoundError("Form version not found.")

        answers = {a.field_id: a for a in self.repo.get_answers_for_session(session.id)}
        summary = []

        for field in version.fields:
            ans = answers.get(field.id)
            translated = await self._get_translated_field(
                field,
                session.user_language,
                session.source_language,
                session.output_language,
            )

            summary.append(
                {
                    "field_id": field.id,
                    "field_key": field.key,
                    "label": translated["label"],
                    "required": field.required,
                    "original_answer": ans.original_answer if ans else None,
                    "normalized_value": ans.normalized_value if ans else None,
                    "output_value": ans.output_value if ans else None,
                    "status": ans.status if ans else "unanswered",
                    "validation_status": ans.validation_status
                    if ans
                    else "not_checked",
                    "confirmed_by_user": ans.confirmed_by_user if ans else False,
                }
            )

        return summary

    def confirm_summary(self, session_id: str, raw_token: str | None) -> Any:
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        if session.status != "in_progress":
            raise StateConflictError("Session is not in progress.")

        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            raise ResourceNotFoundError("Form version not found.")

        # Check required fields
        answers = {a.field_id: a for a in self.repo.get_answers_for_session(session.id)}
        for field in version.fields:
            ans = answers.get(field.id)
            if field.required:
                if not ans or ans.status != "confirmed":
                    raise StateConflictError(
                        f"Required field '{field.key}' must be confirmed."
                    )
            if ans:
                if ans.requires_clarification:
                    raise StateConflictError(
                        f"Field '{field.key}' requires clarification."
                    )
                if ans.validation_status != "valid":
                    raise StateConflictError(
                        f"Field '{field.key}' contains invalid value."
                    )

        # Transition: in_progress -> awaiting_final_confirmation -> ready_for_export
        session.status = "awaiting_final_confirmation"
        self.db.commit()

        session.status = "ready_for_export"
        session.completed_at = datetime.now(UTC)
        self.db.commit()

        return session
