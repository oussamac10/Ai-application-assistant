"""Bridges confirmed detected fields into the existing guided-session
workflow.

Confirmed DetectedField rows are materialized into a synthetic, published
FormTemplate/FormVersion/FormField set — reusing FormService's own
validation (choice fields need options, published versions are immutable,
labels required for the source language, ...) rather than re-implementing
any of it. SessionService.create_session then starts a real guided session
completely unmodified. Only user-confirmed fields are ever used; pending or
rejected candidates never generate a question.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

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


def create_session_from_confirmed_fields(
    db: Session,
    doc: SourceDocument,
    detection_result: FieldDetectionResult,
    user_language: str,
    output_language: str,
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
        source_language=user_language,
        supported_output_languages=[user_language],
        origin="dynamic_detection",
        pdf_template_key=None,
    )

    used_keys: set[str] = set()
    try:
        for position, detected_field in enumerate(confirmed_fields):
            field_type = _map_field_type(detected_field)
            key = _unique_key(detected_field.normalized_name, used_keys)

            options = (
                [
                    OptionSchema(
                        value=option.value,
                        position=option.position,
                        translations=[
                            OptionTranslationSchema(
                                language=user_language, label=option.value
                            )
                        ],
                    )
                    for option in detected_field.options
                ]
                if field_type in _CHOICE_TYPES
                else []
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
                    translations=[
                        TranslationSchema(
                            language=user_language, label=detected_field.label
                        )
                    ],
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
