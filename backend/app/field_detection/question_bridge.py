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
from dataclasses import dataclass

from sqlalchemy.orm import Session

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
from app.translation.base import TranslationProvider
from app.translation.factory import (
    build_fallback_translation_provider,
    build_translation_provider,
)
from app.translation.service import TranslationStats, translate_texts

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


def _supported_languages(
    source_language: str, user_language: str, output_language: str
) -> list[str]:
    """Every language the generated version claims to support.

    `FormService.publish_version` enforces an option translation for each of
    them, so a version claiming a language it has no rows for cannot be
    published — which is exactly how a document containing any choice field
    silently failed whenever the user and output languages differed.

    All three are needed for different reasons: the source language holds the
    original text (audit and PDF mapping), the user language is what the
    guided questions display, and the output language is what the completed
    form is written in — `SessionService.create_session` rejects a version
    that does not list it.
    """
    return sorted({source_language, user_language, output_language})


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


def _persisted_catalog_labels(
    db: Session, fields: list[DetectedField], language: str
) -> dict[str, str]:
    """Translations already stored for these semantic keys but not yet
    approved. Lower precedence than approved text and higher than the
    provider: text translated once and persisted must not be paid for again."""
    repo = QuestionRepository(db)
    persisted: dict[str, str] = {}
    for detected in fields:
        if not detected.label or detected.label in persisted:
            continue
        translation = repo.get_pending_translation(detected.normalized_name, language)
        if translation is not None and translation.text:
            persisted[detected.label] = translation.text
    return persisted


def _translatable_texts(fields: list[DetectedField]) -> list[str]:
    """Every distinct string the document needs rendered in another language:
    field labels and choice-option display labels.

    Option *values* appear here only as the source of their display label —
    the stable value written to the form is never translated.
    """
    texts: list[str] = []
    for detected in fields:
        if detected.label:
            texts.append(detected.label)
        for option in detected.options:
            if option.value:
                texts.append(option.value)
    return texts


@dataclass(frozen=True)
class _PreparedTranslations:
    """Everything the version builder needs about language.

    `source_language` is the language the document's labels are *actually* in,
    as reported by the provider — not the assumption the detection pipeline
    had to make. Carrying it here is what lets the generated version record the
    original text under its true language instead of mislabelling German text
    as English.
    """

    source_language: str
    by_language: dict[str, dict[str, str]]
    deferred_languages: tuple[str, ...]
    detection_confidence: float | None = None


def _resolve_source_language(stats: TranslationStats) -> str:
    """The document's real source language, or the assumed one if no provider
    reported a detection.

    Exactly one language is chosen even when a mixed document yields several:
    a form version has a single source language, and the most frequently
    detected one is the only defensible choice. Ambiguity is logged, never
    guessed at silently.
    """
    detected = stats.detected_source_languages
    if not detected:
        return _DEFAULT_SOURCE_LANGUAGE
    if len(detected) > 1:
        logger.info(
            "Multiple source languages detected (%s); using %s for the version",
            ",".join(detected),
            detected[0],
        )
    return detected[0]


async def _prepare_translations(
    db: Session,
    fields: list[DetectedField],
    user_language: str,
    output_language: str,
    stats: TranslationStats,
    provider: TranslationProvider,
    fallback_provider: TranslationProvider | None,
) -> _PreparedTranslations:
    """Resolves the document's source language and translates it into the
    interface language, in a single batched provider call.

    Ordering matters: translation happens *before* the form version is created,
    because the provider's detected source language is what the version should
    record. Field detection cannot detect a document's language, so before this
    phase every generated version claimed `en` regardless — which both
    mislabelled the original text and sent German labels on a pointless
    `en -> de` round trip.

    Only the interface language is translated here. Other supported languages
    get source-text placeholders that `app/translation/backfill.py` replaces
    when review or export needs them.
    """
    texts = _translatable_texts(fields)

    translated = await translate_texts(
        texts,
        user_language,
        provider,
        fallback_provider,
        # None means "detect it" — the whole point of this phase.
        source_language=None,
        assumed_source_language=_DEFAULT_SOURCE_LANGUAGE,
        stats=stats,
        approved_lookup=_approved_catalog_labels(db, fields, user_language),
        persisted_lookup=_persisted_catalog_labels(db, fields, user_language),
    )

    source_language = _resolve_source_language(stats)
    by_language: dict[str, dict[str, str]] = {}

    # When the document is already in the interface language, the source rows
    # carry the text and no second set is needed.
    if user_language != source_language:
        by_language[user_language] = translated

    deferred = [
        language
        for language in {output_language} - {source_language, user_language}
        if language
    ]
    for language in sorted(deferred):
        by_language[language] = {text: text for text in texts}

    return _PreparedTranslations(
        source_language=source_language,
        by_language=by_language,
        deferred_languages=tuple(sorted(deferred)),
    )


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
    source_text: str,
    source_language: str,
    translations_by_language: dict[str, str],
) -> list[TranslationSchema]:
    """Builds the field-label rows: the original text is always kept under the
    document's own (detected) language for mapping and audit, plus one row per
    other language. `translations_by_language` never contains the source
    language, so no row is ever emitted twice."""
    rows = [TranslationSchema(language=source_language, label=source_text)]
    rows.extend(
        TranslationSchema(language=language, label=label)
        for language, label in translations_by_language.items()
        if language != source_language
    )
    return rows


def _option_translations(
    source_text: str,
    source_language: str,
    translations_by_language: dict[str, str],
) -> list[OptionTranslationSchema]:
    rows = [OptionTranslationSchema(language=source_language, label=source_text)]
    rows.extend(
        OptionTranslationSchema(language=language, label=label)
        for language, label in translations_by_language.items()
        if language != source_language
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
    translation_provider: TranslationProvider | None = None,
    fallback_translation_provider: TranslationProvider | None = None,
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

    # Translation is its own provider family (Phase 15). `ai_provider` is
    # still required for everything else, and is what the Ollama translation
    # provider delegates to when it is the selected or fallback backend.
    if translation_provider is None:
        translation_provider = build_translation_provider(
            settings.TRANSLATION_PROVIDER, ai_provider
        )
    if fallback_translation_provider is None:
        fallback_translation_provider = build_fallback_translation_provider(
            settings.TRANSLATION_FALLBACK_PROVIDER, ai_provider
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

    # Translation runs *before* the version is created, because the provider's
    # detected source language is what the version must record — see
    # `_prepare_translations`. One batched provider call for the whole
    # document; other supported languages get placeholders that
    # `app/translation/backfill.py` replaces on demand.
    translation_stats = TranslationStats()
    translation_started = time.perf_counter()
    prepared = await _prepare_translations(
        db,
        confirmed_fields,
        user_language,
        output_language,
        translation_stats,
        provider=translation_provider,
        fallback_provider=fallback_translation_provider,
    )
    translation_duration = time.perf_counter() - translation_started
    source_language = prepared.source_language
    translations_by_language = prepared.by_language

    version = form_service.create_draft_version(
        form_template_id=template.id,
        # The detected language, not an assumption: the original label text is
        # stored under the language it is actually written in.
        source_language=source_language,
        # Must include output_language itself, not just the source/user
        # languages — otherwise a user who picks an output language that
        # differs from both (e.g. English interface, German output) makes
        # SessionService.create_session() below reject its own freshly
        # created version with "output language is not supported", an
        # unhandled-looking failure for a perfectly normal selection.
        supported_output_languages=_supported_languages(
            source_language, user_language, output_language
        ),
        origin="dynamic_detection",
        pdf_template_key=None,
    )

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
                                option.value, source_language, option_translations
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
                        detected_field.label, source_language, label_translations
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
        "version=%s supported_output_languages=%s source_language=%s "
        "eager_language=%s "
        "deferred_languages=%s translation_duration=%.2fs provider=%s "
        "unique_texts=%d protected_skipped=%d catalog_hits=%d persisted_hits=%d "
        "cache_hits=%d provider_calls=%d fallback_calls=%d characters=%d "
        "provider_latency=%.2fs detected_source=%s untranslated=%d",
        doc.public_id,
        added_field_count,
        skipped_field_count,
        version.status,
        ",".join(version.supported_output_languages or []),
        source_language,
        user_language,
        ",".join(prepared.deferred_languages) or "-",
        translation_duration,
        translation_stats.primary_provider or "-",
        translation_stats.unique_texts,
        translation_stats.protected_skipped,
        translation_stats.catalog_hits,
        translation_stats.persisted_hits,
        translation_stats.cache_hits,
        translation_stats.provider_calls,
        translation_stats.fallback_provider_calls,
        translation_stats.translated_character_count,
        translation_stats.provider_latency_seconds,
        ",".join(translation_stats.detected_source_languages) or "-",
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
