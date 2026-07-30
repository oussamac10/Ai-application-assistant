import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.ai.errors import AIProviderMalformedResponseError, AIProviderValidationError
from app.ai.mock_provider import AIProvider, MockAIProvider
from app.ai.schemas import ExtractionRequest, ExtractionResult
from app.ai.text_translation import translate_text
from app.answers.errors import FieldProblem, SummaryNotConfirmableError
from app.answers.models import FormAnswer
from app.answers.normalization.context import (
    apply_currency_context,
    is_proper_noun_field,
)
from app.answers.normalization.normalization import normalize_value
from app.answers.repositories import AnswerRepository
from app.answers.states import (
    ANSWERED,
    INVALID,
    REQUIRED,
    SKIPPED,
    UNANSWERED,
    UNREACHED,
    answer_state,
    field_requiredness,
    is_declaration,
    is_skippable,
)
from app.answers.validation.validation import validate_value
from app.core.config import settings
from app.forms.models import FormField
from app.forms.repositories import FormRepository
from app.questions.resolver import QuestionResolver
from app.sessions.services import (
    ResourceNotFoundError,
    SessionService,
    StateConflictError,
    ValidationError,
)
from app.translation.backfill import backfill_language
from app.translation.errors import TranslationError
from app.translation.factory import (
    build_fallback_translation_provider,
    build_translation_provider,
)

logger = logging.getLogger(__name__)


def _source_label(field: FormField) -> str:
    """The field's label in the form's own language.

    Deliberately the *source* label, not the translated one: currency words
    and proper-noun keywords are matched against the wording the document
    actually used, which is stable, rather than against a translation that
    varies with the interface language.
    """
    version = getattr(field, "version", None)
    source_language = getattr(version, "source_language", None)
    translations = list(getattr(field, "translations", []) or [])
    if source_language:
        for translation in translations:
            if translation.language == source_language and translation.label:
                return str(translation.label)
    return str(translations[0].label) if translations else ""


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

# Why an answered value cannot be accepted, by field type. A stable code the
# frontend can translate — never a sentence, and never the value itself.
_INVALID_REASON_BY_TYPE: dict[str, str] = {
    "date": "invalid_date",
    "email": "invalid_email",
    "phone": "invalid_phone",
    "number": "invalid_number",
    "integer": "invalid_number",
    "decimal": "invalid_number",
    "money": "invalid_currency",
    "currency": "invalid_currency",
    "country": "invalid_country",
    "iban": "invalid_iban",
    "boolean": "invalid_boolean",
    "single_choice": "invalid_choice",
    "multiple_choice": "invalid_choice",
}


def _invalid_reason(field: FormField, answer: FormAnswer) -> str:
    """The stable reason code for an answer that failed."""
    if answer.requires_clarification:
        return "needs_clarification"
    return _INVALID_REASON_BY_TYPE.get(field.field_type, "invalid_value")


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
        """Progress through the questions the user is actually asked.

        Counted over *answerable* fields, not required ones. Since
        requiredness became evidence-based (Phase 15), a form that marks
        nothing mandatory has zero required fields — and progress read
        "Question 1 of 0 (100%)" before the user had answered anything.
        Completion still checks required fields; only the progress the user
        sees counts every question.
        """
        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            return {
                "confirmedRequiredFields": 0,
                "totalRequiredFields": 0,
                "totalQuestions": 0,
                "answeredQuestions": 0,
                "percentage": 0,
            }

        required_field_ids = {
            f.id for f in version.fields if field_requiredness(f) == REQUIRED
        }
        total_required = len(required_field_ids)

        # Progress the *user* sees is measured over every question they are
        # asked. `totalRequiredFields` keeps its own meaning for completion
        # checks; since requiredness became evidence-based (Phase 15) a form
        # that marks nothing mandatory has zero of them, and the progress bar
        # read "Question 1 of 0 (100%)" before a single answer.
        total_questions = len(version.fields)
        answers = self.repo.get_answers_for_session(session.id)
        # A deliberately skipped question is *dealt with* as far as progress is
        # concerned: the user made a decision about it and must not be shown
        # as having work left on it.
        confirmed_ids = {
            a.field_id for a in answers if a.status in ("confirmed", "skipped")
        }
        answered_questions = sum(1 for f in version.fields if f.id in confirmed_ids)

        if total_required == 0:
            return {
                "confirmedRequiredFields": 0,
                "totalRequiredFields": 0,
                "totalQuestions": total_questions,
                "answeredQuestions": answered_questions,
                "percentage": (
                    int((answered_questions / total_questions) * 100)
                    if total_questions
                    else 100
                ),
            }

        confirmed_required = sum(
            1
            for a in answers
            if a.field_id in required_field_ids and a.status == "confirmed"
        )

        percentage = (
            int((answered_questions / total_questions) * 100) if total_questions else 0
        )
        return {
            "confirmedRequiredFields": confirmed_required,
            "totalRequiredFields": total_required,
            "totalQuestions": total_questions,
            "answeredQuestions": answered_questions,
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
            # Three states, so the frontend can show "Required", "Optional",
            # or — when the document said nothing — no label at all.
            "requiredness": field_requiredness(field),
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

        answers = {a.field_id: a for a in self.repo.get_answers_for_session(session.id)}

        def still_open(field: FormField) -> bool:
            ans = answers.get(field.id)
            # A skipped question is dealt with: the user decided about it and
            # must not be dragged back to it.
            return ans is None or ans.status not in ("confirmed", "skipped")

        fields_by_pos = {f.position: f for f in version.fields}
        stored = fields_by_pos.get(session.current_field_position)

        # The stored position wins whenever it still needs attention. Skip and
        # "edit this one" both move it deliberately, and a rule that always
        # jumped to the first incomplete required field would undo them.
        if stored is not None and still_open(stored):
            current_field = stored
        else:
            # Otherwise resume at the first question that still needs an
            # answer, mandatory ones first.
            first_required_open: FormField | None = next(
                (
                    f
                    for f in version.fields
                    if field_requiredness(f) == REQUIRED and still_open(f)
                ),
                None,
            )
            current_field = first_required_open or stored or version.fields[0]

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

        # A blank submission is not an answer, and it is not a skip either.
        # Storing it would send an empty string into normalization, the
        # validators and the AI provider — all of which then report something
        # about a value that does not exist. Skipping is an explicit action
        # with its own endpoint and its own state.
        if not original_answer or not original_answer.strip():
            raise ValidationError(
                "An answer cannot be empty. Skip the question instead to leave "
                "it unanswered."
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
            # The label is authoritative about currency. A field reading
            # "Revenu net mensuel en euros" came back as USD; overriding
            # deterministically is more reliable than prompting harder, and
            # when the label names no currency none is invented.
            norm_val, currency_corrected = apply_currency_context(
                norm_val, _source_label(field), original_answer
            )
            if currency_corrected:
                logger.info(
                    "Currency corrected from the field label (field_type=%s)",
                    field.field_type,
                )
            is_valid, err = validate_value(
                field.field_type,
                norm_val,
                field.required,
                field.configuration,
                options=field.options,
            )

            answer.normalized_value = norm_val
            # The *output* value is what gets written into the completed form.
            # For a proper noun that must be the text the user typed: asked to
            # render an answer in the output language, the model returned
            # "stuttgart" transliterated into Arabic, and `domain-rules.md`
            # forbids transliterating a name automatically — a city, an
            # employer or a bank is a proper noun exactly like a person.
            # Structured extraction (normalized_value) is still kept; only the
            # rendered output is pinned.
            if is_proper_noun_field(_source_label(field), field.field_type):
                answer.output_value = original_answer
            else:
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

    def skip_field(
        self, session_id: str, field_id: str, raw_token: str | None
    ) -> FormAnswer:
        """Records that the user chose not to answer an optional question.

        A skip is its own state, not an empty answer: an empty string would be
        validated, normalized and counted as invalid, and would be
        indistinguishable from a field the user simply has not reached. So the
        stored answer carries `status="skipped"` with null values, runs no
        validation and no normalization, and needs no confirmation.

        Skipping is allowed for `optional` **and** `unknown`. Unknown does not
        mean required: when the document carries no marker, the user must be
        able to move past a question the form never asked them to answer. Only
        an explicitly `required` field refuses.
        """
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            raise ResourceNotFoundError("Form version not found.")

        field = next((f for f in version.fields if f.id == field_id), None)
        if not field:
            raise ValidationError(
                "Field does not belong to the session's form version."
            )
        if not is_skippable(field):
            raise ValidationError("A required question cannot be skipped.")

        answer = self.repo.get_answer(session.id, field_id)
        if not answer:
            answer = FormAnswer(
                session_id=session.id,
                field_id=field_id,
                original_answer=None,
                original_language=session.user_language,
            )

        answer.original_answer = None
        answer.normalized_value = None
        answer.output_value = None
        answer.status = "skipped"
        answer.validation_status = "not_checked"
        answer.requires_clarification = False
        answer.confirmed_by_user = False
        answer.confirmed_at = None
        self.repo.save_answer(answer)

        # Advance exactly as confirming does, so a skip moves the user on.
        fields = sorted(version.fields, key=lambda f: f.position)
        next_field = next((f for f in fields if f.position > field.position), None)
        if next_field:
            session.current_field_position = next_field.position
            self.db.commit()

        logger.info(
            "Question skipped: session=%s position=%d",
            session.public_id,
            field.position,
        )
        return answer

    def reopen_field(
        self, session_id: str, field_id: str, raw_token: str | None
    ) -> dict[str, Any]:
        """Moves the guided flow back to one question so it can be edited.

        The summary's "Edit" used to re-submit the field's existing answer to
        un-confirm it, which could not work for a question with nothing in it:
        it submitted an empty string, and — now that a blank is refused — would
        fail outright. Editing is a *navigation* action, so it moves the
        session's position and clears confirmation without touching the stored
        value. A skipped question stays skipped until the user answers it.
        """
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        if session.status != "in_progress":
            raise StateConflictError("Session is not in progress.")

        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            raise ResourceNotFoundError("Form version not found.")

        field = next((f for f in version.fields if f.id == field_id), None)
        if not field:
            raise ValidationError(
                "Field does not belong to the session's form version."
            )

        answer = self.repo.get_answer(session.id, field_id)
        if answer is not None and answer.status == "confirmed":
            # Back to the state a valid answer sits in before confirmation —
            # the value is kept, only the user's acceptance of it is withdrawn.
            answer.status = "awaiting_confirmation"
            answer.confirmed_by_user = False
            answer.confirmed_at = None
            self.repo.save_answer(answer)

        session.current_field_position = field.position
        self.db.commit()

        logger.info(
            "Question reopened for editing: session=%s position=%d",
            session.public_id,
            field.position,
        )
        return {"field_id": field.id, "position": field.position}

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

    async def _backfill_output_language(self, version: Any, language: str) -> None:
        """Replaces deferred source-text placeholders for `language`.

        Failures are swallowed on purpose: a summary must still render when
        the translation provider is unavailable, showing source text rather
        than an error. The placeholder rows are already valid text.
        """
        try:
            await backfill_language(
                self.db,
                version,
                language,
                build_translation_provider(
                    settings.TRANSLATION_PROVIDER, self.ai_provider
                ),
                build_fallback_translation_provider(
                    settings.TRANSLATION_FALLBACK_PROVIDER, self.ai_provider
                ),
            )
        except (TranslationError, ValueError) as exc:
            logger.warning(
                "Deferred translation backfill failed for version=%s language=%s "
                "(%s); the summary falls back to source text",
                version.id,
                language,
                type(exc).__name__,
            )

    async def get_summary(
        self, session_id: str, raw_token: str | None
    ) -> list[dict[str, Any]]:
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            raise ResourceNotFoundError("Form version not found.")

        # Question preparation translates only the interface language and
        # leaves other supported languages holding source text (Phase 15).
        # The summary is the first point a user reviews the form as it will be
        # written, so this is where the output language is actually needed.
        # Idempotent and a no-op when nothing was deferred.
        if version.origin == "dynamic_detection":
            await self._backfill_output_language(version, session.output_language)

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
                    "requiredness": field_requiredness(field),
                    "original_answer": ans.original_answer if ans else None,
                    "normalized_value": ans.normalized_value if ans else None,
                    "output_value": ans.output_value if ans else None,
                    "status": ans.status if ans else "unanswered",
                    # What the *user* did, independent of requiredness. The
                    # summary needs to tell "skipped" from "never reached"
                    # from "missing a required answer", and `status` alone
                    # cannot: it says "unanswered" for both of the first two.
                    "answer_state": answer_state(ans),
                    "validation_status": ans.validation_status
                    if ans
                    else "not_checked",
                    "confirmed_by_user": ans.confirmed_by_user if ans else False,
                }
            )

        return summary

    @staticmethod
    def _log_confirmation_diagnostics(
        session: Any,
        version: Any,
        answers: dict[str, FormAnswer],
        missing: list[FieldProblem],
        invalid: list[FieldProblem],
    ) -> None:
        """One line saying why a session is or is not confirmable.

        Counts only. No label, no key, no submitted value and no token — the
        question "why is this form stuck?" is answerable from shape alone, and
        answers are private (`docs/claude/working-rules.md`).
        """
        by_requiredness = {REQUIRED: 0, "optional": 0, "unknown": 0}
        unanswered_optional = unanswered_unknown = skipped = 0
        for field in version.fields:
            state = field_requiredness(field)
            by_requiredness[state] = by_requiredness.get(state, 0) + 1
            answer = answers.get(field.id)
            answer_status = answer_state(answer)
            if answer_status == SKIPPED:
                skipped += 1
            elif answer_status in (UNREACHED, UNANSWERED):
                if state == "optional":
                    unanswered_optional += 1
                elif state == "unknown":
                    unanswered_unknown += 1

        logger.info(
            "Summary confirmation check: session=%s confirmable=%s "
            "required_fields=%d optional_fields=%d unknown_requiredness_fields=%d "
            "missing_required_fields=%d unanswered_optional_fields=%d "
            "unanswered_unknown_fields=%d skipped_fields=%d "
            "invalid_answered_fields=%d",
            session.public_id,
            not (missing or invalid),
            by_requiredness[REQUIRED],
            by_requiredness["optional"],
            by_requiredness["unknown"],
            len(missing),
            unanswered_optional,
            unanswered_unknown,
            skipped,
            len(invalid),
        )

    def _missing_required_fields(
        self, version: Any, answers: dict[str, FormAnswer]
    ) -> list[FieldProblem]:
        """Explicitly required questions with nothing usable in them.

        Only `requiredness == "required"` is considered. A question the
        document never marked cannot be "missing" — there was nothing to
        supply.
        """
        problems: list[FieldProblem] = []
        for field in version.fields:
            if field_requiredness(field) != REQUIRED:
                continue
            ans = answers.get(field.id)
            state = answer_state(ans)
            if state in (UNREACHED, UNANSWERED):
                problems.append(
                    FieldProblem(
                        field.key,
                        "declaration_not_accepted"
                        if is_declaration(field)
                        else "missing_required",
                    )
                )
            elif state == SKIPPED:
                # Skip is refused for required fields, so this is only
                # reachable if requiredness changed after the skip.
                problems.append(FieldProblem(field.key, "required_question_skipped"))
            elif state == ANSWERED and ans is not None and ans.status != "confirmed":
                problems.append(FieldProblem(field.key, "not_confirmed"))
        return problems

    def _invalid_answer_fields(
        self, version: Any, answers: dict[str, FormAnswer]
    ) -> list[FieldProblem]:
        """Questions the user *did* answer whose value cannot be accepted.

        Requiredness is irrelevant here: a wrong date is wrong on an optional
        field too. Absence is equally irrelevant — an unanswered or skipped
        question has no value to be invalid, which is precisely what the old
        single-pass check got wrong.
        """
        problems: list[FieldProblem] = []
        for field in version.fields:
            ans = answers.get(field.id)
            if answer_state(ans) != INVALID or ans is None:
                continue
            problems.append(FieldProblem(field.key, _invalid_reason(field, ans)))
        return problems

    def confirm_summary(self, session_id: str, raw_token: str | None) -> Any:
        session = self.session_service.get_session(
            session_id, raw_token, self.current_user_id
        )
        if session.status != "in_progress":
            raise StateConflictError("Session is not in progress.")

        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            raise ResourceNotFoundError("Form version not found.")

        answers = {a.field_id: a for a in self.repo.get_answers_for_session(session.id)}

        # Two independent questions, asked separately and reported together, so
        # the user sees everything blocking them at once instead of fixing one
        # field per round trip.
        missing = self._missing_required_fields(version, answers)
        invalid = self._invalid_answer_fields(version, answers)

        self._log_confirmation_diagnostics(session, version, answers, missing, invalid)

        if missing or invalid:
            raise SummaryNotConfirmableError(missing, invalid)

        # Transition: in_progress -> awaiting_final_confirmation -> ready_for_export
        session.status = "awaiting_final_confirmation"
        self.db.commit()

        session.status = "ready_for_export"
        session.completed_at = datetime.now(UTC)
        self.db.commit()

        return session
