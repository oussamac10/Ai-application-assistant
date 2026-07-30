"""Bridges confirmed detected fields into the existing guided-session
workflow.

Confirmed DetectedField rows are materialized into a synthetic, published
FormTemplate/FormVersion/FormField set — reusing FormService's own
validation (choice fields need options, published versions are immutable,
labels required for the source language, ...) rather than re-implementing
any of it. SessionService.create_session then starts a real guided session
completely unmodified. Only user-confirmed fields are ever used; pending or
rejected candidates never generate a question.

Language handling: the field-detection pipeline (native PDF text / OCR)
does not perform document-language detection, so a detected label/option's
own language is unknown to the system — it is assumed to be
`_DEFAULT_SOURCE_LANGUAGE` (see constant below). That assumed source
language is kept strictly separate from the session's languages: the
original detected text is always stored under the source language (for
mapping/audit — never discarded), and a translation is produced via the AI
provider for every *other* language the version supports.

Crucially that means **both** `user_language` (what the guided questions
are displayed in) and `output_language` (what the completed form is written
in) — see `_target_languages`. Generating only the user-language rows
produces a version that claims to support an output language it has no text
for, which `FormService.publish_version` rejects for any choice field, and
which therefore silently turned every document containing a choice group
into "no usable questions" whenever the two languages differed.

Stable option `value`s are never translated, only the display label shown
to the user.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.ai.batch_translation import TranslationStats, translate_texts
from app.ai.mock_provider import AIProvider
from app.core.config import settings
from app.documents.models import SourceDocument
from app.field_detection.confidence import AUTO_USABLE_REVIEW_STATUSES
from app.field_detection.errors import FieldDetectionValidationError
from app.field_detection.models import DetectedField, FieldDetectionResult
from app.forms.schemas import (
    FieldCreate,
    OptionSchema,
    OptionTranslationSchema,
    TranslationSchema,
)
from app.forms.services import FormService
from app.forms.services import ValidationError as FormValidationError
from app.questions.repositories import QuestionRepository
from app.sessions.models import FormSession
from app.sessions.services import SessionService

logger = logging.getLogger(__name__)

# Assumed language of detected label/option text — see module docstring.
# Kept independent of `user_language` so the resolver's static-translation
# step is never satisfied by untranslated source text mislabeled as the
# user's language.
_DEFAULT_SOURCE_LANGUAGE = "en"

# Maps a DetectedField.field_type to the form-model's own field_type
# vocabulary (see app/forms/validation/config_validation.py). Types with no
# direct guided-question equivalent (signature) or with unresolved evidence
# (unknown) safely degrade to a plain text question rather than blocking
# question generation.
_FIELD_TYPE_MAP: dict[str, str] = {
    "text": "string",
    "multiline_text": "multiline_text",
    "date": "date",
    "email": "email",
    "phone": "phone",
    "address": "address",
    "number": "integer",
    "currency": "money",
    "checkbox": "boolean",
    "radio": "single_choice",
    "select": "single_choice",
    "multiple_choice": "multiple_choice",
    "signature": "string",
    "unknown": "string",
}

_CHOICE_TYPES = ("single_choice", "multiple_choice")


def _map_field_type(detected_field: DetectedField) -> str:
    mapped = _FIELD_TYPE_MAP.get(detected_field.field_type, "string")
    if mapped in _CHOICE_TYPES and not detected_field.options:
        # A choice type with no known options can't be rendered — the
        # existing FormService.publish_version would reject it outright.
        return "string"
    return mapped


def _unique_key(base: str, used_keys: set[str]) -> str:
    candidate = base or "field"
    suffix = 2
    while candidate in used_keys:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used_keys.add(candidate)
    return candidate


def _target_languages(user_language: str, output_language: str) -> list[str]:
    """Every non-source language the generated version must carry text for.

    Both are required, and for different reasons: `user_language` is what
    the guided questions are displayed in, while `output_language` is what
    the completed form is written in. `FormService.publish_version`
    enforces an option translation for *every* supported output language
    (source language included), so generating only the user-language rows
    would make a version that claims to support an output language it has
    no text for — which is exactly how a document containing any choice
    field failed to publish whenever the two languages differed.
    """
    return sorted({user_language, output_language} - {_DEFAULT_SOURCE_LANGUAGE})


def _approved_catalog_labels(
    db: Session, fields: list[DetectedField], language: str
) -> dict[str, str]:
    """`{detected label: approved catalog label}` for every detected field
    whose normalized name matches an approved reusable question in `language`.

    Per `docs/claude/domain-rules.md`, approved human text wins over anything
    the AI would produce, and the AI must not be called when it exists. This
    is a lookup by semantic key (the detected field's normalized name), not by
    displayed text, which is exactly how the catalog is meant to be addressed.
    """
    repo = QuestionRepository(db)
    approved: dict[str, str] = {}
    for detected in fields:
        if not detected.label or detected.label in approved:
            continue
        translation = repo.get_approved_translation(detected.normalized_name, language)
        if translation is not None and translation.text:
            approved[detected.label] = translation.text
    return approved


async def _translations_by_language(
    db: Session,
    ai_provider: AIProvider,
    fields: list[DetectedField],
    target_languages: list[str],
    stats: TranslationStats,
) -> dict[str, dict[str, str]]:
    """Every translation the whole document needs, as
    `{language: {source_text: translated_text}}`.

    Collected in one pass before any field is built, which is what makes
    batching possible: previously each field (and each of its options) issued
    its own sequential AI call, so a 24-field document made 28 of them and
    took long enough that the frontend gave up on a request the backend was
    still working on.

    Choice-option *values* are translated for display only; the stable value
    written to the form stays the original text.
    """
    texts: list[str] = []
    for detected in fields:
        if detected.label:
            texts.append(detected.label)
        for option in detected.options:
            if option.value:
                texts.append(option.value)

    by_language: dict[str, dict[str, str]] = {}
    for language in target_languages:
        by_language[language] = await translate_texts(
            ai_provider,
            texts,
            _DEFAULT_SOURCE_LANGUAGE,
            language,
            batch_size=settings.AI_TRANSLATION_BATCH_SIZE,
            concurrency=settings.AI_TRANSLATION_CONCURRENCY,
            stats=stats,
            approved_lookup=_approved_catalog_labels(db, fields, language),
        )
    return by_language


def _translations_for(
    text: str, by_language: dict[str, dict[str, str]]
) -> dict[str, str]:
    """Narrows the document-wide map to one text. A text missing for a
    language falls back to itself, never to another field's translation."""
    return {
        language: translations.get(text, text)
        for language, translations in by_language.items()
    }


def _label_translations(
    source_text: str, translations_by_language: dict[str, str]
) -> list[TranslationSchema]:
    """Builds the field-label rows: the original source text is always kept
    (for mapping/audit), plus one row per target language."""
    rows = [TranslationSchema(language=_DEFAULT_SOURCE_LANGUAGE, label=source_text)]
    rows.extend(
        TranslationSchema(language=language, label=label)
        for language, label in translations_by_language.items()
    )
    return rows


def _option_translations(
    source_text: str, translations_by_language: dict[str, str]
) -> list[OptionTranslationSchema]:
    rows = [
        OptionTranslationSchema(language=_DEFAULT_SOURCE_LANGUAGE, label=source_text)
    ]
    rows.extend(
        OptionTranslationSchema(language=language, label=label)
        for language, label in translations_by_language.items()
    )
    return rows


_CHOICE_FIELD_TYPES = frozenset({"radio", "select", "multiple_choice"})


def build_review_metadata(
    detection_result: FieldDetectionResult,
) -> dict[str, int | str]:
    """Safe, non-sensitive counters persisted on the detection result for
    later Phase 14 admin/content-review consumption. Never includes answer
    values, labels, or document text — counts and status only.

    The `*ExcludedCount` breakdown gives Phase 14 a meaningful reason for
    each "needs_clarification" field without storing any of its actual
    content: an unclassifiable type, a choice group missing its options,
    or (the remainder) confidence below the clarification threshold.
    """
    fields = detection_result.fields
    needs_clarification = [
        f for f in fields if f.review_status == "needs_clarification"
    ]
    unknown_type_excluded = sum(
        1 for f in needs_clarification if f.field_type == "unknown"
    )
    missing_options_excluded = sum(
        1
        for f in needs_clarification
        if f.field_type in _CHOICE_FIELD_TYPES and not f.options
    )
    low_confidence_excluded = (
        len(needs_clarification) - unknown_type_excluded - missing_options_excluded
    )
    return {
        "autoConfirmedCount": sum(1 for f in fields if f.review_status == "confirmed"),
        "mediumConfidenceCount": sum(
            1 for f in fields if f.review_status == "pending_review"
        ),
        "needsClarificationCount": len(needs_clarification),
        "rejectedCount": sum(1 for f in fields if f.review_status == "rejected"),
        "totalFieldCount": len(fields),
        "unknownTypeExcludedCount": unknown_type_excluded,
        "missingOptionsExcludedCount": missing_options_excluded,
        "lowConfidenceExcludedCount": max(low_confidence_excluded, 0),
    }


async def create_session_from_confirmed_fields(
    db: Session,
    doc: SourceDocument,
    detection_result: FieldDetectionResult,
    user_language: str,
    output_language: str,
    ai_provider: AIProvider,
    current_user_id: str | None = None,
    include_auto_usable: bool = False,
) -> tuple[FormSession, str]:
    """Builds guided-session questions from the fields on `detection_result`
    that are safe to use.

    `include_auto_usable=False` (default) preserves the exact Phase 11
    contract: only fields a human explicitly marked "confirmed" via the
    review UI are used — this is what the admin/debug review screen calls.

    `include_auto_usable=True` is used by the Phase 13 automatic upload
    flow: it additionally includes fields the deterministic confidence
    router (`app/field_detection/confidence.py`) already judged safe
    ("pending_review" in auto mode means medium-confidence-but-usable, not
    "awaiting human review" — see that module's docstring). Fields the
    router marked "needs_clarification", and any "rejected" field, are
    never included either way.
    """
    usable_statuses = (
        AUTO_USABLE_REVIEW_STATUSES if include_auto_usable else frozenset({"confirmed"})
    )
    confirmed_fields = [
        field
        for field in detection_result.fields
        if field.review_status in usable_statuses
    ]
    logger.info(
        "Question generation input: document=%s detected=%d usable=%d "
        "(mode=%s, accepted_statuses=%s) user_language=%s output_language=%s",
        doc.public_id,
        len(detection_result.fields),
        len(confirmed_fields),
        "auto" if include_auto_usable else "manual",
        ",".join(sorted(usable_statuses)),
        user_language,
        output_language,
    )
    if not confirmed_fields:
        raise FieldDetectionValidationError(
            "No confirmed fields to generate questions from.",
            "field_detection_invalid_result",
        )

    form_service = FormService(db)
    template_key = f"dynamic-doc-{doc.public_id}"
    template = form_service.repo.get_template_by_key(template_key)
    if template is None:
        template = form_service.create_template(
            key=template_key,
            name=f"Dynamic form — {doc.sanitized_filename}",
            description="Auto-generated from user-confirmed detected fields.",
        )

    version = form_service.create_draft_version(
        form_template_id=template.id,
        source_language=_DEFAULT_SOURCE_LANGUAGE,
        # Must include output_language itself, not just the source/user
        # languages — otherwise a user who picks an output language that
        # differs from both (e.g. English interface, German output) makes
        # SessionService.create_session() below reject its own freshly
        # created version with "output language is not supported", an
        # unhandled-looking failure for a perfectly normal selection.
        supported_output_languages=sorted(
            {_DEFAULT_SOURCE_LANGUAGE, user_language, output_language}
        ),
        origin="dynamic_detection",
        pdf_template_key=None,
    )

    # Every language the version claims to support must actually have text
    # (see _target_languages for why both user and output language count).
    target_languages = _target_languages(user_language, output_language)

    # Every translation the document needs, resolved up front in bounded
    # batches (see app/ai/batch_translation.py) instead of one AI call per
    # field per language.
    translation_stats = TranslationStats()
    translation_started = time.perf_counter()
    translations_by_language = await _translations_by_language(
        db, ai_provider, confirmed_fields, target_languages, translation_stats
    )
    translation_duration = time.perf_counter() - translation_started

    used_keys: set[str] = set()
    added_field_count = 0
    skipped_field_count = 0
    position = 0
    for detected_field in confirmed_fields:
        key = _unique_key(detected_field.normalized_name, used_keys)
        try:
            field_type = _map_field_type(detected_field)

            label_translations = _translations_for(
                detected_field.label, translations_by_language
            )

            # Options live exclusively in the FormFieldOption rows created
            # via `options=` below (config_validation.py's strict per-type
            # allowlist rejects an "options" key inside `configuration` for
            # choice fields) — both answer validation and the frontend read
            # the real `field.options` relationship, never `configuration`.
            # The stable `value` is always the original detected text
            # (never translated); only the display label is.
            options: list[OptionSchema] = []
            if field_type in _CHOICE_TYPES:
                for option in detected_field.options:
                    option_translations = _translations_for(
                        option.value, translations_by_language
                    )
                    options.append(
                        OptionSchema(
                            value=option.value,
                            position=option.position,
                            translations=_option_translations(
                                option.value, option_translations
                            ),
                        )
                    )

            form_service.add_field_to_draft(
                version.id,
                FieldCreate(
                    key=key,
                    field_type=field_type,
                    required=(
                        detected_field.required
                        if detected_field.required is not None
                        else True
                    ),
                    position=position,
                    configuration={},
                    translations=_label_translations(
                        detected_field.label, label_translations
                    ),
                    options=options,
                ),
            )
            added_field_count += 1
            position += 1
        except FormValidationError:
            # One bad candidate (e.g. a choice group whose config still
            # can't be validated) must not fail the whole document when
            # other usable fields exist — skip only this field and keep
            # going. Never logs field content (label/options), only that a
            # skip happened and the detected field_type.
            skipped_field_count += 1
            logger.warning(
                "Skipping one detected field that failed form validation "
                "(field_type=%s); %d field(s) already added, continuing.",
                detected_field.field_type,
                added_field_count,
            )
            continue

    if added_field_count == 0:
        raise FieldDetectionValidationError(
            "No confirmed fields could be turned into usable questions.",
            "field_detection_invalid_result",
        )

    try:
        form_service.publish_version(version.id)
    except FormValidationError as e:
        raise FieldDetectionValidationError(
            str(e), "field_detection_invalid_result"
        ) from e

    logger.info(
        "Question generation result: document=%s questions=%d skipped=%d "
        "version=%s supported_output_languages=%s translation_duration=%.2fs "
        "unique_texts=%d cache_hits=%d catalog_hits=%d batch_calls=%d "
        "fallback_calls=%d ollama_call_count=%d untranslated=%d",
        doc.public_id,
        added_field_count,
        skipped_field_count,
        version.status,
        ",".join(version.supported_output_languages or []),
        translation_duration,
        translation_stats.unique_texts,
        translation_stats.cache_hits,
        translation_stats.catalog_hits,
        translation_stats.provider_calls,
        translation_stats.fallback_single_calls,
        translation_stats.ollama_call_count,
        translation_stats.unresolved,
    )

    session_service = SessionService(db)
    return session_service.create_session(
        form_version_id=version.id,
        user_language=user_language,
        output_language=output_language,
        current_user_id=current_user_id,
        source_document_id=doc.id,
    )
