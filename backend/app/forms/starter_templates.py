"""Auto-provision ready-to-send German starter templates for new organizations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.commands.seed_german_templates import GERMAN_TEMPLATE_SPECS
from app.forms.models import FormTemplate
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService

if TYPE_CHECKING:
    from app.organizations.models import Organization

logger = logging.getLogger(__name__)

STARTER_TEMPLATE_KEYS: tuple[str, ...] = (
    "de-anmeldung",
    "de-wohnungsgeberbestaetigung",
    "de-aufenthaltstitel",
)


def provision_starter_templates_for_organization(
    db: Session,
    org: Organization,
) -> list[FormTemplate]:
    """Idempotently provision 3 ready-to-send German templates for a new organization.

    Gives trial/sandbox organizations immediate <60s time-to-value without requiring
    a manual PDF upload + review step first.
    """
    existing = (
        db.query(FormTemplate.id).filter(FormTemplate.organization_id == org.id).first()
    )
    if existing is not None:
        return []

    spec_by_key = {spec["key"]: spec for spec in GERMAN_TEMPLATE_SPECS}
    form_service = FormService(db)
    created: list[FormTemplate] = []
    org_suffix = org.id[:8]

    for base_key in STARTER_TEMPLATE_KEYS:
        spec = spec_by_key.get(base_key)
        if spec is None:
            continue

        scoped_key = f"{base_key}--{org_suffix}"
        if db.query(FormTemplate.id).filter(FormTemplate.key == scoped_key).first():
            continue

        template = form_service.create_template(
            key=scoped_key,
            name=spec["name"],
            description=spec.get("description"),
        )
        template.organization_id = org.id
        template.submission_method = str(
            spec.get("submission_method", "print_and_sign")
        )
        template.instructions = spec.get("instructions")
        template.required_documents = list(spec.get("required_documents", []))
        db.flush()

        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language=spec.get("source_language", "de"),
            supported_output_languages=spec.get("supported_output_languages", ["de"]),
            origin="predefined_template",
            pdf_template_key=f"{base_key}-v1",
        )

        for pos, fspec in enumerate(spec["fields"], start=1):
            form_service.add_field_to_draft(
                version.id,
                FieldCreate(
                    key=fspec["key"],
                    field_type=fspec["field_type"],
                    required=fspec["required"],
                    position=pos,
                    configuration=fspec["configuration"],
                    question_key=fspec["question_key"],
                    translations=[
                        TranslationSchema(language="de", label=fspec["label_de"]),
                        TranslationSchema(language="en", label=fspec["label_en"]),
                    ],
                ),
            )

        form_service.publish_version(version.id)
        created.append(template)

    if created:
        logger.info(
            "Provisioned %d starter templates for organization %s",
            len(created),
            org.id,
        )
    return created
