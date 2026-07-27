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
language is kept strictly separate from the session's `user_language`: the
original detected text is always stored under the source language (for
mapping/audit — never discarded), and a `user_language` translation is
produced via the AI provider only when the two differ. Stable option
`value`s are never translated, only the display label shown to the user.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai.mock_provider import AIProvider
from app.ai.text_translation import TextTranslation, translate_text
from app.documents.models import SourceDocument
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
from app.sessions.models import FormSession
from app.sessions.services import SessionService

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


def _label_translations(
    translation: TextTranslation,
) -> list[TranslationSchema]:
    """Builds the field-label TranslationSchema rows: the original source
    text is always kept (for mapping/audit), plus the user-language
    translation only when it differs from the source."""
    translations = [
        TranslationSchema(
            language=translation.source_language, label=translation.source_text
        )
    ]
    if translation.target_language != translation.source_language:
        translations.append(
            TranslationSchema(
                language=translation.target_language,
                label=translation.translated_text,
            )
        )
    return translations


def _option_translations(
    translation: TextTranslation,
) -> list[OptionTranslationSchema]:
    translations = [
        OptionTranslationSchema(
            language=translation.source_language, label=translation.source_text
        )
    ]
    if translation.target_language != translation.source_language:
        translations.append(
            OptionTranslationSchema(
                language=translation.target_language,
                label=translation.translated_text,
            )
        )
    return translations


async def create_session_from_confirmed_fields(
    db: Session,
    doc: SourceDocument,
    detection_result: FieldDetectionResult,
    user_language: str,
    output_language: str,
    ai_provider: AIProvider,
) -> tuple[FormSession, str]:
    confirmed_fields = [
        field for field in detection_result.fields if field.review_status == "confirmed"
    ]
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
        supported_output_languages=sorted({_DEFAULT_SOURCE_LANGUAGE, user_language}),
        origin="dynamic_detection",
        pdf_template_key=None,
    )

    used_keys: set[str] = set()
    try:
        for position, detected_field in enumerate(confirmed_fields):
            field_type = _map_field_type(detected_field)
            key = _unique_key(detected_field.normalized_name, used_keys)

            label_translation = await translate_text(
                ai_provider,
                detected_field.label,
                _DEFAULT_SOURCE_LANGUAGE,
                user_language,
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
                    option_translation = await translate_text(
                        ai_provider,
                        option.value,
                        _DEFAULT_SOURCE_LANGUAGE,
                        user_language,
                    )
                    options.append(
                        OptionSchema(
                            value=option.value,
                            position=option.position,
                            translations=_option_translations(option_translation),
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
                    translations=_label_translations(label_translation),
                    options=options,
                ),
            )

        form_service.publish_version(version.id)
    except FormValidationError as e:
        raise FieldDetectionValidationError(
            str(e), "field_detection_invalid_result"
        ) from e

    session_service = SessionService(db)
    return session_service.create_session(
        form_version_id=version.id,
        user_language=user_language,
        output_language=output_language,
    )
